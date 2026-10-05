# -*- coding: utf-8 -*-
"""test_guards.py —— 护栏实测：确认「出错时会不会静默算错」。

每道护栏都要**真的触发一次**才算有效（本文件的存在理由：2026-09-29 自检发现
「标定表缺失」警告本身带裸 %，一触发就崩，而它从没被运行过）。

用法：
  python test_guards.py                      # 用默认路径
  python test_guards.py --corpus <语料根> --question <题面 jsonl>
退出码：0 = 全部通过。
"""
from __future__ import annotations
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FAIL = []


def case(name, cond, detail=''):
    print(('  PASS  ' if cond else '  FAIL  ') + name + ('' if cond else '   << ' + str(detail)))
    if not cond:
        FAIL.append(name)


def run(args):
    r = subprocess.run([PY, os.path.join(HERE, 'solver.py')] + args, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stderr or '') + (r.stdout or '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=(os.environ.get('CORPUS_ROOT') or os.environ.get('LVC_CORPUS')
                                        or os.path.abspath(os.path.join(
                                            os.path.dirname(os.path.abspath(__file__)),
                                            '..', '..', '..', '数据', '语料'))))
    ap.add_argument('--question', default=os.environ.get('QUESTION_FILE', ''))
    args = ap.parse_args()
    q = args.question
    if not q:
        print('需要 --question（题面 jsonl）；也可用环境变量 QUESTION_FILE')
        return 1
    tmp = tempfile.mkdtemp()
    print('=== 护栏实测（每道都要真的触发一次） ===')

    rc, out = run(['--question', q, '--corpus', os.path.join(tmp, '不存在'), '--output', os.path.join(tmp, 'a.jsonl')])
    case('语料为 0 首时快速失败（退出码 2 + 指明路径）', rc == 2 and '语料载入为 0' in out, 'rc=%s %s' % (rc, out[:100]))

    rc, out = run(['--question', q, '--corpus', args.corpus, '--overrides', os.path.join(tmp, '无.json'),
                   '--output', os.path.join(tmp, 'b.jsonl'), '--limit', '3'])
    case('标定表缺失：告警且不崩溃（不静默掉 40 个点）',
         rc == 0 and '标定表为空或不可读' in out, 'rc=%s %s' % (rc, out[-160:]))

    bad = os.path.join(tmp, 'bad.json')
    io.open(bad, 'w', encoding='utf-8').write(json.dumps({'佳': 'jia'}, ensure_ascii=False))
    rc, out = run(['--question', q, '--corpus', args.corpus, '--overrides', bad,
                   '--output', os.path.join(tmp, 'c.jsonl'), '--limit', '2'])
    case('标定表取音无声调：拒绝加载（报错而非静默）', rc != 0 and '无合法声调' in out, 'rc=%s' % rc)

    bom = os.path.join(tmp, 'bom.json')
    with io.open(bom, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + json.dumps({'长': {'tone': 2, 'pinyin': 'chang2'}},
                                             ensure_ascii=False).encode('utf-8'))
    rc, out = run(['--question', q, '--corpus', args.corpus, '--overrides', bom,
                   '--output', os.path.join(tmp, 'd.jsonl'), '--limit', '2'])
    case('标定表带 UTF-8 BOM（Windows 记事本常产）：仍可加载', rc == 0 and '标定表：1 字' in out, 'rc=%s' % rc)

    empty = os.path.join(tmp, 'empty.jsonl')
    io.open(empty, 'w', encoding='utf-8').write('')
    rc, out = run(['--question', empty, '--corpus', args.corpus, '--output', os.path.join(tmp, 'e.jsonl')])
    case('空题面：正常结束（0 题）', rc == 0 and '完成：0 题' in out, 'rc=%s' % rc)

    rc, out = run(['--question', q, '--corpus', args.corpus, '--output', os.path.join(tmp, 'f.jsonl'), '--limit', '3'])
    n = len([l for l in io.open(os.path.join(tmp, 'f.jsonl'), encoding='utf-8') if l.strip()])
    case('--limit 3 只算 3 题', rc == 0 and n == 3, 'n=%d' % n)

    # 评测台护栏：题号不在标准答案里必须「明细化」，不能一个 traceback 结束
    one = os.path.join(tmp, 'one.jsonl')
    run(['--question', q, '--corpus', args.corpus, '--output', one, '--limit', '1'])
    rec = json.loads(io.open(one, encoding='utf-8').readline())
    rec['题号'] = 'T-999-V2C1'          # 故意改成标准答案里没有的题号
    badpred = os.path.join(tmp, 'badpred.jsonl')
    io.open(badpred, 'w', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False) + '\n')
    csvp = os.path.join(tmp, 'bad.csv')
    er = subprocess.run([PY, os.path.join(HERE, 'eval.py'), '--pred', badpred, '--gold', q,
                         '--report', csvp], capture_output=True, text=True,
                        encoding='utf-8', errors='replace')
    csvtxt = io.open(csvp, encoding='utf-8-sig').read() if os.path.isfile(csvp) else ''
    case('评测台：题号不在标准答案里 → 明细化而非 traceback',
         er.returncode == 0 and '标准答案缺失' in csvtxt,
         'rc=%s stderr=%s' % (er.returncode, (er.stderr or '')[-160:]))

    print('\n失败 %d 项' % len(FAIL))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
