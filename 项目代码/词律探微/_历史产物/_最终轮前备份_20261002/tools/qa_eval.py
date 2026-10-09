# -*- coding: utf-8 -*-
"""问答评测（可复跑的用例集）：`tests/qa_cases.jsonl` + 一条命令出指标。

为什么要有它：作品里说「问答准确率 100%」这种话，评委只能选择相信或怀疑；
有了固定用例集 + 一条命令，**任何人当场就能验伪**（这也是我给外部交付提的要求）。

判定项（每条用例逐项判定）：
    ① 是否拒答与预期一致；
    ② 有据时，被引证据块里是否含期望 pid（若用例给了）；
    ③ 四道护栏是否通过；
    ④ 边界声明类型是否与问句类型匹配（护栏④已覆盖，此处单独计数）。

用法：python tools/qa_eval.py [--cases tests/qa_cases.jsonl] [--db data/corpus.db]
退出码：0 = 全过；1 = 有 FAIL（用例集为空也判 FAIL，防「空跑报通过」）。
"""
import argparse
import io
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import ask as A                                              # noqa: E402


def load_cases(path):
    return [json.loads(ln) for ln in io.open(path, encoding='utf-8') if ln.strip()]


def main():
    ap = argparse.ArgumentParser(description='问答评测（固定用例集 + 一条命令出指标）')
    ap.add_argument('--cases', default=os.path.join(ROOT, 'tests', 'qa_cases.jsonl'))
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--topk', type=int, default=3)
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    cases = load_cases(args.cases)
    if not cases:
        print('✗ FAIL：用例集为空（0 条 = 没测，不许报通过）')
        return 1
    conn = sqlite3.connect(args.db)
    n_ok = 0
    fails = []
    m = {'拒答正确': [0, 0], '证据含期望篇': [0, 0], '护栏通过': [0, 0], '边界类型匹配': [0, 0]}
    for c in cases:
        res = A.answer(conn, c['question'], topk=args.topk, kind=c.get('kind'))
        pids = [b['pid'] for b in res['blocks']]
        ok_re = (res['refused'] == bool(c['refuse']))
        m['拒答正确'][1] += 1
        m['拒答正确'][0] += 1 if ok_re else 0
        ok_pid = True
        if c.get('expect_pid') and not res['refused']:
            m['证据含期望篇'][1] += 1
            ok_pid = c['expect_pid'] in pids
            m['证据含期望篇'][0] += 1 if ok_pid else 0
        ok_g = bool(res['verify'][0])
        m['护栏通过'][1] += 1
        m['护栏通过'][0] += 1 if ok_g else 0
        ok_k = (res['refused'] or res['kind'] == c.get('kind', res['kind']))
        m['边界类型匹配'][1] += 1
        m['边界类型匹配'][0] += 1 if ok_k else 0
        good = ok_re and ok_pid and ok_g and ok_k
        n_ok += 1 if good else 0
        if not good or not args.quiet:
            print('%s %s  kind=%s 拒答=%s(期望 %s) 护栏=%s%s'
                  % ('PASS' if good else 'FAIL', c['id'], res['kind'], res['refused'],
                     c['refuse'], '通过' if ok_g else '未通过：%s' % res['problems'][:2],
                     '' if ok_pid else '  证据缺 %s' % c['expect_pid']))
            if not good and args.quiet:
                print('   查问句：%s' % c['question'])
        if not good:
            fails.append(c['id'])
    conn.close()
    print('\n===== 问答评测汇总 =====')
    for k, (a, b) in m.items():
        print('  %s：%d/%d' % (k, a, b))
    print('  用例通过：%d/%d' % (n_ok, len(cases)))
    tot = sum(v[1] for v in m.values())
    if tot == 0:
        print('  ✗ FAIL：检查项为 0（防「空跑报通过」）')
        return 1
    if fails:
        print('  失败用例：%s' % fails)
        return 1
    print('  全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
