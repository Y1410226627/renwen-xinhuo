# -*- coding: utf-8 -*-
"""regress.py —— 常设回归门禁：**改完任何一条规则，先跑这一条命令**。

目的（第六/七轮自检的产物）：防「改 A 修好了、B 被带坏了却没人发现」。
一条命令把「确定性 / 期望哈希 / 复算一致率 / 全库抽样泛化 / 引文原样性」全跑一遍。

用法：
  python tools/regress.py --questions <题面.jsonl> --gold <含标准答案的.jsonl> \
      --expect <期望答案文件的 SHA256> --tag 公开

检查项：
  1) 确定性：同一输入连跑两遍，输出文件**逐字节**一致（SHA256 相同）
  2) 期望哈希：本轮输出哈希 == --expect（不给则只报告，不给结论）
  3) 复算一致率：调 eval 对标准答案，逐类给出一致率（与评测台同口径）
  4) 全库抽样泛化：随机 N 首原文「自题自解」（拿自身作者/词牌/首句当题面），
     要求定位**回到原篇**、且引擎不抛异常
  5) 引文原样性：C4/C5 引文必须**原样**出现在语料原文中，且等于该分段某一整句

退出码：0 = 全过；1 = 有 FAIL（可接 CI）。
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import random
import subprocess
import sys
import tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))      # tools/
ROOT = os.path.dirname(HERE)                           # 项目根
SOLVE = os.path.join(ROOT, 'solve')                    # 引擎代码目录
sys.path.insert(0, SOLVE)
sys.path.insert(0, ROOT)

FAIL = []
COUNTS = [0]
PY = sys.executable


def case(name, cond, detail=''):
    print(('  PASS  ' if cond else '  FAIL  ') + name + ('' if cond else '   << ' + str(detail)))
    if not cond:
        FAIL.append(name)    # 通过数
    COUNTS[0] += 1


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest().upper()


def run_solver(questions, corpus, out):
    r = subprocess.run([PY, os.path.join(SOLVE, 'solver.py'), '--question', questions,
                        '--corpus', corpus, '--output', out],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--questions', required=True)
    ap.add_argument('--gold', default=None, help='含标准答案的题面 jsonl（复算用）')
    ap.add_argument('--corpus', default=r'D:\桌面\人文薪火\数据\语料')
    ap.add_argument('--expect', default=None, help='期望的答案文件 SHA256（大写小写均可）')
    ap.add_argument('--tag', default='未命名')
    ap.add_argument('--sample', type=int, default=300, help='全库随机抽样篇数（默认 300）')
    ap.add_argument('--seed', type=int, default=20260929)
    ap.add_argument('--update-manifest', action='store_true',
                    help='把本轮哈希写进 data/golden_sha.json（需先在 --tag 下确认无误）')
    args = ap.parse_args()

    from corpus import load_corpus, get_locator, han_only
    from prosody import Engine
    from pronounce import Pronouncer, default_overrides_path

    tmp = tempfile.mkdtemp(prefix='regress_')
    a1, a2 = os.path.join(tmp, 'a1.jsonl'), os.path.join(tmp, 'a2.jsonl')

    print('=== 1. 确定性（同一输入连跑两遍）===')
    for i, out in enumerate((a1, a2), 1):
        rc, log = run_solver(args.questions, args.corpus, out)
        case('第 %d 遍运行成功' % i, rc == 0 and os.path.isfile(out), log[-200:])
    if os.path.isfile(a1) and os.path.isfile(a2):
        h1, h2 = sha256(a1), sha256(a2)
        case('两遍输出逐字节一致', h1 == h2, '%s vs %s' % (h1[:16], h2[:16]))
        print('     SHA256 = %s' % h1)

    print('=== 2. 期望哈希 ===')
    if os.path.isfile(a1):
        cur = sha256(a1)
        if args.expect:
            case('[%s] 输出哈希与期望一致' % args.tag, cur.upper() == args.expect.upper(),
                 '我=%s 期望=%s' % (cur[:16], args.expect[:16]))
        else:
            print('     （未给 --expect，仅报告：%s）' % cur)

    print('=== 3. 复算一致率 ===')
    if args.gold and os.path.isfile(a1):
        import eval as ev
        gold = {}
        for l in io.open(args.gold, encoding='utf-8-sig'):
            if l.strip():
                q = json.loads(l)
                if q.get('题号'):
                    gold[q['题号']] = q
        stat = {}
        for l in io.open(a1, encoding='utf-8-sig'):
            if not l.strip():
                continue
            r = json.loads(l)
            cls = r['类别']
            st = stat.setdefault(cls, [0, 0])
            st[0] += 1
            gq = gold.get(r['题号'])
            if gq is None or not r.get('答案'):
                continue
            g = ev.parse_gold(cls, gq.get('标准答案', ''))
            good, _ = ev.compare(cls, r['答案'], g)
            st[1] += 1 if good else 0
        tot = sum(v[0] for v in stat.values())
        hit = sum(v[1] for v in stat.values())
        for k in sorted(stat):
            print('     %-3s %3d/%3d = %5.1f%%' % (k, stat[k][1], stat[k][0],
                                                   100.0 * stat[k][1] / stat[k][0]))
        print('     合计 %d/%d = %.1f%%' % (hit, tot, 100.0 * hit / tot if tot else 0))
        case('[%s] 标准答案缺失 0 题' % args.tag,
             all(json.loads(l)['题号'] in gold for l in io.open(a1, encoding='utf-8-sig') if l.strip()))
    else:
        print('     （未给 --gold，跳过）')

    print('=== 4. 全库抽样泛化（自题自解）===')
    poems = load_corpus(args.corpus)
    eng = Engine(Pronouncer(default_overrides_path()))
    if not poems:
        case('语料非空', False, '语料目录：%s' % args.corpus)
    else:
        case('语料非空（%d 首）' % len(poems), True)
        loc = get_locator(poems)
        random.seed(args.seed)
        smp = random.sample(poems, min(args.sample, len(poems)))
        nerr = neng = nback = 0
        for p in smp:
            try:
                eng.c1(p.raw, smp[0].raw)
            except Exception:
                neng += 1
            got = loc.find_one(p.author, p.cipai, han_only(p.raw)[:8], p.dynasty)
            if got is None:
                nerr += 1
            elif got.han != p.han:
                nback += 1
        case('引擎在抽样上无异常', neng == 0, neng)
        case('抽样全部能定位', nerr == 0, '%d/%d 未命中' % (nerr, len(smp)))
        case('抽样「自题自解」全部回到原篇', nback == 0, '%d/%d 回错篇' % (nback, len(smp)))

    print('=== 5. 引文原样性与整句性（C4/C5）===')
    if os.path.isfile(a1):
        by_pid = {}
        for p in poems:
            by_pid[p.pid] = p
            by_pid[p.loc] = p
        nq = badv = bads = 0
        for l in io.open(a1, encoding='utf-8-sig'):
            if not l.strip():
                continue
            r = json.loads(l)
            if r['类别'] not in ('C4', 'C5') or not r.get('答案'):
                continue
            for tag, pid in (r.get('定位') or {}).items():
                p = by_pid.get(pid)
                if p is None:
                    continue
                sents = Engine.split(p.raw)
                cut = len(sents) // 2
                fields = [('后段引文', sents[cut:])] if r['类别'] == 'C4' else \
                         [('前段引文', sents[:cut]), ('后段引文', sents[cut:])]
                for f, seg in fields:
                    qt = (r['答案'].get(tag) or {}).get(f)
                    if not qt:
                        continue
                    nq += 1
                    if qt not in p.raw and qt not in p.raw.replace('\n', ''):
                        badv += 1
                    qh = han_only(qt)
                    if not any(qh == han_only(s) for s in seg):
                        bads += 1
        case('引文 %d 条全部原样可定位' % nq, badv == 0, badv)
        case('引文全部等于所属分段的某一整句', bads == 0, bads)

    print('=== 6. 期望哈希清单 ===')
    mf = os.path.join(SOLVE, 'data', 'golden_sha.json')
    man = {}
    if os.path.isfile(mf):
        man = json.load(io.open(mf, encoding='utf-8-sig'))
    if args.update_manifest and os.path.isfile(a1):
        man[args.tag] = sha256(a1)
        os.makedirs(os.path.dirname(mf), exist_ok=True)
        io.open(mf, 'w', encoding='utf-8').write(
            json.dumps(man, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
        print('     已更新 %s：[%s] = %s' % (os.path.relpath(mf, ROOT), args.tag, man[args.tag]))
    elif args.tag in man and os.path.isfile(a1):
        case('[%s] 与清单里的哈希一致' % args.tag, man[args.tag].upper() == sha256(a1).upper(),
             '清单=%s 本轮=%s' % (man[args.tag][:16], sha256(a1)[:16]))
    else:
        # 修补：清单里没有该 tag 时，旧版只打一行提示——于是**tag 打错就静默通过**。
        # 门禁的意义是「不改坏就过」，因此缺条目必须判 FAIL（首次登记用 --update-manifest）。
        case('[%s] 期望哈希清单里必须有该条目（缺失即不可判定）' % args.tag, False,
             '清单缺少 [%s]；首次登记请加 --update-manifest' % args.tag)

    print('=== 7. 跨源重复篇的定位优先级（第九轮自检新增）===')
    # 背景：跨源存在「汉字逐字全同、标点不同」的重复篇（实测 2 组），标点差异会改变
    # 切句 → 句数/最长句，因此“选哪一份”会直接改变答案。官方口径 = poetry-source 那一份。
    # 本段把三个真实案例锁死，防止以后改定位逻辑时静默翻车。
    locks = [
        ('周容', '小重山', '谢了梅花恨不禁', 7, 15),
        ('李师中', '菩萨蛮', '子规啼破城楼月', 4, 14),
    ]
    for au, cp, head, want_n, want_len in locks:
        got = loc.find_one(au, cp, head, '')
        ok_src = got is not None and got.source == 'poetry-source'
        sents = Engine.split(got.raw) if got else []
        ok_n = len(sents) == want_n
        ok_len = bool(sents) and max(len(han_only(s)) for s in sents) == want_len
        case('跨源重复篇 %s《%s》→ 定位 poetry-source 那份' % (au, cp), ok_src,
             got and got.pid)
        case('跨源重复篇 %s《%s》→ 句数 %d / 最长 %d 字（官方口径）' % (au, cp, want_n, want_len),
             ok_n and ok_len, '句数=%d 最长=%d' % (len(sents), max([len(han_only(s)) for s in sents] or [0])))

    print('=== 8. 定位质量：路径统计 + 假阳性（第十轮新增）===')
    # ① 题面命中篇的定位路径分布：交付集合必须全部走高置信 A4。
    # ② 假阳性：捏造首句/词牌/作者时，定位器会不会“自信地答错”。
    import solver as _solver
    qp = args.questions
    paths = {}
    n_q = 0
    import io as _io
    for _l in _io.open(qp, encoding='utf-8-sig'):
        if not _l.strip():
            continue
        _q = json.loads(_l)
        _sp = _solver.parse_question(_q.get('问题', ''))
        n_q += 1
        for _tag in ('甲', '乙', '丙'):
            if _tag not in _sp:
                continue
            _p, _path = loc.find_one_traced(_sp[_tag]['作者'], _sp[_tag]['词牌'],
                                            han_only(_sp[_tag]['首句'])[:8], _sp.get('朝代', ''))
            _k = _path.split()[0]
            paths[_k] = paths.get(_k, 0) + 1
    n_a4 = paths.get('A4', 0)
    n_other = sum(v for k, v in paths.items() if k != 'A4')
    case('题面定位 %d 题（%d 篇，其中高置信 A4 %d 篇）全部走高置信路径 A4' % (
        n_q, sum(paths.values()), n_a4),
         n_other == 0, '路径分布=%s' % paths)
    # 假阳性抽样（固定种子，可复现）
    import random as _rnd
    _smp = _rnd.Random(10).sample(poems, 100)
    stat = {'真实': 0, '首句捏造': 0, '作者捏造': 0, '全捏造': 0}
    for _p in _smp:
        _h = han_only(_p.raw)
        if loc.find_one(_p.author, _p.cipai, _h[:8], _p.dynasty):
            stat['真实'] += 1
        if loc.find_one(_p.author, _p.cipai, _h[:3] + '春風明月不知路', _p.dynasty):
            stat['首句捏造'] += 1
        if loc.find_one(_p.author + '某', _p.cipai, _h[:8], _p.dynasty):
            stat['作者捏造'] += 1
        if loc.find_one('無名氏XYZ', '不存在調', '海雨天風', ''):
            stat['全捏造'] += 1
    print('     假阳性抽样（100 首）：真实命中 %d、首句捏造仍命中 %d、作者捏造仍命中 %d、全捏造命中 %d'
          % (stat['真实'], stat['首句捏造'], stat['作者捏造'], stat['全捏造']))
    case('完全捏造的篇目一律不命中（宁可缺勿滥）', stat['全捏造'] == 0, stat)
    case('真实篇 100%% 命中（抽样自题自解）', stat['真实'] == len(_smp), stat)

    print('\n=== 9. 交付产物一致性（第十一轮新增：corpus.db / 校订队列）===')
    # 入库与校订队列都是“新产物”，必须进常设门禁：行数变了要有人知道。
    db = os.path.join(ROOT, 'data', 'corpus.db')
    rv = os.path.join(ROOT, 'data', 'review_diff.csv')
    if os.path.exists(db):
        import sqlite3 as _sq
        _c = _sq.connect(db)
        n_poem = _c.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
        n_line = _c.execute('SELECT COUNT(*) FROM lines').fetchone()[0]
        n_full = len(poems)
        case('corpus.db 篇数 == 语料载入篇数（%d）' % n_full, n_poem == n_full, '%d vs %d' % (n_poem, n_full))
        case('corpus.db 句数 > 0 且篇均句数合理', n_line > 0 and 5 <= n_line / max(1, n_poem) <= 12,
             '%d 句 / 篇均 %.2f' % (n_line, n_line / max(1, n_poem)))
        _c.close()
    else:
        print('     （未建库：跳过 data/corpus.db 比对）')
    if os.path.exists(rv):
        import csv as _csv
        _rows = list(_csv.DictReader(io.open(rv, encoding='utf-8-sig')))
        _c = Counter(r.get('字') for r in _rows)
        case('校订队列非空且可解析（工单 %d 条）' % len(_rows), len(_rows) > 0)
        case('校订队列集中在已知口径例外字（长/别/绝/甚）',
             all(k in ('长', '别', '绝', '甚') for k in _c), _c.most_common(6))
        print('     校订工单 TOP：%s' % _c.most_common(5))
    else:
        print('     （未生成：跳过 data/reviews.csv 比对）')
    case('本段确实执行了比对（❌ 防“空比对照样 PASS”）：检查项 %d > 0' % COUNTS[0], COUNTS[0] > 0)

    print('\n=== 10. 前端视图与引擎的一致性底座（第十一轮新增）===')
    # 网页那一侧自己算数字，就必须证明它算得对：字→平仄映射要与引擎同源、对齐、覆盖完整。
    wp = os.path.join(ROOT, 'data', 'web_poems.json')
    if os.path.exists(wp):
        import json as _json
        _p = _json.load(io.open(wp, encoding='utf-8'))
        _ch, _cd = _p['tonemap']
        case('字→平仄映射两串等长（%d）' % len(_ch), len(_ch) == len(_cd))
        _tm = dict(zip(_ch, _cd))
        _ov = _json.load(io.open(os.path.join(ROOT, 'solve', 'data', 'pron_overrides.json'),
                                 encoding='utf-8-sig'))
        _bad = []
        for _zi, _v in _ov.items():
            _w = '2' if int(_v.get('tone') if isinstance(_v, dict) else _v) in (3, 4) else '1'
            if _tm.get(_zi) != _w:
                _bad.append(_zi)
        case('标定表全部字按标定值进入映射', not _bad, '不符 %s' % _bad)
        _miss = set()
        for _r in _p['rows']:
            for _c2 in _r[5]:
                if '\u4e00' <= _c2 <= '\u9fff' and _c2 not in _tm:
                    _miss.add(_c2)
        case('清词全库所用汉字全部有平仄映射（未覆盖 %d 字）' % len(_miss), len(_miss) == 0,
             sorted(_miss)[:6])
        _z = sum(1 for _r in _p['rows'] if _tm.get('绝') != '2' and '绝' in _r[5])
        case('「绝」在映射里为仄（防标定表未生效的静默偏差）', _tm.get('绝') == '2',
             '含绝且映射非仄的篇数 %d' % _z)
    else:
        print('     （未生成：跳过 data/web_poems.json 比对）')
    case('本段确实执行了比对（❌ 防“空比对照样 PASS”）', COUNTS[0] > 0)

    print('\n================ 回归门禁汇总 ================')
    print('检查项 %d，失败 %d 项' % (COUNTS[0], len(FAIL)))
    if FAIL:
        print('失败项：%s' % FAIL)
        return 1
    print('全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
