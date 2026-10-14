# -*- coding: utf-8 -*-
"""gen.py —— 「说法层」：让国产大模型把**引擎算好的事实**写成研究性叙述 / 论证草稿。

分工（这是本项目的核心纪律）：
    引擎（prosody/corpus）→ 算数字；检索（retrieve/evidence）→ 取证据与原文；
    **大模型（本模块）** → 只负责把它写成通顺的话；护栏（guard/safety）→ 逐行核对。

所以本模块的产出**不是「答案」**，而是「**表述**」：
    一律先经 `guard.verify()`（数字有出处 / 引文逐字 / 边界声明 / 引用落地）
    与 `safety.check()`（内容安全）；**任一不过就整段丢弃**，
    由调用方回落到确定性模板。宁可话糙，不可话说错。

用法（命令行等价）：
    python solve/gen.py --db data/corpus.db --question "清 临江仙 仄声比例高于45%"
    python solve/gen.py --db data/corpus.db --question "清 临江仙 仄声比例高于45%" --argument
"""
import argparse
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import guard                                                  # noqa: E402
import safety                                                 # noqa: E402

SYSTEM = (
    '你是「词律探微」的解释层，只负责把给定事实（FACTS）写成通顺的研究性说明。\n'
    '硬规则（违反任何一条，稿件都会被程序丢弃）：\n'
    '1) 只能使用 FACTS 里出现过的数字，**一个都不许自己算、四舍五入或补充**；\n'
    '2) 引用篇目必须写成 [E1]、[E2] 这样的标记，且只能引用 FACTS 里给出的编号；\n'
    '3) 要引词句时，必须**逐字照抄** FACTS 中「原文：」后面的整句，并用中文引号「」括起；\n'
    '4) 不得引入 FACTS 之外的任何史实、生平、版本或他人评价；\n'
    '5) 不得判断作品优劣，不得推测作者心理或创作意图；\n'
    '6) 不要输出表格、代码块、Markdown 标题或项目符号；\n'
    '7) 篇幅控制在 150—300 字，语气克制、学术化；\n'
    '8) 「【查询条件（唯一权威）】」里列出什么条件，就只说什么条件——'
    '提问里出现了但它没被解析进去（比如并列只说了一半），**不得提及、不得补充、不得推测**。'
)
TASK_NARRATE = (
    '请写一段面向研究者的说明：先用一句话点明这批结果的共同特征，再举 1—2 个具体篇目为例'
    '（带 [E#] 与必要数字），最后说明这些数字只在形式与声调层面成立。'
)
TASK_ARGUMENT = (
    '请写一段研究论证草稿，分四层写（用「主张：」「证据：」「可能的反证：」「局限：」开头）：'
    '主张（这批篇目在声律形式上的共性）／证据（引 FACTS 的数字与篇目，带 [E#]）／'
    '可能的反证（哪些情况会让这个形式规律不成立）／局限（本系统只提供形式层证据）。'
)

# ⭐ 2026-10-09 新增（主人实测）：「文意解读」——内容/情感类问题的**生成式回答**。
#   定位：与 produce()（形式层说明/论证）并列的第二条说法通道。
#   为什么要有它：主人要的是「大模型能理解、原材料在数据中能找到的问题，就答出来」——
#   问「主要内容与思想感情是什么」，原文就在证据块里，不该只回一句「请自行判读」。
#   纪律不变：只依据材料（原文 + 引擎数字）、标注「非事实结论」、过四道护栏、不过即丢弃。
SYSTEM_READ = (
    '你是「词律探微」的**文意解读层**：基于给定的原文与事实，回答用户关于词作内容、'
    '意境与思想感情的问题。\n'
    '硬规则（违反任何一条，稿件都会被程序丢弃）：\n'
    '1) 只依据材料中的原文与数据作答，**不得引入材料之外的情节、史实、生平、版本或他人评价**；\n'
    '2) 引用词句必须**逐字照抄**材料里「原文：」后的整句，并用**双引号“…”**括起'
    '（护栏按「模型引文」核验：字字都要能在原文里找到，漏抄句末标点不影响）；\n'
    '3) 不得自己编造数字；要提数字时只能照抄材料里已有的；\n'
    '3.1) **不得从题名推断任何数字**：如「望夜」「中秋」这类词**不得**脑补成"十五""八月十五"'
    '等日期——材料没写明的日期一律不提；\n'
    '4) 解读保持克制（用「可理解为」「似传达出」「或寄寓」这类措辞），不作事实断言、不判优劣；\n'
    '5) **把「原文事实」与「解释推断」分开**：引原文、报数字是事实层面；对情绪/寓意的判断'
    '要让读者看得出是**推断**；**有争议处给出不止一种理解**（如「既可理解为…，也可理解为…」），'
    '不把一种解读说成唯一答案；\n'
    '6) 直接回答用户想知道的层面；材料不足以判断时，明说「据现有原文不足以判断……」，不要硬猜；\n'
    '7) 若【问句】有一部分与词作内容/情感无关（如礼貌语、杂问），忽略即可；'
    '若整句都无法基于材料回应，只输出：NO_READ\n'
    '8) 篇幅 100—260 字，连续段落，不要表格 / 标题 / 项目符号。'
)
TASK_READ_FULL = (
    '用户在【问句】里对词作提出了内容 / 情感层面的问题。请基于原文写出解读：'
    '先概括内容画面，再谈情绪与思想感情的走向（引 1—2 处原文关键句作为依据）。'
)
TASK_READ_PARTS = (
    '用户的【问句】里，以下片段未被系统转换为检索条件：\n  · %s\n'
    '请判断其中**哪些是对上述词作或声律数据的真问题**，基于材料逐一回应；'
    '无法回应的部分略过即可；若全部都无法回应，只输出：NO_READ'
)


