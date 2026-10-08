# -*- coding: utf-8 -*-
"""M6/M7 检索层：查询理解 + **五路**召回 + 融合排序（全部离线、确定性、不用大模型）

五路（对应《系统实现逻辑》M6–M7，比外部交付多两路"词学专用"检索）：
    ① 二字组路（`lines_bigram`，FTS5 + BM25）：中文子串级语义近似检索。
    ② 全文路（`lines_fts`，FTS5 短语）：整句/短语精确匹配。
    ③ 元数据路（SQL）：朝代 / 词人 / 词牌。
    ④ 数值路（SQL + 排序）：仄声比例、字数、句数、变化值、长句阈值。
    ⑤ **声律模式路**（`lines.pz`）：用平仄串检索，如 `仄仄平平`、`平仄?平`
       ——「找出与某词牌声律格局相合的句子」是词学研究的真问题，外部交付没有这一路。
    ⑥ **声情路**（`poems.scene`）：按声情转向（后段上升/后段下降/前后持平）过滤。

融合：各路得分归一后加权求和；**硬条件（元数据/数值/声律/声情）取交集**，
不满足硬条件者不进入候选（宁可少召回，不可乱召回）。

用法：
  python retrieve.py --db data/corpus.db --query "清 临江仙 仄声比例高于45%" --topk 5 --explain
  python retrieve.py --db data/corpus.db --query "声律 仄仄平平仄" --mode pz
  python retrieve.py --db data/corpus.db --query "后段上升 清 临江仙"
"""
import argparse
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 汉字范围**单一来源**：一律取 corpus.HAN_CLASS（含 CJK 扩展 A）。
# 审查 C15 指出：此前 retrieve/pronounce/prosody 各写一套，改一处会漏另一处。
from corpus import HAN_CLASS as _HAN_CLASS          # noqa: E402
_HAN_ONE = re.compile('[%s]' % _HAN_CLASS)

# 数值条件的合理区间（**单一来源**：规则路与大模型路共用；审查 C17 指出此前只有大模型路有）
RNG_BOUNDS = {'ze_min': (0, 100), 'ze_max': (0, 100), 'len_min': (1, 500),
              'len_max': (1, 500), 'sent_min': (1, 80), 'sent_max': (1, 80),
              'change_min': (-100, 100), 'change_max': (-100, 100),
              'thr_min': (1, 60), 'thr_max': (1, 60)}

# 中文数字 → 阿拉伯数字：口语问法「不到五十」「五到八句」「超过一半」里全是汉字数字
# （2026-10-01 深夜，答案解析实测：「字数不到五十的短词」规则路整条漏掉）。
# 2026-10-02 收尾修复：原实现只支持 ≤99，且**正则** `[零…十两]+` 会把「一百」**只吃到「一」**
#   → 「字数不到一百的清词」静默落成 len_max=1（既不报错、也不进 unparsed——最危险的「静默错答案」）。
# 现在：① 补 百/千/万；② NUM 上加安全前瞻，保证**要么整条正确落地、要么整条不落地**。
_CN_DIGITS = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
              '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
_CN_UNITS = {'十': 10, '百': 100, '千': 1000, '万': 10000}


def cn_num(t):
    """中文数字 → int（五十=50、十五=15、二十三=23、一百=100、两千三百=2300）；不认识返回 None。

    宁可返回 None（调用方会把该条件整条丢弃，并如实体现在 unparsed 里），
    **绝不返回一个被截断的错误值**——「静默错答案」远比「漏掉一个条件」危险。
    """
    if not t:
        return None
    if t.isdigit():
        return int(t)
    total = section = number = 0
    seen = False
    for ch in t:
        if ch in _CN_DIGITS:
            number = _CN_DIGITS[ch]
            seen = True
        elif ch == '万':
            total += (section + number or 1) * 10000
            section = number = 0
            seen = True
        elif ch in _CN_UNITS:                     # 十 / 百 / 千
            section += (number or 1) * _CN_UNITS[ch]
            number = 0
            seen = True
        else:
            return None                           # 碰到不认识的字符 → 整条判为不可解析
    return (total + section + number) if seen else None


def num_lit(s):
    """数字字面量（阿拉伯或中文）→ float；不认识返回 None。"""
    v = cn_num(s)
    if v is not None:
        return float(v)
    try:
        return float(s)
    except (TypeError, ValueError):
        return None
DYN = ('清', '宋', '元')
# 语料只含清/宋/元。问句明确指向语料外朝代时必须**拒答**，不能拿语义相近的篇凑数。
UNSUPPORTED_DYN = ('汉', '唐', '五代', '五代十国', '魏晋', '南北朝', '隋', '明', '金', '辽',
                   '先秦', '诗经', '楚辞', '汉朝', '唐朝', '宋朝以前')
MIN_NAME_LEN = 2            # 单字作者名（苏/袁…）参与匹配会把正文片段误当条件
UP = r'(?:高于|大于|多于|超过|超出|不低于|不少于|不小于|不亚于|至少|以上|≥|>=)'
# ⚠ 2026-10-03：补「不小于/不亚于/以上」——口语里很常见，缺了它整条数值条件会**静默丢失**
#   （实测「前后段变化幅度不小于二十」→ 范围从 1393 篇变成全库 58769 篇）。
DOWN = r'(?:低于|小于|少于|不足|不到|不超过|不高于|不大于|不重于|至多|以下|≤|<=)'
PZ_RE = re.compile(r'^[平仄?？]{3,}$')     # 声律模式：整串只由 平/仄/？（任意）组成
SCENES = {'后段上升': ('上升', '升高', '抬高', '走高', '趋于上升'), '后段下降': ('下降', '降低', '走低', '趋于下降'),
          '前后持平': ('持平', '不变', '平稳', '两段持平')}
SCENE_ALIASES = {}          # 别名 → 规范名（由 SCENES 派生；单一来源）
for _sc, _ws in SCENES.items():
    for _w in _ws:
        SCENE_ALIASES[_w] = _sc
# 提问虚词/意图词：抽词面时必须剔除，否则「想表达」「平仄」会被当成检索词
# ⚠ 2026-10-02 修：**问句框架词**必须并入 STOPWORDS。
#   它们描述的是「要做什么」（量词/统计输出/连接），不是要检索的内容。
#   不收进来就会被当**词面条件**——实测 1000 题里 77% 的题词面被污染成
#   「正好有一句」「的中位数是」「多几篇」这种垃圾（答卷因此答非所问）。
FRAME_WORDS = (
    '正好有', '每一句都', '每句都', '所有句子都', '没有任何一句', '没有任何句子',
    '一句都不', '一句也不', '至少有一句', '占比不低于', '占比不少于', '占比至少',
    '中位数', '众数', '最常出现的取值', '最常出现', '多几篇', '少几篇', '多多少', '差几篇',
    '句位', '奇数句位', '偶数句位', '句子数', '满足', '之间的', '之间', '整句', '另有',
    '同时也满足', '同时满足', '其', '几篇', '多少篇', '取值', '有多大比例',
    '第大的那一篇', '的那一篇', '的那一首', '哪一篇', '哪一首', '一句', '有的句',
    # 礼貌语/提问套话（不并入就会被当词面，如「帮我找写」）
    '帮我找写', '帮我找', '帮我查', '帮我算', '帮我', '麻烦', '请问', '想看看', '查一下',
    '请给出', '请统计', '给我个结果', '能帮我', '请列', '问一下', '劳驾', '我想找',
    # 指标/维度词（它们是「问什么」，不是「检索什么」）
    '仄声', '平声', '字数', '句数', '篇幅', '占比', '比例', '声律', '模式', '阈值',
    '变化值', '变幅', '声情', '词作', '作品数', '平均值', '总字数',
)
# 「提问/指标虚词」：整段里**只要含**它们，就不是「要检索的题名」（用于题名识别的守卫）。
# 与 FRAME_WORDS 略有不同：这些词常出现在**问句尾部**（「…的平仄」「…的作者是谁」），
# 单独成串时更该被当成「问什么」而非「检索什么」。
_Q_FRAME = ('平仄', '声律', '声调', '韵脚', '押韵', '声情', '风格', '特点', '作者', '词人',
            '朝代', '词牌', '字数', '句数', '占比', '比例', '意思', '含义', '意涵', '写作',
            '是谁', '什么', '哪些', '多少', '怎么看', '怎么', '如何', '为何', '为什么')

STOPWORDS = FRAME_WORDS + ('什么', '为什么', '为何', '怎么', '如何', '是否', '请问', '想问', '一下',
             '想表达', '表达', '意图', '意思', '含义', '写作目的', '目的', '有什么',
             '有哪些', '哪些', '哪首', '哪篇', '哪一句', '多少', '以及', '关于', '方面',
             '平仄', '声律', '声调', '韵脚', '押韵', '声情', '风格', '特点', '这首',
             '那首', '作品', '词作', '模式', '声律模式', '比例', '水平', '阈值',
             '的词', '这首词', '那首词', '一首')

# 并列/选择连接词。坑（**2026-09-30 主人实测**）：问「句脚是「灯」或者「声」的清词有哪些」，
# 旧解析只取第一个值，且把「或者」当成词面条件——条件被静默丢掉了一半，答案仍是「像对的」。
# 现在：先按连接词切段，能补齐同一字段的多值就补齐（灯的∪声的），补不上就**如实披露未理解片段**。
CONNECTORS = ('或者', '或是', '或', '和', '与', '以及', '及', '还有', '、')
CONN_SPLIT_RE = re.compile('|'.join(re.escape(c) for c in
                                    sorted(CONNECTORS, key=len, reverse=True)))


def is_hanzi(c):
    """是否汉字（单一来源 corpus.HAN_CLASS，含扩展 A）。"""
    return bool(_HAN_ONE.match(c or ' '))


def bigrams(text):
    han = [c for c in text if is_hanzi(c)]
    if len(han) < 2:
        return han
    return [han[i] + han[i + 1] for i in range(len(han) - 1)]


class QuerySpec:
    """查询理解结果（确定性解析；也可由大模型填写，但字段全在这里校验）。

    `*_any` 是**权威存储**（多值＝并列/选择，如「句脚是【灯】或者【声】」）；
    单值快捷字段 `dynasty/cipai/author/tail` 由 `_finalize()` 派生，仅在恰一个值时非空。
    """

    def __init__(self):
        self.dynasty_any = []
        self.author_any = []
        self.cipai_any = []
        # ⚠ 2026-10-05 新增：**题名（词题）**——「蝶恋花·清明同诸子集原白斋中」里的
        #   「清明同诸子集原白斋中」是**题名**，不是正文（词面）。朋友实测抓到：旧版把它
        #   当词面去 `raw` 里搜 → 该串在正文里 0 命中 → 融合分堆出 1069 篇不相关的词，
        #   而正确答案（题名唯一命中的那 1 篇）根本没露面。官方口径亦承认题名独立于正文
        #   （题库统一注明「不计标点、空白和**题名**」）。这一族条件必须走 `title` 列。
        self.title_any = []
        self.tail_any = []             # 句脚字（可多个，取并集）
        self.tail_pz = None            # 句脚字的平仄（平/仄）
        self.pz = None                 # 声律模式（平仄串，? = 任意）
        self.scene = None              # 声情转向
        self.dynasty = None            # 单值快捷字段（由列表派生）
        self.author = None
        self.cipai = None
        self.title = None              # 题名（词题）——「词牌·题名」里的题名部分
        self.tail = None
        self.keywords = []
        self.rng = {}                  # 数值条件：ze_min/ze_max/len_min/len_max/sent_min/sent_max/change_min/change_max/thr_min/thr_max
        self.unsupported = None
        self.unparsed = []             # 没被理解成条件的片段（必须如实披露，不静默丢）
        self.agg = None                # 分组对比统计：{'group_by','values','metric','text'}
        # 配对题（「找出几对每个位置上的字平仄都相同的两首词」）：与篇筛选完全不同的一类意图，
        # 问的是**篇与篇之间**的关系（平仄串逐位相同），不是「哪些篇满足某条件」。
        self.pair = None               # {'dims':('tone',)|('text',), 'n_frame':int}
        self.pair_label = None         # 人话名（如「全篇逐位平仄完全相同」）
        # 极值／排序题（「哪一首…最高/最低」）：排序指标与其 SQL 列（列名取自白名单，防注入）
        self.order_by = None           # 指标名，见 ORDER_COLS
        self.order_col = None          # SQL 列名（白名单映射，不用用户串）
        self.order_dir = 'desc'        # desc＝取大，asc＝取小
        self.extreme = None            # 'max' / 'min'（None＝只排序，不判定极值）
        self.order_label = None        # 指标的人话名（如「仄声比例」）
        self.order_src = None          # '规则' / '大模型'
        self.source = '规则'           # 解析来源：规则／大模型
        # ⚠ 2026-10-06 修（外部审查 P2-17）：一个 `raw` 字段原先同时承担**两种语义**——
        #   「用户原话」与「挖空算子后的解析工作文本」（parse_query 先 _mask_ops 再传入，
        #   `_parse_query_inner` 把 mask 后的文本存进 raw），而 `search()` 又拿它做词面检索。
        #   现拆开：`raw_question`=用户原话（审计/日志/调试用，永不被改写）；
        #   `raw`=挖空算子后的**检索工作文本**（保持既有检索行为不变，仅把语义写清）。
        self.raw_question = ''
        self.raw = ''
        # ⚠ 2026-10-02 新增：**句级算子**（旧版只有「∃ 存在」一种语义）
        self.line_q = None      # dict：{'op':∀|∄|≥k|=k|占比≥p|条数∈[a,b], 'pred':(kind,val), ...}
        self.tail_each = []     # 篇内两值**交集**（每个取值都必须出现一句）
        self.pz_exact = None    # 平仄串**全等**（非子串）
        self.parity = None      # 句位奇偶：0=奇数位(1,3,5…)，1=偶数位
        self.consist = None     # 一致性：声情标注为 X 但实测前后段相反
        self.change_abs = False  # 「变化**幅度**」比绝对值；「变化**值**」比有符号值
        # 对比题里被清掉的**组名**（组名是「被比较的组」，不是筛选条件；但判定「某个字是不是
        # 朝代/人名的一部分」时仍要算上它们，见 `_patch_parse`）
        self.cleared_names = []
        self.disp_group = None  # 离散度最大组：按该维度分组，取组内指标波动最大的那一组
        # ⚠ 2026-10-08 新增（检索层预留字段，任务C）：**规则路永不产出这两个字段**，
        #   只有大模型理解路（qlm/ask）与前端会填。因此对 1000 题（不开 LLM）**零影响**。
        #   改前 → 无这两个字段（大模型给的 semantic、前端传的上一轮 pid 集合无处落地）。
        #   依据（文件级）：`has_hard`/`_sql`/`search` 三处按「非空才生效」接入，见各函数注释。
        #   例：「那里面哪个最短」→ 前端传 ctx_pids=[上一轮命中的 pid…]；「写离愁的清词」→
        #   大模型给 semantic=["离愁","秋日"]。
        self.semantic = []      # 语义检索**扩展词**（如 ["秋日","离愁","凄凉"]）——**不参与 SQL**，
                                #   只并入全文检索（`route_bigram`/`route_phrase`）以**提升召回**。
        self.ctx_pids = []      # **上一轮结果集的 pid 列表**——**参与 SQL**（`p.pid IN (…)`），是硬条件。
        # ⚠ 2026-10-08 新增（主人实测驱动）：「**提取型**意图」——问的不是「筛出哪些篇」，
        #   而是「**在这一篇里取第 N 句第 M 个字**」。实测：「高旭《浪淘沙·杨笃生自沉利物浦死，
        #   吊以此阕》第四句第三字是哪个字」被当成**词面**送进全文检索 → 答了句脚，**答非所问**；
        #   正确篇目其实**已经命中**（题名把住了），缺的只是「取哪一句的哪一个字」这一步。
        #   结构：`{'sent': N(1 起), 'pos': M(1 起), 'unit': 'char'}`。
        #   **不参与 SQL**（它不是筛选条件，只会把检索面缩小到 0），只在**命中之后**用于篇内取值。
        self.extract = None
        # ⚠ 2026-10-08 新增（外部架构审查核心条目）：**布尔过滤树**（`queryplan.py` 的
        #   `filters`）。默认 **None**——这是「零回归的生命线」：为 None 时 `_sql()` 走原路径
        #   （逐字段编译），**逐字节不变**；非 None 时才改走 `_sql_filters()` 递归编译。
        #   为什么必须有：平铺槽位表只能表达「字段间 AND、字段内 IN 并集」，无法表达
        #   「（写秋景 或 写离愁）且 不是 临江仙的清词」这类**任意嵌套布尔**。
        #   规则路（`parse_query`）**永不产出**本字段；只有 `queryplan.to_spec()`（把 Plan 立为
        #   执行真源时）或大模型路/前端会设。故对 1000 题（规则路、不填本字段）零影响。
        #   形状（JSON 可序列化）：`{"and":[…]}` / `{"or":[…]}` / `{"not":{…}}` /
        #   `{"field":…,"op":…,"value":…}`；编译见 `_sql_filters()`。
        self.filters_tree = None

    def describe(self):
        p = []
        dyn = _vals(self, 'dynasty')
        au = _vals(self, 'author')
        cp = _vals(self, 'cipai')
        ti = _vals(self, 'title')
        tl = _vals(self, 'tail')
        if dyn:
            p.append('朝代=%s' % ' 或 '.join(dyn))
        if au:
            p.append('词人=%s' % ' 或 '.join(au))
        if cp:
            p.append('词牌=%s' % ' 或 '.join(cp))
        if ti:
            p.append('题名=%s' % ' 或 '.join(ti))
        if self.pz:
            p.append('声律模式=%s' % self.pz)
        if self.scene:
            p.append('声情=%s' % self.scene)
        if tl:
            p.append('句脚字=%s' % ' 或 '.join(tl))
        if self.tail_pz:
            p.append('句脚平仄=%s' % self.tail_pz)
        # ⚠ 2026-10-02：句级算子也要出现在【查询理解】里（否则用户看不出引擎按什么算的）
        if self.line_q:
            _q = self.line_q
            _k, _v = _q['pred']
            # ⚠ 惰性分支：字典字面量会**一次性求值全部键**，`'%s~%s' % _v` 在 _v 是字符串时直接 TypeError
            if _k == 'tail':
                _ptxt = '句脚字=%s' % _v
            elif _k == 'tail_any':
                _ptxt = '句脚字=%s' % '／'.join(_v)
            elif _k == 'tail_pz':
                _ptxt = '句脚平仄=%s' % _v
            elif _k == 'pz':
                _ptxt = '声律串含%s' % _v
            elif _k == 'pz_exact':
                # ⚠ 2026-10-08（任务B）：`pz_exact` 谓词原先落到下面的 else → 被误标成「偶数句位」
                #   （_v 是平仄串不是 0/1）。改前行为：显示「句级算子=每一句都（偶数句位）」，
                #   与条件不符；改后行为：显示「平仄串全等=仄仄平平仄」。仅影响【查询理解】文案。
                _ptxt = '平仄串全等=%s' % _v
            elif _k == 'len':
                _ptxt = '句长=%s~%s' % (_v[0], _v[1])
            else:                              # 只剩 parity（句位奇偶），其 _v ∈ {0,1}
                _ptxt = '%s数句位' % ('奇' if _v == 0 else '偶')
            _optxt = {'∃': '至少有一句', '∀': '每一句都', '∄': '没有任何一句',
                      '≥k': '至少 %d 句' % _q.get('k', 0),
                      '=k': '正好 %d 句' % _q.get('k', 0),
                      '占比≥p': '满足句占比≥%.0f%%' % (100 * _q.get('ratio', 0)),
                      '条数∈[a,b]': '满足句数在 %d~%d' % (_q.get('ka', 0), _q.get('kb', 0))}[_q['op']]
            p.append('句级算子=%s（%s）' % (_optxt, _ptxt))
        if self.tail_each:
            p.append('篇内两值交集=%s' % ' 且 '.join(self.tail_each))
        if getattr(self, 'consist', None):
            p.append('一致性=声情标注为%s但实测前后段相反' % self.consist)
        if self.pz_exact:
            p.append('平仄串全等=%s' % self.pz_exact)
        if self.keywords:
            p.append('词面=%s' % '、'.join(self.keywords))
        # ⚠ 2026-10-08 新增（任务C）：语义扩展词与「上一轮结果集」范围的人类可读描述。
        #   改前 → 无；改后 → 各一行（规则路为空时不出这两行，故对 1000 题零影响）。
        if getattr(self, 'semantic', None):
            p.append('语义扩展=%s' % '、'.join(self.semantic))
        if getattr(self, 'ctx_pids', None):
            p.append('范围=上一轮结果（%d 篇）' % len(self.ctx_pids))
        # ⚠ 2026-10-08 新增：提取型意图的人类可读描述（规则路不产出时不出这行，故对 1000 题零影响）
        if getattr(self, 'extract', None):
            _ex = self.extract
            p.append('提取=第%s句第%s字' % (_ex.get('sent', '?'), _ex.get('pos', '?')))
        lab = {'ze_min': '仄声比例≥%.1f%%', 'ze_max': '仄声比例≤%.1f%%', 'len_min': '字数≥%d',
               'len_max': '字数≤%d', 'sent_min': '句数≥%d', 'sent_max': '句数≤%d',
               'change_min': ('|变化|≥%.1f' if getattr(self, 'change_abs', False) else '变化≥%.1f'),
               'change_max': ('|变化|≤%.1f' if getattr(self, 'change_abs', False) else '变化≤%.1f'), 'thr_min': '阈值≥%d',
               'thr_max': '阈值≤%d'}
        for k in ('ze_min', 'ze_max', 'len_min', 'len_max', 'sent_min', 'sent_max',
                  'change_min', 'change_max', 'thr_min', 'thr_max'):
            if k in self.rng:
                p.append(lab[k] % self.rng[k])
        if self.agg:
            if self.agg.get('values'):
                p.append('分组对比=%s（%s）' % ('／'.join(self.agg['values']), agg_label(self.agg)))
            else:                       # 组内极值：没有组名，只有维度与方向
                try:                    # 标签取自 aggregate 的单一来源（延迟导入，避免环）
                    import aggregate as _ag
                    _gl = _ag.GROUPS[self.agg['group_by']][1]
                except Exception:
                    _gl = {'author': '词人', 'cipai': '词牌', 'dynasty': '朝代'}.get(
                        self.agg['group_by'], self.agg['group_by'])
                p.append('分组统计=按%s（取%s，%s）'
                         % (_gl,
                            '最多' if self.agg.get('extreme', 'max') == 'max' else '最少',
                            agg_label(self.agg)))
        if self.pair:
            p.append('题型=配对题（%s）' % (self.pair_label or '全篇逐位平仄完全相同'))
        if self.order_by:
            p.append('排序=%s（取%s）'
                     % (self.order_label or self.order_by,
                        '最高' if self.extreme == 'max' else
                        ('最低' if self.extreme == 'min' else '指定顺序')))
        if self.unsupported:
            p.append('语料外范围：%s' % self.unsupported)
        return '；'.join(p) if p else '（无条件：按语义相关度排序）'


