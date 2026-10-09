# -*- coding: utf-8 -*-
"""pairing.py —— M8b 配对题：找出「全篇逐位平仄完全相同」的两首词（声律谱相同的对子）。

为什么需要单独一层：问句「找出几对每个位置上的字平仄都相同的两首词」不是**筛篇**，
而是**在篇与篇之间做配对**——旧版把它当普通条件题，大模型甚至从问句本身捏出一条
「声律模式=平仄平仄平仄平仄」，于是拿最严条件去筛，答案完全离谱（2026-09-30 主人实测）。
配对的判定量是**全篇平仄串**（把该篇每一句的平仄串按句序接起来），
两篇的串**逐位相同**即为一对（串相同自然意味着句数与字数相同）。

纪律：
  · 只认**两段都命中**的问法——要有「配对」框架词（几对／两首／成对…）＋「相同」词
    ＋**明确的维度词**（平仄／声律／声调）。少一段就不认（**不猜**）。
  · 只实现「逐位**平仄**相同」这一维；若问句说的是「字面／用字／原文相同」，
    认出来但**如实说明本系统不提供**（绝不拿平仄冒充字面）。
  · 所有计数都给出**第二条独立路径**（Python 侧重算）复核（`audit`）。
"""
import argparse
import copy
import os
import re
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import retrieve                                              # noqa: E402

# 配对框架词：问句在「找对子」，不是在「筛篇」
PAIR_FRAME = ('几对', '一对', '一对对', '成对', '配对', '两首', '两阕', '两篇', '双璧', '对子')
# 「相同」词
PAIR_EQ = ('都相同', '完全相同', '均相同', '全都相同', '全相同', '一模一样',
           '一样', '一致', '相同')
# 维度：平仄（可实现）／字面（不可实现，要如实说明）
PAIR_DIM = (('tone', ('平仄', '声律', '声调', '音律', '平仄谱', '声谱')),
            ('text', ('字面', '用字', '原文', '字句', '字词', '每个位置上的字', '每个位置的字',
                      '字都相同', '字都一致', '每字都')))
FRAME_STRIP = ('找出', '找', '请给出', '请找', '给我', '几对', '一对', '成对', '配对',
               '每个位置上的字', '每个位置上的', '每一个位置上的字', '每一个位置上的',
               '每个位置', '每个字', '各位', '两首词', '两阕词', '两篇词', '两首', '两阕',
               '两篇', '双璧', '对子', '词', '的都相同', '都相同', '完全相同', '均相同',
               '一样', '一致', '相同', '平仄', '声律', '声调', '音律')

_PAIR_RESULT_CACHE = {}
_AUDIT_CACHE = {}
_AUDIT_SIGS_CACHE = {}

_SIG_SUB = ('(SELECT group_concat(x.pz, \'\') FROM '
            '(SELECT pz FROM lines WHERE lines.pid = p.pid ORDER BY idx) x)')


def parse_pair(conn, text):
    """问句 → 配对题判定。认不出（缺框架词/缺维度词）返回 None，**不猜**。"""
    if not any(w in text for w in PAIR_FRAME):
        return None
    if not any(w in text for w in PAIR_EQ):
        return None
    dims = [name for name, kws in PAIR_DIM if any(k in text for k in kws)]
    if not dims:
        return None
    if 'tone' in dims:
        dims = ['tone']            #「每个位置上的字平仄都相同」说的是平仄，不是字面
    return {'dims': tuple(dims), 'n_frame': len([1 for w in PAIR_FRAME if w in text])}


def clean_text(text):
    """把配对框架词摘掉，剩下的才交给通用解析器（避免「几对…两首词」变成词面条件）。"""
    rest = text
    for w in sorted(FRAME_STRIP, key=len, reverse=True):
        rest = rest.replace(w, ' ')
    return re.sub(r'\s+', ' ', rest).strip()


def _scope_sql(spec):
    """配对题的范围条件（复用引擎唯一的一份条件 SQL）。"""
    return retrieve._sql(spec)


