# -*- coding: utf-8 -*-
"""answer_verify.py —— **集合身份校验**（外部架构审查 B 项）。

问题（2026-10-08，外部审查 B）：
    `guard.py` 的四道护栏（数字/引用/边界/内容安全）只保「**数字自洽**」——
    引用块里的数字互相不矛盾、都能在证据块里找到出处，就判「通过」。
    但**「检索到了一个错误的子集、而每个数字都自洽」**这种情况，四道护栏**看不见**，
    于是成为**静默错答**的来源（答案看着严丝合缝，问的却是另一批篇）。

本模块补上这一层：
  1. **集合身份**：把 `spec` 编成 SQL（**复用 `retrieve._sql` / `retrieve.scope_pids`**，
     不自己重写条件编译），独立算出命中的**完整** pid 集，
     再与「结果里给出的 pid 集」比对；差集非空 → 报「结果集合与条件不符」，
     并给出「多出的」「漏掉的」各前若干 pid；
  2. **聚合复算**（可选）：结果里带 `agg` 时，用独立的 `aggregate` 调用把分组统计重算一遍比对；
  3. **完整性状态**：结果是否被 `limit`（top-k）截断 —— **如实标注**
     `truncated / shown / total`，绝不让「展示了 3 篇」被读成「只有 3 篇」。

★ 结构性隔离（D07）：本模块只被 `web/serve.py` 调用，不进 `ask`/`solver`，
  对 1000 题交付答案**零影响**。
"""

import retrieve as RT

try:                                     # 聚合复算是「可选」项：没有 aggregate 也能跑
    import aggregate as AGG
except Exception:                        # pragma: no cover - 环境缺依赖时静默降级
    AGG = None


def _dedup(seq):
    seen, out = set(), []
    for x in (seq or []):
        s = str(x).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def hit_pids(conn, spec):
    """独立复算：`spec` 命中篇的**完整** pid 列表（不是 top-k）。

    无硬条件（纯语义/词面检索）时返回 **None** —— 此时「命中集」不是可判定的集合，
    调用方必须区分 `None`（无法校验）与 `[]`（确实 0 篇）。
    """
    if spec is None:
        return None
    if getattr(spec, 'unsupported', None):
        return []
    try:
        if not RT.has_hard(spec):
            return None
    except Exception:
        pass
    where, args = RT._sql(spec)
    if where == '1=1':                   # 没有可执行的硬条件
        return None
    return list(RT.scope_pids(conn, where, args))


def verify_result(conn, spec, result_pids, expect_complete=False, sample=8):
    """**集合身份校验**（对外主入口）。返回 `(ok, problems)`。

    · `spec`         —— 理解层产出的 `retrieve.QuerySpec`（由调用方独立重新求得）；
    · `result_pids`  —— 结果里给出的 pid 集合（如 `blocks[].pid`；或上一轮的完整结果集）；
    · `expect_complete` —— `result_pids` 是否**自称完整**：
        - True ：与之差集非空即判失败（「漏掉」也算错）；
        - False：只把「**多出**」（不在命中集内）判为失败；「漏掉」按 top-k 的正常情况，
                 仍如实写出，但不判失败（避免把「只展示了 3 篇」误报成错）。
    · `sample`       —— 「多出的/漏掉的」各列前若干个 pid。

    `problems` 为**人类可读的中文串**列表；未执行校验时给出一条说明（不算失败）。
    """
    pids = _dedup(result_pids)
    S = hit_pids(conn, spec)
    if S is None:
        return True, ['（未执行集合身份校验：本条问句没有可执行的硬条件，检索为语义相关度排序）']
    Sset = set(S)
    Rset = set(pids)
    extra = [p for p in pids if p not in Sset]              # 多出的（不在条件命中集内）
    missing = [p for p in S if p not in Rset]               # 漏掉的（满足条件却未出现在结果里）
    problems = []
    if extra:
        problems.append('结果集合与条件不符：多出 %d 篇（不在条件命中集内）——%s%s'
                        % (len(extra), '、'.join(extra[:sample]),
                           ' 等' if len(extra) > sample else ''))
    if missing:
        msg = ('漏掉 %d 篇（满足条件却未在结果中）——%s%s'
               % (len(missing), '、'.join(missing[:sample]),
                  ' 等' if len(missing) > sample else ''))
        if expect_complete:
            problems.append('结果集合与条件不符：' + msg)
        else:
            # 结果自称只展示一部分（top-k）→「未展示」是正常情况。如实写出，
            # 但**明标为信息**（前缀「（信息）」），由调用方与真正的错误分开呈现。
            problems.append('（信息）' + msg + '（本次结果按 top-k 展示，「未展示」属正常，'
                                              '不计为失败；如需完整集合请改用会话/检索接口）')
    ok = (not extra) and not (missing and expect_complete)
    return ok, problems


