# -*- coding: utf-8 -*-
"""可溯源问答（M6–M9 串起来）：检索 → 证据块 → 结构化成文 → 四道护栏。

成文用**确定性模板**（不接大模型也能跑；接国产大模型时，只需把「结构化事实 + 证据块」
喂给提示词，护栏与引用机制原样复用）。

用法：
  python ask.py --db data/corpus.db --question "清 临江仙 仄声比例高于45%"
  python ask.py --db data/corpus.db --question "纳兰性德 长相思" --json
  python ask.py --db data/corpus.db --question "唐 李白 平仄" --json     # 语料外 → 拒答
"""
import argparse
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aggregate                                             # noqa: E402
import evidence                                              # noqa: E402
import gen                                                    # noqa: E402
import guard                                                 # noqa: E402
import qlm                                                    # noqa: E402
import retrieve                                              # noqa: E402
import safety                                                # noqa: E402

# 边界声明按问句类型分派（互斥标记见 guard.BOUNDARY_KINDS）。
# 写作纪律：正文里的「」**只**用于引用语料原文；查询条件、pid、说明文字一律不用「」，
# 这样护栏②的「引文必须逐字来自被引证据块」才是有效校验。
BOUNDARIES = {
    '数值型': '以上数字只反映当前文本的形式与声调配置，不能直接推断作者意图、'
             '时代因果或作品优劣。',
    '意图型': '声律与字面特征不能直接推断作者意图；若要论及写作目的，须另据序跋、本事、'
             '年谱等文献证据，本系统只提供形式层证据。',
    '因果型': '本文只呈现语料内的形式统计与文本线索，不能据此建立时代因果：'
             '统计上的相关性不等于因果。',
    '优劣型': '仄声比例等指标只描述形式配置，不构成文学价值判断；'
             '不据此评定作品优劣或艺术高下。',
}
KIND_RULES = (
    ('意图型', ('意图', '写作目的', '想表达', '意在', '为什么写', '旨趣', '寄托')),
    ('因果型', ('因果', '为什么', '原因', '导致', '因为', '所以', '与时代')),
    ('优劣型', ('优劣', '高下', '好不好', '哪个好', '更好', '更佳', '价值', '评价', '最佳',
              '最好', '胜过', '是否更')),
)
NO_SUPPORT = ('现有语料未见支持：按查询条件（%s）未召回到任何词作。'
              '可放宽条件后重试（去掉朝代限定、降低阈值），或改用具体词人／词牌检索。')

# 「护栏校验」末行的三条通过文案（各路径措辞不同，抽成常量供**终版与「答案先到」快照**共用，
# 保证快照里的结论行与终版逐字一致；改文案只需改这里）。
GUARD_PASS_MAIN = '通过（数字全部来自被引证据块、引文逐字落地、边界声明与问句类型匹配）'
GUARD_PASS_AGG = '通过（数字全部来自分组统计、口径已写明、边界声明与问句类型匹配）'
GUARD_PASS_PAIR = '通过（数字全部来自分组统计与证据块、引文逐字落地、边界声明与问句类型匹配）'


def _verdict_line(ok, problems, pass_text):
    """护栏结论行（以换行开头；未通过时列出具体原因——不写「未过」这种空话）。"""
    return '\n【护栏校验】' + (pass_text if ok else '未通过：%s' % '；'.join(problems))


def classify_question(text):
    for kind, words in KIND_RULES:
        if any(w in text for w in words):
            return kind
    return '数值型'


# 「模糊意图」词表（2026-10-01 深夜，答案级实测驱动）：
#   没有解析出**任何**形式条件时，这些话问的是本系统**答不了**的层面（语义／评价／因果／
#   情绪／释义）。命中就如实拒答——不拿「融合排序前几篇」冒充答案。
VAGUE_ASK_RE = re.compile(
    r'(中心思想|思想感情|表达了|什么感情|什么意思|含义|赏析|翻译|解读|意境|修辞|'
    r'风格|最好|最差|哪个好|更优美|更胜|评价|有名|著名|经典|推荐|'
    r'为什么|为何|开心|伤心|难过|寂寞|豪放|婉约|清丽|悲凉|欢快|忧愁|好听)')


def _no_hard_condition(spec):
    """是否**没有任何**可检索的形式条件（朝代/词人/词牌/声情/声律/句脚/数值区间）。

    与 `retrieve.search` 里 `hard` 的判据一致（单一来源的语义，两处别走样）。
    """
    return not (retrieve._vals(spec, 'dynasty') or retrieve._vals(spec, 'author')
                or retrieve._vals(spec, 'cipai') or spec.scene or spec.pz
                or retrieve._vals(spec, 'tail') or spec.tail_pz or spec.rng)


def _line_note(spec, L):
    """给展示句加一句「为什么展示它」的说明（行级条件题专用）。"""
    rs = L.get('match_reasons') or []
    if '句脚字' in rs:
        return '（此句句脚为 %s，合问句条件）' % (L.get('tail') or '')
    if '句脚平仄' in rs:
        return '（此句句脚为%s，合问句条件）' % ((L.get('pz') or '')[-1:] or '')
    if '声律模式' in rs:
        return '（此句合声律模式 %s）' % (spec.pz or '')
    return ''


def _clean_frag(s):
    """披露用的片段：去掉引号类字符（「」只用于引用语料原文，不能用在说明里）。"""
    return re.sub(r'[「」『』“”]', '', str(s)).strip()


# 「未解析的方向/数量词」词表：规则路没把它们变成条件时，说明规则路漏听了，
# 这时才值得再花 1.4 秒让大模型听一遍（案例：「清或宋的临江仙里仄声超过一半的有哪些」）。
DIR_WORDS = ('超过', '高于', '大于', '多于', '高出', '低于', '小于', '少于', '不足',
             '至少', '至多', '一半', '过半', '以上', '以下', '最高', '最低', '最多',
             '最少', '最长', '最短', '更高', '更低', '最多字', '占比最')
# 「信息性残留」：规则已把它转成了条件，只是如实披露一句，不算漏听
INFO_UNPARSED = ('已转为排序', '已忽略', '冲突，未并入同一条件')


def _rule_complete(rule, question):
    """规则路的解析是否已经「够用」——够了就不必再花一次大模型往返。

    保守判据（只在**大模型结论必然被丢弃**时返回 True）：
      · 已识别出 对比／配对／极值排序 —— 这三类在这份代码里有**确定性安全网**，
        大模型没听出来也会被订正回规则路（见下方各分支），调用注定被丢弃；
      · 或：已有硬条件 且 无信息性以外的残留 且 问句里的方向词都已被条件覆盖。
    只要拿不准就返回 False（走大模型）——**理解能力优先于省那 1.4 秒**。
    """
    if rule.agg or rule.pair or rule.order_by:
        return True
    hard = bool(rule.dynasty_any or rule.author_any or rule.cipai_any or rule.scene
                or rule.rng or rule.tail_any or rule.pz)
    if not hard:
        return False
    residue = [u for u in (rule.unparsed or [])
               if not any(t in u for t in INFO_UNPARSED)]
    if residue:
        return False
    if rule.keywords:
        # 规则把一部分话当成了「词面检索词」——说明它没听懂那部分（实测反例：
        # 「句脚是灯或者声的清词」被解析成「句脚=灯 + 词面=声的」，漏了多值句脚）。
        # 这种情况一律交给大模型再听一遍（理解能力优先于省 1.4 秒）。
        return False
    if any(w in (question or '') for w in DIR_WORDS) and not (rule.rng or rule.order_by):
        return False                       # 话里有方向词却没变成条件 → 规则漏听，交给模型
    return True


