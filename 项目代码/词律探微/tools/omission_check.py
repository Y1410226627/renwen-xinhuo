# -*- coding: utf-8 -*-
"""omission_check.py —— 遗漏集测试（negative-space tests）。

为什么要有它
------------
项目已有的门禁（235 selftest / 140 test_api / 522242 test_render / …）擅长测
「**返回出来的东西对不对**」，却不擅长测「**本来应该返回的有没有被漏掉**」。
结果这类缺陷全部逃过门禁：

  · `∀`（每一句都满足 P）对**空篇**（sent_n=0 / han_len=0）的语义：SQL 与 Python 复核不一致；
  · `≥0` / `=0` / `条数∈[0,N]`：SQL 用 `GROUP BY … HAVING COUNT(*)` → **0 命中的篇根本不会出现**
    （GROUP BY 只会为「至少有一行」的 pid 建组）；
  · `parity`（句位奇偶）/ `consist`（声情走向）：SQL 有条件但**没有独立复核**。

本脚本的判据
------------
对每一类条件，比较两个**集合**（逐 pid）：

    SQL 命中集     = `retrieve._sql(spec)` 生成的 WHERE 在 poems 上命中的 pid
    Python 复核集  = 对**全库**每篇调用 `retrieve.verify_spec_on_poem()` 且**无违规**的 pid

两者差集非空 ⇒ **FAIL**（差集 = 有一路认为该召回、另一路漏掉/多召的篇）。
「空篇 / 0 命中」这一类**必须全库扫描**才能测到遗漏，故默认对全库扫描（`--sample` 可缩样）。

注意：判据是「SQL 集 == Python 集」，不是「等于我写的期望值」。
本脚本**不修改** solve/** 的任何文件；若 solve/** 正在被并行修改而报错，如实记录，不改判据。

用法
----
    python tools/omission_check.py                  # 全库扫描，退出码 0=全过 / 1=有差集
    python tools/omission_check.py --sample 8000    # 抽样 8000 篇做 Python 复核（快，仅供自查）
    python tools/omission_check.py --only 3         # 只跑第 3 类
    python tools/omission_check.py --list           # 列出全部条件类
退出码：0 = 所有类 SQL 集与 Python 集逐 pid 一致；1 = 存在差集或运行错误。
"""
import argparse
import os
import sqlite3
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import retrieve as R                                              # noqa: E402


# --------------------------------------------------------------------------- 索引
def load_index(conn):
    """一次性把复核/理论所需的量读进内存（全库）。"""
    tot = Counter()                 # pid -> 句数
    tail_c = defaultdict(Counter)   # 句脚字 -> (pid -> 该句脚出现次数)
    par0 = Counter()                # pid -> idx 为偶数（句位 1,3,5…）的句数
    for pid, idx, tail in conn.execute('SELECT pid, idx, tail FROM lines'):
        tot[pid] += 1
        if idx % 2 == 0:
            par0[pid] += 1
        if tail:
            tail_c[tail][pid] += 1
    scene, change = {}, {}
    for pid, sc, ch in conn.execute('SELECT pid, scene, change FROM poems'):
        scene[pid] = sc
        change[pid] = ch
    return tot, tail_c, par0, scene, change


# --------------------------------------------------------------------------- spec 构造
def mk(line_q=None, **attrs):
    """直接构造一个 QuerySpec（隔离「算子语义」，避开 parse_query 的识别盲区）。"""
    s = R.QuerySpec()
    if line_q is not None:
        s.line_q = dict(line_q)
    for k, v in attrs.items():
        setattr(s, k, v)
    return R._finalize(s)


# --------------------------------------------------------------------------- 条件类
# theory(idx) -> set(pid)：独立于 verify 与 SQL 的「应有集合」（能用集合论定义时才给）。
def _cnt(tail_c, char, pid):
    return tail_c[char].get(pid, 0)


def _theory_all(idx):
    return set(idx['all'])


