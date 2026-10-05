# -*- coding: utf-8 -*-
"""calibrate.py —— 用公开集标定「逐字取音表」。

方法：坐标下降。候选值 = 该字的全部异读（pypinyin heteronym），
      目标函数 = 公开集 C1–C4 题的「匹配字段总数」（同分时取「完全一致题数」）。
纪律：只用公开集 700 题；保密集不参与。

用法：python tools/calibrate.py --corpus <语料根> --questions <公开集jsonl> --out <overrides.json>
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'solve'))

from pypinyin import pinyin, Style                     # noqa: E402
from corpus import load_corpus, get_locator            # noqa: E402
from prosody import r1, pct, han_only, SENT_SPLIT_RE    # noqa: E402
import eval as ev                                      # noqa: E402

TONE_RE = re.compile(r'([1-5])\s*$')


def base_tone(ch):
    try:
        py = pinyin(ch, style=Style.TONE3, errors='default')[0][0]
    except Exception:
        py = ''
    m = TONE_RE.search(py or '')
    t = int(m.group(1)) if m else 0
    return 0 if t == 5 else t


def heteronyms(ch):
    try:
        rs = pinyin(ch, style=Style.TONE3, heteronym=True)[0]
    except Exception:
        rs = []
    out = []
    for py in rs:
        m = TONE_RE.search(py)
        if m:
            t = int(m.group(1))
            if t == 5:
                t = 0
            if t not in out:
                out.append(t)
    return out


def sents_of(text):
    """与 prosody.Engine.split **完全同一口径**（共用 SENT_SPLIT_RE，切勿另写一份）。"""
    raw = text.replace('\n', '')
    return [s.strip() for s in SENT_SPLIT_RE.split(raw) if han_only(s)]


class Problem:
    """把一道题固化成：需要参与统计的「字序列片段」。"""

    def __init__(self, tag, cls, poems, gold):
        self.tag = tag
        self.cls = cls
        self.poems = poems            # {甲乙(丙): [chars per sentence]}
        self.gold = gold
        self.chars = set()
        for v in poems.values():
            for s in v:
                self.chars.update(s)


def to_sent_chars(poem):
    return [list(han_only(s)) for s in sents_of(poem.raw)]


def pz(chars, tones, ov):
    out = []
    for c in chars:
        t = ov.get(c)
        if t is None:
            t = tones.get(c, 0)
        out.append('仄' if t in (3, 4) else '平')
    return ''.join(out)


def stats_ratio(allpz):
    ping = allpz.count('平'); ze = allpz.count('仄')
    return ping, ze, pct(ze, len(allpz))


def halves(pzs):
    n = len(pzs); cut = n // 2
    a = ''.join(pzs[:cut]); b = ''.join(pzs[cut:])
    raw_a = (100.0 * a.count('仄') / len(a)) if a else 0.0
    raw_b = (100.0 * b.count('仄') / len(b)) if b else 0.0
    return r1(raw_a), r1(raw_b), r1(raw_b - raw_a)


def evaluate(p, tones, ov):
    """返回 (匹配字段数, 总字段数) 与 明细。"""
    matched = 0; total = 0; mine = {}
    pzs = {k: [pz(s, tones, ov) for s in v] for k, v in p.poems.items()}
    if p.cls == 'C1':
        for k in ('甲', '乙'):
            if k not in pzs:
                continue
            allpz = ''.join(pzs[k]); ping, ze, rt = stats_ratio(allpz)
            lens = [len(s) for s in p.poems[k]]
            mx = max(lens)
            mine[k] = {'句数': len(lens), '最长句序': [i + 1 for i, L in enumerate(lens) if L == mx],
                       '最长句字数': mx, '平': ping, '仄': ze, '仄声比例': rt}
        if '甲' in mine and '乙' in mine:
            d = r1(abs(mine['甲']['仄声比例'] - mine['乙']['仄声比例']))
            mine['比例差'] = d
            mine['较高'] = ('甲' if mine['甲']['仄声比例'] > mine['乙']['仄声比例']
                            else ('乙' if mine['乙']['仄声比例'] > mine['甲']['仄声比例'] else '持平'))
    elif p.cls in ('C2', 'C5'):
        for k in ('甲', '乙'):
            if k not in pzs:
                continue
            ra, rb, chg = halves(pzs[k])
            mine[k] = {'前段比例': ra, '后段比例': rb, '变化': chg, '绝对变幅': r1(abs(chg)),
                       '转向': '后段上升' if chg > 0 else ('后段下降' if chg < 0 else '前后持平')}
        if p.cls == 'C2' and '甲' in mine and '乙' in mine:
            mine['变幅差'] = r1(abs(mine['甲']['绝对变幅'] - mine['乙']['绝对变幅']))
            mine['较大'] = '甲' if mine['甲']['绝对变幅'] > mine['乙']['绝对变幅'] else '乙'
    elif p.cls == 'C3':
        for k in ('甲', '乙'):
            if k not in pzs:
                continue
            sent_chars = p.poems[k]
            total_ch = sum(len(s) for s in sent_chars)
            thr = math.ceil(total_ch / len(sent_chars))
            idx = [i for i, s in enumerate(sent_chars) if len(s) >= thr]
            seg = ''.join(pzs[k][i] for i in idx)
            mine[k] = {'阈值': thr, '入选句序': [i + 1 for i in idx],
                       '平': seg.count('平'), '仄': seg.count('仄'), '比例': pct(seg.count('仄'), len(seg))}
        if '甲' in mine and '乙' in mine:
            mine['密度差'] = r1(abs(mine['甲']['比例'] - mine['乙']['比例']))
            mine['较高'] = '甲' if mine['甲']['比例'] > mine['乙']['比例'] else '乙'
    elif p.cls == 'C4':
        for k in pzs:
            ra, rb, chg = halves(pzs[k])
            mine[k] = {'后段比例': rb}
        vals = {k: v['后段比例'] for k, v in mine.items()}
        # 与 prosody.c4 同口径：同分时按题目标签固定优先序（丙 > 乙 > 甲）
        pri = {'丙': 0, '乙': 1, '甲': 2}
        mine['排序'] = sorted(vals, key=lambda k: (-vals[k], pri.get(k, 99)))
        mine['比例差'] = r1(max(vals.values()) - min(vals.values()))

    for k, gv in p.gold.items():
        if k.startswith('_'):
            continue
        mv = mine.get(k)
        if isinstance(gv, dict):
            for kk, gvv in gv.items():
                if kk.endswith('引文'):
                    continue
                total += 1
                if isinstance(mv, dict) and mv.get(kk) == gvv:
                    matched += 1
        elif k == '排序':
            total += 1
            if mv == gv:
                matched += 1
        else:
            total += 1
            if mv == gv:
                matched += 1
    return matched, total, mine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=(os.environ.get('LVC_CORPUS') or os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '数据', '语料'))))
    ap.add_argument('--questions', default=None)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(HERE), 'solve', 'data', 'candidate_overrides.json'),
                    help='候选表输出路径。★ 默认不碰交付表 pron_overrides.json：'
                         '原始标定结果含噪声项，必须人工逐字复核（含取音是否标准、留一法承重）'
                         '后才能手动提升为交付表。')
    ap.add_argument('--passes', type=int, default=4)
    ap.add_argument('--classes', default='C1,C2,C3,C4')
    args = ap.parse_args()

    qfile = args.questions or (os.environ.get('LVC_QUESTIONS') or os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '数据', '初赛数据',
        '薪火人文-清词-1000题库-V5版本', '公开测试集_700题.jsonl')))
    qs = [json.loads(l) for l in open(qfile, encoding='utf-8-sig') if l.strip()]
    poems = load_corpus(args.corpus)
    loc = get_locator(poems)
    want = set(args.classes.split(','))
    print('语料 %d 首，题目 %d 道，标定类别 %s' % (len(poems), len(qs), want))

    # 建立 Problem 列表
    probs = []
    for q in qs:
        cls = (q.get('题号') or '')[-2:]
        if cls not in want:
            continue
        parts = {}
        for line in (q.get('问题') or '').replace('\\n', '\n').split('\n'):
            m = re.match(r'^\s*([甲乙丙])[：:]\s*(.+)$', line.strip())
            if not m:
                continue
            body = m.group(2)
            ma = re.match(r'^([^·\u00b7]+)[·\u00b7]([^《]+)', body)
            titles = re.findall(r'《([^》]+)》', body)
            mc = re.search(r'词牌[\u201c"]([^\u201d"]+)[\u201d"]', body)
            mh = re.search(r'首句[\u201c"]([^\u201d"]+)[\u201d"]', body)
            parts[m.group(1)] = (ma.group(2).strip() if ma else '',
                                 mc.group(1) if mc else (titles[-1] if titles else ''),
                                 mh.group(1) if mh else '')
        pz_map = {}
        for tag, (au, cp, hd) in parts.items():
            pm = loc.find_one(au, cp, hd)
            if pm is None:
                break
            pz_map[tag] = to_sent_chars(pm)
        if len(pz_map) < 2:
            continue
        gold = ev.parse_gold(cls, q.get('标准答案', ''))
        if '_parse_error' in gold or not gold:
            continue
        probs.append(Problem(q['题号'], cls, pz_map, gold))
    print('可标定题目 %d 道' % len(probs))

    # 初始化
    chars = set()
    for p in probs:
        chars |= p.chars
    tones = {}
    for c in chars:
        tones[c] = base_tone(c)
    ov = {}

    # 字符 -> 题目
    c2p = {}
    for i, p in enumerate(probs):
        for c in p.chars:
            c2p.setdefault(c, []).append(i)

    def score():
        f = 0; ex = 0
        for p in probs:
            m, t, mine = evaluate(p, tones, ov)
            f += m
            if m == t:
                ex += 1
        return f, ex

    f0, ex0 = score()
    print('初始：匹配字段 %d / 完全一致题 %d' % (f0, ex0))
    best = (f0, ex0)
    # 只对存在异读的字做坐标下降
    multi = [c for c in sorted(chars) if len(heteronyms(c)) > 1]
    print('存在异读的字 %d 个' % len(multi))
    for rnd in range(args.passes):
        changed = 0
        for c in multi:
            cur = ov.get(c, tones[c])
            cands = heteronyms(c)
            base_f = 0
            # 当前得分（只算相关题）
            rel = c2p.get(c, [])
            for i in rel:
                m, t, _ = evaluate(probs[i], tones, ov)
                base_f += m
            bestc = cur; bestf = base_f
            for cand in cands:
                if cand == cur:
                    continue
                ov[c] = cand
                f = 0
                for i in rel:
                    m, t, _ = evaluate(probs[i], tones, ov)
                    f += m
                if f > bestf:
                    bestf = f; bestc = cand
            # 关键：无论如何都写回 bestc（之前写成「未改进则删除」会把已生效的覆写抹掉）
            if bestc == tones[c]:
                ov.pop(c, None)
            else:
                ov[c] = bestc
            if bestc != cur:
                changed += 1
        f, ex = score()
        print('第 %d 轮：匹配字段 %d / 完全一致题 %d（本轮改动 %d 字）' % (rnd + 1, f, ex, changed))
        best = max(best, (f, ex))
        if changed == 0:
            break

    # 输出（写回前先备份旧表）
    out = {}
    for c, t in sorted(ov.items()):
        if t != tones[c]:
            out[c] = _entry(c, t, tones[c], '坐标下降标定（公开集）')
    if os.path.isfile(args.out):
        bak = args.out + '.bak'
        with open(args.out, encoding='utf-8-sig') as src, open(bak, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        print('已备份旧表 -> %s' % bak)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print('改写 %d 字 -> %s' % (len(out), args.out))
    print('最终：匹配字段 %d / 完全一致题 %d（初始 %d/%d）' % (best[0], best[1], f0, ex0))


def _entry(ch, tone, default, note):
    """写标定条目：pinyin 必须是【真实拼音字符串】（TONE3），不能是 x3 这类占位。"""
    py = ''
    try:
        for r in pinyin(ch, style=Style.TONE3, heteronym=True)[0]:
            if r and r[-1] == str(tone):
                py = r
                break
    except Exception:
        py = ''
    return {'tone': tone, 'pinyin': py or ('x%d' % tone), 'default': default, 'note': note}


if __name__ == '__main__':
    main()