def understand(conn, question, llm=None, llm_parse=False, llm_policy='always', context=None):
    """问句 → QuerySpec。

    `llm_parse=True` 且模型可用时走**大模型理解路**（`qlm`）：模型只把话听明白，
    字段逐个经引擎校验（落不到库上的直接丢弃并记录）；失败则回落规则解析。
    两条路的产出都是同一个 `QuerySpec`，后续检索/复核/计数/护栏完全一致。

    `context`（可选）：上一轮「问句＋解析」摘要，供多轮指代补全（「那里面呢」）。
    **只在 llm_parse 路生效**（规则路保持纯确定性）；且带上下文时**不再走
    「规则已完整就略过模型」的省时分支**——指代补全这件事规则路干不了（理解优先于省时）。
    """
    rule = retrieve.parse_query(conn, question)
    note = {'source': '规则解析', 'dropped': [], 'notes': [], 'alt': None}
    if not (llm_parse and llm is not None and getattr(llm, 'available', lambda: False)()):
        return rule, note
    if llm_policy == 'auto' and _rule_complete(rule, question) and not context:
        # 响应速度：规则路已够用时省掉一次大模型往返（实测省 1.4~5.7 秒），且结论不变
        note['notes'] = ['规则解析已完整（无残留条件），按 llm_policy=auto 略过大模型理解']
        return rule, note
    q = qlm.parse(conn, llm, question, context=context)
    if q is None:
        note['notes'] = ['大模型未给出可解析的条件（输出不是合法 JSON），已回落规则解析']
        return rule, note
    spec = q['spec']
    # **安全网**（只补不替）：朝代与「语料外朝代」这类高确定性字段，
    # 规则解析能把住就把住——大模型漏了「清」会让答案从 692 篇变成 1362 篇，
    # 这种错看起来依旧「像对的」；补上并如实注明来源。
    notes = list(q['notes'])
    if context:
        notes.append('已结合上一轮上下文理解本轮问句（条件均经引擎逐字段校验）')
    if not spec.dynasty_any and rule.dynasty_any and not spec.agg:
        spec.dynasty_any = list(rule.dynasty_any)
        notes.append('朝代由规则解析补齐（%s）' % '／'.join(spec.dynasty_any))
    if rule.unsupported and not spec.unsupported:
        spec.unsupported = rule.unsupported
        notes.append('语料外朝代由规则解析补齐（%s）：本系统不拿语义相近的篇凑数'
                     % rule.unsupported)
    # **分组对比题的安全网**（实测踩过）：规则路已认出「宋词与清词…哪个更高」是**对比题**，
    # 而模型把这些「组名」当成了检索条件（如 dynasty=["宋","清"] → 语料外 → 拒答）。
    # 对比/统计是**确定性换不来的**一类意图，模型没听出来就一律用规则路的。
    if rule.agg and not spec.agg:
        # ⚠ 组内极值（「哪个词人最多」）的 values 是 **None**——旧版这里 '／'.join(None)
        # 直接抛 TypeError（2026-10-01 深夜答案解析实测：「哪位词人的临江仙最多」大模型路
        # 整条崩掉、网页显示「出错了」）。这里按有无组名分别渲染，绝不对 None 做 join。
        _rl = rule.agg.get('values')
        _rdesc = ('／'.join(_rl) if _rl else
                  '按%s取%s' % (
                      {'author': '词人', 'cipai': '词牌', 'dynasty': '朝代'}.get(
                          rule.agg.get('group_by'), rule.agg.get('group_by') or '未知维度'),
                      '最多' if rule.agg.get('extreme') == 'max' else '最少'))
        notes.append('大模型未把该句识别为分组对比题，已改用规则解析（%s）' % _rdesc)
        if spec.order_by:          # 聚合题里不存在「排序指标」，模型多给的必须清掉并如实说明
            notes.append('大模型给出的排序条件（%s）与本题类型不符，已忽略'
                         % (spec.order_label or spec.order_by))
        if spec.rng or spec.scene or spec.tail_any or spec.pz:
            notes.append('大模型给出的筛选条件与分组对比无关，已忽略（聚合题只看组的统计量）')
        rule.source = '规则解析（大模型未识别为对比题）'
        return rule, {'source': rule.source, 'dropped': q['dropped'],
                      'notes': notes, 'alt': spec}
    # **两路都认出聚合时**：指标以**规则路**为准（2026-09-30 实测）。
    # 反例：问「宋词与清词哪个更优美」——规则路认得出「有组可比、但没点明指标」（unspecified，
    # 应如实认账），而大模型会**替用户发明**一个指标（仄声占比）→ 又变成「答非所问」。
    if rule.agg and spec.agg:
        same = (rule.agg['metric'] == spec.agg['metric']
                and rule.agg.get('cat') == spec.agg.get('cat'))
        if not same:
            if rule.agg['metric'] == 'unspecified':
                why = '规则解析没看到指标（不替用户选）'
            else:
                why = ('两路指标不一致（规则=%s、大模型=%s）'
                       % (rule.agg['metric'], spec.agg['metric']))
            notes.append('聚合指标以规则解析为准：%s' % why)
            rule.source = '规则解析（聚合指标以规则路为准）'
            return rule, {'source': rule.source, 'dropped': q['dropped'],
                          'notes': notes, 'alt': spec}
    # ⭐ **反向安全网**：规则路**没**认出分组统计、而大模型**认出了** → 采纳大模型。
    # 为什么必须加：原来只有「规则认出、模型没认出 → 用规则」这一个方向的安全网，
    # 于是当**规则路本身能力不足**（如「哪个词人的词占比最多」这类组内极值）时，
    # 大模型的正确意图会被整个丢弃 → 系统退化成普通检索 → **答非所问**（2026-10-01 主人实测）。
    # 规则路认不出聚合时，它的「结论」本来就不存在，此时大模型是唯一的理解来源。
    if getattr(spec, 'agg', None) and not rule.agg:
        notes.append('分组统计意图由大模型识别（规则解析未识别）；筛选条件仍两路合并')
        return spec, {'source': spec.source, 'dropped': q['dropped'],
                      'notes': notes, 'alt': rule}

    # **配对题的安全网**（2026-09-30 主人实测，同一个 bug 的第三个入口）：
    # 问「找出几对每个位置上的字平仄都相同的两首词」时，模型只听见「平仄」→ 直接捏出
    # 「声律模式=平仄平仄平仄平仄」去筛篇（本句里根本没有这个谱），答案完全离谱。
    # 配对与对比、极值同属**确定性意图**：模型没听出来就一律用规则路的，并如实注明。
    if rule.pair and not spec.pair:
        notes.append('大模型未把该问句识别为配对题（它把问句当成了声律条件），已改用规则解析')
        rule.source = '规则解析（大模型未识别为配对题）'
        return rule, {'source': rule.source, 'dropped': q['dropped'],
                      'notes': notes, 'alt': spec}
    # **极值／排序题的安全网**（实测踩过，2026-09-30 主人第七炮续）：
    # 问「高旭写的哪首词里仄声字占比最高」时，模型只听了「词人=高旭」、**把「最高」丢了**，
    # 而上一轮的安全网只盖了朝代/语料外朝代/对比题——于是规则路已识别的排序条件被丢掉，
    # 答案从「极值篇」静静退回「融合排序最前者」（旧 bug 换个壳又回来）。
    # 排序/极值是与对比题同类的**确定性意图**：模型没听出来就一律用规则路的，并如实注明。
    if not spec.order_by and rule.order_by:
        spec.order_by, spec.order_col = rule.order_by, rule.order_col
        spec.order_dir, spec.extreme = rule.order_dir, rule.extreme
        spec.order_label, spec.order_src = rule.order_label, '规则'
        notes.append('极值／排序意图由规则解析补齐（【%s】取%s）'
                     % (rule.order_label, '最高' if rule.extreme == 'max' else '最低'))
    elif spec.order_by and rule.order_by and (spec.order_by != rule.order_by
                                              or spec.order_dir != rule.order_dir):
        notes.append('排序条件两路不一致（模型说【%s】取%s，规则说【%s】取%s）：'
                     '已改用规则解析的'
                     % (spec.order_label, '最高' if spec.extreme == 'max' else '最低',
                        rule.order_label, '最高' if rule.extreme == 'max' else '最低'))
        spec.order_by, spec.order_col = rule.order_by, rule.order_col
        spec.order_dir, spec.extreme = rule.order_dir, rule.extreme
        spec.order_label, spec.order_src = rule.order_label, '规则'
    # 「最高／最低」这类极值词若还留在 unparsed 里，披露文案会写成「未被理解成条件，已忽略」——
    # 而它其实**已经**被用作排序条件了：这句话本身就不对。补回排序后一并清掉。
    if spec.order_by:
        _ew = tuple(retrieve.EXTREME_UP) + tuple(retrieve.EXTREME_DOWN)
        spec.unparsed = [x for x in spec.unparsed
                         if not any(str(x) == w or str(x).startswith(w + '（已转为')
                                    for w in _ew)]
    retrieve._finalize(spec)
    return spec, {'source': spec.source, 'dropped': q['dropped'],
                  'notes': notes, 'alt': rule}