# ---- 分组对比统计（M8 聚合层）的解析常量（单一来源）----
# 问「哪一类总体上更高」＝问**组的统计量**，不是问篇；必须与「检索 + 举例」分开处理。
AGG_HINT_RE = re.compile(
    # ⚠ 2026-10-03：补「哪一(个|位|类|种)」与「最(高|低|多|少|大|小)」——
    #   旧版只认「哪个/哪一位」与「更高」，「哪一个朝代的…最高」整类漏掉（三组比较全废）。
    r'(哪一(?:个|位|类|种|些)|哪个|哪位|那个|谁|谁更|相对|对比|相比|比较|统计)'
    r'|(更高|更大|更多|更低|更少|较多|较少|高些|低些|最高|最低|最多|最少|最大|最小)')
# 指标 → 人话标签。**必须与 aggregate.METRICS 的键集合/取值一致**——
# `tools/dual_source_check.py` 第 4 条会逐键核对（同名同义的量不许两处各写一份）。
# 2026-10-02 修：aggregate 加了 `count`（组内极值「哪个词人最多」）而这里漏了，
# 键集合差集为 {'count'} → 双来源一致性门禁 FAIL（长期存在、刚被 reproduce 抓到）。
AGG_METRICS_LABEL = {'ze_ratio': '仄声占比', 'ping_ratio': '平声占比',
                     'han_len': '篇幅（字）', 'sent_n': '句数', 'share': '词作占比',
                     'count': '词作篇数',
                     'unspecified': '（问句未点明统计指标）'}
# 「X 的词作占比」这类问法（X 必须是语料里已知的类别，如声情）
SHARE_HINT_RE = re.compile(r'(词作占比|篇数占比|作品占比|词篇占比|的占比|篇占比|占多少)')


# ---- 「组内极值」：问「哪个词人/词牌/朝代…最多/最少/占比最高」----
# 为什么单独一路：这类问句里**没有两个组名**（不是「甲 vs 乙」），旧实现只支持
# 「预先给两个组名的对比」，于是把它当普通检索 → 答非所问。而它恰恰是词学研究里
# 最常见的一类问题（2026-10-01 主人运行记录实测：「…哪个词人的词占比最多」）。
GROUP_WORD_RE = (('author', re.compile(r'(词人|作者|诗人|哪个人|谁写|是谁|谁的作品|^谁)')),
                 ('cipai', re.compile(r'(词牌|曲牌|调名)')),
                 ('dynasty', re.compile(r'(朝代|时代|哪一代)')))
GROUP_EXTREME_RE = re.compile(
    r'(最多|最少|数量最多|篇数最多|词作最多|占比最多|占比最高|占最多|占比例最高|居首|排第一|'
    r'最多的是|最少的是|最常见|最常见的|出现最多|出现得最多|出现次数最多|用得最多|写得最多)')


def _group_extreme_of(text):
    """「哪个词人的词最多」→ ('author', 'max')；不是这类问法 → (None, None)。"""
    if not GROUP_EXTREME_RE.search(text):
        return (None, None)
    down = any(w in text for w in EXTREME_DOWN) or ('占比最少' in text) or ('占比最低' in text)
    for gb, rx in GROUP_WORD_RE:
        if rx.search(text):
            return (gb, 'min' if down else 'max')
    return (None, None)


def agg_label(agg):
    """聚合题的指标标签（单一来源；share 要带上类别本身）。"""
    if not agg:
        return ''
    if agg.get('metric') == 'share' and agg.get('cat'):
        return '%s的词作占比' % agg['cat'][1]     # 〔〕：类别名不是语料原文，「」只留给语料
    return AGG_METRICS_LABEL.get(agg.get('metric'), agg.get('metric') or '')
AGG_METRIC_PAT = (
    ('ping_ratio', ('平声占比', '平声比例', '平声比重')),
    ('ze_ratio', ('仄声占比', '仄声比例', '仄声比重', '仄的比例', '仄字占比')),
    ('han_len', ('篇幅', '字数', '字多长')),
    ('sent_n', ('句数', '句子数')),
    # ⚠ 2026-10-03：补 count（「作品数/篇数」）——`aggregate.METRICS` 与 `AGG_METRICS_LABEL`
    #   里都有 count，唯独这里的**匹配词表**漏了 → 「哪一个朝代的作品数最高」被判「没点明指标」
    #   而**拒答**（三组比较里一大批因此失效）。
    ('count', ('作品数', '篇数', '词作数量', '作品数量', '篇目数', '词数')),
)


# ---- 极值／排序题（「哪一首…最高/最低」）的解析常量（单一来源）----
# 为什么必须有：这类题问的是**某一指标在全部条件下的极值篇目**，
# 而五路融合分与「最高」毫无关系——旧版会把融合分第一的篇当答案，
# 还硬写「排序最前者为…」（无排序条件时的**虚假陈述**）。实测踩过。
EXTREME_UP = ('最高', '最多', '最大', '最长', '最密', '最强', '最重', '居首', '排第一')
EXTREME_DOWN = ('最低', '最少', '最小', '最短', '最疏', '最弱', '最轻')
# 指标 →（SQL 列，人话标签，是否反向）。“反向”＝指标越大对应列值越小（平声比例 ↔ 仄比）
ORDER_COLS = {
    'ze_ratio': ('ze_ratio', '仄声比例', False),
    'ping_ratio': ('ze_ratio', '平声比例', True),
    'han_len': ('han_len', '全篇字数', False),
    'sent_n': ('sent_n', '句数', False),
    'longest_len': ('longest_len', '最长句长度', False),
    'change': ('change', '前后段变化值', False),
}
# ⚠ 2026-10-03 修：问「前后段变化**幅度**最高」＝比**绝对值**——`change` 是**带符号**列
#   （前段−后段），按符号排会把「后段比前段低 100」排到最后，与真值口径（`ABS(change)`）不符
#   （实测 Q0138：真值 ci.song.8000.json#988（change=−100），引擎给 #992（change=+100））。
#   单一来源：排序表达式在这里登记，`order_pids`/`extreme_info`/作答层共用。
ORDER_EXPR = {'change': 'ABS(p.change)'}


def order_expr(spec):
    """排序用的 SQL 表达式（白名单；`change` 取绝对值）。"""
    col = spec.order_col or ORDER_COLS[spec.order_by][0]
    return ORDER_EXPR.get(spec.order_by, 'p.%s' % col)
# 注意顺序：「最长句」必须先于「字数」判（否则「最长句」会被误判成篇幅）
EXTREME_METRIC_PAT = (
    ('ping_ratio', ('平声字占比', '平声字比例', '平声占比', '平声比例', '平声比重',
                    '平字占比', '平的比例')),
    ('ze_ratio', ('仄声字占比', '仄声字比例', '仄字占比', '仄字比例', '仄声占比',
                  '仄声比例', '仄声比重', '仄的比例', '仄比')),
    ('longest_len', ('最长句', '最长的句子', '长句长度')),
    ('han_len', ('字数', '篇幅', '全篇字', '总字数')),
    ('sent_n', ('句数', '句子数')),
    ('change', ('变化值', '变幅', '声情变化', '前后段变化')),
)
# 极值题里剩下的“提问框架”不应当词面条件（「高旭写的哪首词里」→ 只留「高旭」）
EXTREME_FRAME_WORDS = ('哪首词里', '哪首词中', '哪一首', '哪首词', '哪一篇', '哪阕', '哪首',
                       '哪支', '词里', '词中', '其中', '写的', '的词')


def parse_extreme(conn, text):
    """极值／排序题 → 指标与方向。识别不了（没点名指标）就返回 None，**不猜**。

    ⚠ 2026-10-03 重写「认指标 + 摘字面」两处（逐题审查实测，一大批极值题因此答错篇）：
      ① **指标要与极值词**成对**取最近的那个**。旧版按 `EXTREME_METRIC_PAT` 的书写顺序取
         第一个出现在整句里的指标词——于是「仄声比例高于五十五%的作品里，**句数**最高的是
         哪一篇」被认成「仄声比例最高」（条件词压过了问句词，实测 Q0068/Q0081 一类）；
         「字数在…之间…**全篇字数**最低的那一篇」也同理。
      ② **摘字面只摘极值词附近的那一次**，不做整句 `replace`。旧版 `text.replace('字数','，')`
         会把**篇级条件**里的「字数在四十一到一百十六之间」一并抹掉 → 范围条件整条丢失
         （实测 Q0139：引擎命中 5052、真值 41 篇）。
    """
    ewords = [w for w in list(EXTREME_UP) + list(EXTREME_DOWN) if w in text]
    if not ewords:
        return None
    cands = []                            # (指标, 字面, 起, 止)
    for name, kws in EXTREME_METRIC_PAT:
        for k in kws:
            for mm in re.finditer(re.escape(k), text):
                cands.append((name, k, mm.start(), mm.end()))
    if not cands:
        return None                       # 「哪首最长、谁写得最好」这类没指标的：不靠猜
    best = None
    for name, k, s, e in cands:
        for w in ewords:
            for wm in re.finditer(re.escape(w), text):
                # ⚠ 2026-10-03：极值词**落在指标字面之内**的不算（「最**长句**长度最低」里
                #   的「最长」是「最长句」的一部分，不是「取最长」）——否则方向被判反
                #   （实测 Q0390：问「最长句长度**最低**」，引擎按「最长句长度**最高**」排序）。
                if not (wm.end() <= s or wm.start() >= e):
                    continue
                d = abs(s - wm.start())
                if best is None or d < best[0]:
                    best = (d, name, k, s, e, w, wm.start(), wm.end())
    if best is None:
        return None
    _d, metric, hit, hs, he, word, ws, we = best
    col, label, flip = ORDER_COLS[metric]
    kind = 'max' if word in EXTREME_UP else 'min'
    # 「最长句是…」这类**行级**题（问某一句的用字），不是篇级极值——判据：整句没有「篇/首」，
    # 也没有「哪一首」。⚠ 2026-10-03：旧式一见「句脚」+「最长句」就 return None，把**篇级**
    # 极值题「…的作品里，句数最高**的那一篇**」整类挡掉（实测 Q0674/Q0167：退化成普通检索、
    # 答「融合排序最前者」）。
    if '句' in hit and '句脚' in text and metric in ('sent_n', 'longest_len') \
            and '篇' not in text and not re.search(r'哪一(?:篇|首|阕|支)', text):
        return None
    asc = (kind == 'min') != bool(flip)   # 反向指标（平声比例）要翻向
    # 只摘掉**命中的那两次**（指标字面 + 极值词），其余原样保留
    keep = [True] * len(text)
    for a, b in ((hs, he), (ws, we)):
        for i in range(a, b):
            keep[i] = False
    _buf, _cut = [], False
    for i, ch in enumerate(text):
        if not keep[i]:
            if not _cut:
                _buf.append('，')
            _cut = True
        else:
            _buf.append(ch)
            _cut = False
    cleaned = ''.join(_buf)
    return {'metric': metric, 'col': col, 'label': label, 'kind': kind, 'word': word,
            'dir': 'asc' if asc else 'desc', 'cleaned': cleaned}


def order_pids(conn, spec, topk=None):
    """按用户点名的指标取篇（严格排序）。列名来自 ORDER_COLS 白名单，不用用户串。"""
    if not spec.order_by:
        return []
    col = spec.order_col or ORDER_COLS[spec.order_by][0]
    expr = order_expr(spec)
    where, args = _sql(spec)
    sql = ('SELECT p.pid, %s AS v FROM poems p WHERE %s ORDER BY %s %s, p.pid ASC'
           % (expr, where, expr, 'ASC' if spec.order_dir == 'asc' else 'DESC'))
    if topk:
        sql += ' LIMIT %d' % int(topk)
    return [(r[0], r[1]) for r in conn.execute(sql, args).fetchall()]


def extreme_info(conn, spec):
    """极值题的独立复核：条件内该指标的真值、并列篇数、检索范围。

    「引擎算出来就是答案」也要能被另一条路径复算——这里用一条**独立 SQL** 重算。
    """
    if not spec.order_by:
        return None
    col = spec.order_col or ORDER_COLS[spec.order_by][0]
    expr = order_expr(spec)
    where, args = _sql(spec)
    asc = spec.order_dir == 'asc'
    agg = 'MIN' if asc else 'MAX'
    sql1 = 'SELECT %s(%s) FROM poems p WHERE %s' % (agg, expr, where)
    v = conn.execute(sql1, args).fetchone()
    if not v or v[0] is None:
        return None
    val = v[0]
    # ⚠ 2026-10-03 晚（网页端「第四十题」实测驱动）：`order_expr` 对平声比例走的是**翻转列**
    #   （平声比例最低＝仄声比例最高）。复核行写「【平声比例】的最小值」时，值就必须是
    #   平声比例本身，不能把翻转列的极值直接当被测指标的值写出来——实测写着
    #   「平声比例的最小值 = 68.9」，68.9 是仄声比例（平声比例应为 31.1）。
    #   口径与真值（tools/gen_q1000._expr 的 `(100.0 - p.ze_ratio)`）同源；
    #   并列篇数仍按排序表达式（翻转列）取，与展示顺序一致。round(…,1)：既与库里
    #   ze_ratio 的一位小数口径一致，也避免 100.0-68.9=31.0999… 与文本里的 31.1 对不上。
    disp = round(100.0 - val, 1) if spec.order_by == 'ping_ratio' else val
    sql2 = ('SELECT p.pid, p.dynasty, p.author, p.cipai, p.title, %s FROM poems p '
            'WHERE %s AND %s = ? ORDER BY p.pid ASC' % (expr, where, expr))
    ties = conn.execute(sql2, list(args) + [val]).fetchall()
    dyn = {}
    for r in conn.execute('SELECT dynasty, COUNT(1) FROM poems GROUP BY dynasty'):
        dyn[r[0]] = r[1]
    scope = ('全库（' + '、'.join('%s %d 首' % (k, v2) for k, v2 in sorted(dyn.items())) + '）')
    if _vals(spec, 'dynasty') or _vals(spec, 'author') or _vals(spec, 'cipai') or spec.rng:
        scope = '满足条件的 %d 篇' % scope_count(conn, where, args)
    return {'value': disp, 'n_ties': len(ties), 'ties': ties, 'label': spec.order_label,
            'col': col, 'scope': scope, 'dir': spec.order_dir}


_SCOPE_PIDS_CACHE = {}


def scope_pids(conn, where, args):
    """范围内篇的 pid 列表（**连接级缓存**）。

    为什么加：同一份范围条件在一次问答里会被反复求值（取数、计数、排序、配对各一次），
    实测一次自检里 `SELECT p.pid FROM poems p WHERE <同一条件>` 出现 13 次、
    `SELECT COUNT(*) …` 7 次，合计 2.6 秒，全是同一条结果。
    失效信号用 `conn.total_changes`（任何写入都会 +1），比手工失效表可靠。
    """
    key = (conn, where, tuple(args), conn.total_changes)
    hit = _SCOPE_PIDS_CACHE.get(key)
    if hit is None:
        if len(_SCOPE_PIDS_CACHE) > 32:          # 上限保护：只留最近的范围
            _SCOPE_PIDS_CACHE.clear()
        hit = [r[0] for r in conn.execute('SELECT p.pid FROM poems p WHERE ' + where, args)]
        _SCOPE_PIDS_CACHE[key] = hit
    return hit


_SCOPE_COUNT_CACHE = {}


def scope_count(conn, where, args):
    """范围内篇数（**独立计数缓存**）。

    为什么不像原来那样 `len(scope_pids(...))`：那会把范围内**每一篇的 pid 都建成一个 Python 列表**
    ——全库条件就是 2.6 万个字符串对象。自检里 10 个不同条件各建一次，实测光这一步 2.4 秒，
    而调用方（排序信息、分页提示）要的只是一个数字。改为直接 `COUNT(1)`（走索引、只回一个整数）。
    """
    key = (conn, where, tuple(args), conn.total_changes)
    hit = _SCOPE_COUNT_CACHE.get(key)
    if hit is None:
        if len(_SCOPE_COUNT_CACHE) > 64:
            _SCOPE_COUNT_CACHE.clear()
        hit = conn.execute('SELECT COUNT(1) FROM poems p WHERE ' + where, args).fetchone()[0]
        _SCOPE_COUNT_CACHE[key] = hit
    return hit


_DB_ID_CACHE = {}
_NAMES_CACHE = {}
_NAMES_SORTED_CACHE = {}


def _names(conn, table, col, min_len=MIN_NAME_LEN):
    """词人/词牌名单（带**连接级缓存**）。

    为什么加缓存：`parse_query` 要为「最长名优先匹配」取全表名单，实测一次自检里
    `SELECT cipai FROM cipai` 被调 80 次、`SELECT author FROM authors` 76 次，合计 0.86 秒
    ——全是同一份静态数据。键用**连接对象本身**（可哈希且强引用，不会踩 id 复用坑），
    因此同一连接内只取一次；换连接（如重建库后）自然失效。
    """
    key = _db_identity(conn) + (table, col, min_len)
    hit = _NAMES_CACHE.get(key)
    if hit is not None:
        return hit
    try:
        # 长度过滤下推到 SQL：没必要把 1.4 万行全取回 Python 再筛
        out = [r[0] for r in conn.execute(
            'SELECT %s FROM %s WHERE LENGTH(%s) >= ?' % (col, table, col), (min_len,))]
    except sqlite3.Error:
        out = []
    _NAMES_CACHE[key] = out
    return out


def _db_identity(conn):
    """库的**进程内稳定身份**：文件路径 + 大小 + mtime（跨连接共享缓存用）。

    原来的缓存键含 connection 本身，于是「一个进程开了 13 个连接」就会把 1.4 万行的
    词牌表各取 13 遍（自检实测 183,859 行）。改用库文件身份后，同一份库只取一次；
    库被重建（大小/mtime 变）自然失效。
    """
    # 每个连接只解析一次（原来每次查名单都发一条 PRAGMA，自检里多出 134 条无谓语句）
    ck = id(conn)
    hit = _DB_ID_CACHE.get(ck)
    if hit is not None and hit[0] is conn:
        return hit[1]
    try:
        rows = conn.execute('PRAGMA database_list').fetchall()
        path = next((r[2] for r in rows if r[1] == 'main'), '') or ':memory:'
    except sqlite3.Error:
        _DB_ID_CACHE[ck] = (conn, ('?',))
        return ('?',)
    try:
        st = os.stat(path)
        ident = (path, st.st_size, int(st.st_mtime))
    except OSError:
        ident = (path,)
    _DB_ID_CACHE[ck] = (conn, ident)
    return ident


def _names_longest_first(conn, table, col, min_len=MIN_NAME_LEN):
    """按长度降序的名单（长名优先匹配用）；同样缓存，避免每次重新排序。"""
    key = _db_identity(conn) + (table, col, min_len)
    hit = _NAMES_SORTED_CACHE.get(key)
    if hit is None:
        hit = sorted(_names(conn, table, col, min_len), key=len, reverse=True)
        _NAMES_SORTED_CACHE[key] = hit
    return hit


def _vals(spec, attr):
    """多值字段的取值（单一来源）：优先 `<attr>_any` 列表，兼容直接赋单值。"""
    lst = getattr(spec, attr + '_any', None)
    if lst:
        return list(lst)
    v = getattr(spec, attr, None)
    return [v] if v else []


def _finalize(spec):
    """收尾：单值快捷字段由列表派生；连接词绝不留在词面条件里。"""
    for attr in ('dynasty', 'author', 'cipai', 'title', 'tail'):
        lst = _vals(spec, attr)
        setattr(spec, attr, lst[0] if len(lst) == 1 else None)
    # ⚠ 2026-10-04 修（代码审查 P1-7）：词面残片**去重 + 限长**——旧写法把未识别片段原样全收，
    #   超长/复读式问句会让【查询理解】行与检索打分一起膨胀（实测 51000 字输入 → 单行 12024 字）。
    _seen, _kw = set(), []
    for k in spec.keywords:
        if k in CONNECTORS or len(k) < 2 or k in _seen:
            continue
        _seen.add(k)
        _kw.append(k)
    spec.keywords = _kw[:12]
    return spec


def _alt_of(conn, piece):
    """把并列段（「…或者「声」」的后段）解成一个值：返回 (字段, 值) 或 (None, None)。

    用「能不能落地」来确定字段：词牌表里找不到就当词人试，都不是再看是不是单字/朝代/平仄串。
    """
    txt = piece.strip().strip('，,；;：:。.!！?？ ')
    if not txt:
        return None, None
    m = re.search(r'[「『"](.)[」』"]', txt)
    quoted = m.group(1) if m else None
    for c in _names_longest_first(conn, 'cipai', 'cipai'):
        if c in txt:
            return 'cipai', c
    for a in _names_longest_first(conn, 'authors', 'author'):
        if a in txt:
            return 'author', a
    # 引号里就是一个汉字（如【声】）：最硬的信据，先认它（别再被「清」这类朝代词干扰）
    if quoted and is_hanzi(quoted):
        return 'tail', quoted
    body = txt
    for w in list(STOPWORDS) + list(CONNECTORS) + list(DYN) + ['代', '朝']:
        body = body.replace(w, ' ')
    # ⭐ 剥「疑问尾巴/体裁尾巴」再数汉字（2026-10-01 深夜，答案解析实测驱动）：
    #   问「句脚是灯或者声的**清词**」时后段是「声的清词」——STOPWORDS 盖不住它，
    #   旧版数出「声」「的」「词」（'的'也是汉字！）3 个 → 落不了地 → **多值只剩一半**。
    #   只剥**结尾处**的虚词与体裁词，不影响中间内容（"声"仍在）。
    body = re.sub(r'(?:[啊呀呢吗么吧])*\s*$', ' ', body)
    #    注意 `的` 与体裁词之间可能有**空白**（朝代词「清」被上一步剥掉后留下空格：
    #    「声的清词」→「声的 词」），所以这里必须 `\s*` 容忍——否则剥不干净（实测踩过）。
    body = re.sub(r'的\s*(?:词|曲|诗|调)?\s*$', ' ', body)
    chars = [c for c in body if is_hanzi(c)]
    if len(chars) == 1:
        return 'tail', chars[0]
    for t in re.split(r'[\s，,；;：:。.!！?？]+', body):
        if t.strip() in DYN:
            return 'dynasty', t.strip()
    core = re.sub(r'[\s，,；;：:。.!！?？]+', '', txt)
    if PZ_RE.match(core) and len(core) >= 3:
        return 'pz', core
    return None, None


