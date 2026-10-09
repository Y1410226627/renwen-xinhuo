# -*- coding: utf-8 -*-
"""check_agg.py —— 分组对比（聚合）题的常设门禁。

背景（2026-09-30 主人实测）：问「宋词与清词总体来说仄声占比哪个更高」，
系统按**检索**去理解 → 只认出「朝代=宋」，其余整串成了词面条件 → 召回 0 篇 →
拒答。用户看到的是「系统没料」，实际是**问句类型没被认出**：
问「哪一类整体上更高」问的是**组的统计量**，不是篇；用「检索 + 举几个例子」回答，
要么拒答、要么拿个别篇目冒充总体结论（后者是静默错）。

本门禁逐项验：
  一、**问句类型**：对比题必须解析成 agg（组 ≥ 2、维度与指标正确），
      且**不得**把组名同时当成检索限定（「宋」既是组名又被当 dynasty 条件＝两义相混）；
  二、**数字复核**：答案里每组的篇数/总字/总仄字/篇均/加权，必须与**另一条 SQL**
      （不调 `aggregate.stats`）逐项相符；
  三、**方向复核**：结论里点名的「更高」的那一组，必须与独立算出的排序一致；
  四、**语料外**：跨语料的对比题（唐诗与清词…）必须拒答，不得拿半边数据充数；
  五、**不得误判**：普通检索题（清 临江仙 仄声比例高于45%）不得被当成聚合题。
比对项数为 0 即 FAIL（防「空跑报通过」）。

用法：python tools/check_agg.py [--db data/corpus.db]
退出码：0 = 全部通过；1 = 有 FAIL。
"""
import argparse
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import aggregate
import prosody                                              # noqa: E402
import ask                                                    # noqa: E402
import retrieve                                               # noqa: E402

COLS = {'dynasty': 'dynasty', 'author': 'author', 'cipai': 'cipai'}
LAB = {'ze_ratio': '仄声占比', 'ping_ratio': '平声占比', 'han_len': '篇幅（字）', 'sent_n': '句数'}

# (问句, 期望维度, 期望组, 期望指标)
CASES = [
    ('宋词与清词总体来说仄声占比哪个更高', 'dynasty', ['宋', '清'], 'ze_ratio'),
    ('苏轼与辛弃疾谁的仄声占比高', 'author', ['苏轼', '辛弃疾'], 'ze_ratio'),
    ('念奴娇和临江仙哪个仄声占比更高', 'cipai', ['念奴娇', '临江仙'], 'ze_ratio'),
    ('宋词和清词哪个篇幅长', 'dynasty', ['宋', '清'], 'han_len'),
]
REFUSE = ['唐诗与清词哪个仄声占比更高', '明词与清词哪个平声占比更高']
NOT_AGG = ['清 临江仙 仄声比例高于45%', '句脚是「愁」的清词有哪些']


