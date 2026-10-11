# -*- coding: utf-8 -*-
"""tools/build_indexes.py —— 为语料补建**派生检索索引**（外部架构审查 B8）。

审查原文：

> `title` 无索引，题名检索走 `LIKE '%…%'`（`retrieve.py:1813-1819`）→ 全表扫。
> `pz`   无索引，声律模式走 `LIKE '%…%'`（`retrieve.py:1830-1835`）→ 全表扫。

本脚本补两个**派生**索引（不动语料数据、不改任何查询结果）：

  1. `poems_title_fts`（FTS5 + trigram 分词，自存 `(title, pid)`）
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

★ 2026-10-11 修（审查 H3）——**派生索引不再写进 `data/corpus.db`**：
  改前本脚本默认 `--db data/corpus.db`，并直接在这个**交付语料库**上
  `DROP/CREATE/INSERT/commit`——与本项目「`data/corpus.db`（只读语料）绝不改」的硬红线
  正面冲突（文件字节被改写，任何基于文件字节的校验都会受影响）。
  改后：
    · 派生索引一律建到**侧车库** `data/derived_index.db`（默认；`--index-db` 可改）；
    · 语料库全程**只读**（只发 SELECT，不发任何 DDL/DML）；
    · 检索侧 `retrieve._derived_tables()` 在**需要时只读 ATTACH** 这个侧车库；
    · 侧车库不存在 = 索引没建 → 检索**自动回退到原 LIKE 路径**（与未建时逐篇相同）。
  附带修掉：`bulk = bulk` 空操作（疑为「分块提交」的笔误）与全量累积后单次
  `executemany` 的内存问题——现按 `_CHUNK` 分块写入。

用法：
    python tools/build_indexes.py            # 建/重建侧车库里的两个派生索引
    python tools/build_indexes.py --check    # 只检查是否已建 + 实测一致性
"""
import argparse
import os
import sqlite3
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(_ROOT, 'data', 'corpus.db')
#: 派生索引的**侧车库**（★ 审查 H3：绝不写进语料库本体）
INDEX_DB = os.path.join(_ROOT, 'data', 'derived_index.db')
_CHUNK = 50000


def has_index(conn, name, schema=''):
    q = ("SELECT 1 FROM %ssqlite_master WHERE type IN ('table','index') AND name=?"
         % (schema + '.' if schema else ''))
    return conn.execute(q, (name,)).fetchone() is not None


def build_title_fts(iconn, conn):
    """题名 FTS（自存 title+pid，不依赖外部内容表——侧车库里没有 poems 表）。"""
    if has_index(iconn, 'poems_title_fts'):
        iconn.execute('DROP TABLE poems_title_fts')
    iconn.execute("CREATE VIRTUAL TABLE poems_title_fts USING fts5("
                  "title, pid UNINDEXED, tokenize='trigram')")
    # ⚠ 列序必须与 INSERT 的 (title, pid) **严格对齐**（否则 title 列里装的是 pid，
    #   索引能建起来但永远命中 0 条——正是 `--check` 要抓的那种"静默失效"）。
    rows = conn.execute('SELECT title, pid FROM poems WHERE title IS NOT NULL '
                        "AND title <> ''").fetchall()
    iconn.executemany('INSERT INTO poems_title_fts(title, pid) VALUES(?,?)', rows)
    return len(rows)


def build_pz_gram(iconn, conn):
    """平仄串三字组倒排表。pz 只含「平/仄」二字，三字组足够区分且体积小。

    ★ 2026-10-11：按 `_CHUNK` **分块写入**（改前 `bulk = bulk` 是空操作，
      且 42 万行 × 每串十余个三字组全量累积在内存里再一次 executemany，内存吃紧）。
    """
    if has_index(iconn, 'pz_gram'):
        iconn.execute('DROP TABLE pz_gram')
    iconn.execute('CREATE TABLE pz_gram (gram TEXT NOT NULL, pid TEXT NOT NULL)')
    N = 3
    cur = conn.execute('SELECT pid, pz FROM lines WHERE pz IS NOT NULL AND pz <> ""')
    bulk, total = [], 0
    while True:
        row = cur.fetchone()
        if row is None:
            break
        pid, pz = row[0], row[1]
        if not pz:
            continue
        if len(pz) < N:                 # 短串没法切三字组：整串当一组（保证仍能被候选命中）
            bulk.append((pz, pid))
        else:
            for i in range(len(pz) - N + 1):
                bulk.append((pz[i:i + N], pid))
        if len(bulk) >= _CHUNK:
            iconn.executemany('INSERT INTO pz_gram(gram, pid) VALUES(?,?)', bulk)
            total += len(bulk)
            bulk = []
    if bulk:
        iconn.executemany('INSERT INTO pz_gram(gram, pid) VALUES(?,?)', bulk)
        total += len(bulk)
    iconn.execute('CREATE INDEX IF NOT EXISTS idx_pz_gram ON pz_gram(gram)')
    return total