def _parse_head(spec, note):
    """查询理解头：条件 + 来源 + **如实披露**（丢弃的字段 / 没理解的片段）。"""
    out = ['【查询理解】（来源：%s）%s' % (note['source'], spec.describe())]
    if note['dropped']:
        out.append('　　　注：大模型给出的以下内容无法在语料中落地，已忽略——%s'
                   % '；'.join(_clean_frag(x) for x in note['dropped']))
    if spec.unparsed:
        out.append('　　　注：问句里以下片段未被理解成条件，已忽略——%s'
                   % '；'.join(_clean_frag(x) for x in spec.unparsed))
    if note['notes']:
        out.append('　　　注：%s' % '；'.join(_clean_frag(x) for x in note['notes']))
    alt = note.get('alt')
    if alt is not None and not alt.describe().startswith('（无') \
            and alt.describe() != spec.describe():
        # 审查 B40：alt 是**大模型**那一版（规则路才是 note['source']），旧文案方向写反了
        out.append('　　　注：同一句用大模型解析得到〔%s〕；本次执行以上表为准。'
                   % _clean_frag(alt.describe()))
    return '\n'.join(out)


_NUM_LIT_RE = re.compile(r'\d+(?:\.\d+)?')


def _nums(s):
    """抽取数字字面量，**含小数**。

    为什么要专门抽小数：模型名 `qwen3.8-27b` 里的小数是 `3.8`，而 `re.findall(r'\d+')`
    只会得到 `['3','8','27']`——护栏拿 `3.8` 去白名单里比对必然**对不上**，于是
    整段大模型稿被自己的注脚卡掉（换新模型后实测：每次都回落模板）。
    """
    return _NUM_LIT_RE.findall(str(s or ''))


def _allow_disclose(pnote, spec):
    """披露文字里的数字（模型名版本号如 glm-4-flash / qwen3.8-27b、字段约束如「≥3 位」）
    是**出处标记/诊断信息**，不是对语料下的断言，必须放行——否则自己的注脚会把整篇卡掉。
    """
    out = []
    texts = [pnote.get('source')] + list(pnote.get('dropped') or []) \
        + list(pnote.get('notes') or []) + list(spec.unparsed or [])
    for x in texts:
        for n in _nums(x):
            # 整数给 int、小数给 float：既满足「整数断言」，也让 qwen3.8-27b 的 3.8 被放行
            out.append(int(n) if n.isdigit() else float(n))
    return out


