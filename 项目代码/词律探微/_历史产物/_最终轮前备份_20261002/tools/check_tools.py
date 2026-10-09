# -*- coding: utf-8 -*-
"""check_tools.py —— 给「自检工具自身」加的自检（补 §36 的灯下黑）。

背景：`solve/selftest.py` 检验的是**引擎**，而 `tools/` 里的长跑工具（`loop_check.py` 等）
**没有任何自检覆盖**——于是 `--progress` 是空实现这件事，整整一轮都没被发现：
参数名在、帮助文案在、报告里也写了「已新增」，唯独「打开文件写一行」的代码不在。

本脚本用**极轻量命令**（一条 `python -c`，不是 selftest）验证 `loop_check.py` 对外承诺的能力：

  1. `--progress` 真的落盘，且内容为「已完成 x/y 遍；失败 n；累计墙钟 …」（并发分支）；
  2. 串行分支（`--jobs 1`）同样写进度；
  3. `--expect` 生效：期望子串缺失时必须判失败并返回非 0（否则「通过」毫无意义）；
  4. 汇总里含「首末一致性」判定行（文档承诺的确定性自查）；
  5. `--freeze` 生效：代码树未变时报 ✔；**被改动时必须判作废并返回 2**（否则会出现「假通过」）。

约定：末行含「失败 0」表示全过（与其它门禁同口径）。运行约 10 秒。
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOOP = os.path.join(HERE, 'loop_check.py')
PROG = os.path.join(HERE, '_check_tools_progress.txt')
PROBE_DIR = os.path.join(HERE, '_freeze_probe')
PROBE_FILE = os.path.join(PROBE_DIR, 'x.py')
PY = sys.executable

results = []


def check(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    print('  [%s] %s%s' % ('OK' if cond else '!!', name,
                           ('  —— ' + detail) if (detail and not cond) else ''))


def run_loop(n, jobs, expect, freeze=None, inner=None):
    """不经 shell 直接调 loop_check，规避嵌套引号；--cmd 内部再由 loop_check 走 shell。"""
    if inner is None:
        inner = '"%s" -c "print(1)"' % PY
    if os.path.exists(PROG):
        os.remove(PROG)
    argv = [PY, LOOP, '--cmd', inner, '--n', str(n), '--jobs', str(jobs),
            '--quiet', '--expect', expect, '--progress', PROG]
    if freeze:
        argv += ['--freeze', freeze]
    r = subprocess.run(argv, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    prog = ''
    if os.path.exists(PROG):
        with open(PROG, encoding='utf-8') as f:
            prog = f.read()
    return r.returncode, out, prog


def main():
    print('工具自检（loop_check.py 对外承诺的能力）')

    # 1) 并发分支：进度落盘 + 格式 + 判定行
    rc, out, prog = run_loop(4, 2, '1')
    check('并发分支：4 遍全过、退出码 0', rc == 0, 'rc=%s' % rc)
    check('--progress 落盘', bool(prog), '文件不存在或为空')
    check('--progress 终态为「已完成 4/4 遍」', '已完成 4/4 遍' in prog, repr(prog[:80]))
    check('--progress 含「失败 0」', '失败 0' in prog, repr(prog[:80]))
    check('--progress 含「累计墙钟」', '累计墙钟' in prog, repr(prog[:80]))
    check('汇总含「首末一致性」判定行', '首末一致性' in out, '')

    # 2) 串行分支：同样要写进度（两条分支各写一遍，别只修一条）
    rc, out, prog = run_loop(2, 1, '1')
    check('串行分支：进度也已落盘', bool(prog) and '已完成 2/2 遍' in prog, repr(prog[:80]))

    # 3) --expect 必须真的能判失败（否则「通过」是假的）
    rc, out, prog = run_loop(2, 2, '绝不可能出现的子串XYZ')
    check('--expect 缺失时判失败且退出码非 0', rc != 0, 'rc=%s' % rc)
    check('--expect 缺失时汇总记「失败 2」', '失败 2' in out, '')

    # 4) --freeze：代码树未被改动 → ✔
    rc, out, prog = run_loop(3, 2, '1', freeze='solve')
    check('--freeze 干净时打印冻结指纹', '代码树冻结基线' in out, '')
    check('--freeze 干净时校验通过（含「未变」）', '代码树冻结校验' in out and '未变' in out, '')

    # 5) --freeze：源码被改动 → 必须判「作废」并返回 2（防「假通过」）
    os.makedirs(PROBE_DIR, exist_ok=True)
    with open(PROBE_FILE, 'w', encoding='utf-8') as f:
        f.write('x = 1\n')
    # 这条命令在每遍里都往受控文件追加一行 —— 等价于「跑的时候有人在改代码」
    inner = '"%s" -c "open(r\'%s\', \'a\', encoding=\'utf-8\').write(\'y\\n\')"' % (PY, PROBE_FILE)
    rc, out, prog = run_loop(2, 2, '1', freeze=PROBE_DIR, inner=inner)
    check('--freeze 检测到改动并返回 2', rc == 2, 'rc=%s' % rc)
    check('--freeze 检测到改动时打印「判定作废」', '判定作废' in out, '')
    check('--freeze 检测到改动时列出被改文件', 'x.py' in out, '')

    for p in (PROG,):
        if os.path.exists(p):
            os.remove(p)
    if os.path.isdir(PROBE_DIR):
        shutil.rmtree(PROBE_DIR, ignore_errors=True)

    nfail = sum(1 for _, ok, _ in results if not ok)
    print('-' * 60)
    print('工具自检：通过 %d，失败 %d' % (len(results) - nfail, nfail))
    return 0 if nfail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
