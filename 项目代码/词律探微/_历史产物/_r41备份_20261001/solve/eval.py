# -*- coding: utf-8 -*-
"""eval.py —— 评测台：把官方自然语言标准答案反解成数字，与我的答案逐字段比对。

用法：
  python eval.py --pred answers.jsonl --gold 公开测试集_700题.jsonl --report 测试结果.csv
"""
from __future__ import annotations
import argparse
import csv
import json
import re

FORMS = {
    'C1': [
        re.compile(r'([甲乙])共(\d+)句，最长为第([\d、]+)句、各(\d+)字，全文平(\d+)、仄(\d+)，仄声比例([\d.]+)%'),
        # 并列时官方写「两篇较高」（公开集 13 道）；旧正则只收 [甲乙]，会把并列题
        # 静默跳过 → 评测台放水（第七轮教训：评测台也会骗人）。
        re.compile(r'相差([\d.]+)个百分点，([甲乙]|两篇)较高'),
    ],
    'C2': [
        re.compile(r'([甲乙])仄声比例由([\d.]+)%变为([\d.]+)%，变化([+\-\u2212][\d.]+)个百分点，绝对变幅([\d.]+)个百分点'),
        re.compile(r'变幅相差([\d.]+)个百分点，([甲乙]|两篇)较大'),
    ],
    'C3': [
        re.compile(r'([甲乙])阈值(\d+)字，入选第([\d、]+)句，合计平(\d+)、仄(\d+)，仄声比例([\d.]+)%'),
        re.compile(r'密度相差([\d.]+)个百分点，([甲乙]|两篇)较高'),
    ],
    'C4': [
        re.compile(r'([甲乙丙])后段可引[\u201c\u300c]([^\u201d\u300d]+)[\u201d\u300d]，仄声比例([\d.]+)%'),
        re.compile(r'排序为([甲乙丙＞>]+)'),
        re.compile(r'最高与最低相差([\d.]+)个百分点'),
    ],
    'C5': [
        re.compile(r'([甲乙])前段景物线索：([^；]+)；后段主观感受线索：([^；]+)；仄声比例变化([+\-\u2212][\d.]+)个百分点，节奏转向为(后段上升|后段下降|前后持平)'),
        # 官方 C5 答案末尾的「解释边界：…」——**必须解析**，否则我方按契约输出的
        # 「边界声明」会被下面的「多出的字段」判定误伤（实测：140 道 C5 全判不符）。
        # 它是解释性文字（与参考答案措辞不必逐字相同），故解析成下划线字段 `_boundary`，
        # 不参与严格比对，改由 compare() 里的「存在性 + 认账词」检查负责。
        re.compile(r'解释边界：(.+)'),
    ],
}


def seq(s):
    return [int(x) for x in re.findall(r'\d+', s or '')]


def parse_gold(cls, text):
    """反解官方答案 → 结构化字典。"""
    g = {}
    try:
        if cls == 'C1':
            for m in FORMS['C1'][0].finditer(text):
                g[m.group(1)] = {'句数': int(m.group(2)), '最长句序': seq(m.group(3)),
                                 '最长句字数': int(m.group(4)), '平': int(m.group(5)),
                                 '仄': int(m.group(6)), '仄声比例': float(m.group(7))}
            m = FORMS['C1'][1].search(text)
            if m:
                g['比例差'] = float(m.group(1)); g['较高'] = m.group(2)
        elif cls == 'C2':
            for m in FORMS['C2'][0].finditer(text):
                va = float(m.group(4).replace('\u2212', '-').replace('+', ''))
                g[m.group(1)] = {'前段比例': float(m.group(2)), '后段比例': float(m.group(3)),
                                 '变化': va, '绝对变幅': float(m.group(5))}
            m = FORMS['C2'][1].search(text)
            if m:
                g['变幅差'] = float(m.group(1)); g['较大'] = m.group(2)
        elif cls == 'C3':
            for m in FORMS['C3'][0].finditer(text):
                g[m.group(1)] = {'阈值': int(m.group(2)), '入选句序': seq(m.group(3)),
                                 '平': int(m.group(4)), '仄': int(m.group(5)), '比例': float(m.group(6))}
            m = FORMS['C3'][1].search(text)
            if m:
                g['密度差'] = float(m.group(1)); g['较高'] = m.group(2)
        elif cls == 'C4':
            for m in FORMS['C4'][0].finditer(text):
                g[m.group(1)] = {'后段引文': m.group(2).rstrip('。') + '。', '后段比例': float(m.group(3))}
            m = FORMS['C4'][1].search(text)
            if m:
                g['排序'] = [c for c in m.group(1) if c in '甲乙丙']
            m = FORMS['C4'][2].search(text)
            if m:
                g['比例差'] = float(m.group(1))
        elif cls == 'C5':
            for m in FORMS['C5'][0].finditer(text):
                v = float(m.group(4).replace('\u2212', '-').replace('+', ''))
                g.setdefault(m.group(1), {}).update({
                    '前段引文': m.group(2).strip(), '后段引文': m.group(3).strip(),
                    '变化': v, '转向': m.group(5)})
            m = FORMS['C5'][1].search(text)
            if m:                       # 解释性文字：只留证（下划线字段不参与严格比对）
                g['_boundary'] = m.group(1).strip()
    except Exception as e:  # 解析失败不致命，记下来
        g['_parse_error'] = repr(e)
    return g


