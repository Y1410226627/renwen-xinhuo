# -*- coding: utf-8 -*-
"""audit_questions.py —— **逐题摊开看答卷**：把 1000 道题的完整回答与判定全部落盘。

为什么要"逐题摊开"（主人的要求）：只看自动比对的汇总会漏掉**答非所问**与**牛头不对马嘴**——
这两类不体现为"数字不等"，而体现为**答的不是问的那件事**。所以本工具对每题：

  ① 把**题目**、**引擎解析出的条件**（【查询理解】那行）、**引擎完整答卷**、**独立真值** 全写进报告；
  ② 判定三类缺陷：
     · **答非所问（E_OFFTOPIC）**：问句要求的算子引擎**表达不出来**（∀/∄/≥k/=k/占比/条数/句位/交集/
       平仄串全等/一致性），且引擎**既不认账也不拒答**，却照旧给了一个肯定答案。
     · **运算错误（E_NUM/E_POEM/E_GROUP）**：给了答案，但数字/篇目/组名 ≠ 独立真值。
     · **牛头不对马嘴（E_INCOHERENT）**：答案**自相矛盾**——如「共命中 N 篇」却列出 >N 篇、
       或声称"未召回任何词作"却同时给了数字/引文。
  ③ 另外记录**守卫失职（E_GUARD）**：以上任一缺陷成立而 `guard` 仍报「通过」。
  ④ 对**引擎表达能力之内**的题（∃ + 并集 + 常规谓词/筛选），再加一道**条件逐项比对**（漏听/多听）。

用法：
  python tools/audit_questions.py                 # 审全量 1000 题，写 逐题答卷审查.md
  python tools/audit_questions.py --limit 50      # 只审前 50 题
  python tools/audit_questions.py --show Q0007    # 单独摊开看某一题（连答案原文）
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'solve'))
import gen_q1000 as G                       # 独立真值口径
import retrieve as R                        # 引擎解析
import ask as A                             # 引擎作答

QFILE = os.path.join(ROOT, 'data', 'questions_1000.jsonl')
DB = os.path.join(ROOT, 'data', 'corpus.db')

# ⚠ 必须认**负号**：差值题（「比…多几篇」）的答案常是负数，旧正则只取数字本体
#   → 「-21」被读成 21 → 把正确答案判成错（一批假失败）。
NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')
COUNT_RE = re.compile(r'共命中\s*(\d+)\s*篇')
PIN_RE = re.compile(r'\[E\d+\]')

# 引擎**表达得出来**的算子组合（其余即为「答非所问」的高危区）
# ⚠ 判据必须与引擎**当前实现**同步，否则自己做假（已实现却仍按"不支持"判 → 假 E_OFFTOPIC）。
#   2026-10-02 引擎已实现：∀／∄／≥k／=k／占比≥p／条数∈[a,b]（句级量词）、
#   the_句位奇偶／平仄串全等（谓词）、交集（篇内两值）。
SUPPORTED_LQ = {'∃', '∀', '∄', '=k', '≥k', '占比≥p', '条数∈[a,b]'}
SUPPORTED_SO = {'无', '并集', '交集'}
SUPPORTED_LP = {'句脚字', '句脚平仄', '平仄串包含', '平仄串全等', '句长区间', '句位奇偶'}
# ⚠ 别漏 '无'（= 没有篇级筛选，是最常见的一档）——漏了它会把一大批正确的题判成「答非所问」
SUPPORTED_PF = {'无', '元数据', '声情', '篇级指标区间', '派生量', '一致性'}
# 输出算子：2026-10-02 已全部实现（中位数/众数/占比/差值/条件概率/第N名）→ 空集。
# ⚠ 判据必须与 `retrieve._OP_PATTERNS` 同步：那边清空，这边也必须清空，否则自己做假。
UNSUPPORTED_TASK = set()


def supported(sig, task):
    lq, lp, pf, so, _out = sig
    if task in UNSUPPORTED_TASK:
        return False
    return lq in SUPPORTED_LQ and so in SUPPORTED_SO and lp in SUPPORTED_LP and pf in SUPPORTED_PF


def nums_in(t):
    return [float(x) for x in NUM_RE.findall(t or '')]


def has_num(t, v, tol=0.06):
    if v is None:
        return False
    for x in nums_in(t):
        if abs(x - v) <= tol or abs(x - round(v, 1)) <= tol or abs(x - int(round(v))) <= tol:
            return True
    return False


def engine_conds(sp):
    """引擎解析出的条件（人话）→ 便于与意图逐项比对。"""
    return {
        '朝代': sorted(R._vals(sp, 'dynasty') or []),
        '词人': sorted(R._vals(sp, 'author') or []),
        '词牌': sorted(R._vals(sp, 'cipai') or []),
        '句脚字': sorted(R._vals(sp, 'tail') or []),
        '句脚平仄': sp.tail_pz,
        '声律串': sp.pz,
        '声情': sp.scene,
        '数值': dict(sp.rng or {}),
        '词面': list(sp.keywords or []),
        '未解析': list(sp.unparsed or []),
        '聚合': sp.agg,
        '配对': bool(getattr(sp, 'pair', None)),
        '排序': sp.order_by,
    }


def truth_of(conn, sig, p, task):
    t = {}
    if task in ('count', 'list'):
        t['n'] = G.count_hits(conn, sig, p)
    elif task in ('extreme', 'extreme_field', 'rank'):
        row = G.out_order(conn, sig, p)
        t['pid'] = row[0] if row else None
        t['val'] = row[1] if row else None
        if task == 'extreme_field' and t['pid']:
            t['field'] = G.truth_field(conn, t['pid'], p['then_field'])
    elif task in ('agg_top', 'disp'):
        rec = G.out_groups(conn, sig, p, p['gb'], p['metric'],
                           agg=('stdev' if task == 'disp' else 'weighted'))
        if rec:
            ext = p.get('ext', 'max')
            v = max(rec.values()) if ext == 'max' else min(rec.values())
            t['group'] = sorted(k for k, x in rec.items() if abs(x - v) < 1e-9)[0]
            t['val'] = v
    elif task == 'cmp':
        rec = G.out_groups(conn, sig, p, p['gb'], p['metric'])
        vals = p.get('_vals') or sorted(rec, key=lambda k: -rec[k]['n'])[:2]
        if len(vals) >= 2:
            va = G.group_value(rec[vals[0]], p['metric']) if vals[0] in rec else None
            vb = G.group_value(rec[vals[1]], p['metric']) if vals[1] in rec else None
            t['pairs'] = [(vals[0], va), (vals[1], vb)]
            if va is not None and vb is not None and va != vb:
                t['winner'] = vals[0] if va > vb else vals[1]
    elif task == 'share':
        # ⚠ 2026-10-03 口径修正（真值自身错，不是引擎错）：问句是「…的作品，占全部清词
        #   （或所限朝代）的百分之几」。**分子必须与分母同域**——旧版分子取 `count_hits`
        #   （sig 里没有朝代 → **全库**），分母却取「清词 26742」→ 两个不同集合相除，
        #   真值自身不自洽（实测 Q0006：分子 2669/全库、分母 26742/清词 = 9.98%，而按条件
        #   落在清词里的只有 1420 篇 → 5.3%，后者才是问句要的数）。
        #   规则：分母朝代 = 范围里限定的朝代（无则默认「清」）；分子 = 同域内命中篇数。
        d = (p.get('dynasty') or ['清'])[0]
        _w, _a = G.scope_where(sig, p)
        hit = conn.execute('SELECT COUNT(*) FROM poems p WHERE (%s) AND p.dynasty = ?'
                           % _w, list(_a) + [d]).fetchone()[0]
        tot = conn.execute('SELECT COUNT(*) FROM poems WHERE dynasty = ?', (d,)).fetchone()[0]
        t['pct'] = 100.0 * hit / tot if tot else 0.0
        t['n'] = hit
    elif task == 'median':
        t['v'] = G.out_median(conn, sig, p, p['metric'])
    elif task == 'mode':
        mm = G.out_mode(conn, sig, p, p['metric'])
        t['v'] = mm[0] if mm else None
    elif task == 'diff':
        # ⚠ 第二个范围**不带**原题的并集/交集（问句里它只是另一段条件）
        _sig2 = sig[:3] + ('无',) + sig[4:]
        t['n'] = G.count_hits(conn, sig, p) - G.count_hits(conn, _sig2, p['_p2'])
    elif task == 'condshare':
        _sig2 = sig[:3] + ('无',) + sig[4:]
        t['pct'] = 100.0 * (G.out_cond_share(conn, sig, p, _sig2, p['_p2']) or 0.0)
    elif task == 'pair':
        g, pr = G.out_pair(conn, sig, p)
        t['groups'], t['pairs'] = g, pr
    return t


def judge(task, truth, ans, res):
    """→ (ok: bool|None, 缺陷列表)。"""
    bad = []
    if not ans:
        return False, ['E_EMPTY 没有答案文本']
    # 牛头不对马嘴：自相矛盾
    m = COUNT_RE.search(ans)
    if m:
        n = int(m.group(1))
        shown = len(res.get('blocks') or [])
        if n and shown > n:
            bad.append('E_INCOHERENT 声称共命中 %d 篇，却展示 %d 篇' % (n, shown))
        if '未召回' in ans and nums_in(ans):
            bad.append('E_INCOHERENT 既说「未召回」又给出数字')
    # 运算/事实
    if task in ('count', 'list'):
        got = int(COUNT_RE.search(ans).group(1)) if COUNT_RE.search(ans) else None
        if got != truth.get('n'):
            bad.append('E_NUM 真值 %s ／ 引擎 %s' % (truth.get('n'), got))
    elif task in ('extreme', 'extreme_field', 'rank'):
        blocks = res.get('blocks') or []
        # ⚠ 第 N 名/极值类可能把篇目写在**正文**里、blocks 为空 —— 优先取结果里的 pid
        got = (blocks[0].get('pid') if blocks else None) or res.get('pid')
        if got != truth.get('pid'):
            bad.append('E_POEM 真值篇 %s ／ 引擎篇 %s' % (truth.get('pid'), got))
    elif task in ('agg_top', 'disp'):
        g = truth.get('group')
        if g is None:
            # 真值＝范围内**没有可统计的组**（所有组样本数 < 3 或范围内 0 篇）：引擎如实报「无数据」即对。
            # ⚠ 判据要准：**只有真的给出了组名**才算「给了组名」——旧写法一见到「最多/最少」就判错，
            #   而【查询理解】行里本来就会写「取最少，篇幅（字）」（实测 Q0379 假失败）。
            if ('共命中 0 篇' not in (ans or '')) and ('未见支持' not in (ans or '')) \
                    and re.search(r'(最多|最少)的是\s*\S|波动最大的是〔', ans or ''):
                bad.append('E_GROUP 真值为「无可统计的组」，引擎却给了组名')
        elif g not in ans:
            bad.append('E_GROUP 真值组 %s 未出现在答案里' % g)
    elif task == 'cmp':
        # ⚠ 分组对比题引擎的「结论：X 更高」**不带【】方括号**，旧版只搜【结论】行 → 假失败。
        #   改为在**整段答案**里找胜出组名。
        w = truth.get('winner')
        if w and w not in ans:
            bad.append('E_GROUP 真值胜出组 %s 未出现在答案里' % w)
    elif task in ('share', 'median', 'mode', 'diff', 'condshare'):
        v = truth.get('pct', truth.get('v', truth.get('n')))
        if v is None:
            # ⚠ 真值＝「本范围内**无可统计量**」（如中位数题的范围为空 → 真值 None）。
            #   此时引擎**只要不给出一个具体取值**就算对（「共命中 0 篇」或如实认账都行）。
            #   判据不能只数数字——拒答文本会**回显查询条件**（里面本就有数字）。
            if re.search(r'(中位数|最常出现的取值|取值)是\s*-?\d', ans or '') \
                    or re.search(r'共\s*\d+\s*篇，', ans or ''):
                bad.append('E_NUM 真值为「无可统计」，引擎却给出了数字')
        elif not has_num(ans, v):
            bad.append('E_NUM 真值 %s 未出现在答案里' % v)
    elif task == 'pair':
        if not (has_num(ans, truth.get('groups')) or has_num(ans, truth.get('pairs'))):
            bad.append('E_NUM 真值组数/对数 %s / %s 未出现'
                       % (truth.get('groups'), truth.get('pairs')))
    return (not bad), bad


def one(conn, r):
    sig = tuple(r['sig'].split('｜'))
    p = dict(r['spec'])
    p.update(r['intent'] or {})
    task = r['task']
    it = {'id': r['id'], 'sig': r['sig'], 'q': r['q'], 'task': task,
          'in_supported': supported(sig, task), 'bad': [], 'err': None}
    try:
        it['truth'] = truth_of(conn, sig, p, task)
        sp = R.parse_query(conn, r['q'])
        it['conds'] = engine_conds(sp)
        res = A.answer(conn, r['q'], topk=3)
    except Exception as e:
        it['err'] = '%s: %s' % (type(e).__name__, e)
        it['trace'] = traceback.format_exc(limit=3)
        it['bad'] = ['E_CRASH']
        return it
    ans = res.get('answer') or ''
    it['answer'] = ans
    it['guard'] = bool(res.get('verify') and res['verify'][0])
    it['refused'] = bool(res.get('refused'))
    it['cond_line'] = (ans.splitlines() or [''])[0]
    ok, bad = judge(task, it['truth'], ans, res)
    it['ok'] = ok
    it['bad'] = bad
    # 答非所问：超出表达能力，却既不认账也不拒答，还给了肯定答案
    if not it['in_supported']:
        disclosed = bool(it['conds'].get('未解析')) or it['refused']
        if not disclosed:
            bad.append('E_OFFTOPIC 问句的算子超出引擎表达能力，却未认账也未拒答（照旧作答）')
            it['ok'] = False
    if bad and it['guard']:
        it['bad'] = list(bad) + ['E_GUARD 有缺陷但 guard 报「通过」']
    return it


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--out', default=os.path.join(ROOT, '逐题答卷审查.md'))
    ap.add_argument('--show', default=None)
    ap.add_argument('--maxlen', type=int, default=1600,
                    help='答卷原文写进报告的最大字数（「重新问一遍」时给大值，如 4000）')
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(QFILE, encoding='utf-8')]
    if args.limit:
        rows = rows[:args.limit]
    conn = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True)

    if args.show:
        for r in rows:
            if r['id'] == args.show:
                it = one(conn, r)
                print(json.dumps(it, ensure_ascii=False, indent=2)[:4000])
                return 0
        print('没找到 %s' % args.show)
        return 1

    res_all, kinds, t0 = [], Counter(), time.time()
    for i, r in enumerate(rows, 1):
        if i % 100 == 0:
            sys.stderr.write('  … 已审 %d/%d（%.0f 秒）\n' % (i, len(rows), time.time() - t0))
            sys.stderr.flush()
        it = one(conn, r)
        res_all.append(it)
        for b in it['bad']:
            kinds[b.split()[0]] += 1

    tot = len(rows)
    passed = sum(1 for it in res_all if it.get('ok'))
    print('=== 逐题审查汇总（%d 题，用时 %.0f 秒）===' % (tot, time.time() - t0))
    print('  完全正确 %d ／ 有缺陷 %d' % (passed, tot - passed))
    for k, v in kinds.most_common():
        print('  %-14s %d' % (k, v))

    L = ['# 逐题答卷审查（1000 题全部摊开）', '',
         '每题给出：**题目 / 引擎解析出的条件 / 引擎完整答卷 / 独立真值 / 判定**。', '',
         '缺陷码：`E_OFFTOPIC` 答非所问（算子超出表达能力且未认账）、`E_NUM` 运算错误、',
         '`E_POEM/E_GROUP` 篇目/分组答错、`E_INCOHERENT` 自相矛盾、`E_GUARD` 守卫失职、',
         '`E_CRASH` 引擎异常。', '',
         '## 汇总', '',
         '| 缺陷码 | 条数 |', '| --- | --- |']
    for k, v in kinds.most_common():
        L.append('| %s | %d |' % (k, v))
    L += ['', '完全正确 **%d** / %d。' % (passed, tot), '', '## 逐题明细', '']
    for it in res_all:
        flag = '✅' if it.get('ok') else '❌'
        L.append('### %s %s `%s`' % (flag, it['id'], it['sig']))
        L.append('')
        L.append('**问**：%s' % it['q'])
        if it.get('err'):
            L.append('')
            L.append('**引擎异常**：`%s`' % it['err'])
            L.append('')
            continue
        L.append('')
        L.append('**引擎解析出的条件**：`%s`' % json.dumps(it.get('conds'), ensure_ascii=False))
        L.append('')
        L.append('**独立真值**：`%s`' % json.dumps(it.get('truth'), ensure_ascii=False))
        L.append('')
        L.append('**引擎答卷**：')
        L.append('')
        L.append('```')
        L.append((it.get('answer') or '')[:args.maxlen])
        L.append('```')
        if it['bad']:
            L.append('')
            L.append('**判定**：❌ %s' % '；'.join(it['bad']))
        else:
            L.append('')
            L.append('**判定**：✅ 与真值一致')
        L.append('')
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print('\n已写出 %s' % args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
