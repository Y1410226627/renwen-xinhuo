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
    # ① 结构：照抄全部 CREATE（表/索引/触发器）
    for _typ, _name, sql in src.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL"):
        try:
            out.execute(sql)
        except Exception:                                        # noqa: BLE001
            pass
    # ② 数据：按 pid 抽子集
    ph = ','.join('?' * len(pids))
    copied = {}
    for name, cols in _tables_with_pid(src, _skip):
        try:
            rows = src.execute('SELECT * FROM "%s" WHERE pid IN (%s)' % (name, ph), pids).fetchall()
        except Exception:                                        # noqa: BLE001
            continue
        if not rows:
            continue
        out.executemany('INSERT INTO "%s" VALUES (%s)' % (name, ','.join('?' * len(cols))), rows)
        copied[name] = len(rows)
    # ③ 非 pid 的小表（authors / cipai 之类）整体照抄，保持实体校验可用
    for (name,) in src.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        if name in copied or name in _skip or any(name == n for n, _c in _tables_with_pid(src, _skip)):
            continue
        try:
            cols = [r[1] for r in src.execute('PRAGMA table_info("%s")' % name)]
            rows = src.execute('SELECT * FROM "%s"' % name).fetchall()
            if rows and cols:
                out.executemany('INSERT INTO "%s" VALUES (%s)' % (name, ','.join('?' * len(cols))), rows)
                copied[name] = len(rows)
        except Exception:                                        # noqa: BLE001
            pass
    # ④ 重建 FTS / 倒排索引（外部内容表用 'rebuild' 指令）
    rebuilt = []
    for (name, sql) in src.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table' AND sql LIKE '%fts5%'"):
        try:
            out.execute('INSERT INTO "%s"("%s") VALUES(%s)' % (name, name, "'rebuild'"))
            rebuilt.append(name)
        except Exception:                                        # noqa: BLE001
            pass
    out.commit()
    out.close()
    src.close()

    print('✅ 已生成 %s' % os.path.relpath(a.out, ROOT))
    print('   朝代=%s 篇数=%d ｜ 表：%s ｜ 重建索引：%s'
          % (a.dynasty, len(pids), copied, rebuilt or '（无）'))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
