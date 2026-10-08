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



def _with_unsupported(spec, ok, problems):
    """⚠ 2026-10-02 修：**守卫必须知道"引擎认账了没"**。

    引擎表达不出来的算子会被 `retrieve` 记进 `spec.unparsed`（如「本系统暂不支持：全称量词…」）。
    旧版守卫只看"数字有没有出处"，于是**带着认账的答案照样报「通过」**——
    审计 1000 题里 863 条"守卫失职"正是这么来的。这里把认账内容并入 problems 并判未通过。
    """
    uns = [x for x in (getattr(spec, 'unparsed', None) or [])
           if retrieve.UNSUPPORTED_TAG in x]
    if uns:
        return False, list(problems) + uns
    return ok, problems


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
    """是否**没有任何**可检索的形式条件（朝代/词人/词牌/声情/声律/句脚/数值区间/句级算子）。

    与 `retrieve.search` 的 `restrict` 判据同源（`retrieve.has_hard`，单一来源的语义，两处别走样）。
    """
    return not retrieve.has_hard(spec)


_CN_D = '一二三四五六七八九十'


def _cn(n):
    """阿拉伯数字 → 汉字数字（护栏要求回答文案**不含阿拉伯数字**；序号最大到几十，够用）。"""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if n <= 0:
        return str(n)
    if n <= 10:
        return _CN_D[n - 1]
    if n < 20:
        return '十' + _CN_D[n - 11]
    if n < 100:
        return _CN_D[n // 10 - 1] + '十' + (_CN_D[n % 10 - 1] if n % 10 else '')
    return str(n)


def _extract_answer(conn, spec, blocks):
    """**提取型问题**（第 N 句第 M 字）的正面回答：从命中的篇里把那个字取出来。

    由来（2026-10-08 主人实测）：「高旭《浪淘沙·杨笃生自沉利物浦死，吊以此阕》**第四句第三字**
    是哪个字」——正确篇目**已经命中**，但系统把「第四句第三字」当**检索词面**，于是答了句脚，
    **答非所问**。这类问句要的不是筛篇，而是「**在已定的这一篇里取第 N 句第 M 个字**」。

    纪律（与全项目一致）：
      ① 取字按**汉字序列**（跳过标点与空白）——与语料「不计标点」的既有口径一致；
      ② 句序/字序**越界就如实说明**，绝不硬凑或改口径；
      ③ 多个篇目命中时**逐篇列出**（最多五篇），不替用户选；
      ④ 文案**不含阿拉伯数字**（护栏要求），序号一律用汉字数字。
    """
    ex = getattr(spec, 'extract', None) or {}
    try:
        sn, ps = int(ex.get('sent') or 0), int(ex.get('pos') or 0)
    except Exception:
        return ''
    if sn < 1 or ps < 1 or not blocks:
        return ''
    parts = []
    for b in blocks[:5]:
        pid = b.get('pid')
        title = b.get('title') or b.get('cipai') or ''
        try:
            rows = conn.execute('SELECT idx,text FROM lines WHERE pid=? ORDER BY idx', (pid,)).fetchall()
        except Exception:
            rows = []
        if len(rows) < sn:
            parts.append('《%s》全篇只有%s句，没有第%s句' % (title, _cn(len(rows)), _cn(sn)))
            continue
        L = rows[sn - 1]
        han = [c for c in (L['text'] or '') if retrieve.is_hanzi(c)]
        if len(han) < ps:
            parts.append('《%s》第%s句「%s」只有%s个字，没有第%s个' % (
                title, _cn(sn), (L['text'] or '').strip(), _cn(len(han)), _cn(ps)))
            continue
        parts.append('《%s》第%s句是「%s」，其中第%s个字是「%s」' % (
            title, _cn(sn), (L['text'] or '').strip(), _cn(ps), han[ps - 1]))
    if not parts:
        return ''
    return '【提取】%s。' % '；'.join(parts)


def _line_note(spec, L):
    """给展示句加一句「为什么展示它」的说明（行级条件题专用）。"""
    rs = L.get('match_reasons') or []
    if '句脚字' in rs:
        return '（此句句脚为 %s，合问句条件）' % (L.get('tail') or '')
    if '句脚平仄' in rs:
        return '（此句句脚为%s，合问句条件）' % ((L.get('pz') or '')[-1:] or '')
    if '声律模式' in rs:
        return '（此句合声律模式 %s）' % (spec.pz or '')
    # ⚠ 2026-10-08 加：高级句级算子（`pz_exact` / `tail_each` / `line_q`）的命中句说明。
    #   证据层此前已能正确算出命中句（见 retrieve.line_satisfies），但这里没有对应分支
    #   → 命中句「无说明」，用户看不出「为什么展示这一句」。
    if '平仄串全等' in rs:
        return '（此句整句平仄为 %s，合问句条件）' % (L.get('pz') or spec.pz_exact or '')
    if '篇内交集·句脚字' in rs:
        return '（此句句脚为 %s，合篇内交集条件）' % (L.get('tail') or '')
    if '句级算子·满足句' in rs:
        return '（此句合句级条件）'
    return ''


def _clean_frag(s):
    """披露用的片段：去掉引号类字符（「」只用于引用语料原文，不能用在说明里）。"""
    return re.sub(r'[「」『』“”]', '', str(s)).strip()


def _title_hint(conn, spec):
    """命中 0 篇时的**只读兜底提示**：这些关键词其实是不是**题名**？

    ⚠ 2026-10-05 新增（朋友实测驱动）。由来：「蝶恋花·清明同诸子集原白斋中」被当成
    「词面」去正文里搜 → 0 命中，而它其实是**题名**（库里 title 恰好 1 篇）。
    这里只做**提示**、不改检索结论——把「为什么是 0」说清楚：
      · 关键词在 title 命中 → 明说「这是题名（词题），不是正文」，并给正确写法；
      · 都没命中 → 返回空串（保持原样，不干扰既有文案）。
    文案纪律：**不含阿拉伯数字、不含引号**（`「」` 只用于引用语料原文），
    以免污染护栏校验；命中篇数一律用汉字数词表述。
    """
    kws = [k for k in (getattr(spec, 'keywords', None) or []) if len(k) >= 2]
    if not kws:
        return ''
    hit_titles = []
    for kw in kws[:6]:
        try:
            row = conn.execute(
                'SELECT title FROM poems WHERE title LIKE ? LIMIT 1',
                ('%' + kw + '%',)).fetchone()
        except Exception:
            row = None
        if row and row[0]:
            hit_titles.append((kw, row[0]))
    if not hit_titles:
        return ''
    kw, ttl = hit_titles[0]
    more = ('；另有「%s」等同样命中题名' % hit_titles[1][0]
            if len(hit_titles) > 1 else '')
    return ('\n　　　⚠ 提示：检索词「%s」在**题名**中命中（如《%s》%s），'
            '但**不在正文中**——应按**题名（词题）**检索，而不是当作词原文。'
            '若已知词牌，可用「词牌·题名」的写法（如「…·%s」）让系统直接定位题名。'
            % (kw, ttl, more, kw))


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


_RNG_NOTE_LABEL = {'ze_min': '仄声比例下限', 'ze_max': '仄声比例上限', 'len_min': '字数下限',
                   'len_max': '字数上限', 'sent_min': '句数下限', 'sent_max': '句数上限',
                   'change_min': '变化下限', 'change_max': '变化上限', 'thr_min': '阈值下限',
                   'thr_max': '阈值上限'}


def _copy_rule_hard(spec, rule, notes, skip_scene=False):
    """把规则路听出的**硬条件**补进大模型 spec（只补不替；同键冲突时规则赢并如实注明）。

    为什么必须（2026-10-03 晚，网页端实测驱动）：大模型理解层（qlm）的 JSON **没有**
    句级量词（没有任何一句／至少有一句／每一句都…）、平仄串全等、两值交集、一致性这些
    字段，数值区间也常听漏或放错位置（实测：zhipu 把 len_min 等放在顶层被整组忽略、
    qwen 只听出「四到十句」而漏了「没有任何一句句长在七到十一字」）。规则路明明解析出
    了这些**确定性条件**，旧版却只把它放进「alt」备注里披露、不执行——残缺 spec 照单
    执行 → 按语义相关度排序 → 答非所问（实测：本应命中 3876 篇的条件题，答成全库残片）。

    只补**确定性**字段；不碰 dynasty/author/cipai（分组对比与组内极值会**故意**清空
    这些维度，盲目补回会改变题型——朝代已有专门的安全网）。返回是否发生了补齐/冲突。
    """
    copied, conflict = [], []
    if rule.line_q and not spec.line_q:
        spec.line_q = dict(rule.line_q)
        copied.append('句级算子')
    if rule.pz_exact and not spec.pz_exact:
        spec.pz_exact = rule.pz_exact
        copied.append('平仄串全等')
    if rule.tail_each and not spec.tail_each:
        spec.tail_each = list(rule.tail_each)
        copied.append('篇内两值交集')
    if getattr(rule, 'consist', None) and not getattr(spec, 'consist', None):
        spec.consist = rule.consist
        copied.append('一致性')
    spec.rng = spec.rng or {}
    for k, v in sorted((rule.rng or {}).items()):
        if k not in spec.rng:
            spec.rng[k] = v
            copied.append(_RNG_NOTE_LABEL.get(k, k))
        elif spec.rng[k] != v:
            conflict.append('%s（模型=%s、规则=%s）' % (_RNG_NOTE_LABEL.get(k, k),
                                                         spec.rng[k], v))
            spec.rng[k] = v
    if rule.tail_any and not spec.tail_any:
        spec.tail_any = list(rule.tail_any)
        copied.append('句脚字')
    if rule.tail_pz and not spec.tail_pz:
        spec.tail_pz = rule.tail_pz
        copied.append('句脚平仄')
    if rule.pz and not spec.pz:
        spec.pz = rule.pz
        copied.append('声律模式')
    if rule.scene and not spec.scene and not skip_scene:
        spec.scene = rule.scene
        copied.append('声情')
    if copied:
        notes.append('句级/范围/字面条件由规则解析补齐（%s）：大模型未听出的确定性条件不丢弃'
                     % '、'.join(copied))
    if conflict:
        notes.append('数值条件两路不一致（%s），已改用规则解析的' % '；'.join(conflict))
    return bool(copied or conflict)


def _covered_terms(rule):
    """规则路条件里**已经表达过**的量：数字／声律串／句脚字（用于「冗余条件」过滤）。"""
    nums, pzs, tails, names = set(), set(), set(), set()
    lq = rule.line_q or {}
    _k, _v = (lq.get('pred') or (None, None))
    if _k == 'len' and isinstance(_v, (list, tuple)) and len(_v) == 2:
        nums.update(int(x) for x in _v)
    elif _k == 'pz' and isinstance(_v, str):
        pzs.add(_v)
    elif _k == 'tail' and isinstance(_v, str):
        tails.add(_v)
    elif _k == 'tail_any':
        tails.update(_v or [])
    elif _k == 'tail_pz' and _v in ('平', '仄'):
        tails.update(['平', '仄'])
    if rule.pz_exact:
        pzs.add(rule.pz_exact)
    for _c in (rule.tail_each or []):
        tails.add(_c)
    for _v in (rule.tail_any or []):
        tails.add(_v)
    if rule.pz:
        pzs.add(rule.pz)
    for k, v in (rule.rng or {}).items():
        if isinstance(v, (int, float)):
            nums.add(v)
    for attr in ('dynasty_any', 'author_any', 'cipai_any'):
        names.update(str(x) for x in (getattr(rule, attr) or []))
    return {'nums': nums, 'pz': pzs, 'tails': tails, 'names': names}


def _drop_redundant(spec, rule, notes):
    """丢掉大模型**重复编码**出来的条件（规则路已经表达过同一个量）。

    ⚠ 2026-10-04（主人实测：多轮上下文里问「四到十句之间，没有任何一句句长在七到十一字之间…」）：
    模型把**句长区间 7~11**（规则路已用句级算子「句级算子=没有任何一句（句长=7~11）」表达）
    又编码成一条篇级「阈值≥7；阈值≤11」——多出来的这条把命中数从 **3876 篇砍成 486 篇**。
    与「规则路已覆盖的句脚字不再补」同一口径：**同一个量不因为换了个字段就重复生效**。
    """
    cov = _covered_terms(rule)
    dropped = []
    for k in list((spec.rng or {}).keys()):
        if k in (rule.rng or {}):
            continue                      # 键相同由「同键冲突规则赢」处理，不在这里管
        v = spec.rng[k]
        if isinstance(v, (int, float)) and any(abs(v - c) < 1e-9 for c in cov['nums']):
            spec.rng.pop(k)
            dropped.append({'ze_min': '仄声比例下限', 'ze_max': '仄声比例上限',
                            'len_min': '字数下限', 'len_max': '字数上限',
                            'sent_min': '句数下限', 'sent_max': '句数上限',
                            'change_min': '变化下限', 'change_max': '变化上限',
                            'thr_min': '阈值下限', 'thr_max': '阈值上限'}.get(k, k))
    if spec.pz and spec.pz in cov['pz']:
        spec.pz = None
        dropped.append('声律模式')
    _keep_tails = [t for t in (spec.tail_any or []) if t not in cov['tails']]
    if len(_keep_tails) != len(spec.tail_any or []):
        dropped.append('句脚字 %s' % '／'.join(
            t for t in (spec.tail_any or []) if t in cov['tails']))
        spec.tail_any = _keep_tails
        retrieve._finalize(spec)
    if dropped:
        notes.append('大模型重复编码的条件已忽略（同一个量规则解析已表达过：%s）'
                     % '、'.join(sorted(set(dropped))))
    return bool(dropped)


_ELLIPTIC_RE = re.compile(
    # 只认**真正省略/指代**的句式（「那…呢」「改成宋词呢」「上面那些」）；
    # ⚠ 不要放进「其/这/此/该」这类高频字——它们大量出现在自足问句里
    #   （「其仄声比例的中位数」），一放进去 1000 题里 183 题会被误判成省略型（实测）。
    r'(那(里|里面|些|首|篇|个)?呢[？?]?\s*$|呢[？?]?\s*$|改成|换成|改为'
    r'|上面(这|那)?(个|些|首|篇)?|上述|前面(这|那)?(个|些|首|篇)?|刚才|也是|同样|同理)')
_SELF_CONTAINED_MARK = ('本轮问句',)


def _looks_elliptic(question):
    """问句是否**省略/指代型**（「那里面呢」「改成宋词呢」）——只有这种才允许继承上下文。

    ⚠ 2026-10-04（D 段实测）：自足的问句即便带了上下文也**不该**被上下文改动条件
    （SYSTEM 提示词里就写着「本轮问句若已自足，就忽略上下文」，实测模型并不总遵守）。
    所以继承只对「看上去需要指代补全」的问句开放。
    """
    return bool(_ELLIPTIC_RE.search(question or ''))


def _ctx_attested_additions(model, ctx):
    """挑出「上下文里确有依据」的模型补充条件（多轮指代用）。

    ⚠ 2026-10-04（D 段全量实测，529 项不一致驱动）：**匹配口径必须严**——
      · 数字要**带边界**匹配（旧版 `'1' in ctx` 会让 `1` 命中 `1234` 里的 `1`，
        于是模型凭空多出的「句数≥1」被当成"上下文里有依据"照单收下，Q0001 命中数直接变了）；
      · 单字值（句脚字）必须是**引号里的字**才算依据——否则任何一个「平」字都能给
        「句脚平仄=平」背书（Q0019）。
    其余（朝代/词人/词牌/声情）按整串出现判断。
    """
    import re as _re
    ctx = ctx or ''
    quoted = set()
    for m in _re.finditer(r'[「『"\'《]([^」』"\'》]{1,8})[」』"\'》]', ctx):
        quoted.add(m.group(1))
    dyn = list(model.dynasty_any) if (model.dynasty_any
                                      and all(str(v) in ctx for v in model.dynasty_any)) else []
    au = list(model.author_any) if (model.author_any
                                    and all(str(v) in ctx for v in model.author_any)) else []
    cp = list(model.cipai_any) if (model.cipai_any
                                   and all(str(v) in ctx for v in model.cipai_any)) else []
    tails = [t for t in (model.tail_any or []) if t in quoted]
    scene = model.scene if (model.scene and model.scene in ctx) else None
    nums = {}
    for k, v in (model.rng or {}).items():
        vs = ('%d' % v) if isinstance(v, (int, float)) and float(v).is_integer() else str(v)
        if _re.search(r'(?<!\d)' + _re.escape(vs) + r'(?!\d)', ctx):
            nums[k] = v
    return {'dynasty': dyn, 'author': au, 'cipai': cp, 'tails': tails,
            'scene': scene, 'nums': nums}


def _copy_ctx_attested(base, model, ctx, notes):
    """带上下文（多轮）时：只把**上下文里确有依据**的模型补充并进规则路。

    为什么这样切：多轮指代（「那里面呢」「改成宋词呢」）确实是模型才有能力补的；
    但多轮也最容易让模型把上一轮的东西**顺手带进来**——所以只认「值在上下文文本里出现过」
    的补充，逐项如实注明，其余一概不补（与「不凭空增加条件」同一口径）。
    """
    ctx = ctx or ''
    got = []
    _add = _ctx_attested_additions(model, ctx)
    for attr, label, key in (('dynasty_any', '朝代', 'dynasty'),
                             ('author_any', '词人', 'author'),
                             ('cipai_any', '词牌', 'cipai')):
        cur = list(getattr(base, attr) or [])
        vals = [v for v in _add[key] if v not in cur]
        if vals:
            setattr(base, attr, cur + vals)
            got.append('%s %s' % (label, '／'.join(vals)))
    for k, v in _add['nums'].items():
        if k not in (base.rng or {}):
            base.rng[k] = v
            got.append('%s=%s' % (k, v))
    for t in _add['tails']:
        if t not in (base.tail_any or []):
            base.tail_any = list(base.tail_any) + [t]
            got.append('句脚字 %s' % t)
    if _add['scene'] and not base.scene:
        base.scene = _add['scene']
        got.append('声情 %s' % _add['scene'])
    if got:
        retrieve._finalize(base)
        notes.append('多轮补充由大模型给出、且在本轮上下文里有依据（%s）' % '、'.join(got))
    else:
        notes.append('大模型没有给出「上下文里有依据」的补充条件（本轮问句已自足）')
    return bool(got)


def _rule_conditions(rule):
    """规则路是否解析出了**条件**（「以规则路为准」判定的前置）。"""
    return bool(rule.line_q or rule.pz_exact or rule.tail_each or rule.consist or rule.rng
                or rule.dynasty_any or rule.author_any or rule.cipai_any or rule.scene
                or rule.tail_any or rule.pz or rule.tail_pz or rule.agg or rule.pair
                or rule.order_by)


def _rule_trustworthy(rule, question):
    """规则路是否「听全了」——听全了就**全权以规则路为准**，大模型多给/不同的一律忽略。

    ⚠ 2026-10-03 晚（网页端 B 段全量 1000 题实测驱动）：大模型理解层即使听出了整句，也常
    **多塞**条件——把「满足句数在 3~7（偶数句位）」另加成一条篇级「句数 3~7」（实测
    87 篇 vs 真值 1420 篇）、把「篇内两值交集=上」加成篇级「句脚字=上」（0 篇 vs 1 篇）、
    凭空加「声律模式=…／仄声比例≥…」整类阈值（Q0028：850 篇 vs 真值 3060 篇）。
    这些多出的条件**改的就是答案**。规则路是唯一经过 1000 题离线复核的路径——
    规则路听全时，执行必须以规则路为准（模型的听写只作核对披露）。
    """
    if not _rule_conditions(rule):
        return False
    if rule.keywords:
        return False          # 留了词面 → 规则路可能漏听（如多值并列），走「吸收残片」分支
    residue = [u for u in (rule.unparsed or [])
               if not any(t in str(u) for t in INFO_UNPARSED)]
    if residue:
        return False
    if any(w in (question or '') for w in DIR_WORDS) and not (rule.rng or rule.order_by):
        return False          # 方向词没落地 → 规则漏听
    return True


def _absorb_leftovers(base, model, notes):
    """规则路留了「词面」残片时：以**规则路为基**，只把与残片相关的模型条件并进来。

    职责边界（本轮确立）：大模型理解层只负责「替规则路消化它留在词面里的残片」——典型是
    多值并列「句脚是灯**或者**声」被规则路解析成 句脚=灯＋词面=声的；**不得凭空增加**
    规则路没有的条件（实测凭空多出的篇级句脚字／篇级句数／声律模式／比例阈值都在改答案）。
    返回是否有吸收。
    """
    left = ' '.join([str(x) for x in (base.keywords or [])]
                    + [str(x) for x in (base.unparsed or [])])
    if not left.strip():
        return False
    got = []
    # 句脚字：多值并列最常见的残片（模型的值出现在残片文本里 → 并入，或语义）。
    # ⚠ 但**规则路自己的条件已经覆盖**的值不再补——实测 Q0115/Q0714/Q0833 等 7 题：
    #   规则路已用「至少 2 句（句脚字=光）」＋篇内两值交集把字管住了，模型又补一条
    #   篇级「句脚字=光」，条件虽冗余、结论行却与真值口径不一致。
    _covered = set(base.tail_any or [])
    if base.line_q:
        _k, _v = (base.line_q.get('pred') or (None, None))
        if _k == 'tail' and isinstance(_v, str):
            _covered.add(_v)
        elif _k == 'tail_any':
            _covered.update(_v or [])
        elif _k == 'tail_pz' and _v in ('平', '仄'):
            _covered.update(['平', '仄'])
    for _c in (base.tail_each or []):
        _covered.add(_c)
    extra = [t for t in (model.tail_any or [])
             if t not in base.tail_any and t not in _covered and t in left]
    if extra:
        base.tail_any = list(base.tail_any) + extra
        base.keywords = [k for k in (base.keywords or [])
                         if not any(t in str(k) for t in extra)]
        got.append('句脚字 %s' % '／'.join(extra))
    # 朝代／词人／词牌：模型的值出现在残片文本里、且规则路没给出 → 并入
    for attr, label in (('dynasty_any', '朝代'), ('author_any', '词人'), ('cipai_any', '词牌')):
        cur = list(getattr(base, attr) or [])
        add = [v for v in (getattr(model, attr) or []) if v not in cur and str(v) in left]
        if add:
            setattr(base, attr, cur + add)
            got.append('%s %s' % (label, '／'.join(add)))
    if got:
        retrieve._finalize(base)
        notes.append('大模型替规则路消化了词面残片（%s）' % '、'.join(got))
        notes.append('大模型其它多出的条件与词面残片无关，已忽略（执行以规则解析为准）')
        return True
    notes.append('大模型多出的条件与词面残片无关，已忽略（执行以规则解析为准）')
    return False


def _lq_label(lq):
    """句级算子的人类可读标签（用于吸收时的如实披露）。"""
    k, v = (lq or {}).get('pred') or (None, None)
    _kl = {'tail': '句脚字', 'tail_any': '句脚字', 'tail_pz': '句脚平仄', 'pz': '声律串含',
           'pz_exact': '整句平仄全等', 'len': '句长', 'parity': '句位'}
    if k == 'len' and isinstance(v, (list, tuple)) and len(v) == 2:
        ptxt = '%s=%s~%s' % (_kl.get(k, k), v[0], v[1])
    elif k == 'parity':
        ptxt = '句位=%s' % ('奇数' if v == 0 else '偶数')
    else:
        vt = '／'.join(v) if isinstance(v, (list, tuple)) else v
        ptxt = '%s=%s' % (_kl.get(k, k), vt)
    op = (lq or {}).get('op')
    if op == '∃':
        q = '至少有一句'
    elif op == '∀':
        q = '每一句都'
    elif op == '∄':
        q = '没有任何一句'
    elif op == '≥k':
        q = '至少 %d 句' % lq.get('k', 0)
    elif op == '=k':
        q = '正好 %d 句' % lq.get('k', 0)
    elif op == '占比≥p':
        q = '满足句占比≥%.0f%%' % (100 * lq.get('ratio', 0))
    else:
        q = '满足句数 %s~%s' % (lq.get('ka', 0), lq.get('kb', 0))
    return '%s；%s' % (q, ptxt)


def _drop_consumed(base, consumed):
    """把「已被回填成条件」的词面残片从 keywords/unparsed 里清掉（避免重复、避免误导披露）。"""
    frags = [str(c) for c in (consumed or []) if c and len(str(c)) >= 2]
    if not frags:
        return

    def _hit(s):
        s = str(s)
        return any((f in s or s in f) for f in frags)
    base.keywords = [k for k in (base.keywords or []) if not _hit(k)]
    base.unparsed = [u for u in (base.unparsed or []) if not _hit(u)]


def _absorb_model_extras(base, model, question, notes):
    """在 `_absorb_leftovers` **之外**，额外吸收「**规则路没有、而模型给出了**」的条件（纯加法）。

    为什么需要（2026-10-08，外部审查 · schema 缺口）：规则路 `parse_query` 表达不了
    题名（title_any）／句级算子（line_q）／平仄全等（pz_exact）／篇内交集（tail_each）／
    句位奇偶（parity）／走向一致性（consist）／语义检索词（semantic）；`qlm.SYSTEM` 本轮
    已补齐这些字段，于是模型**能给出**它们——而旧版 `understand` 只在「规则路留了词面残片」
    时吸收与残片相关的条件，其余一律忽略 → **模型听懂了也被静默丢弃**（如「蝶恋花·四月一日
    感粤事」的题名、「至少两句句脚为愁」的句级量词）。

    硬约束（保护既有 1000 题行为）：
      · **只在规则路没有该条件时吸收**（同类条件已有则**不覆盖**）；
      · 每条吸收都追加 notes 如实披露；
      · 吸收后调 `retrieve._finalize(base)` 让单值字段重新派生。
    """
    got = []
    # 1) 题名（词题）——规则路只有「词牌·题名」一种入口，模型能直接给题名
    if getattr(model, 'title_any', None) and not base.title_any:
        base.title_any = list(model.title_any)
        got.append('规则路未表达题名，已采纳大模型给出的题名（%s）' % '／'.join(base.title_any))
    # 2) 平仄串全等（与 pz 子串互斥；line_q 已按全等谓词接管时不重复）
    if getattr(model, 'pz_exact', None) and not base.pz_exact and not base.line_q:
        base.pz_exact = model.pz_exact
        got.append('规则路未表达平仄串全等，已采纳大模型给出的平仄串全等（%s）' % model.pz_exact)
    # 3) 篇内交集（每一个取值都必须各有一句）
    if getattr(model, 'tail_each', None) and not base.tail_each:
        base.tail_each = list(model.tail_each)
        got.append('规则路未表达篇内交集，已采纳大模型给出的篇内交集（%s）'
                   % '／'.join(base.tail_each))
    # 4) 句级算子（∄/∀/∃/≥k/=k/占比/条数）
    if getattr(model, 'line_q', None) and not base.line_q:
        base.line_q = dict(model.line_q)
        got.append('规则路未表达句级算子，已采纳大模型给出的句级算子（%s）'
                   % _lq_label(base.line_q))
    # 5) 句位奇偶：口径同 retrieve（0=奇数位）；检索层只经 line_q 谓词执行，故同时落一条 ∃ 谓词
    if getattr(model, 'parity', None) is not None and base.parity is None:
        base.parity = model.parity
        if not base.line_q:
            base.line_q = {'op': '∃', 'pred': ('parity', model.parity)}
        got.append('规则路未表达句位奇偶，已采纳大模型给出的句位奇偶（%s）'
                   % ('奇数句位' if model.parity == 0 else '偶数句位'))
    # 6) 走向一致性（声情标注为 X 但实测前后段相反）——与规则路口径一致地同时标注 scene
    if getattr(model, 'consist', None) and not getattr(base, 'consist', None):
        base.consist = model.consist
        if not base.scene:
            base.scene = model.consist
        got.append('规则路未表达走向一致性，已采纳大模型给出的走向一致性（%s）' % model.consist)
    # 7) 语义检索词（**只作全文召回扩展，不进 SQL**；规则路恒为空）
    if getattr(model, 'semantic', None) and not (getattr(base, 'semantic', None) or []):
        base.semantic = list(model.semantic)
        got.append('规则路未表达语义检索词，已采纳大模型给出的语义检索词（%s）'
                   % '／'.join(base.semantic))

    # 8) 「口语算子回填」：规则路与模型路**都没给** line_q 时，尽力从问句回填（见 qlm.recover_line_ops）。
    #    典型：模型把算子片段如实塞进 unparsed、却没填 line_ops（如「至少两句」「每一句…正好是…」）。
    if not base.line_q and not getattr(model, 'line_q', None):
        rec = qlm.recover_line_ops(question)
        if rec and rec.get('line_q'):
            base.line_q = rec['line_q']
            if rec.get('pz_exact') and not base.pz_exact:
                base.pz_exact = rec['pz_exact']
            if rec.get('tail_each') and not base.tail_each:
                base.tail_each = list(rec['tail_each'])
            _drop_consumed(base, rec.get('consumed') or [])
            got.append('规则路未表达句级算子，已由问句口语回填（%s）' % _lq_label(base.line_q))

    if got:
        retrieve._finalize(base)
        notes.extend(got)
    return bool(got)


def _clean_extreme_unparsed(spec):
    """「最高／最低」这类极值词若还留在 unparsed 里，披露文案会写成「未被理解成条件，
    已忽略」——而它其实**已经**被用作排序条件了：这句话本身就不对。补回排序后一并清掉。"""
    if not getattr(spec, 'order_by', None):
        return
    _ew = tuple(retrieve.EXTREME_UP) + tuple(retrieve.EXTREME_DOWN)
    spec.unparsed = [x for x in spec.unparsed
                     if not any(str(x) == w or str(x).startswith(w + '（已转为') for w in _ew)]


def _understand_impl(conn, question, llm=None, llm_parse=False, llm_policy='always', context=None):
    """问句 → QuerySpec（**内部实现**；对外入口是下面的 `understand` 包装器）。

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
        # ⚠ 2026-10-04 凌晨（网页端 B 段实测，Q0397/Q0654/Q0707/Q0764/Q0812/Q0866）：
        #   模型会把**众数题**（「全篇字数最常出现的取值是几」）臆造成「分组统计=按词人取最多」
        #   ——这类臆造意图一旦采纳，答案从 116 篇掉成 0 篇。闸门：模型给的若是**组内极值型**
        #   （没有组名、带 extreme），而问句里找不到分组极值意图、且规则路已解析出条件 →
        #   判为臆造，改用规则路（与「规则路优先」同一哲学）。真正的组内极值问句在
        #   `_group_extreme_of` 里认得出，对比题则带显式组名（values 非空）——都不受影响。
        _ge = retrieve._group_extreme_of(question)
        if spec.agg.get('extreme') and not spec.agg.get('values') \
                and _ge[0] is None and _rule_conditions(rule):
            notes.append('大模型自称「按%s分组取%s」，但问句里没有分组极值意图、而规则解析'
                         '已给出条件——判为臆造意图，本次按规则解析作答'
                         % (spec.agg.get('group_by'), spec.agg.get('extreme')))
            rule.source = '规则解析（大模型的分组意图在问句里找不到依据，未采纳）'
            _clean_extreme_unparsed(rule)
            return rule, {'source': rule.source, 'dropped': q['dropped'],
                          'notes': notes, 'alt': spec}
        # ⭐ 筛选条件**真的**两路合并（旧版只在这句注释里说合并、实际没合并）：
        #    大模型认出了分组统计但听漏的硬条件（句级量词/区间/句脚…）由规则路补齐。
        #    share-声情题里 scene 是**被测量的类别**，与组内极值清空的维度同理，不补。
        _skip_scene = (spec.agg.get('metric') == 'share'
                       and (spec.agg.get('cat') or [None])[0] == 'scene')
        _copy_rule_hard(spec, rule, notes, skip_scene=_skip_scene)
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
    # ⭐ **规则路优先**（2026-10-03 晚，网页端 B 段全量 1000 题实测驱动）：规则路已经听出
    #    条件时，执行必须以规则路为准——大模型即使听出整句也常**多塞**条件（篇级句数／句脚字／
    #    声律模式／比例阈值…），实测这些多出的条件改的就是答案（见 _rule_trustworthy 的注释）。
    #    · 规则路「听全了」→ 整体以规则路为准，模型的听写只作核对披露；
    #    · 规则路留了词面残片（可能漏听）→ 以规则路为基，只吸收与残片相关的模型条件；
    #    · 带上下文（多轮指代）时不走这两条——指代补全规则路干不了，理解优先。
    #    · 模型认出了配对题而规则路没有时也不走（那是模型能补的确定性意图缺口）。
    if not (spec.pair and not rule.pair) and _rule_trustworthy(rule, question):
        # ⚠ 2026-10-04：**带上下文时同样走「规则路优先」**。旧版只要带了上下文就整条策略跳过，
        #   而多轮里模型最容易「顺手带进」上一轮的东西——实测主人多轮提问时，模型把本轮
        #   「句长 7~11」重复编码成篇级「阈值 7~11」，命中数 3876 → 486 篇。
        #   多轮真正需要模型的地方只有**指代补全**：所以带上下文时只吸收「上下文里有依据」
        #   的补充（见 _copy_ctx_attested），其余仍以规则路为准。
        if context and _looks_elliptic(question):
            _copy_ctx_attested(rule, spec, context, notes)
            rule.source = '规则解析（整句已完整解析；多轮补充仅取上下文里有依据的）'
        elif context:
            notes.append('本轮问句已自足，按规则解析作答（上下文不改动条件）')
            rule.source = '规则解析（整句已完整解析，上下文未改动条件）'
        else:
            notes.append('规则解析已听全整句条件，大模型多给/不同的条件一律忽略（执行以规则解析为准）')
            rule.source = '规则解析（整句已完整解析，大模型仅作听写核对）'
        # ⭐ **模型补充吸收（加法）**：即便规则路「听全了」，只要它在**新字段**（题名/句级算子/
        #    平仄全等/篇内交集/句位奇偶/走向一致性/语义检索词）上**没有**该条件、而模型给出了，
        #    就补进来执行——旧版一律静默丢弃（模型听懂了也不算）。规则路已有的同类条件**不覆盖**。
        if _absorb_model_extras(rule, spec, question, notes):
            rule.source = '规则解析（整句已完整解析；并补齐了规则路未表达的字段）'
        _clean_extreme_unparsed(rule)
        return rule, {'source': rule.source, 'dropped': q['dropped'],
                      'notes': notes, 'alt': spec}
    if not (spec.pair and not rule.pair) and _rule_conditions(rule):
        # ⚠ 2026-10-04（D 段全量实测）：**带上下文时也以规则路为基**——旧版带 ctx 时直接
        #   退回「模型 spec 为基」，结果模型缺了规则路的词面残留、或多加了篇级条件，
        #   结论行/命中数就与单问不一致（Q0007/Q0015/Q0019）。现在统一为「规则路为基」。
        if spec.order_by and not rule.order_by and not detect_output(question)[0]:
            rule.order_by, rule.order_col = spec.order_by, spec.order_col
            rule.order_dir, rule.extreme = spec.order_dir, spec.extreme
            rule.order_label, rule.order_src = spec.order_label, '大模型'
            notes.append('极值／排序意图由大模型补齐（【%s】取%s）'
                         % (spec.order_label, '最高' if spec.extreme == 'max' else '最低'))
        if context and _looks_elliptic(question):
            _copy_ctx_attested(rule, spec, context, notes)
        _abs_left = _absorb_leftovers(rule, spec, notes)
        # ⭐ **模型补充吸收（加法）**：规则路留了词面残片时，除了吸收与残片相关的条件，
        #    再把模型在**新字段**上给出、而规则路没有的条件补进来（题名/句级算子/平仄全等/
        #    篇内交集/句位奇偶/走向一致性/语义检索词），并做「口语算子回填」（见函数注释）。
        _abs_extra = _absorb_model_extras(rule, spec, question, notes)
        if _abs_extra:
            rule.source = '规则解析（大模型补齐了规则路未表达的字段）'
        elif _abs_left:
            rule.source = '规则解析（大模型补消化了词面残片）'
        else:
            rule.source = '规则解析（模型多出的条件与问句残片无关）'
        _clean_extreme_unparsed(rule)
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
    _clean_extreme_unparsed(spec)
    # ⭐ 硬条件安全网（2026-10-03 晚，网页端实测驱动——「第四十题」事件）：见 _copy_rule_hard。
    #    规则路已解析出的确定性条件，大模型没听出的必须补回执行，而不是只在「alt」里披露。
    #    先按「同一量不重复生效」清掉模型重复编码的条件（见 _drop_redundant）。
    _drop_redundant(spec, rule, notes)
    if _copy_rule_hard(spec, rule, notes):
        # 条件按规则路补齐后，「未理解片段」也改按规则路的披露——大模型列的未理解
        # 片段里可能有规则路其实已听出的条件，留着会与执行口径说反话。
        spec.unparsed = list(rule.unparsed or [])
    retrieve._finalize(spec)
    return spec, {'source': spec.source, 'dropped': q['dropped'],
                  'notes': notes, 'alt': rule}


def _understanding_status(spec):
    """给上层一个**可查询的状态标记**，区分「有明确未理解的部分」与「本来就是自由词面查询」。

    返回 `(status, note_text_or_None)`：
      · `'UNDERSTANDING_INCOMPLETE'`：`spec.unparsed` 非空**且没有形成任何硬条件**
        （也没有 agg/pair/order 这类意图）→ 上层**不应**拿「语义相关度前几篇」冒充答案，
        而应如实告知「未能转成可执行条件」；
      · `'KEYWORD_FREEFORM'`：本来就是自由词面/语义查询（`spec.keywords` 非空、`unparsed` 为空、
        无硬条件）→ 正常的语义检索；
      · `'OK'`：其余（有硬条件，或空问句）。

    ★ 为什么做成**标记**而不是给 `QuerySpec` 加字段：`QuerySpec` 是别人的文件（本任务不改），
      且 `ask.answer` 的 `total is None` 分支**属另一条战线**——本函数只**提供可检测的标记**，
      由调用者（如 answer 的语义排序分支）决定怎么用。
    """
    _has_hard = retrieve.has_hard(spec)
    _intent = bool(spec.agg or getattr(spec, 'pair', None) or getattr(spec, 'order_by', None))
    _unp = list(getattr(spec, 'unparsed', None) or [])
    _kws = list(getattr(spec, 'keywords', None) or [])
    if not _has_hard and not _intent and _unp:
        return ('UNDERSTANDING_INCOMPLETE',
                'UNDERSTANDING_INCOMPLETE：问句有未能转成可执行条件的部分（%s），'
                '且没有形成任何硬条件——不要以「语义相关度前几篇」冒充答案'
                % '；'.join(_clean_frag(u) for u in _unp))
    if not _has_hard and not _intent and _kws and not _unp:
        return 'KEYWORD_FREEFORM', None
    return 'OK', None


def understand(conn, question, llm=None, llm_parse=False, llm_policy='always', context=None,
               ctx_pids=None):
    """问句 → `(QuerySpec, note)`（**对外入口**；在 `_understand_impl` 之上加「附加层」）。

    `ctx_pids`（可选，2026-10-08 新增）：**上一轮命中的 pid 集合**。多轮指代（「那里面哪个最短」）
    的正确做法不是让模型猜「那里面」指什么，而是把上一轮的真实结果集**作为硬条件**带进来 ——
    落到 `spec.ctx_pids` 后由 `retrieve._sql()` 编译成 `p.pid IN (…)`，范围即被锁定。
    规则路永远不会产出该字段，故对本项目 1000 题（不开大模型、不带多轮）**零影响**。

    附加层（纯加法，不改判定与执行）：
      · `note['understanding_status']`：见 `_understanding_status`（'OK' /
        'UNDERSTANDING_INCOMPLETE' / 'KEYWORD_FREEFORM'）——**调用者**据此区分
        「未理解」与「自由词面查询」；
      · 仅当**走过大模型理解路**（`llm_parse`）且状态为未完成时，把带
        `UNDERSTANDING_INCOMPLETE` 前缀的说明**追加进 note['notes']**（规则路答案文本保持逐字不变，
        以免影响 1000 题与既有门禁的文字口径）；
      · 附上可回放的 AST（`note['ast']`）与两路差异（`note['ast_rule']`/`note['ast_diff']`），
        纯调试用、失败静默（不影响理解结果）。
    """
    spec, note = _understand_impl(conn, question, llm=llm, llm_parse=llm_parse,
                                  llm_policy=llm_policy, context=context)
    # ⭐ 多轮「结果集」作为硬条件（2026-10-08）：把上一轮命中的 pid 集合锁进本轮范围。
    #   必须在 `_understanding_status()` **之前**设置——否则 `has_hard()` 看不到它，
    #   会把「那里面…」误判成「没形成任何条件」（UNDERSTANDING_INCOMPLETE）。
    if ctx_pids:
        _cp = []
        for _p in ctx_pids:
            _s = str(_p).strip()
            if _s and _s not in _cp:
                _cp.append(_s)
        if _cp:
            spec.ctx_pids = _cp
            retrieve._finalize(spec)
            note['notes'] = list(note.get('notes') or []) + [
                '范围锁定为上一轮结果集（%d 篇）' % len(_cp)]
    status, msg = _understanding_status(spec)
    note['understanding_status'] = status
    if llm_parse and msg:
        note['notes'] = list(note.get('notes') or []) + [msg]
    try:                                    # 调试层：AST 与「规则路 vs 模型路」差异（可回放）
        import queryast as _qa
        note.setdefault('ast', _qa.to_ast(spec))
        _alt = note.get('alt')
        if _alt is not None:
            note['ast_rule'] = _qa.to_ast(_alt)
            note['ast_diff'] = _qa.diff_ast(note['ast_rule'], note['ast'], '规则路', '模型路')
    except Exception:
        pass
    return spec, note


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
        # 审查 B40（续，2026-10-03 晚）：alt 是**没被采纳**的那一版——主表来自规则解析时
        # alt 是大模型的，主表来自大模型时 alt 是**规则解析**的。旧文案两个方向只写对一半，
        # 实测把规则解析的正确条件标成「大模型解析得到」，误导排查方向。
        _who = '大模型' if str(note['source']).startswith('规则') else '规则'
        out.append('　　　注：同一句用%s解析得到〔%s〕；本次执行以上表为准。'
                   % (_who, _clean_frag(alt.describe())))
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
    # ⚠ 2026-10-04 凌晨（网页端 B 段实测）：**「另一路解析」的披露行**也属诊断信息，
    #   其数字（如模型给的 变化≤100.0）不是对语料的断言——不放进白名单，护栏会把自己的
    #   披露行判成「数字无出处」（实测 Q0008 等）。
    _alt = pnote.get('alt')
    if _alt is not None:
        try:
            texts.append(_alt.describe())
        except Exception:
            pass
    for x in texts:
        for n in _nums(x):
            # 整数给 int、小数给 float：既满足「整数断言」，也让 qwen3.8-27b 的 3.8 被放行
            out.append(int(n) if n.isdigit() else float(n))
    return out




# ================================================================ 输出算子（F3）
# 由来（2026-10-02，逐题答卷审查）：引擎原本只会「检索 + 数篇数」，遇到**统计输出**类问句
# （中位数／众数／占比／两范围差值／条件概率／第 N 名）就答成「融合排序前 3 篇」——
# 问的是统计量，答的是篇目（答非所问）。这里补上六条确定的作答路径。
_METRIC_TEXT = {
    'ze_ratio': ('仄声比例', '仄字占比', '仄声比重', '仄的比例', '仄比'),
    'ping_ratio': ('平声比例', '平字占比', '平声占比', '平声比重'),
    'han_len': ('全篇字数', '字数', '篇幅', '总字数'),
    'sent_n': ('句数', '句子数量'),
}
OUT_MEDIAN_RE = re.compile(r'中位数')
OUT_MODE_RE = re.compile(r'众数|最常出现的取值')
OUT_SHARE_RE = re.compile(r'百分之几')
OUT_DIFF_RE = re.compile(r'比「(.+)」的(?:词|作品)(?:多|少)几篇')
OUT_COND_RE = re.compile(r'有多大比例同时也满足「(.+)」')
OUT_RANK_RE = re.compile(r'第([一二三四五六七八九十])([大小高矮低短长多少])')
OUT_DISP_RE = re.compile(r'哪一个(词牌|词人|作者|朝代)的[^，。]{0,10}?'
                         r'(?:波动最大|离散度最大|差异最大|起伏最大|最不稳定)')


def _metric_of(text, near=None):
    """认指标。⚠ **必须只看「输出算子附近」的那几个字**——整句里往往有别的指标词
    （如「仄声比例高于45%的作品里，全篇字数第三高的是哪一篇」，看整句会误认成仄声比例）。"""
    frag = near if near is not None else (text or '')
    for k, names in _METRIC_TEXT.items():
        for n in names:
            if n in frag:
                return k
    if near is not None:                    # 附近没找到就退回整句
        for k, names in _METRIC_TEXT.items():
            for n in names:
                if n in (text or ''):
                    return k
    return 'han_len'


def _metric_expr(metric):
    if metric == 'ping_ratio':
        return '(100.0 - p.ze_ratio)'
    # ⚠ 「前后段变化幅度」比**绝对值**（与 ORDER_EXPR / 真值口径同源）
    if metric == 'change':
        return 'ABS(p.change)'
    return 'p.%s' % ('ze_ratio' if metric == 'ze_ratio' else metric)


def _near(question, m):
    return question[max(0, m.start() - 14):m.start()]


def _near2(question, m):
    """输出算子附近的片段：**含命中本身**。

    ⚠ 2026-10-03：`_near`（只看命中**之前**）对「哪一个词人的**篇幅**波动最大」取不到指标词
    （指标词在命中之内），退回整句后再撞上范围里的「仄声比例」→ 认成错指标
    （实测 Q0156：问「篇幅波动最大」，引擎按**仄声比例**的标准差分组，答成朱祖谋 10.8，
    真值关汉卿 312.4）。
    """
    return question[max(0, m.start() - 14):m.end()]


def detect_output(question):
    """问句要的是哪种**统计输出**？→ (op, 第二范围原文 / 元组 / None)。"""
    m = OUT_DIFF_RE.search(question)
    if m:
        return 'diff', m.group(1)
    m = OUT_COND_RE.search(question)
    if m:
        return 'condshare', (question[:question.index('有多大比例同时也满足')], m.group(1))
    m = OUT_MEDIAN_RE.search(question)
    if m:
        return 'median', _near2(question, m)
    m = OUT_MODE_RE.search(question)
    if m:
        return 'mode', _near2(question, m)
    m = OUT_DISP_RE.search(question)
    if m:
        gb = {'词牌': 'cipai', '词人': 'author', '作者': 'author', '朝代': 'dynasty'}[m.group(1)]
        return 'disp', (gb, _near2(question, m))
    m = OUT_RANK_RE.search(question)
    if m:
        return 'rank', _near2(question, m)
    if OUT_SHARE_RE.search(question) and '占' in question:
        return 'share', None
    return None, None


def _fmt(v):
    if v is None:
        return '—'
    if isinstance(v, float):
        return ('%.1f' % v) if abs(v - round(v)) > 1e-9 else '%d' % round(v)
    return str(v)


def _outer_scope_text(question):
    """两范围题 → **外层**范围的那段文字（把内层「」内容挖空，避免被内层的条件带偏）。"""
    for anchor in ('，比', '的作品当中'):
        i = question.find(anchor)
        if i > 0:
            return question[:i]
    return question



def _wrap_output(question, spec, pnote, kind, text, ok, problems, refused=False,
                 narrator='template', total=None, pid=None):
    ok, problems = _with_unsupported(spec, ok, problems)
    text += _verdict_line(ok, problems, GUARD_PASS_MAIN)
    return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
            'answer': text, 'verify': (ok, problems), 'refused': refused,
            'problems': problems, 'total': total, 'narrator': narrator,
            'narrative': None, 'parse_source': pnote['source'],
            'parse_dropped': pnote['dropped'], 'parse_notes': pnote['notes'],
            'unparsed': list(spec.unparsed), 'safety': {'ok': True}, 'pid': pid}


def _answer_output(conn, question, spec, pnote, kind, op, extra, topk=3):
    """六条统计输出的**确定**作答路径（模板 + 护栏）。"""
    head = _parse_head(spec, pnote)
    _nearfrag = extra[1] if isinstance(extra, tuple) else (
        extra if isinstance(extra, str) else None)
    metric = _metric_of(question, _nearfrag)
    mlabel = _METRIC_TEXT[metric][0]
    w, a = retrieve._sql(spec)
    val = None
    _pid = None

    def _empty():
        # ⚠ 2026-10-03：三种情形要分清——
        #   · **语料外范围**（unsupported）＝「不支持」→ 拒答；
        #   · **范围内 0 篇**＝「0 篇」就是答案 → 如实报 0；
        #   · **范围非空、但该口径没有可用数据**（如离散度要求组内 ≥3 篇、指标全为空）
        #     → 必须报出**真实命中篇数**，再说清「按该口径无可用数据」。
        #     旧写法一律回「现有语料未见支持：按查询条件未召回到任何词作」，且把含条件回显的
        #     整段文本交给 `check_no_support` → 自己的护栏判「拒答文本里仍出现数字」；
        #     我第一版补的「0 篇」文案又矫枉过正：范围明明有 6 篇也说成 0 篇（实测 Q0324）。
        if spec.unsupported:
            t = head + '\n【结论】现有语料未见支持：问句涉及语料外范围（%s）。' \
                       '本系统语料只含清/宋/元三代词作，不拿语义相近的篇凑数。' \
                % _clean_frag(spec.unsupported)
            _ok, _pb = guard.check_no_support(t.replace(spec.describe(), ''), True)
            return _wrap_output(question, spec, pnote, kind, t, _ok, _pb,
                                refused=True, narrator='template')
        _n_all = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % w, a).fetchone()[0]
        if _n_all == 0:
            # ⚠ 2026-10-05 新增（朋友实测驱动）：**"0 篇"常常不是"没有"，而是"搜错了字段"**。
            #   实测：「清明同诸子集原白斋中」在正文（raw）里 0 命中，但它其实是**题名**，
            #   在 title 里恰好唯一命中 1 篇（清·陈维崧）。旧版只说「共命中 0 篇」——
            #   用户会以为语料里没有这首词，其实是他把题名当正文问了。
            #   这里做**只读的兜底提示**：把词面关键词拿去 title 里探一次，
            #   探到就明说「这是题名，不是正文」，并给出题名检索的写法。
            #   —— 不改检索结果（0 仍是 0），只是把「为什么 0」说清楚，符合
            #      「无据即认账、但认账要认得准确」的既有纪律。
            _hint = _title_hint(conn, spec)
            t = (head + '\n【结论】在条件〔%s〕下共命中 0 篇：本语料中没有作品同时满足上述全部条件。'
                         '\n　　　（口径：按全部条件逐篇比对后计数；0 是确切结果，不是未检索。）%s'
                         '\n【推断边界｜%s问句】%s'
                 % (spec.describe(), _hint, kind, BOUNDARIES[kind]))
            _allow = _nums(t) + re.findall(r'\d+(?:\.\d+)?', spec.describe()) + [0]
            _ok, _pb = guard.verify(t, [], boundary_kind=kind, allow=_allow)
            return _wrap_output(question, spec, pnote, kind, t, _ok, _pb,
                                refused=False, narrator='template', total=0)
        t = (head + '\n【结论】在条件〔%s〕下共命中 %d 篇；但按本题要求的统计口径，'
                     '这些篇目里没有可用于该统计量的数据（如分组后样本不足、指标缺失），'
                     '因此不给该统计量，也不拿看似像答案的数字来充数。'
                     '\n【推断边界｜%s问句】%s' % (spec.describe(), _n_all, kind, BOUNDARIES[kind]))
        _allow = _nums(t) + re.findall(r'\d+(?:\.\d+)?', spec.describe()) + [_n_all]
        _ok, _pb = guard.verify(t, [], boundary_kind=kind, allow=_allow)
        return _wrap_output(question, spec, pnote, kind, t, _ok, _pb,
                            refused=False, narrator='template', total=_n_all)

    # ⚠ 2026-10-03：**语料外范围**一律先拒答——输出算子路径（中位数/众数/占比/差值/条件概率/
    #   第N名/离散度）原本不看 `unsupported`，会照旧拿语料内的篇算出一个数字（答非所问）。
    if spec.unsupported:
        return _empty()

    if op == 'median':
        xs = sorted(r[0] for r in conn.execute(
            'SELECT %s FROM poems p WHERE %s' % (_metric_expr(metric), w), a))
        if not xs:
            return _empty()
        n = len(xs)
        val = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0
        text = (head + '\n【结论】在条件〔%s〕下共 %d 篇，%s的中位数是 %s。'
                '\n　　　（口径：逐篇取值后取中位数；偶数篇取中间两篇均值。）'
                % (spec.describe(), n, mlabel, _fmt(val)))
    elif op == 'mode':
        from collections import Counter as _C
        cs = _C(round(r[0], 1) for r in conn.execute(
            'SELECT %s FROM poems p WHERE %s' % (_metric_expr(metric), w), a))
        if not cs:
            return _empty()
        top = max(cs.values())
        val = sorted(k for k, v in cs.items() if v == top)[0]
        text = (head + '\n【结论】在条件〔%s〕下共 %d 篇，%s最常出现的取值是 %s（出现 %d 篇）。'
                % (spec.describe(), sum(cs.values()), mlabel, _fmt(val), top))
    elif op == 'share':
        n = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % w, a).fetchone()[0]
        dys = retrieve._vals(spec, 'dynasty')
        if dys:
            tot = conn.execute('SELECT COUNT(*) FROM poems WHERE dynasty IN (%s)'
                               % ','.join('?' * len(dys)), list(dys)).fetchone()[0]
            base = '／'.join(dys) + '词'
        else:
            tot = conn.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
            base = '全部语料'
        val = (100.0 * n / tot) if tot else 0.0
        text = (head + '\n【结论】在条件〔%s〕下共命中 %d 篇；占%s（%d 篇）的 %s%%。'
                '\n　　　（口径：占比 = 命中篇数 ÷ 分母篇数；本题分母 = %s。）'
                % (spec.describe(), n, base, tot, _fmt(val), base))
    elif op == 'diff':
        # ⚠ 外层范围**必须**从挖掉内层「」的文字重新解析（否则会被内层的条件带偏）
        spec = retrieve.parse_query(conn, _outer_scope_text(question))
        head = _parse_head(spec, pnote)
        w, a = retrieve._sql(spec)
        spec2 = retrieve.parse_query(conn, extra)
        w2, a2 = retrieve._sql(spec2)
        n1 = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % w, a).fetchone()[0]
        n2 = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % w2, list(a2)).fetchone()[0]
        val = n1 - n2
        text = (head + '\n【结论】范围一命中 %d 篇、范围二命中 %d 篇，**相差 %+d 篇**。'
                '\n　　　范围一：%s\n　　　范围二：%s'
                % (n1, n2, val, spec.describe(), spec2.describe()))
    elif op == 'condshare':
        _h, tail = extra
        spec = retrieve.parse_query(conn, _outer_scope_text(question))
        head = _parse_head(spec, pnote)
        w, a = retrieve._sql(spec)
        spec2 = retrieve.parse_query(conn, tail)
        w2, a2 = retrieve._sql(spec2)
        na = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % w, a).fetchone()[0]
        inter = conn.execute('SELECT COUNT(*) FROM poems p WHERE (%s) AND (%s)' % (w, w2),
                             list(a) + list(a2)).fetchone()[0]
        val = (100.0 * inter / na) if na else 0.0
        text = (head + '\n【结论】在范围〔%s〕的 %d 篇当中，有 %d 篇同时满足〔%s〕，占 %s%%。'
                '\n　　　（口径：条件概率 = 同时满足数 ÷ **前者**篇数。）'
                % (spec.describe(), na, inter, spec2.describe(), _fmt(val)))
    elif op == 'disp':
        # 离散度最大组：按维度分组 → 组内指标标准差最大的那一组（n≥3，防单篇噪声）
        gb, _nf = extra
        col = {'cipai': 'p.cipai', 'author': 'p.author', 'dynasty': 'p.dynasty'}[gb]
        xs = {}
        for g, v in conn.execute('SELECT %s g, %s v FROM poems p WHERE %s'
                                 % (col, _metric_expr(metric), w), a):
            if g:
                xs.setdefault(g, []).append(v)
        best = None
        for g, vs in xs.items():
            if len(vs) < 3:
                continue
            mu = sum(vs) / len(vs)
            sd = (sum((x - mu) ** 2 for x in vs) / (len(vs) - 1)) ** 0.5
            # ⚠ 并列时按组名**字典序**取最小（确定性；与真值 `sorted(...)[0]` 同口径）。
            #   旧版按 dict 插入序取第一个 → 与真值选了不同的组（实测 Q0100：真值「减字木兰花」、
            #   引擎「浣溪沙」，两者标准差都是 0）。
            if (best is None or sd > best[1] + 1e-12
                    or (abs(sd - best[1]) <= 1e-12 and g < best[0])):
                best = (g, sd, len(vs), mu)
        if best is None:
            return _empty()
        glabel = {'cipai': '词牌', 'author': '词人', 'dynasty': '朝代'}[gb]
        val = best[1]
        text = (head + '\n【结论】在条件〔%s〕下按%s分组，%s**波动最大**的是〔%s〕：'
                '组内 %d 篇，%s标准差 %s（组内均值 %s）。'
                '\n　　　（口径：离散度 = 组内样本标准差；样本数 < 3 的组不参与。）'
                % (spec.describe(), glabel, mlabel, best[0], best[2], mlabel,
                   _fmt(val), _fmt(best[3])))
    else:                                   # rank：第 N 大/小
        m = OUT_RANK_RE.search(question)
        n = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5}.get(m.group(1), 2)
        desc = m.group(2) in ('大', '高', '长', '多')
        expr = _metric_expr(metric)
        row = conn.execute('SELECT p.pid, p.dynasty, p.author, p.cipai, %s v FROM poems p '
                           'WHERE %s ORDER BY v %s, p.pid LIMIT 1 OFFSET ?'
                           % (expr, w, 'DESC' if desc else 'ASC'),
                           list(a) + [n - 1]).fetchone()
        if not row:
            return _empty()
        _pid = row[0]
        val = row[4]
        text = (head + '\n【结论】在条件〔%s〕下，%s第%s%s的是：%s·%s《%s》，%s = %s。'
                % (spec.describe(), mlabel, m.group(1), m.group(2),
                   row[1], row[2], row[3], mlabel, _fmt(val)))

    # ⚠ 护栏第④道要求「边界声明」：必须有**限定词**（不能/不可/无法）与**本类专属标记**（形式/声调），否则判未通过。
    text += ('\n【推断边界｜数值型问句】以上数字只反映当前文本的形式与声调配置，'
             '不能直接推断作者意图、时代因果或作品优劣。')
    allow = _nums(text) + re.findall(r'\d+(?:\.\d+)?', spec.describe()) \
        + _allow_disclose(pnote, spec)
    ok, problems = guard.verify(text, [], boundary_kind=kind, allow=allow)
    return _wrap_output(question, spec, pnote, kind, text, ok, problems,
                        refused=False, narrator='template', total=val,
                        pid=(_pid if op == 'rank' else None))


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
        # ⚠ 2026-10-03：**必须**把篇级/句级筛选条件一并传进分组统计，否则
        #   「在后段上升、正好有二句句脚为卷的作品里，清与宋相比哪组篇幅更高」会拿全体清/宋比
        #   ——答的是另一个问题（实测 Q0062）。
        _cw, _ca = retrieve._sql(spec)
        rows = aggregate.stats(conn, ag['group_by'], ag['values'], ag['metric'], _cat,
                               _cw, _ca)
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
    ok, problems = _with_unsupported(spec, ok, problems)
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
    ok, problems = _with_unsupported(spec, ok, problems)
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
           on_engine=None, context=None, ctx_pids=None):
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
    topk = max(1, min(int(topk or 1), 200))
    # ⚠ 2026-10-04 修（代码审查 P1-7）：**问句无长度上限** → 未识别片段会全量回显，
    #   实测 51000 字输入产出 25250 字答案（查询理解单行 12024 字）。超限即**如实拒答**
    #   （拒答文案不含数字与引号，符合护栏③）。
    if len(question or '') > 500:
        _t = ('现有语料未见支持：问句过长（超过五百字）。本系统按形式与字面条件检索，'
              '请把问题拆成一句一条件，例如：清词里句脚为香的作品有多少篇。')
        _ok, _pb = guard.check_no_support(_t, True)
        return {'question': question, 'spec': '（问句超长，未进入检索）', 'kind': kind, 'blocks': [],
                'answer': _t, 'verify': (_ok, _pb), 'verify_kind': 'safety', 'refused': True,
                'problems': _pb, 'safety': {'ok': True}, 'narrator': 'safety', 'total': None}
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

    # ⭐ **官方题型（C1–C5「甲乙两篇对比」）→ 交解题链作答**（2026-10-04 主人实测驱动）：
    #   竞赛题库（公开 700 / 保密 300）全是这种格式，而本问答链面向「问答式」问句。
    #   旧版把官方题面当检索题解析（甲 的朝代 + 乙 的词人 + 题面套话全成条件）→
    #   「共命中 0 篇」，与问题毫无关系（实测保密集 V-001-V2C1）。这里识别后转 `official`：
    #   定位 → prosody c1..c5 → 按官方标准答案的措辞渲染（C1–C3 实测与官方逐字一致）。
    try:
        import official as _official
        if _official.looks_official(question):
            _r = _official.solve(question)
            if _r.get('ok'):
                _txt = _official.render(_r)
                # ⚠ 2026-10-06 修（外部审查 P1-10）：官方题型原先直接声称 verify 通过、
                #   以「未经问答链四道护栏」为理由放行。现改走**官方独立验证器**
                #   （数值可回查／定位完整／无内部 error／含边界声明），结果如实回吐。
                _okv, _pbv = _official.verify_result(_r, _txt)
                _conf = '、'.join('%s[%s]' % (k, v) for k, v in (_r.get('paths') or {}).items())
                return {'question': question, 'spec': '（官方题型 %s：由解题链定位并计算）' % _r['cls'],
                        'kind': '官方题型（%s）' % _r['cls'], 'blocks': [],
                        'answer': _txt + _verdict_line(
                            _okv, _pbv,
                            '官方题型：数值由 prosody 引擎确定性算出，已过**官方独立验证器**'
                            '（数值可回查／定位完整／边界声明），不走问答链证据护栏；'
                            '定位路径 %s' % (_conf or '—')),
                        'verify': (_okv, _pbv),
                        'verify_kind': 'official', 'refused': False, 'problems': list(_pbv),
                        'total': None, 'narrator': 'solver',
                        'official': {'cls': _r['cls'], 'located': _r.get('located'),
                                     'ans': _r.get('ans'), 'errors': _r.get('errors') or []},
                        'safety': {'ok': True}}
            # 识别成官方题但没算出来（定位失败等）→ 如实说明，不拿检索结果冒充
            _t = ('现有语料未见支持：这是官方「甲乙两篇对比」题（%s），但本次未能完成定位/计算——%s。'
                  '请核对题面里的作者、词牌与首句是否与本机语料一致。'
                  % (_r.get('cls') or '类别未判定', '；'.join(_r.get('errors') or ['原因未知'])))
            _ok, _pb = guard.check_no_support(_t, True)
            return {'question': question, 'spec': '（官方题型：定位/计算失败）', 'kind': '官方题型',
                    'blocks': [], 'answer': _t, 'verify': (_ok, _pb), 'refused': True,
                    'problems': _pb, 'total': None, 'narrator': 'solver', 'safety': {'ok': True}}
    except ImportError:
        pass                      # 没有 official/solver 模块时安静跳过（不影响问答链）
    except Exception as _exc:     # 语料目录不可用等 → 如实报错，不当成检索题硬答
        _t = ('现有语料未见支持：官方题型（C1–C5）作答链路不可用——%s: %s。'
              '请检查语料目录（环境变量 LVC_CORPUS）。' % (type(_exc).__name__, _exc))
        _ok, _pb = guard.check_no_support(_t, True)
        return {'question': question, 'spec': '（官方题型链路不可用）', 'kind': '官方题型',
                'blocks': [], 'answer': _t, 'verify': (_ok, _pb), 'refused': True,
                'problems': _pb, 'total': None, 'narrator': 'solver', 'safety': {'ok': True}}
    # ⚠ 2026-10-04 修（代码审查 P2-10）：**topk 未校验**。实测 `topk=0` 会落进
    #   「没有可引用的篇目」分支，答案谎报「未召回任何词作」——而同一问句实际命中 568 篇。
    #   负值更会被当成"全部"（563 篇）。这里统一夹到 [1, 200]。
    spec, pnote = understand(conn, question, llm=llm, llm_parse=llm_parse,
                             llm_policy=llm_policy, context=context, ctx_pids=ctx_pids)
    # ⚠ 2026-10-08 加（实测驱动）：**没有上文却用了强指代词**时如实提示。
    #   实测：「那里面哪一首最短？」在不带 ctx_pids 时会把「那里面」当词面去全文检索，
    #   于是端上来元曲《西华山陈抟高卧》—— 用户以为系统听懂了「那里面」，其实在乱搜。
    #   这里只**加一句提示**（不改检索、不改词面），让用户知道该补什么。
    if not ctx_pids:
        _REF = ('那里面', '这其中', '这些里面', '那些里', '上面的', '它们', '其中')
        _hit_ref = [w for w in _REF if w in (question or '')]
        if _hit_ref:
            pnote['notes'] = list(pnote.get('notes') or []) + [
                '本轮没有上文，「%s」无法确定所指——请把范围写进问题里，或先问一句再追问'
                % _hit_ref[0]]
    # ⭐ **题名条件的「存在性」统一收口**（2026-10-06，主人实测「题名=忆梦中最长的→0 篇」）：
    #   `title_any` 的来源有规则路（「词牌·题名」识别——值来自语料原文，天然可信）与
    #   大模型路（`qlm.validate` 此前**完全没校验 title**——实测模型会把「忆梦中最长的」
    #   这类**问句描述**当成题名塞进来 → `title LIKE` 0 命中 → 全条件 0 篇 →
    #   答复「本语料中没有作品」，而正确篇目明明就在库里）。
    #   这里统一收口：**LIKE 命中 0 的题名一律降级**——移出硬条件、降为词面（若 ≥2 字），
    #   并如实披露。这样无论未来再加多少条产生 title 的路径，出口都只放行「库里真实存在」的题名。
    _bad_t, _ok_t = [], []
    for _t in (spec.title_any or []):
        _row = conn.execute('SELECT 1 FROM poems WHERE title LIKE ? LIMIT 1',
                            ('%' + _t + '%',)).fetchone()
        (_ok_t if _row else _bad_t).append(_t)
    if _bad_t:
        spec.title_any = _ok_t
        for _t in _bad_t:
            if len(_t) >= 2 and _t not in (spec.keywords or []):
                spec.keywords.append(_t)
        spec.title = _ok_t[0] if len(_ok_t) == 1 else None
        pnote['notes'] = list(pnote.get('notes') or []) + [
            '题名「%s」在语料标题中不存在，已降级为词面参与语义检索（不再作为硬条件）'
            % '／'.join(_bad_t)]
        retrieve._finalize(spec)
    # ⭐ **「题名当词原文」兜底**（2026-10-05，朋友实测驱动）：
    #   裸题名（不带词牌，如「清明同诸子集原白斋中」「寄怀阿嫂」）解析后只剩「词面=…」，
    #   无硬条件 → 走语义融合排序 → 端上来的却是元曲里偶含「阿嫂」二字的《单刀会》，
    #   答非所问（朋友截图那一幕）。这里只读探测：词面在 **title** 命中、却在**正文**里 0 命中，
    #   就把词面提升为**题名条件**，改按题名检索。**只在本来没有硬条件时生效**，不动既有路径。
    _rescued = retrieve.rescue_title(conn, spec)
    if _rescued:
        pnote = dict(pnote)
        pnote['notes'] = list(pnote.get('notes') or []) + [
            '识别为**题名（词题）**而非词原文：词面在题名中命中、但不在正文出现，'
            '已改按题名检索（避免拿语义相近的篇凑数）']
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
    # ⚠ 2026-10-02：**输出算子**（中位数/众数/占比/差值/条件概率/第N名）——
    #   检测到就走确定作答路径，绝不再退回「检索 + 融合排序前 3 篇」（那是答非所问的根源）。
    _o_op, _o_extra = detect_output(question)
    if _o_op:
        return _answer_output(conn, question, spec, pnote, kind, _o_op, _o_extra, topk=topk)
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
        # ⚠ 2026-10-03：**条件合法、范围为空**（total == 0）与「没解析出条件」是两回事。
        #   前者「0 篇」就是答案，必须如实报 0——旧版一律回「现有语料未见支持：…未召回到任何词作」，
        #   把确切结果说成了「系统没料」（实测 Q0066：真值 0，被审计判成「引擎没给数」）。
        #   ⚠ **语料外范围（unsupported）例外**：那是「不支持」，必须拒答，不能说成「0 篇」。
        if total == 0 and not spec.unsupported:
            # 措辞里**不得出现「」**（那被引用护栏当作引文；此处只报数字）
            text = (_parse_head(spec, pnote)
                    + '\n【结论】在条件〔%s〕下共命中 0 篇：本语料中没有作品同时满足上述全部条件。'
                      '\n　　　（口径：按全部条件逐篇比对后计数；0 是确切结果，不是未检索。）'
                      '\n【推断边界｜%s问句】%s' % (spec.describe(), kind, BOUNDARIES[kind]))
            _allow = re.findall(r'\d+(?:\.\d+)?', spec.describe()) + _allow_disclose(pnote, spec) + [0]
            ok, problems = guard.verify(text, [], boundary_kind=kind, allow=_allow)
            ok, problems = _with_unsupported(spec, ok, problems)
            return {'question': question, 'spec': spec.describe(), 'kind': kind, 'blocks': [],
                    'answer': text, 'verify': (ok, problems), 'refused': False,
                    'problems': problems, 'total': 0, 'narrator': 'template',
                    'parse_source': pnote['source'], 'parse_dropped': pnote['dropped'],
                    'parse_notes': pnote['notes'], 'unparsed': list(spec.unparsed),
                    'safety': {'ok': True}}
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
        # ⚠ 2026-10-03：**篇目元数据自带的数字**不是论断数字——语料里确有「刘镇2」「杨适1」
        #   这类带序号的作者名，展示出来就会被护栏判「数字无出处」（实测 Q0093/Q0136）。
        allow += re.findall(r'\d+', '%s%s%s' % (b.get('author') or '', b.get('title') or '',
                                                b.get('cipai') or ''))
    if ei:
        allow += [ei['value'], ei['n_ties']]
        # ⚠ 【极值复核】行里会写「比较范围＝全库（元 11057 首、宋 21053 首、清 26742 首）」，
        #   这些分朝代篇数是**范围说明**，不是论断数字——不放行会被护栏判「数字无出处」
        #   （实测 32 题：答案一边给出复核、一边报「护栏未通过」，自相矛盾）。
        allow += [int(x) for x in re.findall(r'\d+', ei.get('scope') or '')]
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
        # ⚠ 2026-10-08 修（外部分析「理解失败会退化成模糊搜索并给出答案」· P0）：
        #   理解**不完整**时（有未理解片段、且没形成任何硬条件），**不得**把「按词面相关度排的
        #   前几篇」冒充成答案 —— 那正是「问 A 却答了看起来有关的 B」的观感来源。
        #   此时明确告知「没转成条件」，并把结果**降级标注**为「不是对该问题的回答」。
        #   而「本来就是自由词面查询」（keywords 非空、unparsed 为空）仍走正常语义检索，不打扰。
        _ust = (pnote.get('understanding_status') if isinstance(pnote, dict) else None)
        _unp = [str(x) for x in (getattr(spec, 'unparsed', None) or []) if str(x).strip()]
        if _ust == 'UNDERSTANDING_INCOMPLETE':
            head = ('【结论】未能把这句话转成可执行条件——其中「%s」没有被理解成检索条件，'
                    '因此没有按条件执行检索。下面按词面相关度展示的前 %d 篇'
                    '**不是对这个问题的回答**，仅供参考。'
                    '请换一种说法，或把它拆成「词牌／词人／朝代／句脚字／声律模式／字数句数」'
                    '这类可执行条件。'
                    % ('、'.join(_clean_frag(x) for x in _unp[:3]), len(blocks)))
        else:
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
    # ⚠ 2026-10-08 新增（主人实测驱动）：「**提取型**」问题（第 N 句第 M 字）——用户要的
    #   **就是那个字**，所以把它作为**第一条结论**给出（在「在条件〔…〕下共命中…」之前）。
    #   实测反例：「高旭《浪淘沙·…》第四句第三字是哪个字」原先被当词面检索、答了句脚；
    #   现在会直接答「《浪淘沙·杨笃生自沉利物浦死，吊以此阕》第四句是「宁与金瓯同破却，
    #   遗恨无穷。」，其中第三个字是「金」」。
    if getattr(spec, 'extract', None):
        _ex_line = _extract_answer(conn, spec, blocks)
        if _ex_line:
            out.append(_ex_line)
    out.append(head)
    # ⚠ 2026-10-03：语料里确有**空篇残片**（0 句 / 0 字，元曲 144 篇）。「没有任何一句…」
    #   「每一句都…」这类条件会被它们**平凡**满足（空集里没有反例/每个元素都满足）。
    #   计数与真值口径一致（它们确实在命中集合里），但作为**证据**必须说明白，
    #   否则读者会以为系统拿残片充数（实测 Q0008：命中 144 篇 = 全库 144 个空篇）。
    if blocks and all((b.get('sent_n') or 0) == 0 for b in blocks):
        out.append('　　　说明：以上展示的篇目均为语料中的**空篇残片**（0 句 / 0 字）；'
                   '它们只是该类条件的**平凡**满足者（空集里没有反例），不代表真实创作。')
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
                   % ('以上条件' if retrieve.has_hard(spec)
                      else '全库（本句未解析出筛选条件）',
                      ei['label'],
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
    ok, problems = _with_unsupported(spec, ok, problems)
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
