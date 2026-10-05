# -*- coding: utf-8 -*-
"""reproduce.py —— **一条命令**把整条链跑一遍，并落一份《复现报告》。

为什么要有它：作品答辩最怕「复现不了」。这里把「入库 → 答题 → 评测 → 不变式 → 问答 →
前端视图 → 门禁」全部串起来，并把每一步的**实际输出**（不是预期值）写进报告，
任何人拿到仓库、跑这一条命令，就能看到同一组数字。

用法：
    python reproduce.py                       # 全流程（含建库，约 5–8 分钟）
    python reproduce.py --skip-build          # 跳过建库（已有 corpus.db 时）
    python reproduce.py --quick               # 快速档（跳过保密集与前端对照）
退出码：0 = 所有步骤 PASS；1 = 有步骤失败（报告里逐条列出）。
"""
import argparse
import io
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
D = r'D:\桌面\人文薪火\数据\初赛数据\薪火人文-清词-1000题库-V5版本'
CORPUS = r'D:\桌面\人文薪火\数据\语料'
PUB_Q = os.path.join(D, '公开测试集_700题.jsonl')
SEC_Q = os.path.join(D, '保密验证集_300题_题面.jsonl')
SEC_G = os.path.join(D, '保密验证集_300题_答案.jsonl')
PY = sys.executable          # 真正的解释器在 main() 里用 pick_python() 定


def pick_python(explicit=None):
    """挑一个**真的能跑这个项目**的解释器。

    坑：IDE（PyCharm/VSCode）里的 `python` 往往是另一个虚拟环境，装没装 pypinyin 不一定。
    选错了，脚本会 0.1 秒就退出，报错还看不到——所以这里逐个试依赖，并把选中结果打印出来。
    """
    cands = []
    for c in (explicit, os.environ.get('LVC_PYTHON'), sys.executable,
              shutil.which('python'), r'D:\conda_envs\langchain-env\python.exe',
              r'C:\Python314\python.exe'):
        if c and c not in cands and (os.path.exists(c) or shutil.which(c)):
            cands.append(c)
    for c in cands:
        try:
            r = subprocess.run([c, '-c', 'import pypinyin,sqlite3,json,csv,hashlib'],
                               capture_output=True, timeout=60)
        except Exception:
            continue
        if r.returncode == 0:
            return c, cands
    return None, cands


def run(title, args, tail=8, env_extra=None):
    """跑一步并回收输出（留尾部若干行，失败时把错误要点顶到面前）。"""
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    if env_extra:
        env.update(env_extra)
    t0 = time.time()
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env)
    out = ((r.stdout or '') + (r.stderr or '')).strip().splitlines()
    dt = time.time() - t0
    ok = (r.returncode == 0)
    print('[%s] %-46s %6.1fs  exit=%d' % ('PASS' if ok else 'FAIL', title, dt, r.returncode))
    if not ok:                                   # 失败就把原因贴出来，别让人猜
        for ln in out[-3:]:
            print('        ! %s' % ln)
    return {'title': title, 'cmd': ' '.join(args), 'exit': r.returncode, 'ok': ok,
            'secs': dt, 'tail': out[-tail:] if tail else [], 'all': out}


