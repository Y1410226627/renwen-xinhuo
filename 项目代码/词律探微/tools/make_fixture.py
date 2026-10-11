# -*- coding: utf-8 -*-
"""make_fixture.py —— 从 corpus.db 派生**小语料 fixture**，供 CI 跑「依赖语料」的门禁。

为什么要它（外部审查 GPT #19 的**替代方案**）：
    CI 不拉 corpus.db（约 160 MB，走 Git LFS），于是 SQL/检索/聚合这些**最关键的回归**
    根本不在 CI 里跑 —— 「Parser 改坏 SQL」这类问题只能在本机发现。
    这里派生一个**几十 KB 的冻结小样本库**（默认 300 篇清词 + 其全部句子 + FTS/倒排），
    随仓库分发，CI 用它对「检索 ↔ 独立 SQL」做端到端一致性门禁。

用法：
    python tools/make_fixture.py                 # 生成 tests/fixture/corpus_mini.db
    python tools/make_fixture.py --n 500 --dynasty 宋
"""
import argparse
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'corpus.db')
OUT = os.path.join(ROOT, 'tests', 'fixture', 'corpus_mini.db')


def _fts_names(src):
    """FTS5 虚表及其**影子表**的名字（这些必须跳过：内容由 'rebuild' 重建，不能整表照抄）。"""
    names = set()
    for (name, sql) in src.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"):
        low = (sql or '').lower()
        if 'fts5' in low or 'virtual' in low:
            names.add(name)
    shadow = set()
    for n in names:
        shadow |= {n + '_data', n + '_idx', n + '_docsize', n + '_config',
                   n + '_content', n + '_segments', n + '_segdir'}
    return names | shadow


def _tables_with_pid(src, skip=()):
    """列出所有含 `pid` 列的表（poems/lines/派生表…），用于按 pid 抽子集。"""
    out = []
    for (name,) in src.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        if name in skip:
            continue
        try:
            cols = [r[1] for r in src.execute('PRAGMA table_info("%s")' % name)]
        except Exception:                                        # noqa: BLE001
            continue
        if 'pid' in cols:
            out.append((name, cols))
    return out