def _split_parse(conn, text):
    """并列/选择式问句：先解首段，再用后续段补齐**同一字段**的多值。

    保守原则：只有首段真解出了条件、且后续段至少有一段能落地，才启用多值解析；
    否则整句退回普通解析（不会因多切一刀而误伤）。解不出的段进 `unparsed`。
    """
    parts = [p for p in CONN_SPLIT_RE.split(text) if p.strip()]
    if len(parts) < 2:
        return None
    # 审查 B34：「和/与/及」可能是**词面本身**的一部分（「平和的词」「共和」），
    # 只有**每一段都能单独解析成条件**时才敢当并列连接词；否则整句退回普通解析（不误切）。
    if any(w in text for w in ('和', '与', '及')) and \
            not any(s in text for s in ('或者', '或是', '或', '以及', '还有', '、')):
        if not all(_alt_of(conn, p)[0] for p in parts):
            return None
    base = _parse_core(conn, parts[0])
    structured = bool(base.dynasty_any or base.author_any or base.cipai_any or base.tail_any
                      or base.tail_pz or base.scene or base.pz or base.rng)
    if not structured:
        return None
    alts, unparsed = [], []
    for p in parts[1:]:
        attr, val = _alt_of(conn, p)
        merged = False
        if attr is not None:
            if attr == 'dynasty' and base.dynasty_any and val not in base.dynasty_any:
                unparsed.append('%s（与首段朝代冲突，未并入同一条件）' % p.strip())
                continue
            if attr == 'tail' and val in base.tail_any:
                continue
            alts.append((attr, val))
            merged = True
        # 审查 B36：后段可能带着**首段没有的其它字段**（句脚/声情/声律模式）。
        # 旧版只补「同一字段的多值」，「清 临江仙 或者 念奴娇 里句脚是愁的」「高旭与纳兰性德
        # 的后段上升词」都会**静默丢掉**后半段的条件（条件丢了一半，答案却还是「像对的」）。
        # 现在后段一律再走一遍完整解析，只补首段没有的字段；仍落不了地的才进 unparsed。
        try:
            sp2 = _parse_core(conn, p)
        except Exception:                     # 解析器自身出错也不能把整句弄崩
            sp2 = None
        if sp2 is not None:
            for f in ('tail_any', 'tail_pz', 'scene', 'pz'):
                if getattr(sp2, f) and not getattr(base, f):
                    setattr(base, f, getattr(sp2, f))
                    merged = True
            if not base.dynasty_any and sp2.dynasty_any:
                base.dynasty_any = list(sp2.dynasty_any)
                merged = True
        if not merged:
            unparsed.append(p.strip())
    if not alts:
        return None
    return base, alts, unparsed


def _dyn_from_text(text):
    """从一句话里找朝代（词/代/朝后缀优先，独立 token 次之）。

    单一来源：单段解析与并列解析都用它。
    并列问句（「句脚是【灯】或者【声】的**清**词」）的朝代往往在后段，
    只看首段会把「清」丢了——实测踩过。
    """
    out = []
    # 后缀集含「曲/人」：研究者常写「元曲」「元人」「宋人」——实测「元曲中哪个词人的作品最多」
    # 曾因只认「代/朝/词」而丢掉朝代条件，答案变成全库统计（58852 篇）。
    # ⚠ 2026-10-03：`(?<!全部)` —— 占比题的模板短语「占**全部清词**（或所限朝代）」不是范围限定，
    #   不当成朝代（实测 Q0148：范围明明写的是「元，…」，引擎却因模板里的「清词」把朝代认成清，
    #   分子 371/清词 而不是 25/元词）。
    m = re.search(r'(?<!全部)(清|宋|元)(?:代|朝|词|曲|人)', text)
    if m:
        out.append(m.group(1))
    else:
        m = re.search(r'(?<![\u4e00-\u9fff\u3400-\u4dbf])(清|宋|元)(?![\u4e00-\u9fff\u3400-\u4dbf])', text)
        if m:
            out.append(m.group(1))
    return out


def _dyn_before_name(conn, text):
    """「元数据块连写」的朝代：`宋望江南・忆江南`、`在清梅花引` —— 朝代字后面**直接**跟着
    词牌/词人，没有任何分隔符，常见规则都认不出（实测 Q0120/Q0569：丢掉朝代 → 拿别的朝代的篇作答）。

    判据用**最长匹配**：若**从该朝代字起**本身就有一个词牌名（如「清平乐」是词牌），
    那它整个是词牌、不是「清 + 平乐」→ 不算朝代。否则再看后一字起是不是词牌/词人。
    """
    cip = _names(conn, 'cipai', 'cipai')
    aut = _names(conn, 'authors', 'author')
    hits = []
    for d in DYN:
        for mm in re.finditer(d, text or ''):
            i = mm.start()
            if any(text.startswith(c, i) for c in cip):
                continue                       # 从朝代字起就是词牌（清平乐…），不是朝代
            if any(text.startswith(c, i + 1) for c in cip) or \
               any(text.startswith(a, i + 1) for a in aut):
                if d not in hits:
                    hits.append(d)
    return hits


def _unsupported_from_text(text, conn=None):
    """语料外朝代（唐/汉……）：必须是独立 token，避免误伤「银汉」这类词句。

    ⚠ 2026-10-03：规则②（整句扫「朝代+体裁后缀」）必须再排掉**词牌名**——
    「金人捧露盘」里的「金人」会被当成「金代词人」→ 整题判成「语料外范围」而拒答
    （实测 Q0753：真值 28 篇，引擎答「共命中 0 篇」）。有 conn 时按词牌表核对。
    """
    for token in re.split(r'[\s，,、；;：:]+', text):
        t = token.strip()
        if not t:
            continue
        core = re.sub(r'(代|朝|词|诗|曲)$', '', t)
        if core in UNSUPPORTED_DYN and len(t) <= len(core) + 1:
            return t
    # ② 无分隔符整句里的「唐诗里最有名的五言绝句」这类写法：整句扫一遍「朝代+体裁后缀」。
    #    必须有后缀（诗/词/曲/人/代/朝）才算朝代名——这样「银汉」「金属」这类词句不会被误伤；
    #    带后缀的朝代名（唐诗/明词/元人）语义上是确定的（答案解析实测：旧版整句漏检 → 拿宋词充数）。
    m = re.search(r'(%s)(?:诗|词|曲|人|代|朝)' % '|'.join(
        sorted(UNSUPPORTED_DYN, key=len, reverse=True)), text)
    if m:
        if conn is not None:
            for c in _names(conn, 'cipai', 'cipai'):
                if len(c) > len(m.group(0)) and text.startswith(c, m.start()):
                    return None           # 是词牌名的一部分（金人捧露盘…），不是朝代限定
        return m.group(0)
    return None


def _drop_sub(vals):
    """去掉被更长名字包含的短名（「临江」是独立词牌名，但问句里的「临江」其实来自「临江仙」）。"""
    return [v for v in vals if not any(v != w and v in w for w in vals)]


def _dyn_all_from_text(text):
    """一句话里提到的**全部**语料内朝代（聚合题需要两个以上的组）。

    与 `_dyn_from_text`（只取第一个，供普通检索用）分开是有意的：
    普通题里「清」是**限定**，聚合题里「宋」「清」是**两个组**。
    判定要求「代词/代/朝/词后缀」或「独立 token」，避开「清平乐」「银汉」这类误伤。
    """
    # ⚠ 2026-10-03：**并列枚举**优先——「清与宋相比」「清／宋／元三者当中」里，
    #   第二个朝代后面跟的是「相」「三」（汉字），过不了下面的孤立判定 → 整组漏掉，
    #   聚合题退化成普通检索（实测 Q0062「清与宋相比，哪一组的平均篇幅更高」答成「未召回」）。
    hits = []
    for m in re.finditer(r'(?:清|宋|元)(?:\s*[／/、与和及,，]\s*(?:清|宋|元))+', text):
        for d in re.findall(r'清|宋|元', m.group(0)):
            if d not in [x for _s, x in hits]:
                hits.append((m.start(), d))
    for d in DYN:
        for m in re.finditer(r'(%s)(?:代|朝|词|曲|人)?' % d, text):
            s, e = m.start(), m.end()
            suf = m.group(1) != m.group(0)        # 「清词/清代/清朝」带了后缀
            lh = text[s - 1] if s > 0 else ''
            rh = text[e] if e < len(text) else ''
            # ⚠ 2026-10-03：右侧放宽到**列举/连接字**（三者/二/和/与）——
            #   「清／宋／元三者当中」的「元」后面紧跟「三」，旧规则判它不孤立 → 整组漏掉。
            #   但仍不允许任意汉字（否则「清平乐」的「清」会被当成朝代）。
            rh_ok = (not is_hanzi(rh)) or (rh in '三二两和与個个者')
            lone = (not is_hanzi(lh)) and rh_ok
            if suf or lone:
                if d not in [x for _s, x in hits]:
                    hits.append((s, d))
                break
    return [d for _s, d in sorted(hits)]


def _uns_dyn_in(text):
    """聚合题里出现的**语料外朝代**（「唐诗与清词哪个…」）。

    `_unsupported_from_text` 按分隔符切 token（普通检索够用），但「唐诗与清词哪个仄声占比高」
    整句是一个 token，切不出来——聚合题里必须单独认，否则会把「唐诗」当限定、
    拿清词数据回答一个跨语料的问题（**看着像答了，实际答的是另一个问题**）。
    """
    for u in UNSUPPORTED_DYN:
        m = re.search(re.escape(u) + r'(?:代|朝|词|诗|曲)?', text)
        if m and m.group(0) != u:
            return m.group(0)                 # 带后缀：确定是朝代名（唐诗/明代/汉赋…）
    return None


def parse_agg(conn, text):
    """分组对比统计的解析：返回 {'group_by','values','metric','text'} 或 None。

    只有「对比/统计」意图**且**能凑出同一维度的 ≥2 个组时才算聚合题；
    否则返回 None、走普通检索（宁可退化成普通检索，也不能把「宋词」这类限定
    误当成一组统计）。取值全部在库上校验：库里没收录的组保留（便于如实说「0 篇」）。
    """
    _ge0 = _group_extreme_of(text)
    if not AGG_HINT_RE.search(text) and not _ge0[0]:
        return None
    # ① 指标是**数值型**（仄声占比／篇幅／句数）；② 指标是**某一类别的篇数占比**
    #    （「后段下降的词作占比」）；③ 两者都没点明 → 记 `unspecified`。
    # ⚠️ 旧版 ③ 直接默认成「仄声占比」——主人本次实测：
    #    「高旭与纳兰性德的词作中谁的后段下降的词作占比更高」被答成「谁仄声占比更高」（答非所问），
    #    而「谁的词更好」也会因此拿到一个数值答案。**没点明就不替用户选指标。**
    metric, cat, mword = None, None, None
    for m, words in AGG_METRIC_PAT:
        for w in words:
            if w in text:
                metric, mword = m, w
                break
        if metric:
            break
    if metric is None:
        sc = next((s for s in SCENES if s in text), None)
        if sc and SHARE_HINT_RE.search(text):
            metric, cat, mword = 'share', ('scene', sc), sc
    cand = []                               # [(dimension, [values])]，优先朝代 → 词人 → 词牌
    uns = _uns_dyn_in(text)
    dyn = _dyn_all_from_text(text)
    if len(dyn) + (1 if uns else 0) >= 2:
        # 含语料外朝代（「唐诗与清词…」）：照样建聚合一题，由作答层**明说拒答**，
        # 而不是退化成「朝代=清 + 词面=唐诗…」把半边数据当答案（实测踩过）。
        cand.append(('dynasty', dyn or [d for d in DYN if d in text]))
    au = [a for a in _names(conn, 'authors', 'author') if a in text]
    au = _drop_sub(sorted(set(au), key=lambda x: text.index(x)))
    if len(au) >= 2:
        cand.append(('author', au))
    cp = [c for c in _names(conn, 'cipai', 'cipai') if c in text]
    cp = _drop_sub(sorted(set(cp), key=lambda x: text.index(x)))
    if len(cp) >= 2:
        cand.append(('cipai', cp))
    if not cand:
        # ⭐ 组内极值：「哪个词人/词牌/朝代…最多」——没有组名，但点明了**维度**。
        gb, ext = _ge0 if _ge0[0] else _group_extreme_of(text)
        if gb:
            if metric is None:
                metric = 'count'          # 「哪个词人的词最多」= 按篇数
            elif metric in ('han_len', 'sent_n'):
                pass                      # 「谁的篇幅最长」也说得通，照用
            return {'group_by': gb, 'values': None, 'metric': metric, 'cat': cat,
                    'metric_word': mword, 'text': text, 'extreme': ext,
                    'note': ''}
        return None
    dim, vals = cand[0]
    if metric is None:
        metric = 'unspecified'          # 有组可比、但问句没点明指标 → 由作答层如实拒答
    return {'group_by': dim, 'values': vals[:4], 'metric': metric, 'cat': cat,
            'metric_word': mword, 'text': text,
            'unsupported': uns,
            'note': ('' if len(vals) <= 4 else '问句里的组多于 4 个，本次只比较前 4 个')}



# ⚠ 2026-10-02 修：**算子识别**。引擎目前只实现「∃（存在）+ 并集」语义；
#   遇到 ∀／∄／≥k／=k／占比／条数区间／句位／交集／平仄串全等／中位数／众数／差值／条件概率
#   这类算子时，旧版**静默丢弃**并按剩余条件照常作答 → 静默答错（审计 1000 题里 639 条答非所问、
#   863 条守卫失职）。现在一律记进 `unparsed` 如实认账，并让守卫据此否决。
_OP_PATTERNS = (
    # ⚠ 2026-10-02：句级算子与**输出算子**均已实现 → 清单清空。
    #   保留这个机制：将来再出现"引擎表达不出来"的问法，在这里登记即可自动认账 + 守卫否决。
)
UNSUPPORTED_TAG = '本系统暂不支持'


def _flag_ops(spec, text):
    """把「引擎表达不出来的算子」如实记进 unparsed。"""
    for pat, name in _OP_PATTERNS:
        if pat.search(text or ''):
            msg = '%s：%s（已按其余条件作答，结论不覆盖该算子）' % (UNSUPPORTED_TAG, name)
            if msg not in spec.unparsed:
                spec.unparsed.append(msg)
    return spec


def _parse_query_inner(conn, text):
    """自然语言 → QuerySpec（规则路；也供大模型理解路复用同一套字段）。

    解析顺序（外部交付踩过的坑，我照单复核过并保留同样的防护）：
      先抽数值条件 → 再出声律模式/声情 → 再匹配词牌（最长）→ 再匹配词人（最长）
      → 判语料外朝代 → 最后才判朝代（避免「清平乐」的「清」被当成朝代）。
    并列式（「句脚是「灯」或者「声」」）走 `_split_parse` 先试，失败则退普通解析。
    """
    agg = parse_agg(conn, text)
    if agg is not None:
        # **keep_names=True**：聚合题里「临江仙」「元」这类是**真条件**（筛选），
        # 不能因为「整串无分隔符」被短语兜底退成词面——实测「哪个词人的临江仙最多」
        # 曾因此丢掉词牌条件、变成全库统计（58852 篇）。对比题的组名随后会被清空，无副作用。
        sp0 = _parse_core(conn, text, keep_names=True)
        sp0.agg = agg
        if agg.get('unsupported'):
            sp0.unsupported = agg['unsupported']   # 跨语料对比 → 拒答（不拿半边数据充数）
        if not agg.get('values'):
            # ⭐ **组内极值**（「哪个词人的词最多」）：这里除 group_by 那一维外，其它都是**真筛选条件**
            #    （「句脚为平 清 临江仙…」里的 清/临江仙/句脚平 必须照旧生效）。
            #    旧代码把筛选全清空——那是对**对比题**的正确处理（「宋／清」是组名），
            #    但对组内极值会把答案变成「全库统计」（实测：命中 58852 篇而不是 418 篇）。
            if agg['group_by'] == 'dynasty':
                sp0.dynasty_any, sp0.dynasty = [], None
            elif agg['group_by'] == 'author':
                sp0.author_any, sp0.author = [], None
            elif agg['group_by'] == 'cipai':
                sp0.cipai_any, sp0.cipai = [], None
            sp0.keywords = []           # 「哪个词人」这类提问词不当词面
            sp0.unparsed = []
            # 「最多」修饰的是**组**而不是篇 → 排序/极值字段清掉（由 agg 接管）
            sp0.order_by = sp0.order_col = sp0.order_dir = None
            sp0.extreme, sp0.order_label, sp0.order_src = None, None, None
            sp0.raw = text
            _finalize(sp0)
            return sp0
        # 对比题：「宋／清」这类**组名**不是检索限定，不能同时当条件（否则两义相混）。
        # ⚠ 2026-10-03 **重大修正**：旧版在这里把 `scene / tail_any / tail_pz / pz / rng` 一并清空，
        #   理由写的是「声情／数值阈值／句脚在聚合题里要么是被测量的类别，要么无意义」——
        #   但生成器造的是「**在<范围条件>的作品里**，甲与乙相比哪一组的<指标>更高」，
        #   范围条件（声情／句级算子／数值区间／句脚）全是**真筛选**！
        #   清空的后果是「拿两位词人的**全部**作品比」，答的是另一个问题；
        #   而**数字判据发现不了**——胜出组往往没变（实测 Q0004：真值 7722 篇、引擎 14429 篇，
        #   两边的"更高的组"却同为汪东，于是长期静默通过）。
        #   现在只清**分组维度本身**那一列，其余条件（含句级算子）一律保留。
        _cleared = []
        if agg['group_by'] == 'dynasty':
            _cleared = list(sp0.dynasty_any)
            sp0.dynasty_any, sp0.dynasty = [], None
        elif agg['group_by'] == 'author':
            _cleared = list(sp0.author_any)
            sp0.author_any, sp0.author = [], None
        elif agg['group_by'] == 'cipai':
            _cleared = list(sp0.cipai_any)
            sp0.cipai_any, sp0.cipai = [], None
        # 被清掉的组名仍要**参与「别把组名误当朝代」的判定**（如组名「宁调元」含「元」）
        sp0.cleared_names = _cleared
        # ⚠ **例外**：当指标是「某一类别的篇数占比」（share）时，那个类别词（如声情「后段下降」）
        #   是**被测量的对象**，不是筛选条件——「高旭与纳兰性德谁的后段下降的词作占比更高」若把
        #   声情当筛选，两边都只剩「后段下降」的篇 → 占比恒为 100.0% 且持平（实测自检项
        #   「类别占比的篇数与独立复算相符」因此失败）。
        if agg.get('metric') == 'share' and agg.get('cat') and agg['cat'][0] == 'scene':
            sp0.scene = None
        sp0.keywords = []
        sp0.unparsed = []
        sp0.order_by = sp0.order_col = sp0.order_dir = None
        sp0.extreme, sp0.order_label, sp0.order_src = None, None, None
        sp0.raw = text
        return sp0
    # 配对题（「找出几对每个位置上的字平仄都相同的两首词」）：**必须在极值/普通条件之前判**——
    # 它根本不是「筛篇」，而是「在篇与篇之间做配对」（旧版把它当普通条件题，大模型甚至从
    # 问句本身捏出一条「声律模式=平仄平仄平仄平仄」，拿最严条件去筛，答案完全离谱）。
    import pairing               # 延迟导入：pairing 要用本模块的 _sql（避开循环导入）
    pr = pairing.parse_pair(conn, text)
    if pr is not None:
        sp2 = _parse_core(conn, pairing.clean_text(text))
        sp2.pair = pr
        sp2.pair_label = '全篇逐位平仄完全相同' if 'tone' in pr['dims'] else '不支持的维度'
        sp2.keywords = []
        sp2.unparsed = []
        sp2.raw = text
        return _finalize(sp2)
    # 极值／排序题（「哪一首…最高/最低」）：先把指标与极值词从问句里摘下，
    # 再用同一套解析器解剩下的条件（词人/朝代/句脚…），最后把排序指标挂上去。
    ext = parse_extreme(conn, text)
    if ext is not None:
        sp1 = _parse_core(conn, ext['cleaned'], keep_names=True)
        if not sp1.dynasty_any:
            sp1.dynasty_any = _dyn_from_text(ext['cleaned'])
        uns1 = _unsupported_from_text(text, conn)
        if uns1:
            sp1.unsupported = uns1
        sp1.order_by, sp1.order_col = ext['metric'], ext['col']
        sp1.order_dir, sp1.extreme = ext['dir'], ext['kind']
        sp1.order_label, sp1.order_src = ext['label'], '规则'
        sp1.keywords = [k for k in sp1.keywords if k not in EXTREME_FRAME_WORDS]
        sp1.raw = text
        sp1.unparsed = [ext['word'] + '（已转为排序：%s）' % ext['label']]
        return _finalize(sp1)
    sp = _split_parse(conn, text)
    if sp is not None:
        base, alts, unparsed = sp
        for attr, val in alts:
            if attr == 'pz':
                if not base.pz:
                    base.pz = val
            else:
                getattr(base, attr + '_any').append(val)
        # 朝代/语料外朝代按**整句**再判一次（并列句里它们常在后段）
        if not base.dynasty_any:
            base.dynasty_any = _dyn_from_text(text)
        uns = _unsupported_from_text(text, conn)
        if uns:
            base.unsupported = uns
        base.unparsed = list(unparsed) + list(base.unparsed)
        base.raw = text
        return _finalize(base)
    return _parse_core(conn, text)


