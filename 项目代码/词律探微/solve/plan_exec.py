# -*- coding: utf-8 -*-
"""plan_exec.py —— Query Plan **执行器**（第二轮审查 P0：让 Plan 成为真正的可执行查询语言）。

为什么要这个文件
================
GPT 第二轮 §9-10 原话：

> `queryplan.py` 能 validate / compile filters / from_plan，但**没有 PlanExecutor** 去完整
> 执行 `step1 → step2 → step3 → result`。尤其「先查 → 再过滤 → 再 group → 再 count →
> 再 argmax → 再 extract」这种真正的多步骤执行链，现在还没有完成。
> … Query Plan 是一个很好的「中间表示」，但还不是一个完整的「可执行查询语言」。

本模块补上这块，并把审查 §35-Phase6 要求的 **Provenance DAG** 一并落实：
每一步都产出新的 `Frame`，同时在 `ProvDAG` 上留一个节点，于是任何一个答案都能回答
「为什么是这个结果」（从结果往上回溯到 corpus）。

设计取舍
========
· **不重写检索/聚合**：所有能力尽量复用 `retrieve`（SQL 编译、排序白名单）、`aggregate`（分组口径）、
  `pairing`（配对）——Executor 是**编排层**，不是第二实现。审查明确警告过「不要两套」。
· **Frame 显式物化 pid 列表**：全库 5.8 万篇，物化成整数列表成本可接受（几百 KB），
  换来的是跨_ops（集合运算、受限向量检索、取篇内句）全部简单且**可独立复算**。
· **每步可失败且如实记录**：任一步出错记进 `problems`，绝不抛到调用方（上层据此决定拒答或降级）。
· **默认不启用**：只有显式调用 `execute()` 才跑；现存主链（`ask.answer` 的规则路）**完全不经过这里**
  → 1000 题零回归。
"""
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import retrieve                                                # noqa: E402
import aggregate                                               # noqa: E402

# 单帧最多承载的篇数（超出即如实截断并标记）
MAX_FRAME = 200000


# ================================================================ 溯源 DAG
class ProvDAG:
    """执行溯源图：节点 = 一次算子调用，边 = 它消费了哪些帧。

    `render()` 输出从**结果往上回溯**到 corpus 的链路（审查 Phase 6 要的东西）：
        F7 argmax
         ↑
        F6 count
         ↑
        …
         ↑
        corpus
    """

    def __init__(self):
        self.nodes = []

    def add(self, op, inputs, note='', kind='set', n=None, seconds=0.0):
        nid = 'F%d' % (len(self.nodes) + 1)
        self.nodes.append({'id': nid, 'op': op, 'inputs': list(inputs or []),
                           'note': note, 'kind': kind, 'n': n, 'seconds': round(seconds, 4)})
        return nid

    def parents_of(self, nid):
        for x in self.nodes:
            if x['id'] == nid:
                return x['inputs']
        return []

    def render(self, leaf=None):
        """自底向上渲染出一条溯源链（`leaf` 缺省取最后一个节点）。"""
        if not self.nodes:
            return '（无步骤）'
        end = leaf or self.nodes[-1]['id']
        chain, seen, stack = [], set(), [end]
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            for x in self.nodes:
                if x['id'] == nid:
                    chain.append(x)
                    stack.extend(x['inputs'])
        order = []
        for x in reversed(chain):
            order.append(x)
        lines = []
        for x in order:
            tail = '（%s）' % x['note'] if x['note'] else ''
            extra = '' if x['n'] is None else '  n=%s' % x['n']
            lines.append('%s  %s%s%s' % (x['id'], x['op'], tail, extra))
        if lines:
            lines.append('↑')
            lines.append('corpus')
        return '\n'.join(lines)

    def to_list(self):
        return list(self.nodes)


# ================================================================ 帧
class Frame:
    """执行器的数据载体。**只装 pid 集合 / 标量 / 分组行**，不装 SQL。"""

    def __init__(self, dag, kind='set', pids=None, scores=None, value=None,
                 rows=None, single=None, note='', prov=None):
        self.dag = dag
        self.kind = kind                       # set | scalar | groups | rows | single
        self.pids = list(pids or [])
        self.scores = dict(scores or {})
        self.value = value
        self.rows = list(rows or [])
        self.single = single
        self.note = note
        self.prov = prov
        self.truncated = False

    def __len__(self):
        return len(self.pids)

    def ids(self):
        return self.pids


