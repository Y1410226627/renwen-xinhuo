# -*- coding: utf-8 -*-
"""snapshot_answers.py —— **答案产物版本化 + 逐版差异**（借自朋友项目的 Analysis/Revision 纪律）。

由来（2026-10-05，朋友项目对照）：
    朋友用 `AnalysisRevision` / `DecisionEvent` 做到「**每轮留快照、可回看任意历史版**」。
    反观我们：`tools/loop_check.py` 有「代码树冻结」与「两遍逐字节一致」，但
    **答案产物本身没有版本化**——改一版引擎重跑，旧答案就没了。
    第 13 轮那个回归，是**跑 100 遍自检偶然抓到**的；若有逐版快照，就能像
    `git bisect` 一样**直接定位是哪一版引入的**。

本工具做**只读 + 追加写快照目录**：
  · `--snapshot <answers.jsonl>`：把某份答案按「内容哈希」归档到 `snapshots/`，
    哈希已存在则不重复（幂等）；并登记一行 `index.jsonl`（时间、哈希、条数、来源、标签）；
  · `--diff <A.jsonl> <B.jsonl>`：按**题号**逐条比对，输出**新增/删除/改动**题号清单，
    并对改动题给出**字段级**差异（甲/乙/答案/errors/路径）；退出码 1 表示「有差异」。
  · `--list`：列出已归档快照（哈希 + 标签 + 条数）。

⚠ 与门禁的关系：本工具**不参与** `regress.py` 的期望哈希，是**旁路留痕**，
   因此**零回归安全**（不入 solver）。

用法：
  python tools/snapshot_answers.py --snapshot answers_700.jsonl --tag 公开-v1
  python tools/snapshot_answers.py --diff snapshots/<旧>.jsonl snapshots/<新>.jsonl
  python tools/snapshot_answers.py --list
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SNAP = os.path.join(ROOT, 'snapshots')


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest().upper()


def _load(path):
    out = {}
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            it = json.loads(line)
            key = it.get('题号') or it.get('id') or it.get('qid')
            out[key] = it
    return out


def snapshot(path, tag=''):
    os.makedirs(SNAP, exist_ok=True)
    h = _sha(path)
    dest = os.path.join(SNAP, '%s.jsonl' % h[:16])
    idx = os.path.join(SNAP, 'index.jsonl')
    already = os.path.isfile(dest)
    if not already:
        with open(path, 'rb') as fsrc, open(dest, 'wb') as fdst:
            fdst.write(fsrc.read())
    else:
        # 同哈希但文件名不同？也照样登记（只是不重复存文件）
        pass
    try:
        n = len(_load(path))
    except Exception:
        n = None
    if not already:
        with open(idx, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
                                'sha256_16': h[:16], 'n': n, 'tag': tag,
                                'src': os.path.relpath(path, ROOT)}, ensure_ascii=False) + '\n')
    print('%s %s（%s，n=%s，标签=%s）'
          % ('归档' if not already else '已存在（幂等，不重复）', h[:16],
             os.path.relpath(path, ROOT), n, tag or '-'))
    return 0


def diff(pa, pb):
    a, b = _load(pa), _load(pb)
    only_a = [k for k in a if k not in b]
    only_b = [k for k in b if k not in a]
    changed = []
    for k in a:
        if k in b and a[k] != b[k]:
            fields = [f for f in set(a[k]) | set(b[k])
                      if a[k].get(f) != b[k].get(f)]
            changed.append((k, sorted(fields)))
    print('A=%s（%d 题）  B=%s（%d 题）' % (os.path.basename(pa), len(a),
                                          os.path.basename(pb), len(b)))
    if only_a:
        print('仅在 A（%d）：%s' % (len(only_a), '、'.join(only_a[:20])))
    if only_b:
        print('仅在 B（%d）：%s' % (len(only_b), '、'.join(only_b[:20])))
    if changed:
        print('改动（%d）：' % len(changed))
        for k, fs in changed[:50]:
            print('  %s  →  字段：%s' % (k, '、'.join(fs)))
    if not (only_a or only_b or changed):
        print('✅ 两份答案逐条**完全相同**')
        return 0
    return 1


def listing():
    idx = os.path.join(SNAP, 'index.jsonl')
    if not os.path.isfile(idx):
        print('（尚无快照索引 %s）' % os.path.relpath(idx, ROOT))
        return 0
    for line in open(idx, encoding='utf-8'):
        line = line.strip()
        if line:
            d = json.loads(line)
            print('%s  %s  n=%-5s  %s' % (d['ts'], d['sha256_16'], d['n'], d.get('tag') or '-'))
    return 0


def main():
    ap = argparse.ArgumentParser(description='答案产物版本化 + 逐版差异（只读/追加）')
    ap.add_argument('--snapshot', metavar='ANSWERS')
    ap.add_argument('--tag', default='')
    ap.add_argument('--diff', nargs=2, metavar=('A', 'B'))
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()
    if args.list:
        return listing()
    if args.diff:
        return diff(*args.diff)
    if args.snapshot:
        return snapshot(args.snapshot, args.tag)
    ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
