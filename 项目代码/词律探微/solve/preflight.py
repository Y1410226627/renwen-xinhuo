# -*- coding: utf-8 -*-
"""preflight.py —— 交付前体检：一条命令把「环境 / 语料 / 标定表 / 题面 / 定位 / 答案 / 合规」全查一遍。

用法（公开集）：
  python preflight.py --questions <公开集700题.jsonl> --answers answers_700.jsonl
用法（保密集，仅终检时用）：
  python preflight.py --questions <保密300题_题面.jsonl> --answers answers_300secret.jsonl

退出码：0 = 全部通过；1 = 有 FAIL 项（便于接 CI / 答辩前自检）。
"""
from __future__ import annotations
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PASS, FAIL, WARN = [], [], []

# 答案契约（单一来源：交付格式校验与「标准答案可解析」体检共用此表）
# 每类 = (篇标签, 各篇子字段, 顶层字段)
REQ_FIELDS = {
    'C1': (('甲', '乙'), ('句数', '最长句序', '最长句字数', '平', '仄', '仄声比例'),
           ('比例差', '较高')),
    'C2': (('甲', '乙'), ('前段比例', '后段比例', '变化', '绝对变幅'), ('变幅差', '较大')),
    'C3': (('甲', '乙'), ('阈值', '入选句序', '平', '仄', '比例'), ('密度差', '较高')),
    'C4': (('甲', '乙'), ('后段引文', '后段比例'), ('排序', '比例差')),
    'C5': (('甲', '乙'), ('前段引文', '后段引文', '变化', '转向'), ('边界声明',)),
}

# 自由文本字段：官方逐题异文（引文 ≠ 参考答案、免责声明是散文），
# 不参与逐字比对，也不要求解析器能提取（提取不到不等于「免考」以外的含义）。
FREE_TEXT = {'前段引文', '后段引文', '边界声明'}