# ================================================================ 指标 → SQL 列（复用白名单）
_METRIC_COL = dict((k, v[0]) for k, v in retrieve.ORDER_COLS.items())  # ze_ratio / han_len / …
_METRIC_EXPR = dict(retrieve.ORDER_EXPR)                               # change → ABS(p.change)
_METRIC_EXPR.update({'abs_change': 'ABS(p.change)'})


def _order_expr(metric):
    """排序/聚合用的 SQL 表达式（**白名单**，不接受用户串）。"""
    if metric in _METRIC_EXPR:
        return _METRIC_EXPR[metric]
    col = _METRIC_COL.get(metric)
    if col:
        return 'p.%s' % col
    return None


_GROUP_COL = {
    'author': 'p.author', 'cipai': 'p.cipai', 'dynasty': 'p.dynasty',
    'scene': 'p.scene', 'sent_n': 'p.sent_n', 'source': 'p.source',
}


def _group_col(field):
    return _GROUP_COL.get(field)


def _chunks(seq, size=900):
    """SQLite 变量上限保护：`pid IN (...)` 超 999 必须分块（审查 B9）。"""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _pid_filter_sql(pids, alias='p'):
    """pid 集合 → (若干 OR 分片, args)（分块，避免变量上限）。"""
    parts, args = [], []
    for c in _chunks(list(pids)):
        parts.append('%s.pid IN (%s)' % (alias, ','.join('?' * len(c))))
        args += list(c)
    return parts, args


