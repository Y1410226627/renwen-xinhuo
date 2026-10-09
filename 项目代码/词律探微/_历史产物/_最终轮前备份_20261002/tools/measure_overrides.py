# -*- coding: utf-8 -*-
"""measure_overrides.py —— 标定表全量度量工具（**可审计**：任何人一条命令复核每一项）。

采纳依据（2026-09-30，第六份外部交付的启发）：标定项的度量必须在**完整公开集 700 题**
的「完全一致题数」上做，不能用 C1 小目标 —— 否则会收进「小目标 +1、全量 −10」的过拟合项。

四个子命令：
  --mode gain   单项边际增益：基线=表中去掉该项，加入后测「修好 / 弄坏」（全量 700 题）
  --mode loo    留一法承重：逐项移除，测各损失多少题
  --mode scan   穷举：语料涉及的每个字 × 每个备选读音，列出所有净增益 > 0 的候选
  --mode check  校验给定覆写（`--set 长=2,别=4,绝=4`，空表写 `--set ''`）

用法：
  python tools/measure_overrides.py --question <公开700题.jsonl> --corpus <语料根> --mode gain

判读规矩（与 preflight 一致）：一项要进交付表，必须 ① 有合法普通话读音或公开集实测的
官方口径证据；② 全量净增益 > 0 **且零破坏**。只满足一条的，一律只进候选表。
"""
from __future__ import annotations
import argparse
import io
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SOLVE = os.path.join(os.path.dirname(HERE), 'solve')
sys.path.insert(0, SOLVE)

from pypinyin import pinyin as _pinyin, Style                 # noqa: E402
from corpus import load_corpus, locate_one                        # noqa: E402
from pronounce import Pronouncer, default_overrides_path      # noqa: E402
from prosody import Engine                                    # noqa: E402
from solver import parse_question, solve_one, CLS_MAP         # noqa: E402
import eval as ev                                             # noqa: E402


def load_all(question_path, corpus_dir):
    """语料 + 题面 + 标准答案 + 定位结果（定位与注音无关，只算一次）。"""
    poems = load_corpus(corpus_dir)
    qs, gold, pids = [], {}, []
    for line in io.open(question_path, encoding='utf-8-sig'):
        if not line.strip():
            continue
        q = json.loads(line)
        cls = CLS_MAP.get(q.get('类别'), (q.get('题号') or '')[-2:])
        qs.append(q)
        gold[q['题号']] = ev.parse_gold(cls, q.get('标准答案', ''))
        parts = parse_question(q.get('问题', ''))
        got = []
        for tag in ('甲', '乙', '丙'):
            sp = parts.get(tag)
            if sp:
                got.append(locate_one(poems, sp['作者'], sp['词牌'], sp['首句'], sp.get('朝代', '')))
        pids.append(got)
    return poems, qs, gold, pids


def char_index(poems, qs, pids):
    """字 -> 会受该字影响到的题目下标集合（倒排，scan 只重算相关题）。"""
    inv = defaultdict(set)
    for qi, got in enumerate(pids):
        for p in got:
            if p is None:
                continue
            for c in set(p.han):
                inv[c].add(qi)
    return inv


def readings(ch):
    """一个字在 pypinyin 里的全部备选读音 -> [(拼音, 声调)]（声调 0 = 轻声/无调）。"""
    try:
        rs = _pinyin(ch, style=Style.TONE3, heteronym=True)[0]
    except Exception:
        return []
    out = []
    for r in rs:
        t = int(r[-1]) if r and r[-1].isdigit() else 0
        if t == 5:
            t = 0
        out.append((r, t))
    return out


def base_tone(ch):
    """不带覆写时的默认声调（同 pronounce.Pronouncer.tone 的口径）。"""
    return Pronouncer(None).tone(ch)


