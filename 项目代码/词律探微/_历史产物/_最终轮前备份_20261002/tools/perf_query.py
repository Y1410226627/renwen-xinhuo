# -*- coding: utf-8 -*-
"""perf_query.py —— 单问句**引擎各阶段计时**（「先量后改」用的尺子）。

为什么有它：优化响应速度时，必须先把时间花在哪一段看清楚（解析／范围／五路检索／计数／
取证据／逐篇复核），否则优化会做偏。2026-10-01 深夜靠它定位到两件事：
  ① 同一条件被查三遍（scope_pids／route_numeric／count_hits，各 ~280 ms）；
  ② 执行计划错选索引（`idx_poems_dyn_ze` 287 ms，正确索引 `idx_poems_dyn_cipai` 只要 2 ms）。
两项修完后，同一问句的引擎耗时从 ~900 ms 降到 ~70 ms（见优化报告）。

注意口径：墙钟受**同机负载**影响（实测同版本 7~46 秒的抖动）；结论要把
`tools/audit_work.py` 的「工作量」（SQL 条数／取回行数，逐次一致）与执行计划一起看。

用法：
    python tools/perf_query.py "清 临江仙 仄声比例高于45%"
    python tools/perf_query.py --repeat 3 "句脚是「愁」的清词有哪些"
"""
import argparse
import os
import sqlite3
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import evidence as EV      # noqa: E402
import retrieve as RT      # noqa: E402


def run_once(conn, q):
    """跑一遍「解析 → 范围 → 五路 → 计数 → 证据 → 逐篇复核」，返回 [(阶段, ms, 备注)]。"""
    rows = []

    def t(label, fn):
        t0 = time.perf_counter()
        r = fn()
        rows.append((label, (time.perf_counter() - t0) * 1000,
                     str(len(r)) if hasattr(r, '__len__') else ''))
        return r

    spec = t('解析 parse_query', lambda: RT.parse_query(conn, q))
    where, args = RT._sql(spec)
    t('范围 scope_pids', lambda: RT.scope_pids(conn, where, args))
    t('二字组 route_bigram', lambda: RT.route_bigram(conn, spec.raw))
    t('短语 route_phrase', lambda: RT.route_phrase(conn, spec.keywords) if spec.keywords else [])
    t('数值 route_numeric', lambda: RT.route_numeric(conn, where, args) if spec.rng else [])
    t('声律 route_pz', lambda: RT.route_pz(conn, spec.pz) if spec.pz else {})
    got = t('融合 search(top3)', lambda: RT.search(conn, spec, topk=3))
    t('计数 count_hits', lambda: RT.count_hits(conn, spec))
    t('证据 build_blocks', lambda: EV.build_blocks(conn, got, with_lines=1, spec=spec))
    for b in got:
        t('复核 ' + b['pid'][:22], lambda b=b: RT.verify_spec_on_poem(conn, b['pid'], spec))
    return spec, rows


def main():
    ap = argparse.ArgumentParser(description='单问句引擎各阶段计时')
    ap.add_argument('question')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--repeat', type=int, default=1, help='重复次数（多次取每阶段中位）')
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    print('问句：%s' % args.question)
    acc = {}
    for i in range(max(1, args.repeat)):
        spec, rows = run_once(conn, args.question)
        for label, ms, note in rows:
            acc.setdefault(label, ([], note))[0].append(ms)
    print('  解析结果：%s' % spec.describe())
    total = 0.0
    for label, (times, note) in acc.items():
        med = statistics.median(times)
        total += med
        print('  %-22s %8.1f ms   %s' % (label, med, note))
    print('  %-22s %8.1f ms（中位合计；墙钟受同机负载影响，请配合 audit_work 使用）'
          % ('合计', total))


if __name__ == '__main__':
    main()