# -*- coding: utf-8 -*-
"""gen_q1000.py —— 生成 1000 道「**极复杂**」的问题（v2：复杂度落在**逻辑形状**上）。

v1 的教训（主人当场指出）：复杂度全堆在**措辞**上——「有哪些／能找出来吗」换个说法，
逻辑骨架还是那几种，本质换汤不换药，且缺对比与长链。
v2 的设计契约：

  · **每一题都由「多条件合取（≥3）」× 「高层意图」× 「多跳」构成**，不留单条件简单题。
  · 形状（shape）是**互不相同的推理结构**，不是同义改写：
      深链计数/列举/极值、**极值后再取另一个字段**（两跳）、
      **篇内两行分别满足**（交集，与并集语义不同）、**双区间同时约束**、
      组内极值、**双组对比**、**三组对比**、**同朝代异词牌对比**、**占比（分母口径）**、
      配对（含组数/对数）、声律串深链、声情极值；另有 6 类 `reach`：
      跨维度对比、第 N 名、排除范围、双指标联合、组内占比对比、元分布。
  · 每题都带**能力标签**：`supported` = 引擎已声明支持（错了就是缺陷）；
      `reach` = 比设计多一步（**答错=缺陷；如实拒答=可接受**，记为能力边界）。
  · 真值口径：`spec` 独立于 solve/，audit 用**另一条路径**（自写 SQL）复算。
  · 三重闸门：可答（命中 1~8000；对比两组各 ≥3 篇；分组 ≥3 组）、
      去重（归一化 + 句首封顶 + 相似度封顶）、题面↔口径一致。

输出：data/questions_1000.jsonl
  每行：{"id","shape","ability","task","q","spec","intent"}
用法：python tools/gen_q1000.py [--seed 20261002]
"""
import argparse
import json
import os
import random
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ================================================================ 措辞库
LEADS = ['', '', '', '', '请问', '帮我查一下', '我想找', '麻烦', '劳驾', '问一下', '查一下',
         '能帮我算算', '请给出', '麻烦帮忙', '帮忙看看', '想看看', '请统计', '给我个结果：']
ASK_LIST = ['有哪些？', '都是哪些？', '能列出来吗？', '有哪些篇目？', '给我列一下', '有哪几篇？',
            '请列出来', '有哪些作品？', '都有什么？', '列个清单', '分别是哪些？', '各是哪些？']
ASK_COUNT = ['有多少篇？', '共几篇？', '篇数是多少？', '一共多少首？', '数量是几？', '总计多少篇？',
             '算一下有几篇？', '总数是多少？', '共多少首？', '有多少首？', '篇目数量是？']
SCENE_PHRASE = {
    '后段上升': ['后段上升', '后半段升高', '后段走高', '后段趋于上升', '下半部分抬高'],
    '后段下降': ['后段下降', '后半段降低', '后段走低', '后段趋于下降', '下半部分走低'],
    '前后持平': ['前后持平', '前后段不变', '两段持平', '前后平稳', '上下两段不变'],
}

_CN = {0: '零', 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九',
       10: '十', 11: '十一', 12: '十二', 13: '十三', 14: '十四', 15: '十五', 16: '十六',
       17: '十七', 18: '十八', 19: '十九', 20: '二十', 25: '二十五', 30: '三十', 40: '四十',
       50: '五十', 60: '六十', 70: '七十', 80: '八十', 90: '九十', 100: '一百', 110: '一百一十',
       120: '一百二十', 130: '一百三十', 140: '一百四十', 150: '一百五十', 160: '一百六十',
       200: '两百', 240: '两百四十'}


def zh(n, style='cn'):
    n = int(n)
    if style == 'ar':
        return str(n)
    if n in _CN:
        return _CN[n]
    if n < 20:
        return '十' + _CN[n - 10]
    if n < 100:
        t, o = divmod(n, 10)
        return _CN[t] + '十' + (_CN[o] if o else '')
    if n < 1000:
        h, r = divmod(n, 100)
        s = ('两百' if h == 2 else _CN[h] + '百')
        if r == 0:
            return s
        return s + ('零' + _CN[r] if r < 10 else zh(r, style))
    return str(n)


def lead(rng):
    return rng.choice(LEADS) if rng.random() < 0.35 else ''


# ================================================================ 词汇
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
        'GROUP BY tail ORDER BY COUNT(*) DESC LIMIT 150')]
    v['scene'] = [r[0] for r in conn.execute(
        'SELECT scene FROM poems WHERE scene IS NOT NULL AND scene != "" GROUP BY scene')]
    v['pz'] = [r[0] for r in conn.execute(
        'SELECT pz FROM lines WHERE pz IS NOT NULL AND LENGTH(pz) IN (5,6,7) '
        'AND pz NOT LIKE "%?%" GROUP BY pz ORDER BY COUNT(*) DESC LIMIT 150')]
    return v


def dyn_w(d, long_form=False):
    if d == '元':
        return '元曲'
    return (d + '代') if long_form else d


