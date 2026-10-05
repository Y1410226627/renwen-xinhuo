# -*- coding: utf-8 -*-
"""sample_check.py —— T2 泛化自查：对**全库随机抽样**复算，验证题目之外的泛化能力。

为什么需要它（2026-09-30 采纳，来自第六份外部交付的启发）：
「1000 题满分」只证明在这些抽样题上口径对了；要用在全库任意一首词上，
必须证明**题目之外**也不出洋相（异常、空结果、越界、定位失败）。

判据：
  * 随机抽样（固定种子，可复现）里 异常 0、空结果 0、指标无越界、
    「自题自解定位（corpus→locator 内部一致性）」失败 0
  * 抽样输出连跑两遍**逐字节一致**（确定性）
  * 覆盖度披露：词人数、含缺字占位符 □○■ 的篇、含 CJK 扩展 A 字的篇、长调（≥90 汉字）篇
  * `--manual` 导出前 20 首的**逐字平仄表**（CSV），供人工核查（评审可当场抽查）

指标释义（重要，避免误读）：
  本脚本第 115 行用「作者 + 词牌 + 正文前 8 字」**直接**调用 `locate_one`，验证的是
  **corpus → locator** 这条内部链路的一致性（给定语料字段能否回查到自己），
  据此命名的指标是「**自题自解定位（corpus→locator 内部一致性）**」。
  它**不等价于**用户自然语言查询的鲁棒性——那条链是 **自然语言 → parser → locator**，
  涉及分词/消歧/同名词牌等，本脚本不覆盖，不能据此宣称「用户随便问都能定位」。

用法：
  python tools/sample_check.py --corpus <语料根> --out t2_抽样_2000首.jsonl --n 2000 \
      --manual t2_人工核查_20首.csv
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOLVE = os.path.join(os.path.dirname(HERE), 'solve')
sys.path.insert(0, SOLVE)

from corpus import load_corpus, locate_one, HAN_RE            # noqa: E402
from pronounce import Pronouncer, default_overrides_path     # noqa: E402
from prosody import Engine                                   # noqa: E402


def measure(eng, raw):
    """对一篇原文跑全套指标（与五类题的字段一一对应，便于逐字段核对）。"""
    sents = Engine.split(raw)
    pzs = [eng.p.ping_ze(s) for s in sents]
    allpz = ''.join(pzs)
    cut = len(sents) // 2
    a, b = ''.join(pzs[:cut]), ''.join(pzs[cut:])
    r = eng.ratio(raw)
    h = eng.halves(raw)
    l = eng.longest(raw)
    d = eng.long_density(raw)
    s = eng.scene_emotion(raw)
    return {
        '句数': len(sents), '平': r['平'], '仄': r['仄'], '仄声比例': r['仄声比例'],
        '最长句序': l['最长句序'], '最长句字数': l['最长句字数'],
        '前段字': len(a), '前段平': a.count('平'), '前段仄': a.count('仄'), '前段比例': h['前段比例'],
        '后段字': len(b), '后段平': b.count('平'), '后段仄': b.count('仄'), '后段比例': h['后段比例'],
        '变化': h['变化'], '绝对变幅': h['绝对变幅'],
        'C3阈值': d['阈值'], 'C3入选句序': d['入选句序'], 'C3比例': d['比例'],
        'C4后段引文': quote_of(sents, cut, 'c4'),
        'C5前段引文': quote_of(sents, cut, 'c5-front'),
        'C5后段引文': quote_of(sents, cut, 'c5-back'),
        'C5转向': s['转向'],
        '总字': len(allpz),
    }


def quote_of(sents, cut, which):
    """按引擎口径取引文：C4 取后段末句，C5 前/后段各取末句（_quote 原样返回）。"""
    from prosody import _quote
    if which == 'c4':
        seg = sents[cut:]
    elif which == 'c5-front':
        seg = sents[:cut]
    else:
        seg = sents[cut:]
    seg = seg or (sents or [''])
    return _quote(seg[-1])


def main():
    ap = argparse.ArgumentParser(description='T2 泛化自查（全库随机抽样复算）')
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=20260929)
    ap.add_argument('--manual', default='', help='可选：逐字平仄人工核查表（CSV，前 20 首）')
    ap.add_argument('--dyn', default='清', help='抽样朝代（默认清词）')
    args = ap.parse_args()

    poems = load_corpus(args.corpus)
    pool = [p for p in poems if p.dynasty == args.dyn]
    print('全库 %d 首；其中「%s」%d 首' % (len(poems), args.dyn, len(pool)))
    ext = [p for p in pool if any(HAN_RE.match(c) and not ('\u4e00' <= c <= '\u9fff') for c in p.raw)]
    ph = [p for p in pool if any(c in p.raw for c in '□○■')]
    lng = [p for p in pool if len(p.han) >= 90]
    print('  含缺字占位符 □○■ 的 %d 首；含 CJK 扩展 A 字的 %d 首；长调（≥90 汉字）%d 首'
          % (len(ph), len(ext), len(lng)))

    rng = random.Random(args.seed)
    sample = rng.sample(pool, min(args.n, len(pool)))
    eng = Engine(Pronouncer(default_overrides_path()))

    rows, nerr, nzero, nloc = [], 0, 0, 0
    for p in sample:
        try:
            rec = measure(eng, p.raw)
        except Exception as exc:                       # 异常必须显式上报，不得静默
            nerr += 1
            rows.append({'pid': p.pid, '异常': '%s: %s' % (type(exc).__name__, exc)})
            continue
        if rec['句数'] <= 0 or rec['平'] + rec['仄'] <= 0:
            nzero += 1
        for k in ('仄声比例', '前段比例', '后段比例', 'C3比例'):
            if not (0.0 <= float(rec[k]) <= 100.0):
                nerr += 1
        if rec['C3阈值'] < 0 or rec['前段字'] <= 0 or rec['后段字'] <= 0:
            nerr += 1
        # 注意：这是「自题自解定位」——直接用该篇自己的字段（作者/词牌/前 8 字）回查，
        # 验证的是 corpus → locator 的内部一致性，**不等价于自然语言查询鲁棒性**。
        hit = locate_one(poems, p.author, p.cipai, p.han[:8], p.dynasty) is not None
        if not hit:
            nloc += 1
        rec.update({'pid': p.pid, '朝代': p.dynasty, '作者': p.author,
                    '题名': p.title, '词牌': p.cipai,
                    '自题自解定位_corpus→locator内部一致性': hit})
        rows.append(rec)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with io.open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        for rec in rows:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n')
    md5 = hashlib.md5(io.open(args.out, 'rb').read()).hexdigest()

    print('\n抽样 %d 首 -> %s' % (len(sample), args.out))
    print('异常 %d；空结果 %d；自题自解定位（corpus→locator 内部一致性）失败 %d；md5=%s'
          % (nerr, nzero, nloc, md5))
    print('　（注：该指标只证明「语料字段能回查到自己」，不等价于用户自然语言查询鲁棒性）')
    print('覆盖：词人 %d 位；含缺字占位符的篇 %d 首；含扩展 A 的篇 %d 首'
          % (len({r.get('作者') for r in rows}),
             sum(1 for p in sample if any(c in p.raw for c in '□○■')),
             sum(1 for p in sample if any(HAN_RE.match(c) and not ('\u4e00' <= c <= '\u9fff')
                                          for c in p.raw))))

    if args.manual:
        by_pid = {p.pid: p for p in sample}
        with io.open(args.manual, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['pid', '作者', '词牌', '句序', '字数', '逐字平仄', '原句'])
            for rec in rows[:20]:
                p = by_pid.get(rec.get('pid'))
                if p is None:
                    continue
                for i, s in enumerate(Engine.split(p.raw), 1):
                    w.writerow([p.pid, p.author, p.cipai, i,
                                len([c for c in s if HAN_RE.match(c)]), eng.p.ping_ze(s), s])
        print('人工核查表已写入：%s' % args.manual)
    return 0


if __name__ == '__main__':
    sys.exit(main())