def main():
    ap = argparse.ArgumentParser(description='标定表全量度量（公开集 700 题口径）')
    ap.add_argument('--question', required=True)
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--overrides', default=default_overrides_path(), help='交付标定表（默认交付表）')
    ap.add_argument('--mode', default='gain', choices=('gain', 'loo', 'scan', 'check'))
    ap.add_argument('--set', default='', help="check 模式：'长=2,别=4,绝=4'（空串=空表）")
    args = ap.parse_args()

    poems, qs, gold, pids = load_all(args.question, args.corpus)
    base = Pronouncer(args.overrides).overrides          # {'长': 'chang2', ...}
    print('题面 %d 道；语料 %d 首；交付标定表 %d 字 %s'
          % (len(qs), len(poems), len(base), sorted(base)))

    def score(ov, subset=None):
        """用给定覆写表重算，返回 (完全一致题数, {下标: bool})。subset=None 表示全量。"""
        eng = Engine(Pronouncer(None))
        eng.p.overrides = dict(ov)
        eng.p._tone_cache.clear()
        idxs = range(len(qs)) if subset is None else subset
        flags = {}
        for qi in idxs:
            q = qs[qi]
            r = solve_one(q, poems, eng)
            cls = r['类别']
            if not r['答案'] or gold.get(q['题号']) is None:
                flags[qi] = False
                continue
            good, _ = ev.compare(cls, r['答案'], gold[q['题号']])
            flags[qi] = bool(good)
        return sum(1 for v in flags.values() if v), flags

    base_n, base_flags = score(base)
    print('\n基线（交付表）：%d/%d = %.1f%%' % (base_n, len(qs), 100.0 * base_n / len(qs)))

    if args.mode == 'check':
        ov = {}
        for item in (args.set or '').split(','):
            if not item.strip():
                continue
            ch, t = item.split('=')
            ov[ch.strip()] = str(int(t))
        n, fl = score(ov)
        fixed = sum(1 for i in fl if fl[i] and not base_flags[i])
        broken = sum(1 for i in fl if base_flags[i] and not fl[i])
        print('指定覆写 %s -> %d/%d；相对交付表：修好 %d、弄坏 %d、净 %+d'
              % (sorted(ov.items()), n, len(qs), fixed, broken, fixed - broken))
        return

    if args.mode == 'loo':
        print('\n留一法承重（移除该项后损失多少题）：')
        for ch in sorted(base):
            ov = dict(base)
            del ov[ch]
            n, _ = score(ov)
            print('  移除「%s」：%d/%d（承重 −%d 题）' % (ch, n, len(qs), base_n - n))
        return

    if args.mode == 'gain':
        print('\n单项边际增益（全量 %d 题口径）：' % len(qs))
        for ch in sorted(base):
            wo = dict(base)
            del wo[ch]
            n_wo, f_wo = score(wo)
            n_with, f_with = score({**wo, ch: base[ch]})
            fixed = sum(1 for i in range(len(qs)) if f_with[i] and not f_wo[i])
            broken = sum(1 for i in range(len(qs)) if f_wo[i] and not f_with[i])
            print('  「%s」 %s→%s：基线 %d → 加入后 %d → 修好 %d、弄坏 %d、净 %+d'
                  % (ch, base_tone(ch), base[ch], n_wo, n_with, fixed, broken, fixed - broken))
        return

    # ---- scan：穷举全部候选（含语料里出现过的每个字 × 每个备选读音）----
    inv = char_index(poems, qs, pids)
    vocab = sorted(inv)
    print('\n语料涉及的不同汉字：%d 个；逐字穷举（只重算受影响的题）……' % len(vocab))
    gains = []
    for ch in vocab:
        cur = base.get(ch, base_tone(ch))
        cur_t = int(str(cur)[-1]) if str(cur)[-1].isdigit() else 0
        cur_ze = 1 if cur_t in (3, 4) else 0
        qi = sorted(inv[ch])
        for py, t in readings(ch):
            if (1 if t in (3, 4) else 0) == cur_ze:
                continue                      # 不改变平仄归类 → 对计数无影响
            _, fl = score({**base, ch: py}, qi)
            fixed = sum(1 for i in qi if fl[i] and not base_flags[i])
            broken = sum(1 for i in qi if base_flags[i] and not fl[i])
            if fixed - broken > 0:
                gains.append((fixed - broken, ch, py, t, fixed, broken))
    gains.sort(key=lambda x: -x[0])
    print('净增益 > 0 的候选：%d 项' % len(gains))
    for net, ch, py, t, fixed, broken in gains:
        print('  「%s」-> %s(%d)  净 %+d（修好 %d、弄坏 %d）%s'
              % (ch, py, t, net, fixed, broken, '  ← 已在交付表' if ch in base else ''))
    if not gains:
        print('  （无——说明交付表在全量口径下已无正收益可言，这是「穷尽」的正面结论）')


if __name__ == '__main__':
    main()