def _parse_core(conn, text, keep_names=False):
    """单段解析（原 `parse_query` 本体；多值由 `_split_parse` 在外层补齐）。

    `keep_names=True`：**不撤**「整串无分隔符 ⇒ 当正文片段」的兵险逻辑。
    极值题摘下指标词后剩下的就是「高旭写的那首词」（无分隔符），
    若不关掉这条逻辑，词人会静默消失、整句退化成词面条件（实测踩过）。
    """
    spec = QuerySpec()
    spec.raw = text
    rest = text
    _oob = []     # 越界的数值条件（字段名）：稍后并入 unparsed，**杜绝静默丢弃**

    def take(pat, key, cast=float, scale=None):
        """在 rest 中找数值条件并摘除；返回是否命中。数字支持阿拉伯与中文（五十/十五/两）。"""
        nonlocal rest
        m = re.search(pat, rest)
        if not m:
            return False
        if key in ('change_min', 'change_max') and '幅度' in m.group(0):
            spec.change_abs = True       # 「变化幅度」= 大小 → 后面 SQL 要取 ABS
        v = num_lit(m.group(1))
        if v is None:
            rest = rest.replace(m.group(0), ' ')
            return False
        lo, hi = RNG_BOUNDS.get(key, (None, None))          # 审查 C17：与大模型路同口径
        if lo is not None and not (lo <= v <= hi):
            # ⚠ **越界不许静默丢弃**（2026-10-02 收尾）。旧行为：把条件从 rest 里抹掉就完事，
            #   于是「字数超过一千的清词」→ 条件消失 → 退化成「不限字数」，照样一本正经地答
            #   「共命中 26742 篇」，而用户以为条件生效了。记账后并入 unparsed 如实披露。
            #   （只记**字段名**，稍后转成不含阿拉伯数字的文案，见函数末。）
            _oob.append(key)
            rest = rest.replace(m.group(0), ' ')
            return False
        spec.rng[key] = cast(v) * scale if scale else cast(v)
        rest = rest.replace(m.group(0), ' ')
        return True

    def take_range(pat, lo_key, hi_key):
        """区间口语（「五到八句」「句数在5到8之间」）：命中就同时写上下界并摘除。

        2026-10-01 深夜新增（答案解析实测：「句数在五到八之间的清词」规则路整条漏掉）。
        """
        nonlocal rest
        m = re.search(pat, rest)
        if not m:
            return False
        a, b = num_lit(m.group(1)), num_lit(m.group(2))
        lo, hi = RNG_BOUNDS.get(lo_key, (None, None))
        if a is None or b is None or a > b:
            rest = rest.replace(m.group(0), ' ')
            return False
        if lo is not None and not (lo <= a and b <= hi):
            _oob.append(lo_key)          # 越界与「上界小于下界」不同：前者要如实记账（同上）
            rest = rest.replace(m.group(0), ' ')
            return False
        spec.rng[lo_key], spec.rng[hi_key] = int(a), int(b)
        rest = rest.replace(m.group(0), ' ')
        return True

    # 数字字面量：阿拉伯或中文（「五十」「十五」「两」「一百」「两千三百」）；take/take_range 统一换算。
    # ⚠ **安全前瞻 `(?![亿萬])`**：万一出现范围外的更大单位（亿/萬），宁可**整条不匹配**
    #   （条件丢弃 → 会体现在 unparsed 里），也**绝不许**把「一亿」截成 1（2026-10-02 收尾修复）。
    NUM = r'(\d+(?:\.\d+)?|[零一二三四五六七八九十百千万两]+)(?![亿萬])'
    n_num = 0
    # ① 区间口语**先于**单值判（「五到八句」不能被别的模式吃掉）
    for pat, lo_key, hi_key in (
            (r'句数\s*(?:在)?\s*%s\s*(?:到|至|~|—|-)\s*%s\s*(?:之间|不等)?' % (NUM, NUM),
             'sent_min', 'sent_max'),
            (r'%s\s*(?:到|至|~|—|-)\s*%s\s*句' % (NUM, NUM), 'sent_min', 'sent_max'),
            (r'(?:字数|篇幅)\s*(?:在)?\s*%s\s*(?:到|至|~|—|-)\s*%s\s*(?:之间|不等)?' % (NUM, NUM),
             'len_min', 'len_max'),
            (r'%s\s*(?:到|至|~|—|-)\s*%s\s*字' % (NUM, NUM), 'len_min', 'len_max')):
        n_num += take_range(pat, lo_key, hi_key)
    # ② 「仄声（比例）超过一半／不到一半／过半」——口语高频，且**必须先于**单值模式：
    #    否则「超过一半」会被 `仄声比例 超过 NUM` 吃掉（NUM 只吃到「一」→ ze_min=1，静默错）。
    for pat, key in (
            (r'(?:仄声|仄字|仄)(?:比例|占比|字)?\s*(?:占)?\s*(?:超过|高于|大于|多于|达到|在)'
             r'\s*(?:一半|半数)(?:以上)?', 'ze_min'),
            (r'(?:仄声|仄字|仄)(?:比例|占比|字)?\s*(?:不到|少于|低于|不足|不及)\s*(?:一半|半数)',
             'ze_max'),
            (r'(?:仄声|仄字|仄)(?:比例|占比|字)?\s*占?过半', 'ze_min')):
        if key not in spec.rng:
            m = re.search(pat, rest)
            if m:
                spec.rng[key] = 50.0
                rest = rest.replace(m.group(0), ' ')
                n_num += 1
    # ③ 单值条件（阿拉伯或中文数字）
    for pat, key in ((r'仄声比例\s*%s\s*%s\s*%%?' % (UP, NUM), 'ze_min'),
                     (r'仄声比例\s*%s\s*%s\s*%%?' % (DOWN, NUM), 'ze_max')):
        n_num += take(pat, key, float)
    for pat, key in ((r'(?:字数|篇幅)\s*%s\s*%s' % (UP, NUM), 'len_min'),
                     (r'(?:字数|篇幅)\s*%s\s*%s' % (DOWN, NUM), 'len_max'),
                     (r'句数\s*%s\s*%s' % (UP, NUM), 'sent_min'),
                     (r'句数\s*%s\s*%s' % (DOWN, NUM), 'sent_max'),
                     # ⚠ 允许「变化**值**/**幅度**」——实测「前后段变化幅度不小于二十」因
                     #   中间夹了「幅度」而整条漏掉（范围从 1393 篇变成全库）。
                     (r'变化(?:值|幅度)?\s*%s\s*%s' % (UP, NUM), 'change_min'),
                     (r'变化(?:值|幅度)?\s*%s\s*%s' % (DOWN, NUM), 'change_max'),
                     (r'(?:阈值|长句阈值)\s*%s\s*%s' % (UP, NUM), 'thr_min'),
                     (r'(?:阈值|长句阈值)\s*%s\s*%s' % (DOWN, NUM), 'thr_max')):
        n_num += take(pat, key, int)

    # 声律模式：整串只由 平/仄/？ 组成且长度 ≥3 的 token（如「仄仄平平」）
    for tok in re.split(r'[\s，,、；;：:]+', rest):
        t = tok.strip().strip('？?')
        if t and PZ_RE.match(t):
            spec.pz = tok.strip()
            rest = rest.replace(tok, ' ')
            break

    # 声情转向
    for scene, words in SCENES.items():
        if scene in rest:
            spec.scene = scene
            rest = rest.replace(scene, ' ')
            break
        for w in words:
            if w in rest:
                spec.scene = scene
                rest = rest.replace(w, ' ')
                break
        if spec.scene:
            break

    # 句脚字 / 句脚平仄：「句脚=声」「句脚是「愁」」「句脚为平」「句末字=声」「句尾字是愁」
    # 坑（实测）：旧写法只允许 [=＝:：]，问「句脚是「愁」」会把「是」当句脚字 → 静默答错。
    # ⚠ 2026-10-03：「句末字**读**仄声」里的「读」也不在功能词表里 → 被当成**句脚字**「读」
    #   （引擎按 l.tail='读' 检索，命中 1 篇；真值按平仄检索，命中 3241 篇。实测 Q0234/Q0290）。
    #   把「读/属」并进可选功能词，后面捕获到的就是「仄/平」→ 走 tail_pz 分支。
    #   ⚠ 同时补 `(?:平仄)?`：「句脚**平仄**是仄」旧式会把「平」当成句脚字（实测 Q0744：
    #   真值 1330 篇，引擎因多出一条「句脚平仄=平」的**与**条件只剩 1288 篇）。
    m = re.search(r'句(?:脚|末字|尾字)\s*(?:字)?\s*(?:平仄)?\s*(?:[=＝:：]|是|为|作|等于|读|属)?\s*'
                  r'[「『\'"]?([%s])' % _HAN_CLASS, rest)
    if m:
        ch = m.group(1)
        if ch in '平仄':                     # 「句脚为平」：这是句脚的平仄，不是一个字
            spec.tail_pz = ch
        else:
            spec.tail_any.append(ch)
        rest = rest.replace(m.group(0), ' ')

    # 词牌（最长匹配优先）
    for c in _names_longest_first(conn, 'cipai', 'cipai'):
        if c in rest:
            spec.cipai_any.append(c)
            rest = rest.replace(c, ' ')
            break

    # ⚠ 2026-10-05 新增：**题名（词题）识别**——「词牌·题名」是词集里最规范的题名写法。
    #   由来（朋友实测驱动）：「蝶恋花·清明同诸子集原白斋中 的作者是谁」被旧版解析成
    #   「词牌=蝶恋花；词面=清明同诸子集原白斋中」——把**题名当成了词原文**，去 `raw` 里搜，
    #   而该串在正文里 0 命中 → 融合分堆出 1069 篇毫不相干的词，唯独正确答案（题名唯一命中
    #   的那 1 篇，清·陈维崧）没露面。官方口径同样把题名独立于正文（题库统一注明
    #   「不计标点、空白和**题名**」）。
    #   判据要**窄**，避免误伤正文里的间隔号（如《蝶恋花·「感春」次任公韵》是标题自带引号）：
    #     ① 词牌已被识别（spec.cipai_any 非空）；
    #     ② 文中存在「·」紧跟其后的**连续汉字串**（题名部分，允许中间有顿号/空格分隔的多段）；
    #     ③ 该串长度 ≥2 且不含疑问框架词（否则是「…的作者的词」这类残片）。
    if spec.cipai_any and not spec.title_any:
        # ⚠ 2026-10-06 修（外部审查 P2-14）：原先只认「·」（U+00B7）一种分隔符，而本文件
        #   其它位置（元数据块连写识别、official 的词牌切分）已经同时考虑「・」等变体——
        #   于是「蝶恋花・清明…」走不完全相同的解析路径。这里统一为**同一分隔符类**。
        m_t = re.search(r'[·・•]\s*([\u4e00-\u9fff\u3400-\u4dbf][\u4e00-\u9fff\u3400-\u4dbf\s、，,]{0,40}?)'
                        r'(?=[\s，,。？?！!、；;：:「」『』“”"]|$)', text)
        if m_t:
            cand = re.sub(r'[\s、，,]+', '', m_t.group(1))
            # ⚠ 2026-10-05 修：「的平仄」这类**框架残片**不能当题名。判据用**更宽的**框架词集
            #   （FRAME_WORDS ∪ 提问/指标虚词），否则「蝶恋花·的平仄」会把「的平仄」当题名 →
            #   「词牌=蝶恋花；题名=的平仄」0 命中（实测），而用户只是想问「蝶恋花的平仄」。
            _FRAME_ALL = tuple(FRAME_WORDS) + tuple(STOPWORDS) + tuple(_Q_FRAME)
            # ⚠ 2026-10-06 修（实测「蝶恋花·四月一日感粤事是谁的作品」答非所问）：
            #   中文问句里「题名」与「疑问框架」之间**常常没有空格**，而上面那条正则的右边界
            #   只认「标点／空白／结尾」→ 会把框架一起吞进来（实测捕获到「四月一日感粤事是谁的作品」），
            #   再被框架词检查**整条判负 → 题名丢失** → 只剩词牌条件 → 命中 1069 篇、端上融合
            #   排序前 3 篇（答非所问）。对照：带空格写法「…原白斋中 的作者是谁」因正则在空格处
            #   停下而正常识别——**同一个问题，写法不同结果不同**。
            #   修法：**切开**而不是整条丢——取「最靠左出现的框架词」的位置，从那里截断；
            #   仅当截断后仍 ≥2 字、且剩余不再含任何框架词时才认作题名（宁缺勿滥，保持原纪律）。
            if any(w in cand for w in _FRAME_ALL):
                _pos = min(cand.find(w) for w in _FRAME_ALL if w in cand)
                if _pos >= 2:
                    cand = cand[:_pos]
            if len(cand) >= 2 and not any(w in cand for w in _FRAME_ALL):
                spec.title_any.append(cand)
                rest = rest.replace(m_t.group(1).strip(), ' ')

    # 词人（最长匹配优先）
    for a in _names_longest_first(conn, 'authors', 'author'):
        if a in rest:
            spec.author_any.append(a)
            rest = rest.replace(a, ' ')
            break

    # ⚠ 2026-10-08 新增：**提取型意图**「第 N 句第 M 字」——问的是「在哪一篇里取哪个字」，
    #   不是筛选条件。旧版把它当**词面**送去全文检索（实测「第四句第三字」被当检索词 →
    #   答了句脚，完全答非所问）。这里识别出来记入 `spec.extract`，并把它从文本里**摘掉**
    #   （否则残留会污染 `keywords` 与 FTS 召回）。放在「短语兜底」之前，才不会先被当成词面收走。
    _m_ex = _EXTRACT_RE.search(rest)
    if _m_ex:
        _sn, _ps = cn_num(_m_ex.group(1)), cn_num(_m_ex.group(2))
        if _sn and _ps and 1 <= _sn <= 200 and 1 <= _ps <= 200:
            spec.extract = {'sent': int(_sn), 'pos': int(_ps), 'unit': 'char'}
            rest = rest.replace(_m_ex.group(0), ' ')

    # 短语兜底：整串汉字、无分隔符、名字匹配后仍有剩余 ⇒ 这是正文片段而非结构化查询
    # （「风紧玉楼斜」里恰好含词牌「玉楼」）。但已有数值/声律/声情/朝代等结构化线索时不撤销。
    has_sep = bool(re.search(r'[\s，,、；;：:·・•？?！!。.…「」『』“”\"]', text))
    structured = bool(n_num or spec.dynasty_any or spec.pz or spec.scene
                      or spec.tail_any or spec.tail_pz)
    leftover = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]{2,}', rest)
    if (not keep_names) and (not has_sep) and leftover and (spec.author_any or spec.cipai_any) \
            and not structured:
        spec.author_any = []
        spec.cipai_any = []
        rest = text

    # 语料外朝代（必须是独立 token，避免误伤「银汉」这类词句）
    uns = _unsupported_from_text(text, conn)
    if uns:
        spec.unsupported = uns

    # 朝代放最后（先整句取朝代，再把它从 rest 里摘掉，避免残留成词面）
    spec.dynasty_any += _dyn_from_text(rest)
    # ⚠ 2026-10-03：连写式元数据块（「宋望江南・忆江南」「在清梅花引」）——朝代字后直接跟
    #   词牌/词人，规则都认不出；用「最长匹配」再补一次（见 `_dyn_before_name`）。
    if not spec.dynasty_any:
        for _d in _dyn_before_name(conn, text):
            if _d not in spec.dynasty_any:
                spec.dynasty_any.append(_d)
    for pat in (r'(清|宋|元)(?:代|朝|词)',
                r'(?<![\u4e00-\u9fff\u3400-\u4dbf])(清|宋|元)(?![\u4e00-\u9fff\u3400-\u4dbf])'):
        m = re.search(pat, rest)
        if m:
            rest = rest.replace(m.group(0), ' ', 1)
            break

    # 剩余整串汉字作词面（保留整串，避免退化成短词匹配）；剔除提问虚词与连接词
    for w in list(STOPWORDS) + list(CONNECTORS):
        rest = rest.replace(w, ' ')
    # ⚠ 2026-10-02 修：词面**结构性过滤**——只靠 STOPWORDS 逐词剔除是打地鼠
    #   （剔掉「正好有」还剩「一句」、剔掉「中位数」还剩「仄是平的」）。
    #   规则：剩下的 2+ 汉字串里，只要**含**框架词/虚词，就不是「要检索的内容」，一律丢弃。
    _FRAME_SUB = tuple(FRAME_WORDS) + ('的', '是', '其', '之', '都', '也', '还', '再', '又')
    # ⚠ 2026-10-06 修（与 D21 同源：**「含框架词就整条丢」**这条判据在中文问句上过粗）：
    #   中文里「要检索的内容」与「疑问框架」之间**常常没有空格**，于是
    #   `'四月一日感粤事是谁的作品'` 因为含「作品」「是」被**整条丢弃** → 词面为空 →
    #   裸题名无法走 D09 已采纳的 `rescue_title()` 通道 → 无语义条件 → 答非所问（实测）。
    #   修法：不再整条丢，而是**从最靠左的框架词处截断**；仅当剩余 ≥2 字且不再含框架词时保留。
    _kws = []
    for _c in re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]{2,}', rest):
        if not _c.strip():
            continue
        _hit = [w for w in _FRAME_SUB if w in _c]
        if _hit:
            _pos = min(_c.find(w) for w in _hit)
            _c2 = _c[:_pos]
            if len(_c2) >= 2 and not any(w in _c2 for w in _FRAME_SUB):
                _kws.append(_c2)
            continue
        _kws.append(_c)
    spec.keywords = _kws

    # 越界的数值条件：**如实披露**（文案只用字段标签，**不含阿拉伯数字**——
    # 答案里每行数字都必须以证据为源，自带数字会撞护栏；标签由构造保证干净）。
    _LABEL = {'len': '字数', 'sent': '句数', 'ze': '仄声比例',
              'thr': '长句阈值', 'change': '变化幅度'}
    for _k in dict.fromkeys(_oob):
        _msg = '数值条件「%s」超出本系统支持范围，已忽略' % _LABEL.get(_k.split('_')[0], _k)
        if _msg not in spec.unparsed:
            spec.unparsed.append(_msg)
    return _finalize(spec)




# ================================================================ 句级算子（∀/∄/≥k/=k/占比/条数/句位/交集）
# 由来（2026-10-02，逐题答卷审查）：引擎原本只实现「∃ 存在」语义，遇到 ∀／∄／≥k／=k／占比／
# 条数区间／句位／交集 一律**静默丢弃**，于是答卷答的是另一个问题（639 条答非所问、863 条守卫失职）。
# 这里把六个量词与两个谓词补上——SQL 与真值口径 `gen_q1000.scope_where()` 同源，已互相验证。
_Q_SIMPLE = ((r'每一句都?|每句都?|所有句子都?', '∀'),
             (r'没有任何一句|没有任何句子|一句都不|一句也不|一句也没有', '∄'),
             # ⚠ ∃ 也要显式识别：像「至少有一句**偶数句位**上」这种组合，
             #   常规解析认不出「句位」这个谓词 → 条件整条丢失（范围被放大）。
             # ⚠ 2026-10-08（任务A）修：旧式第二段 `至少有[一..十]句` 把「至少有二句」
             #   **误判成 ∃**（＝存在一句），量词被丢、语义相反（C3 实测：真值「COUNT≥2」的题
             #   被答成「存在一句」）。现**删去**该段——「(至少)有 N 句」无论阿拉伯/中文一律
             #   交给下方**数值量词分支**按 ≥k 解析（见 `_Q_GE`；N==1 时记 ∃，与原本等价）。
             #   ⚠ 这里**只**保留「至少有一句」：「至少一句」（无「有」）不在此认，以免与
             #   交集短语「且另有至少一句句脚为「X」」抢跑（见 parse_line_ops 的 `_t_scan`）。
             #   例：「至少有两句句脚为愁」→ line_q={op:'≥k', k:2, pred:('tail','愁')}。
             (r'至少有一句', '∃'))
_Q_ATLEAST = re.compile(r'有([零一二三四五六七八九十百两0-9]+)句以上')
_Q_EXACT = re.compile(r'正好有([零一二三四五六七八九十百两0-9]+)句')
_Q_CNT_RANGE = re.compile(r'[的]?句子数在([零一二三四五六七八九十百两0-9]+)到'
                          r'([零一二三四五六七八九十百两0-9]+)句之间')
_Q_RATIO = re.compile(r'句子占比不低于([零一二三四五六七八九十百两0-9]+)%')
# ================================================================ 句级**数量量词**（任务A，2026-10-08）
# 由来（`tools/understand_eval.py` C3 实测）：「至少两句句脚为愁的清词」规则路**认不出量词**，
#   「至少两句」残留成词面（污染 FTS）、line_q 缺失 → 退化回 ∃（＝「句脚为愁」），命中 794 篇，
#   而真值应为 COUNT(tail=愁)>=2 的 33 篇。这里把常见中文数量量词补全（中文/阿拉伯数字皆可）。
# 映射（全部复用**既有**算子，SQL 口径与 `gen_q1000.scope_where` 一致，见 `line_ops_where`）：
#   ≥k          ：至少 N 句 / 至少 N 个句子 / 不少于 N 句 / N 句以上（无「有」）
#   =k          ：正好 N 句 / 恰好 N 句 / 刚好 N 句（含既有的「正好有 N 句」）
#   条数∈[a,b]  ：N 到 M 句之间（a=N,b=M）；不超过 N 句 / N 句以下（a=0,b=N，≤k 走既有 a<=0 分支）
_Q_NUM = r'[零一二三四五六七八九十百千万两0-9]+'
_Q_GE = re.compile(r'(?:至少|不少于|不小于|不低于)\s*(?:有\s*)?(%s)\s*(?:个)?句' % _Q_NUM)
_Q_GE2 = re.compile(r'(%s)\s*(?:个)?句以上' % _Q_NUM)          # 无「有」的「N 句以上」
_Q_EQ = re.compile(r'(?:正好|恰好|刚好)\s*(?:有\s*)?(%s)\s*(?:个)?句' % _Q_NUM)
_Q_LE = re.compile(r'(?:不超过|至多|不多于)\s*(?:有\s*)?(%s)\s*(?:个)?句' % _Q_NUM)
_Q_LE2 = re.compile(r'(%s)\s*(?:个)?句以下' % _Q_NUM)
_Q_RANGE2 = re.compile(r'(%s)\s*(?:到|至|~|—|-)\s*(%s)\s*(?:个)?句之间' % (_Q_NUM, _Q_NUM))


