# -*- coding: utf-8 -*-
"""M8 聚合统计层：**分组对比**（如「宋词与清词总体哪个体仄声占比更高」）。

为什么要单列一层：检索层给的是**篇**，而「总体上哪一类更高」问的是**组的统计量**。
两者是不同的问句类型。用「检索 + 举几个例子」硬凑只有两种下场：
  ① 语义检索召不回 → 拒答（用户看着像系统没料）；
  ② 召回来几篇例句 → 拿个别篇目冒充总体结论（**静默错**，更危险）。
所以这里单独做：在原库上 `GROUP BY` 统计，把「组」当作一等公民。

口径（**两种都算、都写出来**，防止用口径偷换结论）：
  篇均（`mean`）  = 组内各篇指标的算术平均（每篇权重相同）
  加权（`weighted`）= 组内总量之比（如 总仄字 ÷ 总汉字，长词权重更大）
例：宋词与清词的仄声占比，两种口径的高下**可能不同**——不同就照实说「口径不同结论不同」，
不挑一个顺眼的报。数字全部来自 `poems` 表，可由 SQL 独立复算（见 `tools/check_agg.py`）。

用法：
  python aggregate.py --db data/corpus.db --by dynasty --values 宋,清 --metric ze_ratio
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prosody                  # noqa: E402  比例一律走 prosody.pct（Decimal + 银行家舍入）

# 分组维度 → (DB 列, 表头字段名)
GROUPS = {
    'dynasty': ('p.dynasty', '朝代'),
    'author': ('p.author', '词人'),
    'cipai': ('p.cipai', '词牌'),
}
# 指标 → 表头字段名（只在这里登记，别处不得再写一份）
METRICS = {
    'ze_ratio': '仄声占比',
    'ping_ratio': '平声占比',
    'han_len': '篇幅（字）',
    'sent_n': '句数',
    'share': '词作占比',                     # 某一类别的**篇数占比**（如「后段下降的词作占比」）
    'count': '词作篇数',                     # 「哪个词人的词最多」——**「占比最多」在本语境下与篇数同序**
    'unspecified': '（问句未点明统计指标）',   # 没点明就**不替用户选**（审查 B9）
}
# 类别 → (SQL 列, 人话)。只登记做过分组统计的类别列；新类别必须在这里加，不猜。
CATS = {'scene': ('p.scene', '声情')}
# 「占比」类指标有篇均/加权两种口径；计数类指标只有一种（写出来是为了如实说明）
RATIO_METRICS = ('ze_ratio', 'ping_ratio')


def stats(conn, group_by, values, metric='ze_ratio', cat=None):
    """按组算统计量。返回 [{group, n, han, ze, ping, mean, weighted, one, n_hit, share}]。

    `one` = 「该指标只有一种口径」时为真（篇幅/句数/类别占比）；
    `metric='share'` 需要 `cat=(列key, 值)`：统计组内满足该类别（如声情=后段下降）的**篇数占比**。
    比例一律走 `prosody.pct`（Decimal + 银行家舍入），与引擎其它处同口径
    （审查 B12/B13：旧版用 `100.0*ze/han` 与 `100-avz`，会与 `pct()` 差 0.1）。
    """
    if group_by not in GROUPS:
        raise ValueError('未知分组维度：%s' % group_by)
    if metric == 'share':
        if not cat or cat[0] not in CATS:
            raise ValueError('share 指标必须给出已知类别')
    elif metric not in METRICS:
        raise ValueError('未知指标：%s' % metric)
    col = GROUPS[group_by][0]
    rows = []
    for v in values:
        r = conn.execute(
            'SELECT COUNT(*), COALESCE(SUM(p.han_len),0), COALESCE(SUM(p.ze),0), '
            'COALESCE(SUM(p.ping),0), COALESCE(AVG(p.ze_ratio),0), COALESCE(AVG(p.han_len),0), '
            'COALESCE(AVG(p.sent_n),0) '
            'FROM poems p WHERE %s = ?' % col, (v,)).fetchone()
        n, han, ze, ping, avz, avh, avs = [r0 if r0 is not None else 0 for r0 in r]
        n_hit = 0
        if metric == 'share':
            n_hit = conn.execute(
                'SELECT COUNT(*) FROM poems p WHERE %s = ? AND %s = ?' % (col, CATS[cat[0]][0]),
                (v, cat[1])).fetchone()[0]
        w_ze = prosody.pct(ze, han)
        w_ping = prosody.pct(ping, han)                 # 用 SUM(平)/SUM(总)（旧版 100-篇均，不互补）
        mean_avz = prosody.r1(avz)
        mean_avg = prosody.r1(100.0 - avz)
        share = prosody.pct(n_hit, n)
        if metric == 'ze_ratio':
            mean, weighted, one = mean_avz, w_ze, False
        elif metric == 'ping_ratio':
            mean, weighted, one = mean_avg, w_ping, False
        elif metric == 'han_len':
            mean, weighted, one = prosody.r1(avh), prosody.r1((float(han) / n) if n else 0.0), True
        elif metric == 'sent_n':
            mean = weighted = prosody.r1(avs)
            one = True
        elif metric == 'count':
            mean = weighted = float(n)      # 篇数：只有一种口径
            one = True
        else:                                           # share / 其它类别占比
            mean = weighted = share
            one = True
        rows.append({'group': v, 'n': n, 'han': han, 'ze': ze, 'ping': ping,
                     'mean': mean, 'weighted': weighted, 'one': one,
                     'n_hit': n_hit, 'share': share})
    return rows


def scope_stats(conn, group_by, where=None, args=()):
    """范围内的**命中篇数**与**组数**（两者常被混淆：418 篇 ≠ 418 组）。"""
    col = GROUPS[group_by][0]
    w = (' WHERE ' + where) if where else ''
    n_poems = conn.execute('SELECT COUNT(*) FROM poems p' + w, tuple(args)).fetchone()[0] or 0
    n_groups = conn.execute('SELECT COUNT(DISTINCT %s) FROM poems p%s' % (col, w),
                            tuple(args)).fetchone()[0] or 0
    return {'n_poems': n_poems, 'n_groups': n_groups}


def top_groups(conn, group_by, limit=5, metric='count', cat=None, where=None, args=(),
               extreme='max'):
    """**组内极值**：不预先给组名，直接在范围内按组统计，取篇数最多（或最少）的前若干组。

    为什么要这一路：问「句脚为平 清 临江仙的清词中**哪个词人的词最多**」时，
    问句里**根本没有两个组名**（不是「甲 vs 乙」），旧实现只支持「预先给 values 的对比」，
    于是把这类**最常见的研究问题**当成普通检索 → 答非所问（2026-10-01 主人运行记录实测）。
    返回结构与 `stats()` 一致，便于共用渲染与白名单。
    """
    if group_by not in GROUPS:
        raise ValueError('未知分组维度：%s' % group_by)
    if metric not in METRICS:
        raise ValueError('未知指标：%s' % metric)
    col = GROUPS[group_by][0]
    sql = ('SELECT %s AS g, COUNT(*) n, COALESCE(SUM(p.han_len),0), COALESCE(SUM(p.ze),0), '
           'COALESCE(SUM(p.ping),0), COALESCE(AVG(p.ze_ratio),0), COALESCE(AVG(p.han_len),0), '
           'COALESCE(AVG(p.sent_n),0) FROM poems p' % col)
    if where:
        sql += ' WHERE ' + where
    # 排序口径：计数类按篇数；比例/均值类按其均值。**比例类必须设最小篇数门槛**，
    # 否则「只写了 1 篇、那篇恰好 100% 仄」会霸榜——那不是研究结论，是样本噪声。
    order = 'n DESC' if metric == 'count' else (
        'AVG(p.ze_ratio) DESC' if metric == 'ze_ratio' else
        ('AVG(p.ping_ratio) DESC' if metric == 'ping_ratio' else
         ('AVG(p.han_len) DESC' if metric == 'han_len' else 'AVG(p.sent_n) DESC')))
    if extreme == 'min':
        order = order.replace(' DESC', ' ASC')
    min_n = 1 if metric == 'count' else 3
    sql += (' GROUP BY %s HAVING n >= %d ORDER BY %s, g ASC LIMIT ?'
            % (col, min_n, order))
    raw = conn.execute(sql, tuple(args) + (int(limit),)).fetchall()
    # 占比的**分母必须是范围内全部命中篇数**，不是「前 N 组之和」——
    # 否则「占比 32.5%」会把只统计了前 5 组的错觉写进答案（我第一版就写错了，实测发现）。
    _ss = scope_stats(conn, group_by, where, args)
    total = _ss['n_poems']
    out = []
    for g, n, han, ze, ping, avz, avh, avs in raw:
        nh = 0
        if metric == 'share' and cat and cat[0] in CATS:
            nh = conn.execute(
                'SELECT COUNT(*) FROM poems p WHERE %s = ? AND %s = ?' % (col, CATS[cat[0]][0]),
                (g, cat[1])).fetchone()[0]
        share = prosody.pct(nh, n) if metric == 'share' else prosody.pct(n, total)
        if metric == 'count':
            mean = weighted = float(n)
        elif metric == 'share':
            mean = weighted = share
        else:                                   # 其余指标：按需取用（本路主要用于 count）
            mean = weighted = prosody.r1(avz)
        out.append({'group': g, 'n': n, 'han': han, 'ze': ze, 'ping': ping,
                    'mean': mean, 'weighted': weighted, 'one': True,
                    'n_hit': nh, 'share': share})
    return out


def render_top(rows, group_by, metric, extreme='max', scope_text='', n_poems=None, n_groups=None):
    """**组内极值**成文：给出「谁最多/最少」+ 前几名 + 篇数占比。

    数字全部来自 `top_groups`；不使用「」（那只留给语料原文）。
    """
    gl = GROUPS[group_by][1]
    ml = METRICS.get(metric, metric)
    if not rows:
        return ['【结论】在给定条件下没有可统计的组。']
    top = rows[0]
    out = []
    out.append('【结论】按%s分组统计（%s）：命中 %d 篇、涉及 %s 组（下表只列前 %d 组）。'
               % (gl, ml,
                  n_poems if n_poems is not None else sum(r['n'] for r in rows),
                  ('%d' % n_groups) if n_groups is not None else '若干', len(rows)))
    if scope_text:
        out.append('　　　统计范围：条件〔%s〕。' % scope_text)
    _dir = '最多' if extreme == 'max' else '最少'
    if metric == 'count':
        out.append('　　　**%s**的是 %s：%d 篇，占命中篇数的 %.1f%%。'
                   % (_dir, top['group'], top['n'], top['share']))
    else:                                   # 比例/均值类：给出该组的指标值与该组篇数
        out.append('　　　**%s**的是 %s：%s ＝ %.1f（该组 %d 篇；比例类只统计 ≥3 篇的组，'
                   '避免单篇样本噪声）。'
                   % (_dir, top['group'], ml, top['weighted'], top['n']))
    if len(rows) > 1:
        if metric == 'count':
            out.append('　　　其后依次：%s。'
                       % '、'.join('%s %d 篇（%.1f%%）' % (r['group'], r['n'], r['share'])
                                  for r in rows[1:]))
        else:
            out.append('　　　其后依次：%s。'
                       % '、'.join('%s %.1f（%d 篇）' % (r['group'], r['weighted'], r['n'])
                                  for r in rows[1:]))
    out.append('　　　口径说明：占比＝该组篇数 ÷ 命中总篇数；〔占比最多〕与〔篇数最多〕在本语境下同序。')
    return out


def compare(rows, metric='ze_ratio'):
    """谁更高：以**加权口径**为准（长词权重更大，更接近「整体」），
    并核对篇均口径是否同意；不同意就如实标出。"""
    live = [r for r in rows if r['n'] > 0]
    out = {'winner': None, 'loser': None, 'diff_weighted': None,
           'diff_mean': None, 'mean_agrees': None, 'empty': [r['group'] for r in rows if r['n'] == 0]}
    if len(live) < 2:
        return out
    rank = sorted(live, key=lambda r: (-r['weighted'], -r['mean'], r['group']))
    out['winner'], out['loser'] = rank[0], rank[-1]
    out['diff_weighted'] = round(out['winner']['weighted'] - out['loser']['weighted'], 1)
    out['diff_mean'] = round(out['winner']['mean'] - out['loser']['mean'], 1)
    out['mean_agrees'] = (out['winner']['mean'] >= out['loser']['mean'])
    # 平局：两组加权口径差 < 0.05 个百分点（审查 C12：旧版会说「X 更高——高出 0.0」）
    out['tie'] = (len(live) == 2) and (abs(out['diff_weighted']) < 0.05)
    return out


def numbers(rows, cmp_):
    """聚合回答里出现的**全部数字**（供护栏③放行：每个数字都要有出处）。"""
    out = []
    for r in rows:
        out += [r['n'], r['han'], r['ze'], r['mean'], r['weighted'],
                r.get('n_hit', 0), r.get('share', 0.0)]
    for k in ('diff_weighted', 'diff_mean'):
        if cmp_.get(k) is not None:
            out.append(abs(cmp_[k]))
    return out


def render(rows, cmp_, group_by, metric, cat=None):
    """成文（确定性模板；数字全部来自 `stats`）。**不使用「」**——那只留给语料原文。"""
    gl = GROUPS[group_by][1]
    if metric == 'unspecified':
        return ['【结论】问句没有点明要统计的指标，本系统**不替用户选指标**。',
                '　　　可用指标：仄声占比、平声占比、篇幅（字）、句数，或某一类词作（如声情「后段下降」）的篇数占比。',
                '　　　请指明指标后再问（例如「宋词与清词哪个的仄声占比更高」）。']
    if metric == 'share':
        ml = '%s的词作占比' % (cat[1] if cat else '')
    else:
        ml = METRICS[metric]
    two = metric in RATIO_METRICS
    out = ['【结论】按%s分组统计〔%s〕%s：'
           % (gl, ml, '（两种口径：篇均＝各篇指标平均；加权＝组内总量之比）' if two else
              ('（口径：组内该类别的篇数 ÷ 组内篇数）' if metric == 'share' else
               '（合计类指标只有一种口径）'))]
    for r in rows:
        if r['n'] == 0:
            out.append('　　　%s：0 篇（本语料未收录，未参与比较）' % r['group'])
            continue
        if metric == 'share':
            seg = ('　　　%s：%d 篇，其中声情为〔%s〕的 %d 篇，占比 %.1f%%'
                   % (r['group'], r['n'], cat[1] if cat else '', r['n_hit'], r['share']))
        elif two:
            seg = ('　　　%s：%d 篇，总 %d 字，总仄字 %d，篇均%s %.1f%%'
                   % (r['group'], r['n'], r['han'], r['ze'], ml, r['mean']))
            seg += '，加权%s %.1f%%' % (ml, r['weighted'])
        else:
            # 审查 B7：篇幅/句数是**计数**，旧模板硬套 `%.1f%%` 会写成「篇均篇幅（字）67.1%」
            seg = ('　　　%s：%d 篇，总 %d 字，%s 篇均 %.1f、加权 %.1f'
                   % (r['group'], r['n'], r['han'], ml, r['mean'], r['weighted']))
        out.append(seg)
    if cmp_['winner'] is None:
        out.append('结论：可比的组不足两组，本次不作比较。')
    elif len(rows) > 2:                      # 审查 C11：3 组以上要给完整次序
        order = sorted([r for r in rows if r['n'] > 0], key=lambda r: -r['weighted'])
        out.append('结论：%s 最高；完整次序（按%s口径）：%s。'
                   % (order[0]['group'], '加权',
                      ' > '.join('%s %.1f' % (r['group'], r['weighted']) for r in order)))
    else:
        w, l = cmp_['winner'], cmp_['loser']
        if cmp_.get('tie'):
            out.append('结论：%s 与 %s **持平**（加权口径差 0.0 个百分点，两种口径都不足以分出高下）。'
                       % (w['group'], l['group']))
        elif two:
            agree = '两种口径一致' if cmp_['mean_agrees'] else \
                '注意：两种口径不一致（篇均指向 %s、加权指向 %s）——结论随口径变化，须写明口径' \
                % (l['group'] if cmp_['diff_mean'] < 0 else w['group'], w['group'])
            dm = cmp_['diff_mean']
            out.append('结论：%s 更高——加权口径高出 %.1f 个百分点，篇均口径%s %.1f 个百分点（%s）。'
                       % (w['group'], abs(cmp_['diff_weighted']),
                          '高出' if dm >= 0 else '低出', abs(dm), agree))
        else:
            out.append('结论：%s 更高（高出 %.1f）。' % (w['group'], abs(cmp_['diff_weighted'])))
    if cmp_['empty']:
        # 审查 B8：这里原先用「」包类别名，会被引用护栏当成「凭空引文」→ 整段回答判失败
        out.append('　　　注：%s 在本语料中 0 篇，不是「更低」而是没有可比数据。'
                   % '、'.join(cmp_['empty']))
    out.append('【口径说明】本次统计覆盖该组全部词作（不是抽样、不是举例）；'
               '数字可由 SQL 在原库上独立复算（见 tools/check_agg.py），'
               '结论只描述形式统计，不涉及作者意图与作品优劣。')
    return out


def main():
    ap = argparse.ArgumentParser(description='分组对比统计（确定性）')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--by', default='dynasty', choices=sorted(GROUPS))
    ap.add_argument('--values', required=True, help='逗号分隔的组名，如 宋,清')
    ap.add_argument('--metric', default='ze_ratio',
                    choices=[k for k in sorted(METRICS) if k != 'unspecified'])
    ap.add_argument('--cat', default=None, help='share 指标的类别值，如 后段下降')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    vals = [v.strip() for v in a.values.replace('，', ',').split(',') if v.strip()]
    cat = ('scene', a.cat) if (a.metric == 'share' and a.cat) else None
    rows = stats(conn, a.by, vals, a.metric, cat)
    cmp_ = compare(rows, a.metric)
    if a.json:
        print(json.dumps({'rows': rows, 'cmp': cmp_}, ensure_ascii=False, indent=2))
    else:
        print('\n'.join(render(rows, cmp_, a.by, a.metric, cat)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
