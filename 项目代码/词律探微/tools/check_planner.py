# -*- coding: utf-8 -*-
"""check_planner.py —— **规划路（Query Planner → Plan → Executor）常设门禁**。

为什么要有它（2026-10-15 第二轮深挖发现的真缺口）
------------------------------------------------
`启动问答网页.bat` 与服务端默认均为 `LVC_PLANNER=rule`；规划路需显式设为 `plan`。此前
`tools/check_all.py` / `web/test_api.py` / `tools/regress.py` / `reproduce.py`
**都不设该环境变量**，也没有任何断言触碰规划路 → 下列模块（合计约 3,472 行）在
默认门禁下**一行都没被执行**：

    planner.py(524) + plan_exec.py(1353) + queryast.py(480) + queryplan.py(1115)

《架构符合性核查与整改报告》已记录过该路的脆弱点（`queryplan.to_spec` 不存在却被调用、
被 `except` 吞掉 → 静默回落）——正是因为**没有门禁**，这类问题只能靠人眼发现。

本门禁怎么测（**确定性、离线、不联网、不依赖大模型**）
----------------------------------------------------
规划器 `planner.plan()` 需要大模型；但**执行器** `plan_exec.execute()` 是纯确定性的。
于是本门禁用**规则解析产出的 spec → `queryplan.to_plan()` → `plan_exec.execute()`**
这条**不经过大模型**的确定性链，把 IR 编译 + 校验 + 执行器整条跑起来，并与规则路
（`retrieve._sql`）的命中集**对账**：

  一、**IR 编译**：`queryplan.to_plan(spec)` 必须产出合法计划（非空 dict）；
  二、**校验**：`queryplan.validate(plan, conn)` 必须通过（无 unsupported 项）；
  三、**执行**：`plan_exec.execute()` 不得异常、不得 `EXECUTION_FAILED`、必须产出结果帧；
  四、**对账**：执行帧的 pid 集与规则路命中集一致（集合题）或为其子集（极值题）；
  五、**接线**：`LVC_PLANNER=plan` 且**无大模型**时，`ask.answer()` 仍须给出合法回答
      （规划路诚实回落既有链，不得崩、不得空）。

对账口径说明：极值题（「哪首…最长」）规划路只给**前 N 篇**，规则路给**全部命中**，
故取「子集」而非「相等」——不把**正确的**极值语义误判成 FAIL。

`--selftest`：把执行器的结果帧换成**错 pid 集**后重跑，**必须**出现 FAIL——
证明这套检查真的测得出「规划路算错」，而不是空跑报通过。

用法：python tools/check_planner.py [--db data/corpus.db] [--selftest]
退出码：0 = 全部通过；1 = 有 FAIL。
"""
import argparse
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import plan_exec                                              # noqa: E402
import queryplan                                             # noqa: E402
import retrieve                                              # noqa: E402

# (问句, 对账模式)：'eq' = 帧 pid 集必须等于规则路命中集；'subset' = 必须是其子集（极值题）
CASES = [
    ('清 临江仙 仄声比例高于45%', 'eq'),
    ('句脚是「愁」的清词有哪些', 'eq'),
    ('朱彝尊 桂殿秋', 'eq'),
    ('清 临江仙', 'eq'),
    ('清词中哪首字数最长', 'subset'),
]
# 接线冒烟（LVC_PLANNER=plan + 无大模型 → 诚实回落，不得崩）
WIRING = ['清 临江仙 仄声比例高于45%', '朱彝尊 桂殿秋']


def _rule_pids(conn, q):
    """规则路命中集（独立于规划路；无硬条件返回 None）。"""
    spec = retrieve.parse_query(conn, q)
    where, args = retrieve._sql(spec)
    if not where or where.strip() == '1=1':
        return None
    rows = conn.execute('SELECT p.pid FROM poems p WHERE ' + where, args)
    return set(r[0] for r in rows)


