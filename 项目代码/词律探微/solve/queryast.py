# -*- coding: utf-8 -*-
"""queryast.py —— 「统一语义中间表示」（AST）+ 可回放调试层（**纯新增**）。

设计意图（定位）
----------------
本模块给「查询理解层」补上一份**稳定的语义中间表示**，把 `retrieve.QuerySpec`
映射成一个**可打印、可校验、可回放**的结构化 dict，并支持反解：

    · `to_ast(spec)`        QuerySpec  → AST（dict）
    · `from_ast(ast, conn)` AST       → QuerySpec（语义等价；用于「改一处条件再执行」与回放）
    · `render_ast(ast)`     人类可读的多行文本（逐层打印，方便排查「到底哪一层丢了语义」）
    · `diff_ast(a, b)`      两个 AST 的差异行（回答「规则路与模型路到底差在哪」）

**本文件不改变任何现有执行路径**：它只**读** QuerySpec、写回一个**等价**的 QuerySpec；
`retrieve` 的执行链（`_sql`/`search`/`count_hits`）与 `ask.answer` 都不经过本模块。

> 目标形态（未来）：`understand` 可**只产出 AST**、检索层**只消费 AST**；
> 规则路与模型路都各自产出 AST，用 `diff_ast` 逐层比对、`render_ast` 逐层打印、
> 用 AST 做「改一处条件再执行」的回放，而不必每来一个新问法就往 `ask.understand`
> 里塞一层例外。当前这一步先把「表示」与「回放」做出来（加法），不动执行路径。

覆盖度约定
----------
`to_ast` 覆盖 QuerySpec 的**全部**字段：有一等语义的进 `scope` / `filters` / `intent` /
`semantic` / `unparsed`；**没有对应概念的**（解析来源、被清掉的组名、原始文本…）一律进
`extras`，并在此函数里逐键注释说明用途——**不许静默丢**（含运行期动态挂上的
`raw_consist` / `semantic` 之类字段，靠 `vars(spec)` 兜底扫描收进 `extras`）。

往返等价
--------
`from_ast(to_ast(spec))` 与原 spec 必须**语义等价**：
    · `describe()` 逐字一致；
    · 对全库 `retrieve.count_hits()` 相同。
自检：`python solve/queryast.py --selftest`（见文件末尾 `selftest()`）。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import retrieve                                                # noqa: E402


# ---- 数值条件：QuerySpec.rng 的键 ↔（篇级字段, 比较运算）----
# 这张表是**唯一真源**：to_ast/from_ast 共用；键序固定，保证 AST 可复现。
_RNG_FIELD = {
    'ze_min': ('ze_ratio', '>='), 'ze_max': ('ze_ratio', '<='),
    'len_min': ('han_len', '>='), 'len_max': ('han_len', '<='),
    'sent_min': ('sent_n', '>='), 'sent_max': ('sent_n', '<='),
    'change_min': ('change', '>='), 'change_max': ('change', '<='),
    'thr_min': ('threshold', '>='), 'thr_max': ('threshold', '<='),
}
_RNG_ORDER = tuple(_RNG_FIELD)                       # 固定顺序（dict 保持插入序）
_RNG_REV = {(f, o): k for k, (f, o) in _RNG_FIELD.items()}

# 句级算子：QuerySpec.line_q['op'] ↔ AST.quantifier
_LQ_OP2AST = {'∃': 'exists', '∀': 'forall', '∄': 'none',
              '≥k': 'count', '=k': 'count', '占比≥p': 'ratio', '条数∈[a,b]': 'range'}


# ---------------------------------------------------------------- 谓词 <-> AST
def _pred_to_ast(kind, val):
    """句级谓词 `(kind, val)` → AST predicate dict（形如 {'field','op','value'}）。"""
    if kind == 'tail':
        return {'field': 'tail', 'op': '=', 'value': val}
    if kind == 'tail_any':
        return {'field': 'tail', 'op': 'in', 'value': list(val)}
    if kind == 'tail_pz':
        return {'field': 'tail_pz', 'op': '=', 'value': val}
    if kind == 'pz':
        return {'field': 'pz', 'op': '=', 'value': val}
    if kind == 'pz_exact':
        return {'field': 'pz_exact', 'op': '=', 'value': val}
    if kind == 'len':
        return {'field': 'len', 'op': 'between', 'value': [val[0], val[1]]}
    if kind == 'parity':
        return {'field': 'parity', 'op': '=', 'value': val}
    return {'field': str(kind), 'op': '?', 'value': val}       # 未知谓词：如实保留（不丢）


def _pred_from_ast(pred):
    """AST predicate dict → 句级谓词 `(kind, val)`（`_pred_to_ast` 的逆）。"""
    f, op, v = pred.get('field'), pred.get('op'), pred.get('value')
    if f == 'tail':
        if op == 'in':
            vv = list(v)
            return ('tail', vv[0]) if len(vv) == 1 else ('tail_any', vv)
        return ('tail', v)
    if f == 'tail_pz':
        return ('tail_pz', v)
    if f == 'pz':
        return ('pz', v)
    if f == 'pz_exact':
        return ('pz_exact', v)
    if f == 'len':
        if op == 'between' and isinstance(v, (list, tuple)) and len(v) == 2:
            return ('len', (v[0], v[1]))
        return ('len', (v, v))
    if f == 'parity':
        return ('parity', v)
    return (f, v)


# ---------------------------------------------------------------- to_ast
def to_ast(spec):
    """QuerySpec → AST（dict）。覆盖全部字段；无一等概念者进 `extras`（不静默丢）。"""
    scope = {
        # 多值字段以 `<attr>_any` 为权威（`retrieve._vals` 是单一来源）；单值快捷字段
        # dynasty/author/cipai/title 由 `_finalize` 派生，故这里只存列表、不重复存单值。
        'dynasty': retrieve._vals(spec, 'dynasty'),
        'authors': retrieve._vals(spec, 'author'),
        'cipais': retrieve._vals(spec, 'cipai'),
        'titles': retrieve._vals(spec, 'title'),
    }
    filters = []

    # ---- 篇级（poem）筛选：声情 / 一致性 / 数值区间 ----
    if spec.scene:
        filters.append({'scope': 'poem', 'field': 'scene', 'op': '=', 'value': spec.scene})
    if getattr(spec, 'consist', None):
        # consist＝「声情标注为 X 但实测前后段相反」——篇级量（比对 p.change 符号）
        filters.append({'scope': 'poem', 'field': 'consist', 'op': '=',
                        'value': spec.consist})
    for key in _RNG_ORDER:
        if key in (spec.rng or {}):
            f, o = _RNG_FIELD[key]
            filters.append({'scope': 'poem', 'field': f, 'op': o, 'value': spec.rng[key]})

    # ---- 行级（line）筛选：句脚字 / 句脚平仄 / 声律模式 / 全等 / 篇内交集 / 句级算子 / 句位 ----
    _tl = retrieve._vals(spec, 'tail')
    if _tl:
        filters.append({'scope': 'line', 'tag': 'tail_any', 'quantifier': 'exists',
                        'predicate': {'field': 'tail', 'op': 'in', 'value': list(_tl)}})
    if spec.tail_pz:
        filters.append({'scope': 'line', 'tag': 'tail_pz', 'quantifier': 'exists',
                        'predicate': {'field': 'tail_pz', 'op': '=', 'value': spec.tail_pz}})
    if spec.pz:
        filters.append({'scope': 'line', 'tag': 'pz', 'quantifier': 'exists',
                        'predicate': {'field': 'pz', 'op': '=', 'value': spec.pz}})
    if spec.pz_exact:
        filters.append({'scope': 'line', 'tag': 'pz_exact', 'quantifier': 'exists',
                        'predicate': {'field': 'pz_exact', 'op': '=', 'value': spec.pz_exact}})
    if getattr(spec, 'tail_each', None):
        # 篇内交集：**每一个**取值都必须各自出现在某一句（与 exists 语义不同）
        filters.append({'scope': 'line', 'tag': 'tail_each', 'quantifier': 'each',
                        'predicate': {'field': 'tail', 'op': 'in',
                                      'value': list(spec.tail_each)}})
    if getattr(spec, 'line_q', None):
        lq = spec.line_q
        node = {'scope': 'line', 'tag': 'line_q',
                'quantifier': _LQ_OP2AST.get(lq.get('op'), lq.get('op')),
                'predicate': _pred_to_ast(*(lq.get('pred') or (None, None)))}
        if lq.get('op') in ('≥k', '=k'):
            node['count'] = {'op': '>=' if lq['op'] == '≥k' else '=', 'value': lq.get('k', 0)}
        elif lq.get('op') == '占比≥p':
            node['ratio'] = lq.get('ratio', 0)
        elif lq.get('op') == '条数∈[a,b]':
            node['range'] = [lq.get('ka', 0), lq.get('kb', 0)]
        filters.append(node)
    if getattr(spec, 'parity', None) is not None:
        # 句位奇偶（独立字段；0=奇数句位 1/3/5…，1=偶数句位）
        filters.append({'scope': 'line', 'tag': 'parity', 'quantifier': 'exists',
                        'predicate': {'field': 'parity', 'op': '=', 'value': spec.parity}})

    # ---- 意图 ----
    if spec.pair:
        intent = {'type': 'pair', 'pair': dict(spec.pair),
                  'label': spec.pair_label}
    elif spec.agg:
        intent = {'type': 'agg', 'agg': dict(spec.agg)}
    elif spec.order_by:
        intent = {'type': 'extreme', 'metric': spec.order_by,
                  'direction': spec.order_dir, 'extreme': spec.extreme,
                  'col': spec.order_col, 'label': spec.order_label, 'src': spec.order_src}
    else:
        intent = {'type': 'list'}

    # ---- 语义/词面检索词（**不进 SQL**，只作检索扩展召回）----
    # terms    ＝ 大模型给的新「语义检索词」（`spec.semantic`；检索层并入全文召回）
    # keywords ＝ 规则/模型给的「词面」检索词（`spec.keywords`，检索层在用）
    semantic = {'terms': list(getattr(spec, 'semantic', None) or []),
                'keywords': list(spec.keywords or []),
                'raw': spec.raw_question or spec.raw or ''}

    # ---- extras：无一等概念的字段（逐键说明，绝不静默丢）----
    extras = {
        'source': spec.source,            # 解析来源（规则/大模型）
        'unsupported': spec.unsupported,  # 语料外朝代等（走拒答）
        'raw': spec.raw,                  # 挖空算子后的**检索工作文本**
        'raw_question': spec.raw_question,  # 用户原话（永不被改写）
        'change_abs': getattr(spec, 'change_abs', False),   # 变化比幅度还是比有符号值
        'cleared_names': list(getattr(spec, 'cleared_names', None) or []),  # 对比题被清掉的组名
        'disp_group': getattr(spec, 'disp_group', None),    # 离散度最大组
        # 「上一轮结果集」范围（ctx_pids）：由前端/会话层传入，**参与 SQL**（硬条件）。
        # 它不属于「一次问句的语义」，故收在 extras（保留以免回放时丢范围）。
        'ctx_pids': list(getattr(spec, 'ctx_pids', None) or []),
    }
    # 兜底扫描：任何**未在上面显式覆盖**的实例属性，一律收进 extras（防未来新增字段被静默丢）
    _covered = {
        'dynasty_any', 'author_any', 'cipai_any', 'title_any', 'tail_any', 'tail_pz', 'pz',
        'scene', 'dynasty', 'author', 'cipai', 'title', 'tail', 'keywords', 'rng',
        'unsupported', 'unparsed', 'agg', 'pair', 'pair_label', 'order_by', 'order_col',
        'order_dir', 'extreme', 'order_label', 'order_src', 'source', 'raw_question', 'raw',
        'line_q', 'tail_each', 'pz_exact', 'parity', 'consist', 'change_abs',
        'cleared_names', 'disp_group', 'semantic',
    }
    for _a in vars(spec):
        if _a not in _covered and _a not in extras:
            extras[_a] = getattr(spec, _a)        # 如运行期挂上的 raw_consist

    return {'scope': scope, 'filters': filters, 'intent': intent,
            'semantic': semantic, 'unparsed': list(spec.unparsed or []), 'extras': extras}


# ---------------------------------------------------------------- from_ast
def _apply_filter(spec, f):
    sc = f.get('scope')
    if sc == 'poem':
        field = f.get('field')
        if field == 'scene':
            spec.scene = f.get('value')
            return
        if field == 'consist':
            spec.consist = f.get('value')
            return
        key = _RNG_REV.get((field, f.get('op')))
        if key is not None:
            spec.rng[key] = f.get('value')
        return
    if sc == 'line':
        tag = f.get('tag')
        if tag == 'tail_any':
            spec.tail_any = list(f['predicate'].get('value') or [])
        elif tag == 'tail_pz':
            spec.tail_pz = f['predicate'].get('value')
        elif tag == 'pz':
            spec.pz = f['predicate'].get('value')
        elif tag == 'pz_exact':
            spec.pz_exact = f['predicate'].get('value')
        elif tag == 'tail_each':
            spec.tail_each = list(f['predicate'].get('value') or [])
        elif tag == 'parity':
            spec.parity = f['predicate'].get('value')
        elif tag == 'line_q':
            lq = {'op': _rget(_LQ_OP2AST, f.get('quantifier')),
                  'pred': _pred_from_ast(f.get('predicate') or {})}
            q = f.get('quantifier')
            if q == 'count':
                c = f.get('count') or {}
                if c.get('op') == '=':
                    lq['op'], lq['k'] = '=k', c.get('value')
                else:
                    lq['op'], lq['k'] = '≥k', c.get('value')
            elif q == 'ratio':
                lq['op'], lq['ratio'] = '占比≥p', f.get('ratio')
            elif q == 'range':
                rng = f.get('range') or [0, 0]
                lq['op'], lq['ka'], lq['kb'] = '条数∈[a,b]', rng[0], rng[1]
            spec.line_q = lq


def _rget(d, v):
    """反查 `_LQ_OP2AST` 的逆（值→键）；找不到原样返回。"""
    for k, vv in d.items():
        if vv == v:
            return k
    return v


def _apply_intent(spec, intent):
    t = intent.get('type')
    if t == 'pair':
        spec.pair = dict(intent.get('pair') or {})
        spec.pair_label = intent.get('label')
    elif t == 'agg':
        spec.agg = dict(intent.get('agg') or {})
    elif t == 'extreme':
        spec.order_by = intent.get('metric')
        spec.order_dir = intent.get('direction') or 'desc'
        spec.extreme = intent.get('extreme')
        spec.order_col = intent.get('col')
        spec.order_label = intent.get('label')
        spec.order_src = intent.get('src')


def from_ast(ast, conn=None):
    """AST → QuerySpec（`to_ast` 的逆；语义等价）。

    `conn` 预留（未来可做「落地校验后再回放」）。当前反解**不重新过滤**——AST 本应由
    `to_ast` 从未经修改的、已落地的 QuerySpec 产出，直接重建即可保证等价。
    """
    spec = retrieve.QuerySpec()
    sc = ast.get('scope') or {}
    spec.dynasty_any = list(sc.get('dynasty') or [])
    spec.author_any = list(sc.get('authors') or [])
    spec.cipai_any = list(sc.get('cipais') or [])
    spec.title_any = list(sc.get('titles') or [])
    for f in (ast.get('filters') or []):
        _apply_filter(spec, f)
    sem = ast.get('semantic') or {}
    spec.keywords = list(sem.get('keywords') or [])
    _terms = list(sem.get('terms') or [])
    if _terms:
        spec.semantic = _terms          # 动态字段（QuerySpec 暂无此槽位；见报告）
    spec.unparsed = list(ast.get('unparsed') or [])
    _apply_intent(spec, ast.get('intent') or {})
    for k, v in (ast.get('extras') or {}).items():
        setattr(spec, k, v)             # 还原 raw_consist / source / change_abs / … 一切 extras
    return retrieve._finalize(spec)


# ---------------------------------------------------------------- render_ast
def render_ast(ast, indent='  '):
    """AST → 人类可读的多行文本（逐层打印，便于排查「哪一层丢了语义」）。"""
    out = ['查询 AST']
    sc = ast.get('scope') or {}
    out.append('%s[scope]' % indent)
    _lbl = {'dynasty': '朝代', 'authors': '词人', 'cipais': '词牌', 'titles': '题名'}
    for k in ('dynasty', 'authors', 'cipais', 'titles'):
        v = sc.get(k) or []
        out.append('%s%s%s: %s' % (indent, indent, _lbl[k], '／'.join(v) if v else '（无）'))
    out.append('%s[filters]' % indent)
    if not ast.get('filters'):
        out.append('%s%s（无）' % (indent, indent))
    for f in (ast.get('filters') or []):
        if f.get('scope') == 'poem':
            out.append('%s%s[篇] %s %s %s' % (indent, indent, f.get('field'),
                                              f.get('op'), f.get('value')))
        else:
            pd = f.get('predicate') or {}
            extra = ''
            if 'count' in f:
                extra = ' 次数%s%s' % (f['count'].get('op'), f['count'].get('value'))
            elif 'ratio' in f:
                extra = ' 占比≥%s' % f['ratio']
            elif 'range' in f:
                extra = ' 句数∈[%s,%s]' % (f['range'][0], f['range'][1])
            out.append('%s%s[句] %s%s 谓词: %s %s %s'
                       % (indent, indent, f.get('quantifier'), extra, pd.get('field'),
                          pd.get('op'), pd.get('value')))
    it = ast.get('intent') or {}
    out.append('%s[intent] %s%s' % (indent, it.get('type'),
                                    (' 指标=%s 方向=%s' % (it.get('metric'), it.get('direction')))
                                    if it.get('type') == 'extreme' else ''))
    sem = ast.get('semantic') or {}
    out.append('%s[semantic] terms=%s' % (indent, sem.get('terms') or []))
    out.append('%s           keywords=%s' % (indent, sem.get('keywords') or []))
    out.append('%s[unparsed] %s' % (indent, '；'.join(ast.get('unparsed') or []) or '（无）'))
    ex = ast.get('extras') or {}
    if ex:
        out.append('%s[extras] %s' % (indent, json.dumps(ex, ensure_ascii=False, sort_keys=True)))
    return '\n'.join(out)


# ---------------------------------------------------------------- diff_ast
def _flatten(node, prefix=''):
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(_flatten(v, '%s.%s' % (prefix, k) if prefix else str(k)))
    elif isinstance(node, list):
        if not node:
            out[prefix] = '[]'
        elif all(not isinstance(x, (dict, list)) for x in node):
            out[prefix] = json.dumps(node, ensure_ascii=False)
        else:
            for i, v in enumerate(node):
                out.update(_flatten(v, '%s[%d]' % (prefix, i)))
    else:
        out[prefix] = json.dumps(node, ensure_ascii=False)
    return out


def diff_ast(a, b, name_a='A', name_b='B'):
    """两个 AST 的差异行（回答「规则路与模型路到底差在哪」）。无差异返回 []。"""
    fa, fb = _flatten(a), _flatten(b)
    lines = []
    for k in sorted(set(fa) | set(fb)):
        va, vb = fa.get(k, '（缺）'), fb.get(k, '（缺）')
        if va != vb:
            lines.append('- %s: %s.%s = %s' % (k, name_a, k, va))
            lines.append('+ %s: %s.%s = %s' % (k, name_b, k, vb))
    return lines


# ---------------------------------------------------------------- 往返自检
_SEED_QUESTIONS = (
    '清 临江仙 仄声比例高于45%',
    '句脚是灯或者声的清词',
    '没有任何一句句脚为愁的清词',
    '有两句以上句脚为愁的清词',
    '正好有两句句脚为愁的清词',
    '每一句都整句平仄串正好是「仄仄平平仄」的清词',
    '且另有至少一句句脚为「上」的清词',
    '奇数句位句脚为愁的清词',
    '声情标注为后段上升但实测前后段相反的清词',
    '后段上升的清词',
    '哪一首仄声比例最高',
    '哪个词人的词最多',
    '找出几对每个位置上的字平仄都相同的两首词',
    '蝶恋花·四月一日感粤事是谁写的',
    '清 五到八句之间 字数不超过五十',
    '句脚为仄的清词',
)


def selftest(conn, verbose=True):
    """往返等价单测：`spec → ast → spec'` 之后 describe() 一致、全库 count_hits 相同。"""
    ok_all = True
    rows = []
    # ① 规则路种子问句（覆盖 scope/filters/intent 的绝大多数形态）
    specs = [(q, retrieve.parse_query(conn, q)) for q in _SEED_QUESTIONS]
    # ② 合成 spec：覆盖规则路**永不产出**的新字段（semantic/ctx_pids）也要能往返
    _syn = retrieve.QuerySpec()
    _syn.dynasty_any = ['清']
    _syn.semantic = ['秋日', '悲秋', '离愁']      # 语义扩展词（不进 SQL）
    _syn.ctx_pids = []                            # 上一轮结果集（空集时不影响结果）
    _syn.keywords = ['写秋愁']
    specs.append(('（合成）清 + 语义扩展词', retrieve._finalize(_syn)))
    for q, spec in specs:
        ast = to_ast(spec)
        spec2 = from_ast(ast, conn)
        d1, d2 = spec.describe(), spec2.describe()
        try:
            c1, c2 = retrieve.count_hits(conn, spec), retrieve.count_hits(conn, spec2)
        except Exception as e:                              # noqa: BLE001
            c1 = c2 = 'ERR:%s' % e
        diff = diff_ast(ast, to_ast(spec2), 'spec', 'spec2')
        ok = (d1 == d2) and (c1 == c2) and not diff
        ok_all = ok_all and ok
        rows.append((q, d1, d2, c1, c2, diff, ok))
    if verbose:
        for q, d1, d2, c1, c2, diff, ok in rows:
            print('%s %s' % ('✓' if ok else '✗', q))
            if not ok:
                print('    describe 1: %s' % d1)
                print('    describe 2: %s' % d2)
                print('    count_hits : %s vs %s' % (c1, c2))
                for line in diff:
                    print('    %s' % line)
        print('往返等价：%d 条用例，%s' % (len(rows), '全部通过' if ok_all else '存在失败'))
    return ok_all


def main():
    ap = argparse.ArgumentParser(description='统一语义中间表示（AST）：打印 / 反解 / 往返自检')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--question', default=None, help='把该问句解析后打印其 AST')
    ap.add_argument('--roundtrip', action='store_true', help='打印 spec→ast→spec′ 的往返对照')
    ap.add_argument('--selftest', action='store_true', help='往返等价单测（门禁用）')
    args = ap.parse_args()
    conn = __import__('sqlite3').connect(args.db)
    try:
        if args.question:
            spec = retrieve.parse_query(conn, args.question)
            ast = to_ast(spec)
            print(render_ast(ast))
            if args.roundtrip:
                spec2 = from_ast(ast, conn)
                print('--- 反解 describe：%s' % spec2.describe())
                print('--- diff：%s' % (diff_ast(ast, to_ast(spec2)) or '（无差异）'))
            return 0
        if args.selftest or True:
            return 0 if selftest(conn) else 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
