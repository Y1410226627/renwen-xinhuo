# -*- coding: utf-8 -*-
"""import_batch.py —— 批量导入（功能 13）：manifest + 哈希 + 批次对账 + 幂等回滚。

用法（项目根目录下）：
    python tools/import_batch.py --file 待导入.jsonl --tag 初录 [--why 说明]
    python tools/import_batch.py --file a.jsonl --file b.jsonl --tag 二批
    python tools/import_batch.py --dry-run --file 待导入.jsonl --tag 试算   # 只体检，不写库
    python tools/import_batch.py --list            # 批次对账
    python tools/import_batch.py --rollback 3 --why 录错了

输入文件为 **JSONL**（每行一个 JSON 对象，UTF-8；字段同 `personal_works`：
`title`/`content` 必填，`author`/`cipai`/`source`/`source_locator` 可选）。

红线（交接提示词功能 13）：**绝不改动** `data/corpus.db` 的既有 58,852 篇——
本工具只写**研究库**（`data/research.db`）。重复导入不产生重复行（行级唯一键）。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import research as RS                                          # noqa: E402


def load_jsonl(path):
    rows = []
    with open(path, encoding='utf-8-sig') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError as e:
                raise SystemExit('✗ %s 第 %d 行不是合法 JSON：%s' % (path, i, e))
            rows.append(obj)
    return rows


def main():
    ap = argparse.ArgumentParser(description='批量导入（功能 13）')
    ap.add_argument('--file', action='append', default=[], help='JSONL 文件（可多次）')
    ap.add_argument('--tag', default='', help='批次名')
    ap.add_argument('--db', default=None, help='研究库路径（默认 data/research.db）')
    ap.add_argument('--dry-run', action='store_true', help='只体检不写库')
    ap.add_argument('--list', action='store_true', help='列出批次与对账')
    ap.add_argument('--rollback', type=int, default=None, help='回滚指定批次 id')
    ap.add_argument('--why', default='', help='备注/回滚说明')
    a = ap.parse_args()

    dbp = a.db or RS.DEFAULT_PATH
    if a.list:
        conn = RS.connect(dbp)
        batches = RS.list_import_batches(conn)
        if not batches:
            print('（还没有任何导入批次）')
        for b in batches:
            print('#%d  %s  [%s]  承诺 %d 行 / 现存 %d 行 / 作品 %d 篇 ｜ %s' % (
                b['id'], b['tag'], b['status'], b['n_rows'], b['rows_now'], b['works_now'],
                b['created_at']))
        return 0
    if a.rollback is not None:
        conn = RS.connect(dbp)
        r = RS.rollback_import_batch(conn, a.rollback, why=a.why)
        print('回滚 #%d：撤下 %d 行、%d 篇作品（批次状态 = %s）' % (
            r['batch_id'], r['removed_rows'], r['removed_works'], r['status']))
        return 0
    if not a.file:
        raise SystemExit('用法：--file xx.jsonl --tag 批次名（或 --list / --rollback N）')
    if not a.tag:
        raise SystemExit('--tag（批次名）为必填')
    files = []
    for p in a.file:
        if not os.path.isfile(p):
            raise SystemExit('✗ 找不到文件：%s' % p)
        files.append({'name': os.path.basename(p), 'rows': load_jsonl(p)})

    if a.dry_run:
        meta = [(f['name'], RS.content_sha('\n'.join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) for r in f['rows'])),
                 len(f['rows'])) for f in files]
        print('体检（未写库）：')
        for name, fsha, n in meta:
            print('  %s：%d 行，内容 sha=%s' % (name, n, fsha))
        print('  清单哈希 manifest_sha =', RS._manifest_sha(meta))
        if os.path.exists(dbp):
            conn = RS.connect(dbp)
            for f in files:
                dup = 0
                for r in f['rows']:
                    if conn.execute('SELECT 1 FROM import_rows WHERE file=? AND row_key=?',
                                    (f['name'], RS._row_sha(r))).fetchone():
                        dup += 1
                print('  与库内比对：%s 已存在 %d / %d 行' % (f['name'], dup, len(f['rows'])))
        return 0

    conn = RS.connect(dbp)
    res = RS.import_rows(conn, a.tag, files, note=a.why)
    if res.get('already'):
        print('= 同内容批次已导入过（manifest %s），本次零新增。' % res['manifest_sha'])
    else:
        print('✓ 批次 #%d 导入完成：新增 %d 行、跳过 %d 行（manifest %s）' % (
            res['batch_id'], res['inserted'], res['skipped'], res['manifest_sha']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
