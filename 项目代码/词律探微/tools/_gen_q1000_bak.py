# -*- coding: utf-8 -*-
"""gen_q1000.py —— 生成 1000 道「**理论上可答**、刁钻、不同质、逻辑链长」的问题。

为什么要生成器而不是手写：1000 道手写必然同质化（人会不自觉套同一个模板）。
生成器把「题型 × 条件组合 × 措辞 × 数字写法 × 干扰成分」做成**受控的正交采样**，
用固定种子保证**可复现**（同一种子两遍输出逐字节一致）。

设计约束（对应主人的要求）：
  1. **可答**：条件取值全部从库里**真实采样**；且每题过一道「可答闸门」
     （独立 SQL 复算：命中 1~8000、条件真的收窄；聚合类分组数 ≥2）。
  2. **刁钻**：口语数字（「一半」）、中文数字（「五十」「一百」）、区间口语（「五到八句」）、
     无引号多值（「灯或者声」）、体裁尾巴（「的清词」）、干扰词（礼貌语/冗余定语/语序变化）。
  3. **不同质**（本版重点）：① 每个条件有 3~5 种说法；② 每个任务有 10 种问法；
     ③ 15 种开头；④ 条件**顺序随机打乱**；⑤ **归一化去重**（去标点/礼貌语后仍相同即弃）；
     ⑥ **句首封顶**（同一前 4 字最多 12 题，超了重掷）。
  4. **逻辑链长**：多条件合取（3~5 个条件）占主力；「先按条件筛、再在子集里统计」的两跳结构独立成族。

输出：data/questions_1000.jsonl，每行：
  {"id","cat","task","q","spec":{...},"intent":{...}}
  spec 是**独立于 solve/ 的**条件表示，audit 据此自行算真值。

用法：python tools/gen_q1000.py [--seed 20261002] [--out data/questions_1000.jsonl] [--db data/corpus.db]
"""
import argparse
import json
import os
import random
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ================================================================ 措辞库（不同质的根本）
LEADS = ['', '', '', '', '请问', '帮我查一下', '我想找', '麻烦', '劳驾', '问一下', '查一下',
         '能帮我找找', '请给出', '麻烦帮忙', '帮忙看看', '想看看', '请统计', '给我个结果：']

ASK = {
    'list': ['有哪些？', '都是哪些？', '能列出来吗？', '有哪些篇目？', '给我列一下',
             '有哪几篇？', '能找出来吗？', '请列出来', '有哪些作品？', '都有什么？',
             '列个清单', '分别是哪些？'],
    'count': ['有多少篇？', '共几篇？', '篇数是多少？', '一共多少首？', '数量是几？',
              '总计多少篇？', '算一下有几篇？', '总数是多少？', '共多少首？', '有多少首？',
              '篇目数量是？', '统计出来是几篇？'],
}

SCENE_PHRASE = {
    '后段上升': ['后段上升', '后半段升高', '后段走高', '后段趋于上升', '下半部分抬高'],
    '后段下降': ['后段下降', '后半段降低', '后段走低', '后段趋于下降', '下半部分走低'],
    '前后持平': ['前后持平', '前后段不变', '两段持平', '前后平稳', '上下两段不变'],
}

_CN = {0: '零', 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九',
       10: '十', 15: '十五', 20: '二十', 30: '三十', 40: '四十', 50: '五十', 60: '六十',
       70: '七十', 80: '八十', 100: '一百', 200: '两百'}


def zh(n, style='cn'):
    """阿拉伯 / 中文数字渲染（0~999 全覆盖）。中文只对有把握的写法用「两」（两百/两千）。"""
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


def lead_of(rng, task):
    if rng.random() < 0.30:
        return rng.choice(LEADS)
    return ''


