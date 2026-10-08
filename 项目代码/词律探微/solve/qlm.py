# -*- coding: utf-8 -*-
"""qlm.py —— 「查询理解层」（大模型路）：把口语问句解成**结构化条件**，再由引擎校验与执行。

分工纪律（与 gen.py 一致，不越界）：
    大模型**只负责把话听明白**，不负责算数、不负责下结论、不负责引用；
    它给出的每个字段都要在这里过一遍**能落地校验**（必须能在数据库上复算）：
      · dynasty  ∈ {清,宋,元} 且库里有篇目；库外朝代（唐/汉…）→ 记 pending → 拒答；
      · author / cipai  必须在库里存在（不存在 → 丢弃并记明原因）；
      · tail  必须是**单个汉字**（含 CJK 扩展 A）；tail_pz ∈ {平,仄}；
      · pz  只能由 平/仄/？ 组成；scene ∈ {后段上升,后段下降,前后持平}；
      · rng  只认 10 个键，且数值在合理区间；
      · keywords **一律丢弃**（自由文本不许进 SQL）。
    校验不过的字段**不静默丢**：写进 `dropped`，由回答正文如实说明。
    无密钥 / 断网 / JSON 不合法 → 返回 None，调用方回落到规则解析（`retrieve.parse_query`）。

为什么需要它：规则解析对并列/口语（「句脚是「灯」或者「声」」「前段比后段更仄的」）不敏感，
2026-09-30 主人实测抓到「或者」被当词面条件、后半个条件被丢掉。大模型理解 + 引擎校验 = 既听得懂，
又不许它改数、不许它编条件。

用法（自检/演示）：
    python solve/qlm.py --db data/corpus.db --question "句脚是「灯」或者「声」的清词有哪些"
"""
import argparse
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aggregate                                              # noqa: E402
import retrieve                                               # noqa: E402

DYN_OK = ('清', '宋', '元')
RNG_KEYS = ('ze_min', 'ze_max', 'len_min', 'len_max', 'sent_min', 'sent_max',
            'change_min', 'change_max', 'thr_min', 'thr_max')
RNG_BOUNDS = {'ze_min': (0, 100), 'ze_max': (0, 100), 'len_min': (1, 500), 'len_max': (1, 500),
              'sent_min': (1, 80), 'sent_max': (1, 80), 'change_min': (-100, 100),
              'change_max': (-100, 100), 'thr_min': (1, 60), 'thr_max': (1, 60)}
SCENE_OK = ('后段上升', '后段下降', '前后持平')
SCENE_ALIAS = {'上升': '后段上升', '升高': '后段上升', '下降': '后段下降', '降低': '后段下降',
               '持平': '前后持平', '不变': '前后持平', '前段更高': '后段下降', '后段更高': '后段上升'}

# ---- 新增 schema 字段的枚举与边界（单一来源：validate 与「口语算子回填」共用）----
# ⚠ 2026-10-08 新增（外部审查 · 5 类 schema 缺口）：QSYSTEM 原来只有 dynasty/authors/
#   cipais/tail/tail_pz/pz/scene/rng 八个字段，模型**无法表达**题名（titles）、句级算子
#   （line_ops）、平仄全等（pz_exact）、篇内交集（tail_each）、句位奇偶（parity）、走向
#   一致性（consist）、语义检索词（semantic）→ 这些语义只能靠规则路兜底、或整条丢失。
#   下面把缺口的字段补进 schema，并把每个字段的**能落地校验**写在 `validate()` 里。
LINE_OP_QUANT = ('none', 'exists', 'forall', 'count')
LINE_OP_FIELD = ('tail', 'tail_pz', 'pz', 'pz_exact', 'len')
LINE_OP_OP = ('=', 'in', '>=', '<=')
COUNT_OP = ('>=', '=', '<=')
PARITY_ALIAS = {'奇': 'odd', '奇数': 'odd', '奇句位': 'odd', '奇数句位': 'odd', 'odd': 'odd',
                '偶': 'even', '偶数': 'even', '偶句位': 'even', '偶数句位': 'even', 'even': 'even'}
PARITY_SET = (0, 1)                       # 0=奇数句位(1,3,5…)；1=偶数句位（口径同 retrieve.l.idx%2）
SEM_MAX = 12                              # 语义检索词上限（**只作检索扩展，绝不进 SQL**）
SEM_LEN_MAX = 12                          # 单个检索词长度上限