def _answer_agg(conn, question, spec, pnote, kind='数值型', llm=None, narrate=False,
                argument=False, on_delta=None, on_engine=None):
    """聚合/对比题的作答：在**原库上分组统计**，不靠「检索 + 举例」。

    问「宋词与清词总体哪个体仄声占比更高」——检索层给的是**篇**，这里给的是**组的统计量**。
    两种口径（篇均/加权）都算、都写出来；口径不一致就照实说。
    """
    ag = spec.agg
    if spec.unsupported:
        text = ('现有语料未见支持：问句涉及语料外范围（%s）。本系统语料只含清/宋/元三代词作，'
                '不拿语义相近的篇凑数，也不做跨出语料的统计。' % _clean_frag(spec.unsupported))
        ok, problems = guard.check_no_support(text, True)
        return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                'answer': text, 'verify': (ok, problems), 'refused': True, 'problems': problems,
                'total': None, 'narrator': 'template', 'safety': {'ok': True}}
    if ag.get('metric') == 'unspecified':
        # 审查 B9：问句没点明指标时**不替用户选**（旧版默认仄声占比，「谁更优美」会拿到数值答案）
        _t = ('现有语料未见支持：问句没有点明要统计哪个指标，本系统不替用户选指标。'
              '可用指标：仄声占比、平声占比、篇幅（字）、句数，或某一类词作（如声情后段下降）的篇数占比。')
        _ok, _pb = guard.check_no_support(_t, True)
        return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                'answer': _t, 'verify': (_ok, _pb), 'refused': True, 'problems': _pb,
                'total': None, 'narrator': 'template', 'safety': {'ok': True},
                'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
                'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed), 'agg': None}
    _cat = ag.get('cat')
    _allow_extra, _facts = [], None
    if ag.get('values'):
        rows = aggregate.stats(conn, ag['group_by'], ag['values'], ag['metric'], _cat)
        cmp_ = aggregate.compare(rows, ag['metric'])
        out = [_parse_head(spec, pnote)]
        out += aggregate.render(rows, cmp_, ag['group_by'], ag['metric'], _cat)
    else:
        # ⭐ **组内极值**（「哪个词人/词牌…最多」）：没有组名，按维度全组扫描取极值。
        #    筛选条件 = 题面里除该维度外的全部条件（朝代/词牌/句脚…），由 `retrieve._sql` 给。
        _w, _a = retrieve._sql(spec)
        _ss = aggregate.scope_stats(conn, ag['group_by'], _w, _a)
        _ext = ag.get('extreme') or 'max'
        rows = aggregate.top_groups(conn, ag['group_by'], 5, ag['metric'], _cat,
                                    _w, _a, _ext)
        cmp_ = {'winner': None, 'loser': None, 'diff_weighted': None, 'diff_mean': None,
                'mean_agrees': None, 'empty': []}
        out = [_parse_head(spec, pnote)]
        out += aggregate.render_top(rows, ag['group_by'], ag['metric'], _ext,
                                    spec.describe(), _ss['n_poems'], _ss['n_groups'])
        _allow_extra = [_ss['n_poems'], _ss['n_groups']] + [
            x for r0 in rows for x in (r0['n'], r0['share'], r0['weighted'])]
        # 组名本身是**语料值**，可能自带数字（实测存在词牌「309月华清秋夜独游，用洪叔玙韵」），
        # 那些数字不是「无出处的论断数字」，必须放行。
        _allow_extra += re.findall(r'\d+', ' '.join(str(r0['group']) for r0 in rows))
        _gl = aggregate.GROUPS[ag['group_by']][1]
        _facts = ['【分组统计（唯一权威，全部来自本库原库 GROUP BY）】',
                  '统计范围（筛选条件）：%s' % spec.describe(),
                  '命中 %d 篇、涉及 %d 组（%s 维度）' % (_ss['n_poems'], _ss['n_groups'], _gl),
                  '按%s分组、取%s（%s）：' % (_gl, '最多' if _ext == 'max' else '最少',
                                              aggregate.METRICS[ag['metric']])]
        for r0 in rows:
            _facts.append('%s：%d 篇｜占命中篇数 %.1f%%' % (r0['group'], r0['n'], r0['share']))
        if rows:
            _facts.append('结论方向：%s 最多（%d 篇）' % (rows[0]['group'], rows[0]['n']))
    if ag.get('note'):
        out.append('　　　注：%s' % _clean_frag(ag['note']))
    out.append('【推断边界｜%s问句】%s' % (kind, BOUNDARIES[kind]))
    text = '\n'.join(out)
    allow = re.findall(r'\d+(?:\.\d+)?', spec.describe()) + aggregate.numbers(rows, cmp_)
    allow += _allow_disclose(pnote, spec) + _allow_extra
    allow.append(len(rows))
    if cmp_['empty']:
        allow.append(0)
    ok, problems = guard.verify(text, [], boundary_kind=kind, allow=allow)
    narrator, narrative = 'template', None
    if (narrate or argument) and llm is not None and getattr(llm, 'available', lambda: False)():
        _lab = ('%s的词作占比' % _cat[1]) if (ag['metric'] == 'share' and _cat)             else aggregate.METRICS[ag['metric']]
        agg_facts = list(_facts) if _facts is not None else ['【分组统计（唯一权威，全部来自本库原库 GROUP BY）】']
        for r in (() if _facts is not None else rows):
            if ag['metric'] == 'share':
                agg_facts.append('%s：%d 篇｜其中声情〔%s〕%d 篇｜占比 %.1f%%'
                                 % (r['group'], r['n'], _cat[1], r['n_hit'], r['share']))
            else:
                agg_facts.append('%s：%d 篇｜总 %d 字｜总仄字 %d｜篇均 %s %.1f%%｜加权 %s %.1f%%'
                                 % (r['group'], r['n'], r['han'], r['ze'], _lab, r['mean'],
                                    _lab, r['weighted']))
        if cmp_.get('winner') is not None:
            agg_facts.append('结论方向：%s 更高（加权 +%.1f，篇均 +%.1f）'
                             % (cmp_['winner']['group'], cmp_['diff_weighted'],
                                cmp_['diff_mean']))
        if on_engine is not None:
            # 「答案先到」：引擎的确定性结论此刻已全部算完（大模型只负责措辞），
            # 先把这一版**如实**发给前端——用户不必干等大模型整段写完（实测省 1~5 秒体感）。
            on_engine({'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                       'answer': text + _verdict_line(ok, problems, GUARD_PASS_AGG),
                       'verify': (ok, problems), 'refused': False,
                       'problems': problems, 'total': None, 'narrator': 'template',
                       'narrative': None, 'parse_source': pnote['source'],
                       'parse_dropped': pnote['dropped'], 'parse_notes': pnote['notes'],
                       'unparsed': list(spec.unparsed),
                       'agg': {'rows': rows, 'cmp': {k: v for k, v in cmp_.items()
                                                     if k not in ('winner', 'loser')}},
                       'safety': {'ok': True}})
        r = gen.produce(llm, {'question': question, 'spec': spec.describe(), 'kind': kind,
                              'blocks': [], 'agg_facts': agg_facts},
                        kind, BOUNDARIES[kind], argument=argument, on_delta=on_delta)
        narrative = r
        if r['ok']:
            title = '论证辅助草稿' if argument else '论证表述'
            text2 = text + '\n【%s（大模型 %s，已过四道护栏）】\n%s' % (title, r['model'], r['text'])
            allow2 = list(allow) + _nums(r['model'])
            ok2, p2 = guard.verify(text2, [], boundary_kind=kind, allow=allow2)
            if ok2:
                text, ok, problems, narrator = text2, ok2, p2, r['model']
            else:                   # 合并后过不了 → 整段不带，但**必须留下原因**（不静默回退）
                problems = p2
                narrative = dict(r, ok=False, problems=(r['problems'] + p2)
                                 or ['合并后未过护栏（未给出具体项）'])
                narrator = 'template（大模型稿合并后未过护栏，已回退）'
        else:
            narrator = 'template（大模型稿未过护栏，已回退）'
    text += _verdict_line(ok, problems, GUARD_PASS_AGG)
    return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
            'answer': text, 'verify': (ok, problems), 'refused': False, 'problems': problems,
            'total': None, 'narrator': narrator, 'narrative': narrative,
            'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
            'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed),
            'agg': {'rows': rows, 'cmp': {k: v for k, v in cmp_.items()
                                          if k not in ('winner', 'loser')}},
            'safety': {'ok': True}}