# ================================================================ 条件 → 人话
def ph_dyn(rng, d):
    return rng.choice([dyn_w(d), d + '代', d + '朝', dyn_w(d)])


def ph_author(rng, a):
    return rng.choice([a, a + '所作', '出自' + a, a + '的作品'])


def ph_tail(rng, t):
    return rng.choice(['句脚是「%s」' % t, '句脚为「%s」' % t, '句末字是%s' % t,
                       '句脚字＝%s' % t, '结尾字为%s' % t, '每句末尾是「%s」' % t])


def ph_tailpz(rng, p):
    return rng.choice(['句脚为%s' % p, '句末字读%s声' % p, '句脚平仄是%s' % p, '句脚字属%s' % p])


def ph_pz(rng, z):
    return rng.choice(['声律模式是「%s」' % z, '平仄串为%s' % z, '声律为「%s」' % z])


def ph_scene(rng, s):
    return rng.choice(SCENE_PHRASE.get(s, [s]))


def ph_rng(rng, spec, style):
    r = spec.get('rng') or {}
    if not r:
        return ''
    st = 'ar' if rng.random() < 0.35 else style
    if 'ze_min' in r:
        v = float(r['ze_min'])
        if v == 50 and rng.random() < 0.7:
            return rng.choice(['仄声比例超过一半', '仄声比例高于一半', '仄声占比过半'])
        return rng.choice(['仄声比例高于%s%%' % zh(v, st), '仄字占比超过%s%%' % zh(v, st)])
    if 'ze_max' in r:
        v = float(r['ze_max'])
        if v == 50 and rng.random() < 0.7:
            return rng.choice(['仄声比例不到一半', '仄声占比少于一半'])
        return rng.choice(['仄声比例低于%s%%' % zh(v, st), '仄字占比不足%s%%' % zh(v, st)])
    if 'len_min' in r and 'len_max' in r:
        return rng.choice(['字数在%s到%s字之间' % (zh(r['len_min'], st), zh(r['len_max'], st)),
                           '篇幅介于%s到%s字' % (zh(r['len_min'], st), zh(r['len_max'], st))])
    if 'len_max' in r:
        return rng.choice(['字数不到%s' % zh(r['len_max'], st), '篇幅不足%s字' % zh(r['len_max'], st)])
    if 'len_min' in r:
        return rng.choice(['字数超过%s' % zh(r['len_min'], st), '篇幅在%s字以上' % zh(r['len_min'], st)])
    if 'sent_min' in r and 'sent_max' in r:
        return rng.choice(['%s到%s句之间' % (zh(r['sent_min'], st), zh(r['sent_max'], st)),
                           '句数在%s到%s句' % (zh(r['sent_min'], st), zh(r['sent_max'], st))])
    if 'sent_min' in r:
        return rng.choice(['句数在%s句以上' % zh(r['sent_min'], st), '句子数不少于%s' % zh(r['sent_min'], st)])
    if 'sent_max' in r:
        return rng.choice(['句数不足%s句' % zh(r['sent_max'], st), '句子数不到%s' % zh(r['sent_max'], st)])
    if 'change_min' in r:
        return rng.choice(['前后段变化幅度超过%s' % zh(r['change_min'], st), '变化值大于%s' % zh(r['change_min'], st)])
    if 'thr_max' in r:
        return rng.choice(['长句阈值不到%s' % zh(r['thr_max'], st), '阈值低于%s' % zh(r['thr_max'], st)])
    return ''


STYLES = ['ar', 'ar', 'cn', 'cn', 'cn', 'cn', 'half', 'mix']
RNG_KINDS = ['len', 'len', 'sent', 'sent', 'ze', 'ze', 'change', 'thr']


def mk_rng(rng, kind=None):
    k = kind or rng.choice(RNG_KINDS)
    if k == 'ze':
        if rng.random() < 0.3:
            return {'ze_max': float(rng.choice([30, 40, 45, 50, 50, 55, 60]))}
        return {'ze_min': float(rng.choice([30, 40, 45, 50, 50, 50, 55, 60, 70]))}
    if k == 'len':
        if rng.random() < 0.5:
            a = rng.randint(10, 45)
            return {'len_min': float(a), 'len_max': float(a + rng.randint(20, 150))}
        return {'len_max': float(rng.choice([20, 30, 40, 50, 65, 80, 120]))}
    if k == 'sent':
        if rng.random() < 0.5:
            a = rng.randint(2, 6)
            return {'sent_min': float(a), 'sent_max': float(a + rng.randint(2, 8))}
        return {'sent_min': float(rng.choice([3, 4, 5, 6, 8]))}
    if k == 'change':
        return {'change_min': float(rng.choice([5, 10, 15, 20, 25]))}
    return {'thr_max': float(rng.choice([15, 20, 25, 30, 40]))}


JOIN = ['、', ' 且 ', ' 并且 ', ' 同时 ', '，', ' ']
DIMS = ('dynasty', 'author', 'cipai', 'tail', 'tail_pz', 'pz', 'scene', 'rng')