# ================================================================ 词汇采样
def load_vocab(conn):
    v = {}
    v['dyn'] = [r[0] for r in conn.execute(
        'SELECT dynasty FROM poems GROUP BY dynasty ORDER BY COUNT(*) DESC')]
    v['author'] = [r[0] for r in conn.execute(
        'SELECT author FROM poems WHERE author IS NOT NULL AND author != "" '
        'GROUP BY author HAVING COUNT(*) >= 4 ORDER BY COUNT(*) DESC LIMIT 400')]
    v['cipai'] = [r[0] for r in conn.execute(
        'SELECT cipai FROM poems WHERE cipai IS NOT NULL AND cipai != "" '
        'GROUP BY cipai HAVING COUNT(*) >= 6 ORDER BY COUNT(*) DESC LIMIT 300')]
    v['tail'] = [r[0] for r in conn.execute(
        'SELECT tail FROM lines WHERE tail IS NOT NULL AND tail != "" '
        'GROUP BY tail ORDER BY COUNT(*) DESC LIMIT 120')]
    v['scene'] = [r[0] for r in conn.execute(
        'SELECT scene FROM poems WHERE scene IS NOT NULL AND scene != "" GROUP BY scene')]
    v['pz'] = [r[0] for r in conn.execute(
        'SELECT pz FROM lines WHERE pz IS NOT NULL AND LENGTH(pz) IN (5,6,7) '
        'AND pz NOT LIKE "%?%" GROUP BY pz ORDER BY COUNT(*) DESC LIMIT 120')]
    return v


def dyn_w(d, long_form=False):
    if d == '元':
        return '元曲'
    return (d + '代') if long_form else d


# ================================================================ 条件 → 人话（多说法）
def ph_dyn(rng, d):
    return rng.choice(['%s' % dyn_w(d), '%s代' % d, '%s朝' % d, '%s' % dyn_w(d)])


def ph_author(rng, a):
    return rng.choice([a, '%s所作' % a, '出自%s' % a, '%s的作品' % a])


def ph_tail(rng, t):
    return rng.choice(['句脚是「%s」' % t, '句脚为「%s」' % t, '句末字是%s' % t,
                       '句脚字＝%s' % t, '结尾字为%s' % t, '每句末尾是「%s」' % t])


def ph_tailpz(rng, p):
    return rng.choice(['句脚为%s' % p, '句末字读%s声' % p, '句脚平仄是%s' % p,
                       '句脚字属%s' % p])


def ph_pz(rng, z):
    return rng.choice(['声律模式是「%s」' % z, '平仄串为%s' % z, '声律为「%s」' % z])


def ph_scene(rng, s):
    return rng.choice(SCENE_PHRASE.get(s, [s]))