def main():
    ap = argparse.ArgumentParser(description='一条命令复现全流程 + 出报告')
    ap.add_argument('--skip-build', action='store_true')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--python', default=None, help='指定解释器（默认自动挑一个装了 pypinyin 的）')
    ap.add_argument('--out', default=os.path.join(ROOT, '复现报告.md'))
    args = ap.parse_args()

    global PY
    PY, cands = pick_python(args.python)
    print('使用解释器：%s' % PY)
    if PY is None:
        print('✗ 没找到带 pypinyin 的解释器。试过的有：%s' % cands)
        print('  请先装依赖：pip install -r solve/requirements.txt（或指定 --python <路径>）')
        return 2

    steps = []
    if not args.skip_build:
        steps.append(run('M1 语料入库（58,852 首 / 420,476 句）',
                         [PY, 'build_corpus.py', '--corpus', CORPUS, '--db', 'data/corpus.db',
                          '--verify', '100'], tail=2))
    steps.append(run('答题：公开集 700 题',
                     [PY, 'solve/solver.py', '--question', PUB_Q, '--corpus', CORPUS,
                      '--output', 'answers_700.jsonl'], tail=1))
    steps.append(run('评测：公开集（严格口径）',
                     [PY, 'solve/eval.py', '--pred', 'answers_700.jsonl', '--gold', PUB_Q],
                     tail=2))
    if os.path.exists(SEC_Q) and os.path.exists(SEC_G) and not args.quick:
        steps.append(run('答题：第二套 300 题（仅验收用）',
                         [PY, 'solve/solver.py', '--question', SEC_Q, '--corpus', CORPUS,
                          '--output', 'answers_blind.jsonl'], tail=1))
        steps.append(run('评测：第二套 300 题',
                         [PY, 'solve/eval.py', '--pred', 'answers_blind.jsonl', '--gold', SEC_G],
                         tail=2))
    steps.append(run('不变式检查（15 类，直接查库）', [PY, 'tools/invariant_check.py'], tail=3))
    steps.append(run('问答评测（固定用例集）', [PY, 'tools/qa_eval.py'], tail=5))
    steps.append(run('自检（程序化断言）', [PY, 'solve/selftest.py'], tail=2))
    steps.append(run('护栏真触发（7 道）',
                     [PY, 'solve/test_guards.py', '--question', PUB_Q], tail=2))
    if not args.quick:
        steps.append(run('前端视图构建（Vue3 离线四视图 + 问答页，vite）',
                         ['node', 'frontend/tools/build-all.mjs'], tail=6,
                         env_extra={'LVC_PYTHON': PY})
                     if shutil.which('node') else
                     run('前端数据生成（离线视图数据脚本）', [PY, 'web/build_views.py'], tail=2))
        steps.append(run('全库字段导出（供「全库对照」，防止抽样漏错）',
                         [PY, 'tools/dump_metrics_all.py'], tail=1))
        if shutil.which('node'):
            steps.append(run('逻辑层等价性（core 真源 vs 冻结基线，全库逐字节）',
                             ['node', 'frontend/tools/check-core.cjs'], tail=3))
            steps.append(run('组件冒烟（6 视图 SSR 渲染不报错）',
                             ['node', 'frontend/tools/ssr-smoke.mjs'], tail=3))
            # ⚠ 2026-10-06：`--strict` 只在**类型依赖已装**时才加。否则一台没跑过
            #   `npm install` 的答辩机会因「类型检查 SKIP」被判 FAIL——缺依赖是**环境问题**，
            #   不是代码问题，一刀切 strict 与「一键复现」的目标冲突（外部审查 P1-53 的正确落法：
            #   开发期 SKIP 便利 + 有依赖时严格，二者兼得）。
            _tsbin = os.path.join(ROOT, 'frontend', 'node_modules', '.bin')
            _has_ts = any(os.path.exists(os.path.join(_tsbin, n))
                          for n in ('vue-tsc', 'vue-tsc.cmd', 'tsc', 'tsc.cmd'))
            steps.append(run('类型检查（TypeScript / vue-tsc%s）' % ('，strict' if _has_ts else '，未装依赖则 SKIP'),
                             ['node', 'frontend/tools/check-types.mjs'] + (['--strict'] if _has_ts else []),
                             tail=4))
            steps.append(run('组件文档一致性（docs/组件API.md 与源码不漂移）',
                             ['node', 'frontend/tools/gen-docs.mjs', '--check'], tail=2))
            steps.append(run('前端↔引擎逐字段对照（node，全库 26,742 篇）',
                             ['node', 'web/verify_views.js', '--all'], tail=2))
            steps.append(run('前端渲染门禁（页面拼出的表格不得有 NaN／空表）',
                             ['node', 'web/test_render.js'], tail=3))
            steps.append(run('前端功能门禁（检索／队列／页面／共享文件）',
                             ['node', 'web/test_ui.js'], tail=3))
        else:
            print('[SKIP] 前端三个 node 门禁：本机没有 node（装 Node.js 后可跑；不影响其它步骤）')
        steps.append(run('服务端门禁（检索／理解／成文／对比／问答／解析）',
                         [PY, 'web/test_api.py'], tail=3))
    steps.append(run('条件一致性门禁（条件→检索→展示→计数）',
                     [PY, 'tools/check_conditions.py'], tail=3))
    steps.append(run('分组对比门禁（聚合统计→数字独立复算→方向）',
                     [PY, 'tools/check_agg.py'], tail=3))
    steps.append(run('极值／排序题门禁（哪一首…最高→极值篇独立复算→并列如实）',
                     [PY, 'tools/check_extreme.py'], tail=3))
    steps.append(run('极值题门禁自检（停掉解析器后必须报错）',
                     [PY, 'tools/check_extreme.py', '--selftest'], tail=3))
    steps.append(run('配对题门禁（几对逐位平仄相同的两首词→逐位复算）',
                     [PY, 'tools/check_pair.py'], tail=3))
    steps.append(run('配对题门禁自检（停掉识别器后必须报错）',
                     [PY, 'tools/check_pair.py', '--selftest'], tail=3))
    steps.append(run('双来源一致性门禁（同名同义的量两处定义 → 断言一致）',
                     [PY, 'tools/dual_source_check.py'], tail=3))
    if shutil.which('node'):
        steps.append(run('前端功能门禁自检（把旧 bug 注回去必须报错）',
                         ['node', 'web/test_ui.js', '--selftest'], tail=6))
    steps.append(run('回归门禁（确定性 + 期望哈希）',
                     [PY, 'tools/regress.py', '--questions', PUB_Q, '--gold', PUB_Q,
                      '--tag', '公开', '--sample', '120'], tail=6))

    npass = sum(1 for s in steps if s['ok'])
    lines = ['# 词律探微 · 复现报告', '',
             '生成时间：%s　　运行目录：`%s`　　解释器：`%s`' % (time.strftime('%Y-%m-%d %H:%M:%S'), ROOT, PY), '',
             '## 结果总览', '',
             '| 步骤 | 退出码 | 耗时 | 结果 |', '| --- | --- | --- | --- |']
    for s in steps:
        lines.append('| %s | %d | %.1fs | %s |' % (s['title'], s['exit'], s['secs'],
                                                   'PASS' if s['ok'] else 'FAIL'))
    lines += ['', '合计：**%d / %d 步 PASS**' % (npass, len(steps))]
    bad = [s for s in steps if not s['ok']]
    if bad:
        lines += ['', '## 失败步骤的报错（照着最后几行就能定位）', '']
        for s in bad:
            lines += ['**%s**' % s['title'], '', '```'] + s['all'][-8:] + ['```', '']
    lines += ['', '## 各步骤实际输出（尾部）', '']
    for s in steps:
        lines += ['### %s' % s['title'], '', '```', s['cmd'], '```', '']
        lines += ['```'] + s['tail'] + ['```', '']
    lines += ['## 怎么自己验', '',
              '1. `python build_corpus.py --corpus <语料根> --db data/corpus.db --verify 100`（建库并抽样复算）',
              '2. `python tools/invariant_check.py`（15 类恒等式；0 违反）',
              '3. `python tools/qa_eval.py`（22 条问答用例；含拒答与四类边界）',
              '4. `node web/verify_views.js --all`（前端 JS 与 Python 引擎**全库**逐字段对照，需先跑 tools/dump_metrics_all.py）',
              '5. `node web/test_render.js`（页面渲染门禁：逐字表不得有 NaN、计数必须与独立复算一致）',
              '6. `node web/test_ui.js`（前端功能门禁：检索篇数与 SQL 标尺一致、页面/共享文件自洽）',
              '7. `python web/test_api.py`（服务端门禁：检索／理解／成文／对比／问答／解析）',
              '8. `python web/serve.py` 后浏览器打开 http://127.0.0.1:8000/（问答）与 /browse.html（多条件检索）',
              '9. 浏览器打开 `data/vue/index.html`（Vue3 离线四视图，无 CDN、双击即可）', '',
              '> 报告里写的都是**本次实际输出**；任何一条都能被上面命令重跑验伪。', '']
    io.open(args.out, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    print('\n%s  %d/%d 步 PASS → %s' % ('✓' if npass == len(steps) else '✗', npass, len(steps),
                                        args.out))
    return 0 if npass == len(steps) else 1


if __name__ == '__main__':
    sys.exit(main())