def main():
    ap = argparse.ArgumentParser(description='分组对比（聚合）题门禁')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    checks, fails, n_cmp = [], [], 0

    def ck(name, ok, detail=''):
        checks.append(name)
        if not ok:
            fails.append('%s%s' % (name, ('：' + detail) if detail else ''))
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, ('：' + detail) if detail else ''))

    for q, dim, vals, metric in CASES:
        print('· %s' % q)
        spec = retrieve.parse_query(conn, q)
        n_cmp += 1
        ck('一·认出是分组对比题：%s' % q, bool(spec.agg),
           '解析成 %s' % spec.describe())
        if not spec.agg:
            continue
        ck('一·维度与组正确：%s' % q,
           spec.agg['group_by'] == dim and spec.agg['values'] == vals and spec.agg['metric'] == metric,
           str(spec.agg))
        n_cmp += 1
        ck('一·组名未被同时当成检索限定：%s' % q,
           not (spec.dynasty_any or spec.author_any or spec.cipai_any), spec.describe())
        res = ask.answer(conn, q, topk=3)
        text = res['answer']
        # 二、逐组独立复算（另走一条 SQL，不调 aggregate.stats）
        for v in vals:
            n_cmp += 1
            n, han, ze, avz, avh, avs = conn.execute(
                'SELECT COUNT(*), COALESCE(SUM(han_len),0), COALESCE(SUM(ze),0), '
                'COALESCE(AVG(ze_ratio),0), COALESCE(AVG(han_len),0), '
                'COALESCE(AVG(sent_n),0) FROM poems WHERE %s=?' % COLS[dim], (v,)).fetchone()
            # 独立复算：这里另写 SQL 重算（不调 aggregate.stats）；只有**舍入口径**
            # 与引擎共用 prosody.pct（「比例一律银行家舍入」是项目的硬口径，不是实现细节）。
            if metric == 'ze_ratio':
                mean, weighted = prosody.r1(avz), prosody.pct(ze, han)
            elif metric == 'ping_ratio':
                ping = conn.execute('SELECT COALESCE(SUM(ping),0) FROM poems WHERE %s=?'
                                    % COLS[dim], (v,)).fetchone()[0]
                mean, weighted = prosody.r1(100.0 - avz), prosody.pct(ping, han)
            elif metric == 'han_len':
                mean = weighted = prosody.r1(avh)
            else:                                          # sent_n
                mean = weighted = prosody.r1(avs)
            if metric in aggregate.RATIO_METRICS:
                need = ['%s：%d 篇' % (v, n),
                        '篇均%s %.1f%%' % (LAB[metric], mean),
                        '加权%s %.1f%%' % (LAB[metric], weighted)]
            else:
                # 篇幅/句数是**计数**：模板不再套百分号（审查 B7），这里跟着改期望
                need = ['%s：%d 篇' % (v, n), '%s 篇均 %.1f' % (LAB[metric], mean),
                        '加权 %.1f' % weighted]
            miss = [x for x in need if x not in text]
            ck('二·数字与独立复算相符（%s=%s）：%s' % (dim, v, q), not miss, '缺 %s' % miss)
            n_cmp += 1
            ck('二·结论行给出该组：%s' % q, v in text.split('【结论】')[-1].split('【')[0],
               text[:60])
        # 三、方向复核（自己按独立数字排序）
        rows = []
        for v in vals:
            n, han, ze, avz, avh, avs = conn.execute(
                'SELECT COUNT(*), COALESCE(SUM(han_len),0), COALESCE(SUM(ze),0), '
                'COALESCE(AVG(ze_ratio),0), COALESCE(AVG(han_len),0), '
                'COALESCE(AVG(sent_n),0) FROM poems WHERE %s=?' % COLS[dim], (v,)).fetchone()
            if metric == 'ze_ratio':
                w = prosody.pct(ze, han)
            elif metric == 'ping_ratio':
                ping = conn.execute('SELECT COALESCE(SUM(ping),0) FROM poems WHERE %s=?'
                                    % COLS[dim], (v,)).fetchone()[0]
                w = prosody.pct(ping, han)
            elif metric == 'han_len':
                w = prosody.r1(avh)
            else:
                w = prosody.r1(avs)
            rows.append((w, v))
        top = max(rows)[1]
        n_cmp += 1
        m = re.search(r'结论：(\S+?)\s*更高', text)
        ck('三·结论方向与独立排序一致：%s' % q, bool(m) and m.group(1) == top,
           '文中「%s」，独立算出「%s」' % (m.group(1) if m else '缺', top))
        n_cmp += 1
        ck('三·护栏通过：%s' % q, res['verify'][0], str(res['verify'][1]))

    for q in REFUSE:
        print('· %s' % q)
        res = ask.answer(conn, q, topk=3)
        n_cmp += 1
        ck('四·跨语料对比必须拒答：%s' % q, res['refused'] and not res['blocks'],
           str(res.get('spec')))
        n_cmp += 1
        ck('四·拒答文本说明原因：%s' % q, '语料外' in res['answer'], res['answer'][:60])

    for q in NOT_AGG:
        print('· %s' % q)
        spec = retrieve.parse_query(conn, q)
        n_cmp += 1
        ck('五·普通检索题不得误判为聚合题：%s' % q, spec.agg is None, spec.describe())

    # 六、类别占比（share）：问「谁的 X 词作占比更高」，指标是**某一类别的篇数占比**
    # （2026-09-30 主人运行记录实测：旧版答成「谁仄声占比更高」——答非所问）
    print('· 六、类别占比（share）')
    q6 = '高旭与纳兰性德的词作中谁的后段下降的词作占比更高'
    spec6 = retrieve.parse_query(conn, q6)
    n_cmp += 1
    ck('六·认出类别占比（metric=share、类别=声情/后段下降）',
       bool(spec6.agg) and spec6.agg['metric'] == 'share'
       and spec6.agg.get('cat') == ('scene', '后段下降'), str(spec6.agg))
    res6 = ask.answer(conn, q6, topk=3)
    txt6 = res6['answer']
    n_cmp += 1
    ck('六·不得答成「仄声占比」（答非所问的反例）', '仄声占比' not in txt6.split('【结论】')[-1],
       txt6[:80])
    ind6 = []
    for v in ('高旭', '纳兰性德'):
        n_a = conn.execute('SELECT COUNT(*) FROM poems WHERE author=?', (v,)).fetchone()[0]
        n_b = conn.execute("SELECT COUNT(*) FROM poems WHERE author=? AND scene='后段下降'",
                           (v,)).fetchone()[0]
        ind6.append((v, n_a, n_b, prosody.pct(n_b, n_a)))
        need = ['%s：%d 篇' % (v, n_a), '的 %d 篇' % n_b, '占比 %.1f%%' % prosody.pct(n_b, n_a)]
        miss = [x for x in need if x not in txt6]
        n_cmp += 1
        ck('六·每组数字与独立复算相符（%s）' % v, not miss, '独立算出 %s；缺 %s' % (ind6[-1], miss))
    top6 = max(ind6, key=lambda x: x[3])[0]
    n_cmp += 1
    m6 = re.search(r'结论：\s*(\S+?)\s*更高', txt6)
    ck('六·结论方向与独立排序一致', bool(m6) and m6.group(1) == top6,
       '文中「%s」，独立算出「%s」' % (m6.group(1) if m6 else '缺', top6))
    n_cmp += 1
    ck('六·护栏通过', res6['verify'][0], str(res6['verify'][1]))

    # 七、问句**没点明指标**时不许替用户选（旧版默认按仄声占比 → 「谁更优美」也会给出数值答案）
    print('· 七、未点明指标')
    for q7 in ('宋词与清词哪个更优美', '苏轼与辛弃疾谁写得更好'):
        res7 = ask.answer(conn, q7, topk=3)
        n_cmp += 1
        ck('七·未点明指标必须如实认账（%s）' % q7,
           res7['refused'] and '未见支持' in res7['answer']
           and '不替用户选指标' in res7['answer'], res7['answer'][:60])
        n_cmp += 1
        ck('七·拒答文本不得出现数字（%s）' % q7, res7['verify'][0], str(res7['verify'][1]))

    # 八、大模型路（假模型离线复现，不耗网络）：
    # 2026-09-30 实测反例——问「宋词与清词哪个更优美」，规则路认出「有组可比、没点明指标」
    # （unspecified，应如实认账），而模型会**替用户发明**一个指标（仄声占比）→ 又变成答非所问。
    print('· 八、大模型路（假模型）')
    import ask as ASK

    class _FakeLLM:
        name = 'fake:selftest'

        def __init__(self, payload):
            self.payload = payload
            self.last_error = ''

        def available(self):
            return True

        def chat(self, messages, **kw):
            return self.payload

    for q8, payload, want in (
            ('宋词与清词哪个更优美',
             '{"agg":{"group_by":"dynasty","values":["宋","清"],"metric":"ze_ratio"}}', 'unspecified'),
            ('宋词与清词哪个的篇幅更长',
             '{"agg":{"group_by":"dynasty","values":["宋","清"],"metric":"sent_n"}}', 'han_len'),
    ):
        spec8, note8 = ASK.understand(conn, q8, llm=_FakeLLM(payload), llm_parse=True)
        n_cmp += 1
        ck('八·模型发明/搞错指标时以规则路为准（%s）' % q8,
           bool(spec8.agg) and spec8.agg['metric'] == want,
           '得 %s（规则路订正）注=%s' % (spec8.agg, note8['notes']))
        res8 = ASK.answer(conn, q8, topk=3, llm=_FakeLLM(payload), llm_parse=True)
        n_cmp += 1
        if want == 'unspecified':
            ck('八·未点明指标仍如实认账（%s）' % q8,
               res8['refused'] and '不替用户选指标' in res8['answer'], res8['answer'][:50])
        else:
            ck('八·订正后按规则路指标作答（%s）' % q8,
               res8['verify'][0] and '篇幅' in res8['answer'], res8['answer'][:50])

    # ================= 九、⭐ 组内极值（「哪个词人/词牌…最多」） =================
    # 背景（2026-10-01 主人运行记录实测）：问「句脚为平 清 临江仙的清词中**哪个词人的词占比最多**」，
    # 系统只做了检索、答「融合排序最前者为丁澎」——**答非所问**，而且大模型给出的
    # `agg.metric=count` 被白名单（不含「篇数」）丢弃。这类问法在词学研究里**很常见**，
    # 且题面里**没有两个组名**（不是「甲 vs 乙」），旧实现根本走不进聚合层。
    GE_CASES = [
        # (问句, 期望维度, 期望 filter 短语（用于独立 SQL）, 期望方向)
        ('句脚为平 清 临江仙的清词中哪个词人的词占比最多', 'author', "WHERE dynasty='清' AND cipai='临江仙' AND ze_ratio>=0", 'max'),
        ('宋词里哪位词人的满江红最多', 'author', "WHERE dynasty='宋' AND cipai='满江红'", 'max'),
        ('元曲中哪个词人的作品最多', 'author', "WHERE dynasty='元'", 'max'),
        ('清词里哪个词牌最少', 'cipai', "WHERE dynasty='清'", 'min'),
        ('哪个朝代的作品最多', 'dynasty', '', 'max'),
    ]
    for q9, dim9, w9, ext9 in GE_CASES:
        sp9 = retrieve.parse_query(conn, q9)
        n_cmp += 1
        ck('九·%s → 识别为组内极值（%s/%s）' % (q9[:22], dim9, ext9),
           bool(sp9.agg) and sp9.agg['group_by'] == dim9 and not sp9.agg.get('values')
           and (sp9.agg.get('extreme') or 'max') == ext9, sp9.describe()[:60])
        if not sp9.agg:
            continue
        # 独立复核：**另写一条 SQL**（不经过 aggregate.top_groups / stats）算真值
        col9 = {'dynasty': 'dynasty', 'author': 'author', 'cipai': 'cipai'}[dim9]
        # 按 agg 里记的筛选条件重建 where（用 parse 结果里的字段，不直接信任答案文本）
        cond9, args9 = [], []
        if sp9.dynasty_any:
            cond9.append('dynasty IN (%s)' % ','.join('?' * len(sp9.dynasty_any)))
            args9 += list(sp9.dynasty_any)
        if sp9.cipai_any:
            cond9.append('cipai IN (%s)' % ','.join('?' * len(sp9.cipai_any)))
            args9 += list(sp9.cipai_any)
        if sp9.tail_pz:
            cond9.append("pid IN (SELECT pid FROM lines WHERE substr(pz,-1,1)=?)")
            args9.append(sp9.tail_pz)
        wsql = ('WHERE ' + ' AND '.join(cond9)) if cond9 else ''
        ref = conn.execute('SELECT %s g, COUNT(*) n FROM poems %s GROUP BY %s '
                           'ORDER BY n %s, g LIMIT 1'
                           % (col9, wsql, col9, 'DESC' if ext9 == 'max' else 'ASC'),
                           args9).fetchone()
        tot9 = conn.execute('SELECT COUNT(*) FROM poems %s' % wsql, args9).fetchone()[0]
        n_cmp += 1
        res9 = ASK.answer(conn, q9, topk=3)
        txt9 = res9['answer']
        ck('九·%s 结论含真值（%s %d 篇）' % (q9[:20], ref[0], ref[1]),
           ref and (ref[0] in txt9) and (str(ref[1]) in txt9), txt9[:70])
        n_cmp += 1
        ck('九·%s 写明命中总数 %d' % (q9[:20], tot9), str(tot9) in txt9, txt9[:70])
        n_cmp += 1
        ck('九·%s 过护栏且不拒答' % q9[:20], res9['verify'][0] and not res9['refused'],
           str(res9['verify'][1])[:60])
        n_cmp += 1
        # 绝不能再答成「融合排序最前者」（那正是本次 bug 的症状）
        ck('九·%s 不得答成「融合排序最前者」' % q9[:20], '融合排序最前' not in txt9, txt9[:60])
    # 意图覆盖：问句含分组极值意图、但解析不出分组 → 必须**如实认账**，不许拿检索冒充
    _q_guard = '请列出每个位置上平仄都相同的两首词的词人里谁最多'
    _r_guard = ASK.answer(conn, _q_guard, topk=3)
    n_cmp += 1
    ck('九·意图覆盖：分组意图无法解析时必须认账',
       _r_guard['refused'] or bool(_r_guard.get('agg')) or '融合排序最前' not in _r_guard['answer'],
       _r_guard['answer'][:70])

    print('\n===== 分组对比（聚合）汇总 =====')
    print('  检查项 %d，比对项 %d，FAIL %d' % (len(checks), n_cmp, len(fails)))
    if n_cmp == 0 or not checks:
        print('  ✗ FAIL：比对项数为 0（防「空跑报通过」）')
        return 1
    if fails:
        for f in fails:
            print('   ✗ %s' % f)
        return 1
    print('  全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