def cmp_field(a, b, tol=1e-6):
    """比较单个字段值（数字容差 1e-6，列表顺序敏感，字符串精确）。"""
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < tol
    return a == b


def compare(cls, mine, gold):
    """返回 (ok, 差异列表)。

    说明：C4/C5 的「引文」字段不参与严格比对——官方代理评分只核验引文能否
    定位到指定分段，不要求与参考答案选同一句（任何后段句均可用）。
    排序：允许并列（只要求我的排序按我算出的比例非递增）。
    """
    diffs = []
    if '_parse_error' in gold:
        return None, ['gold 解析失败：%s' % gold['_parse_error']]
    # 契约内的解释性字段：官方答案写作「解释边界：…」，我方按契约输出「边界声明」。
    # 二者措辞不必逐字相同（与 C4/C5 引文同理），因此**不算多出的字段**，
    # 改由下方 cls=='C5' 的「存在性 + 认账词」检查负责。
    allowed_extra = {'边界声明'} if cls == 'C5' else set()
    # 审查 C10：旧版只遍历 gold 的键 —— 我方**多写**的顶层键不会被发现
    for k in mine:
        if k in gold or k.startswith('_') or k.endswith('前段') or k == '未用' \
                or k in allowed_extra:
            continue
        diffs.append('多出的字段：%s' % k)
    if cls == 'C5':                     # 边界声明必须存在且真的「认账」
        _bd = (mine or {}).get('边界声明')
        if not isinstance(_bd, str) or not _bd.strip():
            diffs.append('边界声明: 缺失（C5 契约要求给出解释边界）')
        elif not any(w in _bd for w in ('不能', '无法', '不可', '不宜', '不等于')):
            diffs.append('边界声明: 未认账（须写明不能推断什么）：%s' % _bd[:30])
    for k, gv in gold.items():
        if k.startswith('_') or k.endswith('引文'):
            continue
        mv = mine.get(k)
        if k == '排序':
            if not isinstance(mv, list) or not mv:
                diffs.append('排序: 缺失')
                continue
            # 第十轮收紧：官方 C4 无条件给出确定先后（实测 140 题里 0 道写「＝」并列；
            # 最多是「比例差 0.0 个百分点」但仍有 ＞ 方向）。旧版只比集合相等 + 自洽单调，
            # 于是“同一集合换个次序”（如甲乙互换）会被漏报 → 评测台放水。
            # 若将来官方真出现「＝」并列，在 gold 里以集合口径豁免。
            if '＝' in str(gv):
                if sorted(mv) != sorted(gv):
                    diffs.append('排序: 我=%s 标准=%s' % (mv, gv))
                    continue
                ratio = {x: mine.get(x, {}).get('后段比例') for x in mv}
                bad = [(mv[i], mv[j]) for i in range(len(mv)) for j in range(i + 1, len(mv))
                       if (ratio[mv[i]] or 0) + 1e-9 < (ratio[mv[j]] or 0)]
                if bad:
                    diffs.append('排序不单调: %s' % bad)
                continue
            if list(mv) != list(gv):
                diffs.append('排序: 我=%s 标准=%s' % (mv, gv))
                continue
            continue
        if isinstance(gv, dict):
            if not isinstance(mv, dict):
                diffs.append('%s: 缺失' % k); continue
            for kk, gvv in gv.items():
                if kk.endswith('引文'):
                    continue
                mvv = mv.get(kk)
                if not cmp_field(mvv, gvv):
                    diffs.append('%s.%s: 我=%s 标准=%s' % (k, kk, mvv, gvv))
            # 我给了、标准答案里没有的字段 → 也要报（否则「多写的字段」没人管；
            # 多半意味着标准答案解析漏了，或者我多输出了不属于契约的字段）
            for kk in mv:
                if kk not in gv and not kk.endswith('引文'):
                    diffs.append('%s.%s: 标准答案未提供（我=%s）' % (k, kk, mv[kk]))
        else:
            if not cmp_field(mv, gv):
                diffs.append('%s: 我=%s 标准=%s' % (k, mv, gv))
    return (len(diffs) == 0), diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pred', required=True)
    ap.add_argument('--gold', required=True)
    ap.add_argument('--report', default='测试结果.csv')
    ap.add_argument('--corpus', default=None,
                    help='可选：语料目录。给出则复核 C4/C5 引文是否落在题定分段内且可原样定位')
    args = ap.parse_args()

    gold = {}
    for l in open(args.gold, encoding='utf-8-sig'):
        if l.strip():
            q = json.loads(l)
            qid = q.get('题号')
            if not qid:
                print('  WARN  标准答案中有一条没有题号，已跳过')
                continue
            gold[qid] = q

    stat = {}
    # 引文可定位性复核用的语料索引（采纳自另一 AI 版本的 --corpus 设计）
    lookup = {}
    if args.corpus:
        from corpus import load_corpus
        for p in load_corpus(args.corpus):
            lookup[p.loc] = p
            lookup[p.pid] = p
    rows = []
    freq = {}
    for l in open(args.pred, encoding='utf-8-sig'):
        if not l.strip():
            continue
        r = json.loads(l)
        q = gold.get(r['题号'])
        cls = r.get('类别')
        st = stat.setdefault(cls, {'n': 0, 'exact': 0, 'diff': 0, 'miss': 0, 'noparse': 0, 'quote': 0})
        st['n'] += 1
        if q is None:
            # 题号不在标准答案里：标记出来，不要让整个评测台崩掉
            # （哪怕只是拿错题面文件，也应得到一份可读的明细，而不是 traceback）
            st['noparse'] += 1
            rows.append([r['题号'], cls, '标准答案缺失', '题号不在标准答案文件中', '', ''])
            continue
        if not r.get('答案'):
            st['miss'] += 1
            rows.append([r['题号'], cls, '未命中', '; '.join(r.get('errors', [])), '', ''])
            continue
        g = parse_gold(cls, q.get('标准答案', ''))
        ok, diffs = compare(cls, r['答案'], g)
        qnote = _check_quotes(cls, r, lookup) if (lookup and cls in ('C4', 'C5')) else None
        if qnote:
            st['quote'] += 1
        if ok is None:
            st['noparse'] += 1
            rows.append([r['题号'], cls, '标准答案解析失败', '; '.join(diffs), '', qnote or ''])
        elif ok:
            st['exact'] += 1
            rows.append([r['题号'], cls, '一致', '', '', qnote or ''])
        else:
            st['diff'] += 1
            for d in diffs:
                freq[d.split(':')[0]] = freq.get(d.split(':')[0], 0) + 1
            rows.append([r['题号'], cls, '不符', '; '.join(diffs), '', qnote or ''])

    total = sum(v['n'] for v in stat.values())
    tex = sum(v['exact'] for v in stat.values())
    with open(args.report, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['题号', '类别', '判定', '差异', '', ''])
        w.writerows(rows)

    print('%-6s %6s %6s %6s %6s %6s %6s %8s' % ('类别', '题数', '一致', '不符', '未命中', '解析失败', '引文异常', '一致率'))
    for cls in sorted(stat):
        v = stat[cls]
        rate = 100.0 * v['exact'] / v['n'] if v['n'] else 0
        print('%-6s %6d %6d %6d %6d %6d %6d %7.1f%%' % (cls, v['n'], v['exact'], v['diff'], v['miss'], v['noparse'], v['quote'], rate))
    print('%-6s %6d %6d %6d %6d %6d %6d %7.1f%%' % (
        '合计', total, tex,
        sum(v['diff'] for v in stat.values()),
        sum(v['miss'] for v in stat.values()),
        sum(v['noparse'] for v in stat.values()),
        sum(v['quote'] for v in stat.values()),
        100.0 * tex / total if total else 0))
    print('明细见：%s' % args.report)
    if freq:
        print('差异字段频次 TOP20（诊断用，仅统计数值/方向字段）：')
        for k, c in sorted(freq.items(), key=lambda x: -x[1])[:20]:
            print('  %-28s %d' % (k, c))


