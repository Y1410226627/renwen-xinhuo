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

━━ 第二轮审查（GPT）指出的**契约漂移**与本轮的立法方式 ━━
==================================================================
GPT 第二轮原文：

> Planner 的 Prompt 告诉 LLM「scene/consist/tail_pz/pz_exact/tail_each/line_q/parity 都可以
> 放进 filters」，但 `queryplan._LEAF_FIELDS` 实际只登记 14 个 → LLM 正确理解被判 unsupported
> → planner 返回 None → 回落旧规则。
> 根源：**Prompt Schema ≠ IR Schema ≠ Validator Schema**。

本轮的解法不是「手动把缺的字段补进白名单」（那样下一轮还会漂移），而是**消灭三份 schema**：

    LEAF_SCHEMA（本模块唯一真源表）
        ├─→ _LEAF_FIELDS / _LEAF_OPS      ····· 白名单校验（`compile_filters` 的前哨）
        ├─→ check_schema_alignment()      ····· 双向对齐检查（编译 <-> 登记，漏登记即报错）
        ├─→ plan_schema_prompt()          ····· Planner 的 Prompt **由它生成**（不再手写）
        └─→ plan_exec.py / 前端 explain   ····· 运行期展示同一份说明

`check_schema_alignment()` 是本机制的牙齿：它解析 `retrieve._leaf_sql` 实际接受的全部字段，
与本表键集合求差，**任何一侧多出来都报错**。从此不可能再出现
「Prompt 说支持、Validator 说不认识」。

兼容铁律（生命线）
==================
`QuerySpec.filters_tree` 默认 `None`；`retrieve._sql()` 只在它**非空**时才走本模块编译，
否则走原路径**逐字不变** —— 默认环境下 1000 题**零回归**。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import retrieve                                                # noqa: E402

PLAN_VERSION = 1

# 把增删「过滤字段」的流程固化为「只改一处」：改了 LEAF_SCHEMA → Prompt / Validator /
# Executor / 文档同时生效；漏改任何一环都不可能，因为 check_schema_alignment() 会报错。
PLAN_SCHEMA_VERSION = 2

INTENTS = ('list', 'count', 'extreme', 'aggregate', 'extract', 'pair', 'compare',
           'similarity', 'locate')

_NUM_OPS = ('=', '!=', '>', '>=', '<', '<=', 'between')
_SET_OPS = ('=', '!=', 'in', 'not_in')
_TEXT_OPS = ('contains',)