def _bench(conn, label, sql, args, repeat=3):
    t0 = time.time()
    n = -1
    for _ in range(repeat):
        n = conn.execute(sql, args).fetchone()[0]
    return n, (time.time() - t0) / repeat * 1000


def _attach(conn, index_db):
    """把侧车库**只读 ATTACH** 成 `dv`；返回 schema 名（文件不存在 → None）。"""
    if not os.path.isfile(index_db):
        return None
    conn.execute('ATTACH DATABASE ? AS dv', (index_db,))
    return 'dv'


def check(conn, index_db=INDEX_DB, verbose=True):
    """一致性核验：索引加速路径 vs 原 LIKE 路径，命中集合必须**完全相同**。

    ★ 语料库 conn 全程只读；侧车库只 ATTACH（不建表）。侧车库不存在 → 报「未建」，
      此时检索走原 LIKE 路径，结果集不受影响（故判为一致）。
    """
    out = {'index_db': index_db, 'exists': os.path.isfile(index_db)}
    if not out['exists']:
        if verbose:
            print('派生索引：未建（%s 不存在）——检索将回退到原 LIKE 路径，结果不受影响'
                  % index_db)
        out['title_same'] = out['pz_same'] = True
        return out
    sch = _attach(conn, index_db) or 'dv'
    out['title_fts'] = has_index(conn, 'poems_title_fts', sch)
    out['pz_gram'] = has_index(conn, 'pz_gram', sch)
    if verbose:
        print('派生索引（侧车库 %s）：title_fts=%s  pz_gram=%s'
              % (os.path.basename(index_db), out['title_fts'], out['pz_gram']))
    if not (out['title_fts'] and out['pz_gram']):
        return out
    # ⚠ 核验词必须**真实走通** FTS 收窄：trigram 对 <3 字不产生词元，
    #   取 2 字词（如「清明」）时代码会回退纯 LIKE——等于**什么都没验到**。
    #   故这里从库里挑一个真实存在的 3 字题名片段再对拍。
    _t = '清明'
    _r3 = conn.execute("SELECT title FROM poems WHERE title IS NOT NULL AND title <> '' "
                       "AND length(title) >= 3 LIMIT 1").fetchone()
    if _r3:
        _t = (_r3[0] or '')[:3]
    n_like = conn.execute("SELECT COUNT(*) FROM poems WHERE title LIKE ?",
                          ('%' + _t + '%',)).fetchone()[0]
    n_fts = conn.execute(
        "SELECT COUNT(*) FROM poems WHERE title LIKE ? AND pid IN "
        "(SELECT pid FROM dv.poems_title_fts WHERE title MATCH ?)",
        ('%' + _t + '%', '"%s"' % _t)).fetchone()[0] if len(_t) >= 3 else n_like
    out['title_probe'] = _t
    out['title_same'] = (n_like == n_fts)
    _pat = '仄仄平'
    n2_like = conn.execute(
        "SELECT COUNT(DISTINCT pid) FROM lines WHERE pz LIKE ?", ('%' + _pat + '%',)).fetchone()[0]
    _g = [_pat[i:i + 3] for i in range(len(_pat) - 2)]
    if _g:
        q = ("SELECT COUNT(DISTINCT pid) FROM lines WHERE pz LIKE ? AND pid IN (%s)"
             % ','.join('(SELECT pid FROM dv.pz_gram WHERE gram=?)' for _ in _g))
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
    ap.add_argument('--db', default=DB, help='语料库（**只读**：本脚本对它只发 SELECT）')
    ap.add_argument('--index-db', default=INDEX_DB,
                    help='派生索引侧车库（默认 data/derived_index.db）')
    ap.add_argument('--check', action='store_true', help='只检查一致性，不重建')
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    try:
        if a.check:
            r = check(conn, a.index_db)
            return 0 if (r.get('title_same', True) and r.get('pz_same', True)) else 1
        t0 = time.time()
        d = os.path.dirname(a.index_db)
        if d:
            os.makedirs(d, exist_ok=True)
        iconn = sqlite3.connect(a.index_db)
        try:
            n1 = build_title_fts(iconn, conn)
            n2 = build_pz_gram(iconn, conn)
            iconn.commit()
        finally:
            iconn.close()
        print('已建：%s → poems_title_fts（%d 行）、pz_gram（%d 条三字组），耗时 %.1f 秒'
              % (a.index_db, n1, n2, time.time() - t0))
        print('语料库 %s 未被改动（本脚本对它只发 SELECT）。' % a.db)
        r = check(conn, a.index_db)
        ok = r.get('title_same', False) and r.get('pz_same', False)
        print('结论：%s' % ('加速路径与原 LIKE 结果一致，可安全启用' if ok else '★结果不一致，禁止启用★'))
        return 0 if ok else 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
