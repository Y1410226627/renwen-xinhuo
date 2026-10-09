# -*- coding: utf-8 -*-
"""check_pair.py —— 「配对题」门禁：找出几对逐位平仄相同的两首词（含独立复算与护栏）。

为什么要单独一条门禁：配对题是**第三类**被主人实测抓到的错法（前两类是「答非所问」与「极值题」）。
旧版把问句当普通条件题，大模型甚至从问句本身捏出一条声律模式去筛篇——答案与问题毫无关系。
这条门禁盯住七件事：
  一、认出配对题（且不把问句本身当词面/声律条件）；
  二、组数与对数用**Python 侧另一条实现**复算一致；
  三、展示的每一对**逐位**比对（位位数、不同位数）——不能只说「相同」；
  四、护栏通过；
  五、普通检索题/极值题不得被误判为配对题；
  六、大模型理解路（假模型离线复现）也必须落到规则路；
  七、「字面相同」这类未实现的维度必须**认账**（拒答），不许拿平仄冒充。

用法：python tools/check_pair.py [--db data/corpus.db] [--selftest]
退出码：0 = 全过；1 = 有问题（`--selftest` 时反过来：必须报错才算过）。
"""
import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import ask                                                   # noqa: E402
import pairing                                               # noqa: E402
import retrieve                                              # noqa: E402

CMP = [0]
BAD = []


def ck(name, cond, detail=''):
    CMP[0] += 1
    if not cond:
        BAD.append(name + ('：' + str(detail) if detail else ''))
    print('  %s %s%s' % ('ok  ' if cond else 'FAIL', name,
                         ('：' + str(detail)) if detail else ''))


CASES = ['找出几对每个位置上的字平仄都相同的两首词']
NOT_PAIR = ['句脚是「愁」的清词有哪些',
            '高旭写的哪首词里仄声字占比最高',
            '清 临江仙 仄声比例高于45%']


class _FakeLLM:
    """假模型：把问句听成「声律模式」——正是主人实测里那个真实输出。"""
    name = 'fake:pair'
    last_error = None

    def __init__(self, text):
        self.text = text

    def available(self):
        return True

    def chat(self, messages, **kw):
        return self.text