def _pred_of(frag):
    """从句级条件的片段里认出谓词 → (kind, val)。"""
    if not frag:
        return None
    # 先认**平仄**义：「句脚为仄」「句末字读仄声」「句脚平仄是仄」「句脚字属仄」都是平仄；
    # 而「句脚为「仄」」（带引号）才是**字面**的句脚字。（实测把「句脚为仄」当成了句脚字=仄 ✗）
    # ⚠ 2026-10-03 修：旧式末尾带 `(?![」\u4e00-\u9fff])`——「句脚为**平**的作品里」的「平」后跟
    #   「的」，前瞻失败 → 落到下一行的**字面**规则，把「平」当成**句脚字**（引擎按 l.tail='平'
    #   检索，命中 0；真值按平仄检索，命中数千）。实测 Q0043/Q0015 一批因此全错。
    #   现在：无引号的「句脚为平/仄」一律是**平仄**（生成器里字面句脚字必带「」）。
    #   末尾只在「平/仄」后紧跟另一个平/仄（如「句脚为平仄串…」）时才让位，避免吃掉「平仄」二字。
    m = re.search(r'句脚平仄(?:是|为)([平仄])|句末字读([平仄])声|句脚字属([平仄])'
                  r'|句脚为([平仄])(?![平仄])', frag)
    if m:
        return 'tail_pz', next(g for g in m.groups() if g)
    m = re.search(r'句脚(?:是|为)?「([\u4e00-\u9fff\u3400-\u4dbf])」'
                  r'|句脚(?:是|为)([\u4e00-\u9fff\u3400-\u4dbf])'
                  r'|句末字是([\u4e00-\u9fff\u3400-\u4dbf])'
                  r'|结尾字为([\u4e00-\u9fff\u3400-\u4dbf])'
                  r'|句脚字＝([\u4e00-\u9fff\u3400-\u4dbf])', frag)
    if m:
        return 'tail', next(g for g in m.groups() if g)
    # ⚠ 2026-10-08（任务B）：pz_exact 的措辞**从「规范式」扩展到口语式**——改前只认带引号的
    #   「整句平仄串正好是「X」」；改后同时认（有/无引号、有无「整句」前缀）：
    #     「整句平仄串正好是 X」「整句平仄正好是 X」「每句的平仄串完全等于 X」「平仄串恰好为 X」。
    #   **关键约束**：只认「正好/完全/恰好/刚好 + 是/等于/为」这一组词——绝不能吞掉子串语义的
    #   「平仄串为 X」（那是 `pz`，不是全等），否则会把「包含」误升成「全等」（范围被砍）。
    #   例：「每一句整句平仄串正好是仄仄平平仄」（无「都」、无「」）→ ('pz_exact','仄仄平平仄')。
    m = re.search(r'(?:整句)?平仄串?\s*(?:正好|完全|恰好|刚好)\s*(?:是|等于|为)\s*'
                  r'[「『]?([平仄?？]{3,})[」』]?', frag)
    if m:
        return 'pz_exact', m.group(1)          # 全等（与子串语义不同）
    m = re.search(r'声律模式是「([平仄?？]+)」|平仄串为([平仄?？]+)', frag)
    if m:
        return 'pz', next(g for g in m.groups() if g)
    m = re.search(r'句长在([零一二三四五六七八九十百两0-9]+)到'
                  r'([零一二三四五六七八九十百两0-9]+)字之间', frag)
    if m:
        return 'len', (cn_num(m.group(1)), cn_num(m.group(2)))
    m = re.search(r'([奇偶])数句位', frag)
    if m:
        return 'parity', (0 if m.group(1) == '奇' else 1)
    return None


# ⚠ 2026-10-08（任务A）：量词谓词的「同小句」片段提取。**必须按标点截断**，否则跨小句取会误抓：
#   篇级问句「…五到八句之间，至少有一句句脚为愁…」里，若从「五到八句之间」之后取 28 字，会越过
#   「，」抓到下一小句的「句脚为愁」，凭空给**篇级区间**造出一条句级条件（→ 双重约束/范围变窄）。
def _q_frag_after(t, pos, n=28):
    """量词**之后**同一小句的片段（到 ，。？；！ 或 n 字为止）。"""
    return re.split(r'[，。？；！,;!?]', (t or '')[pos:pos + n], 1)[0]


def _q_frag_before(t, pos, n=32):
    """量词**之前**同一小句的片段（谓词在前的量词用，如区间「N到M句之间」）。"""
    _seg = re.split(r'[，。？；！,;!?]', (t or '')[max(0, pos - n):pos])
    return _seg[-1] if _seg else ''


# 算子短语「挖空」：先把这些片段从文本里抹成空格，再交给**常规解析**。
# 否则常规数值解析会把「句子数在二到三句之间」也当成**篇的句数** → 双重约束、范围被砍小
# （实测 36 篇变 28 篇）。注意：**不能反过来一刀切撤掉篇级句数**——题目里可以同时有
# 「在五到七句之间」（篇级）与「句子数在二到四句之间」（句级），撤了会杀掉合法条件。
# 「第 N 句第 M 字」这类**提取型**问法（N/M 支持阿拉伯数字与中文数字）。
# 变体覆盖：「第四句第三字」「第 4 句第 3 个字」「第四句的第三个字」「末句首字」（末/首另见下）。
# ⚠ 只匹配「**第…句 第…字**」这种**双序号**形式——单说「第四句」（没有「第 M 字」）不是提取，
#   那是句级条件，绝不能在这里吃掉。
_EXTRACT_RE = re.compile(
    r'第\s*([0-9０-９]{1,3}|[一二三四五六七八九十两]{1,3})\s*句\s*的?\s*'
    r'第\s*([0-9０-９]{1,3}|[一二三四五六七八九十两]{1,3})\s*(?:个)?[字汉字]'
)

_MASK_RXS = (
    # ⚠ 顺序要紧：先挖**长而完整**的短语（含谓词），再挖短算子词，
    #   否则残留的谓词会被常规解析当成 ∃ 条件，与 ∄/∀ 等冲突（实测：∄下 ∧ ∃下 = 空集）。
    re.compile(r'满足「.+」的句子(?:数在[^，。？]{0,24}句之间|占比不低于[^，。？]{0,12}%)'),
    # ⚠ 2026-10-08（任务A/B）：∀/∄/∃ 的挖空**放宽到口语措辞**——「每一句」（无「都」）、「每句」
    #   （无「都」）、「一句也没有」也一并挖空（与 `_Q_SIMPLE` 的识别保持同一措辞集）；仍保留
    #   `[^，。？]{0,26}` 吃掉紧随谓词（避免残留谓词被常规解析当 ∃，与 ∄/∀ 打架）。
    re.compile(r'(?:每一句都?|每句都?|所有句子都?|没有任何一句|没有任何句子'
               r'|一句都不|一句也不|一句也没有|至少有一句)[^，。？]{0,26}'),
    _Q_EXACT, _Q_ATLEAST, _Q_CNT_RANGE, _Q_RATIO,
    # ⚠ 交集短语必须**早于**下面的 `_Q_GE` 挖空：否则 `_Q_GE` 会先把「至少一句」单独抹掉，
    #   致使本行的整条交集短语匹配失败、残留「句脚为「X」」进常规解析（多余 ∃，虽与 tail_each
    #   重复无害，但顺序上应保持与改前一致）。
    re.compile(r'且另有至少一句句脚为「[\u4e00-\u9fff\u3400-\u4dbf]」'),
    # ⚠ 2026-10-08（任务A）新增：中文数量量词的**量词短语**（只挖量词，谓词留给常规解析，
    #   与既有 `_Q_ATLEAST`/`_Q_EXACT`/`_Q_CNT_RANGE` 同法；句脚族谓词随后由 `_sql` 去重）。
    #   ⚠「N到M句之间」(`_Q_RANGE2`) **不在此处**——它与**篇级**句数区间同形（见 `_mask_ops`）。
    _Q_GE, _Q_GE2, _Q_EQ, _Q_LE, _Q_LE2,
    # 句长区间：它是**句级**谓词，不挖掉会被当成**篇级**字数（5~9 字）→ 与句级条件打架
    re.compile(r'句长在[零一二三四五六七八九十百两0-9]+到[零一二三四五六七八九十百两0-9]+字之间'),
    # ⚠ 2026-10-08（任务B）：pz_exact 的挖空同样放宽到口语式（无引号/无「整句」前缀），
    #   否则口语式会残留成词面（实测 C7：改前残留「串正好」→ 词面污染）。
    re.compile(r'(?:整句)?平仄串?\s*(?:正好|完全|恰好|刚好)\s*(?:是|等于|为)\s*'
               r'[「『]?[平仄?？]{3,}[」』]?'),
    re.compile(r'[奇偶]数句位'),
)


def _mask_ops(text):
    t = text or ''
    for rx in _MASK_RXS:
        t = rx.sub(lambda m: ' ' * len(m.group(0)), t)
    # ⚠ 2026-10-08（任务A）：「N到M句之间」是**篇级/句级同形**短语（题库把**篇级**句数区间也写成
    #   「五到八句之间」，见 gen_q1000.py:206）——**不能无条件挖空**，否则篇级 `sent_min/sent_max`
    #   整条丢失（范围变宽 → 一批假 E_SCOPE）。故**条件挖空**：只有当同一小句里**紧邻其前**存在
    #   句级谓词（「…的句子N到M句之间」）时才按句级挖掉；否则原样留给常规数值解析当**篇级句数**。
    def _range_if_line(m, _t=t):
        return (' ' * len(m.group(0))
                if _pred_of(_q_frag_before(_t, m.start())) else m.group(0))
    t = _Q_RANGE2.sub(_range_if_line, t)
    return t


def parse_line_ops(text, spec):
    """把句级算子解析进 spec（∀/∄/≥k/=k/占比/条数/句位/交集/平仄串全等）。"""
    t = text or ''
    # ⚠ 2026-10-03：**并集**——「句脚是「X」或句脚为「Y」」里的第二个取值，
    #   旧版完全没解析 → 只留第一个取值（实测真值 180、引擎 206）。
    _or = []
    for m in re.finditer(r'(?:或者?|、)\s*句脚为「([\u4e00-\u9fff\u3400-\u4dbf])」', t):
        if m.group(1) not in _or:
            _or.append(m.group(1))
    # 交集：且另有至少一句句脚为「X」
    for m in re.finditer(r'且另有至少一句句脚为「([\u4e00-\u9fff\u3400-\u4dbf])」', t):
        if m.group(1) not in spec.tail_each:
            spec.tail_each.append(m.group(1))
    # ⚠ 2026-10-08（任务A）：**量词扫描前，先把交集短语抹掉**（`_t_scan`，与 `t` 等长、位置对齐）。
    #   交集短语「且另有至少一句句脚为「X」」里的「至少一句」是**交集表达**，不是主量词。若让量词
    #   扫描看到它，会把真正的主量词**覆盖**掉：`_Q_SIMPLE`∃/`_Q_GE` 会先命中它并置 line_q=∃，
    #   使随后「占比不低于N%」「句子数在N到M句之间」等分支被跳过（实测 Q 类：占比+交集题会被
    #   静默降级成 ∃）。抹掉后量词扫描只看真正的主量词；tail_each 已在上面单独记好。
    _t_scan = t
    for _m in re.finditer(r'且另有至少一句句脚为「[\u4e00-\u9fff\u3400-\u4dbf]」', t):
        _t_scan = _t_scan[:_m.start()] + ' ' * (_m.end() - _m.start()) + _t_scan[_m.end():]
    # 平仄串全等
    # ⚠ 2026-10-08（任务B）：同 `_pred_of`，措辞放宽到口语式（无引号/无「整句」前缀）。**无量化词**时
    #   由此直接落成 ∃ 全等（`spec.pz_exact`）；**有** ∀/∄/数量词时由上面的量词分支落成 `line_q`，
    #   二者若同时命中，`_sql` 第 1604 行会去重，不会叠加成自相矛盾（∃ 全等 ∧ ∄ 全等 = 空集）。
    m = re.search(r'(?:整句)?平仄串?\s*(?:正好|完全|恰好|刚好)\s*(?:是|等于|为)\s*'
                  r'[「『]?([平仄?？]{3,})[」』]?', t)
    if m:
        spec.pz_exact = m.group(1)
        spec.pz = None                      # 全等与子串互斥
    # 量词 + 谓词（在 `_t_scan` 上搜——已抹掉交集短语；谓词仍从原 `t` 取，位置对齐）
    for pat, op in _Q_SIMPLE:
        m = re.search(r'(?:%s)(?P<frag>[^，。？]{0,28})' % pat, _t_scan)
        if m:
            pr = _pred_of(m.group('frag'))
            if pr:
                spec.line_q = {'op': op, 'pred': pr}
                break                      # ⚠ 只有**成功取到谓词**才 break；
            #   否则继续试下一个模式——旧版一律 break，导致「没有任何一句整句平仄串正好是X」
            #   量词匹配上、谓词取不到 → **∄ 被静默丢掉**（实测引擎 0，真值 15）。
    if spec.line_q is None:
        for rx, op, key in ((_Q_EXACT, '=k', 'k'), (_Q_ATLEAST, '≥k', 'k')):
            m = rx.search(t)
            if m:
                after = t[m.end():m.end() + 28]
                pr = _pred_of(after)
                if pr:
                    spec.line_q = {'op': op, 'pred': pr, key: int(cn_num(m.group(1)) or 0)}
                break
    if spec.line_q is None:
        m = _Q_CNT_RANGE.search(t)
        if m:
            pr = _pred_of(t[max(0, m.start() - 30):m.start()])   # ⚠ 必须 max(0,…)：否则负索引切片是空串
            if pr:
                spec.line_q = {'op': '条数∈[a,b]', 'pred': pr,
                               'ka': int(cn_num(m.group(1)) or 0),
                               'kb': int(cn_num(m.group(2)) or 0)}

    # ⚠ 2026-10-08（任务A）：**中文数量量词**（至少N句／(至少)有N句以上／正好N句／不超过N句／
    #   N句以下／N到M句之间）。谓词取量词**同一小句**内的片段（谓词在后取后、区间取前）——
    #   跨小句取会误抓（见 `_q_frag_after` 注释：篇级「五到八句之间，至少有一句句脚为愁」）。
    #   这些分支只在「前面 5 类都未认出量词」时启用（`line_q is None`），且**不改动**既有
    #   「有N句以上」「正好有N句」「句子数在N到M句之间」的 SQL 口径（它们更早匹配、结果逐字不变）。
    if spec.line_q is None:                      # 区间：N 到 M 句之间 → 条数∈[N,M]（谓词在前）
        m = _Q_RANGE2.search(_t_scan)
        if m:
            pr = _pred_of(_q_frag_before(t, m.start()))
            if pr:
                spec.line_q = {'op': '条数∈[a,b]', 'pred': pr,
                               'ka': int(cn_num(m.group(1)) or 0),
                               'kb': int(cn_num(m.group(2)) or 0)}
    if spec.line_q is None:                      # ≥k：至少 N 句 / N 句以上
        for rx in (_Q_GE, _Q_GE2):
            m = rx.search(_t_scan)
            if not m:
                continue
            pr = _pred_of(_q_frag_after(t, m.end()))
            if pr:
                _k = int(cn_num(m.group(1)) or 0)
                # k<=1（「至少一句」）与 ∃ 语义等价；为**不改**既有「至少有一句」的表述，记 ∃。
                spec.line_q = ({'op': '≥k', 'pred': pr, 'k': _k} if _k >= 2
                               else {'op': '∃', 'pred': pr})
                break
    if spec.line_q is None:                      # =k：正好 / 恰好 / 刚好 N 句
        m = _Q_EQ.search(_t_scan)
        if m:
            pr = _pred_of(_q_frag_after(t, m.end()))
            if pr:
                spec.line_q = {'op': '=k', 'pred': pr, 'k': int(cn_num(m.group(1)) or 0)}
    if spec.line_q is None:                      # ≤k：不超过 N 句 / N 句以下 → 条数∈[0,k]
        m = _Q_LE.search(_t_scan) or _Q_LE2.search(_t_scan)
        if m:
            pr = _pred_of(_q_frag_after(t, m.end()))
            if pr:
                # 复用「条数∈[a,b]」（a==0 走 `line_ops_where` 的 a<=0 分支，缺陷2 已实现）
                spec.line_q = {'op': '条数∈[a,b]', 'pred': pr, 'ka': 0,
                               'kb': int(cn_num(m.group(1)) or 0)}

    # 一致性：声情标注为 X 但实测前后段相反（声情×派生量 的矛盾面）
    m = re.search(r'声情标注为(后段上升|后段下降|前后持平)但实测前后段相反', t)
    if m:
        spec.consist = m.group(1)
        spec.scene = m.group(1)
        spec.raw_consist = True

    if spec.line_q is None:
        m = _Q_RATIO.search(t)
        if m:
            pr = _pred_of(t[max(0, m.start() - 40):m.start()])
            if pr:
                spec.line_q = {'op': '占比≥p', 'pred': pr,
                               'ratio': (cn_num(m.group(1)) or 0) / 100.0}
    # 并集：把「或句脚为「Y」」并进已有的句脚字谓词（多值 IN 语义）
    if _or and spec.line_q and spec.line_q['pred'][0] == 'tail':
        vals = [spec.line_q['pred'][1]] + [x for x in _or if x != spec.line_q['pred'][1]]
        spec.line_q['pred'] = ('tail_any', vals)
    return spec


def _pred_sql(kind, val):
    """句级谓词 → (SQL, args)。"""
    if kind == 'tail':
        return 'l.tail = ?', [val]
    if kind == 'tail_any':
        return 'l.tail IN (%s)' % ','.join('?' * len(val)), list(val)
    if kind == 'tail_pz':
        return 'substr(l.pz, -1, 1) = ?', [val]
    if kind == 'pz':
        return 'l.pz LIKE ?', ['%' + val.replace('?', '_').replace('？', '_') + '%']
    if kind == 'pz_exact':
        return 'l.pz = ?', [val]
    if kind == 'len':
        return '(l.han_len >= ? AND l.han_len <= ?)', [val[0], val[1]]
    if kind == 'parity':
        return '(l.idx % 2) = ?', [val]
    raise ValueError(kind)


def _line_q_where(lq):
    """**单个**句级算子（`spec.line_q` / Plan 的 `line_q` 叶子）→ (WHERE 片段列表, args)。

    抽成独立函数是**单一来源**（外部架构审查要求「不要重复实现两套」）：
    `line_ops_where()`（经典字段路径）与 `_sql_filters()`（布尔树路径）都调用它，
    从而两条路径对该算子编译出**逐字相同**的 SQL。空 `lq` → 返回 ([], [])。
    """
    w, a = [], []
    if lq:
        expr, ar = _pred_sql(*lq['pred'])
        op = lq['op']
        if op == '∃':
            # ⚠ 漏了这个分支：∃ 的谓词被"挖空"后常规解析看不见，line_ops 又不发条件
            #   → WHERE 退化成 1=1（实测「至少有一句句脚为「残」」命中全库 58852）。
            w.append('p.pid IN (SELECT l.pid FROM lines l WHERE %s)' % expr)
            a += ar
        elif op == '∀':       # 没有任何一句**不**满足 → 篇内每一句都满足
            _k, _v = lq['pred']
            # ⚠ 2026-10-03：**必须支持 tail_any**（并集谓词）。旧版这里是一张写死的字典，
            #   没有 'tail_any' 键 → 「每一句都句脚为「酒」或句脚为「枝」」直接 KeyError 崩掉
            #   （实测 Q0391/Q0741/Q0770/Q0790 四条 E_CRASH）。
            if _k == 'tail_any':
                neg = '(l.tail IS NULL OR l.tail NOT IN (%s))' % ','.join('?' * len(_v))
            else:
                neg = {'tail': '(l.tail IS NULL OR l.tail <> ?)',
                       'tail_pz': '(l.pz IS NULL OR substr(l.pz, -1, 1) <> ?)',
                       'pz': '(l.pz IS NULL OR l.pz NOT LIKE ?)',
                       'pz_exact': '(l.pz IS NULL OR l.pz <> ?)',
                       'len': '(l.han_len IS NULL OR l.han_len < ? OR l.han_len > ?)',
                       'parity': '(l.idx IS NULL OR (l.idx % 2) <> ?)'}[_k]
            nar = _pred_sql(_k, _v)[1]
            w.append('p.pid NOT IN (SELECT l.pid FROM lines l WHERE %s)' % neg)
            a += nar
            # ⚠ 2026-10-08（缺陷1）：这一句 = 「至少有一句」，即把**空篇（0 句）排除在 ∀ 之外**。
            #   口径已与两条独立来源核对一致，故**刻意保留**（而不是删掉）：
            #     ① 真值口径 `tools/gen_q1000.py:scope_where` 的 ∀ 分支（第 262 行）有**同一句**
            #        `w.append('p.pid IN (SELECT pid FROM lines)')`——真值同样把空篇排除；
            #     ② 检索 SQL（本函数）与真值由此逐题相等（verify_1000 ① 条件理解一致性）。
            #   而 `ask.py:1615-1621` 的「平凡满足」注释：其计数声明是「与真值口径一致」，
            #   触发场景实为 **∄**（该注释举的 Q0008 就是 `∄｜句位奇偶`），并非 ∀。
            #   改前行为：SQL 排除空篇（对），但 Python 复核 `n == tot`（0==0）判空篇**满足**（错）→ 两路打架。
            #   改后行为：两路统一为「∀ 要求篇内至少一句且每句都满足」，空篇不计。
            #   全库空篇 = `SELECT COUNT(*) FROM poems WHERE sent_n=0` = 144（元曲残片，且 lines 表无行）。
            w.append('p.pid IN (SELECT l.pid FROM lines l)')
        elif op == '∄':
            w.append('p.pid NOT IN (SELECT l.pid FROM lines l WHERE %s)' % expr)
            a += ar
        elif op in ('≥k', '=k'):
            # ⚠ 2026-10-08（缺陷2）：`GROUP BY l.pid HAVING COUNT(*) …` 只可能产出「至少有一句进入
            #   GROUP BY」的篇 → 当 k==0 时**漏掉全部「0 命中」篇**（含 144 个空篇）。
            #   改前行为：`=0` 返回空集（真值是「所有不含该谓词的篇」）；`≥0` 只返回命中≥1句的篇。
            #   改后行为：`=0` → 补集 `NOT IN (…WHERE expr)`；`≥0` → 恒真（不加此条件）。
            #   保持 `≥1/=k(k≥1)` 的 SQL **逐字不变**（常见情形结果不变）。
            _k = lq['k']
            if op == '=k' and _k == 0:
                w.append('p.pid NOT IN (SELECT l.pid FROM lines l WHERE %s)' % expr)
                a += ar
            elif op == '≥k' and _k == 0:
                pass                                   # ≥0 恒真：不加任何条件
            else:
                cmp_ = '>=' if op == '≥k' else '='
                w.append('p.pid IN (SELECT l.pid FROM lines l WHERE %s GROUP BY l.pid '
                         'HAVING COUNT(*) %s ?)' % (expr, cmp_))
                a += ar + [_k]
        elif op == '占比≥p':
            w.append('p.pid IN (SELECT l.pid FROM lines l GROUP BY l.pid HAVING '
                     'SUM(CASE WHEN %s THEN 1 ELSE 0 END) * 1.0 / COUNT(*) >= ?)' % expr)
            a += ar + [lq['ratio']]
        elif op == '条数∈[a,b]':
            # ⚠ 2026-10-08（缺陷2）：同 `=k`——`BETWEEN a AND b` 也只在「有句进 GROUP BY」的篇里取，
            #   a==0 时漏掉「0 命中」篇。改后行为：a<=0 时拆成 `(NOT EXISTS OR COUNT<=b)`（0 命中 ∪ 1..b）。
            #   保持 a>=1 的 SQL 逐字不变。
            _ka, _kb = lq['ka'], lq['kb']
            if _ka <= 0:
                w.append('(p.pid NOT IN (SELECT l.pid FROM lines l WHERE %s) OR '
                         'p.pid IN (SELECT l.pid FROM lines l WHERE %s GROUP BY l.pid '
                         'HAVING COUNT(*) <= ?))' % (expr, expr))
                a += ar + ar + [_kb]
            else:
                w.append('p.pid IN (SELECT l.pid FROM lines l WHERE %s GROUP BY l.pid '
                         'HAVING COUNT(*) BETWEEN ? AND ?)' % expr)
                a += ar + [_ka, _kb]
    return w, a