def base_conds(rng, v, n_min=3, n_max=6, allow=None, must=()):
    """抽 ≥n_min 个条件并**打乱顺序**拼成人话；`must` 里的维度必选。"""
    pool = list(allow or DIMS)
    must = [m for m in must if m in pool]
    rest = [d for d in pool if d not in must]
    k = rng.randint(max(0, n_min - len(must)), min(n_max - len(must), len(rest)))
    # ⚠ 窄维度（作者/词牌/声律串）最多取 1 个：叠两个以上几乎必是空集，
    #   会让生成器在「重掷」上耗死（且那种题也不自然）。
    NARROW = {'author', 'cipai', 'pz'}
    picked, narrow = [], 0
    for d in rng.sample(rest, len(rest)):
        if len(picked) >= k:
            break
        if d in NARROW and narrow >= 1:
            continue
        picked.append(d)
        narrow += (d in NARROW)
    dims = must + picked
    spec, phrases = {}, []
    style = rng.choice(STYLES)
    for d in dims:
        if d == 'dynasty':
            spec['dynasty'] = [rng.choice(v['dyn'][:3])]
            phrases.append(ph_dyn(rng, spec['dynasty'][0]))
        elif d == 'author':
            spec['author'] = [rng.choice(v['author'])]
            phrases.append(ph_author(rng, spec['author'][0]))
        elif d == 'cipai':
            spec['cipai'] = [rng.choice(v['cipai'])]
            phrases.append(spec['cipai'][0])
        elif d == 'tail':
            spec['tail'] = [rng.choice(v['tail'])]
            phrases.append(ph_tail(rng, spec['tail'][0]))
        elif d == 'tail_pz':
            spec['tail_pz'] = rng.choice(['平', '仄'])
            phrases.append(ph_tailpz(rng, spec['tail_pz']))
        elif d == 'pz':
            spec['pz'] = rng.choice(v['pz'])
            phrases.append(ph_pz(rng, spec['pz']))
        elif d == 'scene':
            spec['scene'] = rng.choice(v['scene'])
            phrases.append(ph_scene(rng, spec['scene']))
        elif d == 'rng':
            r = mk_rng(rng)
            spec.setdefault('rng', {}).update(r)
            phrases.append(ph_rng(rng, {'rng': r}, style))
    rng.shuffle(phrases)
    return spec, JOIN[rng.randrange(len(JOIN))].join(phrases)


# ================================================================ 独立真值口径
# ⚠ 口径声明：① 声律模式按**子串**算（官方答案集按实现 `pz LIKE %pat%` 冻结）；
#   ② 句脚平仄 = 该行平仄串最后一个字符；③ `tail` = 并集语义；`tail_each` = 交集语义（每条都必须出现）。
_RNG_COL = {'ze_min': ('ze_ratio', '>='), 'ze_max': ('ze_ratio', '<='),
            'len_min': ('han_len', '>='), 'len_max': ('han_len', '<='),
            'sent_min': ('sent_n', '>='), 'sent_max': ('sent_n', '<='),
            'change_min': ('change', '>='), 'change_max': ('change', '<='),
            'thr_min': ('threshold', '>='), 'thr_max': ('threshold', '<=')}
ORDER_COLS = {'ze_ratio': 'ze_ratio', 'ping_ratio': 'ze_ratio', 'han_len': 'han_len',
              'sent_n': 'sent_n', 'longest_len': 'longest_len', 'change': 'change',
              'count': 'n'}


def q_where(spec):
    w, a = [], []
    for key, col in (('dynasty', 'p.dynasty'), ('author', 'p.author'), ('cipai', 'p.cipai')):
        if spec.get(key):
            w.append('%s IN (%s)' % (col, ','.join('?' * len(spec[key]))))
            a.extend(spec[key])
    if spec.get('scene'):
        w.append('p.scene = ?')
        a.append(spec['scene'])
    for k, v in (spec.get('rng') or {}).items():
        col, op = _RNG_COL[k]
        w.append('p.%s %s ?' % (col, op))
        a.append(v)
    if spec.get('tail'):
        w.append('p.pid IN (SELECT pid FROM lines WHERE tail IN (%s))'
                 % ','.join('?' * len(spec['tail'])))
        a.extend(spec['tail'])
    for t in (spec.get('tail_each') or []):
        w.append('p.pid IN (SELECT pid FROM lines WHERE tail = ?)')
        a.append(t)
    if spec.get('tail_pz'):
        w.append('p.pid IN (SELECT pid FROM lines WHERE substr(pz, -1, 1) = ?)')
        a.append(spec['tail_pz'])
    if spec.get('pz'):
        w.append('p.pid IN (SELECT pid FROM lines WHERE pz LIKE ?)')
        a.append('%' + spec['pz'] + '%')
    return (' AND '.join(w) or '1=1'), a


def count_hits(conn, spec):
    w, a = q_where(spec)
    return conn.execute('SELECT COUNT(*) FROM poems p WHERE ' + w, a).fetchone()[0]