def _theory_cnt_cmp(idx, char, fn):
    tc = idx['tail_c'][char]
    return {pid for pid in idx['all'] if fn(tc.get(pid, 0))}


def _build_cases():
    cases = []

    # 1) ∀：每一句都满足 P
    cases.append(dict(
        label='∀（每一句都满足 P）  P = 句脚字「酒」',
        factory=lambda: mk({'op': '∀', 'pred': ('tail', '酒')}),
        theory=lambda idx: {pid for pid in idx['all']
                            if _cnt(idx['tail_c'], '酒', pid) == idx['tot'].get(pid, 0)},
        theory_note='（空真口径）空篇（0 句）按「空真」应**算满足 ∀**（0==0）。',
        hint='SQL 的 ∀ 分支多了一条 `p.pid IN (SELECT l.pid FROM lines l)` 二次约束，'
             '会把**空篇**排除；而 verify 的 ∀ 分支 n==tot 对空篇判 0==0＝通过 → 分歧点＝空篇。',
    ))

    # 2) ∄：没有任何一句满足 P
    cases.append(dict(
        label='∄（没有任何一句满足 P）  P = 句脚字「酒」',
        factory=lambda: mk({'op': '∄', 'pred': ('tail', '酒')}),
        theory=lambda idx: _theory_cnt_cmp(idx, '酒', lambda n: n == 0),
    ))

    # 3) 正好 0 句满足 P（理论 = 不含 P 的所有篇）
    cases.append(dict(
        label='=0（正好 0 句满足 P）  P = 句脚字「酒」',
        factory=lambda: mk({'op': '=k', 'pred': ('tail', '酒'), 'k': 0}),
        theory=lambda idx: _theory_cnt_cmp(idx, '酒', lambda n: n == 0),
        theory_note='=0 的语义**等价于 ∄**（不含 P 的所有篇，含空篇）。',
        hint='SQL 用 `WHERE 谓词 GROUP BY pid HAVING COUNT(*)=0`——GROUP BY 只会为'
             '「至少有一行」的 pid 建组，COUNT(*)=0 永不成立 → SQL 恒空集；'
             '应有集合 = 不含 P 的所有篇。',
    ))

    # 4) 至少 0 句满足 P（理论 = 全集）
    cases.append(dict(
        label='≥0（至少 0 句满足 P）  P = 句脚字「酒」',
        factory=lambda: mk({'op': '≥k', 'pred': ('tail', '酒'), 'k': 0}),
        theory=_theory_all,
        theory_note='≥0 恒真 → 应有集合 = **全集**（58852）。',
        hint='SQL 的 `HAVING COUNT(*)>=0` 只作用于「已建组的 pid」，'
             '0 命中的篇根本没建组 → 被静默漏掉；应有集合为全集。',
    ))

    # 5) 满足句数在 0~2 之间
    cases.append(dict(
        label='条数∈[0,2]（满足句数在 0~2 之间）  P = 句脚字「酒」',
        factory=lambda: mk({'op': '条数∈[a,b]', 'pred': ('tail', '酒'), 'ka': 0, 'kb': 2}),
        theory=lambda idx: _theory_cnt_cmp(idx, '酒', lambda n: 0 <= n <= 2),
        theory_note='区间含下界 0 ⇒ 应有集合**必须含「0 命中的篇」**。',
        hint='与 =0/≥0 同源：`HAVING COUNT(*) BETWEEN 0 AND 2` 依赖「已建组」，'
             '0 命中的篇被漏掉；而 0 落在区间 [0,2] 内，本应被召回。',
    ))

    # 6) 至少 2 句满足 P（常见正例，防回归）
    cases.append(dict(
        label='≥2（至少 2 句满足 P，正例防回归）  P = 句脚字「愁」',
        factory=lambda: mk({'op': '≥k', 'pred': ('tail', '愁'), 'k': 2}),
        theory=lambda idx: _theory_cnt_cmp(idx, '愁', lambda n: n >= 2),
    ))

    # 7) 正好 k 句满足 P（k≥1）
    cases.append(dict(
        label='=3（正好 3 句满足 P，k≥1）  P = 句脚字「愁」',
        factory=lambda: mk({'op': '=k', 'pred': ('tail', '愁'), 'k': 3}),
        theory=lambda idx: _theory_cnt_cmp(idx, '愁', lambda n: n == 3),
    ))

    # 8) parity（句位奇偶）
    cases.append(dict(
        label='parity（句位奇偶）∄ 偶数句位句  —— 有 SQL 条件，检查有无独立复核',
        factory=lambda: mk({'op': '∄', 'pred': ('parity', 0)}),
        theory=lambda idx: {pid for pid in idx['all'] if idx['par0'].get(pid, 0) == 0},
        theory_note='「无偶数句位句」只可能命中**空篇**（idx 从 0 起，非空篇必有偶数句位句）。',
        hint='verify_spec_on_poem 的 `_lines_hit()` **没有 parity 分支**（返回 None）→ '
             '复核等于放行全部，SQL 侧条件无人兜底。',
    ))

    # 9) consist（声情走向）
    cases.append(dict(
        label='consist（声情标注为「后段上升」但实测前后段相反）',
        factory=lambda: mk(consist='后段上升', scene='后段上升'),
        theory=lambda idx: {pid for pid in idx['all']
                            if idx['scene'].get(pid) == '后段上升'
                            and idx['change'].get(pid) is not None
                            and idx['change'].get(pid) < 0},
        theory_note='SQL 侧 = scene=上升 AND change<0；verify 侧不查 change 符号 → 预期不一致。',
        hint='① verify 未复核 consist 的 change 符号条件（放行全部「标注=上升」的篇）；'
             '② 语料里 `scene` 由 `change` 符号派生（上升⟺change>0），故 SQL 的'
             '`scene=上升 AND change<0` 恒为空集——条件本身不可满足。',
    ))
    return cases


