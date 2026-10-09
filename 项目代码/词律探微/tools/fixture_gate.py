# -*- coding: utf-8 -*-
"""fixture_gate.py —— 在小语料 fixture 上跑**检索 ↔ 独立 SQL** 端到端一致性门禁。

对应外部审查 GPT #19 的替代方案：CI 不拉 160 MB 语料，但**必须**能挡住
「Parser 改坏 SQL / 布尔树编译错 / 句级算子写反」这类回归。这里用 `tests/fixture/corpus_mini.db`
（由 make_fixture.py 派生，随仓库分发）做不依赖大语料的端到端验证。

用法：python tools/fixture_gate.py    （退出码 0=全绿）
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))

DB = os.path.join(ROOT, 'tests', 'fixture', 'corpus_mini.db')


def main():
    if not os.path.exists(DB):
        print('SKIP 缺 %s（先跑 python tools/make_fixture.py）' % os.path.relpath(DB, ROOT))
        return 0
    import retrieve as RT
    import queryplan as QP
    conn = sqlite3.connect(DB)
    n_ok = n_all = 0

    def chk(name, got, want):
        nonlocal n_ok, n_all
        n_all += 1
        ok = (got == want)
        n_ok += 1 if ok else 0
        print('%s %-42s 得到 %r ／ 期望 %r' % ('✓' if ok else '✗', name, got, want))

    n_poems = conn.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
    print('fixture：%d 篇' % n_poems)

    # ① 规则路「计数」== 独立 SQL
    q = '清 句脚是「愁」的词'
    spec = RT.parse_query(conn, q)
    got = RT.count_hits(conn, spec)
    want = conn.execute("SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND "
                        "p.pid IN (SELECT pid FROM lines WHERE tail='愁')").fetchone()[0]
    chk('① 规则路计数 == 独立 SQL', got, want)

    # ② 布尔树：OR / NOT 编译 == 独立 SQL
    node = {'and': [{'or': [{'field': 'dynasty', 'op': 'in', 'value': ['清']},
                            {'field': 'dynasty', 'op': 'in', 'value': ['宋']}]},
                    {'field': 'cipai', 'op': 'in', 'value': ['临江仙']}]}
    s, a = QP.compile_filters(conn, node)
    got = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % s, a).fetchone()[0]
    want = conn.execute("SELECT COUNT(*) FROM poems WHERE cipai='临江仙'").fetchone()[0]
    chk('② 跨值 OR == 独立 SQL', got, want)

    node = {'and': [{'field': 'dynasty', 'op': 'in', 'value': ['清']},
                    {'not': {'field': 'cipai', 'op': 'in', 'value': ['临江仙']}}]}
    s, a = QP.compile_filters(conn, node)
    got = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % s, a).fetchone()[0]
    want = conn.execute("SELECT COUNT(*) FROM poems WHERE dynasty='清' AND cipai!='临江仙'"
                        ).fetchone()[0]
    chk('③ NOT == 独立 SQL', got, want)

    # ③ 句级量化 line_q（∄ 句脚为仄）== 独立 SQL
    node = {'and': [{'field': 'dynasty', 'op': 'in', 'value': ['清']},
                    {'field': 'line_q', 'op': '=',
                     'value': {'op': '∄', 'pred': ['tail_pz', '仄']}}]}
    s, a = QP.compile_filters(conn, node)
    got = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % s, a).fetchone()[0]
    want = conn.execute("SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND "
                        "p.pid NOT IN (SELECT pid FROM lines WHERE substr(pz,-1,1)='仄')"
                        ).fetchone()[0]
    chk('④ 句级量化(∄) == 独立 SQL', got, want)

    # ④ 计划往返（to_plan → from_plan）计数不变
    spec2 = RT.parse_query(conn, '清 临江仙')
    pl = QP.to_plan(spec2)
    spec3 = QP.from_plan(pl, conn)
    chk('⑤ 计划往返计数一致', RT.count_hits(conn, spec2), RT.count_hits(conn, spec3))

    # ⑤ 无效实体 → 结果集为空（绝不退化成全库）
    import planner as PL
    bad = {('author', '查无此人')}
    fixed = PL._mark_not_found({'field': 'author', 'op': 'in', 'value': ['查无此人']}, bad)
    s, a = QP.compile_filters(conn, fixed)
    chk('⑥ 无效实体 → 0 篇（非全库）',
        conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % s, a).fetchone()[0], 0)

    conn.close()
    print('\n小结：%d / %d 项一致' % (n_ok, n_all))
    return 0 if n_ok == n_all else 1


if __name__ == '__main__':
    sys.exit(main())