def ok(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  PASS  ' if cond else '  FAIL  ') + name + (('   << ' + str(detail)) if not cond and detail else ''))


def warn(name, detail=''):
    WARN.append(name)
    print('  WARN  ' + name + (('   << ' + detail) if detail else ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=(os.environ.get('LVC_CORPUS') or os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '数据', '语料'))))
    ap.add_argument('--questions', default=None, help='题面 jsonl（写答案的那份）')
    ap.add_argument('--answers', default=None, help='对应的答案 jsonl（本程序产出）')
    ap.add_argument('--gold', default=None, help='标准答案 jsonl（可选，用于复算一致率）')
    ap.add_argument('--overrides', default=os.path.join(HERE, 'data', 'pron_overrides.json'))
    args = ap.parse_args()

    print('=== 1. 依赖 ===')
    try:
        import pypinyin
        ok('pypinyin 可用（%s）' % pypinyin.__version__, True)
    except Exception as e:
        ok('pypinyin 可用', False, e)

    print('=== 2. 标定表 ===')
    from pronounce import Pronouncer
    ok('标定表存在', os.path.isfile(args.overrides), args.overrides)
    try:
        pr = Pronouncer(args.overrides)
        ok('标定表可加载且声调合法（%d 字）' % pr.n_overrides, pr.n_overrides > 0,
           '空表会让分数从约 88% 掉到约 47%')
        bad = []
        official = []
        raw = json.load(io.open(args.overrides, encoding='utf-8-sig'))
        for k, v in raw.items():
            if len(k) != 1:
                bad.append('%s 不是单字' % k)
            if isinstance(v, dict):
                t, py = v.get('tone'), v.get('pinyin') or ''
                if not isinstance(t, int) or t not in (1, 2, 3, 4):
                    bad.append('%s 声调 %r 非法' % (k, t))
                if v.get('basis') == '题库实测口径':
                    # 这类项【故意】不满足「拼音尾调 = 声调」：拼音记字典真音，声调记官方口径；
                    # 因此不许它沉默：必须写明理由与证据（题号/修复破坏数）。
                    if not (v.get('note') and v.get('evidence')):
                        bad.append('%s 属「题库实测口径」但缺 note/evidence' % k)
                    official.append('%s（字典音 %s，官方取 %d 声）' % (k, py or '?', t))
                elif py and (not py[-1].isdigit() or int(py[-1]) != t):
                    bad.append('%s 拼音 %s 与声调 %d 不符' % (k, py, t))
        ok('标定表每条自洽（单字键 / 声调 1-4 / 普通话异读项的拼音尾调一致）', not bad, bad)
        if official:
            print('  WARN  以下项按官方口径覆写（非普通话异读，已带证据）：%s' % '；'.join(official))
    except Exception as e:
        ok('标定表可加载', False, e)

    print('=== 3. 语料 ===')
    from corpus import load_corpus, load_qing, load_song, load_yuanqu, HAN_RE
    n_qing, n_song, n_yuan = len(load_qing(args.corpus)), len(load_song(args.corpus)), len(load_yuanqu(args.corpus))
    print('  清(poetry-source .base.json) %d ／ 宋(chinese-poetry) %d ／ 元曲 %d' % (n_qing, n_song, n_yuan))
    ok('三源均非空', min(n_qing, n_song, n_yuan) > 0)
    ok('清词数量合理（>20000，去重真实值 26742）', n_qing > 20000, n_qing)
    ok('宋词数量合理（>15000，真实值 21053）', n_song > 15000, n_song)
    poems = load_corpus(args.corpus)
    ok('语料总载入 > 30000 首', len(poems) > 30000, len(poems))
    ok('无空文本篇目', all(p.han for p in poems[:5000]))
    # ⚠ 2026-10-04 修（代码审查 P3-3）：`HAN_RE.search('')` 为 None，旧写法 `not None` 为真 →
    #   空字符串朝代会被判成「非中文朝代」。加 `p.dynasty` 非空判断后再查。
    _bad_dyn = sorted({p.dynasty for p in poems if p.dynasty and not HAN_RE.search(p.dynasty)})
    ok('朝代字段均为中文（元曲源曾是英文 yuan）', not _bad_dyn, _bad_dyn)
    ok('元曲朝代统一为「元」', all(p.dynasty == '元' for p in load_yuanqu(args.corpus)))
    # 「取音失败」是隐藏数据上最隐蔽的风险：pypinyin 读不出的字会被静默记为平。
    # 全库扫一遍并列出，确保它始终是一个【可枚举的小集合】（实测：4 种 / 5 字次）。
    from pypinyin import pinyin as _pinyin, Style as _Style

    def _read1(c):
        try:
            return _pinyin(c, style=_Style.TONE3, errors='default')[0][0]
        except Exception:
            return ''

    _chars = set()
    for _p in poems:
        _chars.update(HAN_RE.findall(_p.raw))
    _unk = sorted(c for c in _chars if pr.tone(c) == 0 and _read1(c) == c)
    print('  语料含 %d 个不同汉字；其中 pypinyin 完全读不出的：%d 种 %s'
          % (len(_chars), len(_unk), _unk))
    ok('「读不出」的字是可枚举的小集合（< 20 种；它们与官方同源，同样记平）', len(_unk) < 20, _unk)

    print('=== 4. 题面与定位 ===')
    from solver import CLS_MAP, solve_one
    from prosody import Engine
    if not args.questions:
        warn('未给 --questions，跳过题面/定位/答案检查')
    else:
        qs = [json.loads(l) for l in io.open(args.questions, encoding='utf-8-sig') if l.strip()]
        print('  题面 %d 道' % len(qs))
        cls_cnt = {}
        suf_bad = []
        for q in qs:
            cls = CLS_MAP.get(q.get('类别'), '')
            suf = (q.get('题号') or '')[-2:]
            cls_cnt[suf] = cls_cnt.get(suf, 0) + 1
            if cls and suf and cls != suf:
                suf_bad.append(q['题号'])
        print('  类别分布 %s' % dict(sorted(cls_cnt.items())))
        ok('题号后缀与类别映射一致', not suf_bad, suf_bad[:5])
        eng = Engine(pr)
        miss, noloc = [], []
        for q in qs:
            r = solve_one(q, poems, eng)
            if r['errors']:
                miss.append(r['题号'])
            if len(r['定位']) < 2:
                noloc.append(r['题号'])
        ok('全部题目定位到 ≥2 篇原文（未命中 0）', not noloc, noloc[:10])
        ok('全部题目无 error 字段', not miss, miss[:10])

        print('=== 5. 答案文件 ===')
        if args.answers and os.path.isfile(args.answers):
            rows = [json.loads(l) for l in io.open(args.answers, encoding='utf-8-sig') if l.strip()]
            ok('答案条数与题面一致', len(rows) == len(qs), '%d vs %d' % (len(rows), len(qs)))
            ids = [r.get('题号') for r in rows]
            ok('题号无重复', len(ids) == len(set(ids)))
            qid = {q['题号'] for q in qs}
            ok('题号集合与题面一致', set(ids) == qid, set(ids) ^ qid)
            bad_cls = [r['题号'] for r in rows if r.get('类别') != (r.get('题号') or '')[-2:]]
            ok('每条答案的类别与题号后缀一致', not bad_cls, bad_cls[:5])
            locmap = {p.loc: p for p in poems}
            unloc = []
            for r in rows:
                for tag, loc in (r.get('定位') or {}).items():
                    if loc not in locmap:
                        unloc.append('%s/%s' % (r['题号'], loc))
            ok('所有定位 id 都能回查到语料原文', not unloc, unloc[:5])
            ok('所有答案非空', all(r.get('答案') for r in rows))
            # 契约校验：字段齐全 + 数值范围（交付物格式说不清就会被判「不完整」）
            REQ = REQ_FIELDS
            bad_fields, bad_range = [], []
            for r in rows:
                a = r.get('答案') or {}
                tags, subkeys, topkeys = REQ[r['类别']]
                for t in tags:
                    if t not in a:
                        bad_fields.append('%s 缺 %s' % (r['题号'], t))
                        continue
                    for k in subkeys:
                        if k not in (a[t] or {}):
                            bad_fields.append('%s.%s 缺 %s' % (r['题号'], t, k))
                for k in topkeys:
                    if k not in a:
                        bad_fields.append('%s 缺 %s' % (r['题号'], k))
                for t, d in a.items():
                    if not isinstance(d, dict):
                        continue
                    for k, v in d.items():
                        if isinstance(v, (int, float)) and ('比例' in k or '变幅' in k or k == '变化'):
                            if not (-100.0 <= float(v) <= 100.0):
                                bad_range.append('%s.%s.%s=%s' % (r['题号'], t, k, v))
            ok('答案字段齐全（按题目契约逐个字段）', not bad_fields, bad_fields[:5])
            ok('比例/变幅类数值均在合理范围（-100～100）', not bad_range, bad_range[:5])
        else:
            warn('未给 --answers，跳过答案文件检查')

        print('=== 6. 复算一致率（可选） ===')
        if args.gold and args.answers and os.path.isfile(args.gold):
            import eval as ev
            gold = {}
            for _l in io.open(args.gold, encoding='utf-8-sig'):
                if _l.strip():
                    _q = json.loads(_l)
                    if _q.get('题号'):
                        gold[_q['题号']] = _q
            rows = [json.loads(l) for l in io.open(args.answers, encoding='utf-8-sig') if l.strip()]
            st = {}
            n_missing = 0
            missing = []
            for r in rows:
                gq = gold.get(r['题号'])
                if gq is None:
                    print('  WARN  答案里的 %s 不在标准答案文件中，跳过该题' % r['题号'])
                    continue
                g = ev.parse_gold(r['类别'], gq['标准答案'])
                # ★ 评测台自身体检：标准答案里的契约字段必须**全部解析出来**。
                #   解析不到 = 该字段从来没被比对过 → 满分是自我安慰（第七轮的真教训：
                #   官方并列写「两篇较高」，旧正则只收 [甲乙]，34 道题静默免考）。
                tags, subkeys, topkeys = REQ_FIELDS[r['类别']]
                # 只对**数值/方向类**字段要求「必须解析出来」：自由文本（引文、免责声明）
                # 不在此列，但也不允它掩盖真正的免考（如旧正则漏了「两篇较高」）。
                lacks = [k for k in topkeys if k not in g and k not in FREE_TEXT]
                for t in tags:
                    for k in subkeys:
                        if k in FREE_TEXT:
                            continue
                        if k not in (g.get(t) or {}):
                            lacks.append('%s.%s' % (t, k))
                if lacks:
                    n_missing += 1
                    if len(missing) < 5:
                        missing.append('%s 缺 %s' % (r['题号'], lacks))
                good, _ = ev.compare(r['类别'], r['答案'], g)
                k = r['类别']
                st.setdefault(k, [0, 0])
                st[k][0] += 1
                st[k][1] += 1 if good else 0
            tot = sum(v[0] for v in st.values())
            hit = sum(v[1] for v in st.values())
            for k in sorted(st):
                print('  %s  %d/%d = %.1f%%' % (k, st[k][1], st[k][0], 100.0 * st[k][1] / st[k][0]))
            print('  合计  %d/%d = %.1f%%' % (hit, tot, 100.0 * hit / tot))
            ok('标准答案契约字段全部可解析（否则该字段从未被比对）', n_missing == 0, missing)
        else:
            warn('未给 --gold，跳过一致率复算')

    print('=== 7. 合规（不得默认读取保密答案 / 不得含境外模型调用） ===')
    # 注意：不扫 preflight.py 自己（它的检查清单里必然出现这些关键词，自指会误报）
    scan = []
    for d in (HERE, os.path.join(ROOT, 'tools')):
        for x in sorted(os.listdir(d)):
            if x.endswith('.py') and x != 'preflight.py':
                scan.append(os.path.join(d, x))
    leak = []
    for p in scan:
        for i, line in enumerate(io.open(p, encoding='utf-8-sig'), 1):
            s = line.strip()
            if s.startswith('#'):
                continue
            if '保密' in line and ('open(' in line or 'path' in line.lower() or 'jsonl' in line):
                leak.append('%s:%d %s' % (os.path.basename(p), i, s[:60]))
    ok('代码中无「默认读取保密集」的路径', not leak, leak)
    foreign = []
    for p in scan:
        txt = io.open(p, encoding='utf-8-sig').read()
        for kw in ('openai', 'anthropic', 'claude', 'gpt-4', 'gemini'):
            if re.search(kw, txt, re.I):
                foreign.append('%s 提到 %s' % (os.path.basename(p), kw))
    ok('代码中无境外模型调用', not foreign, foreign)

    print('\n================ 体检汇总 ================')
    print('通过 %d ／ 失败 %d ／ 警告 %d' % (len(PASS), len(FAIL), len(WARN)))
    if FAIL:
        print('失败项：')
        for f in FAIL:
            print('  - ' + f)
        return 1
    print('全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
