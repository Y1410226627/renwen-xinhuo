# -*- coding: utf-8 -*-
"""queryplan.py —— Query Plan（**唯一执行真源**）：布尔过滤树 + 多路召回 + 有序步骤。

由来（2026-10-08，两份外部架构审查共同结论）
==========================
`solve/retrieve.py` 的 `QuerySpec` 是一张**平铺槽位表**：字段之间只能 AND、字段内只能
IN 并集——**没有布尔树、没有「步骤」**。于是「（写秋景 或 写离愁）且 不是 临江仙 的清词」
「先取某作者全部作品，再取最长的一首，再取它的第 2 句」这类**复合/多步**问题**结构上无法编码**，
只能退化为「少条件/错条件」→ 召回错误集合 → 答案错。

而 `queryast.py` 里的 AST「**有存在感、没权力**」——只做调试，执行链不经过它。

本模块把它升级为**执行真源**：
    · `compile_filters(conn, node) -> (sql, args)`：布尔树 → SQLite 条件（**递归**，AND/OR/NOT 任意嵌套）；
    · `to_plan(spec)` / `from_plan(plan, conn)`：与旧 `QuerySpec` **双向兼容**（保 1000 题零回归）；
    · `validate(plan, conn)`：计划合法性（节点形状 / op 兼容 / 库中存在性）；
    · `render(plan)`：**逐层可回放**的人类可读文本（排查「哪一层丢了语义」）。

兼容铁律（生命线）
==================
`QuerySpec.filters_tree` 默认 `None`；`retrieve._sql()` 只在它**非空**时才走本模块编译，
否则走原路径**逐字不变** —— 默认环境下 1000 题**零回归**。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import retrieve                                                # noqa: E402

PLAN_VERSION = 1

INTENTS = ('list', 'count', 'extreme', 'aggregate', 'extract', 'pair', 'compare',
           'similarity', 'locate')

# 叶子允许的字段 → (SQL 列表达式, 值形态)
_LEAF_FIELDS = {
    'dynasty':   ('p.dynasty', 'str'),
    'author':    ('p.author', 'str'),
    'cipai':     ('p.cipai', 'str'),
    'title':     ('p.title', 'str'),
    'han_len':   ('p.han_len', 'num'),
    'sent_n':    ('p.sent_n', 'num'),
    'ze_ratio':  ('p.ze_ratio', 'num'),
    'change':    ('p.change', 'num'),
    'longest_len': ('p.longest_len', 'num'),
    'threshold': ('p.threshold', 'num'),
    'lines.text': ('__lines_text__', 'str'),       # 句级存在性（子查询）
    'lines.tail': ('__lines_tail__', 'str'),
    'lines.pz':   ('__lines_pz__', 'str'),
}

_LEAF_OPS = ('=', '!=', 'in', 'not_in', '>', '>=', '<', '<=', 'between', 'contains')


# ------------------------------------------------------------------ 布尔树编译
def _leaf_sql(field, op, value):
    """叶子条件 → (sql 片段, args)。字段/算子不认识时抛 ValueError（上层如实降级）。"""
    col, kind = _LEAF_FIELDS.get(field, (None, None))
    if col is None:
        raise ValueError('未支持的过滤字段：%s' % field)
    if op not in _LEAF_OPS:
        raise ValueError('未支持的过滤算子：%s' % op)

    def _like(col_, v):
        return ('%s LIKE ?' % col_), ['%' + str(v).replace('%', '\\%') + '%']

    if field.startswith('lines.'):
        # 句级存在性：p.pid IN (SELECT pid FROM lines WHERE …)
        lcol = {'lines.text': 'text', 'lines.tail': 'tail', 'lines.pz': 'pz'}[field]
        if op in ('=', 'contains'):
            sub, sa = '%s LIKE ?' % lcol, ['%' + str(value) + '%']
        elif op == 'in':
            sub = '%s IN (%s)' % (lcol, ','.join('?' * len(value)))
            sa = [str(x) for x in value]
        elif op == 'not_in':
            sub = ('%s NOT IN (%s)' % (lcol, ','.join('?' * len(value))),)
            sa = [str(x) for x in value]
        elif op == '!=':
            sub, sa = '%s NOT LIKE ?' % lcol, ['%' + str(value) + '%']
        else:
            raise ValueError('句级字段不支持算子 %s' % op)
        return 'p.pid IN (SELECT pid FROM lines WHERE %s)' % sub, sa

    if op == '=':
        return '%s = ?' % col, [str(value) if kind == 'str' else value]
    if op == '!=':
        return '%s != ?' % col, [str(value) if kind == 'str' else value]
    if op == 'in':
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError('in 需要非空列表：%r' % (value,))
        return '%s IN (%s)' % (col, ','.join('?' * len(value))), list(value)
    if op == 'not_in':
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError('not_in 需要非空列表：%r' % (value,))
        return '%s NOT IN (%s)' % (col, ','.join('?' * len(value))), list(value)
    if op in ('>', '>=', '<', '<='):
        return '%s %s ?' % (col, op), [value]
    if op == 'between':
        if not (isinstance(value, (list, tuple)) and len(value) == 2):
            raise ValueError('between 需要 [a,b]：%r' % (value,))
        return '%s BETWEEN ? AND ?' % col, [value[0], value[1]]
    if op == 'contains':
        return _like(col, value)
    raise ValueError('未支持的算子：%s' % op)


def compile_filters(conn, node):
    """布尔树 → (where_sql, args)。

    **委托 `retrieve._sql_filters`**（单一真源，避免两套编译器漂移——那正是外部审查指出的
    「AST 与执行双轨」问题）。本模块持有 Plan 的**结构定义**与 `to_plan/from_plan` 转换；
    编译委托给执行层。委托前做一次**白名单校验**（叶子的字段/算子是否被支持），
    不支持的如实抛 `ValueError`，由上层降级而不是静默丢条件。
    """
    for bad in _unsupported_leaf(node):
        raise ValueError('未支持的过滤字段/算子：%s' % bad)
    return retrieve._sql_filters(conn, node)


def _unsupported_leaf(node, out=None):
    """遍历布尔树，收集「本模块 `_LEAF_FIELDS` 不认识」的叶子（供白名单校验）。"""
    out = [] if out is None else out
    if not isinstance(node, dict) or not node:
        return out
    if 'and' in node or 'or' in node:
        for c in (node.get('and') or node.get('or') or []):
            _unsupported_leaf(c, out)
    elif 'not' in node:
        _unsupported_leaf(node['not'], out)
    elif 'field' in node:
        f, op = node.get('field'), node.get('op')
        if f not in _LEAF_FIELDS or op not in _LEAF_OPS:
            out.append('%s %s' % (f, op))
    return out


# ------------------------------------------------------------------ Plan <-> QuerySpec
def to_plan(spec):
    """QuerySpec → Plan（**无损**；无法映射的进 `_legacy`，不静默丢）。"""
    ast = _ast_of(spec)
    plan = {
        'version': PLAN_VERSION,
        'intent': (ast.get('intent') or {}).get('type', 'list'),
        'scope': {'base': 'corpus', 'ctx': None},
        'filters': {},          # 默认空（= 不过滤）；from_spec 会填
        'retrieve': [],
        'steps': [],
        'operation': None,
        'context': {'refs': [], 'resolve': None},
        'evidence': {'mode': 'rows', 'bind_numbers': True},
        '_legacy': {},
    }
    it = ast.get('intent') or {}
    if it.get('type') == 'extreme':
        plan['operation'] = {'kind': 'extreme', 'target': {
            'metric': it.get('metric'), 'dir': it.get('direction') or 'desc'},
            'label': it.get('label'), 'src': it.get('src'),
            'extreme': it.get('extreme'), 'col': it.get('col')}
    elif it.get('type') in ('agg', 'pair'):
        plan['operation'] = {'kind': it['type'], 'target': it}
    # ★ 把「筛选字段」填进 filters 布尔树（编译器可处理的叶子才放进来；
    #   line_q/tail_each/pz_exact/consist/scene 这类复杂结构仍由 _sql 原路径处理，
    #   通过 `_legacy.keep_legacy_filters` 标记告知 from_plan/_sql 走混合模式）。
    _flt = []
    sc = ast.get('scope') or {}
    # scope 里的四类（to_ast 把朝代/词人/词牌/题名放在 scope，不放 filters）
    for v in (sc.get('dynasty') or []):
        _flt.append({'field': 'dynasty', 'op': '=', 'value': v})
    for v in (sc.get('authors') or []):
        _flt.append({'field': 'author', 'op': '=', 'value': v})
    for v in (sc.get('cipais') or []):
        _flt.append({'field': 'cipai', 'op': '=', 'value': v})
    for v in (sc.get('titles') or []):
        _flt.append({'field': 'title', 'op': 'contains', 'value': v})
    for f in (ast.get('filters') or []):
        if f.get('scope') == 'poem' and f.get('field') in _LEAF_FIELDS:
            _flt.append({'field': f['field'], 'op': f['op'], 'value': f['value']})
        elif f.get('scope') == 'line' and f.get('tag') == 'tail_any':
            _flt.append({'field': 'lines.tail', 'op': 'in',
                         'value': list((f.get('predicate') or {}).get('value') or [])})
        elif f.get('scope') == 'line' and f.get('tag') == 'pz':
            _flt.append({'field': 'lines.pz', 'op': 'contains',
                         'value': (f.get('predicate') or {}).get('value')})
    if len(_flt) > 1:
        plan['filters'] = {'and': _flt}
    elif _flt:
        plan['filters'] = _flt[0]
    _complex = [f for f in (ast.get('filters') or [])
                if f.get('scope') == 'line' and f.get('tag') in ('pz_exact', 'tail_each', 'line_q', 'parity')]
    if _complex:
        plan['_legacy']['keep_legacy_filters'] = True
        plan['_legacy']['legacy_filters'] = _complex
    # 多轮范围：ctx_pids 非空 → scope.base = prev_result（Plan 层表达「那里面」）
    if ast.get('extras', {}).get('ctx_pids'):
        plan['scope'] = {'base': 'prev_result', 'ctx': list(ast['extras']['ctx_pids'])}
    sem = ast.get('semantic') or {}
    terms = list(sem.get('terms') or [])
    if terms:
        plan['retrieve'].append({'mode': 'vector', 'q': ' '.join(terms), 'topk': 50})
    plan['_legacy'] = {
        'semantic_terms': terms,
        'keywords': list(sem.get('keywords') or []),
        'unparsed': list(ast.get('unparsed') or []),
        'source': (ast.get('extras') or {}).get('source'),
        'raw_question': (ast.get('extras') or {}).get('raw_question'),
        'change_abs': (ast.get('extras') or {}).get('change_abs', False),
    }
    return plan


def _ast_of(spec):
    """复用 queryast.to_ast（避免两套表示）。"""
    import queryast as _qa
    return _qa.to_ast(spec)


def spec_to_filters_tree(spec):
    """把 QuerySpec 的**筛选字段**转成布尔树（AND 根；供 `_sql` 消费）。

    只覆盖 `_sql` 已支持的字段；`line_q` 算子等复杂结构**留空**（由 `_sql` 原路径处理，
    见 `filters_tree` 的「混合模式」约定）。
    """
    ands = []
    for v in retrieve._vals(spec, 'dynasty'):
        ands.append({'field': 'dynasty', 'op': '=', 'value': v})
    for v in retrieve._vals(spec, 'author'):
        ands.append({'field': 'author', 'op': '=', 'value': v})
    for v in retrieve._vals(spec, 'cipai'):
        ands.append({'field': 'cipai', 'op': '=', 'value': v})
    for v in retrieve._vals(spec, 'title'):
        ands.append({'field': 'title', 'op': 'contains', 'value': v})
    for k in ('ze_min', 'ze_max', 'len_min', 'len_max', 'sent_min', 'sent_max',
              'change_min', 'change_max', 'thr_min', 'thr_max'):
        if k in (spec.rng or {}):
            f, o = {'ze_min': ('ze_ratio', '>='), 'ze_max': ('ze_ratio', '<='),
                    'len_min': ('han_len', '>='), 'len_max': ('han_len', '<='),
                    'sent_min': ('sent_n', '>='), 'sent_max': ('sent_n', '<='),
                    'change_min': ('change', '>='), 'change_max': ('change', '<='),
                    'thr_min': ('threshold', '>='), 'thr_max': ('threshold', '<=')}[k]
            ands.append({'field': f, 'op': o, 'value': spec.rng[k]})
    if not ands:
        return None
    return {'and': ands} if len(ands) > 1 else ands[0]


def from_plan(plan, conn):
    """Plan → QuerySpec（`to_plan` 的近似逆；供 Plan 驱动的执行）。"""
    spec = retrieve.QuerySpec()
    sc = plan.get('scope') or {}
    if sc.get('base') == 'prev_result':
        spec.ctx_pids = list(sc.get('ctx') or [])
    flt = plan.get('filters') or {}
    if flt:
        spec.filters_tree = flt
    _apply_leaf_tree(spec, flt)
    it = plan.get('operation') or {}
    if it.get('kind') == 'extreme':
        t = it.get('target') or {}
        spec.order_by = t.get('metric')
        spec.order_dir = t.get('dir') or 'desc'
        spec.extreme = it.get('extreme') or ('max' if (t.get('dir') or 'desc') == 'desc' else 'min')
        spec.order_col = it.get('col')
        spec.order_label = it.get('label')
        spec.order_src = it.get('src')
    for k, v in (plan.get('_legacy') or {}).items():
        if k == 'semantic_terms':
            spec.semantic = list(v or [])
        elif k == 'keywords':
            spec.keywords = list(v or [])
        elif k == 'unparsed':
            spec.unparsed = list(v or [])
        else:
            setattr(spec, k, v)
    return retrieve._finalize(spec)


def _apply_leaf_tree(spec, node):
    """把布尔树叶子里**能落到 QuerySpec 槽位**的（朝代/词人/词牌/题名/数值）写回 spec；
    其余叶子（lines.text 等句级存在性）留在 `filters_tree` 交给 `_sql` 直接消费。"""
    if not isinstance(node, dict):
        return
    for key in ('and', 'or'):
        for c in (node.get(key) or []):
            _apply_leaf_tree(spec, c)
    if 'not' in node:
        _apply_leaf_tree(spec, node['not'])
    if 'field' in node:
        f, v = node.get('field'), node.get('value')
        if f == 'dynasty':
            spec.dynasty_any = list(v) if isinstance(v, list) else [v]
        elif f == 'author':
            spec.author_any = list(v) if isinstance(v, list) else [v]
        elif f == 'cipai':
            spec.cipai_any = list(v) if isinstance(v, list) else [v]
        elif f == 'title':
            spec.title_any = list(v) if isinstance(v, list) else [v]
        else:
            # 数值叶子：ze_ratio/han_len/sent_n/change/threshold 的比较算子 → spec.rng
            # （复用 queryast._RNG_REV 的映射；'between' 拆成 min/max 两条）
            import queryast as _qa
            key = _qa._RNG_REV.get((f, node.get('op')))
            if key is not None:
                spec.rng[key] = v


# ------------------------------------------------------------------ 校验与渲染
def validate(plan, conn):
    """Plan 合法性 → (ok, problems)。节点形状 / op 兼容 / 库中存在性。"""
    problems = []
    if plan.get('version') != PLAN_VERSION:
        problems.append('计划版本不支持：%r' % plan.get('version'))
    it = plan.get('intent')
    if it not in INTENTS:
        problems.append('未知意图：%r' % (it,))
    flt = plan.get('filters') or {}
    if flt:
        try:
            compile_filters(conn, flt)
        except ValueError as e:
            problems.append('过滤条件无法编译：%s' % e)
        except Exception as e:                                   # noqa: BLE001
            problems.append('过滤条件编译异常：%s: %s' % (type(e).__name__, e))
    sc = plan.get('scope') or {}
    if sc.get('base') not in ('corpus', 'prev_result'):
        problems.append('未知检索范围：%r' % sc.get('base'))
    return (not problems), problems


def render(plan):
    """Plan → 人类可读多行文本（逐层可回放）。"""
    out = ['Query Plan（v%s）' % plan.get('version')]
    out.append('  意图   : %s' % plan.get('intent'))
    sc = plan.get('scope') or {}
    out.append('  范围   : %s%s' % (sc.get('base'),
                                    ('（%d 篇）' % len(sc.get('ctx') or []))
                                    if sc.get('base') == 'prev_result' else ''))
    flt = plan.get('filters') or {}
    if flt:
        try:
            s, a = compile_filters(None, flt)
            out.append('  过滤树 : %s' % s)
            out.append('           args=%r' % (a,))
        except Exception as e:                                   # noqa: BLE001
            out.append('  过滤树 : （编译失败：%s）' % e)
    else:
        out.append('  过滤树 : （无）')
    ret = plan.get('retrieve') or []
    if ret:
        out.append('  召回   : %s' % '；'.join('%s（q=%r topk=%s）' % (r.get('mode'), r.get('q'), r.get('topk'))
                                              for r in ret))
    ops = plan.get('steps') or []
    if ops:
        out.append('  步骤   : %s' % ' → '.join(str(o.get('op')) for o in ops))
    op = plan.get('operation')
    if op:
        out.append('  运算   : %s %s' % (op.get('kind'), json.dumps(op.get('target') or {}, ensure_ascii=False)))
    lg = plan.get('_legacy') or {}
    if lg:
        out.append('  legacy : %s' % json.dumps({k: lg[k] for k in sorted(lg)}, ensure_ascii=False)[:200])
    return '\n'.join(out)


# ------------------------------------------------------------------ 自检
def selftest(conn):
    """自检：① 布尔树编译与独立 SQL 复算一致；② to_plan/from_plan 往返。"""
    ok_all = True

    # ① 布尔树：三个复合问句，引擎命中数 == 独立 SQL 复算
    cases = [
        # 「清代既非纳兰性德也非朱彝尊的临江仙」
        ({'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                  {'field': 'cipai', 'op': '=', 'value': '临江仙'},
                  {'not': {'or': [{'field': 'author', 'op': '=', 'value': '纳兰性德'},
                                  {'field': 'author', 'op': '=', 'value': '朱彝尊'}]}}]},
         "SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND p.cipai='临江仙' "
         "AND p.author NOT IN ('纳兰性德','朱彝尊')"),
        # 「清代（句中含月 或 含雪）且 字数>50」
        ({'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                  {'or': [{'field': 'lines.text', 'op': 'contains', 'value': '月'},
                          {'field': 'lines.text', 'op': 'contains', 'value': '雪'}]},
                  {'field': 'han_len', 'op': '>', 'value': 50}]},
         "SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND p.han_len>50 AND "
         "(p.pid IN (SELECT pid FROM lines WHERE text LIKE '%月%') OR "
         " p.pid IN (SELECT pid FROM lines WHERE text LIKE '%雪%'))"),
        # 「清 且 不是 临江仙」（NOT 单叶）
        ({'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                  {'not': {'field': 'cipai', 'op': '=', 'value': '临江仙'}}]},
         "SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND p.cipai!='临江仙'"),
    ]
    for i, (node, ref_sql) in enumerate(cases, 1):
        s, a = compile_filters(conn, node)
        n1 = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % s, a).fetchone()[0]
        n2 = conn.execute(ref_sql).fetchone()[0]
        ok = (n1 == n2)
        ok_all = ok_all and ok
        print('%s 用例%d：编译命中 %d == 独立复算 %d   SQL=%s args=%r'
              % ('✓' if ok else '✗', i, n1, n2, s, a))

    # ② to_plan / 往返
    for q in ('清 临江仙 仄声比例高于45%', '哪一首仄声比例最高',
              '蝶恋花·四月一日感粤事是谁写的'):
        spec = retrieve.parse_query(conn, q)
        plan = to_plan(spec)
        spec2 = from_plan(plan, conn)
        ok = (spec.describe() == spec2.describe())
        ok_all = ok_all and ok
        print('%s 往返：%s → %s' % ('✓' if ok else '✗', q[:18], spec2.describe()))
    print('自检：%s' % ('全部通过' if ok_all else '存在失败'))
    return ok_all


def main():
    import argparse
    import sqlite3
    ap = argparse.ArgumentParser(description='Query Plan（执行真源）：自检 / 渲染')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--question', default=None)
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    try:
        if args.question:
            spec = retrieve.parse_query(conn, args.question)
            print(render(to_plan(spec)))
            return 0
        return 0 if selftest(conn) else 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