# ================================================================ 执行器
class Executor:
    """Query Plan → 结果。每一步产出新 Frame 并在 DAG 上留痕。"""

    def __init__(self, conn, plan, session=None, question='', topk=5):
        self.conn = conn
        self.plan = plan
        self.session = session
        self.question = question
        self.topk = topk
        self.dag = ProvDAG()
        self.problems = []
        self.named = {}          # materialize_as 的命名帧

    # -------------------------------------------------- 入口
    def run(self):
        t0 = time.time()
        try:
            f = self._seed()
        except Exception as e:                                   # noqa: BLE001
            self.problems.append('初始帧构造失败：%s: %s' % (type(e).__name__, e))
            return None
        # 1) 显式 steps（Planner 产出）
        for i, st in enumerate(self.plan.get('steps') or []):
            try:
                f = self._step(f, st)
            except Exception as e:                               # noqa: BLE001
                self.problems.append('第 %d 步（%s）失败：%s: %s'
                                     % (i + 1, (st or {}).get('op'), type(e).__name__, e))
                return f
        # 2) operation（旧 intent 的语义糖：extreme / agg / pair / locate）
        op = self.plan.get('operation')
        if op:
            try:
                f = self._operation(f, op)
            except Exception as e:                               # noqa: BLE001
                self.problems.append('operation（%s）失败：%s: %s'
                                     % (op.get('kind'), type(e).__name__, e))
        # 3) 意图兜底
        f = self._by_intent(f)
        self.problems = [p for p in self.problems if p]
        return {'frame': f, 'dag': self.dag, 'problems': self.problems,
                'named': self.named, 'seconds': round(time.time() - t0, 4)}

    # -------------------------------------------------- 初始帧
    def _seed(self):
        sc = self.plan.get('scope') or {}
        t0 = time.time()
        if sc.get('base') == 'prev_result':
            pids = list(sc.get('ctx') or [])
            nid = self.dag.add('scope.prev_result', [], '上一轮结果集', 'set', len(pids),
                               time.time() - t0)
            return Frame(self.dag, 'set', pids, note='prev_result', prov=nid)
        # 有 filters 就从 SQL 精确集合起步（比先拿全库再过滤省一大截）
        flt = self.plan.get('filters') or {}
        if flt:
            import queryplan as QP
            sql, args = QP.compile_filters(self.conn, flt)
            pids = [r[0] for r in self.conn.execute(
                'SELECT p.pid FROM poems p WHERE %s' % sql, args)]
            nid = self.dag.add('sql.filter', [], '布尔过滤树', 'set', len(pids),
                               time.time() - t0)
            return Frame(self.dag, 'set', pids, note='filter', prov=nid)
        pids = [r[0] for r in self.conn.execute('SELECT pid FROM poems')]
        nid = self.dag.add('scope.corpus', [], '全库', 'set', len(pids), time.time() - t0)
        return Frame(self.dag, 'set', pids, note='corpus', prov=nid)

    # -------------------------------------------------- 算子派发
    def _step(self, f, st):
        op = (st or {}).get('op')
        fn = {
            'filter': self._op_filter, 'sort': self._op_sort, 'limit': self._op_limit,
            'group_by': self._op_group_by, 'aggregate': self._op_aggregate,
            'argmax': self._op_argmax, 'count': self._op_count,
            'extract': self._op_extract, 'pair': self._op_pair,
            'locate': self._op_locate, 'intersect': self._op_intersect,
            'union': self._op_union, 'diff': self._op_diff,
            'anchor': self._op_anchor, 'annotate': self._op_annotate,
            'materialize_as': self._op_materialize,
        }.get(op)
        if fn is None:
            self.problems.append('未知步骤算子：%r' % op)
            return f
        return fn(f, st)

    # ---- 各算子实现 ----
    def _op_filter(self, f, st):
        t0 = time.time()
        import queryplan as QP
        node = st.get('filters') or self.plan.get('filters') or {}
        if not node:
            return f
        sql, args = QP.compile_filters(self.conn, node)
        parts, pargs = _pid_filter_sql(f.pids)
        if not parts:
            return self._mk(Frame(self.dag, 'set', [], note='filter(empty)'),
                            'filter', f, '空集合', time.time() - t0)
        where = '(%s) AND (%s)' % (sql, ' OR '.join(parts))
        pids = [r[0] for r in self.conn.execute(
            'SELECT p.pid FROM poems p WHERE %s' % where, list(args) + pargs)]
        return self._mk(Frame(self.dag, 'set', pids, note='filter'), 'filter', f,
                        '布尔条件收窄', time.time() - t0)

    def _op_sort(self, f, st):
        """多键排序（审查 #13：旧实现只支持单键）。

        `keys` 按**优先级从高到低**书写；实现上从最低优先级开始做**稳定排序**，
        最终得到多键字典序。
        """
        t0 = time.time()
        keys = st.get('keys') or ([{'by': st.get('by'), 'dir': st.get('dir') or 'desc'}]
                                  if st.get('by') else [])
        keys = [k for k in keys if k.get('by')]
        if not keys or f.kind != 'set' or not f.pids:
            return f
        cur = list(f.pids)
        # ⚠ 稳定性只在 **Python 的同一次 sorted() 内**成立：若每个键各跑一条 SQL 就让 SQLite
        #   排，同分组内的返回次序是**任意的**，次级键会被打散（实测多步④：sent_n 相同的两篇，
        #   han_len=142 的那篇没排到前面）。正解：SQL 只负责**取值**（不排序），排序在 Python 侧
        #   按「最低优先级 → 最高优先级」依次做**稳定排序**，这样高优先级同值时完整保留次级的次序。
        _vals = []
        for k in keys:
            expr = _order_expr(k['by'])
            if expr is None:
                self.problems.append('排序指标不在白名单：%r' % k['by'])
                _vals.append(None)
                continue
            parts, args = _pid_filter_sql(f.pids)
            if not parts:
                _vals.append({})
                continue
            rr = self.conn.execute('SELECT p.pid, %s AS v FROM poems p WHERE %s'
                                   % (expr, ' OR '.join(parts)), args).fetchall()
            _vals.append(dict((a, b) for a, b in rr))
        _K = [k for k in keys if _order_expr(k['by']) is not None]
        _V = [v for v in _vals if v is not None]
        cur = sorted(f.pids)                       # 最末兜底：全键同值按 pid，保证确定性
        for k, d in zip(reversed(_K), reversed(_V)):
            _desc = (k.get('dir') or 'desc') == 'desc'

            def _key(p, d=d, _desc=_desc):
                v = d.get(p)
                if v is None:                       # 缺值恒排最后，避免 None 比较崩溃
                    return (1, 0.0)
                return (0, -v if _desc else v)
            cur = sorted(cur, key=_key)
        return self._mk(Frame(self.dag, 'set', cur, scores=f.scores, note='sort'),
                        'sort', f, ' / '.join('%s %s' % (k['by'], k.get('dir') or 'desc')
                                              for k in keys), time.time() - t0)

    def _op_limit(self, f, st):
        t0 = time.time()
        n = int(st.get('n') or self.topk)
        if f.kind != 'set':
            return f
        pids = f.pids[:n]
        fr = Frame(self.dag, 'set', pids, scores=f.scores, note='limit')
        fr.truncated = len(f.pids) > n
        return self._mk(fr, 'limit', f, '取前 %d（共 %d）' % (n, len(f.pids)), time.time() - t0)

    def _op_group_by(self, f, st):
        t0 = time.time()
        field = st.get('field') or st.get('by')
        col = _group_col(field)
        if col is None:
            self.problems.append('不支持的分组维度：%r' % field)
            return f
        parts, args = _pid_filter_sql(f.pids)
        where = (' OR '.join('(%s)' % p for p in parts) if parts else '1=0')
        rows = self.conn.execute(
            'SELECT %s AS k, COUNT(*) AS n FROM poems p WHERE (%s) GROUP BY %s' % (col, where, col),
            args).fetchall()
        out = [{'key': r[0], 'n': r[1]} for r in rows]
        # ⚠ pids **必须带下去**：后续 aggregate/annotate 仍要在这个候选宇宙里做 SQL/GROUP BY，
        #   若 groups 帧丢掉 pids，下一步的 `pid IN ()` 会是空集（实测多步① 因此返回 []）。
        return self._mk(Frame(self.dag, 'groups', pids=f.pids, rows=out,
                              note='group_by:%s' % field),
                        'group_by:%s' % field, f, '', time.time() - t0)

    def _op_aggregate(self, f, st):
        """分组后聚合：count / avg / min / max / sum / ratio_ze（**SQL 精确算**，不是近似）。"""
        t0 = time.time()
        metric = st.get('metric') or 'count'
        # 进入本算子时若还不是 groups 帧 → 先按 st 的 group_by 分组（Planner 常写成一步）
        if f.kind != 'groups':
            f = self._op_group_by(f, st)
        parts, args = _pid_filter_sql(f.pids)
        where = (' OR '.join('(%s)' % p for p in parts) if parts else '1=0')
        field = st.get('field') or st.get('by') or 'author'
        col = _group_col(field)
        if col is None:
            self.problems.append('聚合：不支持的分组维度 %r' % field)
            return f
        expr_map = {'count': 'COUNT(*)', 'avg': 'AVG(%s)' % (_order_expr(st.get('of') or 'ze_ratio') or 'p.ze_ratio'),
                    'min': 'MIN(%s)' % (_order_expr(st.get('of') or 'han_len') or 'p.han_len'),
                    'max': 'MAX(%s)' % (_order_expr(st.get('of') or 'han_len') or 'p.han_len'),
                    'sum': 'SUM(%s)' % (_order_expr(st.get('of') or 'han_len') or 'p.han_len'),
                    'ratio_ze': 'SUM(p.ze)*1.0/NULLIF(SUM(p.ze+p.ping),0)*100'}
        expr = expr_map.get(metric)
        if expr is None:
            self.problems.append('聚合：未知 metric %r' % metric)
            return f
        rows = self.conn.execute(
            'SELECT %s AS k, %s AS v, COUNT(*) AS n FROM poems p WHERE (%s) GROUP BY %s'
            % (col, expr, where, col), args).fetchall()
        out = [{'key': r[0], 'value': round(r[1], 4) if isinstance(r[1], float) else r[1], 'n': r[2]}
               for r in rows]
        return self._mk(Frame(self.dag, 'groups', rows=out, note='agg:%s' % metric),
                        'aggregate:%s' % metric, f, '', time.time() - t0)

    def _op_argmax(self, f, st):
        """「哪一组最多 / 哪个作者写得最多」= 排序 + 取首。"""
        t0 = time.time()
        if f.kind != 'groups':
            self.problems.append('argmax 需要 groups 帧（先 group_by+aggregate）')
            return f
        key = st.get('by') or 'value'
        rev = (st.get('dir') or 'desc') == 'desc'
        rows = sorted(f.rows, key=lambda r: (r.get(key) is None, -(r.get(key) or 0)
                                             if rev else (r.get(key) or 0)))
        out = Frame(self.dag, 'groups', rows=rows[:1], note='argmax')
        return self._mk(out, 'argmax', f, '取%s者' % ('最大' if rev else '最小'), time.time() - t0)

    def _op_count(self, f, st):
        t0 = time.time()
        n = len(f.pids) if f.kind == 'set' else (f.value or 0)
        return self._mk(Frame(self.dag, 'scalar', value=n, note='count'),
                        'count', f, '', time.time() - t0)

    def _op_extract(self, f, st):
        """篇内取值：第 N 句第 M 个字 / 第 N 句整句（审查 #14：旧 extract 只支持单个字位置）。"""
        t0 = time.time()
        pids = f.pids[:1] if f.kind == 'set' else ([f.single] if f.single else [])
        if not pids:
            self.problems.append('extract：没有锚定篇目')
            return Frame(self.dag, 'rows', rows=[], note='extract(empty)')
        pid = pids[0]
        sent = st.get('sent') or 1
        unit = st.get('unit') or 'char'
        pos = st.get('pos')
        row = self.conn.execute('SELECT text FROM lines WHERE pid=? AND idx=?',
                                (pid, sent - 1)).fetchone()
        text = row[0] if row else ''
        if unit == 'line':
            val = text
        else:
            if not pos:
                self.problems.append('extract(char) 缺 pos')
                val = ''
            else:
                val = text[pos - 1:pos] if len(text) >= pos else ''
        rows = [{'pid': pid, 'sent': sent, 'pos': pos, 'unit': unit, 'text': text, 'value': val}]
        return self._mk(Frame(self.dag, 'rows', rows=rows, single=pid, note='extract'),
                        'extract', f, '第%d句%s' % (sent, ('第%d字' % pos) if unit == 'char' else '整句'),
                        time.time() - t0)

    def _op_pair(self, f, st):
        """两两配对：**委托** `pairing.find_pairs`（不重写）。"""
        t0 = time.time()
        try:
            import pairing
            spec = retrieve.QuerySpec()
            spec.pair = {'dims': ('tone',), 'n_frame': int(st.get('n_frame') or 1)}
            if self.plan.get('filters'):
                spec.filters_tree = self.plan['filters']
            spec = retrieve._finalize(spec)
            groups = pairing.find_pairs(self.conn, spec, limit=int(st.get('limit') or 3))
            rows = [{'pids': list(g), 'label': '全篇逐位平仄完全相同'} for g in (groups or [])]
        except Exception as e:                                   # noqa: BLE001
            self.problems.append('pair 失败：%s: %s' % (type(e).__name__, e))
            rows = []
        return self._mk(Frame(self.dag, 'rows', rows=rows, note='pair'),
                        'pair', f, '', time.time() - t0)

    def _op_locate(self, f, st):
        """反查出处：「寒蛩切切响空帷」出自哪首 —— FTS/字面 = 首选，向量 = 兜底。"""
        t0 = time.time()
        q = st.get('q') or (self.plan.get('_legacy') or {}).get('raw_question') or ''
        q = (q or '').strip('「」“”"\'').strip()
        rows = []
        if q:
            try:
                rr = self.conn.execute(
                    'SELECT pid, idx, text FROM lines WHERE text LIKE ? LIMIT 5',
                    ('%' + q + '%',)).fetchall()
                rows = [{'pid': r[0], 'idx': r[1] + 1, 'text': r[2], 'score': 1.0} for r in rr]
            except Exception:                                    # noqa: BLE001
                rows = []
        pids = [r['pid'] for r in rows]
        return self._mk(Frame(self.dag, 'rows', pids=pids, rows=rows, note='locate'),
                        'locate', f, '字面命中 %d 句' % len(rows), time.time() - t0)

    def _op_intersect(self, f, st):
        return self._set_op(f, st, 'intersect')

    def _op_union(self, f, st):
        return self._set_op(f, st, 'union')

    def _op_diff(self, f, st):
        return self._set_op(f, st, 'diff')

    def _set_op(self, f, st, kind):
        t0 = time.time()
        other = self._resolve_ref(st.get('with') or st.get('other'))
        if other is None:
            self.problems.append('%s：找不到参照集合 %r' % (kind, st.get('with')))
            return f
        a, b = set(f.pids), set(other.pids)
        res = {'intersect': a & b, 'union': a | b, 'diff': a - b}[kind]
        out = sorted(res)
        return self._mk(Frame(self.dag, 'set', out, note=kind),
                        kind, f, '%d %s %d' % (len(a), {'intersect': '∩', 'union': '∪',
                                                        'diff': '−'}[kind], len(b)), time.time() - t0)

    def _resolve_ref(self, ref):
        if ref is None:
            return None
        if isinstance(ref, str) and ref in self.named:
            return self.named[ref]
        if isinstance(ref, list):
            return Frame(self.dag, 'set', ref, note='literal')
        return None

    def _op_anchor(self, f, st):
        """锚定到会话里的某一篇 / 某个集合（多轮「那首」「它」）。"""
        t0 = time.time()
        src = st.get('from') or 'prev_single'
        if self.session is not None:
            import context as CTX
            r = CTX.resolve(self.session, self.question or '')
            if src == 'prev_single' and r.get('kind') == 'single':
                pid = r.get('pid')
                return self._mk(Frame(self.dag, 'single', pids=[pid] if pid else [], single=pid,
                                      note='anchor:single'), 'anchor', f, '单篇 pid=%s' % pid,
                                time.time() - t0)
            if r.get('kind') == 'set':
                pids = r.get('pids') or []
                return self._mk(Frame(self.dag, 'set', pids, note='anchor:set'),
                                'anchor', f, '集合 %d 篇' % len(pids), time.time() - t0)
        pid = st.get('pid')
        return self._mk(Frame(self.dag, 'single', pids=[pid] if pid else [], single=pid,
                              note='anchor:literal'), 'anchor', f, '', time.time() - t0)

    def _op_annotate(self, f, st):
        """给当前候选打语义分（**受限**向量检索：只在 f.pids 内做）。"""
        t0 = time.time()
        q = st.get('q') or ' '.join((self.plan.get('_legacy') or {}).get('semantic_terms') or [])
        via = st.get('via') or 'vector'
        if via != 'vector' or not q:
            return f
        try:
            import vector_index as VI
            _allow = set(f.pids) if f.pids else None
            hits = VI.search(q, topk=int(st.get('topk') or max(self.topk, 10)), allow=_allow)
        except Exception as e:                                   # noqa: BLE001
            self.problems.append('annotate 失败：%s: %s' % (type(e).__name__, e))
            return f
        if not hits:
            self.problems.append('annotate：向量不可用或未召回（%s）' % VI.why())
            return f
        scores = dict(f.scores)
        scores.update(dict(hits))
        ordered = sorted(set(f.pids), key=lambda p: (-scores.get(p, -1.0), p))
        return self._mk(Frame(self.dag, 'set', ordered, scores=scores, note='annotate:vector'),
                        'annotate', f, '语义重排 %d 篇' % len(hits), time.time() - t0)

    def _op_materialize(self, f, st):
        name = st.get('name') or ('s%d' % (len(self.named) + 1))
        self.named[name] = f
        return self._mk(f, 'materialize_as:%s' % name, f, '', 0.0)

    # -------------------------------------------------- operation（旧 intent 的语义糖）
    def _operation(self, f, op):
        kind = op.get('kind')
        t = op.get('target') or {}
        if kind == 'extreme':
            f = self._op_sort(f, {'keys': [{'by': t.get('metric'),
                                            'dir': t.get('dir') or 'desc'}]})
            return self._op_limit(f, {'n': self.topk})
        if kind == 'agg':
            return self._op_aggregate(f, t.get('agg') or {})
        if kind == 'pair':
            return self._op_pair(f, t.get('pair') or {})
        if kind == 'locate':
            return self._op_locate(f, {})
        return f

    def _by_intent(self, f):
        """intent 决定**最终形态**（count/extreme/similarity/locate…）。"""
        it = self.plan.get('intent')
        if it == 'count' and f.kind == 'set':
            return self._op_count(f, {})
        if it == 'similarity':
            return self._op_annotate(f, {'via': 'vector',
                                         'q': ' '.join((self.plan.get('_legacy') or {})
                                                       .get('semantic_terms') or []),
                                         'topk': max(self.topk, 10)})
        return f

    # -------------------------------------------------- 小工具
    def _mk(self, frame, op, parent, note, seconds):
        nid = self.dag.add(op, [parent.prov] if parent is not None and parent.prov else [],
                           note, frame.kind,
                           len(frame.pids) if frame.kind in ('set', 'single') else len(frame.rows),
                           seconds)
        frame.prov = nid
        return frame