def main():
    ap = argparse.ArgumentParser(description='派生出用于 CI 的小语料 fixture')
    ap.add_argument('--src', default=SRC)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--n', type=int, default=300)
    ap.add_argument('--dynasty', default='清')
    a = ap.parse_args()

    if not os.path.exists(a.src):
        print('✗ 源库不存在：%s（先跑 build_corpus.py）' % a.src)
        return 1
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    if os.path.exists(a.out):
        os.remove(a.out)

    src = sqlite3.connect(a.src)
    pids = [r[0] for r in src.execute(
        'SELECT pid FROM poems WHERE dynasty=? ORDER BY pid LIMIT ?', (a.dynasty, a.n))]
    if not pids:
        print('✗ 源库里没有朝代「%s」的作品' % a.dynasty)
        return 1

    out = sqlite3.connect(a.out)
    _skip = _fts_names(src)
    # ★ 2026-10-11（审查·低）：改前这里 `except Exception: pass`——
    #   建表/拷数据失败**一声不响**，CI 拿到一份**缺表**的 fixture 却照样「通过」，
    #   于是「门禁绿」其实什么都没验到。现在把失败**收集起来**，末尾统一报并令其失败。
    failures = []

    def _try(what, fn):
        """执行并在失败时**记录**（不静默）；返回是否成功。"""
        try:
            fn()
            return True
        except Exception as exc:                                 # noqa: BLE001
            failures.append('%s 失败：%s: %s' % (what, type(exc).__name__, exc))
            return False

    # ① 结构：照抄全部 CREATE（表/索引/触发器）
    #   跳过三类「本来就不该由我们建」的对象，否则会被记成失败而误报：
    #     · `sqlite_*`（`sqlite_stat1` 等保留给内部使用，建了必然报 reserved）；
    #     · FTS5 的**影子表**（`*_data/_idx/_docsize/...`）——它们由 `CREATE VIRTUAL TABLE`
    #       自动创建，再照抄一次必然 `already exists`。
    for _typ, _name, sql in src.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL"):
        #   注意：**FTS 主表本身仍要建**（只是它的影子表不建）。
        if str(_name).startswith('sqlite_') or (
                _name in _skip and 'fts5' not in (sql or '').lower()):
            continue
        _try('建结构 %s' % _name, (lambda _s=sql: out.execute(_s)))
    # ② 数据：按 pid 抽子集
    ph = ','.join('?' * len(pids))
    copied = {}
    for name, cols in _tables_with_pid(src, _skip):
        _rows = []
        _try('读源表 %s' % name,
             (lambda _n=name: _rows.extend(
                 src.execute('SELECT * FROM "%s" WHERE pid IN (%s)' % (_n, ph), pids).fetchall())))
        if not _rows:
            continue
        _try('写子集 %s' % name,
             (lambda _n=name, _c=cols: out.executemany(
                 'INSERT INTO "%s" VALUES (%s)' % (_n, ','.join('?' * len(_c))), _rows)))
        copied[name] = len(_rows)
    # ③ 非 pid 的小表（authors / cipai 之类）整体照抄，保持实体校验可用
    for (name,) in src.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        if name in copied or name in _skip or any(name == n for n, _c in _tables_with_pid(src, _skip)):
            continue
        _cols, _rows2 = [], []
        _try('读小表 %s' % name, (lambda _n=name: _cols.extend(
            [r[1] for r in src.execute('PRAGMA table_info("%s")' % _n)])))
        _try('读小表数据 %s' % name,
             (lambda _n=name: _rows2.extend(src.execute('SELECT * FROM "%s"' % _n).fetchall())))
        if _rows2 and _cols:
            _try('写小表 %s' % name,
                 (lambda _n=name, _c=list(_cols): out.executemany(
                     'INSERT INTO "%s" VALUES (%s)' % (_n, ','.join('?' * len(_c))), _rows2)))
            copied[name] = len(_rows2)
    # ④ 重建 FTS / 倒排索引（外部内容表用 'rebuild' 指令）
    rebuilt = []
    for (name, sql) in src.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table' AND sql LIKE '%fts5%'"):
        # contentless（`content=''`）的 fts5 **不支持** 'rebuild'——这不是失败，是它本就如此。
        if re.search(r"content\s*=\s*''", sql or ''):
            continue
        if _try('重建 FTS %s' % name,
                (lambda _n=name: out.execute(
                    'INSERT INTO "%s"("%s") VALUES(%s)' % (_n, _n, "'rebuild'")))):
            rebuilt.append(name)
    out.commit()
    src.close()

    # ⑤ 收尾自检：**核心表必须在、且必须有行**——否则这份 fixture 是废的，必须让 CI 红。
    missing = []
    for t in ('poems', 'lines'):
        try:
            n = out.execute('SELECT COUNT(1) FROM "%s"' % t).fetchone()[0]
        except Exception as exc:                                 # noqa: BLE001
            missing.append('%s（查不到：%s）' % (t, exc))
            continue
        if not n:
            missing.append('%s（0 行）' % t)
    out.close()

    if failures:
        print('✗ 生成过程有 %d 处失败（fixture 可能不完整）：' % len(failures))
        for f in failures[:20]:
            print('   · %s' % f)
    if missing:
        print('✗ fixture 缺核心数据：%s' % '；'.join(missing))
    if failures or missing:
        return 1

    print('✅ 已生成 %s' % os.path.relpath(a.out, ROOT))
    print('   朝代=%s 篇数=%d ｜ 表：%s ｜ 重建索引：%s'
          % (a.dynasty, len(pids), copied, rebuilt or '（无）'))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