# ════════════════════════════════════════════════════════════════════════════════
# 结构化论证（2026-10-13：论证稿结构化 + 输出契约）
# --------------------------------------------------------------------------------
# 由来：自查发现我们的「论证辅助」
#   ① 「本质是切换任务提示，生成短篇四层草稿」——**没有独立可编辑的论证稿实体**；
#   ② 「数字曾出现，不等于它支持当前句子的具体论断」——护栏的软肋。
# 吸收：把论证从「一段散文」升级为**结构化 JSON**，并对每条分论点强制要求
#   · bridge（从形式到解释的**桥梁**——防止把形式事实直接说成情感结论）；
#   · assessment（评估态四值——**明说自己有多确信**）；
#   · alternatives（替代解释）与 gaps（缺证）——**承认不确定性**。
# 纪律不变：仍只依据 FACTS；仍过四道护栏；**结构校验或护栏任一不过即整段丢弃**，
#   调用方回落既有模板。本模块默认路径（narrate）**逐字未改**，故对既有行为零影响。
# ════════════════════════════════════════════════════════════════════════════════

# 评估态四值（四态 assessment 枚举）：支持 / 混合 / 证据不足 / 未决
ASSESSMENTS = ('supported', 'mixed', 'insufficient', 'unresolved')

# ════════════════════════════════════════════════════════════════════════════════
# 输出失败码（2026-10-13：把「为什么被拒」变成机器可判的枚举）
# --------------------------------------------------------------------------------
# 她那边有约 30 个固定失败码，把「模型输出为什么被拒」变成**机器可判、可统计、可回查**的枚举，
# 而不是一句自由文本。我们此前只回 `problems`（人话列表），无法聚合诊断。
# 这里补齐同一层：`problems` 仍是人话（界面用），`codes` 是枚举（审计/统计用）。
# ════════════════════════════════════════════════════════════════════════════════
FAILURE_CODES = frozenset({
    # —— 结构化解析 ——
    'output_not_json',          # 不是合法 JSON
    'output_not_object',        # 顶层不是 JSON 对象
    'missing_thesis',           # 缺总论点
    'missing_claims',           # claims 缺失或为空
    'too_many_claims',          # 分论点超上限
    'claim_not_object',         # 分论点不是对象
    'missing_claim',            # 分论点缺 claim
    'missing_bridge',           # 缺桥梁（形式→解释）
    'invalid_assessment',       # 评估态不在四值内
    'gaps_required',            # 证据不足/未决却未给缺证
    'unknown_evidence_anchor',  # 引用了不存在的 [E#]
    'missing_limitations',      # 缺局限声明
    # —— 护栏 ——
    'unsafe_content',           # 内容安全规则命中
    'number_without_source',    # 数字无出处
    'citation_not_verbatim',    # 引文未逐字落地
    'boundary_missing',         # 缺类型化边界声明
    'unsupported_claim',        # 无据认账
    # —— 运行时 ——
    'model_unavailable',        # 无密钥 / 未联网
    'generation_incomplete',    # 模型无返回 / 截断
    'output_validation',        # 兜底（未归类的校验失败）
})