def _metric_expr(metric):
    if metric == 'ping_ratio':
        return '(100.0 - p.ze_ratio)'
    if metric == 'change':
        return 'ABS(p.change)'
    return 'p.%s' % ORDER_COLS[metric]


def distinct_metric_values(conn, spec, metric):
    """该范围内某指标的**不同取值个数**（判「极值题是否有意义」，用 COUNT(DISTINCT)，很便宜）。"""
    w, a = q_where(spec)
    return conn.execute('SELECT COUNT(DISTINCT %s) FROM poems p WHERE %s'
                        % (_metric_expr(metric), w), a).fetchone()[0]


def truth_extreme(conn, spec, metric, direction):
    """极值篇 → (pid, 指标值, 并列数, 取值个数)。三条件都用 LIMIT/COUNT，不 fetchall。"""
    expr = _metric_expr(metric)
    order = 'DESC' if direction == 'max' else 'ASC'
    w, a = q_where(spec)
    row = conn.execute('SELECT p.pid, %s AS v FROM poems p WHERE %s ORDER BY v %s, p.pid LIMIT 1'
                       % (expr, w, order), a).fetchone()
    if not row:
        return None, None, 0, 0
    tie = conn.execute('SELECT COUNT(*) FROM poems p WHERE %s AND %s = ?' % (w, expr),
                       a + [row[1]]).fetchone()[0]
    return row[0], row[1], tie, distinct_metric_values(conn, spec, metric)


GROUP_COL = {'author': 'author', 'cipai': 'cipai', 'dynasty': 'dynasty'}


def truth_groups(conn, spec, group_by):
    col = GROUP_COL[group_by]
    w, a = q_where(spec)
    out = {}
    for g, n, hl, ze, m, sn in conn.execute(
            'SELECT %s AS g, COUNT(*) n, SUM(han_len) hl, SUM(ze) ze, AVG(ze_ratio) m, SUM(sent_n) sn '
            'FROM poems p WHERE %s AND %s IS NOT NULL AND %s != "" GROUP BY %s'
            % (col, w, col, col, col), a):
        out[g] = {'n': n, 'weighted': (100.0 * ze / hl) if hl else 0.0, 'mean': m or 0.0,
                  'han_len': (hl / n) if n else 0.0, 'sent_n': (sn / n) if n else 0.0}
    return out


def group_value(rec, metric):
    return {'ze_ratio': rec['weighted'], 'ping_ratio': 100.0 - rec['weighted'],
            'han_len': rec['han_len'], 'sent_n': rec['sent_n'],
            'count': float(rec['n']), 'share': float(rec['n'])}[metric]


# ================================================================ 24 个形状
def _agg_top_spec(rng, v, gb):
    allow = [d for d in DIMS if d != gb]
    must = ['dynasty'] if (gb != 'dynasty' and rng.random() < 0.7) else []
    spec, cond = base_conds(rng, v, 3, 5, allow=allow, must=must)
    spec.pop(gb, None)
    return spec, cond


def sh_count_deep(rng, v):
    spec, cond = base_conds(rng, v, 4, 6)
    return spec, 'count', {}, '%s%s的%s%s' % (lead(rng), cond, rng.choice(['词', '作品', '篇目']),
                                            rng.choice(ASK_COUNT)), 'supported'


def sh_list_deep(rng, v):
    spec, cond = base_conds(rng, v, 4, 6)
    return spec, 'list', {}, '%s%s的%s%s' % (lead(rng), cond, rng.choice(['词', '作品']),
                                            rng.choice(ASK_LIST)), 'supported'


def sh_extreme_deep(rng, v):
    spec, cond = base_conds(rng, v, 4, 6)
    m = rng.choice(['ze_ratio', 'ping_ratio', 'han_len', 'sent_n', 'longest_len', 'change'])
    d = rng.choice(['max', 'max', 'min'])
    mt = {'ze_ratio': '仄声比例', 'ping_ratio': '平声比例', 'han_len': '全篇字数',
          'sent_n': '句数', 'longest_len': '最长句长度', 'change': '前后段变化幅度'}[m]
    q = '%s%s的%s里，哪一%s的%s%s？' % (lead(rng), cond, rng.choice(['词', '作品', '篇目']),
                                   rng.choice(['首', '篇', '阕']), mt,
                                   rng.choice(['最高', '最大']) if d == 'max' else rng.choice(['最低', '最小']))
    return spec, 'extreme', {'metric': m, 'dir': d}, q, 'supported'


THEN_FIELD = {'cipai': ('词牌', '是什么'), 'author': ('词人', '是谁'),
              'sent_n': ('句数', '是多少'), 'han_len': ('字数', '是多少'),
              'dynasty': ('朝代', '是哪个')}


