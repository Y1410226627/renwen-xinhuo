# -*- coding: utf-8 -*-
"""verify_1000.py —— **逐题复核：答非所问 + 准确性**（比数字比对更严的一层）。

为什么要再写一层（主人的要求：「逐个检查是否答非所问、是否准确」）：
只比「答案里的数字 == 真值」会漏掉两类错——
  · **答非所问**：数字碰巧对上，但条件听漏了一条/听错了一条（范围其实不同）；
  · **形态不符**：问「共几篇」却答了一串篇目、问「中位数」却答了一个篇名。

所以每题做**四道独立检查**：
  ① **条件理解一致性**（最强）：把引擎解析出的 spec 编成 SQL 数一遍命中篇数，
     与独立真值口径（`gen_q1000.scope_where`）的命中篇数**逐题相等**；
     任何一条条件听漏/听错，两边集合就不会等（除非极巧合成，概率可忽略）。
  ② **条件词表对齐**：把问句 spec 的每一类条件（谓词/量词/集合算子/篇级筛选/参数）
     逐项与引擎 spec 对照，指出缺了哪一项——用于定位①不等时的原因。
  ③ **答案形态**：该题型**必须有**的表述（如「共命中 N 篇」「中位数是」「波动最大的是」）
     必须出现；否则判「答非所问」。
  ④ **准确性**：与独立真值逐项比对（数字/篇目/组名），并查自相矛盾。

用法：
  python tools/verify_1000.py                  # 全量 1000 题
  python tools/verify_1000.py --limit 50
  python tools/verify_1000.py --show Q0057
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'solve'))
import gen_q1000 as G
import retrieve as R
import ask as A
import audit_questions as QA          # 复用「真值 → 判定」的既有口径

QF = os.path.join(ROOT, 'data', 'questions_1000.jsonl')
DB = os.path.join(ROOT, 'data', 'corpus.db')

NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')
COUNT_RE = re.compile(r'共命中\s*(\d+)\s*篇')


# ----------------------------------------------------------------- ① 条件理解一致性
def engine_scope_count(conn, spec):
    """按引擎 spec 数命中篇数（与真值口径比的是**同一个集合**）。"""
    w, a = R._sql(spec)
    return conn.execute('SELECT COUNT(*) FROM poems p WHERE ' + w, a).fetchone()[0]


def truth_scope_count(conn, sig, p):
    return G.count_hits(conn, sig, p)


def _truth_scope(conn, sig, p, task):
    """与独立真值**同一口径**的命中篇数（占比题的分子要落回分母朝代同域）。"""
    if task == 'share':
        d = (p.get('dynasty') or ['清'])[0]
        w, a = G.scope_where(sig, p)
        return conn.execute('SELECT COUNT(*) FROM poems p WHERE (%s) AND p.dynasty = ?'
                            % w, list(a) + [d]).fetchone()[0]
    return G.count_hits(conn, sig, p)


# ----------------------------------------------------------------- ② 条件词表对齐
def cond_terms(sig, p):
    """问句 spec → 应有的条件词表（人话），用于逐项核对引擎听没听全。"""
    lq, lp, pf, so, out = sig
    need = []
    if lp == '句脚字':
        need.append('句脚字=%s' % p['tail'])
        if so in ('并集', '交集') and p.get('tail2'):
            need.append('%s=%s' % (so, p['tail2']))
    elif lp == '句脚平仄':
        need.append('句脚平仄=%s' % p['tone'])
    elif lp == '平仄串包含':
        need.append('平仄串含%s' % p['pz'])
    elif lp == '平仄串全等':
        need.append('平仄串全等=%s' % p['pz'])
    elif lp == '句长区间':
        need.append('句长∈[%s,%s]' % (p['lo'], p['hi']))
    else:
        need.append('句位=%s数' % ('奇' if p['parity'] == 0 else '偶'))
    need.append('量词=%s' % lq)
    if pf == '元数据':
        for k, lab in (('dynasty', '朝代'), ('author', '词人'), ('cipai', '词牌')):
            if p.get(k):
                need.append('%s=%s' % (lab, '／'.join(p[k])))
    elif pf == '声情':
        need.append('声情=%s' % p['scene'])
    elif pf == '篇级指标区间':
        need.append('数值区间=%s' % json.dumps(p.get('rng') or {}, ensure_ascii=False))
    elif pf == '派生量':
        need.append('变化幅度≥%s' % p['dchg'])
    elif pf == '一致性':
        need.append('一致性=%s' % p['scene'])
    return need


def engine_terms(sp):
    """引擎 spec → 实际听出来的条件词表。"""
    got = []
    tl = R._vals(sp, 'tail')
    if tl:
        got.append('句脚字=%s' % '／'.join(tl))
    if sp.tail_pz:
        got.append('句脚平仄=%s' % sp.tail_pz)
    if sp.pz:
        got.append('平仄串含%s' % sp.pz)
    if sp.pz_exact:
        got.append('平仄串全等=%s' % sp.pz_exact)
    lq = sp.line_q or {}
    if lq:
        got.append('量词=%s' % lq['op'])
        k, v = lq['pred']
        if k == 'tail':
            got.append('句脚字=%s' % v)
        elif k == 'tail_any':
            got.append('句脚字=%s' % '／'.join(v))
        elif k == 'tail_pz':
            got.append('句脚平仄=%s' % v)
        elif k == 'pz':
            got.append('平仄串含%s' % v)
        elif k == 'pz_exact':
            got.append('平仄串全等=%s' % v)
        elif k == 'len':
            got.append('句长∈[%s,%s]' % (v[0], v[1]))
        else:
            got.append('句位=%s数' % ('奇' if v == 0 else '偶'))
    for t in sp.tail_each:
        got.append('交集=%s' % t)
    for a in R._vals(sp, 'dynasty'):
        got.append('朝代=%s' % a)
    for a in R._vals(sp, 'author'):
        got.append('词人=%s' % a)
    for a in R._vals(sp, 'cipai'):
        got.append('词牌=%s' % a)
    if sp.scene:
        got.append('声情=%s' % sp.scene)
    for k, lab in (('ze_min', '数值区间'), ('ze_max', '数值区间'), ('len_min', '数值区间'),
                   ('len_max', '数值区间'), ('sent_min', '数值区间'), ('sent_max', '数值区间'),
                   ('change_min', '变化幅度'), ('change_max', '变化幅度')):
        if k in sp.rng:
            if lab == '数值区间':
                got.append('数值区间=%s' % json.dumps(sp.rng, ensure_ascii=False))
            else:
                got.append('变化幅度≥%s' % sp.rng[k])
    if getattr(sp, 'consist', None):
        got.append('一致性=%s' % sp.consist)
    return got


def term_missing(need, got):
    """需要的条件词里，哪些在引擎侧**找不到**（做归一化后比较）。"""
    gset = set(got)
    gjoin = '｜'.join(got)
    miss = []
    for n in need:
        if n in gset:
            continue
        if n.startswith('量词='):
            op = n.split('=', 1)[1]
            # ∃ 常常由「句脚字=…」本身表达，没有显式 line_q 也算听了
            if op == '∃' and re.search(r'(句脚字|句脚平仄|平仄串含|平仄串全等|句长∈|句位)=', gjoin):
                continue
            if op == '∀' and '量词=∀' in gjoin:
                continue
            miss.append(n); continue
        if n.startswith('句脚字='):
            vals = n.split('=', 1)[1].split('／')
            if all(v in gjoin for v in vals):
                continue
        if n.startswith('声情=') and '声情=' in gjoin:
            continue
        if n.startswith('数值区间=') and '数值区间=' in gjoin:
            continue
        if n.startswith('并集='):
            v = n.split('=', 1)[1]
            if v in gjoin:
                continue
        miss.append(n)
    return miss


# ----------------------------------------------------------------- ③ 答案形态
def form_ok(task, ans, res, qspec):
    """该题型**必须有**的表述。返回 (ok, 说明)。"""
    a = (ans or '').replace('**', '').replace('＊', '')     # 去掉 markdown 加粗再判形态
    def has(*pats):
        return any(p in a for p in pats)
    # ⚠ 范围内**一篇都没有**（或语料外范围）时，「如实报 0 篇 / 如实认账」本身就是正确形态——
    #   此时没有中位数/众数/极值/分组可言，不能反过来要求它给出这些表述（实测 24 题交集题
    #   真值就是 None/{}，引擎答「共命中 0 篇」被判「答非所问」，属判据过窄）。
    if re.search(r'共命中\s*0\s*篇', a) or '未见支持' in a or '未召回到任何词作' in a \
            or '没有可用于该统计量的数据' in a:
        return True, ''
    if task in ('count', 'list'):
        if not COUNT_RE.search(a):
            return False, '没有给出「共命中 N 篇」'
        n = int(COUNT_RE.search(a).group(1))
        if n and not res.get('blocks') and '全库仅此' not in a and task == 'list':
            return False, '问「有哪些」却没给出任何篇目'
        return True, ''
    if task in ('extreme', 'extreme_field'):
        if '【极值复核】' not in a:
            return False, '极值题没有【极值复核】行'
        if not (res.get('blocks') or res.get('pid')):
            return False, '没有给出极值篇目'
        return True, ''
    if task == 'rank':
        if not re.search(r'第[一二三四五六七八九十][大小高矮低短长多少]的是', a):
            return False, '第N名题没有给出「第N…的是」'
        return True, ''
    if task == 'median':
        if '中位数是' not in a:
            return False, '中位数题没有给出「中位数是」'
        return True, ''
    if task == 'mode':
        if '取值是' not in a:
            return False, '众数题没有给出「取值是」'
        return True, ''
    if task == 'diff':
        if '相差' not in a:
            return False, '差值题没有给出「相差」'
        return True, ''
    if task == 'condshare':
        if not re.search(r'占\s*-?[\d.]+\s*%', a):
            return False, '条件概率题没有给出百分比'
        return True, ''
    if task == 'share':
        if not re.search(r'占.*?的\s*-?[\d.]+\s*%', a):
            return False, '占比题没有给出百分比'
        return True, ''
    if task == 'agg_top':
        if not has('最多的是', '最少的是'):
            return False, '分组极值题没有给出「最多/最少的是 <组名>」'
        return True, ''
    if task == 'disp':
        if '波动最大的是' not in a:
            return False, '离散度题没有给出「波动最大的是」'
        return True, ''
    if task == 'cmp':
        # 二组比较写「更高/更低」，三组比较写「最高；完整次序…」——两种都算合规
        if not has('更高', '更低', '最高', '最低', '持平', '可比的组不足'):
            return False, '分组对比题没有给出比较结论'
        return True, ''
    if task == 'pair':
        if not re.search(r'共\s*\d+\s*组', a):
            return False, '配对题没有给出「共 N 组、M 对」'
        return True, ''
    return True, ''


# ----------------------------------------------------------------- 单题复核
def one(conn, r):
    sig = tuple(r['sig'].split('｜'))
    p = dict(r['spec'])
    p.update(r.get('intent') or {})
    it = {'id': r['id'], 'sig': r['sig'], 'task': r['task'], 'q': r['q'],
          'bad': [], 'miss': [], 'scope_t': None, 'scope_e': None}
    try:
        it['truth'] = QA.truth_of(conn, sig, p, r['task'])
        it['scope_t'] = _truth_scope(conn, sig, p, r['task'])
        # ⚠ 两范围题（差值/条件概率）：问句里**同时**含两个范围，直接解析整句会把第二个范围
        #   的条件也并进来。引擎作答时用的是「外层范围」那一段文字——这里照同口径取，
        #   否则会造出一批假「条件理解不一致」。
        _q = r['q']
        if r['task'] in ('diff', 'condshare'):
            _q = A._outer_scope_text(r['q'])
        sp = R.parse_query(conn, _q)
        it['conds'] = QA.engine_conds(sp)
        it['scope_e'] = engine_scope_count(conn, sp)
        it['miss'] = term_missing(cond_terms(sig, p), engine_terms(sp))
        res = A.answer(conn, r['q'], topk=3)
        it['answer'] = res.get('answer') or ''
    except Exception as e:
        it['bad'] = ['E_CRASH %s: %s' % (type(e).__name__, e)]
        it['trace'] = traceback.format_exc(limit=3)
        return it
    # ① 条件理解一致性
    if it['scope_t'] != it['scope_e']:
        it['bad'].append('E_SCOPE 条件理解不一致（真值命中 %s 篇／引擎 %s 篇）'
                         % (it['scope_t'], it['scope_e']))
    # ①b **「0 篇」不许乱报**：引擎说「共命中 0 篇」时，范围内的实际命中篇数必须是 0。
    #     （实测踩过：范围有 6 篇、只是没有可统计的组，却被写成了「共命中 0 篇」。）
    if '共命中 0 篇' in (it.get('answer') or '') and (it['scope_e'] or 0) > 0:
        it['bad'].append('E_ZERO 谎报 0 篇（范围内实际命中 %s 篇）' % it['scope_e'])
    # ② 条件词表对齐（只在①不等时作为原因说明，本身不单独判错）
    # ③ 形态
    ok, why = form_ok(r['task'], it['answer'], res, p)
    if not ok:
        it['bad'].append('E_FORM 答非所问（%s）' % why)
    # ④ 准确性与自相矛盾（复用逐题审查的判据）
    ok2, bad2 = QA.judge(r['task'], it['truth'], it['answer'], res)
    it['bad'] += bad2
    return it


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--out', default=os.path.join(ROOT, '重新问答复核_答非所问与准确性.md'))
    ap.add_argument('--show', default=None)
    ap.add_argument('--maxlen', type=int, default=2600)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(QF, encoding='utf-8')]
    if args.limit:
        rows = rows[:args.limit]
    conn = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True)

    if args.show:
        for r in rows:
            if r['id'] == args.show:
                print(json.dumps(one(conn, r), ensure_ascii=False, indent=2)[:6000])
                return 0
        print('没找到 %s' % args.show)
        return 1

    res_all, kinds, t0 = [], Counter(), time.time()
    for i, r in enumerate(rows, 1):
        if i % 100 == 0:
            sys.stderr.write('  … 已复核 %d/%d（%.0f 秒）\n' % (i, len(rows), time.time() - t0))
            sys.stderr.flush()
        it = one(conn, r)
        res_all.append(it)
        for b in it['bad']:
            kinds[b.split()[0]] += 1

    tot = len(rows)
    passed = sum(1 for it in res_all if not it['bad'])
    scope_bad = sum(1 for it in res_all if it['scope_t'] != it['scope_e'])
    print('=== 逐题复核（答非所问 + 准确性）：%d 题，用时 %.0f 秒 ===' % (tot, time.time() - t0))
    print('  全部通过 %d ／ 有问题 %d' % (passed, tot - passed))
    print('  其中「条件理解不一致」%d 题' % scope_bad)
    for k, v in kinds.most_common():
        print('  %-12s %d' % (k, v))

    L = ['# 逐题复核：答非所问 + 准确性（1000 题全部摊开）', '',
         '每题给出：**题目 / 引擎听出的条件 / 「条件理解一致性」（引擎命中篇数 vs 独立真值命中篇数）',
         '/ 引擎完整答卷 / 独立真值 / 判定**。', '',
         '缺陷码：`E_SCOPE` 条件听漏或听错（两边命中集合不等）、`E_FORM` 答非所问（答案形态与问句类型不符）、',
         '`E_NUM/E_POEM/E_GROUP` 数值/篇目/分组答错、`E_INCOHERENT` 自相矛盾、`E_CRASH` 引擎异常。', '',
         '## 汇总', '', '| 项目 | 数 |', '| --- | --- |',
         '| 题量 | %d |' % tot, '| 全部通过 | **%d** |' % passed,
         '| 条件理解不一致 | %d |' % scope_bad]
    for k, v in kinds.most_common():
        L.append('| %s | %d |' % (k, v))
    L += ['', '## 逐题明细', '']
    for it in res_all:
        flag = '✅' if not it['bad'] else '❌'
        L.append('### %s %s `%s`' % (flag, it['id'], it['sig']))
        L.append('')
        L.append('**问**：%s' % it['q'])
        if it.get('bad') and any(b.startswith('E_CRASH') for b in it['bad']):
            L.append('')
            L.append('**引擎异常**：`%s`' % it['bad'][0])
            L.append('')
            continue
        L.append('')
        L.append('**引擎听出的条件**：`%s`' % json.dumps(it.get('conds'), ensure_ascii=False))
        L.append('')
        L.append('**条件理解一致性**：独立真值命中 `%s` 篇 ／ 引擎命中 `%s` 篇 %s'
                 % (it['scope_t'], it['scope_e'],
                    '✔ 一致' if it['scope_t'] == it['scope_e'] else '✘ 不一致'))
        if it.get('miss'):
            L.append('')
            L.append('**未听出的条件**：`%s`' % '，'.join(it['miss']))
        L.append('')
        L.append('**独立真值**：`%s`' % json.dumps(it.get('truth'), ensure_ascii=False))
        L.append('')
        L.append('**引擎答卷**：')
        L.append('')
        L.append('```')
        L.append((it.get('answer') or '')[:args.maxlen])
        L.append('```')
        L.append('')
        L.append('**判定**：%s' % ('✅ 听懂且答对' if not it['bad'] else '❌ ' + '；'.join(it['bad'])))
        L.append('')
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print('\n已写出 %s' % args.out)
    return 0 if passed == tot else 1


if __name__ == '__main__':
    sys.exit(main())