SYSTEM = (
    '你是「词律探微」（清代词律声情研究助手）的**查询理解**模块。\n'
    '你的唯一任务：把研究者的自然语言提问，翻译成一个 JSON 对象，供检索程序执行。\n'
    '只输出这个 JSON 对象本身，不要解释、不要代码块、不要多余文字。\n'
    '\n'
    'JSON 字段（没有的写 null，列表写 []）：\n'
    '  "dynasty": 朝代，只能取 "清"、"宋"、"元"；语料不含别的朝代（如唐宋之外一律 null）。\n'
    '  "authors": 词人姓名列表（如 ["朱彝尊"]；不确定就写 []）。\n'
    '  "cipais":  词牌名列表（如 ["临江仙"]）。\n'
    '  "tail":    句脚字列表，每个元素必须是**一个字**（如 ["灯","声"]）。\n'
    '  "tail_pz": 句脚平仄，只能 "平" 或 "仄"。\n'
    '  "pz":      声律模式，只由「平」「仄」「？」组成且长度≥3（如 "仄仄平平仄"）。\n'
    '  "scene":   声情转向，只能 "后段上升"、"后段下降"、"前后持平"。\n'
    '  "rng":     数值条件对象，可用键：\n'
    '             ze_min/ze_max（仄声比例百分数）、len_min/len_max（汉字数）、\n'
    '             sent_min/sent_max（句数）、change_min/change_max（变化值）、\n'
    '             thr_min/thr_max（长句阈值）。如 {"ze_min": 45}。\n'
    '  "unparsed": 你无法映射成上述条件的短语列表（如实填写，不许硬凑）。\n'
    '  "order":  **极值／排序**意图（问「哪一首…最高/最低/最多/最长」时）。形如\n'
    '             {"metric":"ze_ratio"|"ping_ratio"|"han_len"|"sent_n"|"longest_len"|"change",\n'
    '              "dir":"max"|"min"}。不是极值题就写 null（千万不要把「最高」硬凑成条件）。\n'
    '  "pair":   **配对题**（问「找出几对…每个位置上的平仄都相同的两首词」时）写 true，\n'
    '             可选 "pair_dim":"tone"（平仄）或 "text"（字面）。不是配对题就写 null。\n'
    '             ★ 配对题**不要**填 pz／tail 等条件——它要的不是「筛篇」而是「配对」。\n'
    '  "agg":     **分组对比/统计**题专用（问「哪一类更高/更大/更多」时）。形如\n'
    '             {"group_by":"dynasty"|"author"|"cipai", "values":["宋","清"],\n'
    '              "metric":"ze_ratio"|"ping_ratio"|"han_len"|"sent_n"|"count"}。\n'
    '             ★ 若问句**没有组名**，只问「哪个/哪些 词人/词牌/朝代 出现最多、最常见、\n'
    '               数量最多」→ 写 {"group_by":"author"|"cipai"|"dynasty","values":null,\n'
    '               "extreme":"max"}（最少/最少见用 "min"）。\n'
    '             不是对比题就写 null。写了 agg 就**不要**再填 dynasty/authors/cipais\n'
    '             （那些是**组名**，不是检索限定）。\n'
    '  "titles":  **题名（词题）**列表。★ 务必分清：`cipais` 是**词牌**（如「蝶恋花」），\n'
    '             `titles` 是**词题**（如「四月一日感粤事」）——两者**不同**。\n'
    '             「蝶恋花·四月一日感粤事」要**同时**给 "cipais":["蝶恋花"] 与\n'
    '             "titles":["四月一日感粤事"]（「·」前是词牌，后是题名）。\n'
    '             正例：「蝶恋花·四月一日感粤事是谁写的」→ cipais=["蝶恋花"]、\n'
    '                  titles=["四月一日感粤事"]；反例：把「四月一日感粤事」放进 unparsed\n'
    '                  或 keyword（那样就查不到，因为题名不在正文里）。\n'
    '  "pz_exact": 整句平仄**全等**的串（如 "仄仄平平仄"）。\n'
    '             ★ 与 "pz" 的区别必须分清：`pz` 是**子串**（该模式出现在某一句里即可）；\n'
    '             `pz_exact` 是**整句完全相同**（那一句的平仄串与之逐位相等）。\n'
    '             正例：「整句平仄串正好是仄仄平平仄」→ "pz_exact":"仄仄平平仄"；\n'
    '             反例：「句里含仄仄平平仄」→ 用 "pz"（子串），**不要**写 pz_exact。\n'
    '  "tail_each": 句脚字列表，要求**每一句**的句脚都取自该列表（篇内**交集**语义）。\n'
    '             正例：「每一句句脚都是花或者草」→ ["花","草"]（每句都落在集合内，\n'
    '             与 "tail"（**存在**一句）不同）。不是这种问法就写 []。\n'
    '  "line_ops": **句级算子**列表（问「有几句…」「每一句…」「没有任何一句…」时）。\n'
    '             每个元素形如 {"quantifier":"none"|"exists"|"forall"|"count",\n'
    '               "field":"tail"|"tail_pz"|"pz"|"pz_exact"|"len",\n'
    '               "op":"="|"in"|">="|"<=", "value":<字符串或列表>,\n'
    '               "count_op":">="|"="|"<=", "count_value":<整数>}\n'
    '             （`count_op`/`count_value` **只在** quantifier="count" 时填。）映射示例：\n'
    '             · 「没有任何一句句脚为愁」→\n'
    '                 [{"quantifier":"none","field":"tail","op":"in","value":["愁"]}]\n'
    '             · 「每一句句脚都是愁」→ quantifier="forall"、op="in"、value=["愁"]\n'
    '             · 「至少两句句脚为愁」→ quantifier="count"、op="in"、value=["愁"]、\n'
    '                 count_op=">=" 、count_value=2\n'
    '             · 「正好三句句脚为愁」→ count_op="=" 、count_value=3\n'
    '             · 「句脚为愁的句子在 1 到 3 句之间」→ 用**两条**：\n'
    '                 count_op ">=" value 1，count_op "<=" value 3\n'
    '             反例：「句脚为愁」（不含量词＝**存在**一句）→ 写 "tail":["愁"]，\n'
    '              **不要**写 line_ops。\n'
    '  "parity":  句位**奇偶**：只能 "odd"（只要奇数句位的句：第 1、3、5…句）或\n'
    '             "even"（第 2、4、6…句）。不是问句位就写 null。\n'
    '  "consist": 声情**走向一致性**，只能 "后段上升"、"后段下降"、"前后持平"\n'
    '             （问「声情标注为 X 但实测前后段相反」时填该 X）。不是就写 null。\n'
    '  "semantic": **语义检索词**列表（**只当问句含主题/意象/情绪时才填**）。\n'
    '             正例：「写秋愁的词」→ ["秋日","秋景","悲秋","离愁","凄凉"]；\n'
    '                   「描写离愁的作品」→ ["离愁","别离","相思","羁旅"]。\n'
    '             ★ 这是**检索用词**，不是筛选条件（不会进 SQL）；\n'
    '               纯条件题（如「清 临江仙 仄声>45%」）一律写 []。\n'
    '             ★ 不许把问句里的**框架词**（「哪些」「哪首」「描写」「作品」「的词」\n'
    '               这类提问套话）放进来——只放**内容**词（意象/主题/情绪的同义词或\n'
    '               高度相关词）。\n'
    '\n'
    '规则：\n'
    '1) **并列/选择要拆成列表**：「句脚是灯或者声的」→ "tail": ["灯","声"]；\n'
    '   「清或宋的」→ 这类跨朝代并列写 "dynasty": "清" 并把「或宋」放进 "unparsed"。\n'
    '2) 只翻译**条件**，不要翻译「有哪些」「请列举」这类语气词，也不要输出任何检索词。\n'
    '3) 不许臆造条件：问句没提的字段一律 null/[]。\n'
    '4) 数字原样照抄（45% → 45）；**口语数字要换算**：「超过一半」→ ze_min 50、\n'
    '   「不到五十」→ len_max 50、「五到八句之间」→ sent_min 5 与 sent_max 8。\n'
    '5) 「哪个/哪些…最多/最常见」这类**没有组名**的组内极值，务必走 "agg"（见上），\n'
    '   不要塞进 "order"（那会把「哪一篇最高」和「哪一组最多」弄混）。\n'
    '6) 若用户消息给出【上一轮上下文】，可用它补全本轮问句的指代与省略（「那里面」「它的后段」\n'
    '   「改成宋词呢」）；**上下文里没出现过的条件不许臆造**；本轮问句若已自足，就忽略上下文。\n'
    '7) **词牌与题名要分清**：「词牌·题名」按 "·" 切开——前是词牌（cipais）、后是题名\n'
    '   （titles）。题名是词人自拟的词题，**不在正文里**，绝不能塞进 unparsed 或当作检索词。\n'
)