def ph_rng(rng, spec, style):
    """数值条件的人话。**入参是完整 spec**（内部取 `spec['rng']`——曾因误当子字典取键，
    导致「数值条件根本没写进题面、题目退化成『的词都是哪些？』」的严重 bug）。
    数字写法（阿拉伯/中文/口语「一半」）每题独立再抽，保证三种写法都上量。"""
    r = spec.get('rng') or {}
    if not r:
        return ''
    st = 'ar' if rng.random() < 0.35 else style
    if 'ze_min' in r:
        v = float(r['ze_min'])
        if v == 50 and rng.random() < 0.7:
            return rng.choice(['仄声比例超过一半', '仄声比例高于一半', '仄声占比过半'])
        return rng.choice(['仄声比例高于%s%%' % zh(v, st), '仄字占比超过%s%%' % zh(v, st),
                           '仄声比重在%s%%以上' % zh(v, st)])
    if 'ze_max' in r:
        v = float(r['ze_max'])
        if v == 50 and rng.random() < 0.7:
            return rng.choice(['仄声比例不到一半', '仄声占比少于一半', '仄声比例低于一半'])
        return rng.choice(['仄声比例低于%s%%' % zh(v, st), '仄字占比不足%s%%' % zh(v, st)])
    if 'len_min' in r and 'len_max' in r:
        return rng.choice(['字数在%s到%s字之间' % (zh(r['len_min'], st), zh(r['len_max'], st)),
                           '篇幅介于%s到%s字' % (zh(r['len_min'], st), zh(r['len_max'], st))])
    if 'len_max' in r:
        return rng.choice(['字数不到%s' % zh(r['len_max'], st),
                           '篇幅不足%s字' % zh(r['len_max'], st),
                           '全篇少于%s个字' % zh(r['len_max'], st)])
    if 'len_min' in r:
        return rng.choice(['字数超过%s' % zh(r['len_min'], st),
                           '篇幅在%s字以上' % zh(r['len_min'], st)])
    if 'sent_min' in r and 'sent_max' in r:
        return rng.choice(['%s到%s句之间' % (zh(r['sent_min'], st), zh(r['sent_max'], st)),
                           '句数在%s到%s句' % (zh(r['sent_min'], st), zh(r['sent_max'], st))])
    if 'sent_min' in r:
        return rng.choice(['句数在%s句以上' % zh(r['sent_min'], st),
                           '句子数不少于%s' % zh(r['sent_min'], st)])
    if 'sent_max' in r:
        return rng.choice(['句数不足%s句' % zh(r['sent_max'], st),
                           '句子数不到%s' % zh(r['sent_max'], st)])
    if 'change_min' in r:
        return rng.choice(['前后段变化幅度超过%s' % zh(r['change_min'], st),
                           '变化值大于%s' % zh(r['change_min'], st)])
    if 'thr_max' in r:
        return rng.choice(['长句阈值不到%s' % zh(r['thr_max'], st),
                           '阈值低于%s' % zh(r['thr_max'], st)])
    return ''


STYLE_POOL = ['ar', 'ar', 'cn', 'cn', 'cn', 'cn', 'half', 'mix']


def pick_rng(rng):
    kind = rng.choice(['len', 'len', 'sent', 'sent', 'ze', 'ze', 'change', 'thr'])
    if kind == 'ze':
        if rng.random() < 0.3:
            return {'rng': {'ze_max': float(rng.choice([30, 40, 45, 50, 50, 55, 60]))}}, None
        vals = [30, 40, 45, 50, 50, 50, 55, 60, 70]          # 50 → 「一半」口语
        return {'rng': {'ze_min': float(rng.choice(vals))}}, None
    if kind == 'len':
        if rng.random() < 0.5:
            lo = rng.randint(10, 40)
            return {'rng': {'len_min': float(lo), 'len_max': float(lo + rng.randint(20, 160))}}, None
        return {'rng': {'len_max': float(rng.choice([20, 30, 40, 50, 65, 80, 120]))}}, None
    if kind == 'sent':
        if rng.random() < 0.5:
            a = rng.randint(2, 6)
            return {'rng': {'sent_min': float(a), 'sent_max': float(a + rng.randint(2, 8))}}, None
        return {'rng': {'sent_min': float(rng.choice([3, 4, 5, 6, 8]))}}, None
    if kind == 'change':
        return {'rng': {'change_min': float(rng.choice([5, 10, 15, 20, 25]))}}, None
    return {'rng': {'thr_max': float(rng.choice([15, 20, 25, 30, 40]))}}, None


JOIN = ['', '', '', '，', '，且', '，并且', '、', '，同时']


def build_spec(rng, v, n_min, n_max, allow=None, style=None):
    """抽条件并**打乱顺序**后拼成人话（顺序随机是「不同质」的关键一环）。"""
    pool = allow or ['dyn', 'author', 'cipai', 'tail', 'tail_pz', 'pz', 'scene', 'rng']
    k = rng.randint(n_min, min(n_max, len(pool)))
    dims = rng.sample(pool, k)
    spec, phrases, style_used = {}, [], style or rng.choice(STYLE_POOL)
    for d in dims:
        if d == 'dyn':
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
            r, _ = pick_rng(rng)
            spec.update(r)
            phrases.append(ph_rng(rng, spec, style_used))
    rng.shuffle(phrases)
    return spec, ' '.join(phrases), style_used


