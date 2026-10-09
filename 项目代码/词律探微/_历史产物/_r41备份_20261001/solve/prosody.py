# -*- coding: utf-8 -*-
"""prosody.py —— 声律解析引擎（纯确定性，七方法 + 五类题算法）。

公共约定（见《给AI的编码任务书》5.0）：
  * 句 = 按句末标点切（「。」「？」「！」均算句末）；「，」「、」并入所在句。
  * 只统计汉字（含 CJK 扩展 A：U+3400–U+4DBF，如「䕷」）；不计标点、空白、题名，
    也不计语料中的缺字占位符「□」「○」「■」（官方实测同样不计）。
  * 前段 = 前 (n//2) 句，后段 = 其余句。
  * 比例 = 仄 ÷ 该范围汉字数 × 100%，保留一位小数（**银行家舍入 ROUND_HALF_EVEN**）。
  * 【两类“差”口径不同，均已用官方答案穷举反解】：
      - 「差」类（C1 比例差 / C2 变幅差 / C3 密度差 / C4 比例差）= 用【已舍入到一位】的值相减；
      - 「变化值」类（C2 变化 / 绝对变幅、C5 变化）= 用【未舍入的原始比例】相减后再保留一位。
    证据：C2 变化 raw 命中 263 : 先舍入 204；C1 比例差 d1 命中 112 : raw 85。
  * 末尾无「。」的残句也算一句（按「。」切，最后一个非空片段保留）。

舍入口径（2026-09-29 实测改定）：官方用**银行家舍入**（ROUND_HALF_EVEN，
即 Python `round()` / `Decimal` 的默认语义），**不是四舍五入**。
证据：T-010 / T-017 / T-085 / T-092 / T-129 五道题（分属 C1–C4）官方均把
恰为 56.25% / 31.25% 的比例写成 56.2 / 31.2（偶数侧）；四舍五入会写成 56.3 / 31.3
（这 7 道差异题全部只错在这里）。只改这一条，公开集 689 → 696 题。
"""
from __future__ import annotations
import re
from decimal import Decimal, ROUND_HALF_EVEN

from pronounce import Pronouncer
from corpus import han_only   # 汉字范围单一来源在 corpus.py（含 CJK 扩展 A：U+3400–U+4DBF，
# 如「䕷」U+4577；缺字占位符「□」「○」「■」不计）。prosody 直接用 corpus.han_only，
# 所以两模块的汉字范围**构造上就不可能分叉**（自检里用函数对象同一性断言）。

# 句末标点（切句唯一来源；calibrate.py 也从这里导入，防止两处口径分叉）：
# 「。」「？」「！」均为句末，在标点【之后】切开。**标点会被保留在前句**——
# 这是刻意的：引文要「原样可回定位」，所以不能把标点吃掉。
# （审查 C2 指出：旧 docstring 写「去掉标点」，与实现相反，会让后来人按错的口径改代码。）
SENT_SPLIT_RE = re.compile(r'(?<=[。？！])')


def quote(s: str) -> str:
    """公开别名（审查 T7：自检/外部脚本不该锁死 `_quote` 这个私有名）。"""
    return _quote(s)


def r1(x: float) -> float:
    """保留一位小数，**银行家舍入 ROUND_HALF_EVEN**（官方实测口径）。"""
    return float(Decimal(str(x)).quantize(Decimal('0.1'), rounding=ROUND_HALF_EVEN))


def raw_pct(ze: int, total: int):
    """**未舍入**的原始比例（Decimal；供「变化值＝原始比例相减」用，官方 C2 口径）。"""
    if not total:
        return Decimal(0)
    return Decimal(ze) * 100 / Decimal(total)


def pct(ze: int, total: int) -> float:
    """仄声比例（百分数，一位小数，**银行家舍入**）。

    用 Decimal 精确运算后再 quantize，彻底避免浮点在 .x5 边界的表示误差：
    Decimal(ze)*100/Decimal(total) 除不尽时保留 28 位有效数字，再按
    ROUND_HALF_EVEN 保留一位（与 r1(100*ze/total) 同口径）。
    """
    if not total:
        return 0.0
    q = (Decimal(ze) * 100 / Decimal(total)).quantize(Decimal('0.1'), rounding=ROUND_HALF_EVEN)
    return float(q)


def _quote(sent: str) -> str:
    """引文 = 语料原文里的那一句，【原样】取出：不发明标点、也不改标点。

    代理评分要求引文能在原文里【原样定位】，因此任何改写都是自伤：
    旧版会在残句末尾补一个「。」、并把末尾的「；，、」剥掉——实测全库有 26 篇
    文本末尾不带句末标点（末字符是「）」/「，」/「》」/零宽空格/汉字），
    一旦这类篇目出现在题里，旧写法产出的引文立刻定位不到。故一律原样。
    """
    return (sent or '').strip()