def line_ops_where(spec):
    """QuerySpec 的句级条件 → (WHERE 片段列表, args)。

    由三部分组成（与经典 `_sql` 逐字对应）：
      ① 单个句级算子 `spec.line_q`   → `_line_q_where()`（单一来源）
      ② 篇内交集 `spec.tail_each`    → 每个取值各加一条「存在一句句脚=该值」
      ③ 平仄串全等 `spec.pz_exact`   → 存在一句 `l.pz = 该串`（若已被句级算子接管则不重复加）
    """
    w, a = _line_q_where(spec.line_q)
    for t in spec.tail_each:        # 交集：每个取值都必须有**一句**
        w.append('p.pid IN (SELECT l.pid FROM lines l WHERE l.tail = ?)')
        a.append(t)
    # ⚠ 2026-10-03：若这个谓词**已经**由句级算子接管（如「没有任何一句平仄串为X」），
    #   就绝不能再额外加一个同名的 ∃ 条件——∄X ∧ ∃X = 空集（实测引擎答 0，真值 15）。
    _lqp = (spec.line_q or {}).get('pred') if spec.line_q else None
    if spec.pz_exact and not (_lqp and _lqp[0] in ('pz', 'pz_exact')
                              and _lqp[1] == spec.pz_exact):
        w.append('p.pid IN (SELECT l.pid FROM lines l WHERE l.pz = ?)')
        a.append(spec.pz_exact)
    return w, a


# ================================================================ 条件 → SQL：**可复用叶子编译**
# 外部架构审查要求：「把 `_sql()` 对每个字段的编译逻辑抽成可复用函数再递归调用，不要重复实现两套」。
# 下列 `_leaf_*` 是**单一来源**：经典字段路径（`_sql`）与布尔树路径（`_sql_filters`）都调用它们，
# 从而对同一条件保证**逐字相同**的 SQL 片段 —— 这是「零回归」与「布尔树可信」的共同前提。
def _leaf_one(col, vals):
    """等值 / IN —— 元数据字段（朝代/词人/词牌）。空列表 → None（空 IN () 是语法错）。"""
    if not vals:
        return None
    if len(vals) == 1:
        return '%s = ?' % col, [vals[0]]
    return '%s IN (%s)' % (col, ','.join('?' * len(vals))), list(vals)


def _leaf_exists_lines(expr, vals):
    """句级条件：`p.pid IN (SELECT l.pid FROM lines l WHERE <expr> IN (...))`（存在一句即命中）。

    用 IN 子查询而不是逐篇 EXISTS：让 SQLite 从 lines 侧一次取出命中的 pid 集合，再走 poems
    主键索引收窄（实测句脚=愁 2,948 ms → 65 ms）。语义等价：EXISTS(某句满足) ≡ pid∈{满足的 pid}。
    """
    return ('p.pid IN (SELECT l.pid FROM lines l WHERE %s IN (%s))'
            % (expr, ','.join('?' * len(vals)))), list(vals)


def _leaf_title(vals):
    """题名子串并集（`p.title LIKE %题名%`，多项 OR）；空 → None。"""
    if not vals:
        return None
    return ('(' + ' OR '.join('p.title LIKE ?' for _ in vals) + ')',
            ['%' + t + '%' for t in vals])


def _leaf_pid(vals):
    """pid 集合（上一轮结果集/显式 pid 范围）。空 → None。"""
    if not vals:
        return None
    return 'p.pid IN (%s)' % ','.join('?' * len(vals)), list(vals)


def _leaf_num(col, op, v):
    """数值比较（`col op ?`）。`col` 可为普通列或表达式（如 `ABS(p.change)`）。"""
    return '%s %s ?' % (col, op), [v]


def _leaf_pz(v):
    """声律模式（平仄串子串）；`?`/`？` 通配 → SQL `_`。"""
    pat = v.replace('?', '_').replace('？', '_')
    # IN 子查询代替逐篇 EXISTS（实测 1,600+ ms → 800 ms；pz 是 LIKE 通配、主体不可索引）。
    return 'p.pid IN (SELECT l.pid FROM lines l WHERE l.pz LIKE ?)', ['%' + pat + '%']


def _leaf_tail_pz(v):
    """句脚平仄 = 该句平仄串最后一个字（单一来源：pz 串由引擎生成）。"""
    return 'p.pid IN (SELECT l.pid FROM lines l WHERE substr(l.pz, -1, 1) = ?)', [v]


def _leaf_pz_exact(v):
    """平仄串**全等**（非子串）。"""
    return 'p.pid IN (SELECT l.pid FROM lines l WHERE l.pz = ?)', [v]


def _leaf_tail_each(vals):
    """篇内交集：**每一个**取值都必须各自出现在某一句（多值 AND）。空 → None。"""
    if not vals:
        return None
    frags = ['p.pid IN (SELECT l.pid FROM lines l WHERE l.tail = ?)' for _ in vals]
    return '(' + ' AND '.join(frags) + ')', list(vals)


def _leaf_lines_text(v):
    """句级「文字包含」：`text LIKE %X%`（存在句级子串）。

    取舍（LIKE 子查询 vs FTS）：
      · `lines_fts` 是 FTS5 短语索引，按**分词/短语**匹配，对「月」这类单字查询可能因分词粒度
        而不等价于「正文含该字」；而本题型要的正是**精确子串存在性**（官方口径「不计标点、空白」）。
      · LIKE 子查询语义**直白、确定、可独立复算**（临时验证脚本用同一口径 `text LIKE ?` 复算）。
      故此处取 LIKE；若未来改走 FTS，必须同步更新 `_leaf_lines_text` 与真值复算两端。
    """
    return 'p.pid IN (SELECT l.pid FROM lines l WHERE l.text LIKE ?)', ['%' + v + '%']


def _leaf_consist(v):
    """一致性：声情标注与实测派生量**矛盾**的那一面。"""
    if v == '后段上升':
        return 'p.change < 0', []
    if v == '后段下降':
        return 'p.change > 0', []
    return 'ABS(p.change) < 1', []


# 数值条件字段 → SQL 列/表达式（Plan 叶子用列名；`abs_change` = `ABS(p.change)`）
_NUM_COL = {'ze_ratio': 'p.ze_ratio', 'han_len': 'p.han_len', 'sent_n': 'p.sent_n',
            'threshold': 'p.threshold', 'change': 'p.change', 'abs_change': 'ABS(p.change)'}


def _sql(spec):
    """硬条件的 SQL 片段与参数（元数据 + 数值 + 声情 + 句脚 + 声律模式）。

    多值字段（并列/选择）用 `IN (...)` 取**并集**：「句脚是【灯】或者【声】」＝灯的 ∪ 声的。

    ⚠ 2026-10-08（外部架构审查核心条目）：**布尔过滤树优先**。
       `spec.filters_tree` 为 None（**默认**）→ 走下方经典「逐字段」路径，**逐字节不变**；
       非 None → 整段交给 `_sql_filters()` 递归编译（布尔路径），经典字段路径**不再执行**。
       这条「默认走原路径」是**零回归的生命线**：规则路永不填 `filters_tree`。
    """
    if getattr(spec, 'filters_tree', None) is not None:
        where_sql, args = _sql_filters(None, spec.filters_tree)
        assert where_sql.count('?') == len(args), \
            'filters_tree 参数不平行（少写 args.extend 会整段错位，审查 C7）'
        return where_sql, args

    where, args = [], []

    def add(frag):
        if frag is None:
            return
        sql, a = frag
        if sql:
            where.append(sql)
            args.extend(a)

    for attr, col in (('dynasty', 'p.dynasty'), ('author', 'p.author'), ('cipai', 'p.cipai')):
        add(_leaf_one(col, _vals(spec, attr)))
    # ⚠ 2026-10-08 新增（任务C）：**上一轮结果集**范围（会话指代「那里面…」→ 前端传 pid 集合）。
    #   改前 → 无此分支（前端传的上一轮 pid 无处落地）；改后 → 编译成硬条件 `p.pid IN (?,…)`。
    #   依据（性质）：**规则路永不产出 `ctx_pids`**（初始化为 []），只有大模型路/前端会设，
    #   故对 1000 题（规则路）恒不进入此分支 → 零影响。
    #   注意：参数与 where/args **成对追加**（下方 `assert sum(where 的 '?')==len(args)` 校验）。
    #   若 pid 集合极大（>SQLite 变量上限 999）需在上层分块，本层不静默截断。
    if getattr(spec, 'ctx_pids', None):
        add(_leaf_pid(spec.ctx_pids))
    # ⚠ 2026-10-05 新增：**题名检索**（子串 OR-并集，见 `_leaf_title`）。
    add(_leaf_title(_vals(spec, 'title')))
    if spec.scene:
        where.append('p.scene = ?'); args.append(spec.scene)
    _chg = 'ABS(p.change)' if getattr(spec, 'change_abs', False) else 'p.change'
    for key, col, op in (('ze_min', 'p.ze_ratio', '>='), ('ze_max', 'p.ze_ratio', '<='),
                         ('len_min', 'p.han_len', '>='), ('len_max', 'p.han_len', '<='),
                         ('sent_min', 'p.sent_n', '>='), ('sent_max', 'p.sent_n', '<='),
                         ('change_min', _chg, '>='), ('change_max', _chg, '<='),
                         ('thr_min', 'p.threshold', '>='), ('thr_max', 'p.threshold', '<=')):
        if key in spec.rng:
            add(_leaf_num(col, op, spec.rng[key]))
    if spec.pz:
        add(_leaf_pz(spec.pz))
    tl = _vals(spec, 'tail')
    # ⚠ 2026-10-03：若句脚字**已经**被句级算子接管（如「满足「句末字是地」的句子占比≥50%
    #   **或句脚为「圆」**」→ 谓词 = tail_any(地,圆)），就绝不能再额外加一个 `tail IN (…)` 的
    #   **与**条件——那会把范围砍成两个取值的**交集**（实测 Q0242：真值 43、引擎 15）。
    _lqp0 = (spec.line_q or {}).get('pred')
    if tl and _lqp0 and _lqp0[0] in ('tail', 'tail_any'):
        _taken = list(_lqp0[1]) if _lqp0[0] == 'tail_any' else [_lqp0[1]]
        tl = [v for v in tl if v not in _taken]
    if tl:
        add(_leaf_exists_lines('l.tail', tl))
    # ⚠ 2026-10-02：句级算子（∀/∄/≥k/=k/占比/条数/句位/交集/全等）
    _lw, _la = line_ops_where(spec)
    where += _lw
    args += _la
    # 一致性：声情标注与实测派生量**矛盾**的那一面
    if getattr(spec, 'consist', None):
        add(_leaf_consist(spec.consist))
    if spec.tail_pz:
        # ⚠ 2026-10-03：句级算子已按同一谓词接管时不要再加（否则 ∃ 平 ∧ ∄ 平 之类的自相矛盾）。
        _lqp1 = (spec.line_q or {}).get('pred')
        if not (_lqp1 and _lqp1[0] == 'tail_pz' and _lqp1[1] == spec.tail_pz):
            add(_leaf_tail_pz(spec.tail_pz))
    # 审查 C7 + ⚠ 2026-10-06 修（外部审查 P2-18）：自检必须覆盖**最终**的 where/args。
    #   旧版把 assert 写在 tail_pz 追加**之前**，那一步（以及将来任何新增条件）都不在校验范围内，
    #   名义上的「最终参数校验」实际只覆盖了中途状态。现移到 return 之前。
    assert sum(f.count('?') for f in where) == len(args), \
        'where/args 不平行（少写 args.extend 会整段错位，审查 C7）'
    return (' AND '.join(where) if where else '1=1'), args


# ================================================================ 布尔过滤树 → SQL（递归编译）
# 外部架构审查核心条目：`QuerySpec` 只能表达「字段间 AND、字段内 IN 并集」，无法表达
# 「（写秋景 或 写离愁）且 不是 临江仙的清词」这类**任意嵌套布尔**。`filters_tree` 补上这一层。
# 节点形状（与 `queryplan.validate()` 一致）：
#   {"and":[c…]} / {"or":[c…]} / {"not":c} / {"field":…,"op":…,"value":…}
def _sql_filters(conn, node):
    """布尔过滤树 → (where_sql, args)。**递归**编译，支持任意嵌套 and/or/not 与叶子。

    边界语义（**依据**：布尔代数与 SQL 惯例）：
      · **空的 `and`（`{"and":[]}`）= 真** → 编译成 `'1=1'`；「一个都不要求」＝不设限。
        （与「合取空集为真元」一致；也让「无条件」平滑退化为 `1=1`，`count_hits` 据此返回 None。）
      · **空的 `or`（`{"or":[]}`）= 假** → 编译成 `'0=1'`；「任一为真」在无候选时恒假。
        （与「析取空集为假元」一致；若判真会让「没有任何可选」错误地放行全库。）
      · `not` → `NOT (<子>)`。
    `conn` 预留（布尔编译本身不需要查库；保留形参与 `queryplan` 签名一致，便于将来做落地校验）。
    """
    if node is None:
        return '1=1', []
    if not isinstance(node, dict):
        raise ValueError('filters 节点必须是 dict（and/or/not/叶子），得到 %r' % (node,))
    if 'and' in node:
        parts, args = [], []
        for child in (node.get('and') or []):
            s, a = _sql_filters(conn, child)
            if s and s != '1=1':          # 恒真子式不必进 SQL（避免 `(1=1) AND …` 噪声）
                parts.append('(%s)' % s)
                args += a
        return (('(' + ' AND '.join(parts) + ')') if parts else '1=1'), args
    if 'or' in node:
        kids = node.get('or') or []
        if not kids:
            return '0=1', []              # 空 or = 假
        parts, args = [], []
        for child in kids:
            s, a = _sql_filters(conn, child)
            parts.append('(%s)' % s)
            args += a
        return '(' + ' OR '.join(parts) + ')', args
    if 'not' in node:
        s, a = _sql_filters(conn, node.get('not'))
        return 'NOT (%s)' % s, a
    if 'field' in node:
        return _leaf_sql(node)
    raise ValueError('filters 节点既非布尔节点也非叶子：%r' % (node,))


def _leaf_sql(node):
    """单个叶子 `{"field","op","value"}` → (sql, args)。字段与 op 的兼容性由 `queryplan.validate` 校验。"""
    f, op, v = node.get('field'), node.get('op'), node.get('value')
    if f in ('dynasty', 'author', 'cipai'):
        col = {'dynasty': 'p.dynasty', 'author': 'p.author', 'cipai': 'p.cipai'}[f]
        r = _leaf_one(col, list(v) if isinstance(v, (list, tuple)) else [v])
        return r if r else ('1=1', [])
    if f == 'title':
        r = _leaf_title(list(v) if isinstance(v, (list, tuple)) else [v])
        return r if r else ('1=1', [])
    if f == 'pid':
        r = _leaf_pid(list(v) if isinstance(v, (list, tuple)) else [v])
        return r if r else ('1=1', [])
    if f == 'scene':
        return 'p.scene = ?', [v]
    if f == 'consist':
        return _leaf_consist(v)
    if f in _NUM_COL:
        return _leaf_num(_NUM_COL[f], op, v)
    if f == 'lines.tail':
        r = _leaf_exists_lines('l.tail', list(v) if isinstance(v, (list, tuple)) else [v])
        return r if r else ('1=1', [])
    if f == 'lines.text':
        return _leaf_lines_text(v)
    if f == 'tail_pz':
        return _leaf_tail_pz(v)
    if f == 'pz':
        return _leaf_pz(v)
    if f == 'pz_exact':
        return _leaf_pz_exact(v)
    if f == 'tail_each':
        r = _leaf_tail_each(list(v) if isinstance(v, (list, tuple)) else [v])
        return r if r else ('1=1', [])
    if f == 'line_q':
        w, a = _line_q_where(v)     # 单一来源：与经典路径同一编译
        return (('(' + ' AND '.join(w) + ')') if w else '1=1'), a
    raise ValueError('未知的 filters 叶子字段：%r' % (f,))


_PZ_RE_CACHE = {}


def pz_re(pat):
    """声律模式 → 正则（`?`/`？` 表示任意一位）。检索与复核共用这一份定义。

    带缓存（审查 P9）：旧版**每句都 re.compile 一次**，配对/复核题会重复编译上万次。
    """
    r = _PZ_RE_CACHE.get(pat)
    if r is None:
        r = re.compile(''.join('.' if c in '?？' else re.escape(c) for c in pat))
        _PZ_RE_CACHE[pat] = r
    return r


def _line_pred_ok(kind, val, pz, tail, idx, han_len):
    """单句是否满足**句级谓词**——`_pred_sql()` 的 Python 同义实现（供证据层重算）。

    口径必须与 `_pred_sql()` **逐字对齐**：`parity` 用 `l.idx % 2`（idx 从 0 起，
    `=0` 表示句位 1/3/5… 即「奇数句位」）；`len` 是 `han_len` 的**闭区间**。
    """
    if kind == 'tail':
        return (tail or '') == val
    if kind == 'tail_any':
        return (tail or '') in set(val)
    if kind == 'tail_pz':
        return (pz or '')[-1:] == val
    if kind == 'pz':
        return bool(pz) and bool(pz_re(val).search(pz))
    if kind == 'pz_exact':
        return (pz or '') == val
    if kind == 'len':
        return han_len is not None and val[0] <= han_len <= val[1]
    if kind == 'parity':
        return idx is not None and (idx % 2) == val
    return False


def line_satisfies(pz, tail, spec, idx=None, han_len=None):
    """某一句是否满足 spec 的**行级**条件。返回命中的条件名列表。

    行级条件：句脚字（`tail`，可多值）、句脚平仄（`tail_pz`）、声律模式（`pz`）；
    高级句级条件：平仄串全等（`pz_exact`）、篇内交集（`tail_each`）、
    句级算子谓词（`line_q['pred']`，含 `parity` 句位奇偶 / `len` 句长）。
    ——检索（SQL）与证据展示（选哪一句）必须用**同一份判定**，否则就会出现
    「问句脚字，答案却展示另一句」这类看起来没错、其实答非所问的错（2026-09-30 实测）。

    ⚠ 2026-10-08（缺陷3）：旧版只认 tail/tail_pz/pz，**完全不认** line_q / pz_exact /
    tail_each / parity。后果：spec 只带高级句级算子时，本函数对所有句都返回 [] →
    `evidence.poem_block` 的命中句集合 `m_idx` 为空 → 落到「按仄声占比最高的句」补证据 →
    **展示了一句与查询条件无关的句子**（破坏「可溯源问答」）。
    改后行为：把这些条件都纳入判定，使证据层能指名**命中句**（`idx`/`han_len` 由
    调用方按句传入；见 evidence.py 的调用点）。

    取舍（篇级量）：
      · `parity`（句位奇偶）可**句级**判定（看该句 idx 的奇偶），随参数 `idx` 判；
      · `consist`（声情标注为 X 但实测前后段相反）是**篇级**声情走向，**不在这里**按句判
        ——否则会把一整篇的每一句都误标成「命中句」。它在 `evidence.poem_block` 里作为
        **篇级命中理由**（`poem_reasons`）表达（见 evidence.py）。

    `poem_reasons` 的数据结构（`list[str]` 篇级理由，与句级 `match_reasons` 分工）在
    `evidence.poem_block` 顶部有完整契约说明；`ask.py:_line_note` 目前只读
    `lines[i]['match_reasons']`（句级），**尚未**读 `poem_reasons`——接入建议见交付报告。
    """
    hit = []
    if (tail or '') in _vals(spec, 'tail'):
        hit.append('句脚字')
    if spec.tail_pz and (pz or '')[-1:] == spec.tail_pz:
        hit.append('句脚平仄')
    if spec.pz and pz and pz_re(spec.pz).search(pz):
        hit.append('声律模式')
    if spec.pz_exact and (pz or '') == spec.pz_exact:
        hit.append('平仄串全等')
    for _v in (spec.tail_each or []):
        if (tail or '') == _v:
            hit.append('篇内交集·句脚字')
    _lq = getattr(spec, 'line_q', None)
    if _lq and _lq.get('pred') and _line_pred_ok(
            _lq['pred'][0], _lq['pred'][1], pz, tail, idx, han_len):
        # 句级算子谓词本身是「句级」的：满足谓词的句即命中句，与量词（∀/∃/COUNT）无关
        # ——量词只决定「篇是否入结果集」，命中句始终是「满足谓词的那些句」。
        hit.append('句级算子·满足句')
    return hit