# ================================================================ 题型族
def gen_1_single(rng, v):
    spec, cond, _ = build_spec(rng, v, 1, 1)
    return spec, 'list', '%s%s的词%s' % (lead_of(rng, 'list'), cond, rng.choice(ASK['list']))


def gen_2_conj(rng, v):
    spec, cond, _ = build_spec(rng, v, 3, 5)
    return spec, 'list', '%s%s 的%s%s' % (lead_of(rng, 'list'), cond,
                                          rng.choice(['词', '作品', '篇目']), rng.choice(ASK['list']))


def gen_3_multi(rng, v):
    which = rng.choice(['tail', 'cipai', 'dynasty', 'author'])
    spec = {}
    if which == 'tail':
        vals = rng.sample(v['tail'], 2)
        spec['tail'] = vals
        d = rng.choice(v['dyn'][:3]) if rng.random() < 0.6 else None
        if d:
            spec['dynasty'] = [d]           # 题面说了朝代，口径就必须带上（防「题面多出条件」）
        q = '%s句脚是「%s」或「%s」的%s%s' % (lead_of(rng, 'list'), vals[0], vals[1],
                                       (dyn_w(d) if d else '词'), rng.choice(ASK['list']))
    elif which == 'cipai':
        vals = rng.sample(v['cipai'], 2)
        d = rng.choice(v['dyn'][:3])
        spec['cipai'] = vals
        spec['dynasty'] = [d]
        q = '%s%s里 %s 或 %s 的%s%s' % (lead_of(rng, 'list'), dyn_w(d, True), vals[0], vals[1],
                                   rng.choice(['词', '作品']), rng.choice(ASK['list']))
    elif which == 'dynasty':
        vals = rng.sample(v['dyn'][:3], 2)
        cp = rng.choice(v['cipai'])
        spec['dynasty'] = vals
        spec['cipai'] = [cp]
        q = '%s%s和%s里的%s%s' % (lead_of(rng, 'list'), dyn_w(vals[0]), dyn_w(vals[1]), cp,
                              rng.choice(ASK['list']))
    else:
        vals = rng.sample(v['author'], 2)
        spec['author'] = vals
        q = '%s%s和%s的作品各有%s' % (lead_of(rng, 'list'), vals[0], vals[1],
                                   rng.choice(['哪些？', '哪几篇？', '什么？', '哪些篇目？']))
    return spec, 'list', q


def gen_4_rng(rng, v):
    r, _ = pick_rng(rng)
    spec = dict(r)
    d = rng.choice(v['dyn'][:3])
    spec['dynasty'] = [d]
    style = rng.choice(STYLE_POOL)
    q = '%s%s%s的%s%s' % (lead_of(rng, 'count'), dyn_w(d, rng.random() < 0.5),
                       ph_rng(rng, spec, style), rng.choice(['词', '作品', '篇目']),
                       rng.choice(ASK['count']))
    return spec, 'count', q


def gen_5_count(rng, v):
    spec, cond, _ = build_spec(rng, v, 2, 4)
    return spec, 'count', '%s%s的%s%s' % (lead_of(rng, 'count'), cond,
                                        rng.choice(['词', '作品', '篇目']), rng.choice(ASK['count']))


METRIC_TEXT = {'ze_ratio': ['仄声比例', '仄字占比', '仄声比重'],
               'ping_ratio': ['平声比例', '平字占比'],
               'han_len': ['全篇字数', '篇幅', '总字数'],
               'sent_n': ['句数', '句子数量'],
               'longest_len': ['最长句长度', '最长的那一句有多长'],
               'change': ['前后段变化值', '变幅', '声情变化幅度'],
               'count': ['作品数', '篇数', '词作数量']}


EXTREME_METRICS = ('ze_ratio', 'ping_ratio', 'han_len', 'sent_n', 'longest_len', 'change')


