# -*- coding: utf-8 -*-
"""check_extreme.py —— 极值／排序题（「哪一首…最高/最低」）的常设门禁。

背景（2026-09-30 主人实测）：问「高旭写的哪首词里仄声字占比最高」，
系统把「最高」当普通词面条件、按**五路融合分**排序，于是把《菩萨蛮》（仄比 38.6%）
说成「排序最前者」——而把条件里的 147 篇按仄比排，第一名是《酷相思·春感》56.1%。
两处错：① 问句类型没被认出（极值题）；② 文案硬写「排序最前者为…」，
**没有任何排序条件时这是一句虚假陈述**。

本门禁逐项验：
  一、**认出极值题**：指标与方向正确（最高/最低、仄比/字数/句数/最长句/变化值），
      且**不得**把指标词与极值词留成词面条件（「高旭写的」里的词人不能被误撤）；
  二、**答案就是极值篇**：展示首篇必须与**另一条 SQL**（不调 retrieve.order_pids）算出的
      极值篇逐项相同：同 pid、同指标值；
  三、**并列如实**：并列篇数必须等于独立复算值；并列篇目要点名（不得说「已一并列入」而实际没列）；
  四、**没指定排序指标时不许说「排序最前」**：普通检索题的结论行必须写明是融合排序；
  五、**不误判**：普通检索题（句脚是「愁」…）不得被当成极值题。

比对项数为 0 即 FAIL（防「空跑报通过」）。
`--selftest`：把 `parse_extreme` 停掉（＝旧行为）后重跑，**必须**至少有若干项 FAIL，
否则说明这套检查根本测不出那个 bug（检测器自身也要自检）。

用法：python tools/check_extreme.py [--db data/corpus.db] [--selftest]
退出码：0 = 全部通过；1 = 有 FAIL。
"""
import argparse
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import ask                                                    # noqa: E402
import retrieve                                               # noqa: E402

# (问句, 限定 SQL 片段(不含 WHERE)、参数、指标列、方向)
CASES = [
    ('高旭写的哪首词里仄声字占比最高', "author = '高旭'", (), 'ze_ratio', 'desc'),
    ('清词中哪首句数最多', "dynasty = '清'", (), 'sent_n', 'desc'),
    ('清词中哪首字数最长', "dynasty = '清'", (), 'han_len', 'desc'),
    ('清 临江仙 哪首仄声比例最高', "dynasty = '清' AND cipai = '临江仙'", (), 'ze_ratio', 'desc'),
    ('高旭的词里哪首仄声比例最低', "author = '高旭'", (), 'ze_ratio', 'asc'),
]
NOT_EXTREME = ['句脚是「愁」的清词有哪些', '清 临江仙 仄声比例高于45%']


class _FakeLLM:
    """假模型：只听得见词人、**把「最高」丢了**（＝2026-09-30 主人实测那个真实输出）。"""
    name = 'fake:selftest'
    last_error = None

    def __init__(self, text):
        self.text = text

    def available(self):
        return True

    def chat(self, messages, **kw):
        return self.text


# (假模型输出, 期望排序指标, 期望方向) —— 大模型路也必须有安全网
LLM_CASES = [
    ('{"authors":["高旭"]}', 'ze_ratio', 'desc'),
    ('{"authors":["高旭"],"unparsed":["最高"]}', 'ze_ratio', 'desc'),
    ('{"order":{"metric":"ze_ratio","dir":"max"},"authors":["高旭"]}',
     'ze_ratio', 'desc'),
]
LLM_ORDER_BAD = ['{"authors":["高旭"],"order":{"metric":"好看程度","dir":"max"}}']