# ================================================================ 叶子字段：唯一真源表
# 每个条目：
#   col     SQL 列/表达式（**仅作文档与对齐**；真正的 SQL 由 `retrieve._leaf_sql` 产出，
#           本模块不重复实现——那正是审查说的「不要两套编译器」）
#   kind    'str' | 'num' | 'set' | 'struct'（值形态；决定 Prompt 里的例子怎么写）
#   ops     允许算子（子集；compile 之前做白名单）
#   level   'meta'（元数据）| 'poem'（篇级派生量）| 'line'（句级存在/量化）
#   desc    中文说明（**直接进 Prompt**，所以要给 LLM 看得懂的话）
#   eg      示例值（直接进 Prompt）
LEAF_SCHEMA = {
    # ---------------- 元数据 ----------------
    'dynasty':   dict(col='p.dynasty', kind='str', ops=_SET_OPS, level='meta',
                      desc='朝代：清 / 宋 / 元', eg='清'),
    'author':    dict(col='p.author', kind='str', ops=_SET_OPS, level='meta',
                      desc='词人（作者）姓名', eg='纳兰性德'),
    'cipai':     dict(col='p.cipai', kind='str', ops=_SET_OPS, level='meta',
                      desc='词牌名', eg='临江仙'),
    'title':     dict(col='p.title', kind='str', ops=_SET_OPS + ('contains',), level='meta',
                      desc='题名（词牌后面那一段题目，如「清明同诸子集原白斋中」）',
                      eg='清明同诸子集原白斋中'),
    'pid':       dict(col='p.pid', kind='str', ops=('=', 'in'), level='meta',
                      desc='篇号集合（上一轮结果集即由此表达）', eg=[1, 2, 3]),
    'source':    dict(col='p.source', kind='str', ops=_SET_OPS, level='meta',
                      desc='语料来源标记', eg='A'),

    # ---------------- 篇级派生量（数值） ----------------
    'han_len':     dict(col='p.han_len', kind='num', ops=_NUM_OPS, level='poem',
                        desc='全篇汉字数（不计标点）', eg=56),
    'sent_n':      dict(col='p.sent_n', kind='num', ops=_NUM_OPS, level='poem',
                        desc='句数（按 。？！ 切）', eg=8),
    'ze_ratio':    dict(col='p.ze_ratio', kind='num', ops=_NUM_OPS, level='poem',
                        desc='全篇仄声占比（百分点，如 51.3）', eg=45.0),
    'change':      dict(col='p.change', kind='num', ops=_NUM_OPS, level='poem',
                        desc='前后段仄声占比之差（百分点，有符号）', eg=3.5),
    'abs_change':  dict(col='ABS(p.change)', kind='num', ops=_NUM_OPS, level='poem',
                        desc='前后段仄声占比之差的绝对值（问「变化幅度」时用这个）', eg=3.5),
    'threshold':   dict(col='p.threshold', kind='num', ops=_NUM_OPS, level='poem',
                        desc='前后段分界阈值；不确定就不要用这个字段', eg=0.0),
    'longest_len': dict(col='p.longest_len', kind='num', ops=_NUM_OPS, level='poem',
                        desc='最长句的汉字数', eg=9),
    'longest_seq': dict(col='p.longest_seq', kind='num', ops=_NUM_OPS, level='poem',
                        desc='最长连续同声串的长度', eg=4),
    'f_ratio':     dict(col='p.f_ratio', kind='num', ops=_NUM_OPS, level='poem',
                        desc='前段仄声占比（百分点）', eg=48.0),
    'b_ratio':     dict(col='p.b_ratio', kind='num', ops=_NUM_OPS, level='poem',
                        desc='后段仄声占比（百分点）', eg=52.0),

    # ---------------- 篇级分类 / 派生 ----------------
    'scene':   dict(col='p.scene', kind='str', ops=_SET_OPS, level='poem',
                    desc='声情转向：后段上升 / 后段下降 / 前后持平', eg='后段上升'),
    'consist': dict(col='(derived)', kind='str', ops=('=',), level='poem',
                    desc='一致性矛盾：声情标注为某值、但实测前后段相反。取值同样是'
                         '「后段上升 / 后段下降 / 前后持平」，命中「标注与实测相反」的那些篇',
                    eg='后段上升'),

    # ---------------- 句级（存在 / 量化） ----------------
    'lines.text': dict(col='lines.text', kind='str', ops=_TEXT_OPS, level='line',
                       desc='存在一句的正文包含该子串（如含「月」）', eg='月'),
    'lines.tail': dict(col='l.tail', kind='set', ops=_SET_OPS, level='line',
                       desc='存在一句的句脚字属于该集合（多值取并集）', eg=['愁', '秋']),
    'tail_pz':    dict(col='l.pz 末位', kind='str', ops=_SET_OPS, level='line',
                       desc='存在一句的句脚字平仄为平 / 仄', eg='仄'),
    'pz':         dict(col='l.pz', kind='str', ops=_TEXT_OPS, level='line',
                       desc='存在一句的平仄串包含该模式（? 或 ？ 表示任意一位）', eg='仄仄平平'),
    'pz_exact':   dict(col='l.pz', kind='str', ops=('=',), level='line',
                       desc='存在一句的平仄串全等于该串（不是子串）', eg='仄仄平平仄'),
    'tail_each':  dict(col='l.tail', kind='set', ops=('in',), level='line',
                       desc='篇内交集：集合里每一个句脚字都必须各自出现在某一句'
                            '（与「存在一句」语义不同）',
                       eg=['愁', '秋']),
    'line_q':     dict(col='lines', kind='struct', ops=('=',), level='line',
                       desc='句级量化算子。value = {"op":..., "pred":[<谓词种类>, <值>], ...}；'
                            'op ∈ ∃(存在一句) / ∀(每一句) / ∄(没有任何一句) / ≥k(至少k句) / '
                            '=k(恰好k句) / 占比≥p / 条数∈[a,b]；op 为 ≥k、=k 时还要给 "k"；'
                            '为 占比≥p 时给 "ratio"；为 条数∈[a,b] 时给 "ka","kb"。'
                            'pred 种类 ∈ tail(句脚字) / tail_any(句脚字集合) / tail_pz(句脚平仄) / '
                            'pz(平仄串模式) / pz_exact(平仄串全等) / len(句长闭区间) / '
                            'parity(句位奇偶, 0=第1/3/5句)',
                       eg={'op': '∄', 'pred': ['tail_pz', '仄']}),
    'parity':     dict(col='l.idx % 2', kind='num', ops=('=',), level='line',
                       desc='句位奇偶：0=第1/3/5…句（奇数句位），1=第2/4/6…句（偶数句位）', eg=0),
}

# 兼容导出（旧代码按名字取；**由 LEAF_SCHEMA 派生**，不再是第二份手写表）
_LEAF_FIELDS = dict((k, (v['col'], v['kind'])) for k, v in LEAF_SCHEMA.items())
_LEAF_OPS = ('=', '!=', 'in', 'not_in', '>', '>=', '<', '<=', 'between', 'contains')