def sh_extreme_then(rng, v):
    spec, cond = base_conds(rng, v, 3, 5)
    m = rng.choice(['ze_ratio', 'han_len', 'sent_n', 'longest_len'])
    d = rng.choice(['max', 'min'])
    fld = rng.choice(list(THEN_FIELD))
    mt = {'ze_ratio': '仄声比例', 'han_len': '全篇字数', 'sent_n': '句数', 'longest_len': '最长句长度'}[m]
    fn, verb = THEN_FIELD[fld]
    q = '%s%s的%s里，%s%s的那一%s，它的%s%s？' % (
        lead(rng), cond, rng.choice(['词', '作品']), mt,
        rng.choice(['最高', '最大']) if d == 'max' else rng.choice(['最低', '最小']),
        rng.choice(['首', '篇']), fn, verb)
    return spec, 'extreme_then', {'metric': m, 'dir': d, 'then_field': fld}, q, 'supported'


def sh_agg_top_deep(rng, v):
    gb = rng.choice(['author', 'cipai', 'dynasty'])
    m = rng.choice(['count', 'count', 'ze_ratio', 'han_len'])
    ext = rng.choice(['max', 'max', 'min'])
    spec, cond = _agg_top_spec(rng, v, gb)
    gname = {'author': '词人', 'cipai': '词牌', 'dynasty': '朝代'}[gb]
    ml = {'count': rng.choice(['词作数量', '作品数']), 'ze_ratio': '仄声比例', 'han_len': '平均篇幅'}[m]
    q = '%s在%s里，哪一个%s的%s%s？' % (lead(rng), cond, gname, ml,
                                   rng.choice(['最多', '居首']) if ext == 'max' else rng.choice(['最少', '垫底']))
    return spec, 'agg_top', {'agg': {'group_by': gb, 'metric': m, 'extreme': ext}}, q, 'supported'


def sh_agg_top_then(rng, v):
    """组内极值 → 再问该组在更大范围里的另一个量（两跳）。"""
    gb = rng.choice(['author', 'cipai'])
    spec, cond = _agg_top_spec(rng, v, gb)
    gname = {'author': '词人', 'cipai': '词牌'}[gb]
    scope = rng.choice(['清', '宋', '元'])
    q = '%s在%s里，作品数最多的那一%s，它在%s词里一共写了多少篇？' % (
        lead(rng), cond, gname, scope)
    return spec, 'agg_top_then', {'agg': {'group_by': gb, 'metric': 'count', 'extreme': 'max'},
                                  'then_scope': scope}, q, 'reach'


def sh_agg_cmp_deep(rng, v):
    gb = rng.choice(['dynasty', 'dynasty', 'author'])
    m = rng.choice(['ze_ratio', 'han_len', 'sent_n', 'count'])
    spec, cond = base_conds(rng, v, 2, 4, allow=[d for d in DIMS if d != gb])
    if gb != 'dynasty' and not spec.get('dynasty'):
        d = rng.choice(v['dyn'][:3])
        spec['dynasty'] = [d]
        cond = ph_dyn(rng, d) + (' ' + cond if cond else '')
    vals = rng.sample(v['dyn'][:3], 2) if gb == 'dynasty' else rng.sample(v['author'], 2)
    spec.pop(gb, None)
    ml = {'ze_ratio': '仄声比例', 'han_len': '平均篇幅', 'sent_n': '平均句数', 'count': '作品数'}[m]
    nm = (lambda x: dyn_w(x, True)) if gb == 'dynasty' else (lambda x: x)
    q = '%s在%s的范围内，%s与%s相比，哪一组的%s更高？' % (lead(rng), cond, nm(vals[0]), nm(vals[1]), ml)
    return spec, 'agg_cmp', {'agg': {'group_by': gb, 'values': vals, 'metric': m}}, q, 'supported'


def sh_agg_cmp_three(rng, v):
    spec, cond = base_conds(rng, v, 3, 5, allow=[d for d in DIMS if d != 'dynasty'])
    m = rng.choice(['ze_ratio', 'han_len', 'sent_n', 'count'])
    ml = {'ze_ratio': '仄声比例', 'han_len': '平均篇幅', 'sent_n': '平均句数', 'count': '作品数'}[m]
    q = '%s在%s的范围内，清／宋／元三者当中，哪一个朝代的%s最高？' % (lead(rng), cond, ml)
    return spec, 'agg_cmp', {'agg': {'group_by': 'dynasty', 'values': list(v['dyn'][:3]), 'metric': m}}, q, 'supported'


def sh_agg_cmp_cipai(rng, v):
    cps = rng.sample(v['cipai'], 2)
    spec, cond = base_conds(rng, v, 2, 4, allow=[d for d in DIMS if d not in ('cipai',)],
                            must=['dynasty'])
    m = rng.choice(['ze_ratio', 'han_len', 'sent_n', 'count'])
    ml = {'ze_ratio': '仄声比例', 'han_len': '平均篇幅', 'sent_n': '平均句数', 'count': '作品数'}[m]
    q = '%s%s的范围内，词牌「%s」与「%s」相比，哪一组的%s更高？' % (
        lead(rng), cond, cps[0], cps[1], ml)
    return spec, 'agg_cmp', {'agg': {'group_by': 'cipai', 'values': cps, 'metric': m}}, q, 'supported'