def _json_block(text):
    """从模型输出里抠出第一个配对完整的 JSON 对象（字符串内的括号不计数）。"""
    if not text:
        return None
    i = text.find('{')
    if i < 0:
        return None
    depth, in_str, esc = 0, False, False
    for j in range(i, len(text)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:j + 1])
                except ValueError:
                    return None
    return None


def _as_list(v):
    if v is None or v == '':
        return []
    if isinstance(v, (list, tuple)):
        return [x for x in v if x not in (None, '') and isinstance(x, str)]
    if isinstance(v, str):
        return [v]
    return []          # 数字/布尔等标量不是条件（审查 B32：「朝代=0」曾会被当成条件）


# ---- 新字段（line_ops）的落地校验：元素级，坏元素丢弃、不整条崩 ----
def _one_hanzi(v):
    return isinstance(v, str) and len(v) == 1 and retrieve.is_hanzi(v)


def _line_op_field_value(field, value):
    """按 `field` 归一化 `value` → (norm_value, pred)；非法返回 (原因, None)。"""
    if field == 'tail':
        raw = value if isinstance(value, (list, tuple)) else ([value] if value else [])
        vals = [str(x).strip() for x in raw if str(x).strip()]
        if not vals:
            return 'value 为空', None
        bad = [v for v in vals if not _one_hanzi(v)]
        if bad:
            return '句脚字=%s（不是一个汉字）' % '／'.join(bad), None
        return vals, (('tail', vals[0]) if len(vals) == 1 else ('tail_any', vals))
    if field == 'tail_pz':
        v = str(value).strip()
        if v not in ('平', '仄'):
            return '句脚平仄=%s（只能是平/仄）' % v, None
        return v, ('tail_pz', v)
    if field in ('pz', 'pz_exact'):
        v = str(value).strip()
        if not retrieve.PZ_RE.match(v):
            return '%s=%s（只能由平/仄/？组成且≥3 位）' % (field, v), None
        return v, (field, v)
    if field == 'len':
        if isinstance(value, (list, tuple)) and len(value) == 2:
            try:
                a, b = int(value[0]), int(value[1])
            except (TypeError, ValueError):
                return 'len=%s（不是整数区间）' % (value,), None
            if a < 1 or b < a:
                return 'len=%s（区间非法）' % (value,), None
            return [a, b], ('len', (a, b))
        return 'len=%s（须是 [下界,上界] 两个正整数）' % (value,), None
    return 'field=%s（不在枚举内）' % field, None