# ================================================================ 对外入口
def execute(conn, plan, *, session=None, question='', topk=5):
    """执行一个 Query Plan → {frame, dag, problems, named, seconds}。**永不抛异常**。"""
    return Executor(conn, plan, session=session, question=question, topk=topk).run()


def explain(res):
    """把执行结果渲染成人话（供前端「理解详情」与排障）。"""
    if not res:
        return '（未执行）'
    f = res['frame']
    lines = []
    kind_map = {'set': '篇集合', 'scalar': '数值', 'groups': '分组表',
                'rows': '明细行', 'single': '单篇'}
    lines.append('结果形态：%s%s' % (kind_map.get(f.kind, f.kind),
                                    '（被截断，仅含前若干）' if getattr(f, 'truncated', False) else ''))
    if f.kind in ('set', 'single'):
        lines.append('篇数：%d%s' % (len(f.pids), ('  前 %d：%s' % (min(5, len(f.pids)),
                                                  f.pids[:5])) if f.pids else ''))
    elif f.kind == 'scalar':
        lines.append('数值：%s' % f.value)
    elif f.rows:
        lines.append('行：%s' % json.dumps(f.rows[:3], ensure_ascii=False))
    lines.append('溯源：')
    lines.append(res['dag'].render(f.prov))
    if res['problems']:
        lines.append('问题：%s' % '；'.join(res['problems']))
    return '\n'.join(lines)