def _answer_pair(conn, question, spec, pnote, kind='数值型', llm=None, narrate=False,
                 argument=False, topk=3, on_delta=None, on_engine=None):
    """配对题（「找出几对每个位置上的字平仄都相同的两首词」）。

    与篇筛选完全不同：问的是**篇与篇之间**的关系。做法是「先按全篇平仄串分组，再取前几组」，
    每组给两篇；计数与展示都再用**第二条独立路径**（Python 侧重算）复核。
    只实现了「逐位**平仄**相同」这一维；问的是「字面/用字相同」时**认账不假装**。
    """
    import pairing
    pl = spec.pair or {}
    if 'tone' not in pl.get('dims', ()):
        text = ('现有语料未见支持：本题问的是「字面／用字相同」，本系统只实现'
                '「全篇逐位平仄相同」的配对（形式／声调层面），不拿平仄冒充字面。'
                '字面相同的检索请改用词面/全文检索。')
        ok, problems = guard.check_no_support(text, True)
        return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                'answer': text, 'verify': (ok, problems), 'refused': True, 'problems': problems,
                'total': None, 'narrator': 'template', 'safety': {'ok': True}}
    g = pairing.find_pairs(conn, spec, limit=max(1, min(5, topk)), per_group=2)
    au = pairing.audit(conn, spec, g['groups'])
    pids = [p['pid'] for grp in g['groups'] for p in grp['poems']]
    blocks = evidence.build_blocks(conn, retrieve.items_of(conn, pids),
                                   with_lines=1, spec=spec)
    out = []
    out.append(_parse_head(spec, pnote))
    scopes = '　'.join('%s %d 组／%d 对' % (d, ng, np_) for d, ng, np_ in g['by_dyn'] if ng)
    rng = ('未指定朝代：在全部语料（%d 首）内统计，其中 %d 首有平仄串可参与配对'
           % (g['scope_all'], g['scope_n'])) if g['scope_all'] != g['scope_n'] else (
        '未指定朝代：在全部语料（%d 首）内统计' % g['scope_n'])
    out.append('【结论】范围＝%s。按〔%s〕分组（只看平仄、不看字面；串相同即句数与字数也相同）：'
               '共 %d 组、%d 对（%s）。'
               % (rng, spec.pair_label, g['n_groups'], g['n_pairs'], scopes))
    out.append('　　　说明：%d 组共涉及 %d 首；本系统不把相同偷换成相似，只列逐位完全相同的对子%s。'
               % (g['n_groups'], g['n_covered'],
                  '；另有 %d 个极短残篇组（谱长不足 %d 位）不作举例，但计入上述计数'
                  % (g['n_short'], g['min_len']) if g['n_short'] else ''))
    for k, grp in enumerate(g['groups'], 1):
        a, b = grp['poems'][0], grp['poems'][1]
        ea, eb = blocks[2 * (k - 1)]['eid'], blocks[2 * (k - 1) + 1]['eid']
        share = '同词牌' if grp['same_cipai'] else '跨 %d 个词牌' % grp['n_cipai']
        out.append('　　　第 %d 对（组内 %d 首，谱长 %d 位，%s）：%s·%s《%s》[%s] 与 '
                   '%s·%s《%s》[%s]；各 %d 句／%d 字与 %d 句／%d 字，平仄串逐位相同。'
                   % (k, grp['n'], len(grp['sig']), share,
                      a['dynasty'], a['author'], a['title'], ea,
                      b['dynasty'], b['author'], b['title'], eb,
                      a['sent_n'], a['han_len'], b['sent_n'], b['han_len']))
    out.append('　　　【配对复核】独立复算：另用 Python 逐篇重算平仄串再分组，得 %d 组、%d 对'
               '（与上面一致）；并逐位比对展示的每一对：%s。'
               % (au['n_groups'], au['n_pairs'],
                  '；'.join('%s↔%s 共 %d 位、不同 %d 位'
                            % (pp['a'], pp['b'], pp['n_pos'], pp['n_diff'])
                            for pp in au['per_pair']) or '（未展示）'))
    out.append('【证据】每条证据都带出处与引擎算出的数字：')
    out.append(evidence.render_text(blocks))
    out.append('【出处】%s（pid 的文件名#数组下标可直接点回语料原文；语料为公开整理本，'
               '据公开整理本复算，不作学术引证）。'
               % '；'.join('[%s] -> %s' % (b['eid'], b['pid']) for b in blocks))
    out.append('【推断边界｜%s问句】%s' % (kind, BOUNDARIES[kind]))
    text = '\n'.join(out)
    allow = re.findall(r'\d+(?:\.\d+)?', spec.describe()) + _allow_disclose(pnote, spec)
    allow += [g['scope_n'], g['scope_all'], g['n_groups'], g['n_pairs'],
              g['n_covered'], len(blocks)]
    allow += [g['n_short'], g['min_len']] + list(range(1, len(g['groups']) + 3))
    allow += [x for _d, ng, np_ in g['by_dyn'] for x in (ng, np_)]
    allow += [grp['n'] for grp in g['groups']] + [len(grp['sig']) for grp in g['groups']]
    allow += [grp['n_cipai'] for grp in g['groups']]
    allow += [au['n_groups'], au['n_pairs']]
    for pp in au['per_pair']:
        allow += [pp['n_pos'], pp['n_diff']]
    for b in blocks:
        # 审查 B42：pid 里是 '#0004'，直接加进白名单得到 '0004'，模板写 '4' 就会被判无出处
        allow += [str(int(n)) for n in re.findall(r'\d+', b['pid'])]
    ok, problems = guard.verify(text, blocks, boundary_kind=kind, allow=allow)
    narrator, narrative = 'template', None
    if (narrate or argument) and llm is not None and getattr(llm, 'available', lambda: False)():
        if on_engine is not None:
            # 「答案先到」：配对题的确定性结论（组数/对数/复核）此刻已算完，先如实发给前端。
            on_engine({'question': question, 'spec': spec.describe(), 'kind': kind,
                       'blocks': blocks,
                       'answer': text + _verdict_line(ok, problems, GUARD_PASS_PAIR),
                       'verify': (ok, problems),
                       'refused': False, 'problems': problems, 'total': g['scope_n'],
                       'narrator': 'template', 'narrative': None,
                       'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
                       'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed),
                       'safety': {'ok': True}})
        res_now = {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': blocks,
                   'pair_fact': ('【题型：配对题】本题问的是「找出几对…相同」——答案是一批**对子**'
                                 '（每对两篇），不是「有哪些篇满足某条件」。共 %d 组、%d 对，'
                                 '本例展示 %d 对；判定量是全篇逐位平仄串。'
                                 % (g['n_groups'], g['n_pairs'], len(g['groups'])))}
        r = gen.produce(llm, res_now, kind, BOUNDARIES[kind], argument=argument,
                        on_delta=on_delta)
        narrative = r
        if r['ok']:
            title = '论证辅助草稿' if argument else '论证表述'
            text2 = text + '\n【%s（大模型 %s，已过四道护栏）】\n%s' % (title, r['model'], r['text'])
            allow2 = list(allow) + _nums(r['model'])
            ok2, p2 = guard.verify(text2, blocks, boundary_kind=kind, allow=allow2)
            if ok2:
                text, ok, problems, narrator = text2, ok2, p2, r['model']
            else:
                problems = p2
                narrative = dict(r, ok=False, problems=(r['problems'] + p2)
                                 or ['合并后未过护栏（未给出具体项）'])
                narrator = 'template（大模型稿合并后未过护栏，已回退）'
        else:
            narrator = 'template（大模型稿未过护栏，已回退）'
    text += _verdict_line(ok, problems, GUARD_PASS_PAIR)
    return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': blocks,
            'answer': text, 'verify': (ok, problems), 'refused': False, 'problems': problems,
            'total': g['scope_n'], 'narrator': narrator, 'narrative': narrative,
            'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
            'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed),
            'pair': {'n_groups': g['n_groups'], 'n_pairs': g['n_pairs'],
                     'scope_n': g['scope_n'], 'n_covered': g['n_covered'],
                     'by_dyn': g['by_dyn'], 'label': spec.pair_label,
                     'audit': {'n_groups': au['n_groups'], 'n_pairs': au['n_pairs'],
                               'per_pair': au['per_pair']},
                     'groups': [{'sig': grp['sig'], 'n': grp['n'],
                                 'same_cipai': grp['same_cipai'],
                                 'pids': [p['pid'] for p in grp['poems']]}
                                for grp in g['groups']]},
            'safety': {'ok': True}}