def _agg_recompute(conn, spec, agg_result, tol=0.11):
    """**聚合复算**（可选）：用独立 SQL 把分组统计重算一遍，与结果里的 `agg.rows` 比对。

    返回 `(ok, problems)`；无法复算时返回 `(True, [])`（宁可不判，也不误判）。
    只比对**确定性字段**：组名 / 篇数 / 篇均 / 加权；浮点给 0.11 容差（与 `test_api` 同口径）。
    """
    if not agg_result or AGG is None or spec is None:
        return True, []
    ag = getattr(spec, 'agg', None)
    if not ag:
        return True, []
    rows_have = agg_result.get('rows')
    if not rows_have:
        return True, []
    try:
        gb, mt, cat = ag.get('group_by'), ag.get('metric'), ag.get('cat')
        vals = ag.get('values')
        where, args = RT._sql(spec)
        if vals:
            rows2 = AGG.stats(conn, gb, vals, mt, cat, where, args)
        else:
            rows2 = AGG.top_groups(conn, gb, 5, mt, cat, where, args,
                                   ag.get('extreme') or 'max')
    except Exception as exc:                                 # 复算路径不可用 → 不判
        return True, ['（聚合复算未执行：%s: %s）' % (type(exc).__name__, exc)]
    by2 = {str(r.get('group')): r for r in rows2}
    problems = []
    for r in rows_have:
        g = str(r.get('group'))
        r2 = by2.get(g)
        if r2 is None:
            problems.append('聚合复算不符：结果里有组〔%s〕，独立复算没有' % g)
            continue
        for key in ('n', 'mean', 'weighted'):
            if key in r and key in r2:
                a, b = r.get(key), r2.get(key)
                try:
                    if a is None or b is None:
                        if a != b:
                            problems.append('聚合复算不符：组〔%s〕的 %s 一边为空另一边非空' % (g, key))
                    elif abs(float(a) - float(b)) > tol:
                        problems.append('聚合复算不符：组〔%s〕的 %s 结果=%s 独立复算=%s'
                                        % (g, key, a, b))
                except (TypeError, ValueError):
                    if a != b:
                        problems.append('聚合复算不符：组〔%s〕的 %s 结果=%s 独立复算=%s'
                                        % (g, key, a, b))
    return (not problems), problems


