# -*- coding: utf-8 -*-
"""merge_shards.py —— 把 gen_q1000.py 的多个分片合并成最终 1000 题。

分片并行时，组合空间被切片成互不相交的子集，所以**签名天然不重复**；
但分片内只做了**片内**的相似度过滤，跨片仍可能撞车，所以这里再跑一遍**全局**过滤：

  1. 按 `sig` 去重（不同片拿了同一个组合是不可能的，但保险起见）；
  2. 全局相似度过滤（字符二元组 Jaccard ≥ --max-sim 即弃）+ 句首 4 字封顶；
  3. 按 `sig` 稳定排序后裁到 `--n` 条，重编 id。

用法：python tools/merge_shards.py --glob "_shard*.jsonl" --n 1000 --out data/questions_1000.jsonl
"""
import argparse
import glob
import json
import os
import random
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLITE_RE = re.compile(r'(麻烦|请帮我|帮我|我想找|劳驾|请问|问一下|查一下|想看看|请统计|给我个结果|帮我算算)')


def norm_key(q):
    return POLITE_RE.sub('', re.sub(r'[\s，。？、（）()「」“”%？＝*｜]', '', q))


def bigr(q):
    s = norm_key(q)
    return set(s[i:i + 2] for i in range(len(s) - 1))


def jac(a, b):
    i = len(a & b)
    return (i / len(a | b)) if i else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glob', default=os.path.join(ROOT, '_shard*.jsonl'))
    ap.add_argument('--n', type=int, default=1000)
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', 'questions_1000.jsonl'))
    ap.add_argument('--max-sim', type=float, default=0.80)
    ap.add_argument('--max-prefix', type=int, default=3)
    args = ap.parse_args()

    files = sorted(glob.glob(args.glob))
    assert files, '找不到分片文件：%s' % args.glob
    rows, seen_sig, seen_nk = [], set(), set()
    for fp in files:
        for line in open(fp, encoding='utf-8'):
            r = json.loads(line)
            if r['sig'] in seen_sig:
                continue
            nk = norm_key(r['q'])
            if nk in seen_nk:
                continue
            r['_nk'] = nk
            r['_bg'] = bigr(r['q'])
            r['_src'] = os.path.basename(fp)
            seen_sig.add(r['sig'])
            seen_nk.add(nk)
            rows.append(r)
    total_in = len(rows)

    # 稳定排序：先按 OUT、再按 sig，保证可复现
    rows.sort(key=lambda r: (r['sig'].split('｜')[4], r['sig']))
    kept, bags, pref = [], [], Counter()
    for r in rows:
        if any(jac(r['_bg'], b) >= args.max_sim for b in bags):
            continue
        if pref[r['_nk'][:4]] >= args.max_prefix:
            continue
        pref[r['_nk'][:4]] += 1
        bags.append(r['_bg'])
        kept.append(r)

    if len(kept) > args.n:
        kept = kept[:args.n]
    # ⚠ 交错排序：按 OUT 轮转，避免人工翻页时连着看到几十道同一输出算子的题
    #   （按 OUT 连续排列会让"链唯一"的一批题**看起来**同质）
    buckets = {}
    for r in kept:
        buckets.setdefault(r['sig'].split('｜')[4], []).append(r)
    order = sorted(buckets, key=lambda k: -len(buckets[k]))
    for k in order:                     # 桶内确定性打乱：否则各桶第 0 条都是同一个 LQ｜LP
        random.Random(20261003).shuffle(buckets[k])
    kept = []
    i = 0
    while len(kept) < sum(len(v) for v in buckets.values()):
        for k in order:
            if i < len(buckets[k]):
                kept.append(buckets[k][i])
        i += 1
    for i, r in enumerate(kept):
        r['id'] = 'Q%04d' % (i + 1)
        for k in ('_nk', '_bg', '_src'):
            r.pop(k, None)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    sigs = [r['sig'] for r in kept]
    print('分片文件 %d 个；去重后 %d 条；全局过滤后 %d 条 → 写出 %d 条'
          % (len(files), total_in, len(kept), len(sigs)))
    print('  **链（签名）唯一：%d 个签名 / %d 题**' % (len(set(sigs)), len(sigs)))
    print('  来源分片：%s' % dict(Counter(r.get('ability', 'supported') for r in kept)))
    for k, c in Counter(s.split('｜')[4] for s in sigs).most_common():
        print('   OUT=%-8s %d' % (k, c))
    if len(kept) < args.n:
        print('  ⚠ 不足 %d 条：需要补跑更多分片或放宽过滤' % args.n)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
