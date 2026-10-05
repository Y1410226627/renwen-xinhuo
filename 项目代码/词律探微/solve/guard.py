# -*- coding: utf-8 -*-
"""M9 护栏：对生成层的输出做**四道确定性校验**，防幻觉落进报告。

四道护栏（《系统实现逻辑》5.5）：
    ① 数字不可造：回答里每个数字字面量，必须来自**它所在那句所引用的证据块**的数字白名单
       （没有引用标记的句子，才退回到"全部证据块的白名单"——这是**刻意留的宽松通道**，审查 B20/D1
       曾把它当漏洞：聚合题/配对题本来就没有逐篇 `[E#]`，靠 `allow=` 传**独立复算过的**数字；
       真要收紧就得先给这两类题加逐篇引用，那是另一件事，这里如实写明以免后人误解承诺）。
       ——外部交付是「在任一证据块里出现过就算过」的集合级校验，我收紧到**字段级带引用**。
       ——另加「比例自洽」：凡出现 `xx.x%` 且证据块里给了平/仄与汉字数，则必须等于
         `100×仄/汉字` 按**银行家舍入**取一位（防止"数字有出处但算错了"这种更隐蔽的错）。
    ② 引用必须落地：每个 `[E#]` 都要存在；引文必须**逐字**出现在**被引用块**的
       标题或句级片段里（且必须等于某个**整句**，不允许拼接、不允许改标点）。
    ③ 无据即认账：证据为空时必须输出「现有语料未见支持…」，且**不许出现任何数字与引文**。
    ④ 边界声明：按**问句类型**校验（类型化边界），互斥标记判定，防止"模板句恰好过检"。

本模块只做校验；校验是纯确定性集合/字符串运算，可被 `tools/qa_eval.py` 与演示层复用。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import evidence                                              # noqa: E402

NUM_RE = re.compile(r'\d+(?:\.\d+)?')
PCT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
EID_RE = re.compile(r'\[E(\d+)\]')


def _r1(x):
    """官方口径：一位小数 + 银行家舍入。"""
    from decimal import Decimal, ROUND_HALF_EVEN
    return float(Decimal(repr(x)).quantize(Decimal('0.1'), rounding=ROUND_HALF_EVEN))


def check_numbers(answer_text, blocks, allow=()):
    """护栏①（字段级 + 引用绑定）。返回 (通过?, 问题列表)。

    `allow` 用于放行**非论断性数字**：查询条件里用户自己给的阈值、以及 pid 里的编号
    （pid 是可点回的定位串，不是系统对语料下的断言）。
    """
    all_allow = evidence.all_numbers_phrase(blocks, extra=[len(blocks)])
    extra = set()
    for v in allow:
        extra.add(str(v))
        try:
            extra.add('%.1f' % float(v))
        except (TypeError, ValueError):
            pass
    per_block = {b['eid']: evidence.numbers_of(b) for b in blocks}
    problems = []
    for raw_line in answer_text.splitlines():
        line = EID_RE.sub(' ', raw_line)          # [E#] 里的编号不是论断数字
        cited = {'E' + m for m in EID_RE.findall(raw_line)}
        allow_line = set(extra)
        for e in cited:
            allow_line |= per_block.get(e, set())
        if not cited:
            allow_line |= all_allow
        for m in NUM_RE.findall(line):
            cands = {m}
            try:
                f = float(m)
                cands |= {'%.1f' % f, str(int(f)) if f == int(f) else '%.1f' % f,
                          '-%s' % m, '-%.1f' % f}
            except ValueError:
                pass
            if not (cands & allow_line):
                problems.append('数字无出处（%s）：%s ｜行：%s'
                                % ('／'.join(sorted(cited)) or '无引用', m,
                                   raw_line.strip()[:60]))
    # 比例自洽：把证据块里所有 (平,仄,汉字数) 与实际写出的百分比交叉验算
    ok_pairs = set()
    for b in blocks:
        cands = [(b['han_len'], b['ze'], b['ze_ratio'])]
        cands += [(L['han_len'], L['ze'], None) for L in b['lines']]
        for nc, nz, given in cands:
            if nc:
                pct = _r1(100.0 * nz / nc)
                ok_pairs.add('%.1f' % pct)
                ok_pairs.add(('%.1f' % pct).rstrip('0').rstrip('.'))
            else:
                # ⚠ 2026-10-03：`han_len == 0`（语料里确有 0 句 / 0 字 的残片）时，
                #   100×仄/0 无定义、旧写法直接跳过 → 答案里那个合法的 0.0% 被判「不自洽」
                #   （实测 Q0008：头条是元曲残片，6 处 0.0% 全被误判）。按「无字即 0%」放行。
                ok_pairs.add('0.0')
                ok_pairs.add('0')
    # ⚠️ 顺序要紧（审查 B21）：旧版先 `if m in all_allow: continue`，而模板里每个比例本来
    # 就在 all_allow 里 → 这道「比例自洽」**从未真正触发**。现在：只要证据块里有 (平,仄,汉字数)，
    # 写出的百分比就必须等于 100×仄/汉字（银行家舍入）。用户给的阈值（extra）与聚合/配对题的
    # 数字（blocks 为空时另有独立复算）不受此约束。
    for m in PCT_RE.findall(answer_text):
        if not blocks:
            break                      # 聚合/配对题：数字由 allow（独立复算）管，见各门禁
        if any(_isnum(x) and abs(float(m) - float(x)) < 1e-9 for x in extra):
            continue
        if float(m) not in {float(x) for x in ok_pairs if _isnum(x)}:
            problems.append('比例与证据块数字不自洽：%s%%' % m)
    return (not problems), problems


def _isnum(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def check_citations(answer_text, blocks):
    """护栏②（引用落地 + 引文按块校验 + 必须是整句）。返回 (通过?, 问题列表)。

    两种引号分别管：
      · 「」＝**我方模板**专用，必须**逐字等一整句**（不允许改标点、不允许拼接）；
      · “ ”（以及 ASCII 双引号）＝**大模型写法**专用，必须能在证据里找到（子串即可，
        因为模型常把句末句号吞掉），但不管多短都不许凭空造——
        实测事故：模型写了「句脚字为“灯”或“声”」，而“声”根本不在证据里（问题里也没解析出来）。
    """
    problems = []
    valid = {b['eid'] for b in blocks}
    per_block_texts = {b['eid']: evidence.texts_of(b) for b in blocks}
    all_texts = evidence.all_texts(blocks)
    pool = []
    for b in blocks:
        for k in ('dynasty', 'author', 'title', 'cipai', 'scene'):
            if b.get(k):
                pool.append(str(b[k]))
        for L in (b.get('lines') or []):
            pool.append(L.get('text') or '')
            if L.get('tail'):
                pool.append(L['tail'])
    pool = [t for t in pool if t]
    # 逐行建立「行 → 该行引用的证据号集合」：引文必须能在**同一行被引的块**里逐字找到
    # 用**列表**而不是 dict：重复行会让 dict 的后一行覆盖前一行（审查 B27）
    line_cited = [(ln, {'E' + m for m in EID_RE.findall(ln)})
                  for ln in answer_text.splitlines()]
    for m in EID_RE.findall(answer_text):
        if ('E' + m) not in valid:
            problems.append('引用了不存在的证据编号 [E%s]' % m)
    for quoted in re.findall(r'「([^」]+)」', answer_text):
        hosts = set()
        for ln, eids in line_cited:
            if quoted in ln:
                hosts |= eids
        cand = set()
        for e in hosts:
            cand |= per_block_texts.get(e, set())
        if not cand:
            cand = all_texts            # 该行没有引用标记：退回到全部被引块
        # texts_of 只含「标题」与「整句原文」，所以「在集合里」等价于「逐字且为整句」
        if quoted in cand:
            continue
        # 例外：语料**标题自身**就带「」（如《蝶恋花·…「戏」字韵词…》）——
        # 这是台账上就有的引号，不是我们拼接的引文：逐字子串即可。
        pool_t = []
        for b in (blocks if not hosts else [x for x in blocks if x['eid'] in hosts]):
            pool_t += [str(b.get(k) or '') for k in ('title', 'cipai', 'author', 'dynasty')]
        if any(quoted in t for t in pool_t if t):
            continue
        problems.append('引文未逐字出现在被引证据块中（或不是整句）：「%s」' % quoted)
    for quoted in re.findall(r'[“"]([^”"]+)[”"]', answer_text):
        q = quoted.strip()
        if q and not any(q in t for t in pool):
            problems.append('双引号里的内容不是证据原文（不得凭空引用）：“%s”' % q)
    return (not problems), problems


def check_no_support(answer_text, refused):
    """护栏③：拒答时不许出现数字与引文（认账要认得干净）。"""
    if not refused:
        return True, []
    problems = []
    body = answer_text.replace('【查询理解】', '')
    if NUM_RE.search(EID_RE.sub(' ', body)):
        problems.append('拒答文本里仍出现数字')
    if re.search(r'「[^」]+」', answer_text):        # 成对的「」才算引文（单个字符不算，审查 B25）
        problems.append('拒答文本里仍出现引文')
    if '"' in answer_text or '“' in answer_text:      # ASCII／弯引号也都算（审查 B26/C21）
        problems.append('拒答文本里仍出现引文（ASCII／弯引号）')
    if '未见支持' not in answer_text:
        problems.append('拒答文本未包含「未见支持」的明确表述')
    return (not problems), problems


BOUNDARY_KINDS = {
    '数值型': {'markers': ('形式', '声调'), 'conflicts': ('须另据', '不等于因果', '不构成文学价值判断'),
             'negs': ('不能', '不可', '无法', '不宜')},
    '意图型': {'markers': ('须另据',), 'conflicts': ('不等于因果', '不构成文学价值判断'),
             'negs': ('不能', '无法', '不可', '不宜')},
    '因果型': {'markers': ('不等于因果', '相关性'), 'conflicts': ('不构成文学价值判断',),
             'negs': ('不能', '不等于', '无法', '不宜')},
    '优劣型': {'markers': ('不构成文学价值判断',), 'conflicts': ('须另据',),
             'negs': ('不构成', '不能', '无法', '不宜')},
}


def check_boundary(kind, answer_text, required=True):
    """护栏④（类型化边界，互斥判定）。返回 (通过?, 问题列表)。"""
    if not required:
        return True, []
    spec = BOUNDARY_KINDS.get(kind)
    if not spec:
        return True, []
    problems = []
    if not any(n in answer_text for n in spec['negs']):
        problems.append('缺少限定词（%s）' % '/'.join(spec['negs'][:3]))
    if not any(m in answer_text for m in spec['markers']):
        problems.append('未含本类专属标记（%s）' % '/'.join(spec['markers']))
    bad = [c for c in spec['conflicts'] if c in answer_text]
    if bad:
        problems.append('含他类专属标记（%s），与「%s」问句不匹配' % ('/'.join(bad), kind))
    return (not problems), problems


def verify(answer_text, blocks, boundary_kind=None, boundary_required=True, refused=False,
           allow=()):
    """一次跑完四道护栏。返回 (是否全过, 问题清单)。"""
    problems = []
    if refused:
        ok3, p3 = check_no_support(answer_text, True)
        problems += p3
    else:
        ok1, p1 = check_numbers(answer_text, blocks, allow=allow)
        ok2, p2 = check_citations(answer_text, blocks)
        problems += p1 + p2
    _ok4, p4 = check_boundary(boundary_kind, answer_text, boundary_required)
    problems += p4
    return (not problems), problems