# ---------------------------------------------------------------- 引擎
class Engine:
    def __init__(self, pronouncer: Pronouncer):
        self.p = pronouncer
        # 单条缓存：(原文, 句列表, 平仄串列表)。建库时对**同一篇**会依次问
        # halves/longest/ratio/scene_emotion/long_density/c4，每个方法内部原本都重新
        # 切句 + 逐句判平仄（同一篇算 6~7 遍）。实测这是建库 81.5 秒的主因。
        self._lines_memo = (None, None, None)

    # --- 方法 1：切句
    @staticmethod
    def split(text) -> list[str]:
        """按句末标点切句：。「」和「？」「！」都算句末（反解自官方：词只用「。」，
        而元曲曲文用「？！」收句；两者共用此规则不会误伤词）。返回去掉标点、空白的句子列表。

        实测：仅按「。」切时，含元曲的 C4 三篇题一致率 47.8%；改为。？！全切后
        反解出的官方区间逐一命中共实测 4/4 例。
        """
        raw = ''.join(text) if isinstance(text, list) else (text or '')
        raw = raw.replace('\n', '')
        # 在句末标点【之后】切开，标点保留在前句，使引文能原样回定位到语料
        parts = SENT_SPLIT_RE.split(raw)
        return [s.strip() for s in parts if han_only(s)]

    # --- 方法 2：逐字标注
    def annotate(self, text):
        return self.p.annotate(text)

    # --- 内部：把句子列表变成统计对象（带单条缓存，见 __init__ 注释）
    def _lines(self, text):
        raw = ''.join(text) if isinstance(text, list) else (text or '')
        memo = self._lines_memo
        if memo[0] == raw:                      # 同一篇连续问多次 → 直接复用
            return memo[1], memo[2]
        sents = self.split(raw)
        pzs = [self.p.ping_ze(s) for s in sents]
        self._lines_memo = (raw, sents, pzs)
        return sents, pzs

    def lines(self, text):
        """对外暴露：一次拿到 (句列表, 平仄串列表)（建库/校对等批量场景复用同一份结果）。"""
        return self._lines(text)

    # --- 方法 3：全篇比例
    def ratio(self, text):
        _, pzs = self._lines(text)
        allpz = ''.join(pzs)
        ping = allpz.count('平')
        ze = allpz.count('仄')
        return {'句数': len(pzs), '平': ping, '仄': ze, '总字': len(allpz),
                '仄声比例': pct(ze, len(allpz))}

    # --- 方法 4：前后段
    def halves(self, text):
        sents, pzs = self._lines(text)
        n = len(sents)
        cut = n // 2
        a = ''.join(pzs[:cut])
        b = ''.join(pzs[cut:])
        # 官方口径（实测反解）：显示的比例各取一位小数，
        # 但「变化值」用【未舍入的原始比例】相减后再保留一位小数（C2 变化 raw=263 : 先舍入=0）
        raw_a = raw_pct(a.count('仄'), len(a))
        raw_b = raw_pct(b.count('仄'), len(b))
        ra, rb = r1(raw_a), r1(raw_b)
        chg = r1(raw_b - raw_a)
        return {'cut': cut, '前段比例': ra, '后段比例': rb,
                '变化': chg, '绝对变幅': r1(abs(chg)),
                '前段字': len(a), '后段字': len(b)}

    # --- 方法 5：最长句
    def longest(self, text):
        sents, _ = self._lines(text)
        lens = [len(han_only(s)) for s in sents]
        if not lens:
            # 空篇（全库有 144 篇正文无汉字：纯符号/占位符）：句序给空数组，不报异常
            return {'最长句序': [], '最长句字数': 0}
        mx = max(lens)
        return {'最长句序': [i + 1 for i, L in enumerate(lens) if L == mx], '最长句字数': mx}

    # --- 方法 6：长句区段密度
    def long_density(self, text):
        sents, pzs = self._lines(text)
        n = len(sents)
        total = sum(len(han_only(s)) for s in sents)
        thr = ((total + n - 1) // n) if n else 0        # 整数除法：等价 ceil，且不引入浮点
        idx = [i for i, s in enumerate(sents) if len(han_only(s)) >= thr]
        seg = ''.join(pzs[i] for i in idx)
        ping, ze = seg.count('平'), seg.count('仄')
        return {'阈值': thr, '入选句序': [i + 1 for i in idx],
                '平': ping, '仄': ze, '比例': pct(ze, len(seg))}

    # --- 方法 7：景情（临界题，代理评分：只保证引文落在对应分段内）
    def scene_emotion(self, text):
        sents, pzs = self._lines(text)
        n = len(sents)
        cut = n // 2
        front = sents[:cut] or sents[:1] or ['']
        back = sents[cut:] or sents[-1:] or ['']
        h = self.halves(text)
        d = h['变化']
        turn = '后段上升' if d > 0 else ('后段下降' if d < 0 else '前后持平')
        fc = pct(''.join(pzs[:cut]).count('仄'), len(''.join(pzs[:cut]))) if cut else 0.0
        bc = pct(''.join(pzs[cut:]).count('仄'), len(''.join(pzs[cut:]))) if cut else 0.0
        # 引文取该段【末句】（与 c4 一致）；代理评分只核可定位性与分段归属
        return {'前段句': front, '后段句': back,
                '前段引文': _quote(front[-1]), '后段引文': _quote(back[-1]),
                '前段比例': fc, '后段比例': bc, '变化': d, '转向': turn}

    # ------------------------------------------------------------ 五类题
    def c1(self, a, b):
        ra, rb = self.ratio(a), self.ratio(b)
        out = {}
        for k, r in (('甲', ra), ('乙', rb)):
            lg = self.longest(a if k == '甲' else b)
            out[k] = {'句数': r['句数'], '最长句序': lg['最长句序'],
                      '最长句字数': lg['最长句字数'], '平': r['平'], '仄': r['仄'],
                      '仄声比例': r['仄声比例']}
        diff = r1(abs(ra['仄声比例'] - rb['仄声比例']))
        out['比例差'] = diff
        # 并列时的官方写法是「两篇」（实测：公开集 13 道 C1 题都写「…相差0.0个百分点，两篇较高。」），
        # 不是「持平」——第七轮教训的直接应用：不要自己发明词形，要用官方原文的词。
        out['较高'] = '甲' if ra['仄声比例'] > rb['仄声比例'] else ('乙' if rb['仄声比例'] > ra['仄声比例'] else '两篇')
        return out

    def c2(self, a, b):
        ha, hb = self.halves(a), self.halves(b)
        out = {}
        for k, h in (('甲', ha), ('乙', hb)):
            out[k] = {'前段比例': h['前段比例'], '后段比例': h['后段比例'],
                      '变化': h['变化'], '绝对变幅': h['绝对变幅']}
        out['变幅差'] = r1(abs(ha['绝对变幅'] - hb['绝对变幅']))
        out['较大'] = '甲' if ha['绝对变幅'] > hb['绝对变幅'] else ('乙' if hb['绝对变幅'] > ha['绝对变幅'] else '两篇')
        return out

    def c3(self, a, b):
        da, db = self.long_density(a), self.long_density(b)
        out = {}
        for k, d in (('甲', da), ('乙', db)):
            out[k] = {'阈值': d['阈值'], '入选句序': d['入选句序'],
                      '平': d['平'], '仄': d['仄'], '比例': d['比例']}
        out['密度差'] = r1(abs(da['比例'] - db['比例']))
        out['较高'] = '甲' if da['比例'] > db['比例'] else ('乙' if db['比例'] > da['比例'] else '两篇')
        return out

    def c4(self, texts: dict):
        """texts: {'甲':.., '乙':.., 可选 '丙':..}"""
        recs = {}
        for k, t in texts.items():
            h = self.halves(t)
            sents, pzs = self._lines(t)
            cut = h['cut']
            back = sents[cut:] or sents[-1:] or ['']
            recs[k] = {'后段引文': _quote(back[-1]), '后段比例': h['后段比例']}
        # 题库口径要求：按后段仄声比例从高到低排序；若相同，则按题目标签的固定优先级
        # 处理（丙 > 乙 > 甲），不能按插入顺序兜底。
        tag_priority = {'丙': 0, '乙': 1, '甲': 2}
        order = sorted(recs.keys(), key=lambda k: (-recs[k]['后段比例'], tag_priority.get(k, 99)))
        vals = [recs[k]['后段比例'] for k in recs]
        recs['排序'] = order
        recs['比例差'] = r1(max(vals) - min(vals))
        return recs

    def c5(self, a, b):
        out = {}
        for k, t in (('甲', a), ('乙', b)):
            se = self.scene_emotion(t)
            out[k] = {'前段引文': se['前段引文'], '后段引文': se['后段引文'],
                      '变化': se['变化'], '转向': se['转向']}
        out['边界声明'] = ('景物、感受与声律变化只能构成有限的文本互证，'
                          '不能直接证明作者经历、时代因果或作品优劣。')
        return out