def _check_line_op(el):
    """校验单个 line_ops 元素 → (retrieve.line_q 片段, None) 或 (None, 原因)。"""
    if not isinstance(el, dict):
        return None, 'line_ops 元素不是对象'
    q = str(el.get('quantifier') or '').strip()
    field = str(el.get('field') or '').strip()
    op = str(el.get('op') or '').strip()
    if q not in LINE_OP_QUANT:
        return None, 'quantifier=%s（只能是 %s）' % (q, '/'.join(LINE_OP_QUANT))
    if field not in LINE_OP_FIELD:
        return None, 'field=%s（只能是 %s）' % (field, '/'.join(LINE_OP_FIELD))
    if op not in LINE_OP_OP:
        return None, 'op=%s（只能是 %s）' % (op, '/'.join(LINE_OP_OP))
    _norm, pred = _line_op_field_value(field, el.get('value'))
    if pred is None:
        return None, _norm
    if q == 'none':
        return {'op': '∄', 'pred': pred}, None
    if q == 'exists':
        return {'op': '∃', 'pred': pred}, None
    if q == 'forall':
        return {'op': '∀', 'pred': pred}, None
    # quantifier == count：必须有合法 count_op/count_value
    co = str(el.get('count_op') or '').strip()
    if co not in COUNT_OP:
        return None, 'count_op=%s（只能是 %s）' % (co, '/'.join(COUNT_OP))
    try:
        k = int(el.get('count_value'))
    except (TypeError, ValueError):
        return None, 'count_value=%s（不是整数）' % (el.get('count_value'),)
    if k < 0:
        return None, 'count_value=%s（不能为负）' % el.get('count_value')
    if co == '=':
        return {'op': '=k', 'pred': pred, 'k': k}, None
    if co == '>=':
        return {'op': '≥k', 'pred': pred, 'k': k}, None
    return {'op': '条数∈[a,b]', 'pred': pred, 'ka': 0, 'kb': k}, None


def _merge_count_range(lst):
    """把「≥N」与「≤M」两条（同谓词）合并成「条数∈[N,M]」（模型给区间时的常见写法）。"""
    for a in lst:
        if a.get('op') != '≥k':
            continue
        for b in lst:
            if b.get('op') == '条数∈[a,b]' and b.get('pred') == a.get('pred'):
                return {'op': '条数∈[a,b]', 'pred': a['pred'], 'ka': a['k'], 'kb': b['kb']}
    return None


# ---- 「口语算子回填」：规则路与模型路都**没给出** line_q 时，尽力从问句里补一条 ----
# 由来（understand_eval C3/C7 实测）：像「至少两句句脚为愁」「每一句整句平仄串正好是仄仄平平仄」
# 这类措辞，规则路不认（其规范措辞是「有 N 句以上」「每一句都整句平仄串正好是「…」」），
# 大模型又可能把算子片段如实塞进 unparsed 而没填 line_ops。这里做**最后一道尽力而为的回填**：
# 把少数「口语但语义确定」的句式改写成引擎的规范措辞，再复用 `retrieve.parse_line_ops`
# 解析（**单一来源**，不另写一套判定），避免「模型听懂了却当词面残片丢掉」。
_NORM_RXS = (
    (re.compile(r'至少\s*([0-9零一二三四五六七八九十百两]+)\s*句'), r'有\1句以上'),
    (re.compile(r'正好\s*([0-9零一二三四五六七八九十百两]+)\s*句'), r'正好有\1句'),
    (re.compile(r'恰好\s*([0-9零一二三四五六七八九十百两]+)\s*句'), r'正好有\1句'),
    (re.compile(r'每一句(?!都)'), '每一句都'),
    (re.compile(r'(整句平仄串(?:正好是|是|为)?)([平仄?？]{3,})'), r'\1「\2」'),
)


