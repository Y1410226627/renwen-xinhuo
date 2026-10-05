# -*- coding: utf-8 -*-
"""corpus_manifest.py —— **语料来源 manifest 冻结校验**（借自朋友项目的双哈希纪律）。

由来（2026-10-05，朋友项目对照）：
    我们的 `solve/corpus.py` 用**路径分量精确匹配**来隔离「清词」与「清诗」
    （`source/词/清` vs `source/诗/清`）。路径匹配的弱点：**改名/挪目录即失效**，
    而失效是**静默的**——清诗混进清词，数字看起来依旧「像对的」。
    朋友的 `source_import.py` 用**文件字节哈希 + git blob 双重冻结**：
    哈希不会因改名而失效。

本工具做**只读**的三件事，**不改 `corpus.py`、不改建库输出**（因此零回归安全）：
  1) `--write`：把「按现有 loader 口径实读的文件清单」写成 manifest
     （相对路径 + SHA256 + 反序列化后的**条目数** + 全库篇数）；
  2) `--verify`：把当前磁盘上的文件与 manifest 逐项比对，报**缺失/多出/哈希变/条数变**；
  3) 默认（都不给）：打印清单摘要（不落盘）。

条目数用**反序列化后的 len**（而非文件字节）——因为字节哈希只能证明「文件没变」，
条数能进一步证明「loader 读到的内容没变」。

用法：
  python tools/corpus_manifest.py --corpus <语料根> --write solve/data/corpus_manifest.json
  python tools/corpus_manifest.py --corpus <语料根> --verify solve/data/corpus_manifest.json
"""
from __future__ import annotations
import argparse
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

from corpus import _load                                    # noqa: E402


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest().upper()


def _sources(root):
    """**与 solve/corpus.py 的 loader 同源**的「会读哪些文件」清单（只读，不复制加载逻辑）。

    ⚠ 这里的 glob 必须**逐条对应** corpus.py 里的 loader，否则 manifest 会「看着对、其实漏读」。
    每条：(相对路径, 该文件的 loader 口径标签)
    """
    out = []
    # load_qing：poetry-source 的 source/词/清/*.base.json（**只清**，绝不含诗）
    base = os.path.join(root, 'poetry-source-master', 'source', '词', '清')
    if os.path.isdir(base):
        for f in sorted(glob.glob(os.path.join(base, '*.base.json'))):
            out.append(f)
    # load_song：chinese-poetry 的 宋词/ci.song.*.json
    d = os.path.join(root, 'chinese-poetry-master', '宋词')
    if os.path.isdir(d):
        for f in sorted(glob.glob(os.path.join(d, 'ci.song.*.json'))):
            out.append(f)
    # load_yuanqu：chinese-poetry 的 元曲/yuanqu.json
    p = os.path.join(root, 'chinese-poetry-master', '元曲', 'yuanqu.json')
    if os.path.isfile(p):
        out.append(p)
    return out


def build(root):
    root = os.path.abspath(root)
    items, total = [], 0
    for f in _sources(root):
        try:
            n = len(_load(f))
        except Exception as exc:                   # 读不了也要如实记（不静默丢）
            n = None
            sys.stderr.write('（读取失败，仍登记：%s：%s）\n' % (os.path.relpath(f, root), exc))
        items.append({'path': os.path.relpath(f, root).replace('\\', '/'),
                      'sha256': _sha256(f), 'count': n})
        if n:
            total += n
    return {'root': root, 'files': len(items), 'entries_total': total, 'items': items}


def verify(root, manifest_path):
    man = json.load(open(manifest_path, encoding='utf-8'))
    root = os.path.abspath(root)
    old = {it['path']: it for it in man['items']}
    cur = {it['path']: it for it in build(root)['items']}
    bad = []
    for p in sorted(set(old) | set(cur)):
        a, b = old.get(p), cur.get(p)
        if a and not b:
            bad.append('缺失：%s（语料被移走/改名？）' % p)
        elif b and not a:
            bad.append('多出：%s（manifest 之外的文件被读入！）' % p)
        elif a['sha256'] != b['sha256']:
            bad.append('哈希变：%s（%s → %s）' % (p, a['sha256'][:12], b['sha256'][:12]))
        elif a.get('count') != b.get('count'):
            bad.append('条数变：%s（%s → %s）' % (p, a.get('count'), b.get('count')))
    return bad


def main():
    ap = argparse.ArgumentParser(description='语料来源 manifest 冻结校验（只读）')
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--write', metavar='MANIFEST')
    ap.add_argument('--verify', metavar='MANIFEST')
    args = ap.parse_args()

    if args.write:
        m = build(args.corpus)
        os.makedirs(os.path.dirname(os.path.abspath(args.write)), exist_ok=True)
        json.dump(m, open(args.write, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('清单已写入：%s（文件 %d，条目 %d，根 %s）'
              % (args.write, m['files'], m['entries_total'], m['root']))
        return 0
    if args.verify:
        bad = verify(args.corpus, args.verify)
        if bad:
            print('❌ manifest 校验未过（%d 项）：' % len(bad))
            for b in bad:
                print('   ' + b)
            return 1
        print('✅ manifest 校验通过：磁盘文件与冻结清单逐项一致（哈希 + 条数）')
        return 0
    m = build(args.corpus)
    print('文件 %d 个，条目合计 %d，根 %s' % (m['files'], m['entries_total'], m['root']))
    for it in m['items'][:5]:
        print('  %s  %s  n=%s' % (it['sha256'][:12], it['path'], it['count']))
    if len(m['items']) > 5:
        print('  …（共 %d）' % len(m['items']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