def gen_6_extreme(rng, v):
    # ⚠ 只用**篇级**指标：`count` 是聚合指标，「哪一首的词作数量最高」语义不通
    spec, cond, _ = build_spec(rng, v, 1, 3)
    m = rng.choice(EXTREME_METRICS)
    spec['_metric'] = m
    updown = rng.choice(['max', 'max', 'min'])
    spec['_dir'] = updown
    mt = rng.choice(METRIC_TEXT[m])
    q = '%s%s的%s里，哪一%s的%s%s？' % (lead_of(rng, 'list'), cond, rng.choice(['词', '作品', '篇目']),
                                   rng.choice(['首', '篇', '阕']), mt,
                                   rng.choice(['最高', '最大']) if updown == 'max'
                                   else rng.choice(['最低', '最小']))
    return spec, 'extreme', q


def gen_7_aggcmp(rng, v):
    gb = rng.choice(['dynasty', 'dynasty', 'author'])
    m = rng.choice(['ze_ratio', 'han_len', 'sent_n', 'count'])
    spec = {}
    mt = rng.choice(METRIC_TEXT.get(m, [m]))
    if gb == 'dynasty':
        vals = rng.sample(v['dyn'][:3], 2)
        spec['_agg'] = {'group_by': 'dynasty', 'values': vals, 'metric': m}
        extra, cond, _ = build_spec(rng, v, 0, 2, allow=['cipai', 'tail', 'scene', 'rng'])
        spec.update(extra)
        pre = ('%s的范围内，' % cond) if extra else ''
        q = '%s%s%s和%s这两组，哪一组的%s更高？' % (lead_of(rng, 'count'), pre, dyn_w(vals[0], True),
                                          dyn_w(vals[1], True), mt)
    else:
        vals = rng.sample(v['author'], 2)
        spec['_agg'] = {'group_by': 'author', 'values': vals, 'metric': m}
        d = rng.choice(v['dyn'][:3])
        spec['dynasty'] = [d]
        q = '%s%s词里，%s与%s相比，谁的%s更大？' % (lead_of(rng, 'count'), dyn_w(d), vals[0], vals[1], mt)
    return spec, 'agg_cmp', q


def gen_8_aggtop(rng, v):
    gb = rng.choice(['author', 'cipai', 'dynasty'])
    m = rng.choice(['count', 'count', 'ze_ratio', 'han_len'])
    ext = rng.choice(['max', 'max', 'min'])
    spec = {'_agg': {'group_by': gb, 'values': None, 'metric': m, 'extreme': ext}}
    # ⚠ 分组维不能同时当筛选维；朝代若要筛选，**必须在拼措辞之前**决定
    #   （旧版先拼措辞、后 setdefault 补朝代 → 203 题题面与口径脱节，制造假缺陷）
    allow = [x for x in ('cipai', 'tail', 'scene') if x != gb]
    extra, cond, _ = build_spec(rng, v, 0, 3, allow=allow)
    if gb != 'dynasty' and rng.random() < 0.6:
        d = rng.choice(v['dyn'][:3])
        extra['dynasty'] = [d]
        cond = ph_dyn(rng, d) + ((' ' + cond) if cond else '')
    spec.update(extra)
    gname = {'author': '词人', 'cipai': '词牌', 'dynasty': '朝代'}[gb]
    pre = ('在%s里，' % cond) if cond else ''
    q = '%s%s哪一个%s的%s%s？' % (lead_of(rng, 'count'), pre, gname,
                             {'count': rng.choice(['词作数量', '作品数']),
                              'ze_ratio': '仄声比例', 'han_len': '篇幅'}[m],
                             rng.choice(['最多', '居首']) if ext == 'max' else rng.choice(['最少', '垫底']))
    return spec, 'agg_top', q