# ================================================================ 自检
def selftest(conn):
    """自检：多条多步 Plan，逐步结果用**独立 SQL/Python 复算**核对。"""
    import queryplan as QP
    ok_all = True

    def _chk(name, got, want):
        nonlocal ok_all
        ok = (got == want)
        ok_all = ok_all and ok
        print('%s %-42s 得到 %r ／ 期望 %r' % ('✓' if ok else '✗', name, got, want))

    # ── ① 多步：清代句子含「月」的作品里，按作者分组取写得最多的那位 ──
    plan = QP.empty_plan()
    plan['intent'] = 'aggregate'
    plan['filters'] = {'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                               {'field': 'lines.text', 'op': 'contains', 'value': '月'}]}
    plan['steps'] = [{'op': 'group_by', 'field': 'author'},
                     {'op': 'aggregate', 'metric': 'count', 'field': 'author'},
                     {'op': 'argmax', 'by': 'value', 'dir': 'desc'}]
    r = execute(conn, plan)
    rows = r['frame'].rows                       # argmax 之后只剩第 1 名
    rows_sorted = sorted(rows, key=lambda x: -x['value'])
    ref = conn.execute(
        "SELECT p.author, COUNT(*) c FROM poems p WHERE p.dynasty='清' AND "
        "p.pid IN (SELECT pid FROM lines WHERE text LIKE '%月%') GROUP BY p.author "
        "ORDER BY c DESC, p.author LIMIT 3").fetchall()
    _chk('多步① group→count→argmax（top1 计数）',
         rows_sorted[0]['value'] if rows_sorted else None, ref[0][1] if ref else None)
    _chk('多步① argmax 只留第一名', len(rows), 1)
    _chk('多步① argmax 命中作者', rows_sorted[0]['key'] if rows_sorted else None,
         ref[0][0] if ref else None)
    # argmax 前：aggregate 的完整分组表 top3 必须与独立复算一致（**顺序也要一致**）
    r2 = execute(conn, dict(plan, steps=plan['steps'][:2]))
    ag3 = [x['key'] for x in sorted(r2['frame'].rows, key=lambda x: (-x['value'], x['key']))[:3]]
    _chk('多步① aggregate top3 作者一致', sorted(ag3), sorted([x[0] for x in ref]))

    # ── ② 布尔 NOT + 布尔 OR 再计数 ──
    plan = QP.empty_plan()
    plan['intent'] = 'count'
    plan['filters'] = {'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                               {'field': 'cipai', 'op': '=', 'value': '临江仙'},
                               {'not': {'or': [{'field': 'author', 'op': '=', 'value': '纳兰性德'},
                                               {'field': 'author', 'op': '=', 'value': '朱彝尊'}]}}]}
    r = execute(conn, plan)
    ref = conn.execute("SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND p.cipai='临江仙' "
                       "AND p.author NOT IN ('纳兰性德','朱彝尊')").fetchone()[0]
    _chk('多步② 布尔 NOT(OR) 计数', r['frame'].value, ref)

    # ── ③ 排序 + 取极值 ──
    plan = QP.empty_plan()
    plan['intent'] = 'extreme'
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'sort', 'keys': [{'by': 'han_len', 'dir': 'asc'}]},
                     {'op': 'limit', 'n': 3}]
    r = execute(conn, plan)
    ref = [x[0] for x in conn.execute(
        "SELECT pid FROM poems WHERE dynasty='清' ORDER BY han_len ASC, pid ASC LIMIT 3")]
    _chk('多步③ sort(asc)+limit 的 pid 序列', r['frame'].pids, ref)

    # ── ④ 多键排序（审查 #13：旧实现只支持单键）──
    plan = QP.empty_plan()
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'sort', 'keys': [{'by': 'sent_n', 'dir': 'desc'},
                                             {'by': 'han_len', 'dir': 'asc'}]},
                     {'op': 'limit', 'n': 5}]
    r = execute(conn, plan)
    ref = [x[0] for x in conn.execute(
        "SELECT pid FROM poems WHERE dynasty='清' ORDER BY sent_n DESC, han_len ASC, pid ASC LIMIT 5")]
    _chk('多步④ 多键排序', r['frame'].pids, ref)

    # ── ⑤ 集合运算（审查 #15：cross-result op）──
    plan = QP.empty_plan()
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'materialize_as', 'name': 'qing'},
                     {'op': 'filter', 'filters': {'field': 'cipai', 'op': '=', 'value': '临江仙'}},
                     {'op': 'diff', 'with': 'qing'}]
    r = execute(conn, plan)
    _chk('多步⑤ materialize→filter→diff 结果为空集', len(r['frame'].pids), 0)

    # ── ⑥ 提取：清朝最短那首的第 1 句第 3 个字 ──
    plan = QP.empty_plan()
    plan['intent'] = 'extract'
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'sort', 'keys': [{'by': 'han_len', 'dir': 'asc'}]},
                     {'op': 'limit', 'n': 1},
                     {'op': 'extract', 'sent': 1, 'pos': 3, 'unit': 'char'}]
    r = execute(conn, plan)
    row = r['frame'].rows[0] if r['frame'].rows else {}
    _pid = row.get('pid')
    ref_row = conn.execute('SELECT text FROM lines WHERE pid=? AND idx=0', (_pid,)).fetchone()
    ref_char = (ref_row[0][2:3] if ref_row and len(ref_row[0]) >= 3 else '')
    _chk('多步⑥ sort→limit→extract(1句3字)', row.get('value'), ref_char)

    # ── ⑦ 句级量化算子经由 Plan（审查 #5：line_q 必须是一等算子）──
    plan = QP.empty_plan()
    plan['intent'] = 'count'
    plan['filters'] = {'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                               {'field': 'line_q', 'op': '=',
                                'value': {'op': '∄', 'pred': ['tail_pz', '仄']}}]}
    r = execute(conn, plan)
    ref = conn.execute("SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND "
                       "p.pid NOT IN (SELECT pid FROM lines WHERE substr(pz,-1,1)='仄')").fetchone()[0]
    _chk('多步⑦ line_q(∄句脚仄) 计数', r['frame'].value, ref)

    # ── ⑧ 溯源 DAG 可用性 ──
    prov = r['dag'].render(r['frame'].prov)
    ok8 = ('corpus' in prov or 'sql.filter' in prov) and 'count' in prov
    ok_all = ok_all and ok8
    print('%s 溯源 DAG 可回溯到根：%s' % ('✓' if ok8 else '✗', prov.replace('\n', ' ← ')))
    print('自检：%s' % ('全部通过' if ok_all else '存在失败'))
    return ok_all


def main():
    import argparse
    ap = argparse.ArgumentParser(description='PlanExecutor 自检 / 渲染')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--question', default=None, help='用规则路解析后转 Plan 并执行（演示）')
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    try:
        if args.question:
            import queryplan as QP
            spec = retrieve.parse_query(conn, args.question)
            plan = QP.to_plan(spec)
            print(QP.render(plan))
            print('---- 执行 ----')
            print(explain(execute(conn, plan)))
            return 0
        return 0 if selftest(conn) else 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