# `problems` 文案 → 失败码 的归类规则（按关键词，最长匹配优先）
_PROBLEM_CODE_RULES = (
    ('不是合法 JSON', 'output_not_json'),
    ('顶层不是 JSON 对象', 'output_not_object'),
    ('缺少 thesis', 'missing_thesis'),
    ('claims 必须是非空数组', 'missing_claims'),
    ('claims 超过上限', 'too_many_claims'),
    ('不是对象', 'claim_not_object'),
    ('缺少 claim', 'missing_claim'),
    ('缺少 bridge', 'missing_bridge'),
    ('assessment 非法', 'invalid_assessment'),
    ('gaps 不得为空', 'gaps_required'),
    ('引用了不存在的证据', 'unknown_evidence_anchor'),
    ('缺少 limitations', 'missing_limitations'),
    ('内容安全规则', 'unsafe_content'),
    ('数字无出处', 'number_without_source'),
    ('引文', 'citation_not_verbatim'),
    ('边界', 'boundary_missing'),
    ('中文数字无出处', 'number_without_source'),
    ('比例与证据块数字不自洽', 'number_without_source'),
    ('大模型不可用', 'model_unavailable'),
    ('大模型无返回', 'generation_incomplete'),
)


def classify_failures(problems):
    """把人话 `problems` 归类成**失败码**（去重、保序）。未归类者记 `output_validation`。"""
    codes = []
    for p in (problems or []):
        hit = None
        for kw, code in _PROBLEM_CODE_RULES:
            if kw in p:
                hit = code
                break
        code = hit or 'output_validation'
        if code not in codes:
            codes.append(code)
    return codes


# ════════════════════════════════════════════════════════════════════════════════
# 锚点机制（2026-10-13：模型只写锚点，程序填回冻结内容）
# --------------------------------------------------------------------------------
# 她那边让模型**不逐字复述固定内容**（易出错），只写锚点 `@facts` / `@evidence`，
# 由**程序**把冻结的事实/证据填回去——「模型转述出错」这一类问题从根上消失。
# 我们这里补同一机制：正文里出现锚点即被替换为程序冻结的内容，并记录替换了哪些。
# ════════════════════════════════════════════════════════════════════════════════
ANCHOR_FACTS = '@facts'
ANCHOR_EVIDENCE = '@evidence'


def _evidence_text(res):
    """把证据块渲染成**程序冻结**的清单（锚点 `@evidence` 展开用）。"""
    out = []
    for b in (res.get('blocks') or []):
        out.append('[%s] %s·%s《%s》：%d 句 / %d 字，平 %d、仄 %d，仄声比例 %s%%，声情 %s'
                   % (b['eid'], b.get('dynasty') or '', b.get('author') or '',
                      b.get('title') or b.get('cipai') or '', b.get('sent_n') or 0,
                      b.get('han_len') or 0, b.get('ping') or 0, b.get('ze') or 0,
                      _num(b.get('ze_ratio')), b.get('scene') or '—'))
        for L in (b.get('lines') or []):
            out.append('    [%s] 第 %d 句 原文：%s' % (b['eid'], L.get('seq', L['idx'] + 1),
                                                     L['text']))
    return '\n'.join(out) if out else '（本轮没有召回到任何篇目）'


def expand_anchors(text, res):
    """把正文里的 `@facts` / `@evidence` 锚点**展开为程序冻结的内容**。

    返回 `(展开后的文本, 展开了哪些锚点)`。**没有任何锚点时原样返回**（逐字节不变）。
    —— 这是「模型只写锚点、程序填内容」的落点：模型不可能把事实写错，因为它根本没写。
    """
    if not text:
        return text, []
    used = []
    if ANCHOR_FACTS in text:
        text = text.replace(ANCHOR_FACTS, facts(res))
        used.append('facts')
    if ANCHOR_EVIDENCE in text:
        text = text.replace(ANCHOR_EVIDENCE, _evidence_text(res))
        used.append('evidence')
    return text, used