def gen_9_pair(rng, v):
    spec, cond, _ = build_spec(rng, v, 0, 2, allow=['dynasty', 'cipai'])
    if not spec.get('dynasty'):                      # 同上：口径与措辞必须同步
        d = rng.choice(v['dyn'][:3])
        spec['dynasty'] = [d]
        cond = ph_dyn(rng, d) + ((' ' + cond) if cond else '')
    spec['_pair'] = {'dims': ('tone',)}
    dim = rng.choice(['平仄', '声律', '声调', '音律', '平仄谱'])
    q = '%s%s中%s找出几对每个位置上的字%s都相同的两首词' % (
        lead_of(rng, 'list'), cond, rng.choice(['', '，', '请', '麻烦']), dim)
    return spec, 'pair', q


def gen_10_scene(rng, v):
    spec, cond, _ = build_spec(rng, v, 0, 2, allow=['dynasty', 'cipai', 'rng'])
    spec['scene'] = rng.choice(v['scene'])
    if not spec.get('dynasty'):                      # 必须在拼措辞**之前**补，否则题面无朝代却按朝代算
        d = rng.choice(v['dyn'][:3])
        spec['dynasty'] = [d]
        cond = ph_dyn(rng, d) + ((' ' + cond) if cond else '')
    txt = ' '.join(x for x in (cond, ph_scene(rng, spec['scene'])) if x)
    q = '%s%s的%s%s' % (lead_of(rng, 'count'), txt, rng.choice(['词', '作品']), rng.choice(ASK['count']))
    return spec, 'count', q


def gen_11_pz(rng, v):
    spec, cond, _ = build_spec(rng, v, 0, 2, allow=['dynasty', 'cipai'])
    spec['pz'] = rng.choice(v['pz'])
    if not spec.get('dynasty'):                      # 同上：措辞与口径必须同步
        d = rng.choice(v['dyn'][:3])
        spec['dynasty'] = [d]
        cond = ph_dyn(rng, d) + ((' ' + cond) if cond else '')
    txt = ' '.join(x for x in (cond, ph_pz(rng, spec['pz'])) if x)
    q = '%s%s的%s%s' % (lead_of(rng, 'list'), txt, rng.choice(['词', '作品']), rng.choice(ASK['list']))
    return spec, 'list', q


VAGUE = ['清词里最好的是哪一首？', '唐诗里最有名的五言绝句是哪首？',
         '纳兰性德词的中心思想是什么？', '为什么宋词的仄声比例比清词高？',
         '清词里哪一首意境最美？', '帮我推荐几首经典的清词',
         '朱彝尊的词表达了什么感情？', '这首词的修辞手法是什么？',
         '清代哪位词人的成就最高？', '辛弃疾的豪放风格体现在哪里？',
         '哪一首清词最值得背诵？', '宋词和元曲哪个更有文学价值？',
         '清词的艺术特色是什么？', '这首词好在哪里？',
         '元曲为什么会衰落？', '清词与宋词相比有什么不同？']


