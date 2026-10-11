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
import retrieve                                              # noqa: E402

NUM_RE = re.compile(r'\d+(?:\.\d+)?')
PCT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
EID_RE = re.compile(r'\[E(\d+)\]')
# ⚠ 2026-10-06 修（外部审查 P1-23）：原 NUM_RE 只抓阿拉伯数字，「共五百篇」「一百零八处」
#   这类**中文数字断言**完全绕过护栏①。这里补一个中文数字扫描（数值换算复用 retrieve.cn_num，
#   与检索侧同一实现，避免两套口径）。为压掉误报：只收「长度≥2 且含单位字（十百千万亿）」
#   或「长度≥3」的串，且扫描前**剥离引文**（语料词句里「二十四桥」之类极常见，不是系统断言）。
CN_NUM_RE = re.compile(r'[零一二三四五六七八九十百千万亿两]{2,12}')
# ★ 2026-10-11（自查第 4 遍）：**单字中文数字 + 比例/倍数单位**的量化断言（「约三成」「八倍」）。
#   `CN_NUM_RE` 要求长度 ≥2，单字扫不到；但「三成」这类在拒答文本里同样是没认账干净的量化。
#   ⚠ 只收**比例/倍数**单位（成/分/倍）——「一篇」「两个」这类「数词+量词」在中文里是
#     习语（"不留一篇""某一个"），把它们也当量化断言会**大面积误伤**我方自己的拒答文案
#     （实测：一加"篇/个"就令 4 条正规拒答、1 条自检用例被判未通过）。比例/倍数则几乎
#     只用于真正的数量断言，误报可控。
CN_ONE_NUM_RE = re.compile(r'[一二三四五六七八九十两](?=[成分倍])')


def _cn_values(s):
    """中文数字串 → 可能是数量断言的数值写法集合；不像数量断言时返回空集。"""
    if len(s) < 2:
        return set()
    if len(s) == 2 and s[0] not in '十百千万亿' and s[1] not in '十百千万亿':
        return set()                      # 「三五」「一一」这类不作数量断言
    v = retrieve.cn_num(s)
    if v is None:
        return set()
    f = float(v)
    return {str(v), '%.1f' % f, str(int(f)) if f == int(f) else '%.1f' % f, '%.1f' % abs(f)}


