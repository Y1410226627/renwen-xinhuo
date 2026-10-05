# -*- coding: utf-8 -*-
"""uncertainty_report.py —— **可存疑清单**（让「100%」更可信，而不是更弱）。

由来（2026-10-05，朋友项目对照）：
    朋友把「**待核 / 差异**」当成**一等状态**（104 通过 / 39 待核 / 1 差异，三态并存显示），
    而不是把「待核」藏起来当作失败。反观我们：题库 1000/1000 全对的叙事很漂亮，
    但**没有任何「我们不确定」的位置**。真被追问「你这 58852 首里有多少首的平仄是可存疑的」，
    现在答不上来。

本工具**只读** `data/corpus.db` + 覆写表，产出三类**可存疑**篇目的清单与计数：
  A. **走覆写表取音**的篇目（这些字的平仄是**人工标定**、非 ypinyin 直读）；
  B. **空篇残片**（0 句 / 0 字，通常来自元曲切分）；
  C. **含多音字**的篇目（该字有多个合法读音，本系统**取首音**——见下注）。

⚠ 先证口径、再报数：本工具**不改任何答案**，因此**零回归安全**（不入 solver）。
⚠ C 类的「多音」判据：用 pypinyin 对单字取全部读音，若 >1 个**且声调不同**则记疑；
   这是**粗判**（未做语境消歧），意在给出**上界**，不是精确清单——报告里已注明。

用法：
  python tools/uncertainty_report.py --db data/corpus.db [--write data/存疑清单.md]
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

from pronounce import Pronouncer, default_overrides_path, _KNOWN_RE   # noqa: E402


def _overrides():
    p = default_overrides_path()
    if p and os.path.isfile(p):
        return json.load(open(p, encoding='utf-8-sig'))
    return {}


def _pz_flip_chars(pron):
    """语料里实际出现过、且**异读会翻转平/仄**的字（真正有意义的存疑）。

    判据（比「多音」严得多，也更相关）：该字存在**至少两个不同声调**的读音，
    且其中**既有平（1/2 声）又有仄（3/4 声）**——此时「取首音」这一选择会**改变平仄统计**。
    只同侧（如「雨」3/4 声都是仄）的字不算存疑，因为怎么读都记仄。
    """
    import re
    from pypinyin import pinyin, Style
    out = set()
    for ch in list(pron._tone_cache):           # 已被语料触达的字
        try:
            rs = pinyin(ch, style=Style.TONE3, heteronym=True, errors='default')[0]
        except Exception:
            rs = []
        tones = set()
        for r in rs:
            m = re.search(r'([1-5])$', r)
            if m and m.group(1) != '5':
                tones.add(m.group(1))
        pz = {('平' if t in '12' else '仄') for t in tones}
        if len(pz) > 1:                          # 既有平又有仄 → 取音会翻转平仄
            out.add(ch)
    return out


def main():
    ap = argparse.ArgumentParser(description='可存疑清单（只读）')
    ap.add_argument('--db', required=True)
    ap.add_argument('--write', metavar='OUT')
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    pron = Pronouncer.default()
    ovr = _overrides()
    ovr_chars = ''.join(sorted(ovr.keys()))

    # 预热：把语料全部汉字喂进 tone 缓存（只为多音粗判取字集）
    rows_all = conn.execute('SELECT raw FROM poems WHERE raw IS NOT NULL').fetchall()
    for (raw,) in rows_all:
        for ch in (raw or ''):
            if _KNOWN_RE.match(ch):
                pron.tone(ch)
    multi = _pz_flip_chars(pron)

    n_poems = conn.execute('SELECT COUNT(*) FROM poems').fetchone()[0]

    def count_with(chars):
        """含任一给字的篇数（**Python 侧扫描**：字数一多，SQL 的 OR 树会超深）。"""
        cs = set(chars)
        if not cs:
            return 0
        n = 0
        for (raw,) in rows_all:
            if any(ch in cs for ch in (raw or '')):
                n += 1
        return n

    a = count_with(ovr_chars)
    b = conn.execute('SELECT COUNT(*) FROM poems WHERE sent_n = 0 OR han_len = 0').fetchone()[0]
    c = count_with(multi)

    # 多音字按「语料出现次数」排序（给报告一个可读的头部）
    freq = {}
    for (raw,) in rows_all:
        for ch in (raw or ''):
            if ch in multi:
                freq[ch] = freq.get(ch, 0) + 1
    top_chars = [ch for ch, _ in sorted(freq.items(), key=lambda kv: -kv[1])[:40]]

    lines = []
    lines.append('# 可存疑清单（uncertainty report）\n')
    lines.append('> 本清单**只读语料库**，不修改任何答案，故对交付零影响。')
    lines.append('> 目的：把「我们不确定的位置」显式列出——「100% 全对」的前提是**口径明确且一致**，')
    lines.append('> 而非「所有字都经学术校勘」（本库据公开整理本复算，**不作学术引证**）。\n')
    lines.append('## 全库规模\n')
    lines.append('- 篇目总数：**%d**\n' % n_poems)
    lines.append('## A. 走覆写表取音（人工标定，非 ypinyin 直读）\n')
    lines.append('- 覆写字：%s（共 %d 个）' % ('、'.join(ovr.keys()), len(ovr)))
    lines.append('- 含覆写字的篇目：**%d** 篇（占 %.2f%%）' % (a, 100.0 * a / max(1, n_poems)))
    lines.append('- 说明：这些字的平仄是**人工标定**结果；若标定与古音/别本不同，则该篇统计可存疑。\n')
    lines.append('## B. 空篇残片（0 句 / 0 字）\n')
    lines.append('- **%d** 篇' % b)
    lines.append('- 说明：通常来自元曲切分；它们会**平凡满足**「没有任何一句…」「每一句都…」这类条件，')
    lines.append('  在作答时会另行声明（见 `ask.py`），此处只作清单。\n')
    lines.append('## C. 异读会翻转平仄的字（本系统一律取首音）\n')
    lines.append('- 这类字（语料实际触达的）：**%d** 个——即「换一个合法读音，平/仄会翻转」的字' % len(multi))
    lines.append('- 含这类字的篇目：**%d** 篇（占 %.2f%%）' % (c, 100.0 * c / max(1, n_poems)))
    lines.append('- ⚠ 占比为何这么高：这些都是**常用多音字**（看/过/思/为/与…），几乎每篇都有。')
    lines.append('  本系统对它们的处理是**确定性的**——一律**取首音**（不按语境猜），')
    lines.append('  因此在**同一口径**下，任意两遍跑出的数字**逐字节一致**（见 `tools/regress.py`）。')
    lines.append('- 但须承认：**若**某篇的某个多音字「本应」读另一音，则该篇的平仄统计会不同。')
    lines.append('  这是**口径内的一致**，不等于**古音校勘的准确**。')
    lines.append('- 出现最多的前 40 个：**%s**' % '、'.join(top_chars))
    lines.append('  判据为**粗判**：单字存在多个不同声调读音且跨平仄两侧即记疑，**未做语境消歧**；')
    lines.append('  这是**上界**，不是精确清单。\n')
    txt = '\n'.join(lines)
    if args.write:
        open(args.write, 'w', encoding='utf-8').write(txt)
        print('已写入：%s' % args.write)
    print('篇目 %d；A 覆写 %d；B 残片 %d；C 多音 %d；多音字数 %d'
          % (n_poems, a, b, c, len(multi)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
