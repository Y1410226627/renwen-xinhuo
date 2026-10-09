# -*- coding: utf-8 -*-
"""tools/nl_benchmark.py —— **开放自然语言理解基准**（外部架构审查 #11 / B11）。

审查原文（§0.4）：

> `selftest.py` 235/0：结构/安全/确定性/格式；**不含开放理解**。
> `regress.py` 哈希一致：只证明交付链在**固定题型**上无回退；**不证明理解**。
> `verify_1000.py`：用**引擎复算**得真值 → **自证循环**。
> 建议：留出自然语言改写基准集入 CI。

本评测器填补的正是这块：公开 700 题**全部**是官方「甲乙两篇对比」模板题，
与「用户实际会问的话」几乎不重叠；本项目需要一套**独立于题库**的、
用**独立 SQL 复算**给真值的开放措辞基准，用来度量：

  ① Coverage（条件覆盖）：解析出的条件字段 ⊇ 期望字段（漏听一条就算没理解）；
  ② SetIdentity（集合身份）：引擎命中集 == **`truth_sql` 独立复算**的 pid 集（**逐篇**）；
  ③ AnswerCorrect（答案正确）：`expect_count_sql` 给出的计数 == 引擎给的 `total`；
  ④ RefusalQuality（拒答质量）：该拒答的拒了、不该拒的没拒。

★ 为什么「真值」必须用**独立 SQL**而不是引擎复算：审查点名的「自证循环」就是
「引擎自己算的标准、拿引擎自己核」。`truth_sql` 写在基准集里、由人书写，
不走 `retrieve._sql`，二者独立——这才有资格叫验证。

用法：
    python tools/nl_benchmark.py                     # 跑全量（默认规则路，确定性）
    python tools/nl_benchmark.py --mode plan         # 走规划路（需大模型；无模型自动跳过）
    python tools/nl_benchmark.py --id NL015          # 只跑一条
    python tools/nl_benchmark.py --update-baseline   # 把当前结果冻结为基线（**慎用**）

退出码：0 = 全绿；1 = 有失败。
"""
import argparse
import json
import os
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, 'solve'))

CASES = os.path.join(_ROOT, 'tests', 'nl_paraphrase.jsonl')
BASELINE = os.path.join(_ROOT, 'tests', 'nl_baseline.json')


def load_cases(path):
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            out.append(json.loads(line))
    return out


def _fields_of(spec, plan=None):
    """解析结果里**实际表达了哪些条件字段**（供 Coverage 比对）。"""
    got = set()
    import retrieve as R
    if getattr(spec, 'dynasty_any', None) or getattr(spec, 'dynasty', None):
        got.add('dynasty')
    if getattr(spec, 'author_any', None) or getattr(spec, 'author', None):
        got.add('author')
    if getattr(spec, 'cipai_any', None) or getattr(spec, 'cipai', None):
        got.add('cipai')
    if getattr(spec, 'title_any', None) or getattr(spec, 'title', None):
        got.add('title')
    if getattr(spec, 'tail_any', None):
        got.add('lines.tail')
    if getattr(spec, 'tail_pz', None):
        got.add('tail_pz')
    if getattr(spec, 'pz', None):
        got.add('pz')
    if getattr(spec, 'pz_exact', None):
        got.add('pz_exact')
    if getattr(spec, 'tail_each', None):
        got.add('tail_each')
    if getattr(spec, 'parity', None) is not None:
        got.add('parity')
    if getattr(spec, 'scene', None):
        got.add('scene')
    if getattr(spec, 'consist', None):
        got.add('consist')
    if getattr(spec, 'line_q', None):
        got.add('line_q')
    for k in (spec.rng or {}):
        got.add({'ze_min': 'ze_ratio', 'ze_max': 'ze_ratio', 'len_min': 'han_len',
                 'len_max': 'han_len', 'sent_min': 'sent_n', 'sent_max': 'sent_n',
                 'change_min': 'change', 'change_max': 'change',
                 'thr_min': 'threshold', 'thr_max': 'threshold'}.get(k, k))
    # 布尔树（规划路）里出现的字段也算数
    if getattr(spec, 'filters_tree', None):
        import queryplan as QP
        for f in QP._filter_fields(spec.filters_tree):
            got.add(f.rsplit('.', 1)[0])
    if plan:
        import queryplan as QP
        for f in QP._filter_fields(plan.get('filters') or {}):
            got.add(f.rsplit('.', 1)[0])
    return got