# ⚠ 2026-10-09 扩：书名号《…》里的数字是**篇名/词牌名**（如《忆秦娥·十六夜望月，次韵和鹓雏》、
#   《十六字令》），与语料引文同理，**不是系统对数量的断言** —— 一并剥离，消除误报
#   （`tools/check_extreme.py` 四·护栏通过 实测因「十六」误报而 FAIL）。
_QUOTE_SPAN_RE = re.compile(r'「[^」]*」|[“"][^”"]*[”"]|《[^》]*》')


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
    # ⚠ 2026-10-11 修（二期能力增补 · 语义检索暴露的**既有隐患**）：证据块**逐句渲染**会给
    #   每句标上**句序序数**（「第 N 句」，= `L['idx']+1`）。这些序数是**通用标号**（任何篇都能
    #   出现 1、2、3…），与某篇的 change 绝对值**同形**时极易误伤：实测某篇 change=-2.0 →
    #   abs_only={'2','2.0'}，于是一篇**未引用**的「第 2 句」行被判「绝对值专属写法」而误剥。
    #   序数**永远不是**「change 的绝对值专属写法」——故在 abs_only 里**全局排除**所有序数。
    _ordinals = set()
    for b in blocks:
        for L in b.get('lines', []):
            if L.get('idx') is not None:
                _ordinals |= evidence.num_variants(L['idx'] + 1)
    # ⚠ 2026-10-06 修（外部审查 P1-24）：「变化值」与「绝对变幅」语义不同，但
    #   evidence.numbers_of 把 change 与其 abs 混进同一扁平集合——证据 change=-3.7 时，
    #   答案写「变化 3.7」（未提「绝对/变幅」）也会被放行。这里按行语义收窄：
    #   行长若不含表「幅」的词，则不允许使用 change 的**绝对值专属**写法。
    _ABS_WORDS = ('绝对', '变幅', '幅度')
    abs_only = {}
    for b in blocks:
        v = b.get('change')
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError, OverflowError):
            continue
        base = {str(v), '%.1f' % f, str(int(f)) if f == int(f) else '%.1f' % f}
        derived = {'%.1f' % abs(f), str(int(abs(f))) if abs(f) == int(abs(f)) else '%.1f' % abs(f)}
        # ⚠ 2026-10-11 修（二期复核 N1 深挖）：abs_only 若只按「数值」剔除，会**误伤**
        #   同值他字段——实测 change=-8.0 时 abs_only={'8','8.0'}，而该篇某句 ping 恰为 8，
        #   于是正当写法「平 8」被判无出处。故先把「该块其他字段（不含 change）本就合法
        #   的数字」收集起来，从 abs_only 中扣除：只有**仅凭 change 的绝对值才成立**的
        #   数，才算「绝对值专属写法」。
        others = set()
        for k in ('sent_n', 'han_len', 'ping', 'ze', 'ze_ratio', 'longest_len', 'threshold'):
            if b.get(k) is not None:
                others |= evidence.num_variants(b[k])
        for L in b.get('lines', []):
            for k in ('han_len', 'ping', 'ze'):
                if L.get(k) is not None:
                    others |= evidence.num_variants(L[k])
            # ⚠ 2026-10-11 修（二期能力增补 · 语义检索暴露的**既有隐患**）：
            #   证据块正文里的**句序序数**（`render_text` 写的「第 N 句」，= `L['idx']+1`）
            #   是**定位标号**、不是论断数字，`evidence.numbers_of` 已把它算作合法。
            #   但 `abs_only` 的「扣除他字段」集合此前没算它 → 当某篇 change 恰为 ±N
            #   （如 E5 change=-2.0 → abs_only={'2','2.0'}）时，一篇**未引用**的
            #   「第 2 句」行会把 `2` 当作「绝对值专属写法」而**误剥** → 整篇答案判不过
            #   （实测：「找几首写秋景的清词」向量开启后复现）。把序数并入 `others` 即修。
            if L.get('idx') is not None:
                others |= evidence.num_variants(L['idx'] + 1)
        d = (derived - base) - others - _ordinals
        if d:
            abs_only[b['eid']] = d
    # ⚠ 2026-10-11 修（同族根因 · **跨块**视角）：某篇的 change 绝对值 `N`，可能是**另一篇**
    #   某字段的**合法值**（实测 E5 change=-7.0 → abs_only={'7','7.0'}，而 E2 某句 `ze=7` 合法）。
    #   旧版对**未引用**行会减去**所有**块的 abs_only → 把 E2 那句合法的 `ze=7` 误判「绝对值
    #   专属写法」而无出处。故这里收集「全库证据块（所有篇、所有字段，除 change 外）本就合法的
    #   数字」，在**未引用行**的判定里从 abs_only 中扣除（`_legal_anywhere`）。
    _legal_anywhere = set()
    for b in blocks:
        for k in ('sent_n', 'han_len', 'ping', 'ze', 'ze_ratio', 'longest_len', 'threshold'):
            if b.get(k) is not None:
                _legal_anywhere |= evidence.num_variants(b[k])
        for L in b.get('lines', []):
            for k in ('han_len', 'ping', 'ze'):
                if L.get(k) is not None:
                    _legal_anywhere |= evidence.num_variants(L[k])
            if L.get('idx') is not None:
                _legal_anywhere |= evidence.num_variants(L['idx'] + 1)

    problems = []
    for raw_line in answer_text.splitlines():
        line = EID_RE.sub(' ', raw_line)          # [E#] 里的编号不是论断数字
        cited = {'E' + m for m in EID_RE.findall(raw_line)}
        allow_line = set(extra)
        for e in cited:
            allow_line |= per_block.get(e, set())
        if not cited:
            allow_line |= all_allow
        if not any(w in raw_line for w in _ABS_WORDS):
            if cited:
                for e in cited:
                    allow_line -= abs_only.get(e, set())
            else:
                # ⚠ 2026-10-11 修（跨块根因）：**未引用**行无法归到某一篇，旧版减去**所有**块的
                #   abs_only → 会把「另一篇里本就合法的同值」误判无出处（实测 E5 change=-7.0 的
                #   abs_only={'7'} 误伤 E2 那句合法的 `ze=7`）。故未引用行只剥**全库证据里都
                #   取不到**的绝对值写法：`abs_only` 各块并集 减去 `_legal_anywhere`。
                _union = set()
                for s in abs_only.values():
                    _union |= s
                allow_line -= (_union - _legal_anywhere)
        for m in NUM_RE.finditer(line):
            tok = m.group(0)
            # ⚠ 2026-10-11 修（二期复核 N1）：NUM_RE 只抓「数字本体」，不含正负号，
            #   于是「变化 -10.3」与「变化 10.3」都抽出 10.3，护栏无法区分二者——
            #   只要真值恰为 -10.3，写绝对值也会命中真值的负号形态而误放行。
            #   修法：看**原文中该数字紧邻的前一个字符**是否负号，据此决定候选是否带负号。
            neg_tok = m.start() > 0 and line[m.start() - 1] in '-−'
            cands = {tok}
            try:
                f = float(tok)
                cands |= {'%.1f' % f, str(int(f)) if f == int(f) else '%.1f' % f}
                if neg_tok:
                    # 文中写作负数 → 只认同真值的负数形态
                    cands.add('-%s' % tok)
                    cands.add('-%.1f' % f)
            except ValueError:
                pass
            if not (cands & allow_line):
                problems.append('数字无出处（%s）：%s ｜行：%s'
                                % ('／'.join(sorted(cited)) or '无引用', tok,
                                   raw_line.strip()[:60]))
        # 中文数字断言（P1-23）：先剥离引文（语料原文里的「二十四桥」不是系统断言）
        scan = _QUOTE_SPAN_RE.sub(' ', line)
        for cn in CN_NUM_RE.findall(scan):
            vals = _cn_values(cn)
            if not vals:
                continue
            if not (vals & allow_line):
                problems.append('中文数字无出处（%s）：%s ｜行：%s'
                                % ('／'.join(sorted(cited)) or '无引用', cn,
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


def _pool_extras(b):
    """单个证据块里**可被正当引用**的文本池（含材料展示词形）。

    ⚠ 2026-10-09（第三轮审查排障扩展）：模型引用的是它在 FACTS 里**看到的文本**
    （如「声情转向 后段上升」「平仄串 仄仄平」「句脚 明」）——池子若只有裸值，
    这些正当引用会被误判「凭空引用」。把展示词形一并纳入；**编造的内容依然拦得住**
    （不在任何变体里）。
    """
    out = []
    for k in ('dynasty', 'author', 'title', 'cipai'):
        if b.get(k):
            out.append(str(b[k]))
    sc = b.get('scene')
    if sc:
        out += [str(sc), '声情转向 %s' % sc, '声情 %s' % sc]
    for L in (b.get('lines') or []):
        if L.get('text'):
            out.append(L['text'])
        if L.get('tail'):
            out += [str(L['tail']), '句脚 %s' % L['tail']]
        if L.get('pz'):
            out += [str(L['pz']), '平仄串 %s' % L['pz'], '平仄 %s' % L['pz']]
    return out


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
        pool += _pool_extras(b)
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
        # ⚠ 2026-10-08 新增（主人实测驱动）：「**提取型**」问句（第 N 句第 M 字是哪个字）的答案，
        #   引文天然就是**某一句里的一个字符**——`texts_of` 只收「标题 + 整句原文」，单字当然不在集合里，
        #   于是会被误判成「引文未落地」。这里精确放宽：**单字引文只要出现在「已落地」的整句中**
        #   就放行。护栏的本意是**防凭空编造**（那个字必须真实出现在被引证据块的句子里），
        #   而不是禁止引用单字；放宽后「凭空捏一个字」仍然会被拦下。
        if len(quoted) == 1 and any(quoted in s for s in (cand or all_texts)):
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
        if not q:
            continue
        # ⚠ 2026-10-06 修（外部审查 P1-22）：原版在**全部块**的文本池 `pool` 里找，于是
        #   「“明月何时照我还” [E1]」只要该句恰好也出现在 E2 就会被放行——引文与引用号
        #   **脱钩**，破坏了「引用必须落在被引块」的承诺（「」路径早已做到，弯引号没有）。
        #   现改为与「」同一规则：先按**该行出现的 [E#]** 绑定，行内没有引用标记时才退回全部块。
        hosts = set()
        for ln, eids in line_cited:
            if q in ln:
                hosts |= eids
        if hosts:
            ok = any(q in t for b in blocks if b['eid'] in hosts
                     for t in (evidence.texts_of(b)
                               | {L.get('tail') or '' for L in (b.get('lines') or [])}
                               | {L.get('pz') or '' for L in (b.get('lines') or [])}))
            if not ok:
                ok = any(q in str(b.get(k) or '') for b in blocks if b['eid'] in hosts
                         for k in ('title', 'cipai', 'author', 'dynasty', 'scene'))
        else:
            ok = any(q in t for t in pool)
        if not ok:
            problems.append('双引号里的内容不是**被引证据块**的原文（不得凭空引用）：“%s”' % q)
    return (not problems), problems


def check_no_support(answer_text, refused):
    """护栏③：拒答时不许出现数字与引文（认账要认得干净）。"""
    if not refused:
        return True, []
    problems = []
    body = answer_text.replace('【查询理解】', '')
    if NUM_RE.search(EID_RE.sub(' ', body)):
        problems.append('拒答文本里仍出现数字')
    # ★ 2026-10-11（审查 M3）：改上上面只扫**阿拉伯数字**，于是「共五百篇」「约三成」
    #   这类**中文数字**能整条绕过护栏③——「拒答要认得干净」这条纪律等于只对半种写法生效。
    #   这里复用护栏①同款中文数字扫描（含"剥离引文/书名号"的同款降噪，避免「十六字令」
    #   这种篇名被误判），口径与护栏①完全一致。
    # ⚠ 2026-10-11（自查第 4 遍）补：`CN_NUM_RE` 要求「长度 ≥ 2」，于是**单字中文数字**
    #   （「约三成」「八倍于前」）仍能绕过——`findall` 根本扫不到。这些在拒答文本里同样是
    #   "没认账干净"的量化断言。这里补 `CN_ONE_NUM_RE`：只认**比例/倍数**单位（成/分/倍）。
    #   ⚠ 为何只收这三类单位：初版把量词放宽到「篇/首/个/条/句/字/位/名/处/次/种/层/档」，
    #     结果**大面积误伤**我方自己的拒答文案（「不留一篇」「某一个」是习语而非数量断言），
    #     实测令 4 条正规拒答 + 1 条自检用例被判未通过、`qa_eval` 通过数从 34 跌到 30。
    #     收窄到比例/倍数后复原，且这两类单位几乎只出现在真正的数量断言里（误报可控）。
    _scan = _QUOTE_SPAN_RE.sub(' ', EID_RE.sub(' ', body))
    _cn_hits = [cn for cn in CN_NUM_RE.findall(_scan) if _cn_values(cn)]
    for _m in CN_ONE_NUM_RE.finditer(_scan):
        _cn_hits.append(_m.group(0))
    if _cn_hits:
        problems.append('拒答文本里仍出现中文数字（%s）——认账要认得干净，'
                        '中文数字同样是"数字"' % '、'.join(_cn_hits[:3]))
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