def gen_12_edge(rng, v):
    k = rng.choice(['zero', 'zero', 'zero', 'outside', 'outside', 'badrange', 'vague', 'vague'])
    if k == 'zero':
        ch = rng.choice(['龘', '龖', '鑫', '淼', '㐀'])
        d = rng.choice(v['dyn'][:3])
        q = rng.choice([
            '%s句脚是「%s」的%s%s' % (lead_of(rng, 'list'), ch, dyn_w(d), rng.choice(ASK['list'])),
            '%s%s里句脚为「%s」的%s' % (lead_of(rng, 'list'), dyn_w(d, True), ch, rng.choice(ASK['list'])),
            '帮我找句脚是「%s」的%s%s' % (ch, dyn_w(d), rng.choice(ASK['list'])),
            '%s句末字是%s的%s%s' % (lead_of(rng, 'list'), ch, dyn_w(d), rng.choice(ASK['list'])),
        ])
        return {'dynasty': [d], 'tail': [ch]}, 'refuse', q
    if k == 'outside':
        d = rng.choice(['唐', '明', '汉', '五代', '隋', '魏晋', '南北朝', '金', '辽', '先秦'])
        cp = rng.choice(v['cipai'])
        q = rng.choice(['%s%s的词平仄如何？' % (d, cp), '%s里的%s词有哪些？' % (d, cp),
                        '统计%s%s的词作数量' % (d, cp), '%s%s中仄声比例最高的是哪一首？' % (d, cp),
                        '帮我看看%s%s的句数分布' % (d, cp), '%s诗与清词相比哪个体仄声占比更高？' % d,
                        '%s词里句脚是「愁」的有多少篇？' % d, '%s人写的%s在库里有多少？' % (d, cp)])
        return {'_unsupported': True}, 'refuse', q
    if k == 'badrange':
        a, b = rng.choice([(8, 5), (20, 3), (100, 40)])
        d = rng.choice(v['dyn'][:3])
        q = rng.choice(['句数在%s到%s之间的%s词有哪些？' % (a, b, d),
                        '%s词里句数%s到%s句的有几篇？' % (d, a, b)])
        return {'dynasty': [d], 'rng': {}}, 'badrange', q
    return {'_vague': True}, 'vague', rng.choice(VAGUE)


CATS = [
    ('单条件检索', gen_1_single, 60),
    ('多条件合取', gen_2_conj, 140),
    ('多值并列', gen_3_multi, 80),
    ('数值/区间', gen_4_rng, 140),
    ('计数+多条件', gen_5_count, 110),
    ('极值+前置条件', gen_6_extreme, 110),
    ('聚合对比+前置条件', gen_7_aggcmp, 80),
    ('组内极值+前置条件', gen_8_aggtop, 100),
    ('配对', gen_9_pair, 40),
    ('声情/派生量', gen_10_scene, 60),
    ('声律模式', gen_11_pz, 40),
    ('边界/负面', gen_12_edge, 40),
]

# ================================================================ 独立真值口径
# ⚠ 口径声明（写进审查报告，避免「拿实现当真理」）：
#   · 声律模式按**子串**算 —— 官方答案集是按实现（`l.pz LIKE '%pat%'`）冻结的，子串即契约；
#     「整句全等」是另一种读法，标注为**待主人裁定的语义歧义**。
#   · 句脚平仄 = 该行平仄串的**最后一个字符**（`substr(pz,-1,1)`），与契约一致。
_RNG_COL = {'ze_min': ('ze_ratio', '>='), 'ze_max': ('ze_ratio', '<='),
            'len_min': ('han_len', '>='), 'len_max': ('han_len', '<='),
            'sent_min': ('sent_n', '>='), 'sent_max': ('sent_n', '<='),
            'change_min': ('change', '>='), 'change_max': ('change', '<='),
            'thr_min': ('threshold', '>='), 'thr_max': ('threshold', '<=')}


def spec_where(spec):
    """spec → (WHERE 片段, 参数)。**独立于 solve/ 实现**，只依赖库表结构。"""
    w, a = [], []
    for key, col in (('dynasty', 'p.dynasty'), ('author', 'p.author'), ('cipai', 'p.cipai')):
        v = spec.get(key)
        if v:
            w.append('%s IN (%s)' % (col, ','.join('?' * len(v))))
            a.extend(v)
    if spec.get('scene'):
        w.append('p.scene = ?')
        a.append(spec['scene'])
    r = spec.get('rng') or {}
    for k, (col, op) in _RNG_COL.items():
        if k in r:
            w.append('p.%s %s ?' % (col, op))
            a.append(r[k])
    if spec.get('tail'):
        w.append('p.pid IN (SELECT pid FROM lines WHERE tail IN (%s))'
                 % ','.join('?' * len(spec['tail'])))
        a.extend(spec['tail'])
    if spec.get('tail_pz'):
        w.append('p.pid IN (SELECT pid FROM lines WHERE substr(pz, -1, 1) = ?)')
        a.append(spec['tail_pz'])
    if spec.get('pz'):
        w.append('p.pid IN (SELECT pid FROM lines WHERE pz LIKE ?)')
        a.append('%' + spec['pz'] + '%')
    return (' AND '.join(w) or '1=1'), a


