# -*- coding: utf-8 -*-
"""check_all.py —— **统一门禁入口**：一条命令跑完本项目全部关键门禁。

为什么要有它（工程机制「单一入口」）
------------------------------------
本项目的门禁**很多**（`reproduce.py` 串了 20+ 步），但对日常「改一处 → 验一下」来说太重：
改完一个检索分支，你可能只想快速确认「语法没错 / 自检没红 / 交付答案 SHA256 没变」，
而不是每次都跑 5–8 分钟的全流程。散落各处就会**忘记跑哪几道**，于是出现
「改完忘了验就提交」的缺口。

本脚本把**关键门禁**收成一个入口，分两档：
  · `--fast`（约 10–20 秒）：交付答案 SHA256 零回归 + selftest。
    ——**pre-commit 钩子与「改完随手验」用这一档**。
  · 默认（全档，约 20–25 分钟）：fast 全部 + **双集零回归（regress）** + test_api
    + check-core + verify_1000。
    ——**提交前 / 答辩前 / CI 用这一档**。

设计红线（与项目纪律一致）
--------------------------
1. **不重复造轮子**：每一档都只是**调用**既有脚本（regress / selftest / test_api /
   check-core / verify_1000），不重写任何判据——单一来源口径。
2. **失败即停**（默认）：任一门禁非零退出 → 立即停并打印**失败要点**（尾部若干行），
   不把「没跑」伪装成「通过」。
3. **零回归锚点内建**：交付答案 `answers_700.jsonl` 的 SHA256 必须等于
   `GOLD_SHA256`；不等 → 直接判 FAIL 并给出手工核对指引。这是**结构性隔离**的守门人。
4. **可跳过**：缺语料 / 缺 node 时相关项**显式 SKIP**（打印原因），不算通过、也不算失败。

用法
----
    python tools/check_all.py               # 全档（提交前 / CI）
    python tools/check_all.py --fast        # 快速档（pre-commit / 随手验）
    python tools/check_all.py --list        # 只列要跑哪些门禁
    python tools/check_all.py --only sha256,selftest
退出码：0 = 全部（未被跳过地）通过；1 = 有门禁失败；2 = 环境不满足（找不到解释器）。
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ★ 零回归锚点：交付答案的**期望 SHA256**（与 `_历史产物` 冻结值、开源版一致）。
#   改这个值 **必须** 同时说明「交付答案为何应当变化」——它是一道**结构性隔离**的守门人。
GOLD_SHA256 = 'bf863368ffaf85d89ddd1aae28b334be5a0fdfd532a365fa9f8110a747ff7d1e'
ANSWERS = os.path.join(ROOT, 'answers_700.jsonl')


def pick_python(explicit=None):
    """挑一个**真的能跑这个项目**的解释器（与 `reproduce.py` 同口径，避免选错环境）。"""
    cands = []
    for c in (explicit, os.environ.get('LVC_PYTHON'), sys.executable,
              shutil.which('python'), r'D:\conda_envs\langchain-env\python.exe',
              r'C:\Python314\python.exe'):
        if c and c not in cands and (os.path.exists(c) or shutil.which(c)):
            cands.append(c)
    for c in cands:
        try:
            r = subprocess.run([c, '-c', 'import pypinyin,sqlite3,json,hashlib'],
                               capture_output=True, timeout=60)
        except Exception:
            continue
        if r.returncode == 0:
            return c
    return None


def pick_node():
    """挑一个可用的 node（check-core 需要；缺失则该门禁 SKIP，不算失败）。"""
    for c in (os.environ.get('LVC_NODE'), shutil.which('node'),
              r'D:\node\node.exe',
              os.path.expanduser('~/.workbuddy-ai/binaries/node/versions/22.22.2-6/node.exe')):
        if c and (os.path.exists(c) or shutil.which(c)):
            return c
    return None


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ 各门禁定义
def gate_sha256(py):
    """门禁 A：交付答案 SHA256 恒等（零回归锚点）。**纯 Python，无外部依赖。**"""
    def _run():
        if not os.path.exists(ANSWERS):
            return 'SKIP', '缺少 answers_700.jsonl（未随本副本分发？）', None
        got = sha256_of(ANSWERS)
        if got == GOLD_SHA256:
            return 'PASS', 'SHA256=%s…%s（与锚点一致）' % (got[:12], got[-6:]), None
        return ('FAIL',
                'SHA256=%s…%s ≠ 锚点 %s…%s（交付答案已变！）'
                % (got[:12], got[-6:], GOLD_SHA256[:12], GOLD_SHA256[-6:]),
                '若本次改动**不应**影响交付链，请查：\n'
                '      ① solver.py/official.py 是否被问答链污染（结构性隔离被破坏）；\n'
                '      ② data/corpus.db 是否被改动；\n'
                '      ③ 确认无误要改锚点时，务必同步改 check_all.py 的 GOLD_SHA256。')
    return ('交付答案 SHA256 零回归', _run)


def gate_regress(py):
    """门禁 · **双集零回归**（regress.py；期望哈希**只从 golden_sha.json 读一处**）。

    ⚠ 2026-10-13 补（真缺口）：此前统一门禁只校验 `answers_700.jsonl` 的 SHA256，
    **没有跑双集回归**——公开集哈希一致，只说明「 engines 对公开 700 题没变」，
    **不等于** 300 题保密集也没变（两个是独立哈希）。
    现在按 skill 的「门禁四件套」口径补齐：**公开 + 第二套都跑，都逐字节一致才算过**。
    题库不在项目内 → 定位不到时**显式 SKIP**（不算通过，也不误报失败）。
    """
    def _qbase():
        env = os.environ.get('LVC_QUESTIONS_DIR')
        cands = []
        if env:
            cands.append(env)
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cands += [
            os.path.join(here, '..', '..', '数据', '初赛数据',
                         '薪火人文-清词-1000题库-V5版本'),
            os.path.join(here, '..', '..', '数据', '初赛数据'),
        ]
        for c in cands:
            if os.path.isdir(c):
                return c
        return None

    def _expect(tag):
        try:
            import json as _json
            with open(os.path.join(ROOT, 'solve', 'data', 'golden_sha.json'),
                      encoding='utf-8') as f:
                return (_json.load(f) or {}).get(tag)
        except Exception:                                      # noqa: BLE001
            return None

    def _run():
        base = _qbase()
        if base is None:
            return 'SKIP', '未找到题库目录（设 LVC_QUESTIONS_DIR 指向题库版本目录）', None
        pub_q = os.path.join(base, '公开测试集_700题.jsonl')
        sec_q = os.path.join(base, '保密验证集_300题_题面.jsonl')
        sec_g = os.path.join(base, '保密验证集_300题_答案.jsonl')
        if not os.path.exists(pub_q):
            return 'SKIP', '题库目录下没有公开测试集_700题.jsonl', None
        runs = [(pub_q, pub_q, '公开', _expect('公开'))]
        if os.path.exists(sec_q) and os.path.exists(sec_g):
            runs.append((sec_q, sec_g, '第二套', _expect('第二套')))
        else:
            return 'SKIP', '缺保密验证集题面/答案（第二套回归无法执行）', None
        problems, briefs = [], []
        for q, g, tag, exp in runs:
            args = [py, 'tools/regress.py', '--questions', q]
            if g:
                args += ['--gold', g]
            if exp:
                args += ['--expect', exp]
            args += ['--tag', tag, '--sample', '120']
            status, brief, detail = _cmd(args, tail=8)()
            briefs.append('%s:%s' % (tag, brief[:40]))
            if status != 'PASS':
                problems.append('[%s] %s' % (tag, brief))
        if problems:
            return 'FAIL', '；'.join(problems)[:200], None
        return 'PASS', '｜'.join(briefs), None
    return ('双集零回归（regress 公开+第二套）', _run)


def gate_selftest(py):
    """门禁 B：程序化断言自检（selftest.py）。"""
    return ('自检（selftest.py）', _cmd([py, 'solve/selftest.py'], tail=6))


def gate_test_api(py):
    """门禁 C：服务端门禁（web/test_api.py，不需要起服务、不联网）。"""
    return ('服务端门禁（web/test_api.py）', _cmd([py, 'web/test_api.py'], tail=8))


def gate_check_core(node):
    """门禁 D：前端逻辑层等价性（core 真源 vs 冻结基线，全库逐字节）。"""
    def _run():
        if node is None:
            return 'SKIP', '本机没有 node（装 Node.js 后可跑）', None
        if not (os.path.exists(os.path.join(ROOT, 'data', 'web_poems.json'))
                and os.path.exists(os.path.join(ROOT, 'data', 'expect_search.json'))):
            return 'SKIP', '缺少 data/web_poems.json / expect_search.json 快照', None
        return _cmd([node, 'frontend/tools/check-core.cjs'], tail=8)()
    return ('前端逻辑层等价性（check-core）', _run)


def gate_verify_1000(py):
    """门禁 E：1000 题逐题复核（答非所问 + 准确性）。**慢项，只有全档才跑。**"""
    def _run():
        if not os.path.exists(os.path.join(ROOT, 'data', 'corpus.db')):
            return 'SKIP', '缺少 data/corpus.db（未随本副本分发？）', None
        return _cmd([py, 'tools/verify_1000.py'], tail=6)()
    return ('1000 题逐题复核（verify_1000）', _run)


def _cmd(args, tail=8):
    """跑一条命令并回收输出（与 reproduce.run 同风格，失败时把尾部贴出来）。"""
    def _run():
        env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
        try:
            r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', env=env, timeout=1800)
        except Exception as e:                                   # noqa: BLE001
            return 'FAIL', '%s: %s' % (type(e).__name__, e), None
        out = ((r.stdout or '') + (r.stderr or '')).strip().splitlines()
        ok = (r.returncode == 0)
        brief = 'exit=%d' % r.returncode
        # 从输出里捞一行「最有信息量」的汇总（如「检查项 N，失败 M」）
        for ln in reversed(out):
            if any(k in ln for k in ('检查项', '不符', '失败', '全部通过', 'PASS', '项 0')):
                brief = ln.strip()
                break
        detail = None if ok else '\n'.join('      ! %s' % x for x in out[-3:])
        return ('PASS' if ok else 'FAIL'), brief, detail
    return _run


def build_gates(py, node, fast):
    """按档位组装门禁列表（顺序：最快的、最能挡住低级错误的排前面）。"""
    gates = [gate_sha256(py), gate_selftest(py)]
    if not fast:
        # ★ 2026-10-13：双集回归提到最前——它比 SHA256 更强（不只比哈希，
        #   还做「确定性 + 复算一致率 + 泛化抽样 + 引文原样性」），且覆盖第二套。
        gates.insert(1, gate_regress(py))
        gates.append(gate_test_api(py))
        gates.append(gate_check_core(node))
        gates.append(gate_verify_1000(py))
    return gates


def main():
    ap = argparse.ArgumentParser(description='统一门禁入口（改完随手验 / 提交前 / CI 共用）')
    ap.add_argument('--fast', action='store_true',
                    help='快速档：语法类 + SHA256 + selftest（pre-commit 用；约 10–20 秒）')
    ap.add_argument('--only', default=None,
                    help='只跑指定门禁（逗号分隔：sha256,selftest,regress,test_api,'
                         'check_core,verify_1000）')
    ap.add_argument('--python', default=None, help='指定解释器（默认自动挑）')
    ap.add_argument('--list', action='store_true', help='只列出将要跑的门禁，不执行')
    args = ap.parse_args()

    py = pick_python(args.python)
    node = pick_node()

    gates = build_gates(py, node, args.fast)
    if args.only:
        want = {s.strip() for s in args.only.split(',') if s.strip()}
        keymap = {'sha256': '交付答案', 'selftest': '自检', 'regress': '双集零回归',
                  'test_api': '服务端', 'check_core': '逻辑层', 'verify_1000': '1000 题'}
        gates = [g for g in gates
                 if any(k in g[0] for kk, k in keymap.items() if kk in want)]

    if args.list:
        print('将要跑的门禁（%s档）：' % ('快速' if args.fast else '全'))
        for name, _ in gates:
            print('  · %s' % name)
        return 0
    print('=' * 74)
    print('词律探微 · 统一门禁  [%s档]' % ('快速' if args.fast else '全'))
    print('解释器：%s' % (py or '✗ 未找到（请 pip install -r solve/requirements.txt）'))
    print('node  ：%s' % (node or '（无，check-core 将 SKIP）'))
    print('=' * 74)
    if py is None:
        print('✗ 没找到带 pypinyin 的解释器，无法跑门禁。')
        return 2

    n_pass = n_fail = n_skip = 0
    fails = []
    t_all = time.time()
    for name, fn in gates:
        t0 = time.time()
        try:
            status, brief, detail = fn()
        except Exception as e:                                   # noqa: BLE001
            status, brief, detail = 'FAIL', '%s: %s' % (type(e).__name__, e), None
        dt = time.time() - t0
        mark = {'PASS': '✓ PASS', 'FAIL': '✗ FAIL', 'SKIP': '· SKIP'}[status]
        print('[%s] %-34s %6.1fs  %s' % (mark, name, dt, brief))
        if detail:
            print(detail)
        if status == 'PASS':
            n_pass += 1
        elif status == 'FAIL':
            n_fail += 1
            fails.append(name)
        else:
            n_skip += 1

    print('=' * 74)
    print('汇总：通过 %d ｜ 失败 %d ｜ 跳过 %d ｜ 总耗时 %.1f 秒'
          % (n_pass, n_fail, n_skip, time.time() - t_all))
    if fails:
        print('失败门禁：%s' % '、'.join(fails))
        return 1
    if n_skip:
        print('（有 %d 项因环境缺失被跳过——不算通过，见上方原因）' % n_skip)
    print('全部（未被跳过的）门禁通过。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
