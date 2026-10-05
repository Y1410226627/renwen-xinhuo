# -*- coding: utf-8 -*-
"""refine.py —— 在已有标定表基础上做模拟退火（固定种子，可复现）。

目标：公开集 C1–C5 的「完全一致题数」（同分比匹配字段数）。
候选值：该字的异读（pypinyin heteronym）。纪律：只用公开集。
"""
from __future__ import annotations
import argparse
import json
import math
import os
import random
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'solve'))
sys.path.insert(0, HERE)

import calibrate as C   # 复用 Problem 构建与 evaluate     # noqa: E402


def build_problems(corpus, qfile, classes):
    """复用 solver.parse_question，避免两处各写一份题面解析（口径分家风险）。"""
    import eval as ev
    from corpus import load_corpus, get_locator
    import solver as S
    qs = [json.loads(l) for l in open(qfile, encoding='utf-8-sig') if l.strip()]
    poems = load_corpus(corpus)
    loc = get_locator(poems)
    probs = []
    for q in qs:
        cls = (q.get('题号') or '')[-2:]
        if cls not in classes:
            continue
        parts = S.parse_question(q.get('问题', ''))
        pz_map = {}
        for tag, spec in parts.items():
            pm = loc.find_one(spec['作者'], spec['词牌'], spec['首句'])
            if pm is None:
                break
            pz_map[tag] = C.to_sent_chars(pm)
        if len(pz_map) < 2:
            continue
        gold = ev.parse_gold(cls, q.get('标准答案', ''))
        if '_parse_error' in gold or not gold:
            continue
        probs.append(C.Problem(q['题号'], cls, pz_map, gold))
    return probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=r'D:\桌面\人文薪火\数据\语料')
    ap.add_argument('--questions', default=os.path.join(
        r'D:\桌面\人文薪火\数据\初赛数据', '薪火人文-清词-1000题库-V5版本', '公开测试集_700题.jsonl'))
    ap.add_argument('--overrides', default=os.path.join(os.path.dirname(HERE), 'solve', 'data', 'pron_overrides.json'))
    ap.add_argument('--classes', default='C1,C2,C3,C4,C5')
    ap.add_argument('--iters', type=int, default=20000)
    ap.add_argument('--seed', type=int, default=20260929)
    args = ap.parse_args()

    probs = build_problems(args.corpus, args.questions, set(args.classes.split(',')))
    print('题目 %d 道' % len(probs))

    # 初始表
    tones = {}
    chars = set()
    for p in probs:
        chars |= p.chars
    for c in chars:
        tones[c] = C.base_tone(c)
    ov = {}
    if os.path.isfile(args.overrides):
        raw = json.load(open(args.overrides, encoding='utf-8-sig'))
        for k, v in raw.items():
            t = v.get('tone') if isinstance(v, dict) else None
            if t:
                ov[k] = int(t)
    print('初始覆写 %d 字' % len(ov))

    def score_all():
        f = 0; ex = 0
        for p in probs:
            m, t, _ = C.evaluate(p, tones, ov)
            f += m
            if m == t:
                ex += 1
        return f, ex

    c2p = {}
    for i, p in enumerate(probs):
        for c in p.chars:
            c2p.setdefault(c, []).append(i)

    multi = [c for c in sorted(chars) if len(C.heteronyms(c)) > 1]
    rng = random.Random(args.seed)
    best_f, best_ex = score_all()
    f0, ex0 = best_f, best_ex
    best_ov = dict(ov)
    print('起点：字段 %d / 一致题 %d' % (best_f, best_ex))

    def local_score(c):
        f = 0; ex = 0
        for i in c2p.get(c, []):
            m, t, _ = C.evaluate(probs[i], tones, ov)
            f += m
            if m == t:
                ex += 1
        return f, ex

    cur_f, cur_ex = best_f, best_ex
    for it in range(args.iters):
        T = max(0.5, 12.0 * (1.0 - it / args.iters))
        c = rng.choice(multi)
        cands = C.heteronyms(c)
        new = rng.choice(cands + [C.base_tone(c)])
        old = ov.get(c, tones[c])
        if new == old:
            continue
        lf0, lex0 = local_score(c)
        if new == C.base_tone(c):
            ov.pop(c, None)
        else:
            ov[c] = new
        lf1, lex1 = local_score(c)
        accept = (lf1, lex1) > (lf0, lex0)      # 先按「字段数→一致题数」词典序
        if not accept:
            # 允许小倒退以跳出局部最优
            acc_metric = (lf1 - lf0) + (lex1 - lex0) * 0.0
            if rng.random() < math.exp(min(0.0, acc_metric / T)):
                accept = True
        if accept:
            cur_f += lf1 - lf0
            cur_ex += lex1 - lex0
            if (cur_f, cur_ex) > (best_f, best_ex):
                # 以全局评估确认（局部增量可能有偏差），确认后再更新最优
                gf, gex = score_all()
                cur_f, cur_ex = gf, gex
                if (gf, gex) >= (best_f, best_ex):
                    best_f, best_ex = gf, gex
                    best_ov = dict(ov)
        else:
            # 回退
            if old == C.base_tone(c):
                ov.pop(c, None)
            else:
                ov[c] = old

    print('退火结束：字段 %d / 一致题 %d（起点 %d/%d）' % (best_f, best_ex, f0, ex0))

    # 关键：无改进就不改写交付表（旧版无条件重写，会把标定表覆盖成退火后的同值/劣值）
    if (best_f, best_ex) <= (f0, ex0):
        print('无提升：保持原表不变 -> %s' % args.overrides)
        return

    out = {}
    for c, t in sorted(best_ov.items()):
        if t != tones[c]:
            out[c] = C._entry(c, t, tones[c], '模拟退火标定（公开集，seed=%d）' % args.seed)
    if os.path.isfile(args.overrides):
        bak = args.overrides.replace('.json', '_before_sa.json')
        shutil.copyfile(args.overrides, bak)
        print('已备份旧表 -> %s' % bak)
    os.makedirs(os.path.dirname(args.overrides), exist_ok=True)
    with open(args.overrides, 'w', encoding='utf-8') as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print('写出 %d 字 -> %s' % (len(out), args.overrides))


if __name__ == '__main__':
    main()