def answer(conn, question, topk=3, with_lines=1, kind=None, llm=None, narrate=False,
           argument=False, llm_parse=False, llm_policy='always', on_delta=None,
           on_engine=None, context=None):
    """执行一次完整问答，返回 dict（回答文本、证据块、护栏结论、问句类型、是否拒答）。

    `llm_parse=True` 时先让大模型理解问句（条件经引擎校验），否则用规则解析。
    `llm` 给一个 `llm.LLM` 实例且 `narrate/argument` 为真时，会在**确定性模板之外**
    再让大模型写一段「说法」（叙述或论证草稿）；该段必须同时过 `guard` 与 `safety`，
    否则整段丢弃、回落模板。**不传 llm 时行为与从前逐字一致**（确定性内核不变）。
    `on_delta` 收大模型逐字增量；`on_engine` 在**确定性结论已算完、大模型尚未开写**时
    被回调一次（「答案先到、说法后补」；网页流式端点据此先渲染答案，不必干等模型）。
    `context` 为上一轮「问句＋解析」摘要（多轮指代补全；只在 llm_parse 路生效）。
    """
    kind = kind or classify_question(question)
    # 内容安全护栏（入向）：命中就不进检索（作品规范第七点（三）(5)）
    sf = safety.check(question, 'in')
    if not sf['ok']:
        text = safety.refusal(sf['category'])
        # 审查 B23：护栏**没跑过**却回 (True, []) ，界面会显示「护栏通过」——必须说清
        return {'question': question, 'spec': '（已在内容安全环节拦截，未进入检索）',
                'kind': '安全拦截', 'blocks': [], 'answer': text,
                'verify': (True, ['（未执行：内容安全拦截，数字与引用护栏本次未跑）']),
                'verify_kind': 'safety', 'refused': True, 'problems': [],
                'safety': sf, 'narrator': 'safety'}
    spec, pnote = understand(conn, question, llm=llm, llm_parse=llm_parse,
                             llm_policy=llm_policy, context=context)
    # ⭐ **意图覆盖自检**：问句里出现「哪个词人/词牌/朝代…最多/最少」这类**分组极值意图**，
    #    而最终既没有分组统计、也没有排序/配对意图 → **如实认账**，绝不拿检索结果冒充答案。
    #    这一条是 2026-10-01 主人运行记录里那个 bug 的「防复发闸」：
    #    当时系统答「融合排序最前者是丁澎」，用户问的却是「哪个词人最多」——答非所问且报「护栏通过」。
    _ge = retrieve._group_extreme_of(question)
    if _ge[0] and not (spec.agg or getattr(spec, 'order_by', None)
                       or getattr(spec, 'pair', None)):
        _t = ('现有语料未见支持：这句话问的是**按%s分组、取%s**，而本次没能把它解析成分组统计，'
              '因此不给「看起来像答案」的检索结果。请改写成明确的分组问法，例如'
              '「句脚为平 清 临江仙的清词中哪个词人的词最多」；'
              '或去掉分组意图、只做条件检索。' % (
                  {'author': '词人', 'cipai': '词牌', 'dynasty': '朝代'}.get(_ge[0], _ge[0]),
                  '最多' if _ge[1] == 'max' else '最少'))
        _ok, _pb = guard.check_no_support(_t, True)
        return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                'answer': _t, 'verify': (_ok, _pb), 'refused': True, 'problems': _pb,
                'total': None, 'narrator': 'template', 'safety': {'ok': True},
                'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
                'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed), 'agg': None}
    # ⭐ **「模糊意图」自检**（2026-10-01 深夜，答案级实测驱动，与上面那条是同族问题的
    #    下一个入口）：问句没解析出**任何**形式条件，却带着语义/评价/意图类请求
    #    （中心思想／最好／为什么／有名／开心的词…）时，**不许**把「融合排序前几篇」端上去。
    #    实测旧版对「唐诗里最有名的五言绝句」答「融合排序最前者为 元·关汉卿《钱大尹智宠谢天香》」，
    #    护栏还报「通过」——这正是「答非所问却报通过」，比崩溃更危险。
    if (_no_hard_condition(spec) and not spec.agg and not getattr(spec, 'pair', None)
            and not getattr(spec, 'order_by', None) and VAGUE_ASK_RE.search(question)):
        _why = ('问句涉及语料外范围（%s），本系统语料只含清/宋/元三代词作' % spec.unsupported
                if spec.unsupported else
                '这句话问的是语义／评价／意图层面，而问句里没有可检索的形式条件')
        _t = ('现有语料未见支持：%s。本系统的检索只能按形式与字面条件工作'
              '（朝代／词人／词牌／句脚字／声律模式／数值区间等），不拿融合排序的前几篇冒充答案。'
              '可改成带形式条件的问法——例如给出朝代、词牌或数值区间；'
              '若想研讨某一篇的意涵，请先指明篇目（作者＋词牌），再结合证据块的逐句原文自行审读。'
              % _why)
        _ok, _pb = guard.check_no_support(_t, True)
        return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                'answer': _t, 'verify': (_ok, _pb), 'refused': True, 'problems': _pb,
                'total': None, 'narrator': 'template', 'safety': {'ok': True},
                'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
                'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed)}
    if spec.agg:
        return _answer_agg(conn, question, spec, pnote, kind='数值型', llm=llm,
                           narrate=narrate, argument=argument, on_delta=on_delta,
                           on_engine=on_engine)
    if getattr(spec, 'pair', None):
        return _answer_pair(conn, question, spec, pnote, kind='数值型', llm=llm,
                            narrate=narrate, argument=argument, topk=topk, on_delta=on_delta,
                            on_engine=on_engine)
    rows = retrieve.search(conn, spec, topk=topk)
    total = retrieve.count_hits(conn, spec)          # 真·命中篇数（不是 top-k）
    # 多值字段（如「句脚是「灯」或者「声」」）：**每个取值都必须在展示里露面**。
    # 否则条件解对了，例子却只举了一半——读者无法验证另一个取值到底有没有例。
    cover = retrieve.cover_fields(spec)
    cov = {}
    if cover:
        pool = retrieve.search(conn, spec, topk=max(40, topk * 8))
        rows, eff = retrieve.pick_covering(conn, spec, pool, cover, topk)
        with_lines = max(with_lines, min(3, max(len(v) for v in cover.values())))
        if eff > topk:
            topk = eff
    if not rows:
        text = NO_SUPPORT % spec.describe()
        # 拒答文本会**回显查询条件**（其中可能含用户自己给的数字），先剔掉再查护栏③
        ok, problems = guard.check_no_support(text.replace(spec.describe(), ''), True)
        return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                'answer': text, 'verify': (ok, problems), 'refused': True, 'problems': problems}

    blocks = evidence.build_blocks(conn, rows, with_lines=with_lines, spec=spec)
    if not blocks:
        # 审查 B1：旧写法直接 `b0 = blocks[0]` → IndexError。无据就**认账**（不许崩，也不许举例冒充）
        _t = ('现有语料未见支持：本次检索没有可引用的篇目。本系统不拿语义相近的篇凑数，'
              '请换个问法或放宽条件。')
        _ok, _pb = guard.check_no_support(_t, True)
        return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                'answer': _t, 'verify': (_ok, _pb), 'refused': True, 'problems': _pb,
                'total': total, 'narrator': 'template', 'safety': {'ok': True}}
    # 结果自查：逐篇用另一条路径（Python 侧逐条比对）复核是否真的满足问句的全部条件
    cond_bad = []
    for b in blocks:
        v = retrieve.verify_spec_on_poem(conn, b['pid'], spec)
        if v:
            cond_bad.append('%s：%s' % (b['eid'], '；'.join(v)))
    b0 = blocks[0]
    # 极值／排序题：答案就是该指标的极值篇目——必须**独立复算**一遍再写进答复
    ei = retrieve.extreme_info(conn, spec) if getattr(spec, 'order_by', None) else None
    # 行级条件题：展示**命中的那一句**，而不是「仄声占比最高的句」（否则答非所问）
    L = next((x for x in b0['lines'] if x.get('matched')), None) or (b0['lines'][0] if b0['lines'] else None)
    # 放行【非论断性数字】：查询条件里用户给的阈值、pid 里的编号（定位串）、命中总数、展示篇数
    allow = re.findall(r'\d+(?:\.\d+)?', spec.describe())
    allow += _allow_disclose(pnote, spec)
    allow.append(len(blocks))
    if total is not None:
        allow.append(total)
    for b in blocks:
        allow += re.findall(r'\d+', b['pid'])
    if ei:
        allow += [ei['value'], ei['n_ties']]
    out = []
    out.append(_parse_head(spec, pnote))
    if cover:
        cov = retrieve.coverage_of(conn, blocks, cover)
        label = {'tail': '句脚字', 'cipai': '词牌', 'author': '词人', 'dynasty': '朝代'}
        segs, miss = [], []
        for attr in cover:
            segs.append('%s ' % label.get(attr, attr)
                        + '／'.join('%s %d 篇' % (v, cov[attr][v]) for v in cover[attr]))
            for v in cover[attr]:
                if cov[attr][v] == 0:
                    t = retrieve.count_for_value(conn, spec, attr, v)
                    if t:
                        miss.append('%s=%s（语料中 %d 篇，本次未展示）'
                                    % (label.get(attr, attr), v, t))
                    else:
                        miss.append('%s=%s（语料中 0 篇，无例可举）'
                                    % (label.get(attr, attr), v))
        out.append('【展示覆盖】' + '；'.join(segs)
                   + '（共展示 %d 篇；被查的每个取值都至少举了一例）' % len(blocks))
        if miss:
            out.append('　　　未覆盖：' + '；'.join(miss))
            for attr in cover:
                for v in cover[attr]:
                    if cov[attr][v] == 0:
                        allow.append(retrieve.count_for_value(conn, spec, attr, v))
        for attr in cover:
            allow += list(cov[attr].values())
    if total is None:
        head = ('【结论】未给结构化条件，按语义相关度排序（融合分）展示前 %d 篇；'
                '融合排序最前者为 '
                '%s·%s《%s》：全篇 %d 句 / %d 字，平 %d、仄 %d，仄声比例 %.1f%%，声情 %s [E1]。'
                % (len(blocks), b0['dynasty'], b0['author'], b0['title'], b0['sent_n'],
                   b0['han_len'], b0['ping'], b0['ze'], b0['ze_ratio'], b0['scene']))
    elif ei is not None:
        more = '（按【%s%s】排序展示前 %d 篇）' \
               % (ei['label'], '取最高' if spec.extreme == 'max' else '取最低', len(blocks))
        head = ('【结论】在条件〔%s〕下共命中 %d 篇%s；其中【%s】%s的是 %s·%s《%s》：'
                '全篇 %d 句 / %d 字，平 %d、仄 %d，仄声比例 %.1f%%，声情 %s [E1]。'
                % (spec.describe(), total, more, ei['label'],
                   '最高' if spec.extreme == 'max' else '最低',
                   b0['dynasty'], b0['author'], b0['title'], b0['sent_n'],
                   b0['han_len'], b0['ping'], b0['ze'], b0['ze_ratio'], b0['scene']))
    else:
        more = '（全库仅此 %d 篇，已全部列出）' % total if total <= len(blocks) \
            else ('（此处展示 %d 篇，已保证被查的每个取值各有实例）' % len(blocks) if cover
                  else '（此处展示融合排序前 %d 篇；本问没有指定排序指标）' % len(blocks))
        head = ('【结论】在条件〔%s〕下共命中 %d 篇%s；融合排序最前者为 %s·%s《%s》：'
                '全篇 %d 句 / %d 字，平 %d、仄 %d，仄声比例 %.1f%%，声情 %s [E1]。'
                % (spec.describe(), total, more, b0['dynasty'], b0['author'], b0['title'],
                   b0['sent_n'], b0['han_len'], b0['ping'], b0['ze'], b0['ze_ratio'],
                   b0['scene']))
    out.append(head)
    if ei is not None:
        # 「引擎算的就是答案」也要能被另一条路径复算：这里写的是**独立 SQL 重算**的结果
        vtxt = ('%.1f' % ei['value']) if spec.order_by in ('ze_ratio', 'ping_ratio', 'change') \
            else ('%d' % round(ei['value']))
        if ei['n_ties'] <= 1:
            ties, tname = '；无并列', ''
        else:
            ties = '；并列 %d 篇' % ei['n_ties']
            if ei['n_ties'] <= len(blocks):
                ties += '（已一并列入）'
            else:
                ties += '（此处展示前 %d 篇）' % len(blocks)
            tname = '：' + '、'.join('%s《%s》' % (r[2], r[4]) for r in ei['ties'][:6])
            if ei['n_ties'] > 6:
                tname += ' 等'
        out.append('　　　【极值复核】引擎独立复算：%s中【%s】的%s = %s（与首篇一致）%s%s；'
                   '比较范围＝%s。'
                   % ('以上条件', ei['label'],
                      '最大值' if spec.extreme == 'max' else '最小值',
                      vtxt, ties, tname, ei['scope']))
    if L:
        out.append('　　　该篇第 %d 句「%s」%d 字，平 %d 仄 %d，平仄串 %s%s [E1]。'
                   % (L['idx'] + 1, L['text'], L['han_len'], L['ping'], L['ze'], L['pz'],
                      _line_note(spec, L)))
    for b in blocks[1:]:
        m = next((x for x in b['lines'] if x.get('matched')), None)
        note = ''
        if m is not None:
            rs = m.get('match_reasons') or []
            if '句脚字' in rs:
                note = '；该篇第 %d 句以 %s 收句' % (m['idx'] + 1, m.get('tail') or '')
            elif '句脚平仄' in rs:
                note = '；该篇第 %d 句句脚为%s' % (m['idx'] + 1, (m.get('pz') or '')[-1:])
            elif '声律模式' in rs:
                note = '；该篇第 %d 句合声律模式 %s' % (m['idx'] + 1, spec.pz or '')
        out.append('　　　另见 [%s] %s·%s《%s》：%d 句 / %d 字，仄声比例 %.1f%%，声情 %s%s。'
                   % (b['eid'], b['dynasty'], b['author'], b['title'], b['sent_n'], b['han_len'],
                      b['ze_ratio'], b['scene'], note))
    out.append('【证据】每条证据都带出处与引擎算出的数字：')
    out.append(evidence.render_text(blocks))
    out.append('【出处】%s（pid 的文件名#数组下标可直接点回语料原文；语料为公开整理本，'
               '据公开整理本复算，不作学术引证）。'
               % '；'.join('[%s] -> %s' % (b['eid'], b['pid']) for b in blocks))
    out.append('【推断边界｜%s问句】%s' % (kind, BOUNDARIES[kind]))
    text = '\n'.join(out)

    ok, problems = guard.verify(text, blocks, boundary_kind=kind, allow=allow)
    if cond_bad:                      # 结果自查不通过 → 整体判不过（宁可报错，不许静默错）
        ok = False
        problems = list(problems) + ['条件复核未通过：%s' % '；'.join(cond_bad)]
    narrator = 'template'
    narrative = None
    if (narrate or argument) and llm is not None and getattr(llm, 'available', lambda: False)():
        if on_engine is not None:
            # 「答案先到」：主检索路的确定性结论（含证据块与护栏结论）此刻已算完，
            # 先如实发给前端；大模型的「论证表述」随后边写边补（实测省 1~5 秒干等）。
            on_engine({'question': question, 'spec': spec.describe(), 'kind': kind,
                       'blocks': blocks,
                       'answer': text + _verdict_line(ok, problems, GUARD_PASS_MAIN),
                       'verify': (ok, problems),
                       'refused': False, 'problems': problems, 'total': total,
                       'cond_violations': cond_bad, 'extreme': ei,
                       'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
                       'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed),
                       'narrator': 'template', 'narrative': None})
        res_now = {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': blocks}
        if ei is not None:
            res_now['extreme_fact'] = ('【题型：极值题】本题问的是「哪一首…%s」，答案就是极值篇目，'
                                       '**不是**在找共同特征：条件内【%s】的%s = %.1f'
                                       '（并列 %d 篇），首篇即 %s·%s《%s》。'
                                       % ('最高' if spec.extreme == 'max' else '最低',
                                          ei['label'],
                                          '最大值' if spec.extreme == 'max' else '最小值',
                                          ei['value'], ei['n_ties'],
                                          b0['dynasty'], b0['author'], b0['title']))
        r = gen.produce(llm, res_now, kind, BOUNDARIES[kind], argument=argument,
                        on_delta=on_delta)
        narrative = r
        if r['ok']:
            title = '论证辅助草稿' if argument else '论证表述'
            text2 = text + '\n【%s（大模型 %s，已过四道护栏）】\n%s' % (title, r['model'], r['text'])
            # 标题里的模型名是**出处标记**（如 glm-4-flash 的 4），不是对语料下的断言，
            # 与 pid 里的编号同等对待——否则自己的标题会把稿子卡掉（实测踩过）。
            allow2 = list(allow) + _nums(r['model'])
            ok2, p2 = guard.verify(text2, blocks, boundary_kind=kind, allow=allow2)
            if ok2:
                text, ok, problems, narrator = text2, ok2, p2, r['model']
            else:                       # 合并后过不了 → 保守做法：整段不带
                problems = p2
                # 一定要把**具体原因**留下来（只写「未过护栏」等于丢掉诊断信息）
                narrative = dict(r, ok=False, problems=(r['problems'] + p2)
                                 or ['合并后未过护栏（未给出具体项）'])
                narrator = 'template（大模型稿合并后未过护栏，已回退）'
        else:
            narrator = 'template（大模型稿未过护栏，已回退）'
    text += _verdict_line(ok, problems, GUARD_PASS_MAIN)
    return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': blocks,
            'answer': text, 'verify': (ok, problems), 'refused': False, 'problems': problems,
            'total': total, 'cond_violations': cond_bad, 'extreme': ei,
            'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
            'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed),
            'narrator': narrator, 'narrative': narrative}