ARGUMENT_SYSTEM = (
    '你是「词律探微」的**论证层**：把给定事实（FACTS）组织成**结构化论证稿**。\n'
    '硬规则（违反任何一条，稿件都会被程序丢弃）：\n'
    '1) 只能使用 FACTS 里出现过的数字，**一个都不许自己算、四舍五入或补充**；\n'
    '2) 引用篇目必须写 [E1]、[E2] 这样的标记，且**只能引用 FACTS 里给出的编号**；\n'
    '3) 要引词句时，必须**逐字照抄** FACTS 中「原文：」后面的整句，用中文引号「」括起；\n'
    '4) 不得引入 FACTS 之外的任何史实、生平、版本或他人评价；不得判断优劣、推测作者心理；\n'
    '5) **每一条分论点都必须写 bridge（桥梁）**：说明「这个形式事实」为什么能推出「这个判断」'
    '——**不得把形式事实直接当成情感结论**（如不得由「仄声比例高」直接说「情感悲壮」）；\n'
    '6) assessment 只能取四个值之一：\n'
    '   · supported    证据直接支持该主张；\n'
    '   · mixed        部分支持、部分相悖；\n'
    '   · insufficient 证据不足（**此时 gaps 必须非空**）；\n'
    '   · unresolved   现有材料无法判定（**此时 gaps 必须非空**）。\n'
    '7) alternatives 列出**替代解释**（至少在想当然的单一解释之外，给一种别的读法）；\n'
    '8) gaps 列出**缺什么证据**才能让这个主张更可靠；\n'
    '9) 只输出一个 JSON 对象，**不要 Markdown 代码围栏、不要多余文字**。\n'
)
TASK_ARGUMENT_JSON = (
    '请输出如下 JSON（字段名不可改）：\n'
    '{"thesis":"总论点（一句话，限定在声律形式层面）",'
    '"claims":[{"claim":"分论点","bridge":"从形式事实到该判断的桥梁",'
    '"assessment":"supported|mixed|insufficient|unresolved",'
    '"alternatives":["替代解释…"],"gaps":["缺证…"],"evidence":["E1","E2"]}],'
    '"limitations":["本系统只提供形式层证据…"]}\n'
    'claims 给 1—4 条；evidence 只填 FACTS 里真实存在的 [E#] 编号。'
)

_ARG_MAX_CLAIMS = 6
_ARG_MAX_ALT = 5
_ARG_MAX_GAPS = 5
_ARG_MAX_LIMITS = 6
_ARG_TEXT_CAP = 1200


def _s(v):
    """把任意值安全转成去空白字符串（非字符串一律空串）。"""
    return v.strip() if isinstance(v, str) else ''


def _slist(v, cap):
    """把任意值转成「非空字符串」列表（最多 cap 条）。"""
    if not isinstance(v, list):
        return []
    out = []
    for x in v:
        t = _s(x)
        if t:
            out.append(t[:400])
        if len(out) >= cap:
            break
    return out