def leaf_help(field):
    """字段的中文说明（供前端 explain、Planner 报错、文档生成共用同一份）。"""
    d = LEAF_SCHEMA.get(field)
    if not d:
        return None
    return {'field': field, 'desc': d['desc'], 'ops': list(d['ops']),
            'kind': d['kind'], 'level': d['level'], 'example': d['eg']}


# ================================================================ 步骤算子 / 召回模式：同一份表
# 第二轮审查要求 executor 算子也必须是 schema 的一部分（否则 Executor 与 Prompt 又会漂移）。
STEP_OPS = {
    'filter':          '按 filters 布尔树收窄当前结果集',
    'sort':            '排序；keys=[{"by":<指标>,"dir":"desc"|"asc"}]（多键依次生效）',
    'limit':           '取前 n 个（常与 sort 连用取极值）',
    'group_by':        '按某字段分组（author / cipai / dynasty / scene / sent_n …）',
    'aggregate':       '分组后聚合：metric ∈ ' + ' / '.join(('count', 'sum', 'avg', 'min', 'max', 'ratio_ze')),
    'argmax':          '取度量最大 / 最小的那一组（sort+limit 的语义糖）',
    'count':           '计数（结果是一个数，不是集合）',
    'extract':         '篇内取值：{"sent":N,"pos":M,"unit":"char"|"line"}',
    'pair':            '两两配对（找出满足关系的篇对）',
    'locate':          '反查出处（某句出自哪首）',
    'intersect':       '与另一个结果集求交（「这些里面哪些还…」）',
    'union':           '与另一个结果集求并',
    'diff':            '与另一个结果集求差（「不是…的那些」）',
    'anchor':          '锚定到会话里的单篇 / 集合（来自 context.resolve）',
    'annotate':        '给结果集挂一个派生标注（如 via=vector 的语义相关度）',
    'materialize_as':  '把当前结果集命名保存（供后续 steps 引用）',
}

RETRIEVE_MODES = {
    'sql':    '精确 SQL 过滤（计数 / 区间 / 作者 / 词牌等一切可精确判定的条件走这里）',
    'fts':    '全文短语检索（字面）：{"mode":"fts","q":"香冷金猊","field":"lines.text"}',
    'vector': '向量语义检索（写秋景 / 离愁这类词面不重合的主题）：'
              '{"mode":"vector","q":"写秋景","topk":50,"candidate_from":"s1"}；'
              '"candidate_from" 指向某个已命名结果集时，只在该集合内做向量检索',
}

AGG_METRICS = ('count', 'sum', 'avg', 'min', 'max', 'ratio_ze')


# ------------------------------------------------------------------ 布尔树编译
def _leaf_sql(field, op, value):
    """叶子条件 → (sql 片段, args)。**委托** `retrieve._leaf_sql`（单一真源）。

    保留本函数只为向后兼容旧调用方；语义与 `retrieve._leaf_sql` 完全等价。
    """
    return retrieve._leaf_sql({'field': field, 'op': op, 'value': value})


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
    """遍历布尔树，收集「本模块 `LEAF_SCHEMA` 不认识」的叶子（供白名单校验）。"""
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
        if f not in LEAF_SCHEMA:
            out.append('未知字段 %s' % f)
        elif f != 'line_q' and op not in LEAF_SCHEMA[f]['ops']:
            # line_q 的 op 是它自己的算子空间（∃/∀/…），不走通用算子表
            out.append('%s 不支持算子 %s' % (f, op))
    return out


# ------------------------------------------------------------------ Plan <-> QuerySpec
def empty_plan():
    """空 Plan（合法、无限制；供 Planner 与 tests 构造基准）。"""
    return {
        'version': PLAN_VERSION,
        'intent': 'list',
        'scope': {'base': 'corpus', 'ctx': None},
        'filters': {},
        'retrieve': [],
        'steps': [],
        'operation': None,
        'context': {'refs': [], 'resolve': None},
        'evidence': {'mode': 'rows', 'bind_numbers': True},
        '_legacy': {},
    }


