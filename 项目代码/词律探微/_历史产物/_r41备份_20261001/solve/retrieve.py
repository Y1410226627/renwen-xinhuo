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
DYN = ('清', '宋', '元')
# 语料只含清/宋/元。问句明确指向语料外朝代时必须**拒答**，不能拿语义相近的篇凑数。
UNSUPPORTED_DYN = ('汉', '唐', '五代', '五代十国', '魏晋', '南北朝', '隋', '明', '金', '辽',
                   '先秦', '诗经', '楚辞', '汉朝', '唐朝', '宋朝以前')
MIN_NAME_LEN = 2            # 单字作者名（苏/袁…）参与匹配会把正文片段误当条件
UP = r'(?:高于|大于|多于|超过|超出|不低于|不少于|至少|≥|>=)'
DOWN = r'(?:低于|小于|少于|不足|不超过|不高于|至多|≤|<=)'
PZ_RE = re.compile(r'^[平仄?？]{3,}$')     # 声律模式：整串只由 平/仄/？（任意）组成
SCENES = {'后段上升': ('上升', '升高', '抬高'), '后段下降': ('下降', '降低', '走低'),
          '前后持平': ('持平', '不变', '平稳')}
# 提问虚词/意图词：抽词面时必须剔除，否则「想表达」「平仄」会被当成检索词
STOPWORDS = ('什么', '为什么', '为何', '怎么', '如何', '是否', '请问', '想问', '一下',
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
        self.tail_any = []             # 句脚字（可多个，取并集）
        self.tail_pz = None            # 句脚字的平仄（平/仄）
        self.pz = None                 # 声律模式（平仄串，? = 任意）
        self.scene = None              # 声情转向
        self.dynasty = None            # 单值快捷字段（由列表派生）
        self.author = None
        self.cipai = None
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
        self.raw = ''

    def describe(self):
        p = []
        dyn = _vals(self, 'dynasty')
        au = _vals(self, 'author')
        cp = _vals(self, 'cipai')
        tl = _vals(self, 'tail')
        if dyn:
            p.append('朝代=%s' % ' 或 '.join(dyn))
        if au:
            p.append('词人=%s' % ' 或 '.join(au))
        if cp:
            p.append('词牌=%s' % ' 或 '.join(cp))
        if self.pz:
            p.append('声律模式=%s' % self.pz)
        if self.scene:
            p.append('声情=%s' % self.scene)
        if tl:
            p.append('句脚字=%s' % ' 或 '.join(tl))
        if self.tail_pz:
            p.append('句脚平仄=%s' % self.tail_pz)
        if self.keywords:
            p.append('词面=%s' % '、'.join(self.keywords))
        lab = {'ze_min': '仄声比例≥%.1f%%', 'ze_max': '仄声比例≤%.1f%%', 'len_min': '字数≥%d',
               'len_max': '字数≤%d', 'sent_min': '句数≥%d', 'sent_max': '句数≤%d',
               'change_min': '变化≥%.1f', 'change_max': '变化≤%.1f', 'thr_min': '阈值≥%d',
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
AGG_HINT_RE = re.compile(r'(哪个|哪一位|哪位|哪一类|哪些|那个|谁|谁更|相对|对比|相比|比较|统计)'
                         r'|(更高|更大|更多|更低|更少|较多|较少|高些|低些)')
AGG_METRICS_LABEL = {'ze_ratio': '仄声占比', 'ping_ratio': '平声占比',
                     'han_len': '篇幅（字）', 'sent_n': '句数', 'share': '词作占比',
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
    r'(最多|最少|数量最多|篇数最多|词作最多|占比最多|占比最高|占最多|占比例最高|居首|排第一|最多的是|最少的是)')


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
    """极值／排序题 → 指标与方向。识别不了（没点名指标）就返回 None，**不猜**。"""
    up = next((w for w in EXTREME_UP if w in text), None)
    dn = next((w for w in EXTREME_DOWN if w in text), None)
    if not up and not dn:
        return None
    metric, hit = None, None
    for name, kws in EXTREME_METRIC_PAT:
        for k in kws:
            if k in text:
                metric, hit = name, k
                break
        if metric:
            break
    if metric is None:
        return None                      # 「哪首最长、谁写得最好」这类没指标的：不靠猜
    col, label, flip = ORDER_COLS[metric]
    if up and up in text:
        kind, word = 'max', up
    else:
        kind, word = 'min', dn
    if '句' in hit and '句脚' in text and metric in ('sent_n', 'longest_len'):
        return None                      # 「最长句是…」是行级题，不是篇级极值
    asc = (kind == 'min') != bool(flip)   # 反向指标（平声比例）要翻向
    cleaned = text.replace(hit, '，').replace(word, '，')
    return {'metric': metric, 'col': col, 'label': label, 'kind': kind, 'word': word,
            'dir': 'asc' if asc else 'desc', 'cleaned': cleaned}


def order_pids(conn, spec, topk=None):
    """按用户点名的指标取篇（严格排序）。列名来自 ORDER_COLS 白名单，不用用户串。"""
    if not spec.order_by:
        return []
    col = spec.order_col or ORDER_COLS[spec.order_by][0]
    where, args = _sql(spec)
    sql = ('SELECT p.pid, p.%s AS v FROM poems p WHERE %s ORDER BY p.%s %s, p.pid ASC'
           % (col, where, col, 'ASC' if spec.order_dir == 'asc' else 'DESC'))
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
    where, args = _sql(spec)
    asc = spec.order_dir == 'asc'
    agg = 'MIN' if asc else 'MAX'
    sql1 = 'SELECT %s(p.%s) FROM poems p WHERE %s' % (agg, col, where)
    v = conn.execute(sql1, args).fetchone()
    if not v or v[0] is None:
        return None
    val = v[0]
    sql2 = ('SELECT p.pid, p.dynasty, p.author, p.cipai, p.title, p.%s FROM poems p '
            'WHERE %s AND p.%s = ? ORDER BY p.pid ASC' % (col, where, col))
    ties = conn.execute(sql2, list(args) + [val]).fetchall()
    dyn = {}
    for r in conn.execute('SELECT dynasty, COUNT(1) FROM poems GROUP BY dynasty'):
        dyn[r[0]] = r[1]
    scope = ('全库（' + '、'.join('%s %d 首' % (k, v2) for k, v2 in sorted(dyn.items())) + '）')
    if _vals(spec, 'dynasty') or _vals(spec, 'author') or _vals(spec, 'cipai') or spec.rng:
        scope = '满足条件的 %d 篇' % scope_count(conn, where, args)
    return {'value': val, 'n_ties': len(ties), 'ties': ties, 'label': spec.order_label,
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
    for attr in ('dynasty', 'author', 'cipai', 'tail'):
        lst = _vals(spec, attr)
        setattr(spec, attr, lst[0] if len(lst) == 1 else None)
    spec.keywords = [k for k in spec.keywords if k not in CONNECTORS and len(k) >= 2]
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
    m = re.search(r'(清|宋|元)(?:代|朝|词|曲|人)', text)
    if m:
        out.append(m.group(1))
    else:
        m = re.search(r'(?<![\u4e00-\u9fff\u3400-\u4dbf])(清|宋|元)(?![\u4e00-\u9fff\u3400-\u4dbf])', text)
        if m:
            out.append(m.group(1))
    return out


def _unsupported_from_text(text):
    """语料外朝代（唐/汉……）：必须是独立 token，避免误伤「银汉」这类词句。"""
    for token in re.split(r'[\s，,、；;：:]+', text):
        t = token.strip()
        if not t:
            continue
        core = re.sub(r'(代|朝|词|诗|曲)$', '', t)
        if core in UNSUPPORTED_DYN and len(t) <= len(core) + 1:
            return t
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
    hits = []
    for d in DYN:
        for m in re.finditer(r'(%s)(?:代|朝|词|曲|人)?' % d, text):
            s, e = m.start(), m.end()
            suf = m.group(1) != m.group(0)        # 「清词/清代/清朝」带了后缀
            lh = text[s - 1] if s > 0 else ''
            rh = text[e] if e < len(text) else ''
            lone = not (is_hanzi(lh) or is_hanzi(rh))
            if suf or lone:
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


def parse_query(conn, text):
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
        # 对比题：「宋／清」是**组名**而不是检索限定，不能同时当朝代条件（否则两义相混）
        sp0.dynasty_any, sp0.dynasty = [], None
        sp0.cipai_any, sp0.cipai = [], None
        sp0.author_any, sp0.author = [], None
        sp0.keywords = []
        sp0.unparsed = []
        # 审查 B31 同类：**聚合层不用的东西不许留在「查询理解」里**，否则用户看到条件被列出来、
        # 实际统计时却没用到（静默不一致）。声情／数值阈值／句脚在聚合题里要么是「被测量的类别」
        # （share 指标），要么无意义；排序意图也不该出现在「谁更高」的题里。
        sp0.scene = None
        sp0.tail_any, sp0.tail_pz = [], None
        sp0.pz, sp0.rng = None, {}
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
        uns1 = _unsupported_from_text(text)
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
        uns = _unsupported_from_text(text)
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

    def take(pat, key, cast=float, scale=None):
        """在 rest 中找数值条件并摘除；返回是否命中。"""
        nonlocal rest
        m = re.search(pat, rest)
        if not m:
            return False
        v = cast(m.group(1))
        lo, hi = RNG_BOUNDS.get(key, (None, None))          # 审查 C17：与大模型路同口径
        if lo is not None and not (lo <= v <= hi):
            rest = rest.replace(m.group(0), ' ')
            return False
        spec.rng[key] = v * scale if scale else v
        rest = rest.replace(m.group(0), ' ')
        return True

    n_num = 0
    for pat, key in ((r'仄声比例\s*%s\s*(\d+(?:\.\d+)?)\s*%%?' % UP, 'ze_min'),
                     (r'仄声比例\s*%s\s*(\d+(?:\.\d+)?)\s*%%?' % DOWN, 'ze_max')):
        n_num += take(pat, key, float)
    for pat, key in ((r'(?:字数|篇幅)\s*%s\s*(\d+)' % UP, 'len_min'),
                     (r'(?:字数|篇幅)\s*%s\s*(\d+)' % DOWN, 'len_max'),
                     (r'句数\s*%s\s*(\d+)' % UP, 'sent_min'),
                     (r'句数\s*%s\s*(\d+)' % DOWN, 'sent_max'),
                     (r'变化\s*%s\s*(\d+(?:\.\d+)?)' % UP, 'change_min'),
                     (r'变化\s*%s\s*(\d+(?:\.\d+)?)' % DOWN, 'change_max'),
                     (r'(?:阈值|长句阈值)\s*%s\s*(\d+)' % UP, 'thr_min'),
                     (r'(?:阈值|长句阈值)\s*%s\s*(\d+)' % DOWN, 'thr_max')):
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
    m = re.search(r'句(?:脚|末字|尾字)\s*(?:字)?\s*(?:[=＝:：]|是|为|作|等于)?\s*[「『\'"]?([%s])' % _HAN_CLASS, rest)
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

    # 词人（最长匹配优先）
    for a in _names_longest_first(conn, 'authors', 'author'):
        if a in rest:
            spec.author_any.append(a)
            rest = rest.replace(a, ' ')
            break

    # 短语兜底：整串汉字、无分隔符、名字匹配后仍有剩余 ⇒ 这是正文片段而非结构化查询
    # （「风紧玉楼斜」里恰好含词牌「玉楼」）。但已有数值/声律/声情/朝代等结构化线索时不撤销。
    has_sep = bool(re.search(r'[\s，,、；;：:·？?！!。.…「」『』“”\"]', text))
    structured = bool(n_num or spec.dynasty_any or spec.pz or spec.scene
                      or spec.tail_any or spec.tail_pz)
    leftover = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]{2,}', rest)
    if (not keep_names) and (not has_sep) and leftover and (spec.author_any or spec.cipai_any) \
            and not structured:
        spec.author_any = []
        spec.cipai_any = []
        rest = text

    # 语料外朝代（必须是独立 token，避免误伤「银汉」这类词句）
    uns = _unsupported_from_text(text)
    if uns:
        spec.unsupported = uns

    # 朝代放最后（先整句取朝代，再把它从 rest 里摘掉，避免残留成词面）
    spec.dynasty_any += _dyn_from_text(rest)
    for pat in (r'(清|宋|元)(?:代|朝|词)',
                r'(?<![\u4e00-\u9fff\u3400-\u4dbf])(清|宋|元)(?![\u4e00-\u9fff\u3400-\u4dbf])'):
        m = re.search(pat, rest)
        if m:
            rest = rest.replace(m.group(0), ' ', 1)
            break

    # 剩余整串汉字作词面（保留整串，避免退化成短词匹配）；剔除提问虚词与连接词
    for w in list(STOPWORDS) + list(CONNECTORS):
        rest = rest.replace(w, ' ')
    spec.keywords = [c for c in re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]{2,}', rest) if c.strip()]
    return _finalize(spec)


def _sql(spec):
    """硬条件的 SQL 片段与参数（元数据 + 数值 + 声情 + 句脚 + 声律模式）。

    多值字段（并列/选择）用 `IN (...)` 取**并集**：「句脚是【灯】或者【声】」＝灯的 ∪ 声的。
    """
    where, args = [], []

    def one(col, vals):
        if not vals:                      # 空列表不能写成 IN ()（SQL 语法错/零行）
            return
        if len(vals) == 1:
            where.append('%s = ?' % col); args.append(vals[0])
        else:
            where.append('%s IN (%s)' % (col, ','.join('?' * len(vals)))); args.extend(vals)

    def any_line(expr, vals):
        where.append('EXISTS (SELECT 1 FROM lines l WHERE l.pid = p.pid AND %s IN (%s))'
                     % (expr, ','.join('?' * len(vals))))
        args.extend(vals)

    for attr, col in (('dynasty', 'p.dynasty'), ('author', 'p.author'), ('cipai', 'p.cipai')):
        one(col, _vals(spec, attr))
    if spec.scene:
        where.append('p.scene = ?'); args.append(spec.scene)
    for key, col, op in (('ze_min', 'p.ze_ratio', '>='), ('ze_max', 'p.ze_ratio', '<='),
                         ('len_min', 'p.han_len', '>='), ('len_max', 'p.han_len', '<='),
                         ('sent_min', 'p.sent_n', '>='), ('sent_max', 'p.sent_n', '<='),
                         ('change_min', 'p.change', '>='), ('change_max', 'p.change', '<='),
                         ('thr_min', 'p.threshold', '>='), ('thr_max', 'p.threshold', '<=')):
        if key in spec.rng:
            where.append('%s %s ?' % (col, op)); args.append(spec.rng[key])
    if spec.pz:
        pat = spec.pz.replace('?', '_').replace('？', '_')
        where.append("EXISTS (SELECT 1 FROM lines l WHERE l.pid = p.pid AND l.pz LIKE ?)")
        args.append('%' + pat + '%')
    tl = _vals(spec, 'tail')
    if tl:
        any_line('l.tail', tl)
    # 审查 C7：where/args 若错位，SQLite 有时会静默接受 → 这里按**占位符个数**自检。
    # （注意：多值条件是「一条片段多个 ?」，所以必须数 ? 而不是数片段条数。）
    assert sum(f.count('?') for f in where) == len(args), \
        'where/args 不平行（少写 args.extend 会整段错位，审查 C7）'
    if spec.tail_pz:
        # 句脚平仄 = 该句平仄串的最后一个字（单一来源：pz 串由引擎生成）
        where.append("EXISTS (SELECT 1 FROM lines l WHERE l.pid = p.pid AND substr(l.pz, -1, 1) = ?)")
        args.append(spec.tail_pz)
    return (' AND '.join(where) if where else '1=1'), args


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


def line_satisfies(pz, tail, spec):
    """某一句是否满足 spec 的**行级**条件。返回命中的条件名列表。

    行级条件只有三类：句脚字（`tail`，可多值）、句脚平仄（`tail_pz`）、声律模式（`pz`）。
    ——检索（SQL）与证据展示（选哪一句）必须用**同一份判定**，否则就会出现
    「问句脚字，答案却展示另一句」这类看起来没错、其实答非所问的错（2026-09-30 实测）。
    """
    hit = []
    if (tail or '') in _vals(spec, 'tail'):
        hit.append('句脚字')
    if spec.tail_pz and (pz or '')[-1:] == spec.tail_pz:
        hit.append('句脚平仄')
    if spec.pz and pz and pz_re(spec.pz).search(pz):
        hit.append('声律模式')
    return hit


def has_line_cond(spec):
    return bool(_vals(spec, 'tail') or spec.tail_pz or spec.pz)


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
    r = conn.execute('SELECT dynasty,author,cipai,scene,han_len,sent_n,ze_ratio,change,threshold '
                     'FROM poems WHERE pid=?', (pid,)).fetchone()
    if not r:
        return ['篇目不存在']
    dyn, au, cp, sc, hl, sn, zr, ch, th = r
    if _vals(spec, 'dynasty') and dyn not in _vals(spec, 'dynasty'):
        bad.append('朝代不符（%s∉%s）' % (dyn, '／'.join(_vals(spec, 'dynasty'))))
    if _vals(spec, 'author') and (au or '').strip() not in _vals(spec, 'author'):
        bad.append('词人不符（%s∉%s）' % (au, '／'.join(_vals(spec, 'author'))))
    if _vals(spec, 'cipai') and (cp or '').strip() not in _vals(spec, 'cipai'):
        bad.append('词牌不符（%s∉%s）' % (cp, '／'.join(_vals(spec, 'cipai'))))
    if spec.scene and sc != spec.scene:
        bad.append('声情不符（%s≠%s）' % (sc, spec.scene))
    for key, val, op, lab in (('ze_min', zr, '>=', '仄声比例'), ('ze_max', zr, '<=', '仄声比例'),
                              ('len_min', hl, '>=', '字数'), ('len_max', hl, '<=', '字数'),
                              ('sent_min', sn, '>=', '句数'), ('sent_max', sn, '<=', '句数'),
                              ('change_min', ch, '>=', '变化'), ('change_max', ch, '<=', '变化'),
                              ('thr_min', th, '>=', '阈值'), ('thr_max', th, '<=', '阈值')):
        if key not in spec.rng:
            continue
        want = spec.rng[key]
        got = val
        ok = (got is not None) and (got >= want if op == '>=' else got <= want)
        if not ok:
            bad.append('%s不符（%s %s %s 不成立）' % (lab, got, op, want))
    if has_line_cond(spec):
        rows = conn.execute('SELECT pz,tail FROM lines WHERE pid=?', (pid,)).fetchall()
        # 每个行级条件各用一条 EXISTS 语义（可由不同句分别满足，与 SQL 一致）
        tl = _vals(spec, 'tail')
        if tl and not any((x or '') in tl for _pz, x in rows):
            bad.append('无句脚字为 %s 的句子' % '／'.join(tl))
        if spec.tail_pz and not any((pz or '')[-1:] == spec.tail_pz for pz, _tl in rows):
            bad.append('无句脚为%s的句子' % spec.tail_pz)
        if spec.pz and not any(pz and pz_re(spec.pz).search(pz) for pz, _tl in rows):
            bad.append('无声律模式 %s 命中句' % spec.pz)
    return bad


def _norm(d):
    if not d:
        return {}
    mx = max(d.values()) or 1.0
    return {k: v / mx for k, v in d.items()}


def route_bigram(conn, text):
    """① 二字组路：FTS5(bigram) + BM25，**直接返回篇级分**（同篇取最高分行）。"""
    bs = bigrams(text)
    if not bs:
        return {}
    q = ' OR '.join('"%s"' % b for b in dict.fromkeys(bs))
    out = {}
    for pid, score in conn.execute(
            'SELECT l.pid, bm25(lines_bigram) FROM lines_bigram b JOIN lines l ON l.rowid=b.rowid '
            # 审查 P15：旧 LIMIT 20000 会把宽条件（如朝代=清 26,742 篇）**静默截断**，
# 且截断顺序由 bm25 决定（不确定）。全库 42 万句，这里放到 40 万即等于不截断。
'WHERE b.big MATCH ? ORDER BY bm25(lines_bigram) LIMIT 400000', (q,)):
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
                'WHERE b.big MATCH ? LIMIT 20000', (q,))
        except sqlite3.OperationalError:
            continue
        for (pid,) in rows:
            out[pid] = out.get(pid, 0.0) + 1.0
    return out


def route_numeric(conn, where, args, limit=20000):
    """④ 数值路：符合硬条件者按「仄声占比 + 篇幅」给排序信号（不代表优劣）。"""
    rows = conn.execute(
        'SELECT p.pid, p.ze_ratio, p.han_len FROM poems p WHERE %s LIMIT %d'
        % (where, limit), args).fetchall()
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


def search(conn, query, topk=5, weights=(0.40, 0.20, 0.15, 0.10, 0.15), explain=False):
    """五路检索 + 融合。返回按融合分排序的篇级结果。

    行级索引 → 篇级聚合：同一篇取**最高分行**计入语义/全文分（篇内不重复累加，
    否则长调天然占优）。
    """
    spec = parse_query(conn, query) if isinstance(query, str) else query
    if spec.unsupported:
        return []
    where, args = _sql(spec)
    hard = any([_vals(spec, 'dynasty'), _vals(spec, 'author'), _vals(spec, 'cipai'), spec.scene,
                spec.pz, _vals(spec, 'tail'), spec.tail_pz]) or bool(spec.rng)

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
    lex = route_bigram(conn, spec.raw) if spec.raw else {}
    ft = route_phrase(conn, spec.keywords) if spec.keywords else {}
    # 数值路只在用户明确给了数值条件时参与（否则会把「满足 1=1 的前 N 篇」灌进来）
    num = route_numeric(conn, where, args) if spec.rng else {}
    pzs = route_pz(conn, spec.pz) if spec.pz else {}
    meta = {pid: 1.0 for pid in scope_pids(conn, where, args)} if hard else {}

    w1, w2, w3, w4, w5 = weights
    cands = set(lex) | set(ft) | set(num) | set(meta) | set(pzs)
    if restrict is not None:
        cands &= restrict
    lex, ft, num, meta, pzs = _norm(lex), _norm(ft), _norm(num), _norm(meta), _norm(pzs)
    fused = []
    for pid in cands:
        s = (w1 * lex.get(pid, 0) + w2 * meta.get(pid, 0) + w3 * ft.get(pid, 0)
             + w4 * num.get(pid, 0) + w5 * pzs.get(pid, 0))
        fused.append((s, pid))
    fused.sort(key=lambda x: (-x[0], x[1]))
    fused = fused[:topk]

    return items_of(conn, [pid for _s, pid in fused],
                    scores={pid: s for s, pid in fused}, explain=explain,
                    routes={'二字组': lex, '元数据': meta, '全文': ft, '数值': num, '声律': pzs})


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