def parse_argument_ex(raw, blocks):
    """解析并**校验**模型返回的结构化论证稿。返回 `(结构 or None, 问题列表, 失败码列表)`。

    校验规则（逐项校验，落到论证稿）：
      1) 必须是 JSON 对象，且 `thesis` 非空；
      2) `claims` 为 1—`_ARG_MAX_CLAIMS` 条；
      3) 每条 `claim`、`bridge` 非空——**bridge 是硬要求**（形式→解释的桥梁）；
      4) `assessment` ∈ `ASSESSMENTS`；
      5) `assessment ∈ {insufficient, unresolved}` → `gaps` 非空；
      6) `evidence` 里每个 [E#] 都必须**真实存在**于本轮 blocks；
      7) `limitations` 至少一条。
    **任一条不过即返回 None**，调用方回落（绝不把不合格结构当成结果）。
    `codes` 为 `FAILURE_CODES` 里的枚举（机器可判、可统计），`problems` 仍是人话（界面用）。
    """
    problems = []
    txt = (raw or '').strip()
    # 容忍模型偶尔套 Markdown 代码围栏
    if txt.startswith('```'):
        txt = re.sub(r'^```[a-zA-Z]*\s*', '', txt)
        txt = re.sub(r'\s*```$', '', txt).strip()
    try:
        data = json.loads(txt)
    except (ValueError, TypeError):
        return None, ['论证稿不是合法 JSON'], ['output_not_json']
    if not isinstance(data, dict):
        return None, ['论证稿顶层不是 JSON 对象'], ['output_not_object']

    thesis = _s(data.get('thesis'))
    if not thesis:
        problems.append('缺少 thesis（总论点）')

    raw_claims = data.get('claims')
    if not isinstance(raw_claims, list) or not raw_claims:
        problems.append('claims 必须是非空数组')
        raw_claims = []
    if len(raw_claims) > _ARG_MAX_CLAIMS:
        problems.append('claims 超过上限（%d 条），已截断' % _ARG_MAX_CLAIMS)
        raw_claims = raw_claims[:_ARG_MAX_CLAIMS]

    valid_eids = {b['eid'] for b in (blocks or [])}
    claims = []
    for i, c in enumerate(raw_claims):
        if not isinstance(c, dict):
            problems.append('claims[%d] 不是对象' % i)
            continue
        claim = _s(c.get('claim'))
        bridge = _s(c.get('bridge'))
        ass = _s(c.get('assessment')).lower()
        alts = _slist(c.get('alternatives'), _ARG_MAX_ALT)
        gaps = _slist(c.get('gaps'), _ARG_MAX_GAPS)
        ev = _slist(c.get('evidence'), 8)
        if not claim:
            problems.append('claims[%d] 缺少 claim' % i)
            continue
        if not bridge:
            problems.append('claims[%d] 缺少 bridge（形式→解释的桥梁，硬要求）' % i)
        if ass not in ASSESSMENTS:
            problems.append('claims[%d] assessment 非法（%s）' % (i, ass or '空'))
            ass = 'insufficient'
        if ass in ('insufficient', 'unresolved') and not gaps:
            problems.append('claims[%d] assessment=%s 时 gaps 不得为空' % (i, ass))
        # 证据编号存在性（锚点必须真实存在）
        eids = []
        for e in ev:
            e_norm = e if e.startswith('E') else ('E' + e.lstrip('Ee'))
            if e_norm not in valid_eids:
                problems.append('claims[%d] 引用了不存在的证据 %s' % (i, e))
            else:
                eids.append(e_norm)
        claims.append({'claim': claim[:_ARG_TEXT_CAP], 'bridge': bridge[:_ARG_TEXT_CAP],
                       'assessment': ass, 'alternatives': alts, 'gaps': gaps,
                       'evidence': eids})

    limitations = _slist(data.get('limitations'), _ARG_MAX_LIMITS)
    if not limitations:
        problems.append('缺少 limitations（局限声明，至少一条）')

    if problems:
        return None, problems, classify_failures(problems)
    return {'thesis': thesis[:_ARG_TEXT_CAP], 'claims': claims,
            'limitations': limitations}, [], []


def parse_argument(raw, blocks):
    """`parse_argument_ex` 的**向后兼容**包装（只回 `(结构, 问题列表)`）。"""
    struct, problems, _codes = parse_argument_ex(raw, blocks)
    return struct, problems


_ASSESS_CN = {'supported': '支持', 'mixed': '部分支持',
              'insufficient': '证据不足', 'unresolved': '未决'}


def render_argument(struct):
    """把结构化论证稿渲染成**人话文本**（供既有文本消费方与网页展示）。"""
    out = ['【论证辅助草稿（结构化 · 已过护栏）】', '主张：%s' % struct['thesis']]
    for i, c in enumerate(struct['claims'], 1):
        out.append('')
        out.append('分论点 %d：%s' % (i, c['claim']))
        out.append('  · 桥梁：%s' % c['bridge'])
        out.append('  · 评估：%s（%s）' % (c['assessment'], _ASSESS_CN.get(c['assessment'], c['assessment'])))
        if c['evidence']:
            out.append('  · 证据：%s' % '、'.join('[%s]' % e for e in c['evidence']))
        if c['alternatives']:
            out.append('  · 替代解释：%s' % '；'.join(c['alternatives']))
        if c['gaps']:
            out.append('  · 缺证：%s' % '；'.join(c['gaps']))
    if struct['limitations']:
        out.append('')
        out.append('局限：%s' % '；'.join(struct['limitations']))
    return '\n'.join(out)