def has_line_cond(spec):
    """是否含**行级（句级）条件**——决定 verify / 证据展示要不要逐句复核。

    ⚠ 2026-10-06 修（外部审查 P1-12）：旧判据只查 tail/tail_pz/pz，漏了
    `pz_exact` / `tail_each` / `line_q`。后果：spec 只带高级句级算子（例如「每一句都
    整句平仄串正好是『仄仄平平仄仄』」）时，本函数返回 False → `verify_spec_on_poem`
    的**整段行级复核被跳过** → 这些算子**完全没有独立复核**（SQL 执行了、但没有兜底）。
    `has_hard()` 早在 2026-10-03（Q0121 教训）就补全了这几项，此处属**未同步的补集**。
    """
    return bool(_vals(spec, 'tail') or spec.tail_pz or spec.pz
                or spec.pz_exact or getattr(spec, 'tail_each', None) or spec.line_q)


def count_hits(conn, spec):
    # 语义（审查 C8 指出接口含糊，这里写死）：返回 **None = 没有硬条件**（不是「0 篇」）；
    # 返回 **0 = 有硬条件但一篇都不满足**；返回正整数 = 真值。调用方必须区分 None 与 0。
    """满足**硬条件**的篇数（真值，不是 top-k）。无硬条件时返回 None。

    为什么必须有它：回答里写「共召回 N 篇」若用 top-k（=3），用户会以为全库只有 3 篇；
    实测「句脚是愁的清词」真值是 794 篇，而旧文案写的是「共召回 3 篇」。
    """
    if spec.unsupported:
        return 0
    where, args = _sql(spec)
    if where == '1=1':
        return None
    return scope_count(conn, where, args)


def verify_spec_on_poem(conn, pid, spec):
    """独立复核：某篇是否真的满足 spec 的**全部**条件（不依赖检索 SQL，逐条重查）。

    这是「结果自查」层：检索 SQL 写错列名/漏条件时，SQL 自己不会报错，
    但这里会用另一条路径（Python 侧逐条比对）把它抓出来。返回违反项描述列表。
    """
    bad = []
    r = conn.execute('SELECT dynasty,author,cipai,title,scene,han_len,sent_n,ze_ratio,change,threshold '
                     'FROM poems WHERE pid=?', (pid,)).fetchone()
    if not r:
        return ['篇目不存在']
    dyn, au, cp, ti, sc, hl, sn, zr, ch, th = r
    if _vals(spec, 'dynasty') and dyn not in _vals(spec, 'dynasty'):
        bad.append('朝代不符（%s∉%s）' % (dyn, '／'.join(_vals(spec, 'dynasty'))))
    if _vals(spec, 'author') and (au or '').strip() not in _vals(spec, 'author'):
        bad.append('词人不符（%s∉%s）' % (au, '／'.join(_vals(spec, 'author'))))
    if _vals(spec, 'cipai') and (cp or '').strip() not in _vals(spec, 'cipai'):
        bad.append('词牌不符（%s∉%s）' % (cp, '／'.join(_vals(spec, 'cipai'))))
    # ⚠ 2026-10-06 修（外部审查 P1-13）：`title` 早已进入检索 SQL（`_sql` 用
    #   `p.title LIKE %题名%` 子串匹配），但这里**从未复核**——「SQL 筛了、独立复核没查」，
    #   破坏了「SQL + Python 双路复核」的设计。现按同一**子串**语义补上。
    if _vals(spec, 'title') and not any((x or '') in (ti or '') for x in _vals(spec, 'title')):
        bad.append('题名不符（%s 不含 %s）' % (ti, '／'.join(_vals(spec, 'title'))))
    if spec.scene and sc != spec.scene:
        bad.append('声情不符（%s≠%s）' % (sc, spec.scene))
    # ⚠ 2026-10-08 新增（缺陷4）：`consist` 在 `_sql()`（第 1644-1650 行）里被编译成**真实硬条件**
    #   （`后段上升` → `p.change < 0`、`后段下降` → `p.change > 0`、其余 → `ABS(p.change) < 1`），
    #   `has_hard()` 也把它算作硬条件；但本复核**唯独漏了它** → 「SQL 筛一次 + Python 独立复核一次」
    #   在这个量上并不成立（改前行为）。改后行为：按 `_sql()` 的同一口径，用篇的 `change` 字段独立复算。
    #   注意 `scene` 已被同步设为 consist 值（parse_query 第 1484 行），上面的声情复核只覆盖了
    #   「标注」这一半，「实测相反」这一半必须靠这里。
    if getattr(spec, 'consist', None):
        if ch is None:
            bad.append('一致性不符（声情标注为%s但实测前后段相反，需 change 判定，本篇 change 缺失）'
                       % spec.consist)
        elif spec.consist == '后段上升':
            if not (ch < 0):
                bad.append('一致性不符（声情标注为后段上升，要求 change<0，实测 %.1f）' % ch)
        elif spec.consist == '后段下降':
            if not (ch > 0):
                bad.append('一致性不符（声情标注为后段下降，要求 change>0，实测 %.1f）' % ch)
        else:
            if not (abs(ch) < 1):
                bad.append('一致性不符（声情标注为%s，要求 |change|<1，实测 %.1f）'
                           % (spec.consist, ch))
    for key, val, op, lab in (('ze_min', zr, '>=', '仄声比例'), ('ze_max', zr, '<=', '仄声比例'),
                              ('len_min', hl, '>=', '字数'), ('len_max', hl, '<=', '字数'),
                              ('sent_min', sn, '>=', '句数'), ('sent_max', sn, '<=', '句数'),
                              ('change_min', ch, '>=', '变化'), ('change_max', ch, '<=', '变化'),
                              ('thr_min', th, '>=', '阈值'), ('thr_max', th, '<=', '阈值')):
        if key not in spec.rng:
            continue
        want = spec.rng[key]
        got = val
        # ⚠ 2026-10-03：问「变化**幅度**」时筛选 SQL 用的是 `ABS(change)`，复核也必须取绝对值——
        #   否则「|变化|≥10」的篇（变化 = −10.0）会被自己的复核判成「变化不符」
        #   （实测 Q0387：答案一边命中该篇、一边报「条件复核未通过：变化不符」，自相矛盾）。
        if getattr(spec, 'change_abs', False) and key in ('change_min', 'change_max') and got is not None:
            got = abs(got)
        ok = (got is not None) and (got >= want if op == '>=' else got <= want)
        if not ok:
            bad.append('%s不符（%s %s %s 不成立）' % (lab, got, op, want))
    if has_line_cond(spec):
        # ⚠ 2026-10-08（缺陷5）：旧版是 `SELECT pz,tail`，**没有 idx / han_len** —— 于是
        #   `parity`（句位）与 `len`（句长）两类谓词**根本无从复核**：它们经 line_q 进了 SQL，
        #   却在 Python 侧被 `_lines_hit` 返回 None → 整条落到 else 分支 → 没有任何兜底。
        #   现把行数据补成 `idx,han_len,pz,tail`（只是让数据齐备，不改任何既有判定口径）。
        rows = conn.execute('SELECT idx,han_len,pz,tail FROM lines WHERE pid=?', (pid,)).fetchall()
        _lq = spec.line_q or {}
        _pred, _op = _lq.get('pred'), _lq.get('op')

        def _lines_hit(kind, val):
            # ⚠ rows 是 `SELECT idx, han_len, pz, tail`：第 3 个是**平仄串**、第 4 个是**句脚字**。
            #   第一版把 pz/tail 写反了 → 恒为 0 命中，误报「句级算子不满足」（实测 Q0622/Q0674）。
            if kind == 'tail':
                return [1 for _i, _hl, _pz, t in rows if (t or '') == val]
            if kind == 'tail_any':
                return [1 for _i, _hl, _pz, t in rows if (t or '') in set(val)]
            if kind == 'tail_pz':
                return [1 for _i, _hl, _pz, _t in rows if (_pz or '')[-1:] == val]
            if kind == 'pz':
                return [1 for _i, _hl, _pz, _t in rows if _pz and pz_re(val).search(_pz)]
            if kind == 'pz_exact':
                return [1 for _i, _hl, _pz, _t in rows if (_pz or '') == val]
            # ⚠ 2026-10-08（缺陷5）：与 `_pred_sql()` **逐字同口径**——
            #   parity：`(l.idx % 2) = ?`（idx 从 0 起，=0 即句位 1/3/5…）；len：han_len 闭区间。
            if kind == 'parity':
                return [1 for _i, _hl, _pz, _t in rows if _i is not None and (_i % 2) == val]
            if kind == 'len':
                return [1 for _i, _hl, _pz, _t in rows
                        if _hl is not None and val[0] <= _hl <= val[1]]
            return None

        hit = _lines_hit(*_pred) if _pred else None
        if hit is not None and _op in ('∃', '∀', '∄', '=k', '≥k', '占比≥p', '条数∈[a,b]'):
            # ⚠ 2026-10-03：句级算子接管谓词时，**不能**再用「存在一句满足」判它——算子的语义是
            #   「篇内满足的句数 =k/≥k/占比/条数/∀/∄」（实测 Q0390：=k 1 句 且句脚∈{瘦,去}，
            #   复核按单值 tail=瘦 判 → 误报「无句脚字为瘦的句子」，与 SQL 自相矛盾）。
            n, tot = len(hit), len(rows)
            # ⚠ 2026-10-08 修（缺陷1）：`∀` 由 `n == tot` 改为 `tot > 0 and n == tot`。
            #   改前行为：空篇（tot=0, n=0）→ `0 == 0` 判**满足**；而检索 SQL（line_ops_where 的
            #   ∀ 分支）与真值口径（gen_q1000.scope_where 的 ∀ 分支）**都**加了
            #   `pid IN (SELECT pid FROM lines)` → 排除空篇。三处里只有本复核把空篇算进去 → 打架。
            #   改后行为：与 SQL/真值统一为「∀ 要求篇内至少一句、且每句都满足」；空篇不计。
            #   （全库空篇 = 144 篇；`SELECT COUNT(*) FROM poems WHERE sent_n=0`。）
            _okq = {'∃': n >= 1, '∀': (tot > 0 and n == tot), '∄': n == 0,
                    '=k': n == _lq.get('k', 0), '≥k': n >= _lq.get('k', 0),
                    '占比≥p': (tot > 0 and n * 1.0 / tot >= _lq.get('ratio', 0)),
                    '条数∈[a,b]': _lq.get('ka', 0) <= n <= _lq.get('kb', 0)}[_op]
            if not _okq:
                bad.append('句级算子不满足（%s，满足句数 %d/%d）' % (_op, n, tot))
        else:
            _pzs = [r[2] for r in rows]
            _tls = [r[3] for r in rows]
            tl = _vals(spec, 'tail')
            if _pred and _pred[0] in ('tail', 'tail_any'):
                tl = list(dict.fromkeys(list(tl) + (
                    list(_pred[1]) if _pred[0] == 'tail_any' else [_pred[1]])))
            if tl and not any((x or '') in tl for x in _tls):
                bad.append('无句脚字为 %s 的句子' % '／'.join(tl))
            if spec.tail_pz and not any((pz or '')[-1:] == spec.tail_pz for pz in _pzs):
                bad.append('无句脚为%s的句子' % spec.tail_pz)
            if spec.pz and not any(pz and pz_re(spec.pz).search(pz) for pz in _pzs):
                bad.append('无声律模式 %s 命中句' % spec.pz)
            # ⚠ 2026-10-06 修（外部审查 P1-12）：高级句级条件原先**不在复核范围内**
            #   （has_line_cond 漏判 → 整块被跳过）。这里补上 pz_exact 与 tail_each 的独立复核。
            # ⚠ 2026-10-08 修（缺陷5）：原先注释里写「parity 暂未纳入复核」——本轮已补齐：
            #   parity/len 由上面的 `_lines_hit` 处理（走 `hit is not None` 那条分支）。
            if spec.pz_exact and not any((pz or '') == spec.pz_exact for pz in _pzs):
                bad.append('无声律模式**全等** %s 的句子' % spec.pz_exact)
            for _v in (spec.tail_each or []):
                if not any((t or '') == _v for t in _tls):
                    bad.append('tail_each 要求每个句脚都出现，但缺「%s」' % _v)
    return bad


def _norm(d):
    if not d:
        return {}
    mx = max(d.values()) or 1.0
    return {k: v / mx for k, v in d.items()}


# ⚠ 2026-10-06 新增（外部审查 P2-37/38/39）：候选上限**被触发**时必须显式记录，而不是
#   静默截断——否则「本可排进 top-k 的作品」可能因截断永远进不了候选池，表现为
#   「结果看起来正常、其实少了一部分」。记录 = 进程内列表 + stderr 警告；
#   `search()` 每次开头清空，上层可经 `route_truncations()` 读取并如实披露。
_ROUTE_TRUNCATED = []


def _note_trunc(name, n, limit):
    if n >= limit:
        msg = '%s 候选达上限 %d（实际 %d），排序信号可能不完整' % (name, limit, n)
        if msg not in _ROUTE_TRUNCATED:
            _ROUTE_TRUNCATED.append(msg)
            try:
                sys.stderr.write('⚠ %s\n' % msg)
            except Exception:
                pass


def route_truncations():
    """本次检索是否发生过候选截断（供上层如实披露，而不是静默）。"""
    return list(_ROUTE_TRUNCATED)


def route_bigram(conn, text):
    """① 二字组路：FTS5(bigram) + BM25，**直接返回篇级分**（同篇取最高分行）。"""
    bs = bigrams(text)
    if not bs:
        return {}
    q = ' OR '.join('"%s"' % b for b in dict.fromkeys(bs))
    out = {}
    # ⚠ 2026-10-06（P2-37）：改 fetchall 以便检测「是否真的撞到上限」并显式记录（不静默）。
    rows = conn.execute(
        'SELECT l.pid, bm25(lines_bigram) FROM lines_bigram b JOIN lines l ON l.rowid=b.rowid '
        # 审查 P15：旧 LIMIT 20000 会把宽条件（如朝代=清 26,742 篇）**静默截断**，
        # 且截断顺序由 bm25 决定（不确定）。全库 42 万句，这里放到 40 万即等于不截断。
        'WHERE b.big MATCH ? ORDER BY bm25(lines_bigram) LIMIT 400000', (q,)).fetchall()
    _note_trunc('route_bigram', len(rows), 400000)
    for pid, score in rows:
        v = 1.0 / (1.0 + abs(score))
        if v > out.get(pid, 0.0):
            out[pid] = v
    return out


def route_phrase(conn, keywords):
    """② 全文路：**二字组短语查询**（FTS5 把连续二字组当短语 ⇒ 等价于子串精确匹配）。

    注意：不能用 `lines_fts`（默认分词器把整串汉字当一个 token，子串直接搜不到）——
    这一点是实测出来的：初始版用 lines_fts 搜「风紧玉楼斜」召回 0。
    """
    out = {}
    for kw in keywords:
        bs = bigrams(kw)
        if not bs:
            continue
        if len(bs) == 1:                      # 只有 2 个字：退回单词查询
            q = '"%s"' % bs[0]
        else:
            q = '"%s"' % ' '.join(bs)
        try:
            rows = conn.execute(
                'SELECT l.pid FROM lines_bigram b JOIN lines l ON l.rowid=b.rowid '
                'WHERE b.big MATCH ? LIMIT 20000', (q,)).fetchall()
        except sqlite3.OperationalError:
            continue
        # ⚠ 2026-10-06（P2-37）：撞上限时显式记录（不静默）。
        _note_trunc('route_phrase(%s)' % kw, len(rows), 20000)
        for (pid,) in rows:
            out[pid] = out.get(pid, 0.0) + 1.0
    return out


def rescue_title(conn, spec):
    """**「题名当词原文」兜底**：词面（keywords）其实是**题名**时，把它提升为题名条件。

    ⚠ 2026-10-05 新增（朋友实测驱动）。由来：
      · 问句「蝶恋花·清明同诸子集原白斋中 的作者是谁」→ 已由 parse_query 的
        「词牌·题名」识别接住（题名=清明…），命中 1 篇；
      · 但**裸题名**（不带词牌，如「清明同诸子集原白斋中」「寄怀阿嫂」）解析后
        只剩「词面=…」→ 无硬条件 → 走**语义融合排序**，端上来的却是元曲里
        偶含「阿嫂」二字的《单刀会》——答非所问（朋友截图里那一幕）。
    判据（两条同时成立才提升，宁缺勿滥）：
      ① 词面里**至少一个 2+ 字串**在 title 里命中（子串）；
      ② 这些词面在**正文（lines 的整句）**里**命中为 0**——
         说明它们不是「词里的句子」，而更可能是**题名**。
    命中即把该词面移入 `title_any`（硬条件），并清出 keywords，随后检索按题名而不再
    按语义乱排。**只对「本来没有硬条件」的问句生效**（有词牌/词人/朝代等条件时不抢）。
    """
    # ⚠ 2026-10-06 修（外部审查 P2-15）：原判据是「有任何硬条件就不救题名」——于是
    #   「清 清明同诸子集原白斋中」这类**朝代 + 裸题名**的问句被一刀切挡掉（朝代本身
    #   不是「检索式」线索、与题名判定也不冲突），题名永远救不回来。
    #   现收窄为：只在存在**与题名判定易打架**的形式条件时才不动——已有题名，或已有
    #   词牌/词人/句级算子/声律模式等具体条件。单纯的朝代、数值范围、声情不阻止 rescue。
    if _vals(spec, 'title'):
        return False                   # 已有题名条件：不重复添加
    if (_vals(spec, 'cipai') or _vals(spec, 'author') or spec.pz or spec.pz_exact
            or getattr(spec, 'line_q', None) or _vals(spec, 'tail') or spec.tail_pz):
        return False                   # 与题名判定易打架的形式条件：保持旧行为（不动）
    kws = [k for k in (getattr(spec, 'keywords', None) or []) if len(k) >= 2]
    if not kws:
        return False
    t_hits = []
    for kw in kws[:6]:
        try:
            row = conn.execute('SELECT COUNT(*) FROM poems WHERE title LIKE ?',
                               ('%' + kw + '%',)).fetchone()
        except sqlite3.OperationalError:
            row = None
        if row and row[0] > 0:
            t_hits.append(kw)
    if not t_hits:
        return False
    # ② 这些词面在**正文**里命中为 0（题名不在正文里出现，正是「被当词原文」的症状）
    for kw in t_hits:
        bs = bigrams(kw)
        if not bs:
            continue
        q = '"%s"' % (' '.join(bs) if len(bs) > 1 else bs[0])
        try:
            n = conn.execute(
                'SELECT COUNT(*) FROM lines_bigram b JOIN lines l ON l.rowid=b.rowid '
                'WHERE b.big MATCH ?', (q,)).fetchone()[0]
        except sqlite3.OperationalError:
            n = 0
        if n > 0:                      # 这个串在正文里确有其句 → 不是题名，不提升
            return False
    kept = [k for k in kws if k not in t_hits]
    spec.title_any = list(spec.title_any or []) + t_hits
    spec.keywords = kept
    _finalize(spec)                    # 派生单值 title（与「词牌·题名」识别同源）
    return True


def route_numeric(conn, where, args, limit=20000):
    """④ 数值路：符合硬条件者按「仄声占比 + 篇幅」给排序信号（不代表优劣）。"""
    rows = conn.execute(
        'SELECT p.pid, p.ze_ratio, p.han_len FROM poems p WHERE %s LIMIT %d'
        % (where, limit), args).fetchall()
    # ⚠ 2026-10-06（P2-39）：撞上限时显式记录——数值路的候选池不完整会让融合排序
    #   看不到本该靠前的篇目（答案是另一路给的，但展示质量受影响）。
    _note_trunc('route_numeric', len(rows), limit)
    return {pid: (zr or 0) / 100.0 * 0.6 + min(nc or 0, 120) / 120.0 * 0.4
            for pid, zr, nc in rows}


def route_pz(conn, pat):
    """⑤ 声律模式路：按平仄串匹配句（`?`/`？` 为任意位），**匹配句越长分越高**。

    为什么按句子长度加权：词学关心的是「某种声律格局是否显著」，全篇句均 2 字的小令
    偶合出一个五字格局，意义远不如长句命中。
    """
    like = '%' + pat.replace('?', '_').replace('？', '_') + '%'
    # 「每篇取最高句分」下推到 SQL：原实现把**命中行全部搬进 Python**（实测一次 130,914 行）
    # 再逐行比较；改成 GROUP BY pid + MAX(...) 后只回「每篇一行」，聚合在 C 层做。
    # 数值等价：两边都是 int→double 除法（CAST AS REAL / float()），MAX 是精确比较；
    # 原来 `max(1, sn)` 的兜底在 SQL 里写成标量 MAX(1, p.sent_n)。
    rows = conn.execute(
        'SELECT l.pid, MAX(CAST(l.han_len AS REAL) / MAX(1, p.sent_n)) AS sc '
        'FROM lines l JOIN poems p ON p.pid = l.pid WHERE l.pz LIKE ? GROUP BY l.pid',
        (like,)).fetchall()
    return {pid: sc for pid, sc in rows}


