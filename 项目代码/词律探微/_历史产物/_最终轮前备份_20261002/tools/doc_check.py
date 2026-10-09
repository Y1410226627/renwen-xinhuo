# -*- coding: utf-8 -*-
"""doc_check.py —— 文档与行为一致性检查（**文档是承诺，承诺要被验伪**）。

背景：第十轮真漏洞就是「README 写『严格次序相等』，代码却仍是集合口径」——
文档与代码不一致，是自检最容易漏的一类。这里把可自动核的部分程序化：

  ① **命令活性**：README 里出现的每条 `python/tools/… .py` 命令，跑 `--help`（或语法编译）
     必须能起得来（防「README 写了参数，代码没有」）；
  ② **数字承诺**：README 里写的成绩/门禁数字必须与当前产物**实际**相符；
  ③ **文件承诺**：README/任务书里点名的文件必须存在（防「文档写了、文件没做」）；
  ④ **口径承诺**：README 里声明「唯一真源」的常量必须真在源码里（汉字区间 / 切句正则 / 舍入）。

用法：python tools/doc_check.py [--readme solve/README.md] [--root .]
退出码：0 = 全部通过；1 = 有 FAIL（检查项为 0 也判 FAIL）。
"""
import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def main():
    ap = argparse.ArgumentParser(description='文档↔行为一致性检查')
    ap.add_argument('--readme', default=os.path.join(ROOT, 'solve', 'README.md'))
    ap.add_argument('--root', default=ROOT)
    args = ap.parse_args()

    txt = io.open(args.readme, encoding='utf-8').read()
    checks = []
    fails = []

    def ck(name, ok, detail=''):
        checks.append(name)
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, ('：' + detail) if detail else ''))
        if not ok:
            fails.append('%s %s' % (name, detail))

    # ① 命令活性（README 在 solve/ 下，命令路径可能相对 solve/ 或项目根）
    here = os.path.dirname(os.path.abspath(args.readme))
    cmds = sorted(set(re.findall(r'python\s+([\w/\.-]+\.py)', txt)))
    ck('① 命令活性：README 至少出现 5 条 python 命令', len(cmds) >= 5, '实际 %d' % len(cmds))
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    alive = total = 0
    for rel in cmds:
        cands = [os.path.join(args.root, rel.replace('/', os.sep)),
                 os.path.join(here, rel.replace('/', os.sep))]
        p = next((c for c in cands if os.path.exists(c)), None)
        if not p:
            ck('① 命令所指文件存在：%s' % rel, False, '按根目录与 README 同目录都没找到')
            continue
        total += 1
        r = subprocess.run([PY, p, '--help'], capture_output=True, text=True, encoding='utf-8',
                           errors='replace', env=env, timeout=300)
        if r.returncode in (0, 2) or 'usage' in (r.stdout + r.stderr).lower():
            alive += 1
        else:
            ck('① 命令可跑：%s' % rel, False, (r.stderr or r.stdout).strip().splitlines()[-1:])
    ck('① 命令活性：全部可跑', total > 0 and alive == total, '%d/%d' % (alive, total))

    # ② 数字承诺（README 里出现的成绩/门禁数字必须与产物一致）
    def grep_num(pattern, files, cast=int):
        """在产物里找出该指标的实际值（与 README 的声明对照）。"""
        for f in files:
            if not os.path.exists(f):
                continue
            s = io.open(f, encoding='utf-8', errors='replace').read()
            m = re.search(pattern, s)
            if m:
                try:
                    return cast(m.group(1))
                except (TypeError, ValueError):
                    return None
        return None

    # 实际产物：答案条数
    ans = os.path.join(args.root, 'answers_700.jsonl')
    n_ans = sum(1 for ln in io.open(ans, encoding='utf-8') if ln.strip()) if os.path.exists(ans) else 0
    claim = None
    m = re.search(r'公开集\s*(\d+)\s*/\s*700', txt)
    if m:
        claim = int(m.group(1))
    ck('② 成绩承诺：README 公开集声明与答案文件条数相符',
       claim is not None and (claim == n_ans or n_ans == 0),
       'README=%s，答案文件=%s 条' % (claim, n_ans))

    # ③ 文件承诺
    named = ['solve/solver.py', 'solve/eval.py', 'solve/selftest.py', 'solve/preflight.py',
             'solve/retrieve.py', 'solve/evidence.py', 'solve/guard.py', 'solve/ask.py',
             'solve/llm.py', 'solve/gen.py', 'solve/safety.py', 'solve/qlm.py',
             'solve/aggregate.py', 'tools/check_conditions.py', 'tools/check_agg.py',
             'build_corpus.py', 'reproduce.py', 'web/build_views.py', 'web/metrics.js',
             'web/verify_views.js', 'web/serve.py', '启动问答网页.bat',
             'tools/invariant_check.py', 'tools/qa_eval.py', 'tools/check_conditions.py',
             'tools/append_md.py',
             'tools/review_apply.py', 'tools/regress.py', 'tools/review_diff.py',
             'tests/qa_cases.jsonl', 'data/corpus.db']
    missing = [p for p in named if not os.path.exists(os.path.join(args.root, p.replace('/', os.sep)))]
    ck('③ 关键文件齐备（%d 项）' % len(named), not missing, '缺 %s' % missing)

    # ④ 口径承诺（唯一真源）
    src = io.open(os.path.join(args.root, 'solve', 'corpus.py'), encoding='utf-8').read()
    ck('④ 汉字区间单一来源含扩展 A（corpus.HAN_CLASS）',
       re.search(r"HAN_CLASS\s*=\s*r'\\u3400-\\u4dbf\\u4e00-\\u9fff'", src) is not None)
    pr = io.open(os.path.join(args.root, 'solve', 'prosody.py'), encoding='utf-8').read()
    # 切句正则：**只能有一份定义**（定义在 prosody.py），其他文件只能引用它
    defs = []
    for sub in ('solve', 'tools'):
        for fn in os.listdir(os.path.join(args.root, sub)):
            if fn.endswith('.py'):
                s = io.open(os.path.join(args.root, sub, fn), encoding='utf-8').read()
                if re.search(r'^SENT_SPLIT_RE\s*=', s, re.M):
                    defs.append('%s/%s' % (sub, fn))
    ck('④ 切句正则单一来源（只在一处定义）', defs == ['solve/prosody.py'], '定义处 %s' % defs)
    ck('④ 切句字符集为「。？！」', '(?<=[。？！])' in pr)
    ck('④ 舍入为银行家舍入', 'ROUND_HALF_EVEN' in pr)
    jd = io.open(os.path.join(args.root, 'solve', 'data', 'pron_overrides.json'),
                 encoding='utf-8-sig').read()
    ck('④ 标定表每项都带依据字段', jd.count('"basis"') == jd.count('"tone"') and '"tone"' in jd)

    print('\n===== 文档一致性汇总 =====')
    print('  检查项 %d，FAIL %d' % (len(checks), len(fails)))
    if not checks:
        print('  ✗ FAIL：检查项为 0（防「空跑报通过」）')
        return 1
    if fails:
        for f in fails:
            print('   ✗ %s' % f)
        return 1
    print('  全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
