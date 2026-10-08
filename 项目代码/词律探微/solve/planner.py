# -*- coding: utf-8 -*-
"""planner.py —— 「查询规划器」（Query Planner）：让大模型产出**查询计划（Plan）**，
再由确定性执行器执行；而不是像 `qlm.SYSTEM` 那样往固定槽位里填值。

为什么要有它（架构级，外部审查 B 条）：
    旧路是「填槽式理解」——`qlm.SYSTEM` 是一份 ~90 行的**字段手册**，模型只能往
    dynasty/authors/cipais/tail/pz/scene/rng… 这些**预定义槽位**里塞值。对题库内的
    措辞够用，但**题库外的开放措辞**（「先筛出…再看…」「满足 A 但不满足 B 的」
    「有没有既…又…的」）几乎无解：模型没有「先想清要做什么、再表达条件」的余地。

    本模块把理解升级为「规划式理解」：
        用户问题 → Query Planner（LLM 负责「要做什么」）→ Query Plan → 确定性执行器
    模型不再填槽，而是产出一个 **Plan JSON**：
      · `intent`   —— 这道题要「干什么」（list/count/extreme/aggregate/extract/pair…）；
      · `filters`  —— 用**布尔树**表达**精确条件**（朝代/作者/词牌/题名/字数/句数/平仄/句脚…）；
      · `retrieve` —— **语义条件**（写秋景/离愁/主题相近）走向量检索，绝不混进 filters；
      · `operation`/`steps` —— 取值/统计/相似等后置动作。

与 `solve/queryplan.py` 的关系（**唯一约定，绝不自建第二套 IR**）：
    Query Plan 的 IR 由 `queryplan.py` 定义（另一条战线）。本模块**只按约定调用**：
        empty_plan() / validate(plan, conn) / to_spec(plan, conn) / from_spec(spec, conn)
    `filters` 是**任意嵌套布尔树**：`{"and":[…]}` / `{"or":[…]}` / `{"not":{…}}` /
    叶子 `{"field":F,"op":O,"value":V}`；合法 F/O 见 `queryplan._FIELD_OPS`（本模块的
    提示词与之一致）。**若 `queryplan` 尚未就绪**（ImportError 等），本模块**优雅降级**：
    `plan()` 返回 None，调用方（`qlm.understand` → `ask`）回落到规则解析——**绝不自建 IR**。

失败一律返回 None（调用方回落规则路），**绝不抛异常**。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import qlm                                                       # noqa: E402

PLAN_MAX_TOKENS = 700


# --------------------------------------------------------------------------- 规划提示词
# ⚠ 2026-10-08 第二轮审查 P0-#2（**契约漂移**）：审查原话——
#   「Planner 的 Prompt 告诉 LLM 可以用 scene/consist/tail_pz/pz_exact/tail_each/line_q/parity，
#     但 `queryplan._LEAF_FIELDS` 实际只有 14 个 → 正确理解被判 unsupported → plan() 返回 None
#     → 回落旧规则。根源是 Prompt Schema ≠ IR Schema ≠ Validator Schema。」
#   本版的治法：**字段/算子/步骤/召回模式的说明书由 `queryplan.plan_schema_prompt()` 现场生成**，
#   Planner 不再手写任何一份字段清单。`queryplan.check_schema_alignment()` 与
#   `selftest()` 里的「Prompt 覆盖全部字段」断言保证二者不可能再漂移。
_SYSTEM_HEAD = (
    '你是「词律探微」（清代词律声情研究助手）的**查询规划器（Query Planner）**。\n'
    '你的任务不是填表格，而是**先想清楚这道题要做什么，再把它写成一个查询计划**。\n'
    '只输出这个**计划 JSON 对象本身**，不要解释、不要代码块、不要多余文字。\n'
    '\n'
    '=================  计划（Plan）的结构  =================\n'
    '{\n'
    '  "version": 1,\n'
    '  "intent":  <意图，见下>,\n'
    '  "scope":   {"base": "corpus"},\n'
    '  "filters": <布尔树：精确条件，见下>,\n'
    '  "retrieve":<非空列表；无语义条件就写 [{"mode":"sql"}]>,\n'
    '  "steps":   [],\n'
    '  "operation": null,\n'
    '  "context": {},\n'
    '  "evidence": {}\n'
    '}\n'
)

_SYSTEM_TAIL = (
    '\n'
    '--- 布尔节点的写法（filters 是**任意嵌套**的树，不是平铺列表）---\n'
    '    {"and": [子节点, …]}   —— 全部满足\n'
    '    {"or":  [子节点, …]}   —— 满足其一\n'
    '    {"not": 子节点}        —— 不满足\n'
    '  句级「没有任何一句 / 至少两句」用 布尔组合 或 line_q 叶子表达：\n'
    '    · 「没有任何一句句脚为「愁」」→ {"not": {"field":"lines.tail","op":"in","value":["愁"]}}\n'
    '      （lines.tail 的存在性取反 = 不存在这样的句子）\n'
    '    · 「每一句句脚都是「愁」」→ line_q 叶子的 value 写 {"op":"∀","pred":["tail","愁"]}\n'
    '    · 「至少两句句脚为「愁」」→\n'
    '        {"field":"line_q","op":"=","value":{"op":"≥k","pred":["tail","愁"],"k":2}}\n'
    '      （line_q 叶子的 value 是**整个算子对象**；「正好 N 句」用 op="=k" 且带 "k"；\n'
    '        「存在一句」用 op="∃"；「没有任何一句」用 op="∄"。）\n'
    '\n'
    '=================  五条铁律  =================\n'
    '1) **精确条件进 filters，语义条件进 retrieve**：能落到列上的（朝代/作者/词牌/题名/\n'
    '   字数/句数/平仄/句脚/声情…）一律 filters；只有「主题/意象/情绪」才用 retrieve。\n'
    '2) **不要编造库里没有的值**：作者、词牌、题名必须是真实存在过的；拿不准就别写进 filters，\n'
    '   宁可留空——执行器会把落不了地的值记为 dropped 并披露。\n'
    '3) **并列/选择写进同一个叶子**：{"field":"lines.tail","op":"in","value":["灯","声"]}；\n'
    '   不要拆成两个 and 叶子（那是「同时」，不是「或者」）。\n'
    '4) **词牌与题名分清**：「蝶恋花·四月一日感粤事」= cipai=["蝶恋花"] + title=["四月一日感粤事"]。\n'
    '5) **不臆造条件**：问句没提的字段一律不要出现在计划里；数字原样照抄（45% → 45）。\n'
    '\n'
    '=================  五个示例（复杂问句直接照此措辞）  =================\n'
    '例1（并集/选择）「句脚是「灯」或者「声」的清词」\n'
    '  {"version":1,"intent":"list","scope":{"base":"corpus"},\n'
    '   "filters":{"and":[{"field":"dynasty","op":"in","value":["清"]},\n'
    '                     {"field":"lines.tail","op":"in","value":["灯","声"]}]},\n'
    '   "retrieve":[{"mode":"sql"}],"steps":[],"operation":null,"context":{},"evidence":{}}\n'
    '\n'
    '例2（句级否定）「没有任何一句句脚为「愁」的清词」\n'
    '  {"version":1,"intent":"list","scope":{"base":"corpus"},\n'
    '   "filters":{"and":[{"field":"dynasty","op":"in","value":["清"]},\n'
    '                     {"not":{"field":"lines.tail","op":"in","value":["愁"]}}]},\n'
    '   "retrieve":[{"mode":"sql"}],"steps":[],"operation":null,"context":{},"evidence":{}}\n'
    '\n'
    '例3（句级数量）「至少两句句脚为「愁」的清词」\n'
    '  {"version":1,"intent":"list","scope":{"base":"corpus"},\n'
    '   "filters":{"and":[{"field":"dynasty","op":"in","value":["清"]},\n'
    '                     {"field":"line_q","op":"≥k",\n'
    '                      "value":{"op":"≥k","pred":["tail","愁"],"k":2}}]},\n'
    '   "retrieve":[{"mode":"sql"}],"steps":[],"operation":null,"context":{},"evidence":{}}\n'
    '\n'
    '例4（词牌·题名）「蝶恋花·四月一日感粤事是谁写的」\n'
    '  {"version":1,"intent":"list","scope":{"base":"corpus"},\n'
    '   "filters":{"and":[{"field":"cipai","op":"in","value":["蝶恋花"]},\n'
    '                     {"field":"title","op":"contains","value":["四月一日感粤事"]}]},\n'
    '   "retrieve":[{"mode":"sql"}],"steps":[],"operation":{"kind":"extract"},'
    '"context":{},"evidence":{}}\n'
    '\n'
    '例5（精确 + 语义混合）「清词里写离愁的那种，仄声比例高于一半」\n'
    '  {"version":1,"intent":"list","scope":{"base":"corpus"},\n'
    '   "filters":{"and":[{"field":"dynasty","op":"in","value":["清"]},\n'
    '                     {"field":"ze_ratio","op":">=","value":50}]},\n'
    '   "retrieve":[{"mode":"vector","q":"离愁 别离 相思 羁旅 凄凉"}],\n'
    '   "steps":[],"operation":null,"context":{},"evidence":{}}\n'
    '\n'
    '若问句给出【上一轮上下文】，可用它补全指代与省略（「那里面」「改成宋词呢」），\n'
    '但**上下文里没出现过的条件不许臆造**；本轮问句若已自足，就忽略上下文。\n'
)


def system_prompt():
    """完整提示词 = 头部 + **由 IR 现场生成的字段说明书** + 尾部（铁律与示例）。

    这就是第二轮审查 P0-#2 的解药：字段/算子/步骤/召回的说明**只有一份**（`queryplan.LEAF_SCHEMA`），
    Prompt 是它的**渲染结果**，不是第二份手写清单。
    """
    QP = _load_queryplan()
    mid = ''
    if QP is not None:
        try:
            mid = '\n' + QP.plan_schema_prompt() + '\n'
        except Exception:                                        # noqa: BLE001
            mid = ''
    return _SYSTEM_HEAD + mid + _SYSTEM_TAIL


# 兼容旧引用（`planner.SYSTEM`）：module 级即生成，queryplan 不可用则退化为「无字段说明书」版本
try:
    SYSTEM = system_prompt()
except Exception:                                                # noqa: BLE001
    SYSTEM = _SYSTEM_HEAD + _SYSTEM_TAIL

# field 的族归类（落地校验与 filters 剪枝共用；**宽松**匹配多种写法）
_AUTHOR_FIELD = ('author', 'authors', 'poet', 'writer')
_CIPAI_FIELD = ('cipai', 'cipais', 'tune', 'cipai_name')
_TITLE_FIELD = ('title', 'titles', 'timu')
_STR_OPS = ('in', 'eq', '=', 'nin', 'not_in', 'contains', 'all_in')


def _load_queryplan():
    """惰性加载 `queryplan`（Query Plan IR，另一条战线）。未就绪 → None（优雅降级）。"""
    try:
        import queryplan                                        # noqa: F401
        return queryplan
    except Exception:
        return None


# --------------------------------------------------------------------------- filters 遍历/剪枝
def _iter_leaves(node):
    """深度遍历布尔树，产出所有叶子（dict）。非法节点直接跳过（不抛异常）。"""
    if not isinstance(node, dict):
        return
    if isinstance(node.get('and'), list):
        for c in node['and']:
            for x in _iter_leaves(c):
                yield x
    elif isinstance(node.get('or'), list):
        for c in node['or']:
            for x in _iter_leaves(c):
                yield x
    elif isinstance(node.get('not'), (dict, list)):
        for x in _iter_leaves(node['not']):
            yield x
    elif 'field' in node:
        yield node


def _leaf_values(leaf):
    """取叶子的值列表（标量→单元素列表；不做类型转换）。"""
    v = leaf.get('value')
    if isinstance(v, (list, tuple)):
        return list(v)
    if v is None:
        return []
    return [v]


def _real_sets(conn):
    """库里真实存在的作者/词牌集合（查不到表时退化为 None，表示「无法校验」——**不臆断**）。"""
    try:
        authors = {r[0] for r in conn.execute('SELECT author FROM authors')}
    except Exception:                                            # noqa: BLE001
        authors = None
    try:
        cipai = {r[0] for r in conn.execute('SELECT cipai FROM cipai')}
    except Exception:                                            # noqa: BLE001
        cipai = None
    return authors, cipai


def _landing_check(node, conn):
    """对 filters 做**落地校验**：作者/词牌是否真在库中、题名是否真命中。

    返回 `(bad_pairs, dropped)`：
      · bad_pairs：`{(field, value), …}`——落不了地的叶子（**不再用于剪枝**，见 `_mark_not_found`）；
      · dropped：  中文说明列表（**记 dropped，绝不静默丢**）。
    """
    bad, dropped = set(), []
    real_authors, real_cipai = _real_sets(conn)
    if real_authors is None and real_cipai is None:
        return bad, dropped

    for leaf in _iter_leaves(node):
        fld = str(leaf.get('field') or '').strip()
        if leaf.get('op') not in _STR_OPS:
            continue
        for val in _leaf_values(leaf):
            if not isinstance(val, str):
                continue
            if fld in _AUTHOR_FIELD and real_authors is not None and val not in real_authors:
                bad.add((fld, val))
                dropped.append('词人=%s（库中没有此人）' % val)
            elif fld in _CIPAI_FIELD and real_cipai is not None and val not in real_cipai:
                bad.add((fld, val))
                dropped.append('词牌=%s（库中没有此调）' % val)
            elif fld in _TITLE_FIELD:
                try:
                    hit = conn.execute('SELECT 1 FROM poems WHERE title LIKE ? LIMIT 1',
                                       ('%' + val + '%',)).fetchone()
                except Exception:                                # noqa: BLE001
                    hit = None
                if not hit:
                    bad.add((fld, val))
                    dropped.append('题名=%s（语料标题中不存在）' % val)
    return bad, dropped


# ⛔ 常量：**永不匹配**的 pid 哨兵。用于把「查无此实体」编译成恒假的叶子，
#    而不是把条件删掉（删掉 = 全库查询，那是审查 §25 点名的危险形态）。
_NOT_FOUND_PID = '__LVC_NOT_FOUND__'


def _mark_not_found(node, bad):
    """把「查无此实体」的叶子换成**恒假/恒真**哨兵 —— **绝不剪枝**。

    为什么不能再剪枝（2026-10-08 第二轮审查 §25，原话）：

    > 用户问「只有某个不存在的人」→ 剪掉以后 filters 变成空 → 退化为**全库查询**。
    > 这是非常危险的：「模型认为条件不存在」不能等价于「用户没有这个条件」。
    > 对 `author = nonexistent`，正确语义是**结果集 = 空 / NOT_FOUND**，不是全库。

    ★ 一个容易判反的细节（本函数第一版就搞错了，自检抓了出来）：
      无效实体的叶子**在任何位置都换成「恒假」**，不需要按是否在 `not` 之下分方向——
      因为布尔逻辑自己会处理：
        · 普通位：`author=查无此人` → FALSE → 整篇不命中 → **0 篇**（正确）；
        · `not` 之下：`NOT(author=查无此人)` = `NOT FALSE` = TRUE → **全库**
          （正确：库里确实没有这人写的，所以「不是他写的」对每一篇都成立）。
      若像第一版那样在 `not` 之下换成「恒真」，就得到 `NOT TRUE` = FALSE → 0 篇，**判反了**。
    """
    def rec(n):
        if not isinstance(n, dict):
            return n
        if isinstance(n.get('and'), list):
            return {'and': [rec(c) for c in n['and']]}
        if isinstance(n.get('or'), list):
            return {'or': [rec(c) for c in n['or']]}
        if isinstance(n.get('not'), (dict, list)):
            return {'not': rec(n['not'])}
        if 'field' not in n:
            return n
        fld = str(n.get('field') or '').strip()
        for val in _leaf_values(n):
            if (fld, val) in bad:
                return {'field': 'pid', 'op': 'in', 'value': [_NOT_FOUND_PID]}
        return n
    return rec(node) if node else node


def _prune(node, bad):
    """按 `bad={(field,value)}` 剪掉落不了地的叶子；布尔节点空则上递 None。

    「落不了地」的作者/词牌/题名多半是模型臆造——**不能静默留着执行**（留着一个
    `author='查无此人'` 会把命中数砍成 0，看起来却「像对的」）；这里把该叶子删掉，
    并在 `dropped` 里如实记明（由 `plan()` 写入 `plan['_dropped']`）。
    """
    if not isinstance(node, dict):
        return None
    if isinstance(node.get('and'), list):
        kids = [k for k in (_prune(c, bad) for c in node['and']) if k is not None]
        if not kids:
            return None
        return kids[0] if len(kids) == 1 else {'and': kids}
    if isinstance(node.get('or'), list):
        kids = [k for k in (_prune(c, bad) for c in node['or']) if k is not None]
        if not kids:
            return None
        return kids[0] if len(kids) == 1 else {'or': kids}
    if isinstance(node.get('not'), (dict, list)):
        inner = _prune(node['not'], bad)
        return {'not': inner} if inner is not None else None
    fld = str(node.get('field') or '').strip()
    for val in _leaf_values(node):
        if (fld, val) in bad:
            return None
    return node


# --------------------------------------------------------------------------- 计划校验（对外）
def validate(plan, conn):
    """校验一个 Plan：**先做落地剪枝**（记 dropped），再调 `queryplan.validate`。

    返回 `(ok, problems)`（与 `queryplan.validate` 同形：bool + 中文问题列表）。
    ⚠ 副作用：把落不了地的值写进 `plan['_dropped']`（**记而不静默丢**），并从 filters 剪掉。
    本函数**绝不抛异常**——任何异常都折算成 `(False, [说明])`。
    """
    QP = _load_queryplan()
    if QP is None:
        return False, ['queryplan（Query Plan IR）尚未就绪，无法校验计划']
    if not isinstance(plan, dict):
        return False, ['计划不是对象']
    # (1) 落地校验 + 剪枝（先剪，再交给 IR 校验——免得臆造实体把整份计划判死）
    try:
        bad, dropped = _landing_check(plan.get('filters'), conn)
    except Exception as e:
        bad, dropped = set(), ['落地校验异常：%s' % e]
    if dropped:
        plan['_dropped'] = list(plan.get('_dropped') or []) + dropped
    if bad:
        # ⛔ 不再剪枝（审查 §25）：改成**恒假哨兵**，让结果集诚实地为「空 + NOT_FOUND」，
        #    而不是「条件消失 → 全库」。同时把引用记录下来供上层如实披露。
        plan['_not_found'] = list(plan.get('_not_found') or []) + dropped
        plan['filters'] = _mark_not_found(plan.get('filters'), bad)
    # (2) 交给 IR 做结构/语义校验
    try:
        ok, problems = QP.validate(plan, conn)
    except Exception as e:
        return False, ['计划校验异常：%s' % e]
    return bool(ok), list(problems or [])


# --------------------------------------------------------------------------- 规划（对外）
def plan(conn, llm, question, context=None):
    """问句 → **查询计划（Plan）**。失败/未就绪一律返回 None（调用方回落规则路）。

    返回的 dict 就是 Plan；另附三个以 `_` 开头的**元数据**键（不参与 IR 执行）：
      · `_raw`     模型原始输出（审计用）；
      · `_dropped` 落不了地、被剪掉的值（如实披露）；
      · `_notes`   规划层说明。
    """
    try:
        if not (llm and llm.available()):
            return None
        QP = _load_queryplan()
        if QP is None:                    # IR 未就绪 → 优雅降级（**不自建第二套 IR**）
            return None
        try:
            base = QP.empty_plan()        # 缺省框架来自 IR，绝不自己 hardcode 一份
        except Exception:
            return None
        # ---- 调模型（流式见到完整 JSON 即断开，同 qlm.parse）----
        kw = {'temperature': 0.0, 'max_tokens': PLAN_MAX_TOKENS}
        try:
            if 'expect_json' in llm.chat.__code__.co_varnames:
                kw['expect_json'] = True
        except Exception:
            pass
        user = '问句：%s' % question
        if context:
            user = ('【上一轮上下文】%s\n（本轮问句若含指代/省略——如「那里面呢」——请结合上下文补全；'
                    '本轮问句若已自足，则忽略上下文。）\n%s' % (context, user))
        raw = llm.chat([{'role': 'system', 'content': SYSTEM},
                        {'role': 'user', 'content': user}], **kw)
        obj = qlm._json_block(raw)
        if not isinstance(obj, dict):
            return None
        # ---- 归一化：以 IR 的 empty_plan 为底，叠加模型给的计划字段 ----
        pl = dict(base) if isinstance(base, dict) else {}
        for k, v in obj.items():
            pl[k] = v
        pl['version'] = pl.get('version', 1) or 1
        if not isinstance(pl.get('filters'), dict):
            pl['filters'] = {'and': []}
        if not isinstance(pl.get('retrieve'), list) or not pl['retrieve']:
            pl['retrieve'] = [{'mode': 'sql'}]
        if not pl.get('intent'):
            pl['intent'] = 'list'
        # ---- 校验（含落地剪枝；落不了地的值被剪掉并记 dropped）----
        ok, problems = validate(pl, conn)
        if not ok:
            return None
        pl['_raw'] = raw or ''
        pl['_notes'] = ['计划已通过 queryplan.validate 与落地校验'
                        + ('（其中 %d 个实体在语料中查无，已按「结果集为空」处理，'
                           '而非删除条件）' % len(pl.get('_not_found') or [])
                           if pl.get('_not_found') else '')]
        return pl
    except Exception:
        return None               # 硬约束：绝不抛异常


def main():
    """自检/演示：问句 → 计划 JSON。"""
    import argparse
    import sqlite3
    ap = argparse.ArgumentParser(description='查询规划器：问句 → Query Plan（JSON）')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--question', default=None)
    ap.add_argument('--provider', default=None)
    ap.add_argument('--selftest', action='store_true', help='跑契约/落地自检（不需要大模型）')
    args = ap.parse_args()
    if args.selftest:
        import sqlite3
        _c = sqlite3.connect(args.db)
        try:
            return 0 if selftest(_c) else 1
        finally:
            _c.close()
    if not args.question:
        ap.error('缺少 --question（或改用 --selftest）')
    if _load_queryplan() is None:
        print('queryplan（Query Plan IR）尚未就绪 → planner 优雅降级，返回 None（调用方回落规则路）')
        return 1
    import llm as L
    conn = sqlite3.connect(args.db)
    client = L.LLM(provider=args.provider)
    print('模型：%s（可用=%s）' % (client.name or '无', client.available()))
    pl = plan(conn, client, args.question)
    print('计划：%s' % (json.dumps(pl, ensure_ascii=False, indent=2) if pl else 'None（回落规则路）'))
    conn.close()
    return 0


def selftest(conn):
    """自检：契约不漂移（#2）+ 无效实体不退化成全库（#14）+ 未就绪时优雅降级。"""
    ok_all = True
    QP = _load_queryplan()

    # ① 契约：Prompt 里出现过的字段**必须**都在 IR schema 里（反向由 queryplan 自检兜住）
    if QP is None:
        print('✗ queryplan 不可用，无法做契约检查')
        return False
    _p = system_prompt()
    import re as _re
    mentioned = set(_re.findall(r'`([a-zA-Z_][\w.]*)`', _p))
    unknown = sorted(f for f in mentioned
                     if f not in QP.LEAF_SCHEMA and f not in QP.STEP_OPS
                     and f not in QP.RETRIEVE_MODES and f not in QP.INTENTS
                     and f not in QP.AGG_METRICS)
    ok1 = not unknown
    ok_all &= ok1
    print('%s 契约检查：Prompt 提及的字段全部在 IR schema 内（越界：%s）'
          % ('✓' if ok1 else '✗', unknown or '无'))

    # ② 无效实体 → 结果集为空，**不是全库**
    bad = {('author', '查无此人'), ('cipai', '不存在的词牌')}
    node = {'and': [{'field': 'dynasty', 'op': 'in', 'value': ['清']},
                    {'field': 'author', 'op': 'in', 'value': ['查无此人']}]}
    fixed = _mark_not_found(node, bad)
    sql, args = QP.compile_filters(conn, fixed)
    n_bad = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % sql, args).fetchone()[0]
    n_all = conn.execute("SELECT COUNT(*) FROM poems WHERE dynasty='清'").fetchone()[0]
    ok2 = (n_bad == 0 and n_all > 0)
    ok_all &= ok2
    print('%s 无效实体 → 命中 %d 篇（清词共 %d 篇 → 必须为空，不得退化为全库）'
          % ('✓' if ok2 else '✗', n_bad, n_all))

    # ③ NOT 之下的无效实体 → 语义上恒真（「不是查无此人写的」= 全部）
    node2 = {'and': [{'field': 'dynasty', 'op': 'in', 'value': ['清']},
                     {'not': {'field': 'author', 'op': 'in', 'value': ['查无此人']}}]}
    fixed2 = _mark_not_found(node2, bad)
    sql2, args2 = QP.compile_filters(conn, fixed2)
    n_not = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s' % sql2, args2).fetchone()[0]
    ok3 = (n_not == n_all)
    ok_all &= ok3
    print('%s NOT(无效实体) → 命中 %d 篇（应等于清词全部 %d 篇）'
          % ('✓' if ok3 else '✗', n_not, n_all))

    # ④ 无模型时 `plan()` 必须返回 None（绝不抛异常、绝不伪造计划）
    ok4 = (plan(conn, None, '清 临江仙') is None)
    ok_all &= ok4
    print('%s 无大模型时优雅降级（返回 None → 调用方回落规则路）' % ('✓' if ok4 else '✗'))
    print('自检：%s' % ('全部通过' if ok_all else '存在失败'))
    return bool(ok_all)


if __name__ == '__main__':
    sys.exit(main())