def to_plan(spec):
    """QuerySpec → Plan（**无损**；无法映射的进 `_legacy`，不静默丢）。"""
    ast = _ast_of(spec)
    plan = empty_plan()
    plan['intent'] = (ast.get('intent') or {}).get('type', 'list')
    it = ast.get('intent') or {}
    if it.get('type') == 'extreme':
        plan['operation'] = {'kind': 'extreme', 'target': {
            'metric': it.get('metric'), 'dir': it.get('direction') or 'desc'},
            'label': it.get('label'), 'src': it.get('src'),
            'extreme': it.get('extreme'), 'col': it.get('col')}
    elif it.get('type') in ('agg', 'pair'):
        plan['operation'] = {'kind': it['type'], 'target': it}

    # ★ 把筛选字段填进 filters 布尔树。**句级复杂条件（line_q / tail_each / pz_exact /
    #   consist / scene）也一并进树**——第二轮审查后 `retrieve._leaf_sql` 已支持它们，
    #   不再需要 legacy 兜底；只有「编译真的报错」的那片才降级到 `_legacy.legacy_filters`。
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
        if f.get('scope') == 'poem':
            _flt.append({'field': f['field'], 'op': f['op'], 'value': f['value']})
        elif f.get('scope') == 'line':
            _flt.append(_line_leaf(f))
    if len(_flt) > 1:
        plan['filters'] = {'and': _flt}
    elif _flt:
        plan['filters'] = _flt[0]

    # ── 编译探活：把编译不了的叶子挑出来，剩下的一律留在布尔树里 ──
    _good, _bad = [], []
    for node in _flt:
        try:
            compile_filters(None, node)
            _good.append(node)
        except Exception:                                        # noqa: BLE001
            _bad.append(node)
    if _bad:
        plan['filters'] = ({'and': _good} if len(_good) > 1 else (_good[0] if _good else {}))
        _legacy_extra = {'keep_legacy_filters': True, 'legacy_filters': _bad}
    else:
        _legacy_extra = {}

    # 多轮范围：ctx_pids 非空 → scope.base = prev_result（Plan 层表达「那里面」）
    _ctx = list(getattr(spec, 'ctx_pids', None) or ast.get('extras', {}).get('ctx_pids') or [])
    if _ctx:
        plan['scope'] = {'base': 'prev_result', 'ctx': _ctx}

    sem = ast.get('semantic') or {}
    terms = list(sem.get('terms') or [])
    if terms:
        plan['retrieve'].append({'mode': 'vector', 'q': ' '.join(terms), 'topk': 50})

    # ⚠ 2026-10-08 修（GPT 第二轮 §11 的实际 bug）：旧代码先写
    #   `plan['_legacy']['keep_legacy_filters'] = True`，**后面又整体赋值** `plan['_legacy'] = {...}`
    #   → 这两项被悄悄覆盖，于是「注释宣称不静默丢」实际丢了。现改为**先拼全、一次性赋值**。
    _legacy = {
        'semantic_terms': terms,
        'keywords': list(sem.get('keywords') or []),
        'unparsed': list(ast.get('unparsed') or []),
        'source': (ast.get('extras') or {}).get('source'),
        'raw_question': (ast.get('extras') or {}).get('raw_question'),
        'change_abs': (ast.get('extras') or {}).get('change_abs', False),
        'unsupported': (ast.get('extras') or {}).get('unsupported'),
        'extract': getattr(spec, 'extract', None),
        'disp_group': (ast.get('extras') or {}).get('disp_group'),
        'cleared_names': list((ast.get('extras') or {}).get('cleared_names') or []),
    }
    _legacy.update(_legacy_extra)          # 合并，而非覆盖
    plan['_legacy'] = _legacy
    return plan


def _line_leaf(f):
    """`queryast` 的行级 AST 节点 → Plan 叶子（统一进布尔树，不再走 legacy）。"""
    tag, pred = f.get('tag'), f.get('predicate') or {}
    if tag == 'tail_any':
        return {'field': 'lines.tail', 'op': 'in', 'value': list(pred.get('value') or [])}
    if tag == 'tail_pz':
        return {'field': 'tail_pz', 'op': '=', 'value': pred.get('value')}
    if tag == 'pz':
        return {'field': 'pz', 'op': 'contains', 'value': pred.get('value')}
    if tag == 'pz_exact':
        return {'field': 'pz_exact', 'op': '=', 'value': pred.get('value')}
    if tag == 'tail_each':
        return {'field': 'tail_each', 'op': 'in', 'value': list(pred.get('value') or [])}
    if tag == 'parity':
        return {'field': 'parity', 'op': '=', 'value': pred.get('value')}
    if tag == 'line_q':
        return {'field': 'line_q', 'op': '=', 'value': _line_q_value(f)}
    return {'field': 'lines.text', 'op': 'contains', 'value': str(pred.get('value') or '')}


def _line_q_value(f):
    """AST 的 line_q 节点 → `retrieve._line_q_where` 认识的结构（算子 + 谓词 + 参数）。"""
    op = f.get('quantifier') or '∃'
    op = {'exists': '∃', 'all': '∀', 'none': '∄'}.get(op, op)
    d = {'op': op, 'pred': _ast_pred_to_pred(f.get('predicate') or {})}
    cnt = f.get('count') or {}
    if cnt and cnt.get('value') is not None:
        d['k'] = cnt.get('value')
        d['op'] = '≥k' if cnt.get('op') == '>=' else '=k'
    if f.get('ratio') is not None:
        d['ratio'] = f['ratio']
    rg = f.get('range')
    if rg and len(rg) == 2:
        d['ka'], d['kb'] = rg[0], rg[1]
        d['op'] = '条数∈[a,b]'
    return d


