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


# ==================================================================== P1-5 自动枚举
_SQLCOL = {
    'dynasty': 'p.dynasty', 'author': 'p.author', 'cipai': 'p.cipai',
    'source': 'p.source', 'scene': 'p.scene',
    'han_len': 'p.han_len', 'sent_n': 'p.sent_n', 'ze_ratio': 'p.ze_ratio',
    'change': 'p.change', 'abs_change': 'ABS(p.change)', 'threshold': 'p.threshold',
    'longest_len': 'p.longest_len', 'longest_seq': 'p.longest_seq',
    'f_ratio': 'p.f_ratio', 'b_ratio': 'p.b_ratio',
}
_NUM_FIELDS = ('han_len', 'sent_n', 'ze_ratio', 'change', 'abs_change', 'threshold',
               'longest_len', 'longest_seq', 'f_ratio', 'b_ratio')
_EXPR = {'abs_change': 'ABS(change)'}      # 取中位值时的表达式（不带表别名）


def _lit(x):
    if isinstance(x, str):
        return "'" + x.replace("'", "''") + "'"
    return str(x)


def _lit_list(vs):
    return ','.join(_lit(x) for x in vs)


def _pick(conn, field, skip=None):
    """取一个**真实存在**的取值（挑中频，避免"全库"或"空集"两种无信息档位）。"""
    if field in ('dynasty', 'author', 'cipai', 'source', 'scene'):
        return conn.execute('SELECT %s FROM poems WHERE %s IS NOT NULL %s'
                            'GROUP BY %s ORDER BY COUNT(*) DESC LIMIT 1'
                            % (field, field, ("AND %s != %s " % (field, _lit(skip)))
                               if skip is not None else '', field)).fetchone()[0]
    if field == 'title':
        return conn.execute('SELECT title FROM poems WHERE title IS NOT NULL '
                            'AND length(title) > 2 GROUP BY title '
                            'ORDER BY COUNT(*) DESC LIMIT 1').fetchone()[0]
    if field == 'pid':
        return [r[0] for r in conn.execute('SELECT pid FROM poems LIMIT 2')]
    if field in _NUM_FIELDS:
        e = _EXPR.get(field, field)
        n = conn.execute('SELECT COUNT(*) FROM poems WHERE %s IS NOT NULL' % e).fetchone()[0]
        return conn.execute('SELECT %s FROM poems WHERE %s IS NOT NULL '
                            'ORDER BY %s LIMIT 1 OFFSET ?' % (e, e, e), (n // 2,)).fetchone()[0]
    if field == 'lines.tail':
        return conn.execute("SELECT tail FROM lines WHERE tail IS NOT NULL AND tail != '' "
                            'GROUP BY tail ORDER BY COUNT(*) DESC LIMIT 1').fetchone()[0]
    if field == 'tail_pz':
        return '仄'
    if field == 'pz':
        return conn.execute('SELECT pz FROM lines WHERE pz IS NOT NULL AND length(pz) >= 5 '
                            'GROUP BY pz ORDER BY COUNT(*) ASC LIMIT 1 OFFSET 20').fetchone()[0]
    if field == 'pz_exact':
        return conn.execute('SELECT pz FROM lines WHERE pz IS NOT NULL AND length(pz) >= 5 '
                            'GROUP BY pz ORDER BY COUNT(*) DESC LIMIT 1 OFFSET 3').fetchone()[0]
    if field == 'lines.text':
        return '月'
    if field == 'tail_each':
        pid = conn.execute('SELECT pid FROM poems ORDER BY sent_n DESC LIMIT 1').fetchone()[0]
        ts = [r[0] for r in conn.execute(
            "SELECT DISTINCT tail FROM lines WHERE pid=? AND tail != '' LIMIT 2", (pid,))]
        return ts or ['愁']
    if field == 'parity':
        return 0
    if field == 'consist':
        return '后段上升'
    return None


def _indep(field, op, v):
    """**独立手写 SQL**（不复用引擎任何辅助函数）——这是对拍的"真值"一侧。"""
    col = _SQLCOL.get(field)
    vs = list(v) if isinstance(v, (list, tuple)) else [v]
    if field in ('dynasty', 'author', 'cipai', 'source', 'scene'):
        return {'=': '%s = %s' % (col, _lit(vs[0])),
                '!=': '%s != %s' % (col, _lit(vs[0])),
                'in': '%s IN (%s)' % (col, _lit_list(vs)),
                'not_in': '%s NOT IN (%s)' % (col, _lit_list(vs))}.get(op)
    if field == 'title':
        if op == '=':
            return 'p.title = %s' % _lit(vs[0])
        if op == '!=':
            return 'p.title != %s' % _lit(vs[0])
        if op == 'in':
            return 'p.title IN (%s)' % _lit_list(vs)
        if op == 'not_in':
            return 'p.title NOT IN (%s)' % _lit_list(vs)
        if op == 'contains':
            return "p.title LIKE '%" + str(vs[0]).replace("'", "''") + "%'"
    if field == 'pid':
        if op == '=':
            return 'p.pid = %s' % _lit(vs[0])
        if op == 'in':
            return 'p.pid IN (%s)' % _lit_list(vs)
    if field in _NUM_FIELDS:
        if op == 'between':
            return '(%s BETWEEN %s AND %s)' % (col, _lit(v[0]), _lit(v[1]))
        return '%s %s %s' % (col, op, _lit(v))
    if field == 'lines.tail':
        inner = 'SELECT pid FROM lines WHERE tail IN (%s)' % _lit_list(vs)
        return ('p.pid NOT IN (' + inner + ')') if op in ('not_in', '!=') \
            else ('p.pid IN (' + inner + ')')
    if field == 'tail_pz':
        inner = 'SELECT pid FROM lines WHERE substr(pz,-1,1) IN (%s)' % _lit_list(vs)
        return ('p.pid NOT IN (' + inner + ')') if op in ('not_in', '!=') \
            else ('p.pid IN (' + inner + ')')
    if field == 'lines.text':
        return "p.pid IN (SELECT pid FROM lines WHERE text LIKE '%" + str(vs[0]) + "%')"
    if field == 'pz':
        pat = str(vs[0]).replace('?', '_').replace('？', '_')
        return "p.pid IN (SELECT pid FROM lines WHERE pz LIKE '%" + pat + "%')"
    if field == 'pz_exact':
        return 'p.pid IN (SELECT pid FROM lines WHERE pz = %s)' % _lit(vs[0])
    if field == 'tail_each':
        return '(' + ' AND '.join('p.pid IN (SELECT pid FROM lines WHERE tail = %s)'
                                  % _lit(x) for x in vs) + ')'
    if field == 'parity':
        return ('p.pid IN (SELECT pid FROM lines WHERE (idx % 2) = ' + _lit(vs[0]) + ')')
    if field == 'consist':
        return {'后段上升': 'p.change < 0', '后段下降': 'p.change > 0'}.get(
            vs[0], 'ABS(p.change) < 1')
    return None


def _auto_enum(conn):
    """遍历 `LEAF_SCHEMA`：**每个字段 × 每个允许算子**各造一组真实取值，与独立 SQL 逐篇对拍。

    同时在每个字段上验证「schema 未允许的算子」必须**被拒**（而不是按别的语义执行）。
    """
    import queryplan as _QP
    all_ops = sorted({o for s in _QP.LEAF_SCHEMA.values() for o in s['ops']})
    n_case, n_live = 0, 0
    for f in sorted(_QP.LEAF_SCHEMA):
        spec = _QP.LEAF_SCHEMA[f]
        if f == 'line_q':
            continue                              # 结构体：取值形态特殊，由上方硬编码用例覆盖
        base = _pick(conn, f)
        if base is None:
            ok('P1-5 自动枚举 %s 有可用取值' % f, False, '取值为 None')
            continue
        for op in spec['ops']:
            # ── 按算子形态造取值 ──
            if op == 'between':
                try:
                    mid = float(base)
                except (TypeError, ValueError):
                    continue
                val = [mid - 2, mid + 2]
            elif op in ('in', 'not_in'):
                if f == 'tail_each' or (isinstance(base, list)):
                    val = list(base)
                else:
                    _b2 = None
                    try:
                        _b2 = _pick(conn, f, skip=base)
                    except Exception:                            # noqa: BLE001
                        _b2 = None
                    val = [base] + ([_b2] if _b2 is not None and _b2 != base else [])
            else:
                val = base[0] if isinstance(base, list) else base
            leaf = {'field': f, 'op': op, 'value': val}
            _want = _indep(f, op, val)
            if _want is None:
                continue
            n_case += 1
            try:
                sql, args = _QP.compile_filters(conn, leaf)
                got = set(_run(conn, sql, args))
            except Exception as e:                               # noqa: BLE001
                ok('P1-5 %s×%s 可编译' % (f, op), False, '编译异常：%r' % e)
                continue
            want = set(_run(conn, _want))
            if want:
                n_live += 1
            ok('P1-5 %s×%s（取值 %s）' % (f, op, str(val)[:40]), got == want,
               '引擎 %d 篇 ／ 独立 SQL %d 篇' % (len(got), len(want)))
        # ── schema 未允许的算子必须被拒 ──
        for bad_op in all_ops:
            if bad_op in spec['ops'] or f == 'line_q':
                continue
            try:
                _QP.compile_filters(conn, {'field': f, 'op': bad_op, 'value': base})
                bad = True
            except ValueError:
                bad = False
            except Exception:                                    # noqa: BLE001
                bad = False
            ok('P1-5 %s×%s（schema 未允许）必须被拒' % (f, bad_op), not bad, '未报错')
    print('  · 自动枚举：比对 %d 组字段×算子（其中 %d 组真值非空，非空转校验）'
          % (n_case, n_live))


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
         "p.title NOT IN ('二月望夜')"),
        ({'field': 'title', 'op': '=', 'value': '浣溪沙'},
         "p.title = '浣溪沙'"),
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

    # ══════════════════════════════════════════════════════════════════════
    # ★ 2026-10-10（《关键核心现状》P1-5）：**自动穷尽 LEAF_SCHEMA 的字段×算子组合**。
    #   改前 → 只有上方硬编码 36 条用例；「36 项全过」只说明这 36 条没问题，
    #     并不能说明「所有允许的 field×op 都语义正确」——`title` 的 `=` 语义错误就没被覆盖。
    #   改后 → 遍历 `LEAF_SCHEMA` 的每个字段、每个允许算子，各造一组真实取值，
    #     用**独立手写 SQL** 复算并逐篇比对；同时把 schema **未允许**的组合验证为"必须被拒"。
    # ══════════════════════════════════════════════════════════════════════
    _auto_enum(conn)

    # ── P0-4：多个数值条件必须**各自绑定**自己的比较语义（不许整句一刀切）──
    _p04_cases = [
        ('字数至少 50 字', [('han_len', '>', 50)], ['>=']),
        ('字数少于 100 字', [('han_len', '<', 100)], ['<']),
        ('字数严格大于 50 字', [('han_len', '>', 50)], ['>']),
        ('字数至少 50 字、同时少于 100 字', [('han_len', '>', 50), ('han_len', '<', 100)],
         ['>=', '<']),
        ('字数不少于 50、仄声比例低于 60%',
         [('han_len', '>', 50), ('ze_ratio', '<', 60)], ['>=', '<']),
    ]
    for q, leaves, want_ops in _p04_cases:
        node = {'and': [{'field': f, 'op': o, 'value': v} for f, o, v in leaves]}
        QP.normalize_ops(node, q)
        got_ops = [c['op'] for c in node['and']]
        ok('P0-4 逐条件绑定「%s」→ %s' % (q, '/'.join(got_ops)), got_ops == want_ops,
           '得到 %s ／ 期望 %s' % (got_ops, want_ops))

    # ── P1-1：显式空条件必须**恒假**（不能静默变成全库）；validate 必须拒 ──
    for f, empty in (('cipai', []), ('cipai', ''), ('cipai', ['']), ('title', ''),
                     ('title', []), ('author', [])):
        _s, _a = QP.compile_filters(conn, {'field': f, 'op': 'in', 'value': empty})
        _n = len(_run(conn, _s, _a))
        ok('P1-1 显式空条件 %s=%r → 恒假（0 篇）' % (f, empty), _n == 0, '得 %d 篇' % _n)
    _emp_probs = QP.validate(dict(QP.empty_plan(),
                                  filters={'field': 'cipai', 'op': '=', 'value': []}), conn)[1]
    ok('P1-1 validate 拒绝显式空值', any('空' in str(x) for x in _emp_probs),
       '问题=%r' % _emp_probs)
    _nul_probs = QP.validate(dict(QP.empty_plan(),
                                  filters={'field': 'cipai', 'op': '='}), conn)[1]
    ok('P1-1 validate 拒绝缺失 value', any('value' in str(x) for x in _nul_probs),
       '问题=%r' % _nul_probs)
    # 反向：`{"and": []}`（合取空集=真元）**必须仍是 1=1**，不许被误判为显式空
    _s2, _a2 = QP.compile_filters(conn, {'and': []})
    ok('P1-1 空 AND（真元）仍为 1=1（未被误伤）', _s2 == '1=1', _s2)

    # ── P1-2：`title` 的 `=` 是**严格等值**，`contains` 才是子串 ──
    _t = conn.execute("SELECT title FROM poems WHERE title IS NOT NULL AND length(title)>2 "
                      "GROUP BY title ORDER BY COUNT(*) DESC LIMIT 1").fetchone()[0]
    _eq = set(_run(conn, *QP.compile_filters(conn, {'field': 'title', 'op': '=', 'value': _t})))
    _ct = set(_run(conn, *QP.compile_filters(conn, {'field': 'title', 'op': 'contains',
                                                   'value': _t})))
    _want_eq = set(_run(conn, "p.title = '%s'" % _t.replace("'", "''")))
    _want_ct = set(_run(conn, "p.title LIKE '%%%s%%'" % _t.replace("'", "''")))
    ok('P1-2 title `=` == 严格等值 SQL', _eq == _want_eq, '%d vs %d' % (len(_eq), len(_want_eq)))
    ok('P1-2 title `contains` == 子串 SQL', _ct == _want_ct,
       '%d vs %d' % (len(_ct), len(_want_ct)))
    ok('P1-2 `=` 严格 ⊂ `contains` 子串（且通常真包含）', _eq < _ct or _eq == _ct,
       '=%d contains=%d' % (len(_eq), len(_ct)))

    print('=' * 64)
    print('字段×算子真值：比对 %d 项，不符 %d 项' % (CMP[0], len(BAD)))
    for b in BAD:
        print('  ✗', b)
    print('结果：%s' % ('PASS' if not BAD and CMP[0] > 0 else 'FAIL'))
    return 0 if (not BAD and CMP[0] > 0) else 1


if __name__ == '__main__':
    sys.exit(main())