# --------------------------------------------------------------------------- 运行
def _pids_of_sql(conn, spec):
    where, args = R._sql(spec)
    return set(r[0] for r in conn.execute('SELECT p.pid FROM poems p WHERE ' + where, args)), where


def _name_of(names, pid):
    n = names.get(pid)
    if not n:
        return pid
    cp, ti, au = n
    piece = '·'.join(x for x in (cp, ti) if x) or pid
    return '%s（%s）' % (piece, au or '佚名')


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='遗漏集测试：对每类条件比较 SQL 命中集 与 Python 逐篇复核集（逐 pid），差集非空即 FAIL。',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--sample', type=int, default=0,
                    help='Python 复核的抽样篇数（0=全库，默认；抽样仅供快速自查）')
    ap.add_argument('--only', type=int, default=0, help='只跑第 N 类（1 起；0=全部）')
    ap.add_argument('--max-report', type=int, default=5, help='每类最多打印的差集样例篇数')
    ap.add_argument('--list', action='store_true', help='列出全部条件类后退出')
    args = ap.parse_args(argv)

    cases = _build_cases()
    if args.list:
        for i, c in enumerate(cases, 1):
            print('%2d) %s' % (i, c['label']))
        return 0

    if not os.path.isfile(args.db):
        print('✗ 找不到数据库：%s' % args.db)
        return 1

    conn = sqlite3.connect(args.db)
    n_poems = conn.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
    n_empty = conn.execute('SELECT COUNT(*) FROM poems WHERE sent_n=0 OR han_len=0 '
                           'OR han_len IS NULL').fetchone()[0]
    n_noline = conn.execute('SELECT COUNT(*) FROM poems p '
                            'WHERE NOT EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid)').fetchone()[0]

    print('=' * 78)
    print('遗漏集测试（negative-space tests）  ——  SQL 命中集 vs Python 逐篇独立复核集')
    print('=' * 78)
    print('数据库：%s' % args.db)
    print('全库篇数：%d    空篇（无句/0字）：%d    无 lines 记录的篇：%d' % (n_poems, n_empty, n_noline))
    print('判据：对每类条件逐 pid 比较【SQL 命中集】与【Python 复核集(verify_spec_on_poem 无违规)】，')
    print('      差集非空即 FAIL。（差集 = 有一路认为该召回、另一路漏掉/多召的篇）')
    if args.sample:
        print('⚠ 抽样模式：Python 复核只扫 %d 篇（非全库），结论仅供自查。' % args.sample)
    print('')

    t0 = time.time()
    tot_t, tail_c, par0, scene, change = load_index(conn)
    allp = [r[0] for r in conn.execute('SELECT pid FROM poems')]
    names = {r[0]: (r[1], r[2], r[3]) for r in
             conn.execute('SELECT pid, cipai, title, author FROM poems')}
    idx = {'all': allp, 'tot': tot_t, 'tail_c': tail_c, 'par0': par0,
           'scene': scene, 'change': change}
    print('已建索引：seg %.1fs' % (time.time() - t0))

    scan = allp if not args.sample else allp[:args.sample]

    n_inconsistent = 0
    n_run = 0
    for i, case in enumerate(cases, 1):
        if args.only and i != args.only:
            continue
        n_run += 1
        print('-' * 78)
        print('[%d/%d] %s' % (i, len(cases), case['label']))
        try:
            spec = case['factory']()
            sql_set, where = _pids_of_sql(conn, spec)
        except Exception as e:                                    # solve/** 可能正被改坏
            print('  ✗ 运行错误（构造 spec / 生成 SQL 失败）：%s: %s' % (type(e).__name__, e))
            n_inconsistent += 1
            continue

        t = time.time()
        py_set = set()
        verify_err = None
        try:
            for pid in scan:
                if not R.verify_spec_on_poem(conn, pid, spec):    # 无违规 = 复核通过
                    py_set.add(pid)
        except Exception as e:
            verify_err = '%s: %s' % (type(e).__name__, e)
        dt = time.time() - t

        sql_only = sorted(sql_set - py_set)     # SQL 认为命中、Python 复核判不通过
        py_only = sorted(py_set - sql_set)      # Python 复核通过、SQL 却漏掉
        diff = sql_only + py_only

        print('  SQL 命中：%d 篇      Python 复核命中：%d 篇      （复核 %.1fs）'
              % (len(sql_set), len(py_set), dt))
        if 'theory' in case and case['theory'] is not None:
            th = case['theory'](idx)
            print('  理论应有：%d 篇%s' % (len(th), ('    ← %s' % case['theory_note'])
                                          if case.get('theory_note') else ''))
            if th != sql_set:
                print('    · SQL 侧偏离理论：%d 篇' % len(th ^ sql_set))
            if th != py_set:
                print('    · Python 侧偏离理论：%d 篇' % len(th ^ py_set))
        if verify_err:
            print('  ✗ verify_spec_on_poem 抛错：%s' % verify_err)

        if not diff:
            print('  => PASS（SQL 集 == Python 集）')
            continue

        n_inconsistent += 1
        print('  => FAIL：两者差集 %d 篇' % len(diff))
        print('     · 仅 SQL 命中 / Python 复核不通过：%d 篇' % len(sql_only))
        print('     · 仅 Python 复核通过 / SQL 未命中：%d 篇' % len(py_only))
        if case.get('hint'):
            print('     归因：%s' % case['hint'])
        for tag, sample in (('仅Py', py_only), ('仅SQL', sql_only)):
            for pid in sample[:args.max_report]:
                print('       [%s] %s  %s' % (tag, pid, _name_of(names, pid)))
            if len(sample) > args.max_report:
                print('       [%s] …（其余 %d 篇略）' % (tag, len(sample) - args.max_report))

    print('')
    print('=' * 78)
    print('遗漏集测试：%d 类条件，%d 类存在不一致' % (n_run, n_inconsistent))
    print('=' * 78)
    conn.close()
    return 1 if n_inconsistent else 0


if __name__ == '__main__':
    sys.exit(main())