def _ast_pred_to_pred(pred):
    """AST 谓词 dict → `_pred_sql` 的 (kind, value) 二元组。

    `queryast` 的 `_pred_from_ast` 是它的逆运算（ приводят AST → pred），保持一致。
    """
    import queryast as _qa
    f, v = pred.get('field'), pred.get('value')
    _direct = ('tail', 'tail_pz', 'pz', 'pz_exact', 'len', 'parity')
    if f in _direct:
        return (f, v)
    if f == 'tail_any':
        return ('tail_any', list(v or []))
    fn = getattr(_qa, '_pred_from_ast', None)
    if callable(fn):
        try:
            return tuple(fn(pred))
        except Exception:                                        # noqa: BLE001
            pass
    return (f, v)


def _ast_of(spec):
    """复用 queryast.to_ast（避免两套表示）。"""
    import queryast as _qa
    return _qa.to_ast(spec)


def spec_to_filters_tree(spec):
    """把 QuerySpec 的筛选字段转成布尔树（AND 根；供 `_sql` 消费）。"""
    return to_plan(spec).get('filters') or None


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
    # 复杂过滤的**还原**（to_plan 里编译失败而降级到 `_legacy.legacy_filters` 的那些）：
    # 第二轮之前这里只 setattr 一个标记，等于丢失；现在真正写回 spec 字段。
    for node in ((plan.get('_legacy') or {}).get('legacy_filters') or []):
        _restore_complex(spec, node)
    it = plan.get('operation') or {}
    if it.get('kind') == 'extreme':
        t = it.get('target') or {}
        spec.order_by = t.get('metric')
        spec.order_dir = t.get('dir') or 'desc'
        spec.extreme = it.get('extreme') or ('max' if (t.get('dir') or 'desc') == 'desc' else 'min')
        spec.order_col = it.get('col')
        spec.order_label = it.get('label')
        spec.order_src = it.get('src')
    elif it.get('kind') == 'agg':
        spec.agg = (it.get('target') or {}).get('agg')
    elif it.get('kind') == 'pair':
        spec.pair = (it.get('target') or {}).get('pair')
        spec.pair_label = (it.get('target') or {}).get('label')
    for k, v in (plan.get('_legacy') or {}).items():
        if k == 'semantic_terms':
            spec.semantic = list(v or [])
        elif k == 'keywords':
            spec.keywords = list(v or [])
        elif k == 'unparsed':
            spec.unparsed = list(v or [])
        elif k in ('legacy_filters', 'keep_legacy_filters'):
            continue                      # 已在上面单独还原 / 仅作标记
        elif k == 'extract':
            spec.extract = v
        else:
            setattr(spec, k, v)
    return retrieve._finalize(spec)


def _restore_complex(spec, node):
    """把「编译不了」的叶子尽力写回 QuerySpec；写不回的挂 `spec.unparsed`（如实披露）。"""
    if not isinstance(node, dict) or 'field' not in node:
        return
    f, v = node.get('field'), node.get('value')
    try:
        if f == 'scene':
            spec.scene = v
        elif f == 'consist':
            spec.consist = v
        elif f == 'tail_pz':
            spec.tail_pz = v
        elif f == 'pz':
            spec.pz = v
        elif f == 'pz_exact':
            spec.pz_exact = v
        elif f == 'tail_each':
            spec.tail_each = list(v or [])
        elif f == 'lines.tail':
            spec.tail_any = list(v if isinstance(v, list) else [v])
        elif f == 'line_q':
            spec.line_q = dict(v or {})
        elif f == 'parity':
            spec.parity = v
        elif f == 'dynasty':
            spec.dynasty_any = list(v if isinstance(v, list) else [v])
        elif f == 'author':
            spec.author_any = list(v if isinstance(v, list) else [v])
        elif f == 'cipai':
            spec.cipai_any = list(v if isinstance(v, list) else [v])
        elif f == 'title':
            spec.title_any = list(v if isinstance(v, list) else [v])
        else:
            import queryast as _qa
            key = _qa._RNG_REV.get((f, node.get('op')))
            if key is not None:
                spec.rng[key] = v
            else:
                spec.unparsed.append('%s=%s' % (f, v))
    except Exception:                                            # noqa: BLE001
        pass