def main():
    ap = argparse.ArgumentParser(description='规划路（Planner→Plan→Executor）门禁')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--selftest', action='store_true',
                    help='把执行器结果帧换成错 pid 集后重跑，必须报错')
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    conn.row_factory = sqlite3.Row

    checks, fails, n_cmp = [], [], 0

    def ck(name, ok, detail=''):
        checks.append(name)
        if not ok:
            fails.append('%s%s' % (name, ('：' + detail) if detail else ''))
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                             ('：' + detail) if detail else ''))

    if a.selftest:
        # 让执行器返回一个「必然错」的帧 → 对账必须 FAIL（证明检查器有效）
        _real_execute = plan_exec.execute

        def _broken_execute(conn_, plan, **kw):
            res = _real_execute(conn_, plan, **kw)
            fr = res.get('frame')
            if fr is not None:
                fr.pids = ['__bogus_pid__']
            return res
        plan_exec.execute = _broken_execute
        print('（自检模式：已把执行帧换成错 pid 集，期望出现 FAIL）')

    # ---------------- 一~四：IR 编译 + 校验 + 执行 + 对账 ----------------
    for q, mode in CASES:
        print('· %s' % q)
        try:
            spec = retrieve.parse_query(conn, q)
            plan = queryplan.to_plan(spec)
        except Exception as e:                               # noqa: BLE001
            n_cmp += 1
            ck('一·IR 编译：%s' % q, False, '%s: %s' % (type(e).__name__, e))
            continue
        n_cmp += 1
        ck('一·IR 编译：%s' % q, isinstance(plan, dict) and bool(plan),
           'type=%s' % type(plan).__name__)

        try:
            ok, problems = queryplan.validate(plan, conn)
        except Exception as e:                               # noqa: BLE001
            ok, problems = False, ['%s: %s' % (type(e).__name__, e)]
        n_cmp += 1
        ck('二·计划校验通过：%s' % q, bool(ok),
           '；'.join(str(x) for x in (problems or [])[:3]))

        try:
            res = plan_exec.execute(conn, plan, question=q, topk=3)
        except Exception as e:                               # noqa: BLE001
            n_cmp += 1
            ck('三·执行不抛异常：%s' % q, False, '%s: %s' % (type(e).__name__, e))
            continue
        state = res.get('state') or 'EXECUTION_OK'
        frame = res.get('frame')
        n_cmp += 1
        ck('三·执行成功且产出帧：%s' % q,
           state != 'EXECUTION_FAILED' and frame is not None,
           'state=%s problems=%s' % (state, (res.get('problems') or [])[:2]))

        rp = _rule_pids(conn, q)
        fp = set(frame.pids) if frame is not None else set()
        if rp is None:
            n_cmp += 1
            ck('四·对账（规则路无硬条件，仅查非空）：%s' % q, bool(fp),
               '规则路无硬条件')
        elif mode == 'eq':
            n_cmp += 1
            ck('四·帧 pid 集 == 规则路命中集：%s' % q, fp == rp,
               '|帧|=%d |规则|=%d 差集=%d' % (len(fp), len(rp), len(fp ^ rp)))
        else:                                                # subset
            n_cmp += 1
            ck('四·帧 pid 集 ⊆ 规则路命中集（极值题）：%s' % q,
               bool(fp) and fp <= rp,
               '|帧|=%d |规则|=%d 越界=%d' % (len(fp), len(rp), len(fp - rp)))

    # ---------------- 五：接线（LVC_PLANNER=plan + 无大模型 → 诚实回落） ----------------
    os.environ['LVC_PLANNER'] = 'plan'
    try:
        import ask as A
    except Exception as e:                                   # noqa: BLE001
        n_cmp += 1
        ck('五·导入 ask（规划路接线）：', False, '%s: %s' % (type(e).__name__, e))
        A = None
    if A is not None:
        for q in WIRING:
            try:
                r = A.answer(conn, q, topk=3)
                ans = r.get('answer') or ''
                why = ('答案为空' if not ans else
                       ('含 NaN' if 'NaN' in ans else
                        ('含 Traceback' if 'Traceback' in ans else '')))
                n_cmp += 1
                ck('五·LVC_PLANNER=plan 无模型时仍给出合法回答：%s' % q,
                   not why, why or '答案 %d 字（规划路诚实回落既有链）' % len(ans))
            except Exception as e:                           # noqa: BLE001
                n_cmp += 1
                ck('五·LVC_PLANNER=plan 无模型时仍给出合法回答：%s' % q,
                   False, '%s: %s' % (type(e).__name__, e))

    print('-' * 60)
    print('检查项 %d，失败 %d' % (len(checks), len(fails)))
    if not checks:
        print('比对项为 0 → 判 FAIL（防空跑报通过）')
        return 1
    if fails:
        print('失败：')
        for x in fails[:12]:
            print('  ! %s' % x)
        return 1
    print('规划路门禁全部通过。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