def count_hits(conn, spec):
    w, a = spec_where(spec)
    return conn.execute('SELECT COUNT(*) FROM poems p WHERE ' + w, a).fetchone()[0]


def n_groups(conn, spec, group_by):
    col = {'author': 'p.author', 'cipai': 'p.cipai', 'dynasty': 'p.dynasty'}[group_by]
    w, a = spec_where(spec)
    return conn.execute('SELECT COUNT(*) FROM (SELECT %s FROM poems p WHERE %s AND %s IS NOT NULL '
                        'AND %s != "" GROUP BY %s HAVING COUNT(*) >= 3)'
                        % (col, w, col, col, col), a).fetchone()[0]


def answerable(conn, spec, task, cat, intent):
    if cat == '边界/负面':
        return True
    if intent.get('_agg'):
        return n_groups(conn, spec, intent['_agg']['group_by']) >= 2
    n = count_hits(conn, spec)
    if n < 1 or n > 8000:
        return False
    if task == 'pair' and n < 4:
        return False
    return True


POLITE_RE = re.compile(r'(麻烦|请帮我|帮我|我想找|劳驾|请问|问一下|查一下|想看看|请统计|给我个结果)')
PUNC_RE = re.compile(r'[\s，。？、（）()「」“”%？＝]')


def norm_key(q):
    return POLITE_RE.sub('', PUNC_RE.sub('', q))


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
    ap.add_argument('--max-prefix', type=int, default=12, help='同一前 4 字最多允许多少题')
    ap.add_argument('--max-sim', type=float, default=0.75,
                    help='与任何已收题的最大字符二元组 Jaccard（超了重掷，防「换汤不换药」）')
    args = ap.parse_args()

    rng = random.Random(args.seed)
    conn = sqlite3.connect(args.db)
    v = load_vocab(conn)

    rows, seen, seen_norm, pref, bags = [], set(), set(), {}, []
    qid = 0
    for cat, fn, quota in CATS:
        made, tries = 0, 0
        while made < quota and tries < quota * 800:
            tries += 1
            spec, task, q = fn(rng, v)
            q = q.strip()
            if q in seen:
                continue
            nk = norm_key(q)
            if nk in seen_norm:                       # 归一化去重：换汤不换药也要弃
                continue
            p4 = nk[:4]
            if pref.get(p4, 0) >= args.max_prefix:     # 句首封顶：防措辞骨架雷同
                continue
            bg = _bigr(q)
            if any(_jac(bg, x) >= args.max_sim for x in bags):   # 相似度封顶
                continue
            pub = {k: val for k, val in spec.items() if not k.startswith('_')}
            intent = {k: val for k, val in spec.items() if k.startswith('_')}
            if not answerable(conn, pub, task, cat, intent):
                continue
            seen.add(q)
            seen_norm.add(nk)
            pref[p4] = pref.get(p4, 0) + 1
            bags.append(bg)
            qid += 1
            rows.append({'id': 'Q%04d' % qid, 'cat': cat, 'task': task, 'q': q,
                         'spec': pub, 'intent': intent})
            made += 1
        assert made == quota, '%s 只造出 %d/%d' % (cat, made, quota)

    assert len(rows) == 1000, len(rows)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('已生成 %d 题 → %s' % (len(rows), args.out))
    from collections import Counter
    for c, n in Counter(r['cat'] for r in rows).items():
        print('  %-14s %d' % (c, n))
    print('  归一化后仍重复：0（生成时已按归一化去重）')
    print('  同一前 4 字最大簇：%d（上限 %d）' % (max(pref.values()), args.max_prefix))


if __name__ == '__main__':
    main()