def _apply_leaf_tree(spec, node):
    """把布尔树叶子落到 QuerySpec 槽位；句级 / 复杂叶子留在 `filters_tree` 由 `_sql` 直接消费。"""
    if not isinstance(node, dict):
        return
    for key in ('and', 'or'):
        for c in (node.get(key) or []):
            _apply_leaf_tree(spec, c)
    if 'not' in node:
        # ★ NOT 子树**不能**降维到槽位（降维会把它变成正向条件 → 语义反转），
        #   必须留在 `filters_tree` 让 `_sql` 用 `NOT (...)` 原样编译。
        return
    if 'field' not in node:
        return
    f, v, op = node.get('field'), node.get('value'), node.get('op')
    if f == 'dynasty':
        spec.dynasty_any = list(v) if isinstance(v, list) else [v]
    elif f == 'author':
        spec.author_any = list(v) if isinstance(v, list) else [v]
    elif f == 'cipai':
        spec.cipai_any = list(v) if isinstance(v, list) else [v]
    elif f == 'title':
        spec.title_any = list(v) if isinstance(v, list) else [v]
    elif f == 'lines.tail':
        spec.tail_any = list(v if isinstance(v, list) else [v])
    elif f == 'tail_pz':
        spec.tail_pz = v
    elif f == 'pz':
        spec.pz = v
    elif f == 'pz_exact':
        spec.pz_exact = v
    elif f == 'tail_each':
        spec.tail_each = list(v or [])
    elif f == 'line_q':
        spec.line_q = dict(v or {})
    elif f == 'parity':
        spec.parity = v
    elif f == 'scene':
        spec.scene = v
    elif f == 'consist':
        spec.consist = v
    else:
        import queryast as _qa
        key = _qa._RNG_REV.get((f, op))
        if key is not None:
            spec.rng[key] = v


# ------------------------------------------------------------------ 校验与渲染
def validate(plan, conn, strict=True):
    """Plan 合法性 → (ok, problems)。节点形状 / op 兼容 / 步骤 / 召回 / 库中存在性。"""
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
    for i, st in enumerate(plan.get('steps') or []):
        if not isinstance(st, dict) or st.get('op') not in STEP_OPS:
            problems.append('第 %d 步的算子不认识：%r' % (i + 1, (st or {}).get('op')))
    for r in (plan.get('retrieve') or []):
        if (r or {}).get('mode') not in RETRIEVE_MODES:
            problems.append('未知召回模式：%r' % (r or {}).get('mode'))
    for ag in [s for s in (plan.get('steps') or []) if (s or {}).get('op') == 'aggregate']:
        m = (ag.get('metric') or 'count')
        if m not in AGG_METRICS:
            problems.append('未知聚合指标：%r' % m)
    if strict:
        problems += _entity_check(plan, conn)
    return (not problems), problems


def _entity_check(plan, conn):
    """实体落地校验：**库里没有的作者/词牌/朝代必须如实报**（GPT §25）。

    ⚠ 这里**只报告、不剪枝**：不存在的实体 = 结果集为空，而不是「删掉条件 = 全库」。
    是否降级由调用方（`plan_exec` / `planner`）决定，本函数保证「不会静默变小」。
    """
    out = []
    if conn is None:
        return out
    _seen = {}

    def walk(node):
        if not isinstance(node, dict):
            return
        for key in ('and', 'or'):
            for c in (node.get(key) or []):
                walk(c)
        if 'not' in node:
            walk(node['not'])
        if 'field' not in node:
            return
        f, v = node.get('field'), node.get('value')
        vals = v if isinstance(v, list) else [v]
        if f == 'dynasty':
            have = set(r[0] for r in conn.execute('SELECT DISTINCT dynasty FROM poems'))
            miss = [str(x) for x in vals if x not in have]
            if miss:
                out.append('库中无此朝代：%s' % '、'.join(miss))
        elif f == 'author':
            for x in vals:
                if x not in _seen:
                    _seen[x] = conn.execute('SELECT COUNT(*) FROM poems WHERE author=?',
                                            (x,)).fetchone()[0]
                if _seen[x] == 0:
                    out.append('库中无此词人：%s' % x)
        elif f == 'cipai':
            for x in vals:
                n = conn.execute('SELECT COUNT(*) FROM poems WHERE cipai=?', (x,)).fetchone()[0]
                if n == 0:
                    out.append('库中无此词牌：%s' % x)
        elif f == 'title' and node.get('op') in ('=', 'contains'):
            for x in vals:
                n = conn.execute('SELECT COUNT(*) FROM poems WHERE title LIKE ?',
                                 ('%' + str(x) + '%',)).fetchone()[0]
                if n == 0:
                    out.append('库中无此题名：%s' % x)
    walk(plan.get('filters') or {})
    return out


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
        out.append('  召回   : %s' % '；'.join('%s（q=%r topk=%s）'
                                              % (r.get('mode'), r.get('q'), r.get('topk'))
                                              for r in ret))
    ops = plan.get('steps') or []
    if ops:
        out.append('  步骤   : %s' % ' → '.join(str(o.get('op')) for o in ops))
    op = plan.get('operation')
    if op:
        out.append('  运算   : %s %s' % (op.get('kind'),
                                         json.dumps(op.get('target') or {}, ensure_ascii=False)))
    lg = plan.get('_legacy') or {}
    if lg:
        out.append('  legacy : %s' % json.dumps({k: lg[k] for k in sorted(lg)},
                                                ensure_ascii=False)[:200])
    return '\n'.join(out)