def produce_argument(llm, res, kind, boundary, max_tokens=900, temperature=0.2,
                     on_delta=None):
    """生成**结构化论证稿**（论证稿结构化）。失败一律 `ok=False`，调用方回落。

    返回体比 `produce()` 多两个字段：
      · `struct`：结构化论证稿（ok=True 时非 None）；
      · `trace` ：`guard.audit_number_traceability()` 的数字可追溯性审计。
    """
    model = getattr(llm, 'name', None) or '未知模型'
    if not (llm and llm.available()):
        return {'ok': False, 'model': model, 'text': '', 'raw': '', 'struct': None,
                'trace': None, 'codes': ['model_unavailable'],
                'problems': ['大模型不可用（无密钥或未联网），回落到模板作答']}
    user = ('【问句】%s\n【查询理解】%s\n【问句类型】%s\n【FACTS】\n%s\n【任务】%s'
            % (res.get('question', ''), res.get('spec', ''), kind, facts(res),
               TASK_ARGUMENT_JSON))
    kw = {'temperature': temperature, 'max_tokens': max_tokens}
    if on_delta is not None:
        kw['on_delta'] = on_delta
    raw = llm.chat([{'role': 'system', 'content': ARGUMENT_SYSTEM},
                    {'role': 'user', 'content': user}], **kw)
    if not raw:
        return {'ok': False, 'model': model, 'text': '', 'raw': '', 'struct': None,
                'trace': None, 'codes': ['generation_incomplete'],
                'problems': ['大模型无返回：%s' % (getattr(llm, 'last_error', '') or '未知原因')]}
    struct, probs, codes = parse_argument_ex(raw, res.get('blocks') or [])
    if struct is None:
        return {'ok': False, 'model': model, 'text': '', 'raw': raw.strip(),
                'struct': None, 'trace': None, 'codes': codes,
                'problems': ['论证稿结构校验未通过：' + '；'.join(probs[:4])]}
    text = render_argument(struct)
    # 锚点展开（@facts/@evidence）：模型只写锚点，**程序**把冻结内容填回
    text, anchors = expand_anchors(text, res)
    # 护栏：结构化稿仍须过四道（数字/引文/边界），并附数字可追溯性审计
    check_body = text + ('\n【推断边界｜%s问句】%s' % (kind, boundary))
    problems = []
    sf = safety.check(text, 'out')
    if not sf['ok']:
        problems.append('生成文本命中内容安全规则（%s）' % sf['category'])
    ok_g, gprobs = guard.verify(check_body, res.get('blocks') or [], boundary_kind=kind,
                                allow=_allow(res))
    if not ok_g:
        problems += gprobs[:4]
    trace = guard.audit_number_traceability(text, res.get('blocks') or [], allow=_allow(res))
    ok = (not problems) and ok_g
    return {'ok': ok, 'model': model, 'text': text if ok else '', 'raw': text,
            'struct': struct if ok else None, 'trace': trace,
            'codes': classify_failures(problems), 'anchors': anchors,
            'problems': problems}


def read_content(llm, res, kind, boundary, parts=None, content_full=False,
                 max_tokens=700, temperature=0.3, on_delta=None):
    """生成「**文意解读**」并过护栏（内容 / 情感类问题专用；失败时调用方**静默跳过**）。

    · `content_full=True`：用户整体在问内容/情感（`content_ask`）→ 「内容解读」任务；
    · `parts=[…]`：问句里有开放提问 / 系统没听懂的片段（如「有什么作用」）→ 「逐条回应」任务；
    · 两者同时给出 → 两个任务合并（先解读内容，再逐条回应）；
    · 模型判定无法基于材料回应时输出 `NO_READ` 标记 → 本函数返回 ok=False
      （调用方不显示该段——**宁可不说，不可乱说**）。
    """
    model = getattr(llm, 'name', None) or '未知模型'
    if not (llm and llm.available()):
        return {'ok': False, 'model': model, 'text': '', 'raw': '',
                'problems': ['大模型不可用（无密钥或未联网）']}
    _t_parts = (TASK_READ_PARTS % '；'.join(list(parts)[:6])) if parts else ''
    if content_full and _t_parts:
        task = TASK_READ_FULL + '\n另外，' + _t_parts
    elif content_full:
        task = TASK_READ_FULL
    else:
        task = _t_parts
    user = ('【问句】%s\n【查询理解】%s\n【FACTS】\n%s\n【任务】%s'
            % (res.get('question', ''), res.get('spec', ''), facts(res), task))
    kw = {'temperature': temperature, 'max_tokens': max_tokens}
    if on_delta is not None:
        kw['on_delta'] = on_delta
    raw = llm.chat([{'role': 'system', 'content': SYSTEM_READ},
                    {'role': 'user', 'content': user}], **kw)
    if not raw:
        return {'ok': False, 'model': model, 'text': '', 'raw': '',
                'codes': ['generation_incomplete'],
                'problems': ['大模型无返回：%s' % (getattr(llm, 'last_error', '') or '未知原因')]}
    txt = raw.strip()
    if 'NO_READ' in txt[:40]:
        return {'ok': False, 'model': model, 'text': '', 'raw': txt,
                'problems': ['模型判定无法基于材料回应（已跳过该段）']}
    check_body = txt + ('\n【推断边界｜%s问句】%s' % (kind, boundary))
    problems = []
    sf = safety.check(txt, 'out')
    if not sf['ok']:
        problems.append('生成文本命中内容安全规则（%s）' % sf['category'])
    ok_g, probs = guard.verify(check_body, res.get('blocks') or [], boundary_kind=kind,
                               allow=_allow(res))
    if not ok_g:
        problems += probs[:4]
    ok = (not problems) and ok_g
    return {'ok': ok, 'model': model, 'text': txt, 'raw': txt,
            'codes': classify_failures(problems), 'problems': problems}