def build_set_check(conn, spec, result_pids, total=None, shown=None,
                    expect_complete=None, sample=8, agg_result=None):
    """给 `/api/ask`、`/api/ask_stream` 的 `set_check` 字段（**结构化**，供前端展示）。

    字段：
      · `ok`            整体是否通过（集合身份 + 可选聚合复算）；
      · `checked`       是否真的做了集合身份校验（无硬条件时为 False）；
      · `reason`        未校验/说明；
      · `hit_total`     独立复算命中总数；`result_total` 引擎自报总数；
      · `shown`         结果中展示的篇数；`truncated` 是否被 limit 截断；
      · `extra/extra_n` 「多出的」（不在命中集内）；`missing/missing_n`「漏掉的」；
      · `problems`      问题串列表；`agg` 聚合复算摘要（无则 None）。
    """
    pids = _dedup(result_pids)
    if shown is None:
        shown = len(pids)
    # 完整性：结果自称完整 ⇔ 引擎给的总数与展示篇数相等（且总数存在）
    if expect_complete is None:
        expect_complete = bool(total is not None and total == shown)
    truncated = None
    if total is not None and shown is not None:
        truncated = total > shown

    S = hit_pids(conn, spec)
    checked = S is not None
    notes = []
    if not checked:
        ok = True
        problems = []
        extra, missing = [], []
        hit_total = None
        notes.append('未执行集合身份校验：本条问句没有可执行的硬条件，检索为语义相关度排序，'
                     '「命中集」不可判定。')
    else:
        ok, problems = verify_result(conn, spec, pids, expect_complete=expect_complete, sample=sample)
        Sset = set(S)
        Rset = set(pids)
        extra = [p for p in pids if p not in Sset]
        missing = [p for p in S if p not in Rset]
        hit_total = len(S)
        # verify_result 里「非完整结果」的漏掉提示是**信息**（前缀「（信息）」）——搬到 notes，
        # 免得界面上「正常只展示 top-k」被读成「集合不符」。
        keep = []
        for p in problems:
            if p.startswith('（信息）'):
                notes.append(p[len('（信息）'):])
            else:
                keep.append(p)
        problems = keep
        # 独立复算总数 vs 引擎自报总数：仅当自报总数**是篇数**（int）时才比。
        # （聚合/配对/中位数/占比/第N名等路径的 `total` 不是篇数，比了会误报。）
        if isinstance(total, int) and not isinstance(total, bool) and hit_total != total:
            notes.append('命中总数不一致：引擎自报 %s 篇，独立复算 %s 篇（两条理解路径的结果集不同，'
                         '多为理解层对条件的取舍差异）' % (total, hit_total))

    agg_ok, agg_pb = _agg_recompute(conn, spec, agg_result)
    if agg_pb:
        if not agg_ok:
            ok = False
        problems = list(problems) + list(agg_pb)

    reason = None
    if not checked:
        reason = '无硬条件：检索为语义相关度排序，命中集不可判定，未做集合身份校验'
    return {
        'ok': bool(ok),
        'checked': bool(checked),
        'reason': reason,
        'hit_total': hit_total,
        'result_total': total,
        'shown': shown,
        'truncated': truncated,
        'complete_checked': bool(expect_complete),
        'extra': extra[:sample], 'extra_n': len(extra),
        'missing': missing[:sample], 'missing_n': len(missing),
        'problems': problems,
        'notes': notes,
        'agg': (None if agg_ok or not agg_pb else {'ok': False, 'problems': list(agg_pb)}),
    }


# ─────────────────────────── 自测（python solve/answer_verify.py） ───────────────────────────
def _selftest():
    import os
    import sqlite3
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    conn = sqlite3.connect(os.path.join(root, 'data', 'corpus.db'))
    spec = RT.parse_query(conn, '清 临江仙 仄声比例高于45%')
    S = hit_pids(conn, spec)
    print('独立复算命中：%d 篇' % (len(S) if S is not None else -1))
    # ① 完整集合 → 通过
    print('① 完整集合 ->', verify_result(conn, spec, S, expect_complete=True))
    # ② 多出 2 篇（模拟「检索到了错误子集」的静默错答）
    bad = list(S) + ['NOTEXIST1', 'NOTEXIST2']
    print('② 多出 2 篇 ->', verify_result(conn, spec, bad))
    # ③ 只展示前 3 篇（expect_complete=False 时「漏掉」不判失败）
    print('③ 仅展示前 3 篇(非完整) ->', verify_result(conn, spec, S[:3]))
    print('③ 仅展示前 3 篇(自称完整) ->', verify_result(conn, spec, S[:3], expect_complete=True))
    # ④ 无硬条件（纯语义检索 → 命中集不可判定 → 返回 None）
    #    注意：本语料本身即「清代词」，故「…的清词」里的「清」是**匹配全库**的硬条件，
    #    不算「无硬条件」；要演示「无硬条件」须用不带朝代的问句。
    spec2 = RT.parse_query(conn, '写离愁的词')
    print('④ 无硬条件 ->', verify_result(conn, spec2, ['x']))
    # ⑤ 结构化
    sc = build_set_check(conn, spec, S[:5], total=len(S), shown=5)
    print('⑤ set_check =', {k: sc[k] for k in ('ok', 'checked', 'hit_total', 'result_total',
                                               'shown', 'truncated', 'extra_n', 'missing_n',
                                               'complete_checked')})
    print('   problems =', sc['problems'])
    print('   notes    =', sc['notes'])
    # ⑥ 自称完整 + 多出 → 必须判失败
    sc2 = build_set_check(conn, spec, list(S[:3]) + ['GHOST'], total=3, shown=4)
    print('⑥ 自称完整但多出 → ok=%s problems=%s' % (sc2['ok'], sc2['problems']))
    # ⑦ 自称完整且完全一致 → 通过
    sc3 = build_set_check(conn, spec, S, total=len(S), shown=len(S))
    print('⑦ 完整一致 → ok=%s complete_checked=%s truncated=%s'
          % (sc3['ok'], sc3['complete_checked'], sc3['truncated']))
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(_selftest())