def run_case(conn, case, mode='rule', llm=None, verbose=False):
    import ask
    import retrieve as R
    cid, q = case['id'], case['q']
    res = {'id': cid, 'q': q, 'note': case.get('note', '')}
    try:
        spec = R.parse_query(conn, q)
    except Exception as e:                                       # noqa: BLE001
        res.update(ok=False, err='解析异常：%s: %s' % (type(e).__name__, e))
        return res
    plan = None
    if mode == 'plan' and llm is not None:
        try:
            import planner as PL
            plan = PL.plan(conn, llm, q)
        except Exception:                                        # noqa: BLE001
            plan = None
    got = _fields_of(spec, plan)
    res['plan_ok'] = bool(plan)
    want = set(case.get('fields') or [])
    res['fields_got'] = sorted(got)
    res['fields_want'] = sorted(want)
    res['coverage_ok'] = want.issubset(got)
    res['fields_missing'] = sorted(want - got)

    # ② 集合身份：**独立 SQL 复算**
    if case.get('truth_sql'):
        try:
            truth = [r[0] for r in conn.execute(case['truth_sql'])]
        except Exception as e:                                   # noqa: BLE001
            truth = None
            res['err'] = '基准集真值 SQL 出错：%s' % e
        if truth is not None:
            hit = None
            if plan and plan.get('filters'):      # 规划路：以 Plan 的布尔过滤树为准
                try:
                    import queryplan as QP
                    w, a = QP.compile_filters(conn, plan['filters'])
                    hit = [r[0] for r in conn.execute(
                        'SELECT p.pid FROM poems p WHERE %s' % w, a)]
                except Exception:                                # noqa: BLE001
                    hit = None
            if hit is None:
                try:
                    hit = R.hit_pids_of_spec(conn, spec)
                except Exception:                                # noqa: BLE001
                    hit = None
            if hit is None:
                # 兜底：用引擎自己编的 SQL 取（会标注为「引擎侧」）
                where, args = R._sql(spec)
                hit = [r[0] for r in conn.execute(
                    'SELECT p.pid FROM poems p WHERE %s' % where, args)]
            s1, s2 = set(truth), set(hit)
            res['truth_n'] = len(s1)
            res['hit_n'] = len(s2)
            res['extra_n'] = len(s2 - s1)
            res['missing_n'] = len(s1 - s2)
            res['set_ok'] = (not (s2 - s1)) and (not (s1 - s2))
            res['set_extra'] = sorted(s2 - s1)[:3]
            res['set_missing'] = sorted(s1 - s2)[:3]
    # ③ 计数
    if case.get('expect_count_sql'):
        try:
            want_n = conn.execute(case['expect_count_sql']).fetchone()[0]
        except Exception:                                        # noqa: BLE001
            want_n = None
        try:
            ans = ask.answer(conn, q, topk=3, llm=llm, llm_parse=False)
            got_n = ans.get('total')
        except Exception as e:                                   # noqa: BLE001
            got_n = None
            res['err'] = 'answer 异常：%s' % e
        res['count_want'] = want_n
        res['count_got'] = got_n
        res['count_ok'] = (want_n is not None and got_n is not None and want_n == got_n)
    # ④ 拒答质量
    if case.get('refuse'):
        try:
            ans = ask.answer(conn, q, topk=3, llm=llm, llm_parse=False)
            res['refuse_ok'] = bool(ans.get('refused'))
        except Exception:                                        # noqa: BLE001
            res['refuse_ok'] = False

    checks = [res.get('coverage_ok'), res.get('set_ok'), res.get('count_ok'),
              res.get('refuse_ok')]
    checks = [c for c in checks if c is not None]
    res['ok'] = all(checks) if checks else bool(res.get('coverage_ok'))
    return res


