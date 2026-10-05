# -*- coding: utf-8 -*-
"""gen_q1000.py —— v3：**以「操作链」为单位**出题，强制 **1000 题 = 1000 条互不相同的链**。

v1/v2 的教训（主人在《核验报告》里逐题指出）：
  「换汤不换药」的判据是——把词牌/朝代/句脚字/声律串/阈值等**参数抽象掉**后，**操作链是否相同**。
  v2 有 24 个「形状」，但那 24 个形状就是 24 条链；同一形状内的 70 题只是参数不同。
  → **参数化 ≠ 多样性。** 真正要变的是**算子序列**。

v3：一道题 = 一条签名 sig（**只由算子构成，不含任何参数**）：sig = LQ｜LP｜PF｜SO｜OUT
  生成器**强制 sig 全局唯一** → 1000 题对应 1000 条不同的链；
  审查工具用同一签名算法复算，**出现同签名即判「换汤不换药」**。

算子空间（组合 7×6×6×3×16 = 12096，可行子集足以放回不重复地抽 1000 条）：
  LQ  句级量词 7：∃ / ∀ / ∄ / ≥k / =k / 占比≥p / 条数∈[a,b]
  LP  句级谓词 6：句脚字 / 句脚平仄 / 平仄串包含 / 平仄串全等 / 句长区间 / 句位
  PF  篇级筛选 6：元数据 / 声情 / 篇级指标区间 / 派生量 / 一致性 / 无
  SO  集合算子 3：无 / 并集 / 交集
  OUT 输出算子 16：计数／列举／极值／极值再取字段／第N名／分组极值／二组比较／三组比较／
                  占比／离散度最大组／中位数／众数／两范围计数差／条件概率／配对／最相近篇

真值口径：`scope_where()` 独立于 solve/，只依赖库表；每个 OUT 有独立复算函数。

输出 data/questions_1000.jsonl：{"id","sig","task","q","spec","intent"}
用法：python tools/gen_q1000.py [--n 1000] [--seed 20261003]
"""
import argparse
import itertools
import json
import os
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LQ = ['∃', '∀', '∄', '≥k', '=k', '占比≥p', '条数∈[a,b]']
LP = ['句脚字', '句脚平仄', '平仄串包含', '平仄串全等', '句长区间', '句位奇偶']
PF = ['元数据', '声情', '篇级指标区间', '派生量', '一致性', '无']
SO = ['无', '并集', '交集']
OUT = ['计数', '列举', '极值', '极值再取字段', '第N名', '分组极值', '二组比较', '三组比较',
       '占比', '离散度最大组', '中位数', '众数', '两范围计数差', '条件概率', '配对', '最相近篇']

LEADS = ['', '', '', '', '请问', '帮我查一下', '麻烦', '劳驾', '问一下', '查一下',
         '想看看', '请统计', '给我个结果：', '帮我算算', '请给出']
SCENE_PHRASE = {
    '后段上升': ['后段上升', '后半段升高', '后段走高', '后段趋于上升'],
    '后段下降': ['后段下降', '后半段降低', '后段走低', '后段趋于下降'],
    '前后持平': ['前后持平', '前后段不变', '两段持平', '前后平稳'],
}
_CN = {0: '零', 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九',
       10: '十', 11: '十一', 12: '十二', 13: '十三', 14: '十四', 15: '十五', 16: '十六',
       17: '十七', 18: '十八', 19: '十九', 20: '二十', 25: '二十五', 30: '三十', 40: '四十',
       50: '五十', 60: '六十', 70: '七十', 80: '八十', 90: '九十', 100: '一百',
       110: '一百一十', 120: '一百二十', 150: '一百五十', 200: '两百'}


def _zh_under100(n, lead_one=False):
    """100 以内读法。`lead_one=True` 时 10~19 读作「一十X」——百位后的余数必须带这个「一」。"""
    if n < 10:
        return _CN[n]
    if n < 20:
        return ('一十' if lead_one else '十') + (_CN[n - 10] if n > 10 else '')
    t, o = divmod(n, 10)
    return _CN[t] + '十' + (_CN[o] if o else '')


def zh(n, style='cn'):
    n = int(n)
    if style == 'ar':
        return str(n)
    if n in _CN:
        return _CN[n]
    if n < 20:
        return '十' + _CN[n - 10]
    if n < 100:
        return _zh_under100(n)
    if n < 1000:
        h, r = divmod(n, 100)
        s = ('两百' if h == 2 else _CN[h] + '百')
        return s if r == 0 else s + ('零' + _CN[r] if r < 10 else _zh_under100(r, lead_one=True))
    return str(n)


def lead(rng):
    return rng.choice(LEADS) if rng.random() < 0.3 else ''