def normalize_ops(text):
    """口语句级算子 → 引擎规范措辞（尽力而为）。返回 (改写后文本, 被改写的原片段列表)。"""
    t = text or ''
    consumed = []

    def _repl(m, rep):
        consumed.append(m.group(0))
        return m.expand(rep)

    for rx, rep in _NORM_RXS:
        t = rx.sub(lambda m, _rep=rep: _repl(m, _rep), t)
    return t, consumed


def recover_line_ops(text):
    """从问句原文尽力回填句级算子 → {'line_q','pz_exact','tail_each','consumed'} 或 None。

    只在「规则路与模型路都没有 line_q」时由 `ask._absorb_model_extras` 调用；解析走
    `retrieve.parse_line_ops`（单一来源）。识别不出、或问句未被改写 → 返回 None（不硬凑）。
    """
    norm, consumed = normalize_ops(text)
    if not consumed or norm == (text or ''):
        return None
    tmp = retrieve.QuerySpec()
    retrieve.parse_line_ops(norm, tmp)
    if not (tmp.line_q or tmp.pz_exact or tmp.tail_each):
        return None
    return {'line_q': tmp.line_q, 'pz_exact': tmp.pz_exact,
            'tail_each': list(tmp.tail_each), 'consumed': consumed}


def validate(conn, obj, question=''):
    """把模型给的 JSON 校验成 QuerySpec。返回 (spec, dropped, notes)。"""
    dropped, notes = [], []
    spec = retrieve.QuerySpec()
    spec.raw = question
    spec.source = '大模型'
    spec.unparsed = [str(x) for x in _as_list(obj.get('unparsed'))]

    # 朝代：**宽容接受列表**（模型常把并列朝代写成列表）——但列表不能在检索层使用，
    # 它要么是「对比题的两个组」（交给 agg 处置），要么是模型自作主张（记 note）。
    dyn_list = [str(x).strip() for x in _as_list(obj.get('dynasty'))]
    ok_dyn = [d for d in dyn_list if d in DYN_OK]
    bad_dyn = [d for d in dyn_list if d not in DYN_OK]
    multi_dyn = []
    if len(dyn_list) >= 2 and len(ok_dyn) >= 2:
        multi_dyn = ok_dyn
        notes.append('朝代给了多个值（%s）：本系统不做跨朝代并列检索，'
                     '对比题请用 agg 字段；已按下文处置' % '／'.join(ok_dyn))
    elif len(ok_dyn) == 1:
        dyn = ok_dyn[0]
        n = conn.execute('SELECT COUNT(*) FROM poems WHERE dynasty=?', (dyn,)).fetchone()[0]
        if n:
            spec.dynasty_any = [dyn]
        else:
            dropped.append('朝代=%s（库里没有）' % dyn)
    if bad_dyn:                                   # 语料外朝代 → 走拒答路径
        # 不能循环覆盖、只留最后一个（审查 B17：问「唐诗与汉代」曾只报「汉」）
        spec.unsupported = '／'.join(bad_dyn)
        for d in bad_dyn:
            notes.append('朝代=%s 不在语料范围' % d)

    # 模型可能把 authors 写成显式 null、值放在 author 里（审查 B33）
    au = [str(x).strip() for x in _as_list(obj.get('authors') or obj.get('author'))]
    real = {r[0] for r in conn.execute('SELECT author FROM authors')}
    for a in au:
        if a in real:
            spec.author_any.append(a)
        else:
            dropped.append('词人=%s（库中没有此人）' % a)

    cp = [str(x).strip() for x in _as_list(obj.get('cipais', obj.get('cipai')))]
    realc = {r[0] for r in conn.execute('SELECT cipai FROM cipai')}
    for c in cp:
        if c in realc:
            spec.cipai_any.append(c)
        else:
            dropped.append('词牌=%s（库中没有此调）' % c)

    # ⚠ 2026-10-08 新增：**题名（词题）**。★ 题名是「题名存在性」收口（源头第二道；
    #   `ask.answer` 里已有一道兜底）。每个值必须在 `poems.title` 里 `LIKE '%值%'` 至少命中
    #   1 篇，否则丢弃——防模型把「问句描述」（如「忆梦中最长的」）当成题名塞进来，
    #   导致 `title LIKE` 0 命中 → 全条件 0 篇（实测主人踩过）。
    ti = [str(x).strip() for x in _as_list(obj.get('titles'))]
    for t in ti:
        try:
            row = conn.execute('SELECT 1 FROM poems WHERE title LIKE ? LIMIT 1',
                               ('%' + t + '%',)).fetchone()
        except Exception:
            row = None
        if row:
            if t not in spec.title_any:
                spec.title_any.append(t)
        else:
            dropped.append('题名=%s（语料标题中不存在）' % t)

    tl = [str(x).strip() for x in _as_list(obj.get('tail'))]
    for ch in tl:
        if len(ch) == 1 and retrieve.is_hanzi(ch):
            spec.tail_any.append(ch)
        else:
            dropped.append('句脚字=%s（不是一个汉字）' % ch)

    # 篇内交集（每一句句脚都取自该集合）：每个元素必须是**单个汉字**
    te = [str(x).strip() for x in _as_list(obj.get('tail_each'))]
    for ch in te:
        if _one_hanzi(ch):
            if ch not in spec.tail_each:
                spec.tail_each.append(ch)
        else:
            dropped.append('篇内交集字=%s（不是一个汉字）' % ch)

    tp = obj.get('tail_pz')
    if tp in ('平', '仄'):
        spec.tail_pz = tp
    elif tp:
        dropped.append('句脚平仄=%s（只能是平/仄）' % tp)

    pz = obj.get('pz')
    if pz:
        pzs = str(pz).strip()
        if retrieve.PZ_RE.match(pzs):
            spec.pz = pzs
        else:
            dropped.append('声律模式=%s（只能由平/仄/？组成且≥3 位）' % pzs)

    # 平仄串**全等**（与 pz 的子串语义互斥）：只由 平/仄/？ 组成且长度≥3
    pze = obj.get('pz_exact')
    if pze:
        pzv = str(pze).strip()
        if retrieve.PZ_RE.match(pzv):
            spec.pz_exact = pzv
        else:
            dropped.append('平仄全等串=%s（只能由平/仄/？组成且≥3 位）' % pzv)

    sc = obj.get('scene')
    if sc:
        sc = SCENE_ALIAS.get(str(sc).strip(), str(sc).strip())
        if sc in SCENE_OK:
            spec.scene = sc
        else:
            dropped.append('声情=%s（只能是后段上升/后段下降/前后持平）' % sc)

    # 句位奇偶：odd→0（奇数句位 1,3,5…）、even→1（偶数句位）；口径同 retrieve `l.idx % 2`
    pa = obj.get('parity')
    if pa:
        key = PARITY_ALIAS.get(str(pa).strip(), str(pa).strip().lower())
        if key == 'odd':
            spec.parity = 0
        elif key == 'even':
            spec.parity = 1
        else:
            dropped.append('句位奇偶=%s（只能是 odd/even）' % pa)

    # 走向一致性：「声情标注为 X 但实测前后段相反」——与规则路口径一致地**同时**标注 scene
    cs = obj.get('consist')
    if cs:
        cs = SCENE_ALIAS.get(str(cs).strip(), str(cs).strip())
        if cs in SCENE_OK:
            spec.consist = cs
            if not spec.scene:
                spec.scene = cs
        else:
            dropped.append('一致性=%s（只能是后段上升/后段下降/前后持平）' % cs)

    rng = obj.get('rng') or {}
    if isinstance(rng, dict):
        for k, v in rng.items():
            if v is None or v == '':        # 模型常把所有键都列出来、没给的写 null
                continue
            if k not in RNG_KEYS:
                dropped.append('数值条件 %s（不认识）' % k)
                continue
            try:
                f = float(v)
            except (TypeError, ValueError):
                dropped.append('数值条件 %s=%s（不是数字）' % (k, v))
                continue
            lo, hi = RNG_BOUNDS[k]
            if not (lo <= f <= hi):
                dropped.append('数值条件 %s=%s（超出合理区间 %s–%s）' % (k, v, lo, hi))
                continue
            spec.rng[k] = int(f) if f.is_integer() and k.startswith(('len', 'sent', 'thr')) else f
    elif rng:
        dropped.append('rng 字段不是对象')

    # ---- 句级算子（line_ops）：逐个元素落地校验，坏元素丢弃并记明（不整条崩）----
    lo = obj.get('line_ops')
    valid_lq = []
    if isinstance(lo, list):
        for el in lo:
            lq1, why = _check_line_op(el)
            if lq1 is None:
                dropped.append('句级算子（%s）' % why)
            else:
                valid_lq.append(lq1)
    elif lo:
        dropped.append('line_ops 字段不是列表')
    if valid_lq:
        spec.line_q = valid_lq[0]
        if len(valid_lq) > 1:
            _merged = _merge_count_range(valid_lq)
            if _merged is not None:
                spec.line_q = _merged
                notes.append('句级算子按「区间」合并（≥%s 与 ≤%s）'
                             % (_merged['ka'], _merged['kb']))
                if len(valid_lq) > 2:
                    notes.append('句级算子多于两条，已按区间合并前两条，其余忽略')
            else:
                notes.append('句级算子一次只支持一条，已取其第一条，其余忽略')

    # ---- 语义检索词（semantic）：**只作检索扩展，绝不进 SQL** ----
    # 每项长度 1~12、去重、最多 SEM_MAX 项；不合法项丢弃并记明。
    sm = _as_list(obj.get('semantic'))
    _terms = []
    for t in sm:
        t = str(t).strip()
        if not (1 <= len(t) <= SEM_LEN_MAX):
            dropped.append('语义检索词=%s（长度须在 1~%d）' % (t, SEM_LEN_MAX))
            continue
        if t not in _terms:
            _terms.append(t)
    if len(_terms) > SEM_MAX:
        notes.append('语义检索词过多，只取前 %d 个' % SEM_MAX)
        _terms = _terms[:SEM_MAX]
    if _terms:
        spec.semantic = _terms        # 语义扩展词（QuerySpec 已有该槽位；检索层并入全文召回，不进 SQL）

    for k in obj:
        if k not in ('dynasty', 'authors', 'author', 'cipais', 'cipai', 'tail', 'tail_pz',
                     'pz', 'scene', 'rng', 'unparsed', 'agg', 'order', 'sort', 'pair',
                     'pair_dim', 'titles', 'pz_exact', 'tail_each', 'line_ops', 'parity',
                     'consist', 'semantic'):
            notes.append('模型多给的字段 %s 已忽略' % k)

    # 分组对比（聚合）题：组名同样要**逐个在库上验**（落不了库的进 dropped）
    ag = obj.get('agg')
    if isinstance(ag, dict) and ag:
        gb = str(ag.get('group_by') or '').strip()
        mt = str(ag.get('metric') or 'ze_ratio').strip()
        # ⭐ 组内极值：「哪个词人/词牌…最多」——问句里没有组名，靠 extreme 标记方向
        _extreme = str(ag.get('extreme') or '').strip().lower() or None
        if _extreme not in ('max', 'min'):
            _extreme = None
        vals = [str(x).strip() for x in _as_list(ag.get('values'))]
        # 模型常把组名放错地方（写了 agg 却把 ["宋","清"] 放进 dynasty）——
        # 宽容：按 group_by 从对应字段里回填，但要经库上逐个校验后才生效。
        if not vals:
            vals = {'dynasty': multi_dyn or spec.dynasty_any,
                    'author': [a for a in au if a in real],
                    'cipai': [c for c in cp if c in realc]}.get(gb, [])
            if vals:
                notes.append('agg.values 未给，已按 %s 从问句解析的组名回填（%s）'
                             % (gb, '／'.join(vals)))
        if gb not in aggregate.GROUPS:
            dropped.append('agg.group_by=%s（只能是 dynasty/author/cipai）' % gb)
        elif mt not in aggregate.METRICS:
            dropped.append('agg.metric=%s（只能是 ze_ratio/ping_ratio/han_len/sent_n/share/count）' % mt)
        elif len(vals) < 2 and _extreme:
            # ⭐ **组内极值**：没有组名是这类问法的**正常形态**（「哪个词人的词最多」）。
            #    只清空 group_by 自己那一维的筛选（避免把「作者=某某」当限定），
            #    其它维度（朝代/词牌/句脚…）**照旧当筛选条件**——这一点很关键：
            #    「句脚为平 清 临江仙…哪个词人最多」里的 清/临江仙/句脚平 全是筛选。
            spec.agg = {'group_by': gb, 'values': None, 'metric': mt, 'text': question,
                        'extreme': _extreme, 'note': ''}
            if gb == 'author':
                spec.author_any, spec.author = [], None
            elif gb == 'cipai':
                spec.cipai_any, spec.cipai = [], None
            elif gb == 'dynasty':
                spec.dynasty_any, spec.dynasty = [], None
            notes.append('按%s分组做**组内极值**统计（取%s）'
                         % (gb, '最多' if _extreme == 'max' else '最少'))
        elif len(vals) < 2:
            dropped.append('agg.values（对比题至少要两个组；组内极值请把 extreme 写成 max 或 min）')
        else:
            col = {'dynasty': 'dynasty', 'author': 'author', 'cipai': 'cipai'}[gb]
            ok = []
            for v in vals:
                n = conn.execute('SELECT COUNT(*) FROM poems WHERE %s=?' % col, (v,)).fetchone()[0]
                if n:
                    ok.append(v)
                else:
                    dropped.append('对比组 %s=%s（库里没有）' % (gb, v))
            if len(ok) >= 2:
                spec.agg = {'group_by': gb, 'values': ok, 'metric': mt, 'text': question,
                            'extreme': None, 'note': ''}
                # 组名不是检索限定：清空单值字段，避免两义相混
                spec.dynasty_any, spec.dynasty = [], None
                spec.author_any, spec.author = [], None
                spec.cipai_any, spec.cipai = [], None
                spec.keywords = []
            else:
                dropped.append('agg（可比的组不足两个，未启用分组统计）')
    elif ag:
        dropped.append('agg 字段不是对象')

    # 极值／排序意图（「哪一首…最高/最低」）：**指标走白名单**，方向只认 max/min。
    # ⚠ 实测踩过（2026-09-30 主人第七炮续）：模型只听了「词人=高旭」、**没听出「最高」**，
    # 而 `ask.understand` 当时只给朝代/语料外朝代/对比题加了安全网，没给排序加——
    # 于是规则路已识别的排序被丢掉，答案又从「极值篇」退回「融合排序最前者」。
    # 这里接受模型给的排序（白名单校验），**模型没给也不打紧**：调用方会用规则解析补回。
    od = obj.get('order', obj.get('sort'))
    if isinstance(od, dict) and od:
        mt = str(od.get('metric') or '').strip()
        dv = str(od.get('dir') or 'max').strip().lower()
        dv = {'high': 'max', 'desc': 'max', 'descending': 'max', '最高': 'max', '取高': 'max',
              'low': 'min', 'asc': 'min', 'ascending': 'min', '最低': 'min', '取低': 'min'}.get(dv, dv)
        if mt not in retrieve.ORDER_COLS:
            dropped.append('排序指标=%s（只能是 %s）'
                           % (mt, '／'.join(retrieve.ORDER_COLS)))
        elif dv not in ('max', 'min'):
            dropped.append('排序方向=%s（只能是 max/min）' % dv)
        else:
            col, label, flip = retrieve.ORDER_COLS[mt]
            asc = (dv == 'min') != bool(flip)
            spec.order_by, spec.order_col = mt, col
            spec.order_dir, spec.extreme = ('asc' if asc else 'desc'), dv
            spec.order_label, spec.order_src = label, '大模型'
    elif od:
        dropped.append('order 字段不是对象')

    # 配对题（「找出几对…平仄都相同的两首词」）：这不是「筛篇」而是「配对」，绝不能允许
    # 把问句本身当成词面/声律条件（实测：旧版从问句里捏出「声律模式=平仄平仄平仄平仄」）。
    # 本层只认「pair=true」这个声明；真正的判定量（全篇平仄串）由 `pairing` 模块算，
    # 模型没听出来也不打紧——`ask.understand` 会用规则路补回。
    if obj.get('pair'):
        dim = str(obj.get('pair_dim') or 'tone').strip().lower()
        dims = ('tone',) if dim in ('tone', 'pz', 'ping_ze', '声调', '平仄') else \
            ('text',) if dim in ('text', '字面', '用字', '字词') else ('tone',)
        if dim not in ('tone', 'pz', 'ping_ze', '声调', '平仄', 'text', '字面', '用字', '字词'):
            dropped.append('配对维度=%s（只能是 tone/text）' % dim)
        spec.pair = {'dims': dims, 'n_frame': 1}
        spec.pair_label = '全篇逐位平仄完全相同' if dims == ('tone',) else '不支持的维度'
        spec.keywords = []
    return retrieve._finalize(spec), dropped, notes