def has_hard(spec):
    """是否有**可检索的形式条件**（单一来源：`search` 的 restrict 与作答层的模糊意图闸共用）。

    ⚠ 2026-10-03：旧判据漏了 `pz_exact`／`line_q`／`tail_each`／`consist`——
    「每一句都整句平仄串正好是「仄仄平平仄仄」的作品」这类**只有句级算子**的问句被判成
    「没有硬条件」→ `restrict=None` → 检索**不做范围限定**，端上去的是全库融合排序前几篇
    （实测 Q0121：真值 2 篇，却展示 3 篇、还声称「全库仅此 2 篇」）。
    """
    # ⚠ 2026-10-08（任务C）：`ctx_pids`（上一轮结果集）是**硬条件**（`_sql` 编译成 `p.pid IN (…)`），
    #   故必须计入——否则「那里面哪个最短」这类**只带范围**的追问会被判成「无硬条件」而全库排序。
    #   规则路 ctx_pids 恒为空 → 对 1000 题零影响。
    return bool(_vals(spec, 'dynasty') or _vals(spec, 'author') or _vals(spec, 'cipai')
                or _vals(spec, 'title')
                or spec.scene or spec.pz or spec.pz_exact or _vals(spec, 'tail')
                or spec.tail_pz or spec.tail_each or spec.line_q or spec.consist or spec.rng
                or getattr(spec, 'ctx_pids', None))


# ⚠⚠ 2026-10-08 新增（任务：**真正的向量语义检索 + RRF 融合 + Reranker**）。
# 背景：外部架构审查确认旧「语义相关度」不是 embedding，而是「LLM 扩词 → 塞进 FTS/bigram」，
#   对「秋景」「羁旅愁思」这类**词面必然不重合**的问题天然无能——那是**结构缺失**。
# 下面两个函数 + `search()` 中新增的一段，是**最小接入**：向量作为**额外一路候选**参与融合，
#   绝不动任何既有 SQL 硬条件。四点硬性约束（对应审查要求）逐条钉在 `search()` 的注释里。
def _vector_enabled():
    """向量路开关：`LVC_VECTOR=1` 才启用（**默认关闭**）——默认关闭时行为与改动前逐字节一致。"""
    return os.environ.get('LVC_VECTOR') == '1'


def semantic_signal(spec):
    """`spec` 是否命中「语义类信号」（决定要不要**额外**跑一次向量检索）。

    判据（单一来源）：① 大模型路给出的 `semantic` 扩展词非空；或
      ② 规则路 `keywords` 里有 **2+ 字**的自由词面——规则路已用 STOPWORDS/FRAME_WORDS
         把「平仄/字数/占比/句脚…」这类**提问虚词**剔净，剩下的即**主题类词**
         （如「秋景」「离乡漂泊」「隐逸闲适」「边塞风雪」）。
    规则路对「清 临江仙 仄声比例高于45%」这类**纯形式条件**问句，keywords 恒为空 → 不触发。
    """
    if getattr(spec, 'semantic', None):
        return True
    return any(len(k) >= 2 for k in (getattr(spec, 'keywords', None) or []))


def _vector_channel(conn, qtext, restrict, topk):
    """跑一次向量检索，返回 `{pid: score}`。**任何不可用/异常都返回 `{}`**（主链绝不因它崩）。

    硬性约束③：有硬条件时用 `restrict` 收窄——向量候选**绕不过**硬过滤。
    """
    try:
        import vector_index
        if not qtext or not vector_index.available(conn):
            return {}
        hits = vector_index.search(qtext, topk=max(50, topk * 10), conn=conn)
    except Exception:
        return {}
    d = {pid: s for pid, s in hits}
    if restrict is not None:
        d = {pid: s for pid, s in d.items() if pid in restrict}
    return d


def search(conn, query, topk=5, weights=(0.40, 0.20, 0.15, 0.10, 0.15), explain=False):
    """五路检索 + 融合。返回按融合分排序的篇级结果。

    行级索引 → 篇级聚合：同一篇取**最高分行**计入语义/全文分（篇内不重复累加，
    否则长调天然占优）。
    """
    spec = parse_query(conn, query) if isinstance(query, str) else query
    _ROUTE_TRUNCATED.clear()        # 本次检索的截断记录从零开始（外部审查 P2-37/38/39）
    if spec.unsupported:
        return []
    where, args = _sql(spec)
    hard = has_hard(spec)

    restrict = None
    if hard:
        restrict = set(scope_pids(conn, where, args))
        if not restrict:
            return []

    if getattr(spec, 'order_by', None):
        # 极值／排序题：问「哪一首…最高」，答案就是该指标的**极值篇**，与五路融合分毫无关系
        # （旧版把融合分第一当答案，还硬写「排序最前者为…」）。
        return items_of(conn, [pid for pid, _v in order_pids(conn, spec, topk=topk)])

    # 审查 B6：旧写法 `isinstance(query, str)` 在 ask.py 主路径（传的是 QuerySpec）下恒为 False，
    # 于是权重最高（0.40）的二字组路**永远为空**。判据改成「有没有原始问句」：
    # ⚠ 2026-10-08（任务C）：**语义扩展词 `semantic` 并入全文检索**（提升召回）——**不改任何 SQL
    #   硬条件**（`_sql` 完全不看 semantic），有硬条件时候选仍会被 `restrict` 收窄，故不影响
    #   硬条件题的结果集；只在**无硬条件**的语义题上补充召回。规则路 semantic 恒为空 → 1000 题零影响。
    _sem = [w for w in (getattr(spec, 'semantic', None) or []) if w]
    _lex_txt = ((spec.raw or '') + ' ' + ' '.join(_sem)).strip() if _sem else (spec.raw or '')
    _ft_kws = list(dict.fromkeys(list(spec.keywords or []) + _sem)) if _sem else (spec.keywords or [])
    lex = route_bigram(conn, _lex_txt) if _lex_txt else {}
    ft = route_phrase(conn, _ft_kws) if _ft_kws else {}
    # 数值路只在用户明确给了数值条件时参与（否则会把「满足 1=1 的前 N 篇」灌进来）
    num = route_numeric(conn, where, args) if spec.rng else {}
    pzs = route_pz(conn, spec.pz) if spec.pz else {}
    meta = {pid: 1.0 for pid in scope_pids(conn, where, args)} if hard else {}

    w1, w2, w3, w4, w5 = weights
    lex, ft, num, meta, pzs = _norm(lex), _norm(ft), _norm(num), _norm(meta), _norm(pzs)
    # ⚠⚠ 2026-10-08 新增（真正的向量语义检索 + RRF 融合）——**五点硬性约束**，逐条对应：
    #   ① **开关默认关闭**：只有 `LVC_VECTOR=1` 才进入本块；默认时 `vec` 恒为 `{}`，
    #      走下方 `else` 的原加权融合 → 与改动前**逐字节一致**（1000 题门禁即在此口径验证）。
    #   ② **索引不可用 / 无网络 / 无嵌入端点 → 完全跳过**：`_vector_channel` 捕获一切异常、
    #      不可用直接返回 `{}` → 行为与现在一致（绝不因向量崩或阻塞）。
    #   ③ **不改任何 SQL 硬条件**：本块**只读** `where/args/restrict`，绝不改动它们；
    #      向量只影响「召回哪些候选、怎么排序」，**绝不**影响「哪些篇满足条件」。
    #   ④ **有硬条件时向量候选仍被 `restrict` 收窄**（见 `_vector_channel`），绕不过硬过滤。
    #   ⑤ **RRF 而非固定权重**：向量分与 BM25/声律/数值分**不同尺度**，故按**名次**融合
    #      （`fusion.rrf`）——理由见 `fusion.py` 模块 docstring。
    # ⚠ 向量查询文本的**优先级**：大模型语义扩展词 > 规则路关键词（框架词已剔净，
    #   剩下的即主题词，如「秋景」「离乡漂泊之苦」） > 整句问句。
    #   实测：整句嵌入会混入「清词/有哪些」这类噪声，相关性明显下降；
    #   用关键词后「描写边塞风雪」能命中「落日塞垣路，风劲戛貂裘」这类作品。
    _kws = [w for w in (spec.keywords or []) if len(w) >= 2]
    _qtext = (' '.join(_sem) if _sem
              else (' '.join(_kws) if _kws
                    else (spec.raw_question or spec.raw or (query if isinstance(query, str) else ''))))
    vec = (_vector_channel(conn, _qtext, restrict, topk)
           if (_vector_enabled() and semantic_signal(spec)) else {})
    if vec:
        import fusion as _fusion
        # ⚠ 2026-10-08：**向量主导排序的两版尝试均不理想，已回退为经典 RRF**——
        #   版本一（restrict 为 None 时向量主导）：仅覆盖无硬条件场景；
        #   版本二（向量经 restrict 收窄后主导）：部分语义问句被硬条件把向量候选滤空 → 0 篇拒答。
        #   两版都出现「写秋景」排到不相关篇或 0 篇的问题 → 恢复经典 RRF（至少不出 0 篇）。
        #   语义排序的调优（向量分阈值、语义题专用通道、rerank 介入点）记为下一迭代（D26）。
        #   基础设施保留：vector_index.py（嵌入+faiss）、fusion.py（RRF+rerank）、
        #   build_vector_index.py（建索引 CLI，--limit 试跑/断点续跑），开关 LVC_VECTOR 默认关。
        _rrf = _fusion.rrf([_fusion.ranked(lex), _fusion.ranked(meta), _fusion.ranked(ft),
                            _fusion.ranked(num), _fusion.ranked(pzs), _fusion.ranked(vec)])
        cands = set(_rrf)
        # 六路（含向量）各按名次降序 → RRF 融合：多路共识者靠前，免疫量纲差异。
        _rrf = _fusion.rrf([_fusion.ranked(lex), _fusion.ranked(meta), _fusion.ranked(ft),
                            _fusion.ranked(num), _fusion.ranked(pzs), _fusion.ranked(vec)])
        cands = set(_rrf)
        if restrict is not None:
            cands &= restrict
        fused = [(_rrf.get(pid, 0.0), pid) for pid in cands]
        fused.sort(key=lambda x: (-x[0], x[1]))
        if _fusion.rerank_enabled():
            # 精排：**默认关闭**（`LVC_RERANK=1` 才开）。见 fusion.py 的实测提醒
            # ——本机网关的 qwen3-reranker 在多文档下区分度不足，先保「不劣化」。
            # 只重排头部，其余保持原序；不可用/失败时 rerank_block **原序返回**（不改结果）。
            _n = min(len(fused), max(20, topk * 4))
            _head = fused[:_n]
            _by = {p: s for s, p in _head}
            _order = _fusion.rerank_block(conn, _qtext, [p for _s, p in _head])
            fused = [(_by.get(p, 0.0), p) for p in _order] + fused[_n:]
    else:
        cands = set(lex) | set(ft) | set(num) | set(meta) | set(pzs)
        if restrict is not None:
            cands &= restrict
        fused = []
        for pid in cands:
            s = (w1 * lex.get(pid, 0) + w2 * meta.get(pid, 0) + w3 * ft.get(pid, 0)
                 + w4 * num.get(pid, 0) + w5 * pzs.get(pid, 0))
            fused.append((s, pid))
        fused.sort(key=lambda x: (-x[0], x[1]))
    # ⚠ 2026-10-03 展示层：**空篇（0 句 / 0 字）不占头条**——语料里确有元曲残片（0 句 / 0 字），
    #   它们只是「空集」的**平凡**满足者（如「没有任何一句…」「每一句都…」），作为证据毫无信息量
    #   （实测 Q0008：头条是一篇 0 句 / 0 字的元曲残片，还连带触发「比例不自洽」的误判）。
    #   只在**同分**的头 200 名内重排，不改任何计数与范围。
    if len(fused) > 1:
        _head = fused[:200]
        _pids = [pid for _s, pid in _head]
        _nz = {}
        for _i in range(0, len(_pids), 500):
            _ch = _pids[_i:_i + 500]
            for _r in conn.execute('SELECT pid, sent_n FROM poems WHERE pid IN (%s)'
                                   % ','.join('?' * len(_ch)), _ch):
                _nz[_r[0]] = _r[1] or 0
        _head.sort(key=lambda x: (-x[0], 0 if _nz.get(x[1], 0) > 0 else 1, x[1]))
        fused = _head + fused[200:]
    fused = fused[:topk]

    return items_of(conn, [pid for _s, pid in fused],
                    scores={pid: s for s, pid in fused}, explain=explain,
                    routes={'二字组': lex, '元数据': meta, '全文': ft, '数值': num,
                            '声律': pzs, '向量': vec})


def items_of(conn, pids, scores=None, explain=False, routes=None):
    """按给定篇序组装结果（问答层与极值/排序题共用同一份字段口径）。

    性能：一条 `WHERE pid IN (...)` 取回全部行再按传入顺序重组，取代「逐 pid 查一次」。
    （原实现对每个 pid 各发一条 SELECT，而本函数在一次问答里会被调用多次。）
    分块是为了不撞 SQLite 的宿主参数上限（默认 32766，旧版 999）。
    """
    scores = scores or {}
    routes = routes or {}
    pids = list(pids)
    if not pids:
        return []
    by_pid = {}
    for i in range(0, len(pids), 500):
        chunk = pids[i:i + 500]
        qs = ','.join('?' * len(chunk))
        for r in conn.execute(
                'SELECT pid,dynasty,author,cipai,title,sent_n,han_len,ping,ze,ze_ratio,scene,'
                'change,longest_len,threshold,source FROM poems WHERE pid IN (%s)' % qs, chunk):
            by_pid[r[0]] = r
    out = []
    for pid in pids:                        # 保持调用方给的顺序（排序题依赖它）
        r = by_pid.get(pid)
        if not r:
            continue
        item = {'pid': r[0], 'dynasty': r[1], 'author': r[2], 'cipai': r[3], 'title': r[4],
                'n_line': r[5], 'n_char': r[6], 'n_ping': r[7], 'n_ze': r[8], 'ze_ratio': r[9],
                'scene': r[10], 'change': r[11], 'longest_len': r[12], 'threshold': r[13],
                'source': r[14], 'score': round(scores.get(pid, 0.0), 4)}
        if explain:
            item['contrib'] = {name: round(d.get(pid, 0), 4) for name, d in routes.items()}
        out.append(item)
    return out


def cover_fields(spec):
    """问句里被查了**多个取值**的字段（这些取值都应在展示里露面）。

    主人实测：问「句脚是「灯」或者「声」的清词」时，展示的三句只覆盖了「灯」——
    条件解对了，但**举的例子没覆盖**，读者无法验证另一个取值到底有没有例。
    凡多值字段（≥ 2 个取值）一律要求「每个取值都有实例」。
    """
    out = {}
    for attr in ('tail', 'cipai', 'author', 'dynasty'):
        vs = _vals(spec, attr)
        if len(vs) >= 2:
            out[attr] = vs
    return out


def poem_has_value(conn, pid, attr, val):
    """该篇是否满足「attr=val」这一条（**只判这一条**，与其它条件无关）。"""
    if attr == 'tail':
        return bool(conn.execute('SELECT 1 FROM lines WHERE pid=? AND tail=? LIMIT 1',
                                 (pid, val)).fetchone())
    col = {'dynasty': 'dynasty', 'author': 'author', 'cipai': 'cipai'}[attr]
    row = conn.execute('SELECT %s FROM poems WHERE pid=?' % col, (pid,)).fetchone()
    return bool(row and (row[0] or '').strip() == val)


def count_for_value(conn, spec, attr, val):
    """把 spec 收窄到「attr 只取 val」后**独立复算**的真值篇数（用于「无例可举」的核实）。"""
    import copy
    s2 = copy.deepcopy(spec)
    setattr(s2, attr + '_any', [val])
    _finalize(s2)
    return count_hits(conn, s2)


def pick_covering(conn, spec, pool, cover, topk):
    """从候选池里挑展示篇：**先保证每个被查取值各有实例**，再按原排序补齐。

    返回 (chosen, eff_topk)；chosen 的条目与 `search` 的条目同构（含 score）。
    """
    need = sum(len(v) for v in cover.values())
    eff = min(len(pool), max(topk, need))
    chosen, seen = [], set()
    for attr in cover:
        for v in cover[attr]:
            if any(poem_has_value(conn, r['pid'], attr, v) for r in chosen):
                continue                       # 已露过面（同一篇可同时覆盖多个取值）
            for r in pool:
                if r['pid'] in seen:
                    continue
                if poem_has_value(conn, r['pid'], attr, v):
                    chosen.append(r)
                    seen.add(r['pid'])
                    break
    for r in pool:                             # 补齐到 eff 篇（保持原排序）
        if len(chosen) >= eff:
            break
        if r['pid'] not in seen:
            chosen.append(r)
            seen.add(r['pid'])
    return chosen[:eff], eff


def coverage_of(conn, blocks, cover):
    """统计展示篇里每个被查取值出现了几篇（0 篇的要**说清楚**）。"""
    out = {}
    for attr in cover:
        d = {}
        for v in cover[attr]:
            d[v] = sum(1 for b in blocks if poem_has_value(conn, b['pid'], attr, v))
        out[attr] = d
    return out


def main():
    ap = argparse.ArgumentParser(description='M6/M7 检索层（五路：二字组/全文/元数据/数值/声律模式）')
    ap.add_argument('--db', required=True)
    ap.add_argument('--query', required=True)
    ap.add_argument('--topk', type=int, default=5)
    ap.add_argument('--explain', action='store_true')
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    spec = parse_query(conn, args.query)
    print('查询理解：%s' % spec.describe())
    rows = search(conn, spec, args.topk, explain=args.explain)
    if not rows:
        print('未召回到符合条件的词作（可放宽条件）。')
        conn.close()
        return 1
    print('\n召回 %d 篇：' % len(rows))
    for i, r in enumerate(rows, 1):
        print('  [%d] %.4f %s·%s《%s》（%s）%d 句 / %d 字，仄 %d，仄声比例 %.1f%%，声情 %s'
              % (i, r['score'], r['dynasty'], r['author'], r['title'], r['cipai'], r['n_line'],
                 r['n_char'], r['n_ze'], r['ze_ratio'], r['scene']))
        print('      出处：%s' % r['pid'])
        if args.explain:
            print('      贡献：%s' % r['contrib'])
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())


_PZ_INLINE_RE = re.compile(r'平仄串为([平仄?？]{3,})|声律为「([平仄?？]{3,})」'
                            r'|声律模式是「([平仄?？]{3,})」')
# ⚠ 2026-10-03 修：旧式的**前置**边界（`(?:^|[，,、\s]|在|限|仅|只)`）挡掉了一整类问法——
#   生成器的「元数据」篇级条件把朝代写在**范围开头**，前面常跟着礼貌语：「请给出**清**，每一句…」
#   → 前置字是「出」，不是分隔符 → 朝代整条丢失（实测 Q0025 引擎命中 1393、真值只 139，答成
#   元曲里的篇）。现在只看**后置**边界：朝代后紧跟分隔符/机构后缀/句末，才算一次「提到」。
#   「句脚为「清」」这类**带引号**的会因后置是「」而自动排除。
_DYN_INLINE_RE = re.compile(r'(?<!全部)(清|宋|元)(?=[，,、；;：:。\s]|词|代|朝|曲|的|里|中|$)')


def _patch_parse(text, spec):
    """补两处解析缺口（2026-10-02 逐题审查实测）：
      ① 「平仄串为仄仄平仄仄平仄」这种**连写**形式：token 里混了「平仄串为」，
         过不了「整串只由平/仄/?组成」的判定 → 声律串整条丢失（范围被放大）。
      ② 「在宋，…」：朝代字前面是汉字「在」，被「前后不能是汉字」的边界规则挡掉 → 朝代丢失。
    """
    if not spec.pz:
        m = _PZ_INLINE_RE.search(text or '')
        if m:
            _pz = next(g for g in m.groups() if g)
            # 同上：句级算子已接管该声律串时不要再补（否则 ∃ 与 ∄ 打架）
            _lqp = (getattr(spec, 'line_q', None) or {}).get('pred')
            if not (_lqp and _lqp[0] == 'pz' and _lqp[1] == _pz):
                spec.pz = _pz
    # ⚠ 聚合/对比题里「宋词与清词」的宋/清是**组名**，不是检索限定——绝不补成筛选
    #   （既有门禁「聚合：组名不当成检索限定」就盯这一条；实测撞过一次）。
    #   ⚠ 2026-10-03 收紧：只在**分组维度就是朝代**时才算「组名」；分组维度是词人/词牌时，
    #     问句里的朝代仍是**真筛选**（实测 Q0057「在宋，…哪一个**词牌**的平均篇幅最少」，
    #     旧规则因 spec.agg 非空而丢掉「宋」→ 命中 1540、真值 462，整题作废）。
    _agg_gb = (spec.agg or {}).get('group_by')
    if not _vals(spec, 'dynasty') and _agg_gb != 'dynasty':
        # ⚠ 2026-10-03：**已被词人/词牌名覆盖的位置不算朝代**。实测 Q0434「**宁调元**，没有任何
        #   一句句脚是「曲」…」——「元」右邻是「，」，被右边界规则认成朝代 → 范围变成「元」，
        #   与词人「宁调元」自相矛盾 → 0 篇（真值 116 字的那一篇在清词里）。
        _cover = set()
        for _nm in (list(spec.author_any) + list(spec.cipai_any)
                    + list(getattr(spec, 'cleared_names', []) or [])):
            _st = 0
            while True:
                _j = (text or '').find(_nm, _st)
                if _j < 0:
                    break
                _cover.update(range(_j, _j + len(_nm)))
                _st = _j + 1
        _hits = [m.group(1) for m in _DYN_INLINE_RE.finditer(text or '')
                 if m.start() not in _cover]
        # ⚠ 占比题模板「占全部清词（或所限朝代）」里的「清」是**默认分母域**：
        #   范围自带朝代时用它，否则才回落到清词（与作答层的分母口径一致）。
        if not _hits and '全部清词' in (text or ''):
            _hits = ['清']
        for _d in _hits:
            if _d not in spec.dynasty_any:
                spec.dynasty_any.append(_d)
    return spec


def parse_query(conn, text):
    """对外入口：**挖空算子短语** → 内部规则解析 → 句级算子 → 解析补丁 → 算子认账。

    ⚠ 语义拆分（外部审查 P2-17）：入参 `text` 是**用户原话**，这里先记进 `spec.raw_question`
    （审计/日志用，永不被改写）；传给内部解析的是 `_mask_ops(text)`（挖空算子短语后的工作
    文本），它被存为 `spec.raw` 并用于词面检索（`route_bigram`）——这是**既有设计**：算子短语
    （「句脚是…」「每一句…」）本就不该参与词面匹配。两者现在各自有名、互不混淆。
    """
    spec = _parse_query_inner(conn, _mask_ops(text))
    spec.raw_question = text or ''
    parse_line_ops(text, spec)
    _patch_parse(text, spec)
    return _flag_ops(spec, text)
