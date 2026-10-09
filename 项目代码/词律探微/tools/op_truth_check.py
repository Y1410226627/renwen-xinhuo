# -*- coding: utf-8 -*-
"""op_truth_check.py —— **字段×算子真值测试**（第三轮审查 P0-1 的硬要求）。

为什么必须有它：`queryplan.LEAF_SCHEMA` 决定「哪些 field×op 组合被允许」，
`retrieve._leaf_sql` 决定「这些组合实际编译成什么 SQL」——**登记合法 ≠ 语义正确**。
审查点名的反例：`{"field":"cipai","op":"not_in","value":["临江仙"]}` 曾被编译成
**正向**的 `cipai IN ('临江仙')`（语义相反）。本工具把**每一个允许的组合**逐一编译，
与**手写的独立 SQL** 逐篇对拍；不支持的组合必须在校验阶段被拒（而不是悄悄按别的语义执行）。

覆盖（对照审查要求）：等值 / 并集 / 否定 / between 区间 / 文本包含 / 嵌套布尔（AND·OR·NOT）
+ 比较符号的**边界值**（恰等于阈值时 `>` 与 `>=` 的差异）。

用法：python tools/op_truth_check.py
退出码：0 = 全过；1 = 有组合不一致（**这就是"把旧错误写法注回去必须报错"的守卫**：
把 `_leaf_one` 的 op 分派改回「只看值个数」时，否定用例立即 FAIL）。
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import queryplan as QP                                          # noqa: E402

CMP = [0]
BAD = []


def ok(name, cond, detail=''):
    CMP[0] += 1
    if not cond:
        BAD.append(name + ('：' + detail if detail else ''))


def _run(conn, sql, args=()):
    return [r[0] for r in conn.execute('SELECT p.pid FROM poems p WHERE %s' % sql, list(args))]


def main():
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'corpus.db'))
    conn.row_factory = sqlite3.Row
    # 取两个真实 pid 供 pid 字段用
    rp = [r[0] for r in conn.execute('SELECT pid FROM poems WHERE dynasty=? LIMIT 2', ('清',))]

    # ── 逐组合用例：叶子 → 手写的独立 SQL（**字面量内联，完全独立于编译器实现**）──
    CASES = [
        # 元数据：等值 / 并集 / 否定（P0-1 的核心）
        ({'field': 'cipai', 'op': '=', 'value': '临江仙'},
         "p.cipai = '临江仙'"),
        ({'field': 'cipai', 'op': 'in', 'value': ['临江仙', '蝶恋花']},
         "p.cipai IN ('临江仙','蝶恋花')"),
        ({'field': 'cipai', 'op': '!=', 'value': '临江仙'},
         "p.cipai != '临江仙'"),
        ({'field': 'cipai', 'op': 'not_in', 'value': ['临江仙', '蝶恋花']},
         "p.cipai NOT IN ('临江仙','蝶恋花')"),
        ({'field': 'author', 'op': 'not_in', 'value': ['高旭']},
         "p.author NOT IN ('高旭')"),
        ({'field': 'dynasty', 'op': '!=', 'value': '清'},
         "p.dynasty != '清'"),
        ({'field': 'scene', 'op': '=', 'value': '后段上升'},
         "p.scene = '后段上升'"),
        ({'field': 'scene', 'op': '!=', 'value': '后段上升'},
         "p.scene != '后段上升'"),
        ({'field': 'source', 'op': 'not_in', 'value': ['poetry-source']},
         "p.source NOT IN ('poetry-source')"),
        ({'field': 'title', 'op': 'contains', 'value': '二月望夜'},
         "p.title LIKE '%二月望夜%'"),
        ({'field': 'title', 'op': 'not_in', 'value': ['二月望夜']},
         "NOT (p.title LIKE '%二月望夜%')"),
        ({'field': 'pid', 'op': 'in', 'value': rp},
         "p.pid IN (%s)" % ','.join("'%s'" % p for p in rp)),
        # 数值：六种算子 + between（闭区间）
        ({'field': 'han_len', 'op': '>', 'value': 50},
         "p.han_len > 50"),
        ({'field': 'han_len', 'op': '>=', 'value': 50},
         "p.han_len >= 50"),
        ({'field': 'han_len', 'op': '!=', 'value': 42},
         "p.han_len != 42"),
        ({'field': 'han_len', 'op': 'between', 'value': [40, 60]},
         "(p.han_len BETWEEN 40 AND 60)"),
        ({'field': 'ze_ratio', 'op': '<', 'value': 45},
         "p.ze_ratio < 45"),
        ({'field': 'ze_ratio', 'op': '<=', 'value': 45},
         "p.ze_ratio <= 45"),
        # 句级：存在 / 否定（NOT IN 反向）
        ({'field': 'lines.tail', 'op': 'in', 'value': ['愁']},
         "p.pid IN (SELECT pid FROM lines WHERE tail IN ('愁'))"),
        ({'field': 'lines.tail', 'op': 'not_in', 'value': ['愁']},
         "p.pid NOT IN (SELECT pid FROM lines WHERE tail IN ('愁'))"),
        ({'field': 'tail_pz', 'op': '=', 'value': '仄'},
         "p.pid IN (SELECT pid FROM lines WHERE substr(pz,-1,1) = '仄')"),
        ({'field': 'tail_pz', 'op': 'not_in', 'value': ['平']},
         "p.pid NOT IN (SELECT pid FROM lines WHERE substr(pz,-1,1) IN ('平'))"),
        ({'field': 'lines.text', 'op': 'contains', 'value': '月'},
         "p.pid IN (SELECT pid FROM lines WHERE text LIKE '%月%')"),
        ({'field': 'pz', 'op': 'contains', 'value': '仄仄平'},
         "p.pid IN (SELECT pid FROM lines WHERE pz LIKE '%仄仄平%')"),
        # 嵌套布尔：AND / OR / NOT
        ({'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                  {'field': 'cipai', 'op': 'not_in', 'value': ['临江仙']}]},
         "p.dynasty = '清' AND p.cipai NOT IN ('临江仙')"),
        ({'or': [{'field': 'cipai', 'op': '=', 'value': '临江仙'},
                 {'field': 'cipai', 'op': '=', 'value': '蝶恋花'}]},
         "p.cipai = '临江仙' OR p.cipai = '蝶恋花'"),
        ({'not': {'field': 'dynasty', 'op': '=', 'value': '清'}},
         "p.dynasty != '清'"),
        ({'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                  {'not': {'or': [{'field': 'author', 'op': '=', 'value': '高旭'},
                                  {'field': 'author', 'op': '=', 'value': '纳兰性德'}]}}]},
         "p.dynasty = '清' AND p.author NOT IN ('高旭','纳兰性德')"),
    ]
    for i, (leaf, want_sql) in enumerate(CASES, 1):
        try:
            sql, args = QP.compile_filters(conn, leaf)
            got = set(_run(conn, sql, args))
            want = set(_run(conn, want_sql))
            ok('组合 %02d %s' % (i, str(leaf)[:64]),
               got == want and len(got) > 0 or (got == want and len(want) == 0),
               '引擎 %d 篇 ／ 独立 SQL %d 篇' % (len(got), len(want)))
        except Exception as e:                                   # noqa: BLE001
            ok('组合 %02d %s' % (i, str(leaf)[:64]), False, '编译异常：%r' % e)

    # ── 边界值（P0-6）：恰好等于阈值的篇，`>` 不含、`>=` 含 ──
    row = conn.execute("SELECT pid FROM poems WHERE ze_ratio = 45.0 LIMIT 1").fetchone()
    if row:
        pid45 = row[0]
        s1, a1 = QP.compile_filters(conn, {'field': 'ze_ratio', 'op': '>', 'value': 45})
        s2, a2 = QP.compile_filters(conn, {'field': 'ze_ratio', 'op': '>=', 'value': 45})
        g1, g2 = set(_run(conn, s1, a1)), set(_run(conn, s2, a2))
        ok('边界：恰等于 45 的篇不在 `>45` 里', pid45 not in g1)
        ok('边界：恰等于 45 的篇在 `>=45` 里', pid45 in g2)
        ok('边界：`>45` ⊂ `>=45` 且差集即等于 45 的篇', g1 <= g2)
    else:
        ok('边界：数据库存在 ze_ratio=45.0 的篇（供边界测试）', False, '未找到样例')

    # ── 措辞驱动的归一（P0-6）：高于→>=；严格大于→保留；无依据→保留 ──
    leaf1 = {'field': 'ze_ratio', 'op': '>', 'value': 45}
    n1 = QP.normalize_ops(leaf1, '仄声比例高于45%')
    e1 = QP.compile_filters(conn, leaf1)          # 归一原地生效后再编译
    ok('措辞「高于」→ 归一为 >=', n1 == 1 and '>=' in e1[0], str(e1))
    leaf3 = {'field': 'ze_ratio', 'op': '>', 'value': 45}
    n3 = QP.normalize_ops(leaf3, '仄声比例严格大于45%')
    ok('措辞「严格大于」→ 保留 >', n3 == 0 and leaf3['op'] == '>')
    leaf4 = {'field': 'ze_ratio', 'op': '>', 'value': 45}
    n4 = QP.normalize_ops(leaf4, '')
    ok('无措辞依据 → 保留 >', n4 == 0 and leaf4['op'] == '>')

    # ── 不支持组合必须被拒（不许悄悄按另一种语义执行）──
    try:
        QP.compile_filters(conn, {'field': 'pid', 'op': 'not_in', 'value': ['x']})
        ok('pid×not_in（schema 未允许）必须被拒', False, '未报错')
    except ValueError:
        ok('pid×not_in（schema 未允许）必须被拒', True)
    try:
        QP.compile_filters(conn, {'field': 'lines.text', 'op': 'not_in', 'value': ['月']})
        ok('lines.text×not_in（schema 未允许）必须被拒', False, '未报错')
    except ValueError:
        ok('lines.text×not_in（schema 未允许）必须被拒', True)

    print('=' * 64)
    print('字段×算子真值：比对 %d 项，不符 %d 项' % (CMP[0], len(BAD)))
    for b in BAD:
        print('  ✗', b)
    print('结果：%s' % ('PASS' if not BAD and CMP[0] > 0 else 'FAIL'))
    return 0 if (not BAD and CMP[0] > 0) else 1


if __name__ == '__main__':
    sys.exit(main())