def find_pairs(conn, spec, limit=3, per_group=2, min_len=6):
    """在满足条件的篇目里按「全篇平仄串」分组，取前 `limit` 组，每组给 `per_group` 篇。

    组内优先挑**不同词人**的两篇（更有对照价值），不足时再按 pid 补。
    `min_len`：举例时跳过**谱长不足 min_len 位的残篇组**（元曲零句、失调名碎片等）——
    这类「两个字都平」也算一对，拿它举例毫无信息量；但**照样计入总数**并如实披露跳过几个。

    性能：把「范围条件 + 全篇平仄串」**物化一次**进临时表，后续 10 条聚合/取样都读它。
    原实现把同一段 `WITH s AS (…含逐篇 group_concat 相关子查询…)` 抄了 10 遍，
    SQLite 会把 CTE 内联，于是全库范围下那 5.9 万次相关子查询被重算 10 遍（实测 4.72 秒）。
    """
    where, args = _scope_sql(spec)
    # 结果缓存：同一连接、同一范围/参数、且库未改动时，第二次调用直接返回上次结果
    # （自检与问答会对同一道配对题多次调用；实测第二次调用白花 0.9 秒）
    _key = (conn, where, tuple(args), limit, per_group, min_len, conn.total_changes)
    _hit = _PAIR_RESULT_CACHE.get(_key)
    if _hit is not None:
        return copy.deepcopy(_hit)
    _COLS = ('p.pid, p.dynasty, p.author, p.cipai, p.title, p.sent_n, p.han_len, '
             'p.ze_ratio, p.scene')
    base = ('SELECT %s, %s AS sig FROM poems p WHERE %s' % (_COLS, _SIG_SUB, where))

    # 物化：临时表列序与 base 完全一致（下游按 r[0]..r[9] 取值，不能变）
    materialized = False
    try:
        conn.execute('DROP TABLE IF EXISTS _pair_scope')
        conn.execute('CREATE TEMP TABLE _pair_scope AS ' + base, args)
        materialized = True
    except sqlite3.Error:                 # 只读库等异常场景 → 回退到原 CTE 写法（语义相同）
        materialized = False

    if materialized:
        # ① 按「全篇平仄串」单独分组：组数／对数／覆盖篇数／短谱组数／Top 组
        #    （原来是 5 条各自 GROUP BY 的 SQL，此处一次分组后在 Python 侧汇总）
        _rows = conn.execute(
            "SELECT sig, COUNT(1) n, MIN(sent_n) mn, LENGTH(sig) L FROM _pair_scope "
            "WHERE sig IS NOT NULL AND sig <> '' GROUP BY sig").fetchall()
        n_groups = n_pairs = n_covered = n_short = 0
        _cands = []
        for _sig, _n, _mn, _L in _rows:
            if _n < 2:
                continue
            n_groups += 1
            n_pairs += _n * (_n - 1) // 2
            n_covered += _n
            if _L < min_len:
                n_short += 1
            else:
                _cands.append((_n, _mn, _L, _sig))
        # 与原 SQL 的 ORDER BY n DESC, mn DESC, LENGTH(sig) DESC, sig 等价
        # （SQLite 默认 BINARY 排序＝按 UTF-8 字节序，与 Python 码位序一致）
        _cands.sort(key=lambda t: (-t[0], -t[1], -t[2], t[3]))
        top = [(_c[3], _c[0], _c[1]) for _c in _cands[:limit]]
        # ② 按朝代分组（组数／对数）：一次 GROUP BY dynasty, sig 后在 Python 侧汇总
        _dyn = {}
        for _d, _sig, _n in conn.execute(
                "SELECT dynasty, sig, COUNT(1) n FROM _pair_scope "
                "WHERE sig IS NOT NULL AND sig <> '' GROUP BY dynasty, sig HAVING n >= 2"):
            _g, _p = _dyn.get(_d, (0, 0))
            _dyn[_d] = (_g + 1, _p + _n * (_n - 1) // 2)
        by_dyn = [(_d,) + _dyn.get(_d, (0, 0)) for _d in ('清', '宋', '元')]
        n_scope_all, n_scope = conn.execute(
            "SELECT COUNT(1), SUM(CASE WHEN sig IS NOT NULL AND sig <> '' THEN 1 ELSE 0 END) "
            "FROM _pair_scope").fetchone()
        n_scope_all, n_scope = int(n_scope_all), int(n_scope or 0)
    else:                                  # 回退路径：保持原 CTE 写法
        b = 'WITH s AS (%s) ' % base
        cnt = conn.execute(
            b + "SELECT COUNT(1), SUM(CASE WHEN sig IS NOT NULL AND sig <> '' THEN 1 ELSE 0 END) "
                'FROM s', args).fetchone()
        n_scope_all, n_scope = int(cnt[0]), int(cnt[1])
        cnt2 = conn.execute(
            b + 'SELECT COUNT(1), COALESCE(SUM(n * (n - 1) / 2), 0), COALESCE(SUM(n), 0) FROM '
                "(SELECT sig, COUNT(1) n FROM s WHERE sig IS NOT NULL AND sig <> '' "
                'GROUP BY sig HAVING n >= 2)', args).fetchone()
        n_groups, n_pairs, n_covered = int(cnt2[0]), int(cnt2[1]), int(cnt2[2])
        by_dyn = []
        for d in ('清', '宋', '元'):
            r = conn.execute(
                b + 'SELECT COUNT(1), COALESCE(SUM(n * (n - 1) / 2), 0) FROM '
                    "(SELECT sig, COUNT(1) n FROM s WHERE sig IS NOT NULL AND sig <> '' "
                    'AND dynasty = ? GROUP BY sig HAVING n >= 2)', args + [d]).fetchone()
            by_dyn.append((d, int(r[0]), int(r[1])))
        short = conn.execute(
            b + 'SELECT COUNT(1) FROM (SELECT sig FROM s WHERE sig IS NOT NULL '
                "AND sig <> '' GROUP BY sig HAVING COUNT(1) >= 2 AND LENGTH(sig) < ?)",
            args + [min_len]).fetchone()[0]
        n_short = int(short)
        top = conn.execute(
            b + 'SELECT sig, COUNT(1) n, MIN(sent_n) mn FROM s '
                "WHERE sig IS NOT NULL AND sig <> '' "
                'GROUP BY sig HAVING n >= 2 AND LENGTH(sig) >= ? '
                'ORDER BY n DESC, mn DESC, LENGTH(sig) DESC, sig LIMIT ?',
            args + [min_len, limit]).fetchall()

    # ③ 取入选组的全部行：一条 IN 查询后在 Python 侧分桶（原为每组一条 WHERE sig = ?）
    if materialized:
        _buckets = {}
        if top:
            _qs = ','.join('?' * len(top))
            for _r in conn.execute(
                    'SELECT * FROM _pair_scope WHERE sig IN (%s)' % _qs, [t[0] for t in top]):
                _buckets.setdefault(_r[9], []).append(_r)
    groups = []
    for sig, n, _mn in top:
        if materialized:
            rows = sorted(_buckets.get(sig, []), key=lambda r: r[0])   # 与原 ORDER BY pid 一致
        else:
            rows = conn.execute(
                'WITH s AS (%s) SELECT * FROM s WHERE sig = ? ORDER BY pid' % base,
                args + [sig]).fetchall()
        pick, seen_a = [], set()
        for r in rows:                                  # 先挑「不同词人」的两篇
            if r[2] not in seen_a:
                pick.append(r)
                seen_a.add(r[2])
            if len(pick) == per_group:
                break
        for r in rows:                                  # 不足再从同词人里补
            if len(pick) == per_group:
                break
            if r not in pick:
                pick.append(r)
        groups.append({'sig': sig, 'n': int(n),
                       'same_cipai': len({r[3] for r in rows}) == 1,
                       'n_cipai': len({r[3] for r in rows}),
                       'poems': [{'pid': r[0], 'dynasty': r[1], 'author': r[2], 'cipai': r[3],
                                  'title': r[4], 'sent_n': r[5], 'han_len': r[6],
                                  'ze_ratio': r[7], 'scene': r[8], 'sig': r[9]} for r in pick]})
    if materialized:
        conn.execute('DROP TABLE IF EXISTS _pair_scope')
    _res = {'scope_n': n_scope, 'scope_all': n_scope_all, 'n_groups': n_groups,
            'n_pairs': n_pairs, 'n_covered': n_covered, 'n_short': int(n_short),
            'min_len': min_len, 'by_dyn': by_dyn, 'groups': groups}
    if len(_PAIR_RESULT_CACHE) > 16:            # 上限保护
        _PAIR_RESULT_CACHE.clear()
    _PAIR_RESULT_CACHE[_key] = copy.deepcopy(_res)
    return _res


def audit(conn, spec, groups=()):
    """**独立路径**复算：Python 侧把每篇的平仄串重算一遍再分组（不用 SQL 的 GROUP BY）。

    同时对展示的每一对做**逐位**比对（位位数、不同位数、首个不同位）。

    性能：一次 JOIN 取回范围内全部句（按 pid, idx 有序），在 Python 侧按 pid 聚合。
    原实现对**每一篇**单独发一条 `SELECT pz FROM lines WHERE pid = ?`——全库范围下
    即 58,852 条查询（与 selftest 剖面里 118,298 次 execute 吻合），单次 audit 约 9.4 秒；
    改为单查询后语义完全不变（仍是 Python 侧重算 + Counter 分组，独立于 SQL 的 GROUP BY）。
    """
    where, args = _scope_sql(spec)
    # 结果缓存：同一连接、同一范围、且库未改动时复用（自检与问答会对同一道题多次调用 audit）。
    # **独立性不变**：这里仍是 Python 侧重算 + Counter 分组 + 逐位比对（不用 SQL 的 GROUP BY），
    # 只是不再把同一份全库平仄串重复取两遍（一次 42 万行）。
    _akey = (conn, where, tuple(args), conn.total_changes)
    _ahit = _AUDIT_CACHE.get(_akey)
    if _ahit is not None and not groups:
        import copy as _copy
        return _copy.deepcopy(_ahit)
    # 「全篇平仄串」也是**派生结果**：同一条件算过一次就不必再取一遍 42 万行。
    # 独立性不受影响——串仍是 Python 侧从 lines 逐行拼出来的，只是不重复取数；
    # 逐对比验（per_pair）每次照算，不缓存。
    sigs = _AUDIT_SIGS_CACHE.get(_akey)
    if sigs is None:
        rows = conn.execute(
            'SELECT ln.pid, ln.pz FROM lines ln JOIN poems p ON p.pid = ln.pid '
            'WHERE %s ORDER BY ln.pid, ln.idx' % where, args).fetchall()
        sigs = {}
        buf = []
        cur = None
        for pid, pz in rows:                   # 已按 (pid, idx) 有序，顺序拼接即得全篇平仄串
            if pid != cur:
                if cur is not None and buf:
                    sigs[cur] = ''.join(buf)
                cur, buf = pid, []
            buf.append(pz or '')
        if cur is not None and buf:
            sigs[cur] = ''.join(buf)
        if len(_AUDIT_SIGS_CACHE) > 16:
            _AUDIT_SIGS_CACHE.clear()
        _AUDIT_SIGS_CACHE[_akey] = sigs
    c = Counter(sigs.values())
    n_groups = sum(1 for v in c.values() if v >= 2)
    n_pairs = sum(v * (v - 1) // 2 for v in c.values() if v >= 2)
    per_pair = []
    for g in groups or ():
        ps = g['poems']
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                a, b = ps[i], ps[j]
                sa, sb = sigs.get(a['pid'], ''), sigs.get(b['pid'], '')
                n_pos = min(len(sa), len(sb))
                diff = [k for k in range(n_pos) if sa[k] != sb[k]]
                per_pair.append({'a': a['pid'], 'b': b['pid'], 'n_pos': n_pos,
                                 'n_diff': len(diff) + abs(len(sa) - len(sb)),
                                 'first_diff': (diff[0] + 1) if diff else None,
                                 'ok': sa == sb and sa != ''})
    _ares = {'n_groups': n_groups, 'n_pairs': n_pairs, 'n_pairs_scope': len(sigs),
             'per_pair': per_pair}
    if not groups:
        import copy as _copy
        if len(_AUDIT_CACHE) > 16:
            _AUDIT_CACHE.clear()
        _AUDIT_CACHE[_akey] = _copy.deepcopy(_ares)
    return _ares


def main():
    ap = argparse.ArgumentParser(description='配对题：全篇逐位平仄相同的对子（独立复核）')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--question', default='找出几对每个位置上的字平仄都相同的两首词')
    ap.add_argument('--limit', type=int, default=3)
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    spec = retrieve.parse_query(conn, args.question)
    print('条件：%s' % spec.describe())
    if not getattr(spec, 'pair', None):
        print('· 未被识别为配对题')
        return 1
    g = find_pairs(conn, spec, limit=args.limit)
    print('范围 %d 篇：组 %d、对 %d、涉及篇 %d'
          % (g['scope_n'], g['n_groups'], g['n_pairs'], g['n_covered']))
    for d, ng, np_ in g['by_dyn']:
        print('   %s：组 %d、对 %d' % (d, ng, np_))
    for k, grp in enumerate(g['groups'], 1):
        print('第 %d 组：组内 %d 首、平仄串 %d 位' % (k, grp['n'], len(grp['sig'])))
        for p in grp['poems']:
            print('   %s · %s《%s》（%s）%d 句 / %d 字'
                  % (p['dynasty'], p['author'], p['title'], p['cipai'], p['sent_n'], p['han_len']))
    a = audit(conn, spec, g['groups'])
    print('独立复核：组 %d、对 %d（SQL：组 %d、对 %d）'
          % (a['n_groups'], a['n_pairs'], g['n_groups'], g['n_pairs']))
    for pp in a['per_pair']:
        print('   逐位：%s ↔ %s → %d 位，不同 %d 位，%s'
              % (pp['a'], pp['b'], pp['n_pos'], pp['n_diff'], 'OK' if pp['ok'] else 'FAIL'))
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