def diff(p1, p2):
    """两个 Plan 的差异行（供意图比较、架构测试、会话调试）。"""
    keys = ('version', 'intent', 'scope', 'filters', 'retrieve', 'steps', 'operation', 'context')
    out = []
    for k in keys:
        a, b = (json.dumps(p1.get(k), ensure_ascii=False, sort_keys=True),
                json.dumps(p2.get(k), ensure_ascii=False, sort_keys=True))
        if a != b:
            if k == 'filters':
                sa = sorted(set(_filter_fields(p1.get('filters'))))
                sb = sorted(set(_filter_fields(p2.get('filters'))))
                out.append('filters 仅左有：%s' % (sorted(set(sa) - set(sb)) or '（无）'))
                out.append('filters 仅右有：%s' % (sorted(set(sb) - set(sa)) or '（无）'))
            else:
                out.append('%s: 左=%s' % (k, a[:160]))
                out.append('%s: 右=%s' % (k, b[:160]))
    return out


def _filter_fields(node, acc=None):
    """收集布尔树里出现的「字段.算子」路径（用于 Plan 差异与覆盖率比较）。"""
    acc = [] if acc is None else acc
    if not isinstance(node, dict):
        return acc
    for key in ('and', 'or'):
        for c in (node.get(key) or []):
            _filter_fields(c, acc)
    if 'not' in node:
        _filter_fields(node['not'], acc)
        return acc
    if 'field' in node:
        acc.append('%s.%s' % (node['field'], node.get('op')))
    return acc


# ------------------------------------------------------------------ 由 schema 生成 Planner Prompt
def plan_schema_prompt():
    """**从 LEAF_SCHEMA / STEP_OPS / RETRIEVE_MODES 现场生成**给 LLM Planner 的字段说明书。

    ★ 这就是第二轮审查 §9 的解药：Planner 不再手写「支持的字段」，而是**引用本模块真源表**。
    `check_schema_alignment()` 保证二者不可能再漂移。
    """
    lines = []
    lines.append('### 过滤字段（filters 叶子）')
    lines.append('布尔节点：{"and":[...]} / {"or":[...]} / {"not":{...}}；')
    lines.append('叶子节点：{"field":"<字段名>","op":"<算子>","value":<值>}。')
    lines.append('字段名必须是下表之一（**不得自创**）：')
    _lv = {'meta': '元数据', 'poem': '篇级量', 'line': '句级'}
    for name, d in LEAF_SCHEMA.items():
        lines.append('- `%s`（%s；算子 %s）\n    %s\n    例：{"field":"%s","op":"%s","value":%s}'
                     % (name, _lv[d['level']], '/'.join(d['ops']), d['desc'],
                        name, d['ops'][0], json.dumps(d['eg'], ensure_ascii=False)))
    lines.append('')
    lines.append('### 步骤算子（steps[].op）')
    for name, desc in STEP_OPS.items():
        lines.append('- `%s`：%s' % (name, desc))
    lines.append('')
    lines.append('### 召回模式（retrieve[].mode）')
    for name, desc in RETRIEVE_MODES.items():
        lines.append('- `%s`：%s' % (name, desc))
    lines.append('')
    lines.append('### 意图（intent）')
    lines.append('必须是之一：%s' % ' / '.join(INTENTS))
    lines.append('')
    lines.append('### 聚合指标（steps[].metric，仅 aggregate 用）')
    lines.append('必须是之一：%s' % ' / '.join(AGG_METRICS))
    return '\n'.join(lines)


# ------------------------------------------------------------------ 自检
def check_schema_alignment():
    """**双向对齐**：本表字段集合 ⟷ `retrieve._leaf_sql` 真正接受的字段集合。

    · 左多（本表登记了编译器不认的）→ 「虚报」；
    · 右多（编译器认了本表没登记的）→ 「漏登记」 —— 这正是第二轮审查抓到的
      line_q / pz_exact 那批 bug 的形态（LLM 可用、却被判 unsupported）。
    """
    import inspect
    src = inspect.getsource(retrieve._leaf_sql)
    accepted = set(re.findall(r"f == '([^']+)'", src))
    for m in re.finditer(r"if f in \(([^)]*)\)\s*:", src):
        accepted |= set(re.findall(r"'([^']+)'", m.group(1)))
    accepted |= set(retrieve._NUM_COL.keys())
    # `{'field': 'X'}` 这种元组/字典形式
    for m in re.finditer(r"\['(\w+)'\s*,\s*'(\w+)'\s*,\s*'(\w+)'\]\s*\[f\]", src):
        accepted |= set(x for x in m.groups() if x in LEAF_SCHEMA)
    accepted.discard('__main__')
    return sorted(set(LEAF_SCHEMA) - accepted), sorted(accepted - set(LEAF_SCHEMA))