def _num(x, fmt='%.1f'):
    try:
        return fmt % float(x)
    except (TypeError, ValueError):
        return '—'


def facts(res):
    """把证据块里的**事实**列成清单（只有事实，没有评价）。

    第一条固定是「查询条件（唯一权威）」——清单是脚本从 spec 里抄出来的，
    不是让模型自己总结问题，从根上防「把没解析到的条件编进去」（2026-09-30 实测事故）。
    """
    out = ['【查询条件（唯一权威）】%s' % (res.get('spec') or '（无条件）')]
    for line in (res.get('agg_facts') or []):        # 聚合题：组级事实（同样来自原库）
        out.append(line)
    if res.get('extreme_fact'):                     # 极值题：问的是「哪一首…」，别写成「共同特征」
        out.append(res['extreme_fact'])
    if res.get('pair_fact'):                        # 配对题：答案是一批**对子**，不是「哪些篇满足条件」
        out.append(res['pair_fact'])
    for b in res.get('blocks') or []:
        out.append('[%s] %s·%s《%s》｜%d 句 / %d 字｜平 %d、仄 %d｜仄声比例 %s%%｜声情转向 %s｜出处 %s'
                   % (b['eid'], b['dynasty'], b['author'], b['title'] or b['cipai'],
                      b['sent_n'], b['han_len'], b['ping'], b['ze'], _num(b['ze_ratio']),
                      b['scene'], b['pid']))
        if b.get('change') is not None:
            out.append('    （前段与后段的变化值 %s，长句阈值 %s）'
                       % (_num(b['change']), b.get('threshold', '—')))
        for L in (b.get('lines') or []):
            out.append('    [%s] 第 %d 句 原文：%s（%d 字，平 %d、仄 %d，平仄串 %s）'
                       % (b['eid'], L.get('seq', L['idx'] + 1), L['text'], L['han_len'],
                          L['ping'], L['ze'], L['pz']))
    if not out:
        out.append('（无——本轮没有召回到任何篇目）')
    return '\n'.join(out)


def _allow(res):
    """说法层允许出现的数字。

    审查 B5：聚合题（blocks=[]）里，FACTS 是唯一的数字来源，旧版没把 FACTS 数字放进白名单
    → 模型照抄 FACTS 立刻被判「数字无出处」→ **聚合题的说法层从未生效**。
    FACTS 全部由引擎产出（含组级统计、极值复核、配对复核），放行它们不降低严格度。
    """
    allow = re.findall(r'\d+(?:\.\d+)?', res.get('spec') or '')
    allow.append(len(res.get('blocks') or []))
    for b in res.get('blocks') or []:
        allow += [str(int(n)) for n in re.findall(r'\d+', b['pid'])]
    allow += re.findall(r'\d+(?:\.\d+)?', facts(res))
    return allow