def load_vocab(conn):
    v = {}
    v['dyn'] = [r[0] for r in conn.execute(
        'SELECT dynasty FROM poems GROUP BY dynasty ORDER BY COUNT(*) DESC')]
    v['author'] = [r[0] for r in conn.execute(
        'SELECT author FROM poems WHERE author IS NOT NULL AND author != "" '
        'GROUP BY author HAVING COUNT(*) >= 6 ORDER BY COUNT(*) DESC LIMIT 300')]
    v['cipai'] = [r[0] for r in conn.execute(
        'SELECT cipai FROM poems WHERE cipai IS NOT NULL AND cipai != "" '
        'GROUP BY cipai HAVING COUNT(*) >= 10 ORDER BY COUNT(*) DESC LIMIT 250')]
    v['tail'] = [r[0] for r in conn.execute(
        'SELECT tail FROM lines WHERE tail IS NOT NULL AND tail != "" '
        'GROUP BY tail ORDER BY COUNT(*) DESC LIMIT 200')]
    v['scene'] = [r[0] for r in conn.execute(
        'SELECT scene FROM poems WHERE scene IS NOT NULL AND scene != "" GROUP BY scene')]
    v['pz'] = [r[0] for r in conn.execute(
        'SELECT pz FROM lines WHERE pz IS NOT NULL AND LENGTH(pz) IN (5,6,7) '
        'AND pz NOT LIKE "%?%" GROUP BY pz ORDER BY COUNT(*) DESC LIMIT 200')]
    return v


def dyn_w(d, long_form=False):
    return '元曲' if d == '元' else ((d + '代') if long_form else d)


# ================================================================ 句级谓词 → SQL
def lp_sql(kind, p):
    if kind == '句脚字':
        return 'tail = ?', [p['tail']]
    if kind == '句脚平仄':
        return 'substr(pz, -1, 1) = ?', [p['tone']]
    if kind == '平仄串包含':
        return 'pz LIKE ?', ['%' + p['pz'] + '%']
    if kind == '平仄串全等':
        return 'pz = ?', [p['pz']]
    if kind == '句长区间':
        return '(han_len >= ? AND han_len <= ?)', [p['lo'], p['hi']]
    return '(idx % 2) = ?', [p['parity']]


def lp_not_sql(kind, p):
    if kind == '句脚字':
        return '(tail IS NULL OR tail <> ?)', [p['tail']]
    if kind == '句脚平仄':
        return '(pz IS NULL OR substr(pz, -1, 1) <> ?)', [p['tone']]
    if kind == '平仄串包含':
        return '(pz IS NULL OR pz NOT LIKE ?)', ['%' + p['pz'] + '%']
    if kind == '平仄串全等':
        return '(pz IS NULL OR pz <> ?)', [p['pz']]
    if kind == '句长区间':
        return '(han_len IS NULL OR han_len < ? OR han_len > ?)', [p['lo'], p['hi']]
    return '(idx IS NULL OR (idx % 2) <> ?)', [p['parity']]


def lp_text(rng, kind, p):
    if kind == '句脚字':
        return rng.choice(['句脚是「%s」' % p['tail'], '句脚为「%s」' % p['tail'],
                           '句末字是%s' % p['tail'], '结尾字为%s' % p['tail']])
    if kind == '句脚平仄':
        return rng.choice(['句脚为%s' % p['tone'], '句末字读%s声' % p['tone'],
                           '句脚平仄是%s' % p['tone']])
    if kind == '平仄串包含':
        return rng.choice(['声律模式是「%s」' % p['pz'], '平仄串为%s' % p['pz']])
    if kind == '平仄串全等':
        return '整句平仄串正好是「%s」' % p['pz']
    if kind == '句长区间':
        return '句长在%s到%s字之间' % (zh(p['lo']), zh(p['hi']))
    return '%s句位上' % ('奇数' if p['parity'] == 0 else '偶数')


# ================================================================ 篇级筛选 → SQL
def pf_sql(kind, p):
    if kind == '元数据':
        w, a = [], []
        for key in ('dynasty', 'author', 'cipai'):
            if p.get(key):
                w.append('p.%s IN (%s)' % (key, ','.join('?' * len(p[key]))))
                a.extend(p[key])
        return w, a
    if kind == '声情':
        return ['p.scene = ?'], [p['scene']]
    if kind == '篇级指标区间':
        w, a = [], []
        for k, col, op in (('ze_min', 'ze_ratio', '>='), ('ze_max', 'ze_ratio', '<='),
                           ('len_min', 'han_len', '>='), ('len_max', 'han_len', '<='),
                           ('sent_min', 'sent_n', '>='), ('sent_max', 'sent_n', '<=')):
            if k in (p.get('rng') or {}):
                w.append('p.%s %s ?' % (col, op))
                a.append(p['rng'][k])
        return w, a
    if kind == '派生量':
        return ['ABS(p.change) >= ?'], [p['dchg']]
    if kind == '一致性':
        if p['scene'] == '后段上升':
            return ['p.scene = ? AND p.change < 0'], [p['scene']]
        if p['scene'] == '后段下降':
            return ['p.scene = ? AND p.change > 0'], [p['scene']]
        return ['p.scene = ? AND ABS(p.change) < 1'], [p['scene']]
    return [], []