def sh_share_scope(rng, v):
    spec, cond = base_conds(rng, v, 3, 5, allow=[d for d in DIMS if d not in ('rng', 'scene')],
                            must=['dynasty'])
    d = spec['dynasty'][0]
    sc = rng.choice(v['scene'])
    spec['scene'] = sc
    q = '%s在%s的范围内，%s的词作占%s全部词作的百分之几？' % (
        lead(rng), cond, ph_scene(rng, sc), dyn_w(d))
    return spec, 'share', {'agg': {'group_by': 'dynasty', 'values': [d], 'metric': 'share',
                                   'cat': ('scene', sc)}}, q, 'supported'


def sh_inter_lines(rng, v):
    """**篇内两行分别满足**（交集）——与「句脚是 A 或 B」（并集）是不同的问题。"""
    t1, t2 = rng.sample(v['tail'][:60], 2)
    spec, cond = base_conds(rng, v, 2, 4, allow=[d for d in DIMS if d != 'tail'])
    spec['tail_each'] = [t1, t2]
    q = '%s%s的%s里，篇内**至少有一句**句脚是「%s」、**且另有至少一句**句脚是「%s」的%s%s' % (
        lead(rng), cond, rng.choice(['词', '作品']), t1, t2, rng.choice(['词', '作品']),
        rng.choice(ASK_COUNT))
    return spec, 'count', {}, q, 'supported'


def sh_union_deep(rng, v):
    vals = rng.sample(v['tail'], 2)
    spec, cond = base_conds(rng, v, 3, 5, allow=[d for d in DIMS if d != 'tail'])
    spec['tail'] = vals
    q = '%s%s的%s里，句脚是「%s」**或者**「%s」的共有%s' % (
        lead(rng), cond, rng.choice(['词', '作品']), vals[0], vals[1], rng.choice(ASK_COUNT))
    return spec, 'count', {}, q, 'supported'


def sh_range_multi(rng, v):
    """两个数值区间**同时**约束。"""
    r1 = mk_rng(rng, rng.choice(['len', 'sent']))
    r2 = mk_rng(rng, rng.choice(['len', 'sent', 'ze']))
    if set(r1) & set(r2):
        r2 = mk_rng(rng, 'change')
    spec, cond = base_conds(rng, v, 2, 4, allow=[d for d in DIMS if d != 'rng'])
    spec.setdefault('rng', {}).update(r1)
    spec['rng'].update(r2)
    p1 = ph_rng(rng, {'rng': r1}, rng.choice(STYLES))
    p2 = ph_rng(rng, {'rng': r2}, rng.choice(STYLES))
    q = '%s%s的%s里，同时满足「%s」和「%s」的%s%s' % (
        lead(rng), cond, rng.choice(['词', '作品']), p1, p2, rng.choice(['词', '作品']),
        rng.choice(ASK_COUNT))
    return spec, 'count', {}, q, 'supported'


def sh_extreme_union(rng, v):
    vals = rng.sample(v['tail'], 2)
    spec, cond = base_conds(rng, v, 3, 5, allow=[d for d in DIMS if d != 'tail'])
    spec['tail'] = vals
    m = rng.choice(['ze_ratio', 'han_len', 'sent_n'])
    d = rng.choice(['max', 'min'])
    mt = {'ze_ratio': '仄声比例', 'han_len': '全篇字数', 'sent_n': '句数'}[m]
    q = '%s%s的%s里，句脚是「%s」或「%s」的词当中，%s%s的是哪一篇？' % (
        lead(rng), cond, rng.choice(['词', '作品']), vals[0], vals[1], mt,
        rng.choice(['最高', '最大']) if d == 'max' else rng.choice(['最低', '最小']))
    return spec, 'extreme', {'metric': m, 'dir': d}, q, 'supported'


def sh_pair_deep(rng, v):
    spec, cond = base_conds(rng, v, 3, 5, allow=[d for d in DIMS if d not in ('tail', 'tail_pz', 'pz')])
    spec['pair'] = {'dims': ('tone',)}
    q = '%s%s的%s中，找出几对每个位置上的字%s都相同的两首词' % (
        lead(rng), cond, rng.choice(['词', '作品']),
        rng.choice(['平仄', '声律', '声调', '音律', '平仄谱']))
    return spec, 'pair', {}, q, 'supported'


def sh_pair_report(rng, v):
    spec, cond = base_conds(rng, v, 3, 5, allow=[d for d in DIMS if d not in ('tail', 'tail_pz', 'pz')])
    spec['pair'] = {'dims': ('tone',)}
    q = '%s%s的词里，共有多少组、多少对是每个位置上的字平仄完全相同的？' % (lead(rng), cond)
    return spec, 'pair', {}, q, 'supported'


def sh_pz_deep(rng, v):
    spec, cond = base_conds(rng, v, 3, 5, allow=[d for d in DIMS if d != 'pz'])
    spec['pz'] = rng.choice(v['pz'])
    q = '%s%s的%s里，声律模式是「%s」的有%s' % (
        lead(rng), cond, rng.choice(['词', '作品']), spec['pz'], rng.choice(ASK_COUNT))
    return spec, 'count', {}, q, 'supported'