def parse(conn, llm, question, temperature=0.0, max_tokens=400, context=None):
    """大模型理解问句。失败一律返回 None（调用方回落规则解析）。

    `context`（可选）：上一轮「问句＋解析」摘要（多轮指代补全用）。它只是**提示的一部分**，
    模型据此补出的每个字段仍然要走 `validate()` 的逐字段落地校验——上下文不会成为
    「绕过校验」的通道。
    """
    if not (llm and llm.available()):
        return None
    # 流式 + **见到完整 JSON 即断开**：理解路的输出就是一个小 JSON 对象，
    # 实测首字 0.34~0.47 秒、完整对象约 1.6~2.2 秒返回，且不必为多余的尾巴继续等。
    kw = {'temperature': temperature, 'max_tokens': max_tokens}
    try:
        _sig = llm.chat.__code__.co_varnames
        if 'expect_json' in _sig:
            kw['expect_json'] = True
    except Exception:
        pass
    user = '问句：%s' % question
    if context:
        user = ('【上一轮上下文】%s\n（本轮问句若含指代/省略——如「那里面呢」「它的后段呢」——'
                '请结合上下文补全；本轮问句若已自足，则忽略上下文。）\n%s' % (context, user))
    raw = llm.chat([{'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': user}], **kw)
    obj = _json_block(raw)
    if obj is None:
        return None
    spec, dropped, notes = validate(conn, obj, question)
    spec.source = '大模型 %s' % (getattr(llm, 'name', '') or '未知模型')
    return {'spec': spec, 'dropped': dropped, 'notes': notes,
            'model': getattr(llm, 'name', '') or '未知模型', 'raw': raw or ''}


def main():
    ap = argparse.ArgumentParser(description='查询理解（大模型路）：问句 → 结构化条件（引擎校验）')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--question', required=True)
    ap.add_argument('--provider', default=None)
    args = ap.parse_args()
    import llm as L
    conn = sqlite3.connect(args.db)
    client = L.LLM(provider=args.provider)
    print('模型：%s（可用=%s）' % (client.name or '无', client.available()))
    rs = parse(conn, client, args.question)
    if rs is None:
        print('大模型不可用或输出不是合法 JSON → 规则解析：%s'
              % retrieve.parse_query(conn, args.question).describe())
        return 1
    print('大模型原始输出：%s' % rs['raw'])
    print('校验后条件：%s' % rs['spec'].describe())
    print('丢弃项：%s' % (rs['dropped'] or '无'))
    print('提示：%s' % (rs['notes'] or '无'))
    print('未理解片段：%s' % (rs['spec'].unparsed or '无'))
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