def main():
    ap = argparse.ArgumentParser(description='可溯源问答（检索 + 证据 + 四道护栏）')
    ap.add_argument('--db', required=True)
    ap.add_argument('--question', required=True)
    ap.add_argument('--topk', type=int, default=3)
    ap.add_argument('--kind', default=None, help='强制问句类型（测试用）')
    ap.add_argument('--llm', action='store_true', help='启用国产大模型「说法层」（需密钥，可用时）')
    ap.add_argument('--llm-parse', action='store_true',
                    help='用大模型**理解问句**（条件经引擎校验；失败回落规则解析）')
    ap.add_argument('--argument', action='store_true', help='生成「论证辅助草稿」而不是普通叙述')
    ap.add_argument('--provider', default=None, help='指定模型服务商 zhipu/deepseek/dashscope')
    ap.add_argument('--llm-policy', default='always', choices=('always', 'auto', 'never'),
                    help='always=每次都让大模型听（默认）；auto=规则已够用则略过（省 1.4~5.7 秒，结论不变）；'
                         'never=只用规则')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    client = None
    if args.llm or args.argument or args.llm_parse:
        import llm as _llm
        client = _llm.LLM(provider=args.provider)
        if not client.available():
            sys.stderr.write('（未取到国产大模型密钥，本次按模板作答：%s）\n' % client.last_error)
    res = answer(conn, args.question, topk=args.topk, kind=args.kind, llm=client,
                 narrate=args.llm, argument=args.argument, llm_parse=args.llm_parse, llm_policy=args.llm_policy)
    if args.json:
        res2 = dict(res)
        res2['blocks'] = [{k: v for k, v in b.items() if k != 'raw'} for b in res['blocks']]
        print(json.dumps(res2, ensure_ascii=False, indent=1))
    else:
        print(res['answer'])
        # 大模型稿被丢弃时**必须说出来**（不能静默回落，否则用户以为那是模型写的）
        nv = res.get('narrative') or {}
        if (args.llm or args.argument) and not nv.get('ok'):
            sys.stderr.write('（大模型稿未采纳，已回落确定性模板：%s）\n'
                             % '；'.join(nv.get('problems') or ['未知原因']))
    conn.close()
    return 0 if res['verify'][0] else 1


if __name__ == '__main__':
    sys.exit(main())