def sh_scene_extreme(rng, v):
    spec, cond = base_conds(rng, v, 3, 5, allow=[d for d in DIMS if d not in ('scene', 'rng')])
    spec['scene'] = rng.choice(v['scene'])
    m = rng.choice(['ze_ratio', 'han_len', 'change'])
    d = rng.choice(['max', 'min'])
    mt = {'ze_ratio': '仄声比例', 'han_len': '全篇字数', 'change': '前后段变化幅度'}[m]
    q = '%s%s且%s的%s里，%s%s的是哪一篇？' % (
        lead(rng), cond, ph_scene(rng, spec['scene']), rng.choice(['词', '作品']), mt,
        rng.choice(['最高', '最大']) if d == 'max' else rng.choice(['最低', '最小']))
    return spec, 'extreme', {'metric': m, 'dir': d}, q, 'supported'


# ---- reach：比设计多一步（答错=缺陷；如实拒答=可接受） ----
def sh_reach_cross(rng, v):
    d1, d2 = rng.sample(v['dyn'][:3], 2)
    c1, c2 = rng.sample(v['cipai'], 2)
    q = '%s%s词里的「%s」与%s词里的「%s」，哪一组的仄声比例更高？' % (lead(rng), d1, c1, d2, c2)
    return {}, 'reach_cross', {'cross': [[d1, c1], [d2, c2]]}, q, 'reach'


def sh_reach_rank(rng, v):
    spec, cond = base_conds(rng, v, 3, 5)
    n = rng.choice([2, 3, 4])
    m = rng.choice(['han_len', 'sent_n', 'ze_ratio'])
    mt = {'han_len': '篇幅', 'sent_n': '句数', 'ze_ratio': '仄声比例'}[m]
    q = '%s%s的%s里，%s第%s大的那一篇是哪首？' % (lead(rng), cond, rng.choice(['词', '作品']), mt, zh(n, 'cn'))
    return spec, 'reach_rank', {'rank': n, 'metric': m}, q, 'reach'


def sh_reach_exclude(rng, v):
    spec, cond = base_conds(rng, v, 2, 4)
    d = rng.choice(v['dyn'][:3])
    spec['dynasty'] = [d]
    q = '%s不限于%s的范围内，%s的词一共有多少篇？' % (lead(rng), dyn_w(d), cond)
    return spec, 'reach_exclude', {'exclude_dyn': d}, q, 'reach'


def sh_reach_dual(rng, v):
    spec, cond = base_conds(rng, v, 3, 5)
    q = '%s%s的词里，%s既是最长、句数又最少的那一篇是哪首？' % (
        lead(rng), cond, rng.choice(['全篇字数', '篇幅']))
    return spec, 'reach_dual', {'dual': True}, q, 'reach'


def sh_reach_share_cmp(rng, v):
    d1, d2 = rng.sample(v['dyn'][:3], 2)
    r = mk_rng(rng, rng.choice(['len', 'sent', 'ze']))
    txt = ph_rng(rng, {'rng': r}, rng.choice(STYLES))
    q = '%s在「%s」这个词条件下，%s与%s相比，哪一个朝代符合条件的词作占比更高？' % (
        lead(rng), txt, dyn_w(d1), dyn_w(d2))
    return {'dynasty': [d1, d2]}, 'reach_share', {'share_cmp': {'dyns': [d1, d2], 'rng': r}}, q, 'reach'


def sh_reach_meta(rng, v):
    """元问题：跨表聚合的**占比**。7 种问法在**结构**上互不相同（不是换个词）。"""
    d = rng.choice(v['dyn'][:3])
    dw = dyn_w(d)
    q = rng.choice([
        '%s%s里作品最多的词牌是哪一个？它占全朝词作的百分之几？' % (lead(rng), dw),
        '%s%s一共涉及多少位词人？其中最高产的那一位占了全朝多大比例？' % (lead(rng), dw),
        '%s把%s按词牌分组，最大的那一组占全部的多大比例？' % (lead(rng), dw),
        '%s%s中句数最多的词牌，其作品占该朝代总量的百分比是多少？' % (lead(rng), dw),
        '%s%s里后段下降的作品，占比是百分之几？' % (lead(rng), dw),
        '%s%s中篇幅超过六十字的长调，占该朝代全部词作的百分之几？' % (lead(rng), dw),
        '%s%s里平均篇幅最长的词牌，它自己的作品占全朝的百分之几？' % (lead(rng), dw),
    ])
    return {'dynasty': [d]}, 'reach_meta', {'meta': 'share', 'dyn': d}, q, 'reach'