def main():
    ap = argparse.ArgumentParser(description='配对题门禁（逐位平仄相同的两首词）')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--selftest', action='store_true',
                    help='自检：停掉配对识别器，门禁必须报错')
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    if args.selftest:
        pairing.parse_pair = lambda c, t: None            # 注入旧行为：认不出配对题

    for q in CASES:
        print('· %s' % q)
        spec = retrieve.parse_query(conn, q)
        ck('一·认得出配对题（且维度是平仄）',
           bool(getattr(spec, 'pair', None)) and spec.pair['dims'] == ('tone',),
           spec.describe())
        ck('一·问句本身不得留成词面/声律条件',
           not spec.pz and not spec.tail_any and not spec.keywords, spec.describe())
        if not getattr(spec, 'pair', None):
            continue
        res = ask.answer(conn, q, topk=3)
        pj = res.get('pair') or {}
        ck('二·给了组数与对数', pj.get('n_groups', 0) > 0 and pj.get('n_pairs', 0) > 0, pj)
        au = pairing.audit(conn, spec,
                           [{'poems': [{'pid': p} for p in g['pids']]} for g in pj['groups']])
        ck('二·独立复算的组数一致', au['n_groups'] == pj.get('n_groups'),
           '%s vs %s' % (au['n_groups'], pj.get('n_groups')))
        ck('二·独立复算的对数一致', au['n_pairs'] == pj.get('n_pairs'),
           '%s vs %s' % (au['n_pairs'], pj.get('n_pairs')))
        ck('二·范围篇数与库中条件一致', pj.get('scope_n') == au['n_pairs_scope'],
           '%s vs %s' % (pj.get('scope_n'), au['n_pairs_scope']))
        ck('三·展示至少一对、且每对逐位相同',
           len(au['per_pair']) >= 1 and all(x['ok'] for x in au['per_pair']), au['per_pair'][:3])
        for x in au['per_pair']:
            ck('三·逐位比对：%s↔%s' % (x['a'], x['b']),
               x['n_pos'] > 0 and x['n_diff'] == 0 and x['first_diff'] is None,
               '%d 位 / 不同 %d 位' % (x['n_pos'], x['n_diff']))
        ck('三·每对两篇都在证据块里', len(res['blocks']) >= 2
           and {b['pid'] for b in res['blocks']} >= {p for x in au['per_pair'] for p in (x['a'], x['b'])})
        ck('四·护栏通过', res['verify'][0], '；'.join(res['verify'][1])[:150])
        ck('四·结论行不得写「排序最前者」（那是另一类题的模板句）',
           '排序最前者' not in res['answer'])
        ck('四·组数与对数在正文里出现（不是只在 JSON 里）',
           ('%d 组' % pj['n_groups']) in res['answer'] and ('%d 对' % pj['n_pairs']) in res['answer'])

    for q in NOT_PAIR:
        print('· [不得误判] %s' % q)
        spec = retrieve.parse_query(conn, q)
        ck('五·普通/极值题不得被认成配对题', not getattr(spec, 'pair', None), spec.describe())

    # 六、大模型理解路：模型把配对题听成声律条件 → 必须改用规则路
    q6 = CASES[0]
    print('· [大模型路] %s ＋假模型输出 {"pz":"平仄平仄平仄平仄"}' % q6)
    spec6, note6 = ask.understand(conn, q6, llm=_FakeLLM('{"pz":"平仄平仄平仄平仄"}'),
                                  llm_parse=True)
    ck('六·模型丢掉配对意图时由规则补回', bool(getattr(spec6, 'pair', None)),
       '条件=%s 注=%s' % (spec6.describe(), note6['notes']))
    res6 = ask.answer(conn, q6, topk=3, llm=_FakeLLM('{"pz":"平仄平仄平仄平仄"}'),
                      llm_parse=True)
    ck('六·大模型路的答案仍是配对题答案（不是被声律条件筛出来的篇）',
       bool(res6.get('pair')) and '组' in res6['answer'], res6['answer'][:80])
    ck('六·大模型路的护栏也通过', res6['verify'][0], '；'.join(res6['verify'][1])[:150])

    # 七、未实现的维度：字面相同 → 必须认账（拒答），不许拿平仄冒充
    q7 = '找出几对每个位置上的字都相同的两首词'
    spec7 = retrieve.parse_query(conn, q7)
    ck('七·「字面相同」要认出来（但维度标成 text）',
       bool(getattr(spec7, 'pair', None)) and spec7.pair['dims'] == ('text',), spec7.describe())
    res7 = ask.answer(conn, q7, topk=3)
    ck('七·未实现的维度必须拒答且说清', res7.get('refused') is True
       and '未见支持' in res7['answer'] and '平仄' in res7['answer'], res7['answer'][:80])
    ck('七·拒答文本里不得出现数字', not any(ch.isdigit() for ch in res7['answer']))

    print('\n===== 配对题汇总 =====')
    print('  检查项 %d，比对项 %d，FAIL %d' % (CMP[0], CMP[0], len(BAD)))
    for b in BAD[:20]:
        print('  ✗ ' + b)
    if CMP[0] == 0:
        print('  ✗ FAIL：比对项数为 0（防「空跑报通过」）')
        return 1
    if args.selftest:
        if BAD:
            print('  ✓ 自检通过：停掉识别器后共报错 %d 项（旧行为被门禁抓到）' % len(BAD))
            return 0
        print('  ✗ 自检失败：停掉识别器后门禁竟然没报错')
        return 1
    print('  全部通过' if not BAD else '  存在问题')
    return 0 if not BAD else 1


if __name__ == '__main__':
    sys.exit(main())