def _check_quotes(cls, r, lookup):
    """复核引文：须能在定位到的语料原文中找到，且是该篇题定分段内的整句。

    代理评分口径（题库说明）：引文只核可定位性与分段归属，不比对语义。
    返回差异说明串（通过则 None）。此设计采纳自另一 AI 版本的 --corpus 复核。
    """
    from prosody import Engine, han_only
    from pronounce import Pronouncer, default_overrides_path
    if _ENG[0] is None:
        _ENG[0] = Engine(Pronouncer(default_overrides_path()))
    eng = _ENG[0]
    loc = r.get('定位') or {}
    ans = r.get('答案') or {}
    notes = []
    for tag, pid in loc.items():
        p = lookup.get(pid)
        if p is None:
            notes.append('%s 定位 %s 无法回查' % (tag, pid))
            continue
        sents = eng.split(p.raw)
        cut = len(sents) // 2
        front, back = sents[:cut], sents[cut:]
        pairs = [('后段引文', back)] if cls == 'C4' else [('前段引文', front), ('后段引文', back)]
        for fname, seg in pairs:
            qt = (ans.get(tag) or {}).get(fname)
            if not qt:
                continue
            # ① 原样可定位（连标点一起，与语料原文逐字符一致）
            if qt not in p.raw and qt not in p.raw.replace('\n', ''):
                notes.append('%s.%s 不能原样定位：%s' % (tag, fname, qt[-16:]))
            # ② 分段归属：必须等于该分段【某一整句】（不放松成包含），
            #    否则一句跨段、或只截半句，也会被当成「在分段内」而漏报。
            qth = han_only(qt)
            if not any(qth == han_only(s) for s in seg):
                notes.append('%s.%s 不属题定分段/非整句：%s' % (tag, fname, qt[-14:]))
    return '；'.join(notes) if notes else None


_ENG = [None]


if __name__ == '__main__':
    main()