def pf_text(rng, kind, p):
    if kind == '元数据':
        return ''.join('／'.join(p.get(k) or []) for k in ('dynasty', 'author', 'cipai'))
    if kind == '声情':
        return rng.choice(SCENE_PHRASE.get(p['scene'], [p['scene']]))
    if kind == '篇级指标区间':
        r = p.get('rng') or {}
        parts = []
        if 'ze_min' in r:
            parts.append('仄声比例高于%s%%' % zh(r['ze_min']))
        if 'len_min' in r and 'len_max' in r:
            parts.append('字数在%s到%s之间' % (zh(r['len_min']), zh(r['len_max'])))
        elif 'len_max' in r:
            parts.append('字数不到%s' % zh(r['len_max']))
        if 'sent_min' in r and 'sent_max' in r:
            parts.append('%s到%s句之间' % (zh(r['sent_min']), zh(r['sent_max'])))
        elif 'sent_min' in r:
            parts.append('句数在%s以上' % zh(r['sent_min']))
        return '、'.join(parts) or '篇幅适中'
    if kind == '派生量':
        return '前后段变化幅度不小于%s' % zh(p['dchg'])
    if kind == '一致性':
        return '声情标注为%s但实测前后段相反' % p['scene']
    return ''


def qtok(rng, lq, ltxt, p):
    """句级量词 → 人话。**惰性取分支**（旧版一次性建字典 → KeyError）。"""
    if lq == '∃':
        return '至少有一句%s' % ltxt
    if lq == '∀':
        return '每一句都%s' % ltxt
    if lq == '∄':
        return '没有任何一句%s' % ltxt
    if lq == '≥k':
        return '有%s句以上%s' % (zh(p['k']), ltxt)
    if lq == '=k':
        return '正好有%s句%s' % (zh(p['k']), ltxt)
    if lq == '占比≥p':
        return '满足「%s」的句子占比不低于%s%%' % (ltxt, zh(round(p['ratio'] * 100)))
    return '满足「%s」的句子数在%s到%s句之间' % (ltxt, zh(p['ka']), zh(p['kb']))


# ================================================================ 范围 → WHERE（真值单一来源）
def scope_where(sig, p):
    lq, lp, pf, so, _out = sig
    w, a = [], []
    pw, pa = pf_sql(pf, p)
    w += pw
    a += pa
    # ⚠ 2026-10-03 修：并集/交集原本只写在 `∃` 分支里 → 用 ∄/∀/≥k/=k/占比/条数 的题
    #   会**漏掉第二个取值**，真值因此比引擎**宽**，把本来正确的引擎判成错（出现一批假失败）。
    #   现在统一处理：并集并入同一谓词；交集是所有量词下都要加的**额外存在性**要求。
    pexpr, pargs = lp_sql(lp, p)
    t2 = p.get('tail2')
    if so == '并集' and t2 and lp == '句脚字':
        pexpr, pargs = 'tail IN (?, ?)', [p['tail'], t2]
    if lq == '∃':
        w.append('p.pid IN (SELECT pid FROM lines WHERE %s)' % pexpr)
        a += pargs
    elif lq == '∀':
        # ⚠ 2026-10-03 修：∀ 原先走 `lp_not_sql`，**绕过了并集**——「每一句都句脚为「人」**或**
        #   句脚为「笑」」的真值只算 `tail <> '人'`，把「笑」的那几篇漏掉（真值 10、引擎 11；
        #   实测 Q0790/Q0770）。∀ 的语义是「**没有任何一句落在这组取值之外**」，
        #   所以并集必须一起进否定式。
        if so == '并集' and t2 and lp == '句脚字':
            nexpr, nargs = '(tail IS NULL OR tail NOT IN (?, ?))', [p['tail'], t2]
        else:
            nexpr, nargs = lp_not_sql(lp, p)
        w.append('p.pid NOT IN (SELECT pid FROM lines WHERE %s)' % nexpr)
        a += nargs
        w.append('p.pid IN (SELECT pid FROM lines)')
    elif lq == '∄':
        w.append('p.pid NOT IN (SELECT pid FROM lines WHERE %s)' % pexpr)
        a += pargs
    elif lq == '≥k':
        w.append('p.pid IN (SELECT pid FROM lines WHERE %s GROUP BY pid HAVING COUNT(*) >= ?)'
                 % pexpr)
        a += pargs + [p['k']]
    elif lq == '=k':
        w.append('p.pid IN (SELECT pid FROM lines WHERE %s GROUP BY pid HAVING COUNT(*) = ?)'
                 % pexpr)
        a += pargs + [p['k']]
    elif lq == '占比≥p':
        w.append('p.pid IN (SELECT pid FROM lines GROUP BY pid HAVING '
                 'SUM(CASE WHEN %s THEN 1 ELSE 0 END) * 1.0 / COUNT(*) >= ?)' % pexpr)
        a += pargs + [p['ratio']]
    elif lq == '条数∈[a,b]':
        w.append('p.pid IN (SELECT pid FROM lines WHERE %s GROUP BY pid HAVING '
                 'COUNT(*) BETWEEN ? AND ?)' % pexpr)
        a += pargs + [p['ka'], p['kb']]
    if so == '交集' and t2:                     # 「且另有至少一句句脚为 B」——任何量词下都成立
        w.append('p.pid IN (SELECT pid FROM lines WHERE tail = ?)')
        a.append(t2)
    return (' AND '.join(w) or '1=1'), a