def selftest(conn):
    """自检：① schema 双向对齐；② 布尔树编译 == 独立复算；③ 往返等价（含复杂句级条件）。"""
    ok_all = True

    # ⓪ schema 对齐（本轮新增：把「契约漂移」变成**自检会失败**的事）
    left_extra, right_extra = check_schema_alignment()
    ok0 = not left_extra and not right_extra
    ok_all = ok_all and ok0
    print('%s schema 对齐：本表 %d 字段 vs 编译器' % ('✓' if ok0 else '✗', len(LEAF_SCHEMA)))
    if left_extra:
        print('   ✗ 本表虚报（编译器不认）：%s' % left_extra)
    if right_extra:
        print('   ✗ 编译器支持但本表漏登记：%s' % right_extra)
    _p = plan_schema_prompt()
    _missing = [f for f in LEAF_SCHEMA if ('`%s`' % f) not in _p]
    ok0b = not _missing
    ok_all = ok_all and ok0b
    print('%s Planner Prompt 覆盖全部 %d 个字段（漏：%s）'
          % ('✓' if ok0b else '✗', len(LEAF_SCHEMA), _missing or '无'))

    # ① 布尔树：五个复合问句，引擎命中数 == 独立 SQL 复算
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
        # ⭐ 第二轮新增：复杂句级条件进布尔树（审查称 LLM 会用却被判不支持的那批）
        # 「清代 存在一句句脚为愁」
        ({'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                  {'field': 'lines.tail', 'op': 'in', 'value': ['愁']}]},
         "SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND "
         "p.pid IN (SELECT pid FROM lines WHERE tail='愁')"),
        # 「清代 没有任何一句句脚为仄」
        ({'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                  {'field': 'line_q', 'op': '=',
                   'value': {'op': '∄', 'pred': ['tail_pz', '仄']}}]},
         "SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND "
         "p.pid NOT IN (SELECT l.pid FROM lines l WHERE substr(l.pz,-1,1)='仄')"),
        # 「清代 每一句句脚都为仄」（∀）
        ({'and': [{'field': 'dynasty', 'op': '=', 'value': '清'},
                  {'field': 'line_q', 'op': '=',
                   'value': {'op': '∀', 'pred': ['tail_pz', '仄']}}]},
         "SELECT COUNT(*) FROM poems p WHERE p.dynasty='清' AND "
         "p.pid NOT IN (SELECT l.pid FROM lines l WHERE l.pz IS NULL OR substr(l.pz,-1,1)<>'仄') "
         "AND p.pid IN (SELECT l.pid FROM lines l)"),
    ]
    for i, (node, ref_sql) in enumerate(cases, 1):
        try:
            s, a = compile_filters(conn, node)
            n1 = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % s, a).fetchone()[0]
            n2 = conn.execute(ref_sql).fetchone()[0]
            ok = (n1 == n2)
        except Exception as e:                                   # noqa: BLE001
            n1 = n2 = -1
            ok = False
            print('     异常：%s: %s' % (type(e).__name__, e))
        ok_all = ok_all and ok
        print('%s 用例%d：编译命中 %d == 独立复算 %d' % ('✓' if ok else '✗', i, n1, n2))

    # ② to_plan / from_plan 往返（含复杂句级条件，验证 _legacy 不再被覆盖）
    for q in ('清 临江仙 仄声比例高于45%', '哪一首仄声比例最高',
              '蝶恋花·四月一日感粤事是谁写的', '清 句脚为愁的词',
              '清 每一句句脚都是仄的词'):
        try:
            spec = retrieve.parse_query(conn, q)
            plan = to_plan(spec)
            spec2 = from_plan(plan, conn)
            ok = (spec.describe() == spec2.describe()
                  and retrieve.count_hits(conn, spec) == retrieve.count_hits(conn, spec2))
        except Exception as e:                                   # noqa: BLE001
            ok = False
            print('     异常：%s: %s' % (type(e).__name__, e))
        ok_all = ok_all and ok
        print('%s 往返：%-22s → %s' % ('✓' if ok else '✗', q[:22],
                                       (spec2.describe() if ok else '（失败）')))
    print('自检：%s' % ('全部通过' if ok_all else '存在失败'))
    return ok_all


def main():
    import argparse
    import sqlite3
    ap = argparse.ArgumentParser(description='Query Plan（执行真源）：自检 / 渲染 / schema')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--question', default=None)
    ap.add_argument('--schema', action='store_true', help='打印给 Planner 用的字段说明书')
    args = ap.parse_args()
    if args.schema:
        print(plan_schema_prompt())
        return 0
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
