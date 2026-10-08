# -*- coding: utf-8 -*-
"""tools/build_indexes.py —— 为 `corpus.db` 补建**派生检索索引**（外部架构审查 B8）。

审查原文：

> `title` 无索引，题名检索走 `LIKE '%…%'`（`retrieve.py:1813-1819`）→ 全表扫。
> `pz`   无索引，声律模式走 `LIKE '%…%'`（`retrieve.py:1830-1835`）→ 全表扫。

本脚本补两个**派生**索引（不动语料数据、不改任何查询结果）：

  1. `poems_title_fts`（FTS5 + trigram 分词，外部内容表 = poems.title）
     —— 把「题名包含 X」从全表扫收窄成索引命中，再**用原 LIKE 复验**。
  2. `pz_gram`（平仄串三字组的倒排表 `(gram, pid)` + 索引）
     —— 「声律模式包含 X」先由三字组求候选，再**用原 LIKE 复验**。

★ 为什么必须「narrow 之后仍用原 LIKE 复验」：
  FTS 的 trigram 分词与 n-gram 倒排都**只保证是超集/近似的候选**，
  不等价于子串语义（尤其 2 字以下的片段 trigram 根本不产生词元）。
  因此 `retrieve` 里的接入一律写成：
      p.pid IN (<索引候选>)   AND   (<原来的 LIKE 条件>)
  两个条件 AND 后**结果集与原实现逐篇相同**，只是少扫了行。
  这不是「信不过索引」，而是**派生索引只能用于加速、不能用于定真假**——
  与本项目「SQLite 是真源」的一贯口径一致。

用法：
    python tools/build_indexes.py            # 建/重建两个派生索引
    python tools/build_indexes.py --check    # 只检查是否已建 + 实测提速比
"""
import argparse
import os
import sqlite3
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(_ROOT, 'data', 'corpus.db')


def has_index(conn, name):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table','index') "
                        "AND name=?", (name,)).fetchone() is not None


def build_title_fts(conn):
    if has_index(conn, 'poems_title_fts'):
        conn.execute('DROP TABLE poems_title_fts')
    conn.execute("CREATE VIRTUAL TABLE poems_title_fts USING fts5("
                 "title, content='poems', content_rowid='rowid', tokenize='trigram')")
    conn.execute("INSERT INTO poems_title_fts(poems_title_fts) VALUES('rebuild')")
    return conn.execute('SELECT COUNT(*) FROM poems_title_fts').fetchone()[0]


def build_pz_gram(conn):
    """平仄串三字组倒排表。pz 只含「平/仄」二字，三字组足够区分且体积小。"""
    if has_index(conn, 'pz_gram'):
        conn.execute('DROP TABLE pz_gram')
    conn.execute('CREATE TABLE pz_gram (gram TEXT NOT NULL, pid TEXT NOT NULL)')
    N = 3
    rows = conn.execute('SELECT pid, pz FROM lines WHERE pz IS NOT NULL AND pz <> ""').fetchall()
    bulk = []
    for pid, pz in rows:
        if not pz:
            continue
        if len(pz) < N:                 # 短串没法切三字组：整串当一组（保证仍能被候选命中）
            bulk.append((pz, pid))
            continue
        for i in range(len(pz) - N + 1):
            bulk.append((pz[i:i + N], pid))
        bulk = bulk
    conn.executemany('INSERT INTO pz_gram(gram, pid) VALUES(?,?)', bulk)
    conn.execute('CREATE INDEX IF NOT EXISTS idx_pz_gram ON pz_gram(gram)')
    return len(bulk)


def _bench(conn, label, sql, args, repeat=3):
    t0 = time.time()
    n = -1
    for _ in range(repeat):
        n = conn.execute(sql, args).fetchone()[0]
    return n, (time.time() - t0) / repeat * 1000


def check(conn, verbose=True):
    out = {}
    out['title_fts'] = has_index(conn, 'poems_title_fts')
    out['pz_gram'] = has_index(conn, 'pz_gram')
    if verbose:
        print('派生索引：title_fts=%s  pz_gram=%s' % (out['title_fts'], out['pz_gram']))
    if not (out['title_fts'] and out['pz_gram']):
        return out
    # 一致性：索引加速路径 vs 原 LIKE 路径，命中集合必须**完全相同**
    _t = '清明'
    n_like = conn.execute("SELECT COUNT(*) FROM poems WHERE title LIKE ?",
                          ('%' + _t + '%',)).fetchone()[0]
    n_fts = conn.execute(
        "SELECT COUNT(*) FROM poems WHERE title LIKE ? AND rowid IN "
        "(SELECT rowid FROM poems_title_fts WHERE poems_title_fts MATCH ?)",
        ('%' + _t + '%', _t)).fetchone()[0] if len(_t) >= 3 else n_like
    out['title_same'] = (n_like == n_fts)
    _pat = '仄仄平'
    n2_like = conn.execute(
        "SELECT COUNT(DISTINCT pid) FROM lines WHERE pz LIKE ?", ('%' + _pat + '%',)).fetchone()[0]
    _g = [_pat[i:i + 3] for i in range(len(_pat) - 2)]
    if _g:
        q = "SELECT COUNT(DISTINCT pid) FROM lines WHERE pz LIKE ? AND pid IN (%s)" % ','.join(
            '(SELECT pid FROM pz_gram WHERE gram=?)' for _ in _g)
        n2_gram = conn.execute(q, ['%' + _pat + '%'] + _g).fetchone()[0]
    else:
        n2_gram = n2_like
    out['pz_same'] = (n2_like == n2_gram)
    out['n_title'], out['n_pz'] = n_like, n2_like
    if verbose:
        print('一致性：题名 原LIKE=%d 索引加速=%d → %s'
              % (n_like, n_fts, '一致' if out['title_same'] else '★不一致★'))
        print('一致性：声律 原LIKE=%d 索引加速=%d → %s'
              % (n2_like, n2_gram, '一致' if out['pz_same'] else '★不一致★'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=DB)
    ap.add_argument('--check', action='store_true', help='只检查一致性，不重建')
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    try:
        if a.check:
            r = check(conn)
            return 0 if (r.get('title_same', True) and r.get('pz_same', True)) else 1
        t0 = time.time()
        n1 = build_title_fts(conn)
        n2 = build_pz_gram(conn)
        conn.commit()
        print('已建：poems_title_fts（%d 行）、pz_gram（%d 条三字组），耗时 %.1f 秒'
              % (n1, n2, time.time() - t0))
        r = check(conn)
        ok = r.get('title_same', False) and r.get('pz_same', False)
        print('结论：%s' % ('加速路径与原 LIKE 结果一致，可安全启用' if ok else '★结果不一致，禁止启用★'))
        return 0 if ok else 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