def main():
    ap = argparse.ArgumentParser(description='极值／排序题门禁')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--selftest', action='store_true',
                    help='停掉 parse_extreme（＝旧行为）后重跑，必须报错')
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    conn.row_factory = sqlite3.Row
    checks, fails, n_cmp = [], [], 0

    def ck(name, ok, detail=''):
        checks.append(name)
        if not ok:
            fails.append('%s%s' % (name, ('：' + detail) if detail else ''))
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, ('：' + detail) if detail else ''))

    if a.selftest:
        # 把「认识极值题」这一步停掉＝旧行为：应当全部不认得 → 检查必须报错
        retrieve.parse_extreme = lambda conn, text: None
        print('（自检模式：已停用 parse_extreme，期望出现 FAIL）')

    for q, where, args, col, direction in CASES:
        print('· %s' % q)
        spec = retrieve.parse_query(conn, q)
        n_cmp += 1
        ck('一·认出是极值题：%s' % q, bool(spec.order_by),
           '解析成 %s' % spec.describe())
        n_cmp += 1
        ck('一·指标与方向正确：%s' % q,
           spec.order_by == col and spec.order_dir == direction,
           'order_by=%r dir=%r' % (spec.order_by, spec.order_dir))
        n_cmp += 1
        ck('一·指标词未被留成词面条件：%s' % q,
           not any(('比例' in k or '字数' in k or '句数' in k or '最高' in k or '最低' in k)
                   for k in (spec.keywords or [])), '词面=%s' % (spec.keywords or []))
        # 独立复算（另一条 SQL，不调 retrieve.order_pids / extreme_info）
        agg = 'MAX' if direction == 'desc' else 'MIN'
        sql = 'SELECT %s(%s) FROM poems WHERE %s' % (agg, col, where)
        val = conn.execute(sql, args).fetchone()[0]
        ties = conn.execute(
            'SELECT pid, dynasty, author, title, %s AS v FROM poems WHERE %s AND %s = ? '
            'ORDER BY pid' % (col, where, col), list(args) + [val]).fetchall()
        spec2 = retrieve.parse_query(conn, q)          # 自检模式下这里已无 order_by
        rows = retrieve.search(conn, spec2, topk=3)
        n_cmp += 1
        ck('二·首篇就是极值篇：%s' % q,
           bool(rows) and rows[0]['pid'] == ties[0][0],
           '首篇 %s vs 独立复算 %s' % (rows[0]['pid'] if rows else None, ties[0][0]))
        n_cmp += 1
        key = {'ze_ratio': 'ze_ratio', 'sent_n': 'n_line', 'han_len': 'n_char'}[col]
        ck('二·首篇指标值等于极值：%s' % q,
           bool(rows) and abs(float(rows[0][key]) - float(val)) < 1e-9,
           '%s vs %s' % (rows[0][key] if rows else None, val))
        res = ask.answer(conn, q, topk=3)
        text = res['answer']
        ei = res.get('extreme')
        n_cmp += 1
        ck('三·并列篇数与独立复算一致：%s' % q,
           bool(ei) and ei['n_ties'] == len(ties),
           '文中 %s vs SQL %d' % (ei and ei['n_ties'], len(ties)))
        n_cmp += 1
        need = ('已一并列入' if len(ties) <= len(res['blocks']) else '此处展示前')
        ck('三·并列篇目的表述与实际相符：%s' % q,
           (len(ties) <= 1 and '无并列' in text) or (len(ties) > 1 and need in text),
           text.split('【极值复核】')[-1][:80])
        n_cmp += 1
        ck('四·护栏通过（极值复核行数字有出处）：%s' % q, res['verify'][0],
           str(res['verify'][1][:2]))

    for q in NOT_EXTREME:
        print('· %s' % q)
        spec = retrieve.parse_query(conn, q)
        n_cmp += 1
        ck('五·普通检索题不得误判为极值题：%s' % q, spec.order_by is None, spec.describe())
        res = ask.answer(conn, q, topk=3)
        n_cmp += 1
        ck('四·未指定排序指标时不得写「排序最前」：%s' % q,
           '融合排序最前者' in res['answer'] or res['refused'], res['answer'][:70])

    # 六、大模型理解路也必须把极值意图执行出来（否则旧 bug 换个壳又回来）
    q6 = '高旭写的哪首词里仄声字占比最高'
    _v0 = conn.execute("SELECT MAX(ze_ratio) FROM poems WHERE author='高旭'").fetchone()[0]
    ties0 = conn.execute("SELECT pid FROM poems WHERE author='高旭' AND ze_ratio=? ORDER BY pid",
                         (_v0,)).fetchall()
    for raw, metric, direction in LLM_CASES:
        print('· [大模型路] %s ＋模型输出 %s' % (q6, raw))
        spec6, note6 = ask.understand(conn, q6, llm=_FakeLLM(raw), llm_parse=True)
        n_cmp += 1
        ck('六·模型丢掉极值意图时由规则补回：%s' % raw,
           spec6.order_by == metric and spec6.order_dir == direction,
           'order_by=%r dir=%r 注=%s' % (spec6.order_by, spec6.order_dir, note6['notes']))
        res6 = ask.answer(conn, q6, topk=3, llm=_FakeLLM(raw), llm_parse=True)
        rows6 = res6['blocks']
        n_cmp += 1
        ck('六·答案首篇仍是极值篇：%s' % raw,
           bool(rows6) and rows6[0]['pid'] == ties0[0][0] if ties0 else False,
           '%s vs %s' % (rows6[0]['pid'] if rows6 else None, ties0[0][0] if ties0 else None))
        n_cmp += 1
        ck('六·大模型路的回答不得再写「融合排序最前者」：%s' % raw,
           '融合排序最前者' not in res6['answer'], res6['answer'][:80])
    for raw in LLM_ORDER_BAD:
        print('· [大模型路] 非法指标 %s' % raw)
        spec7, note7 = ask.understand(conn, q6, llm=_FakeLLM(raw), llm_parse=True)
        n_cmp += 1
        ck('六·模型给的非法指标不许落地（回落规则）：%s' % raw,
           spec7.order_by == 'ze_ratio', 'order_by=%r dropped=%s' % (spec7.order_by, note7['dropped']))
        n_cmp += 1
        ck('六·非法指标要如实记进 dropped：%s' % raw,
           any('排序指标' in str(x) for x in note7['dropped']), str(note7['dropped']))

    print('\n===== 极值／排序题汇总 =====')
    print('  检查项 %d，比对项 %d，FAIL %d' % (len(checks), n_cmp, len(fails)))
    if n_cmp == 0 or not checks:
        print('  ✗ FAIL：比对项数为 0（防「空跑报通过」）')
        return 1
    if a.selftest:
        if fails:
            print('  ✓ 自检通过：停用 parse_extreme 后确实报错 %d 项（说明这些检查真能测出旧 bug）'
                  % len(fails))
            for f in fails[:3]:
                print('     · %s' % f)
            return 0
        print('  ✗ 自检失败：停用 parse_extreme 后竟然全部通过——这套检查测不出目标 bug')
        return 1
    if fails:
        for f in fails:
            print('   ✗ %s' % f)
        return 1
    print('  全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