def main():
    ap = argparse.ArgumentParser(description='开放自然语言理解基准')
    ap.add_argument('--db', default=os.path.join(_ROOT, 'data', 'corpus.db'))
    ap.add_argument('--cases', default=CASES)
    ap.add_argument('--mode', default='rule', choices=['rule', 'plan'])
    ap.add_argument('--id', default=None, help='只跑某一条（如 NL015）')
    ap.add_argument('--json', default=None, help='把结果写成 JSON 文件')
    ap.add_argument('--update-baseline', action='store_true',
                    help='把当前结果冻结为基线（**只有在确认是改善时才该用**）')
    a = ap.parse_args()

    if a.mode == 'plan':
        os.environ['LVC_PLANNER'] = 'plan'
    cases = load_cases(a.cases)
    if a.id:
        cases = [c for c in cases if c['id'] == a.id]
    conn = sqlite3.connect(a.db)
    conn.row_factory = sqlite3.Row
    llm = None
    if a.mode == 'plan':
        try:
            import llm as L
            llm = L.LLM()
            if not llm.available():
                print('（大模型不可用 → 规划路自动跳过，按规则路跑）')
                llm = None
        except Exception:                                        # noqa: BLE001
            llm = None

    results, n_ok = [], 0
    t0 = __import__('time').time()
    for c in cases:
        r = run_case(conn, c, mode=a.mode, llm=llm)
        results.append(r)
        n_ok += 1 if r.get('ok') else 0
        mark = '✓' if r.get('ok') else '✗'
        detail = ''
        if not r.get('coverage_ok'):
            detail = '漏条件=%s' % (r.get('fields_missing') or [])
        elif r.get('set_ok') is False:
            detail = '集合不符（真值%d 引擎%d：多%d 漏%d）' % (
                r.get('truth_n', -1), r.get('hit_n', -1),
                r.get('extra_n', -1), r.get('missing_n', -1))
        elif r.get('count_ok') is False:
            detail = '计数不符（期望%s 得到%s）' % (r.get('count_want'), r.get('count_got'))
        elif r.get('err'):
            detail = r['err']
        print('%s %-7s %-34s %s' % (mark, c['id'], c['q'][:34], detail))

    total = len(results)
    cov = sum(1 for r in results if r.get('coverage_ok'))
    setc = [r for r in results if r.get('set_ok') is not None]
    setn = sum(1 for r in setc if r.get('set_ok'))
    cnt = [r for r in results if r.get('count_ok') is not None]
    cntn = sum(1 for r in cnt if r.get('count_ok'))
    print('\n———— 汇总（模式=%s，%.1f 秒）————' % (a.mode, __import__('time').time() - t0))
    print('用例总数           : %d' % total)
    print('① 条件覆盖 Coverage : %d/%d' % (cov, total))
    print('② 集合身份 SetIdentity: %d/%d（有真值 SQL 的用例）' % (setn, len(setc)))
    print('③ 计数正确 AnswerCorrect: %d/%d（有期望计数的用例）' % (cntn, len(cnt)))
    print('整体通过           : %d/%d' % (n_ok, total))
    if a.json:
        json.dump(results, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('结果已写入 %s' % a.json)
    if a.update_baseline:
        json.dump({'total': total, 'ok': n_ok, 'coverage': cov, 'set': setn,
                   'set_total': len(setc), 'count': cntn, 'count_total': len(cnt)},
                  open(BASELINE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('基线已更新 → %s' % BASELINE)
        return 0
    if os.path.exists(BASELINE):
        b = json.load(open(BASELINE, encoding='utf-8'))
        worse = (n_ok < b.get('ok', 0) or cov < b.get('coverage', 0)
                 or setn < b.get('set', 0) or cntn < b.get('count', 0))
        print('对比基线：%s（基线 ok=%s 覆盖=%s 集合=%s 计数=%s）'
              % ('★ 有回退 ★' if worse else '无回退', b.get('ok'), b.get('coverage'),
                 b.get('set'), b.get('count')))
        if worse:
            return 1
    return 0 if n_ok == total else 1


if __name__ == '__main__':
    sys.exit(main())
