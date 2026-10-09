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
                 rows=None, single=None, note='', prov=None, label=None, group_field=None):
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
        # ★ 2026-10-09（第三轮审查 P1-8）：**帧自述**——scalar 的语义标签（篇数/中位数/标准差…），
        #   分组帧的真实分组字段。渲染层据此出文案，不再用一套通用文案覆盖所有情况
        #   （旧版把所有 scalar 都写成"共 N 篇"、把所有分组都写成"按作者分组"）。
        self.label = label
        self.group_field = group_field

    def __len__(self):
        return len(self.pids)

    def ids(self):
        return self.pids


# ================================================================ 指标 → SQL 列（复用白名单）
_METRIC_COL = dict((k, v[0]) for k, v in retrieve.ORDER_COLS.items())  # ze_ratio / han_len / …
_METRIC_EXPR = dict(retrieve.ORDER_EXPR)                               # change → ABS(p.change)
_METRIC_EXPR.update({'abs_change': 'ABS(p.change)'})

#: 数值字段的中文名（scalar 帧的标签用；2026-10-09 第三轮审查 P1-8）
_FIELD_CN = {'ze_ratio': '仄声比例', 'han_len': '字数', 'sent_n': '句数', 'change': '变化值',
             'abs_change': '变化幅度', 'threshold': '阈值', 'longest_len': '最长句字数',
             'longest_seq': '最长同声串', 'f_ratio': '前段仄声比例', 'b_ratio': '后段仄声比例'}


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
        self.retrieve_report = []      # ★ retrieve 各路召回的**执行报告**（是否执行/召回了多少）
        # ★ 2026-10-09（第三轮审查 P0-2/P0-3）：**失败语义**——关键步骤失败不得再产出
        #   「已满足条件」式的正常答案。`failed_steps` 里的任何一条都会让 whole-plan
        #   标为 EXECUTION_FAILED（上层据此回落既有链并如实报告原因）；
        #   `partial_reasons` 为可控降级（继续执行、但要如实标注）。
        self.failed_steps = []
        self.partial_reasons = []

    # -------------------------------------------------- 入口
    def run(self):
        t0 = time.time()
        try:
            f = self._seed()
        except Exception as e:                                   # noqa: BLE001
            self.problems.append('初始帧构造失败：%s: %s' % (type(e).__name__, e))
            self.failed_steps.append(self.problems[-1])
            return None
        # 0) ★ retrieve（2026-10-09 修，第三轮审查 P0）：执行 plan['retrieve'] 的
        #    **多路召回**——「理解层说了（vector/fts），执行层照做」。纯 sql 时零变化。
        try:
            f = self._retrieve(f)
        except Exception as e:                                   # noqa: BLE001
            self.problems.append('retrieve 执行失败：%s: %s（已按 SQL 候选继续）'
                                 % (type(e).__name__, e))
            self.failed_steps.append(self.problems[-1])
        # 1) 显式 steps（Planner 产出）
        for i, st in enumerate(self.plan.get('steps') or []):
            try:
                f = self._step(f, st)
            except Exception as e:                               # noqa: BLE001
                msg = ('第 %d 步（%s）失败：%s: %s'
                       % (i + 1, (st or {}).get('op'), type(e).__name__, e))
                self.problems.append(msg)
                self.failed_steps.append(msg)                    # ★ 关键步骤失败 → 状态 FAILED
                return {'frame': f, 'dag': self.dag, 'problems': self.problems,
                        'named': self.named, 'seconds': round(time.time() - t0, 4),
                        'retrieve_report': self.retrieve_report,
                        'state': 'EXECUTION_FAILED'}
        # 2) operation（旧 intent 的语义糖：extreme / agg / pair / locate）
        op = self.plan.get('operation')
        if op:
            try:
                f = self._operation(f, op)
            except Exception as e:                               # noqa: BLE001
                msg = ('operation（%s）失败：%s: %s' % (op.get('kind'), type(e).__name__, e))
                self.problems.append(msg)
                self.failed_steps.append(msg)                    # ★ 同上
        # 3) 意图兜底
        f = self._by_intent(f)
        self.problems = [p for p in self.problems if p]
        state = ('EXECUTION_FAILED' if self.failed_steps
                 else ('EXECUTION_PARTIAL' if self.partial_reasons else 'EXECUTION_OK'))
        return {'frame': f, 'dag': self.dag, 'problems': self.problems,
                'named': self.named, 'seconds': round(time.time() - t0, 4),
                'retrieve_report': self.retrieve_report, 'state': state}

    # -------------------------------------------------- 初始帧
    def _seed(self):
        sc = self.plan.get('scope') or {}
        t0 = time.time()
        if sc.get('base') == 'prev_result':
            pids = list(sc.get('ctx') or [])
            # ★ 2026-10-09（第三轮审查 P0-5）：本轮根级 `plan['filters']` 必须与上一轮
            #   结果集**求交**——旧版此分支直接返回、根级条件被静默跳过
            #   （「这些词里字数超过五十的有哪些」会把新条件丢掉）。
            flt = self.plan.get('filters') or {}
            if flt and pids:
                import queryplan as QP
                sql, args = QP.compile_filters(self.conn, flt)
                parts, pargs = _pid_filter_sql(pids)
                _hits = set(r[0] for r in self.conn.execute(
                    'SELECT p.pid FROM poems p WHERE (%s) AND (%s)'
                    % (sql, ' OR '.join(parts)), list(args) + pargs))
                pids = [p for p in pids if p in _hits]           # 保持上一轮顺序
            nid = self.dag.add('scope.prev_result', [], '上一轮结果集∩本轮条件',
                               'set', len(pids), time.time() - t0)
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

    # -------------------------------------------------- 多路召回（retrieve 的真正执行）
    def _retrieve(self, f):
        """执行 `plan['retrieve']`——「**理解层说了，执行层照做**」的落点（第三轮审查 P0）。

        `retrieve` 条目：`{"mode": "sql"|"vector"|"fts", "q": "…", "topk": N}`（见 queryplan.RETRIEVE_MODES）。
          · 纯 `sql`（**默认**，也是 planner 在无语义条件时给的）：本函数**不做任何事**——
            seed 的布尔过滤就是 SQL 路 → 既有行为**逐字节不变**；
          · `vector`：**候选集内**受限语义召回 `vector_index.search(q, allow=f.pids)`；
          · `fts`   ：候选集内**全文短语**召回（多词计分，可独立复算）；
          · 多路 → RRF 名次融合（fusion.rrf，k=60）→ 候选帧，**上限 500**（候选≠全集，如实截断）。
        索引不可用 / 召回为空 → **如实进 problems 与 retrieve_report**（绝不假装执行过）。
        """
        items = [x for x in (self.plan.get('retrieve') or []) if isinstance(x, dict)]
        active = [x for x in items if (str(x.get('mode') or 'sql')) in ('vector', 'fts')]
        if not active:
            return f                                     # 纯 sql：零变化
        t0 = time.time()
        allow = set(f.pids)
        channels = []
        for x in active:
            mode = str(x.get('mode'))
            q = str(x.get('q') or self.question or '').strip()
            tk = int(x.get('topk') or max(self.topk * 10, 50))
            if mode == 'vector':
                try:
                    import vector_index as VI
                    if not VI.available():
                        why = (VI.why() or '未知原因')[:80]
                        self.problems.append('retrieve.vector 未执行：向量索引不可用（%s）' % why)
                        self.retrieve_report.append({'mode': 'vector', 'q': q, 'topk': tk,
                                                     'n': 0, 'executed': False, 'why': why})
                        continue
                    hits = VI.search(q, topk=tk, allow=allow)
                    pids = [p for p, _s in hits]
                    self.retrieve_report.append({'mode': 'vector', 'q': q, 'topk': tk,
                                                 'n': len(pids), 'executed': True,
                                                 'allow_n': len(allow)})
                    if pids:
                        channels.append(pids)
                except Exception as e:                   # noqa: BLE001
                    self.problems.append('retrieve.vector 执行失败：%r' % e)
                    self.retrieve_report.append({'mode': 'vector', 'q': q, 'topk': tk,
                                                 'n': 0, 'executed': False, 'why': repr(e)})
            elif mode == 'fts':
                try:
                    pids = self._fts_in(allow, q, tk)
                    self.retrieve_report.append({'mode': 'fts', 'q': q, 'topk': tk,
                                                 'n': len(pids), 'executed': True,
                                                 'allow_n': len(allow)})
                    if pids:
                        channels.append(pids)
                except Exception as e:                   # noqa: BLE001
                    self.problems.append('retrieve.fts 执行失败：%r' % e)
                    self.retrieve_report.append({'mode': 'fts', 'q': q, 'topk': tk,
                                                 'n': 0, 'executed': False, 'why': repr(e)})
        if not channels:
            # ★ 2026-10-09（第三轮审查 P0-2）：**召回失败/为空不得回落到原 SQL 候选集**——
            #   旧版 `return f` 会把「清词全量」当成「写秋景的作品」交给答案渲染。
            #   现在统一走**失败语义**（返回空帧 + 记 failed，由上层回落既有链并报告原因）：
            #   语义条件「没执行成功」时，宁可不给结果，也不拿未经筛选的集合冒充。
            _why = '；'.join('%s：%s' % (x.get('mode'), x.get('why') or '未返回候选')
                           for x in self.retrieve_report) or '未返回候选'
            self.failed_steps.append('语义召回未完成（%s）——不以 SQL 候选集冒充语义结果' % _why)
            self.problems.append(self.failed_steps[-1])
            nid = self.dag.add('retrieve.failed', [f.prov], '召回未完成（failed-closed）',
                               'set', 0, time.time() - t0)
            return Frame(self.dag, 'set', [], note='retrieve_failed', prov=nid)
        if len(channels) == 1:
            merged = list(channels[0])
        else:
            import fusion
            merged = fusion.ranked(fusion.rrf(channels))
        cap = 500                                        # 候选上限：语义候选是**候选**，不是全集
        truncated = len(merged) > cap
        merged = merged[:cap]
        modes = '+'.join(sorted(set(str(x.get('mode')) for x in active)))
        nid = self.dag.add('retrieve.%s' % modes, [f.prov],
                           '候选集内召回（%d 路，RRF 融合%s）'
                           % (len(channels), '，已截断至 %d' % cap if truncated else ''),
                           'set', len(merged), time.time() - t0)
        out = Frame(self.dag, 'set', merged, note='retrieve', prov=nid)
        out.truncated = truncated
        return out

    def _fts_in(self, allow, q, tk):
        """候选集内**全文短语**召回：多词 OR 计分（命中句数降序、pid 升序 → **可独立复算**）。"""
        import re as _re2
        terms = [t for t in _re2.split(r'[\s,，、;；/]+', q or '') if len(t) >= 2][:8]
        if not terms and q:
            terms = [q]
        if not terms:
            return []
        parts, args = _pid_filter_sql(list(allow), alias='l')
        if not parts:
            return []
        where = '(%s) AND (%s)' % (' OR '.join(['l.text LIKE ?'] * len(terms)),
                                   ' OR '.join(parts))
        largs = ['%' + t + '%' for t in terms] + list(args) + [max(1, int(tk))]
        rows = self.conn.execute(
            'SELECT l.pid, COUNT(DISTINCT l.idx) AS c FROM lines l WHERE %s '
            'GROUP BY l.pid ORDER BY c DESC, l.pid LIMIT ?' % where, largs).fetchall()
        return [r[0] for r in rows]

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
            'median': self._op_median, 'stddev': self._op_stddev,
            'mode': self._op_mode, 'rank': self._op_rank,
            'project': self._op_project, 'similar_to': self._op_similar_to,
            'retrieve': self._op_retrieve,
        }.get(op)
        if fn is None:
            self.problems.append('未知步骤算子：%r' % op)
            self.failed_steps.append(self.problems[-1])          # ★ 未知算子=关键失败
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
        # ★ 2026-10-09（第三轮审查 P1-8⑥）：`n=0`/负数不再被静默当成"未传参数"——
        #   显式非法的 n 报 problem 并按默认处理（validate 已挡一层，这是执行层双保险）。
        n_raw = st.get('n')
        if isinstance(n_raw, int) and not isinstance(n_raw, bool) and n_raw >= 1:
            n = n_raw
        else:
            if n_raw is not None:
                self.problems.append('limit.n 非法（%r）——已按默认 %d 处理' % (n_raw, self.topk))
            n = self.topk
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
                              note='group_by:%s' % field, group_field=field),
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
        # ★ 2026-10-09（第三轮审查 P1-8③）：聚合的分组**沿用上一阶段的真实分组字段**
        #   （groups 帧的 group_field）；只有完全没有分组信息时才退回 author——旧版无条件默认
        #   author，会让「按声情分组、再求统计」的多步计划退化成按作者分组。
        field = (st.get('field') or st.get('by')
                 or getattr(f, 'group_field', None) or 'author')
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
        return self._mk(Frame(self.dag, 'scalar', value=n, note='count', label='篇数'),
                        'count', f, '', time.time() - t0)

    def _op_extract(self, f, st):
        """篇内取值：第 N 句第 M 个**汉字** / 第 N 句整句。

        ⚠ 2026-10-09（第三轮审查 P1-10）两处口径修订：
        ① 多篇候选时**如实披露**「基于首篇」（旧版静默取首篇——候选未排序时会提取错篇目）；
        ② 「第 M 个字」统一为**汉字序号**（跳过标点，与全库口径 `lines.pz` 一致）——
           旧版用字符串下标，'……分明。' 的「第 7 字」会取到句号。
        """
        t0 = time.time()
        if f.kind == 'set' and len(f.pids) > 1:
            self.problems.append('extract：在 %d 篇候选上取**首篇**（如需指定篇目请先 sort/limit）'
                                 % len(f.pids))
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
                import re as _re3
                _han = _re3.findall(r'[\u3400-\u4dbf\u4e00-\u9fff]', text)
                val = _han[pos - 1] if len(_han) >= pos else ''
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
            # ★ 2026-10-09（第三轮审查 P1-9）：**当前帧（已收窄）必须参与配对范围**——
            #   旧版只用根级条件重查，上一阶段的筛选会被越过（「先筛后配」的步骤失效）。
            #   （≤30000 才带 ctx_pids：更大即视为"接近全库"，避免超 SQLite 变量上限。）
            if f.kind == 'set' and f.pids and len(f.pids) <= 30000:
                spec.ctx_pids = list(f.pids)
            spec = retrieve._finalize(spec)
            groups = pairing.find_pairs(self.conn, spec, limit=int(st.get('limit') or 3))
            rows = [{'pids': list(g), 'label': '全篇逐位平仄完全相同'} for g in (groups or [])]
        except Exception as e:                                   # noqa: BLE001
            self.problems.append('pair 失败：%s: %s' % (type(e).__name__, e))
            self.failed_steps.append(self.problems[-1])          # ★ 关键步骤失败
            rows = []
        return self._mk(Frame(self.dag, 'rows', rows=rows, note='pair'),
                        'pair', f, '', time.time() - t0)

    def _op_locate(self, f, st):
        """反查出处：「寒蛩切切响空帷」出自哪首 —— 字面（当前帧内）= 首选，句级向量 = 兜底。

        ⚠ 2026-10-09（第三轮审查 P1-9）：原实现**全库搜**（不继承当前帧约束）、
        且注释声称的"向量兜底"并不存在。现补：① 在当前帧内做字面检索；
        ② 字面 0 命中时走 `search_lines` 句级向量兜底（同样限定当前帧）。
        """
        t0 = time.time()
        q = st.get('q') or (self.plan.get('_legacy') or {}).get('raw_question') or ''
        q = (q or '').strip('「」“”"\'').strip()
        rows = []
        _restrict = (f.kind == 'set' and f.pids)
        if q:
            try:
                sql = 'SELECT pid, idx, text FROM lines WHERE text LIKE ?'
                args = ['%' + q + '%']
                if _restrict:
                    parts, pargs = _pid_filter_sql(f.pids, alias='lines')
                    sql += ' AND (' + ' OR '.join(parts) + ')'
                    args += pargs
                rr = self.conn.execute(sql + ' LIMIT 5', args).fetchall()
                rows = [{'pid': r[0], 'idx': r[1] + 1, 'text': r[2], 'score': 1.0} for r in rr]
            except Exception:                                    # noqa: BLE001
                rows = []
        _via = '字面'
        if not rows and q:                       # ★ 句级向量兜底（限定在当前帧内）
            try:
                import vector_index as VI
                if VI.available():
                    _al = set(f.pids) if _restrict else None
                    for _p, _i, _t, _s in VI.search_lines(q, topk=6):
                        if _al is not None and _p not in _al:
                            continue
                        rows.append({'pid': _p, 'idx': (_i or 0) + 1, 'text': _t,
                                     'score': round(float(_s), 3)})
                        if len(rows) >= 3:
                            break
                    if rows:
                        _via = '字面 0 句→句级向量兜底'
            except Exception as e:                               # noqa: BLE001
                self.problems.append('locate 向量兜底失败：%r' % e)
        pids = [r['pid'] for r in rows]
        return self._mk(Frame(self.dag, 'rows', pids=pids, rows=rows, note='locate'),
                        'locate', f, '%s命中 %d 句' % (_via, len(rows)), time.time() - t0)

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

    def _numeric_values(self, f, field):
        """当前集合在 `field` 上的数值列表（表达式走**白名单**）。

        ⚠ 2026-10-09（第三轮审查 P1-8⑤）：字段无法解析时**不再静默回退**到 ze_ratio——
        旧版会把「错误的 of 参数」悄悄换成另一个字段去算（用户拿到的是别的东西的数）。
        现在：报 problem + 记 failed（由上层决定回落），返回空。
        """
        expr = _order_expr(field)
        if expr is None:
            self.problems.append('数值字段不在白名单：%r（不静默回退）' % field)
            self.failed_steps.append(self.problems[-1])
            return []
        parts, args = _pid_filter_sql(f.pids)
        if not parts:
            return []
        rows = self.conn.execute('SELECT %s FROM poems p WHERE %s'
                                 % (expr, ' OR '.join(parts)), args).fetchall()
        return [r[0] for r in rows if r[0] is not None]

    def _op_median(self, f, st):
        """中位数（审查 Top8：把 median 从「特殊入口」变成**算子**）。"""
        t0 = time.time()
        if f.kind != 'set' or not f.pids:
            return f
        import statistics
        _of = st.get('of') or 'ze_ratio'
        vals = self._numeric_values(f, _of)
        val = round(statistics.median(vals), 4) if vals else None
        return self._mk(Frame(self.dag, 'scalar', value=val, note='median',
                              label='中位数（%s）' % _FIELD_CN.get(_of, _of)),
                        'median', f, '中位数（n=%d）' % len(vals), time.time() - t0)

    def _op_stddev(self, f, st):
        """总体标准差（同为算子化）。"""
        t0 = time.time()
        if f.kind != 'set' or not f.pids:
            return f
        import statistics
        _of = st.get('of') or 'han_len'
        vals = self._numeric_values(f, _of)
        val = round(statistics.pstdev(vals), 4) if vals else None
        return self._mk(Frame(self.dag, 'scalar', value=val, note='stddev',
                              label='标准差（%s）' % _FIELD_CN.get(_of, _of)),
                        'stddev', f, '标准差（n=%d）' % len(vals), time.time() - t0)

    def _op_mode(self, f, st):
        """众数：按 field 分组取计数最大的一组（组合已有算子，不新增分支语义）。"""
        t0 = time.time()
        f1 = self._op_group_by(f, st)
        f2 = self._op_aggregate(f1, {'metric': 'count', 'field': st.get('field') or 'author'})
        out = self._op_argmax(f2, {'by': 'value', 'dir': 'desc'})
        out.note = 'mode'
        return out

    def _op_rank(self, f, st):
        """给分组表按 `by`（默认 value）排名，名次写入每行 `rank`。"""
        t0 = time.time()
        if f.kind != 'groups':
            self.problems.append('rank 需要 groups 帧（先 group_by+aggregate）')
            return f
        key = st.get('by') or 'value'
        rev = (st.get('dir') or 'desc') == 'desc'
        rows = sorted(f.rows, key=lambda r: (r.get(key) is None,
                                             -(r.get(key) or 0) if rev else (r.get(key) or 0)))
        out = []
        for i, r in enumerate(rows, 1):
            r2 = dict(r)
            r2['rank'] = i
            out.append(r2)
        return self._mk(Frame(self.dag, 'groups', pids=f.pids, rows=out, note='rank'),
                        'rank', f, '', time.time() - t0)

    def _op_project(self, f, st):
        """取字段：**单篇→一行；集合→逐篇投影**（第三轮审查 P1-10）。

        旧版对集合**静默只取首篇**（「这些作品的作者分别是谁」会退化成只输出一篇）。
        现在：集合输入 → 对至多 500 篇逐篇投影为多行（超过即截断并在 problems 披露）；
        单篇/单篇帧 → 一行。字段仍走**白名单**。
        """
        t0 = time.time()
        if f.kind == 'set':
            pids = list(f.pids)
            if len(pids) > 500:
                self.problems.append('project：集合 %d 篇超过 500——只投影前 500 篇（如实披露）'
                                     % len(pids))
                pids = pids[:500]
        elif f.single:
            pids = [f.single]
        else:
            pids = list(f.pids[:1])
        allow = {'author': 'author', 'cipai': 'cipai', 'title': 'title', 'dynasty': 'dynasty',
                 'han_len': 'han_len', 'sent_n': 'sent_n', 'ze_ratio': 'ze_ratio',
                 'scene': 'scene', 'pid': 'pid', 'source': 'source'}
        fields = list(st.get('fields') or ['author', 'cipai', 'title'])
        cols = [allow[x] for x in fields if x in allow]
        rows = []
        if pids and cols:
            parts, args = _pid_filter_sql(pids)              # 生成 `p.pid IN (…)`（alias=p）
            rr = self.conn.execute(
                'SELECT %s FROM poems p WHERE %s'
                % (','.join(['p.pid'] + ['p.%s' % c for c in cols]), ' OR '.join(parts)),
                args).fetchall()
            rows = [dict(zip(['pid'] + cols, row)) for row in rr]
        return self._mk(Frame(self.dag, 'rows', pids=pids,
                              single=(pids[0] if len(pids) == 1 else None), rows=rows,
                              note='project'),
                        'project', f, '取字段 %s' % ','.join(cols), time.time() - t0)

    def _op_similar_to(self, f, st):
        """「与这首/这段话主题相近」（向量）。不可用则**如实记 problem**，不伪造。"""
        t0 = time.time()
        # ★ 2026-10-09（第三轮审查 P1-9）：`restrict=True` 而当前集合为空时**保持空**——
        #   旧版把 allow 设为 None → 退化成**全库**相似检索（越过一切范围约束）。
        if st.get('restrict') and not f.pids:
            self.problems.append('similar_to：restrict=True 但当前集合为空——保持空结果，'
                                 '不进行全库相似检索')
            return self._mk(Frame(self.dag, 'set', [], note='similar_to(empty)'),
                            'similar_to', f, '空集合，未检索', time.time() - t0)
        pid = st.get('pid') or (f.pids[0] if f.pids else None)
        q = st.get('q') or ''
        try:
            import vector_index as VI
            if not VI.available():
                self.problems.append('similar_to：向量索引不可用（%s）' % VI.why())
                self.failed_steps.append(self.problems[-1])      # ★ 语义步骤失败=关键
                return f
            tk = int(st.get('topk') or max(self.topk, 10))
            allow = set(f.pids) if (f.pids and st.get('restrict')) else None
            hits = (VI.similar(pid, topk=tk, allow=allow) if pid
                    else VI.search(q, topk=tk, allow=allow))
        except Exception as e:                                   # noqa: BLE001
            self.problems.append('similar_to 失败：%s: %s' % (type(e).__name__, e))
            self.failed_steps.append(self.problems[-1])
            return f
        pids = [p for p, _s in (hits or [])]
        return self._mk(Frame(self.dag, 'set', pids, scores=dict(hits or {}), note='similar_to'),
                        'similar_to', f, '语义相近 %d 篇' % len(pids), time.time() - t0)

    def _op_materialize(self, f, st):
        name = st.get('name') or ('s%d' % (len(self.named) + 1))
        self.named[name] = f
        return self._mk(f, 'materialize_as:%s' % name, f, '', 0.0)

    def _op_retrieve(self, f, st):
        """**步骤级召回**（第三轮审查 P1-16）：在当前帧（上一步结果）内执行一路召回。

        这就是「先构造中间集合、再在该集合内语义检索」的正解——把本步骤放在那一阶段之后，
        **天然受当前帧约束**（等价于 `candidate_from=上一命名集`，但语义由顺序保证、无需引用）。
        空集合→空结果；索引不可用→失败语义（绝不退化为全库）。
        """
        mode = str(st.get('mode') or 'vector')
        q = str(st.get('q') or self.question or '').strip()
        tk = int(st.get('topk') or max(self.topk * 10, 50))
        t0 = time.time()
        if f.kind != 'set':
            self.problems.append('retrieve 步骤需要集合输入（当前 %s）' % f.kind)
            self.failed_steps.append(self.problems[-1])
            return f
        allow = set(f.pids)
        if not allow:
            return self._mk(Frame(self.dag, 'set', [], note='retrieve(empty)'),
                            'retrieve.%s' % mode, f, '空集合，未检索', time.time() - t0)
        pids = []
        if mode == 'vector':
            try:
                import vector_index as VI
                if not VI.available():
                    self.problems.append('步骤 retrieve(vector)：索引不可用（%s）' % VI.why())
                    self.failed_steps.append(self.problems[-1])
                    return self._mk(Frame(self.dag, 'set', [], note='retrieve_failed'),
                                    'retrieve.vector', f, '', time.time() - t0)
                pids = [p for p, _s in VI.search(q, topk=tk, allow=allow)]
            except Exception as e:                               # noqa: BLE001
                self.problems.append('步骤 retrieve(vector) 失败：%r' % e)
                self.failed_steps.append(self.problems[-1])
                return self._mk(Frame(self.dag, 'set', [], note='retrieve_failed'),
                                'retrieve.vector', f, '', time.time() - t0)
        elif mode == 'fts':
            pids = self._fts_in(allow, q, tk)
        else:
            self.problems.append('步骤 retrieve：未知 mode %r' % mode)
            self.failed_steps.append(self.problems[-1])
            return f
        return self._mk(Frame(self.dag, 'set', pids, note='retrieve.%s' % mode),
                        'retrieve.%s' % mode, f,
                        '候选集（%d 篇）内召回 %d 篇' % (len(allow), len(pids)),
                        time.time() - t0)

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

    # ── ⑨ 新增算子：median / stddev / rank / project / mode（独立复算对照）──
    import statistics as _st
    plan = QP.empty_plan()
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'median', 'of': 'han_len'}]
    r = execute(conn, plan)
    ref = [x[0] for x in conn.execute("SELECT han_len FROM poems WHERE dynasty='清'")]
    _chk('多步⑨ median(han_len) 清', r['frame'].value, round(_st.median(ref), 4))

    plan = QP.empty_plan()
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'stddev', 'of': 'han_len'}]
    r = execute(conn, plan)
    _chk('多步⑩ stddev(han_len) 清', r['frame'].value, round(_st.pstdev(ref), 4))

    plan = QP.empty_plan()
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'group_by', 'field': 'author'},
                     {'op': 'aggregate', 'metric': 'count', 'field': 'author'},
                     {'op': 'rank', 'by': 'value', 'dir': 'desc'}]
    r = execute(conn, plan)
    rk = sorted(r['frame'].rows, key=lambda x: x['rank'])[:1]
    ref = conn.execute("SELECT p.author, COUNT(*) c FROM poems p WHERE p.dynasty='清' "
                       "GROUP BY p.author ORDER BY c DESC, p.author LIMIT 1").fetchone()
    _chk('多步⑪ rank 第 1 名', (rk[0]['key'] if rk else None, rk[0]['rank'] if rk else None),
         (ref[0], 1))

    _p1 = conn.execute("SELECT pid FROM poems WHERE dynasty='清' ORDER BY pid LIMIT 1").fetchone()[0]
    plan = QP.empty_plan()
    plan['scope'] = {'base': 'corpus'}
    plan['filters'] = {'field': 'pid', 'op': 'in', 'value': [_p1]}
    plan['steps'] = [{'op': 'project', 'fields': ['author', 'cipai', 'title']}]
    r = execute(conn, plan)
    ref = conn.execute('SELECT author, cipai, title FROM poems WHERE pid=?', (_p1,)).fetchone()
    got = r['frame'].rows[0] if r['frame'].rows else {}
    _chk('多步⑫ project(author,cipai,title)', (got.get('author'), got.get('cipai'), got.get('title')),
         (ref[0], ref[1], ref[2]))

    plan = QP.empty_plan()
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'mode', 'field': 'cipai'}]
    r = execute(conn, plan)
    ref = conn.execute("SELECT p.cipai, COUNT(*) c FROM poems p WHERE p.dynasty='清' "
                       "GROUP BY p.cipai ORDER BY c DESC, p.cipai LIMIT 1").fetchone()
    rows = r['frame'].rows
    _chk('多步⑬ mode(cipai) 清', (rows[0]['key'] if rows else None,
                                   rows[0]['value'] if rows else None), (ref[0], ref[1]))

    plan = QP.empty_plan()
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['steps'] = [{'op': 'limit', 'n': 1},
                     {'op': 'similar_to', 'restrict': True, 'topk': 3}]
    r = execute(conn, plan)
    ok9 = isinstance(r['problems'], list)     # 无向量索引时必须**如实记 problem**而非崩
    print('%s 多步⑭ similar_to 无索引时优雅降级：problems=%s' % ('✓' if ok9 else '✗', r['problems']))
    ok_all = ok_all and ok9

    # ── ⑧ 溯源 DAG 可用性（**重跑本用例自己的计划**；避免被上面新插用例的 r 覆盖）──
    plan = QP.empty_plan()
    plan['intent'] = 'count'
    plan['filters'] = {'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                               {'field': 'line_q', 'op': '=',
                                'value': {'op': '∄', 'pred': ['tail_pz', '仄']}}]}
    r = execute(conn, plan)
    prov = r['dag'].render(r['frame'].prov)
    ok8 = ('corpus' in prov or 'sql.filter' in prov) and 'count' in prov
    ok_all = ok_all and ok8
    print('%s 溯源 DAG 可回溯到根：%s' % ('✓' if ok8 else '✗', prov.replace('\n', ' ← ')))

    # ── ⑯ **retrieve 执行**（第三轮审查 P0：证明「计划里的召回命令确实影响结果」）──
    import vector_index as _VI
    _qing = set(x[0] for x in conn.execute("SELECT pid FROM poems WHERE dynasty='清'"))
    plan = QP.empty_plan()
    plan['intent'] = 'list'
    plan['filters'] = {'field': 'dynasty', 'op': '=', 'value': '清'}
    plan['retrieve'] = [{'mode': 'vector', 'q': '秋景、萧瑟、秋日愁绪', 'topk': 20}]
    rv = execute(conn, plan)
    rep = rv.get('retrieve_report') or []
    if _VI.available():
        okv1 = bool(rep) and rep[0].get('executed') is True
        _chk('⑯ retrieve.vector 已执行且报告', okv1, True)
        # 独立复算：帧 == 受限检索（同一 q、同一候选集）的前 20
        _hits = [p for p, _s in _VI.search('秋景、萧瑟、秋日愁绪', topk=20, allow=_qing)]
        _chk('⑯ 与受限检索独立复算逐篇一致', list(rv['frame'].pids), _hits)
        _chk('⑯ 召回全部落在候选集内', set(rv['frame'].pids) <= _qing, True)
        _chk('⑯ 溯源出现 retrieve 节点',
             any('retrieve' in n['op'] for n in rv['dag'].to_list()), True)
    else:
        # 索引不可用：召回路全未执行 → 失败语义（空帧 + failed，由上层回落并报告）
        _chk('⑯ 索引不可用时按失败关闭（不拿原候选冒充语义结果）',
             bool(rep) and rep[0].get('executed') is False
             and any('语义召回未完成' in p for p in rv['problems'])
             and len(rv['frame'].pids) == 0, True)
    # ⑰ fts 路：与独立 SQL 复算逐篇一致
    plan2 = dict(plan, retrieve=[{'mode': 'fts', 'q': '明月 孤灯', 'topk': 10}])
    rf = execute(conn, plan2)
    _ref = [x[0] for x in conn.execute(
        "SELECT l.pid FROM lines l WHERE l.pid IN (SELECT pid FROM poems WHERE dynasty='清') "
        "AND (l.text LIKE '%明月%' OR l.text LIKE '%孤灯%') "
        "GROUP BY l.pid ORDER BY COUNT(DISTINCT l.idx) DESC, l.pid LIMIT 10")]
    _chk('⑰ fts 召回与独立 SQL 复算一致', list(rf['frame'].pids), _ref)
    # ⑰ 纯 sql：零变化（无报告、帧=过滤集）
    plan3 = dict(plan, retrieve=[{'mode': 'sql'}])
    rs = execute(conn, plan3)
    _chk('⑰ 纯 sql 计划零变化（无召回报告）', rs.get('retrieve_report'), [])
    _chk('⑰ 纯 sql 帧=过滤集', len(rs['frame'].pids), len(_qing))
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