def count_hits(conn, sig, p):
    w, a = scope_where(sig, p)
    return conn.execute('SELECT COUNT(*) FROM poems p WHERE ' + w, a).fetchone()[0]


# ================================================================ 输出算子真值
METRIC = ['ze_ratio', 'ping_ratio', 'han_len', 'sent_n', 'longest_len', 'change']

def truth_field(conn, pid, field):
    """取某篇的某字段（极值再取字段用）。"""
    row = conn.execute('SELECT %s FROM poems WHERE pid = ?' % field, (pid,)).fetchone()
    return row[0] if row else None


def group_value(rec, metric):
    """分组统计记录 → 指定指标值（与 out_groups 的口径一致）。

    ⚠ `out_groups` 对 metric='count' 返回的是**裸 float**，不是字典 —— 旧版这里按字典取键，
    直接 `TypeError: 'float' object is not subscriptable`（审计里 162 条假 E_CRASH 的根因）。
    """
    if isinstance(rec, (int, float)):
        return float(rec)
    return {'ze_ratio': rec['weighted'], 'ping_ratio': 100.0 - rec['weighted'],
            'han_len': rec['han_len'], 'sent_n': rec['sent_n'],
            'count': float(rec['n']), 'share': float(rec['n'])}[metric]


GROUP_COL = {'author': 'author', 'cipai': 'cipai', 'dynasty': 'dynasty'}


def _expr(metric):
    if metric == 'ping_ratio':
        return '(100.0 - p.ze_ratio)'
    if metric == 'change':
        return 'ABS(p.change)'
    return 'p.%s' % metric


def out_order(conn, sig, p):
    w, a = scope_where(sig, p)
    o = 'DESC' if p['dir'] == 'max' else 'ASC'
    n = p.get('rank', 1)
    rows = conn.execute('SELECT p.pid, %s v FROM poems p WHERE %s ORDER BY v %s, p.pid LIMIT ?'
                        % (_expr(p['metric']), w, o), a + [n]).fetchall()
    return rows[n - 1] if len(rows) >= n else None


def out_groups(conn, sig, p, gb, metric, agg='weighted'):
    col = GROUP_COL[gb]
    w, a = scope_where(sig, p)
    rec = {}
    for g, n, ze, hl, m_, sn in conn.execute(
            'SELECT %s g, COUNT(*) n, SUM(ze) ze, SUM(han_len) hl, AVG(ze_ratio) m, SUM(sent_n) sn '
            'FROM poems p WHERE %s AND %s IS NOT NULL AND %s != "" GROUP BY %s'
            % (col, w, col, col, col), a):
        rec[g] = {'n': n, 'weighted': (100.0 * ze / hl) if hl else 0.0, 'mean': m_ or 0.0,
                  'han_len': (hl / n) if n else 0.0, 'sent_n': (sn / n) if n else 0.0}
    if agg == 'stdev':
        xs = defaultdict(list)
        for g, v in conn.execute('SELECT %s g, %s v FROM poems p WHERE %s AND %s IS NOT NULL '
                                 'AND %s != ""' % (col, _expr(metric), w, col, col), a):
            xs[g].append(v)
        out = {}
        for g, vs in xs.items():
            if len(vs) >= 3:
                mu = sum(vs) / len(vs)
                out[g] = (sum((x - mu) ** 2 for x in vs) / (len(vs) - 1)) ** 0.5
        return out
    if metric == 'count':
        return {g: float(r['n']) for g, r in rec.items()}
    if metric == 'ze_ratio':
        return {g: (r['weighted'] if agg == 'weighted' else r['mean']) for g, r in rec.items()}
    if metric == 'ping_ratio':
        return {g: (100.0 - r['weighted'] if agg == 'weighted' else 100.0 - r['mean'])
                for g, r in rec.items()}
    return {g: r[metric] for g, r in rec.items()}


def out_median(conn, sig, p, metric):
    w, a = scope_where(sig, p)
    xs = sorted(r[0] for r in conn.execute(
        'SELECT %s FROM poems p WHERE %s' % (_expr(metric), w), a))
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def out_mode(conn, sig, p, metric):
    w, a = scope_where(sig, p)
    c = Counter(round(r[0], 1) for r in conn.execute(
        'SELECT %s FROM poems p WHERE %s' % (_expr(metric), w), a))
    if not c:
        return None
    top = max(c.values())
    return sorted(k for k, v in c.items() if v == top)[0], top