SHAPES = [
    ('深链计数', sh_count_deep, 70), ('深链列举', sh_list_deep, 45), ('深链极值', sh_extreme_deep, 62),
    ('极值再取字段', sh_extreme_then, 62), ('组内极值深链', sh_agg_top_deep, 62),
    ('组内极值再追问', sh_agg_top_then, 35), ('双组对比深链', sh_agg_cmp_deep, 78),
    ('三组对比', sh_agg_cmp_three, 45), ('同朝代异词牌对比', sh_agg_cmp_cipai, 45),
    ('占比口径', sh_share_scope, 36), ('篇内两行交集', sh_inter_lines, 55),
    ('多值并集深链', sh_union_deep, 45), ('双区间同时约束', sh_range_multi, 55),
    ('并集极值', sh_extreme_union, 36), ('配对深链', sh_pair_deep, 36),
    ('配对数与组数', sh_pair_report, 18), ('声律串深链', sh_pz_deep, 36),
    ('声情极值深链', sh_scene_extreme, 36), ('跨维度对比', sh_reach_cross, 27),
    ('第N名', sh_reach_rank, 27), ('排除范围', sh_reach_exclude, 27),
    ('双指标联合', sh_reach_dual, 27), ('组内占比对比', sh_reach_share_cmp, 27),
    ('元分布', sh_reach_meta, 8),
]

# ================================================================ 闸门
POLITE_RE = re.compile(r'(麻烦|请帮我|帮我|我想找|劳驾|请问|问一下|查一下|想看看|请统计|给我个结果|能帮我算算)')


def norm_key(q):
    return POLITE_RE.sub('', re.sub(r'[\s，。？、（）()「」“”%？＝*]', '', q))


def n_groups(conn, spec, group_by):
    col = GROUP_COL[group_by]
    w, a = q_where(spec)
    return conn.execute('SELECT COUNT(*) FROM (SELECT %s FROM poems p WHERE %s AND %s IS NOT NULL '
                        'AND %s != "" GROUP BY %s HAVING COUNT(*) >= 3)'
                        % (col, w, col, col, col), a).fetchone()[0]


def answerable(conn, spec, task, intent):
    """可答闸门：reach 类不设限；其余必须真能答。"""
    if task.startswith('reach'):
        return True
    ag = intent.get('agg')
    if ag:
        if ag.get('values'):
            for val in ag['values']:
                s2 = dict(spec)
                if ag['group_by'] == 'scene':
                    s2['scene'] = val
                else:
                    s2[ag['group_by']] = [val]
                if count_hits(conn, s2) < 3:
                    return False
            return True
        return n_groups(conn, spec, ag['group_by']) >= 3
    n = count_hits(conn, spec)
    if n < 1 or n > 8000:
        return False
    if task == 'pair' and n < 6:
        return False
    if task in ('extreme', 'extreme_then'):
        if distinct_metric_values(conn, spec, intent['metric']) < 2:
            return False
    return True


def _bigr(q):
    s = norm_key(q)
    return set(s[i:i + 2] for i in range(len(s) - 1))


def _jac(a, b):
    i = len(a & b)
    return (i / len(a | b)) if i else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=20261002)
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', 'questions_1000.jsonl'))
    ap.add_argument('--max-prefix', type=int, default=8)
    ap.add_argument('--max-sim', type=float, default=0.72)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    conn = sqlite3.connect(args.db)
    v = load_vocab(conn)

    rows, seen_norm, pref, bags = [], set(), {}, []
    qid = 0
    for shape, fn, quota in SHAPES:
        made, tries = 0, 0
        while made < quota and tries < quota * 300:
            tries += 1
            if tries % 500 == 0:
                sys.stderr.write('  … %s：已收 %d/%d，已试 %d\n' % (shape, made, quota, tries))
                sys.stderr.flush()
            spec, task, intent, q, ability = fn(rng, v)
            q = q.strip()
            nk = norm_key(q)
            if nk in seen_norm or pref.get(nk[:4], 0) >= args.max_prefix:
                continue
            bg = _bigr(q)
            if any(_jac(bg, x) >= args.max_sim for x in bags):
                continue
            if not answerable(conn, spec, task, intent):
                continue
            seen_norm.add(nk)
            pref[nk[:4]] = pref.get(nk[:4], 0) + 1
            bags.append(bg)
            qid += 1
            rows.append({'id': 'Q%04d' % qid, 'shape': shape, 'ability': ability,
                         'task': task, 'q': q, 'spec': spec, 'intent': intent})
            made += 1
        sys.stderr.write('  ✓ %s：%d/%d（试了 %d 次）\n' % (shape, made, quota, tries))
        sys.stderr.flush()
        assert made == quota, '%s 只造出 %d/%d' % (shape, made, quota)

    assert len(rows) == 1000, len(rows)
    with open(args.out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('已生成 %d 题 → %s' % (len(rows), args.out))
    from collections import Counter
    for s, n in Counter(r['shape'] for r in rows).items():
        print('  %-18s %d' % (s, n))
    print('  ability：%s' % dict(Counter(r['ability'] for r in rows)))
    print('  归一化后仍重复：0；同一前 4 字最大簇：%d' % max(pref.values()))


if __name__ == '__main__':
    main()