def produce(llm, res, kind, boundary, argument=False, max_tokens=700, temperature=0.2,
            on_delta=None):
    """生成「说法层」文本并过护栏。返回 dict（ok=False 时调用方必须回落到模板）。

    ⭐ 2026-10-13：`argument=True` 时**先试结构化论证稿**（`produce_argument`，吸收
    Claim 结构）；结构或护栏不过，**回落既有散文四层草稿**（`_produce_plain`，
    逐字未改）；仍不过才由调用方回落模板。**narrate 路径完全不受影响**。
    """
    if argument:
        r = produce_argument(llm, res, kind, boundary, temperature=temperature,
                             on_delta=on_delta)
        if r.get('ok'):
            return r
        fb = _produce_plain(llm, res, kind, boundary, argument=True,
                            max_tokens=max_tokens, temperature=temperature,
                            on_delta=on_delta)
        fb.setdefault('struct', None)
        fb.setdefault('trace', None)
        fb['struct_fallback'] = r.get('problems') or []
        if not fb.get('ok'):
            fb['problems'] = (r.get('problems') or []) + (fb.get('problems') or [])
            fb['codes'] = list(dict.fromkeys((r.get('codes') or []) + (fb.get('codes') or [])))
        return fb
    return _produce_plain(llm, res, kind, boundary, argument=False,
                          max_tokens=max_tokens, temperature=temperature,
                          on_delta=on_delta)


def _produce_plain(llm, res, kind, boundary, argument=False, max_tokens=700, temperature=0.2,
                   on_delta=None):
    """既有散文说法层（叙述 / 四层论证草稿）。返回 dict（ok=False 时调用方必须回落到模板）。"""
    model = getattr(llm, 'name', None) or '未知模型'
    if not (llm and llm.available()):
        return {'ok': False, 'model': model, 'text': '', 'raw': '',
                'codes': ['model_unavailable'],
                'problems': ['大模型不可用（无密钥或未联网），回落到模板作答']}
    user = ('【问句】%s\n【查询理解】%s\n【问句类型】%s\n【FACTS】\n%s\n【任务】%s'
            % (res.get('question', ''), res.get('spec', ''), kind, facts(res),
               TASK_ARGUMENT if argument else TASK_NARRATE))
    kw = {'temperature': temperature, 'max_tokens': max_tokens}
    if on_delta is not None:
        kw['on_delta'] = on_delta            # 网页端可边生成边显示（首字延迟 ~0.4 秒）
    raw = llm.chat([{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
                   **kw)
    if not raw:
        return {'ok': False, 'model': model, 'text': '', 'raw': '',
                'codes': ['generation_incomplete'],
                'problems': ['大模型无返回：%s' % (getattr(llm, 'last_error', '') or '未知原因')]}
    # ⚠ 2026-10-04 修（代码审查 P2-13）：护栏④（类型化边界）要求叙述文本自身**含边界声明**，
    #   所以校验用的文本要补一行；但**返回给调用方的 text 不能再带这一行**——
    #   调用方（ask.py 的模板）结尾本来就有一句「【推断边界｜…】」，两边都带就会打印两遍
    #   （主人 10-03 的运行记录里已经出现过两次）。
    check_body = raw.strip() + ('\n【推断边界｜%s问句】%s' % (kind, boundary))
    problems = []
    sf = safety.check(raw.strip(), 'out')
    if not sf['ok']:
        problems.append('生成文本命中内容安全规则（%s）' % sf['category'])
    ok_g, probs = guard.verify(check_body, res.get('blocks') or [], boundary_kind=kind,
                               allow=_allow(res))
    if not ok_g:
        problems += probs[:4]
    ok = (not problems) and ok_g
    return {'ok': ok, 'model': model, 'text': raw.strip(), 'raw': raw.strip(),
            'codes': classify_failures(problems), 'problems': problems}


def main():
    ap = argparse.ArgumentParser(description='说法层：大模型写叙述 / 论证草稿（必须过护栏）')
    ap.add_argument('--db', required=True)
    ap.add_argument('--question', required=True)
    ap.add_argument('--topk', type=int, default=3)
    ap.add_argument('--argument', action='store_true')
    ap.add_argument('--show-struct', action='store_true',
                    help='打印结构化论证稿（JSON）与数字可追溯性审计')
    ap.add_argument('--provider', default=None)
    args = ap.parse_args()
    import ask as ASK
    import llm as L
    client = L.LLM(provider=args.provider)
    conn = sqlite3.connect(args.db)
    res = ASK.answer(conn, args.question, topk=args.topk, llm=client,
                     narrate=not args.argument, argument=args.argument)
    conn.close()
    print('模型：%s（可用=%s）' % (client.name or '无', client.available()))
    print('─' * 60)
    print(res['answer'])
    r = res.get('narrative') or {}
    print('─' * 60)
    print('说法层结果：%s' % ('已采用' if r.get('ok') else '已丢弃（回落模板）'))
    for p in r.get('problems') or []:
        print('  · %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