def out_pair(conn, sig, p):
    """配对：**一条 SQL** 完成（旧版逐篇相关子查询 → 慢到分钟级）。"""
    w, a = scope_where(sig, p)
    rows = conn.execute(
        'SELECT k, COUNT(*) c FROM (SELECT l.pid AS pid, GROUP_CONCAT(l.pz, "|") AS k '
        'FROM lines l JOIN poems p ON p.pid = l.pid WHERE %s GROUP BY l.pid) '
        'GROUP BY k HAVING c >= 2' % w, a).fetchall()
    return len(rows), sum(c * (c - 1) // 2 for _k, c in rows)


def out_cond_share(conn, sigA, pA, sigB, pB):
    """条件概率：问句是「**在 A 当中**，有多大比例同时也满足 B」→ 分母 = |A|。

    ⚠ 2026-10-02 修：旧版分母写成 |B|（与问句措辞不符，属真值口径自身错误）。
    """
    wa, aa = scope_where(sigA, pA)
    a_n = conn.execute('SELECT COUNT(*) FROM poems p WHERE ' + wa, aa).fetchone()[0]
    if not a_n:
        return None
    wb, ab = scope_where(sigB, pB)
    inter = conn.execute('SELECT COUNT(*) FROM poems p WHERE (%s) AND (%s)' % (wa, wb),
                         aa + ab).fetchone()[0]
    return inter / a_n


# ================================================================ 参数
OUT_PARAMS = {
    '极值': lambda rng: {'metric': rng.choice(METRIC), 'dir': rng.choice(['max', 'min'])},
    '极值再取字段': lambda rng: {'metric': rng.choice(['ze_ratio', 'han_len', 'sent_n']),
                          'dir': rng.choice(['max', 'min']),
                          'then_field': rng.choice(['cipai', 'author', 'sent_n', 'han_len'])},
    '第N名': lambda rng: {'metric': rng.choice(['han_len', 'sent_n', 'ze_ratio']),
                       'dir': rng.choice(['max', 'min']), 'rank': rng.choice([2, 3])},
    '分组极值': lambda rng: {'gb': rng.choice(['author', 'cipai', 'dynasty']),
                        'metric': rng.choice(['count', 'count', 'ze_ratio', 'han_len']),
                        'ext': rng.choice(['max', 'min'])},
    '二组比较': lambda rng: {'gb': rng.choice(['author', 'cipai', 'dynasty']),
                        'metric': rng.choice(['ze_ratio', 'han_len', 'sent_n', 'count'])},
    '三组比较': lambda rng: {'gb': 'dynasty', 'metric': rng.choice(['ze_ratio', 'han_len', 'count'])},
    '离散度最大组': lambda rng: {'gb': rng.choice(['author', 'cipai']),
                          'metric': rng.choice(['han_len', 'sent_n', 'ze_ratio'])},
    '中位数': lambda rng: {'metric': rng.choice(['han_len', 'sent_n', 'ze_ratio'])},
    '众数': lambda rng: {'metric': rng.choice(['sent_n', 'han_len'])},
}


def _out_params(out, rng):
    return OUT_PARAMS.get(out, lambda r: {})(rng)


def mk_params(rng, v, lq, lp, pf, so, out):
    p = {}
    if lp == '句脚字':
        p['tail'] = rng.choice(v['tail'])
        if so in ('并集', '交集'):
            p['tail2'] = rng.choice([t for t in v['tail'] if t != p['tail']])
    elif lp == '句脚平仄':
        p['tone'] = rng.choice(['平', '仄'])
    elif lp in ('平仄串包含', '平仄串全等'):
        p['pz'] = rng.choice(v['pz'])
    elif lp == '句长区间':
        lo = rng.randint(3, 8)
        p['lo'], p['hi'] = lo, lo + rng.randint(2, 6)
    else:
        p['parity'] = rng.choice([0, 1])
    if lq == '≥k':
        p['k'] = rng.choice([2, 3, 4])
    elif lq == '=k':
        p['k'] = rng.choice([1, 2, 3])
    elif lq == '占比≥p':
        p['ratio'] = rng.choice([0.3, 0.5, 0.7])
    elif lq == '条数∈[a,b]':
        a0 = rng.randint(1, 3)
        p['ka'], p['kb'] = a0, a0 + rng.randint(1, 4)
    if pf == '元数据':
        pick = rng.sample(['dynasty', 'author', 'cipai'], rng.choice([1, 1, 2]))
        for k in pick:
            if k == 'dynasty':
                p[k] = [rng.choice(v['dyn'][:3])]
            elif k == 'author':
                p[k] = [rng.choice(v['author'])]
            else:
                p[k] = [rng.choice(v['cipai'])]
    elif pf == '声情':
        p['scene'] = rng.choice(v['scene'])
    elif pf == '篇级指标区间':
        kind = rng.choice(['len', 'sent', 'ze'])
        if kind == 'len':
            a0 = rng.randint(15, 45)
            p['rng'] = {'len_min': float(a0), 'len_max': float(a0 + rng.randint(20, 120))}
        elif kind == 'sent':
            a0 = rng.randint(2, 6)
            p['rng'] = {'sent_min': float(a0), 'sent_max': float(a0 + rng.randint(2, 8))}
        else:
            p['rng'] = {'ze_min': float(rng.choice([30, 40, 45, 50, 55, 60]))}
    elif pf == '派生量':
        p['dchg'] = float(rng.choice([5, 10, 15, 20]))
    elif pf == '一致性':
        p['scene'] = rng.choice(v['scene'])
    p.update(_out_params(out, rng))
    return p


def mk_second(conn, sig, p, v):
    """造第二个范围：**必须与第一个真不同**（否则「多几篇」恒为 0，是退化题）。"""
    lq, lp, pf, so, out = sig
    base = scope_where(sig, p)
    for _ in range(15):
        q = dict(p)
        if pf == '声情':
            alts = [s for s in v['scene'] if s != p.get('scene')]
            if not alts:
                return None
            q['scene'] = rng_global.choice(alts)
        elif pf == '元数据' and p.get('dynasty'):
            alts = [d for d in v['dyn'][:3] if d != p['dynasty'][0]]
            q['dynasty'] = [rng_global.choice(alts)]
        elif pf == '一致性':
            alts = [s for s in v['scene'] if s != p.get('scene')]
            if not alts:
                return None
            q['scene'] = rng_global.choice(alts)
        elif pf == '篇级指标区间':
            r = dict(p.get('rng') or {})
            if 'len_max' in r:
                r['len_max'] = max(float(r.get('len_min', 5)) + 3, r['len_max'] - 15)
            elif 'sent_max' in r:
                r['sent_max'] = max(float(r.get('sent_min', 2)) + 1, r['sent_max'] - 2)
            elif 'ze_min' in r:
                r['ze_min'] = max(5.0, r['ze_min'] - 10)
            q['rng'] = r
        elif lp == '句脚字' and 'tail' in p:
            q['tail'] = rng_global.choice([t for t in v['tail'] if t != p['tail']])
        elif lp == '句脚平仄' and 'tone' in p:
            q['tone'] = '仄' if p['tone'] == '平' else '平'
        elif lp == '平仄串包含' and 'pz' in p:
            q['pz'] = rng_global.choice([z for z in v['pz'] if z != p['pz']])
        elif lp == '句长区间' and 'lo' in p:
            q['lo'], q['hi'] = p['lo'] + 1, p['hi'] + 1
        elif lp == '句位奇偶' and 'parity' in p:
            q['parity'] = 1 - p['parity']
        elif pf == '派生量':
            q['dchg'] = p['dchg'] + 5
        else:
            return None
        q = {k: val for k, val in q.items() if not k.startswith('_')}
        try:
            if scope_where(sig, q) == base:      # 两范围必须真不同
                continue
            if count_hits(conn, sig, q) >= 2:
                return q
        except Exception:
            return None
    return None


# ================================================================ 可行性 + 出题
def feasible(conn, sig, p, v):
    lq, lp, pf, so, out = sig
    if out == '配对' and lq != '∃':
        return False
    if out == '最相近篇':
        return False        # v3.0 暂不出（专属问法/真值口径未定型），避免退化成配对题文案
    n = count_hits(conn, sig, p)
    if out == '配对':
        if n < 8 or n > 3000:
            return False
        g, pr = out_pair(conn, sig, p)
        return g >= 1 and pr >= 1
    if n < 2 or n > 8000:
        return False
    if out in ('极值', '极值再取字段', '第N名'):
        w, a = scope_where(sig, p)
        if conn.execute('SELECT COUNT(DISTINCT %s) FROM poems p WHERE %s'
                        % (_expr(p['metric']), w), a).fetchone()[0] < 3:
            return False
        return not (out == '第N名' and n < 4)
    if out in ('分组极值', '离散度最大组'):
        gb = p.get('gb', 'author')
        col = GROUP_COL[gb]
        w, a = scope_where(sig, p)
        ng = conn.execute('SELECT COUNT(*) FROM (SELECT %s FROM poems p WHERE %s AND %s IS NOT NULL '
                          'AND %s != "" GROUP BY %s HAVING COUNT(*) >= 3)'
                          % (col, w, col, col, col), a).fetchone()[0]
        if ng < 3:
            return False
        if out == '离散度最大组':
            d = out_groups(conn, sig, p, gb, p['metric'], agg='stdev')
            return len({round(x, 3) for x in d.values()}) >= 2
        return True
    if out in ('二组比较', '三组比较'):
        col = GROUP_COL[p['gb']]
        w, a = scope_where(sig, p)
        vals = [r[0] for r in conn.execute(
            'SELECT %s FROM poems p WHERE %s AND %s IS NOT NULL AND %s != "" GROUP BY %s '
            'HAVING COUNT(*) >= 4 ORDER BY COUNT(*) DESC LIMIT 30' % (col, w, col, col, col), a)]
        if len(vals) < (3 if out == '三组比较' else 2):
            return False
        p['_vals'] = vals[:3] if out == '三组比较' else vals[:2]
        return True
    if out in ('两范围计数差', '条件概率'):
        q2 = mk_second(conn, sig, p, v)
        if q2 is None:
            return False
        p['_p2'] = q2
        return True
    return True


def build_question(conn, sig, p, v, rng):
    lq, lp, pf, so, out = sig
    ltxt = lp_text(rng, lp, p)
    ptxt = pf_text(rng, pf, p)
    cond = qtok(rng, lq, ltxt, p)
    if so == '并集' and p.get('tail2'):
        cond += '或句脚为「%s」' % p['tail2']
    if so == '交集' and p.get('tail2'):
        cond += '，且另有至少一句句脚为「%s」' % p['tail2']
    scope = '，'.join(x for x in (ptxt, cond) if x)
    if out == '计数':
        return '%s%s的作品%s' % (lead(rng), scope,
                              rng.choice(['有多少篇？', '共几篇？', '总数是多少？', '篇数是多少？',
                                          '算一下有几篇？'])), 'count'
    if out == '列举':
        return '%s%s的作品%s' % (lead(rng), scope,
                              rng.choice(['有哪些？', '给我列一下', '都是哪些？', '分别是哪些？',
                                          '有哪些篇目？'])), 'list'
    if out in ('极值', '极值再取字段', '第N名'):
        mt = {'ze_ratio': '仄声比例', 'ping_ratio': '平声比例', 'han_len': '全篇字数',
              'sent_n': '句数', 'longest_len': '最长句长度', 'change': '前后段变化幅度'}[p['metric']]
        if out == '极值':
            return '%s%s的作品里，%s%s的是哪一篇？' % (
                lead(rng), scope, mt, '最高' if p['dir'] == 'max' else '最低'), 'extreme'
        if out == '极值再取字段':
            fn = {'cipai': '词牌', 'author': '词人', 'sent_n': '句数', 'han_len': '字数'}[p['then_field']]
            return '%s%s的作品里，%s%s的那一篇，它的%s是多少？' % (
                lead(rng), scope, mt, '最高' if p['dir'] == 'max' else '最低', fn), 'extreme_field'
        return '%s%s的作品里，%s第%s%s的是哪一篇？' % (
            lead(rng), scope, mt, zh(p['rank']), '高' if p['dir'] == 'max' else '低'), 'rank'
    if out == '分组极值':
        gname = {'author': '词人', 'cipai': '词牌', 'dynasty': '朝代'}[p['gb']]
        return '%s在%s的作品里，哪一个%s的%s%s？' % (
            lead(rng), scope, gname,
            {'count': '作品数', 'ze_ratio': '仄声比例', 'han_len': '平均篇幅'}[p['metric']],
            '最多' if p['ext'] == 'max' else '最少'), 'agg_top'
    if out == '离散度最大组':
        gname = {'author': '词人', 'cipai': '词牌'}[p['gb']]
        return '%s在%s的作品里，哪一个%s的%s波动最大？' % (
            lead(rng), scope, gname,
            {'han_len': '篇幅', 'sent_n': '句数', 'ze_ratio': '仄声比例'}[p['metric']]), 'disp'
    if out in ('二组比较', '三组比较'):
        ml = {'ze_ratio': '仄声比例', 'han_len': '平均篇幅', 'sent_n': '平均句数',
              'count': '作品数'}[p['metric']]
        if out == '三组比较':
            return '%s在%s的作品里，清／宋／元三者当中，哪一个朝代的%s最高？' % (
                lead(rng), scope, ml), 'cmp'
        return '%s在%s的作品里，%s与%s相比，哪一组的%s更高？' % (
            lead(rng), scope, p['_vals'][0], p['_vals'][1], ml), 'cmp'
    if out == '占比':
        return '%s%s的作品，占全部清词（或所限朝代）的百分之几？' % (lead(rng), scope), 'share'
    if out == '中位数':
        return '%s%s的作品，其%s的中位数是多少？' % (
            lead(rng), scope,
            {'han_len': '全篇字数', 'sent_n': '句数', 'ze_ratio': '仄声比例'}[p['metric']]), 'median'
    if out == '众数':
        return '%s%s的作品，%s最常出现的取值是几？' % (
            lead(rng), scope, {'sent_n': '句数', 'han_len': '全篇字数'}[p['metric']]), 'mode'
    if out == '两范围计数差':
        q2 = scope_of_second(rng, sig, p['_p2'])
        return '%s%s的作品，比「%s」的作品多几篇？' % (lead(rng), scope, q2), 'diff'
    if out == '条件概率':
        q2 = scope_of_second(rng, sig, p['_p2'])
        return '%s在%s的作品当中，有多大比例同时也满足「%s」？' % (lead(rng), scope, q2), 'condshare'
    return '%s%s的作品中，找出几对每个位置上的字平仄都相同的两首词？' % (lead(rng), scope), 'pair'


def scope_of_second(rng, sig, p2):
    lq, lp, pf, so, out = sig
    ltxt = lp_text(rng, lp, p2)
    return '，'.join(x for x in (pf_text(rng, pf, p2), qtok(rng, lq, ltxt, p2)) if x)


# ================================================================ 主流程
rng_global = random.Random(0)
POLITE_RE = re.compile(r'(麻烦|请帮我|帮我|我想找|劳驾|请问|问一下|查一下|想看看|请统计|给我个结果|帮我算算)')


def norm_key(q):
    return POLITE_RE.sub('', re.sub(r'[\s，。？、（）()「」“”%？＝*｜]', '', q))


def bigr(q):
    s = norm_key(q)
    return set(s[i:i + 2] for i in range(len(s) - 1))


def jac(a, b):
    i = len(a & b)
    return (i / len(a | b)) if i else 0.0


def main():
    global rng_global
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=20261003)
    ap.add_argument('--n', type=int, default=1000)
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', 'questions_1000.jsonl'))
    ap.add_argument('--max-sim', type=float, default=0.80)
    ap.add_argument('--max-try', type=int, default=11000)
    ap.add_argument('--shard', type=int, default=0, help='分片号（0 起）')
    ap.add_argument('--shards', type=int, default=1, help='分片总数（>1 即并行跑）')
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rng_global = rng
    # 只读打开：多个分片并行读同一个库不互相加锁（写锁才是并发杀手）
    conn = sqlite3.connect('file:%s?mode=ro' % args.db.replace('\\', '/'), uri=True)
    v = load_vocab(conn)

    combos = list(itertools.product(LQ, LP, PF, SO, OUT))
    # ⚠ 假多样性拦截：SO（并集/交集）只在**谓词是句脚字**时才有文本效果；
    #   对「句长区间/平仄串…」等谓词它是**空操作** → 交集/并集/无 三个签名会生成同一道题
    #   （只差一个参数），按「抽象掉参数看操作链」的判据就是换汤不换药。直接剪掉。
    combos = [c for c in combos if c[3] == '无' or c[1] == '句脚字']
    rng.shuffle(combos)
    # ⚠ 便宜量词优先：∃/∀/∄ 是单趟子查询；占比≥p / 条数∈[a,b] 要按篇 GROUP BY（秒级）。
    #   不排序的话，随机顺序会频繁撞上秒级组合，1000 题要跑几小时。稳定排序 → 组内顺序仍随机。
    combos.sort(key=lambda t: 0 if t[0] in ('∃', '∀', '∄') else 1)
    if args.shards > 1:                     # 按分片切分组合空间（切片不相交 → 签名天然不重复）
        combos = combos[args.shard::args.shards]
    sys.stderr.write('分片 %d/%d：本片组合 %d，目标 %d 条不同的链……\n'
                     % (args.shard, args.shards, len(combos), args.n))
    rows, pref, bags, tried = [], {}, [], 0
    for sig in combos:
        if len(rows) >= args.n or tried >= args.max_try:
            break
        tried += 1
        if tried % 200 == 0:
            sys.stderr.write('  … 已试 %d / 已收 %d\n' % (tried, len(rows)))
            sys.stderr.flush()
        att = 4 if sig[0] in ('∃', '∀', '∄') else 1
        for _ in range(att):
            try:
                p = mk_params(rng, v, *sig)
                if not feasible(conn, sig, p, v):
                    continue
                q, task = build_question(conn, sig, p, v, rng)
            except Exception:
                continue
            nk = norm_key(q)
            if len(nk) < 10 or pref.get(nk[:4], 0) >= 3:
                continue
            bg = bigr(q)
            if any(jac(bg, x) >= args.max_sim for x in bags):
                continue
            pref[nk[:4]] = pref.get(nk[:4], 0) + 1
            bags.append(bg)
            rows.append({'id': 'Q%04d' % (len(rows) + 1), 'sig': '｜'.join(sig),
                         'task': task, 'q': q,
                         'spec': {k: val for k, val in p.items() if not k.startswith('_')},
                         'intent': {k: val for k, val in p.items() if k.startswith('_')},
                         'ability': 'supported'})
            break

    sigs = [r['sig'] for r in rows]
    assert len(set(sigs)) == len(sigs), '签名必须唯一！'
    with open(args.out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('已生成 %d 题 → %s（试了 %d 个组合）' % (len(rows), args.out, tried))
    print('  **链（签名）数 = %d / 题数 %d**' % (len(set(sigs)), len(rows)))
    for k, c in Counter(s.split('｜')[4] for s in sigs).most_common():
        print('   OUT=%-6s %d' % (k, c))


if __name__ == '__main__':
    main()
