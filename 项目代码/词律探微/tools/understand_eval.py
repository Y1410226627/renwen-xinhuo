# -*- coding: utf-8 -*-
"""understand_eval.py —— 「大模型有没有听懂」回归（双模式）。

为什么要有它
------------
现有门禁 **全部** 只覆盖规则回退路径：
  · `tools/qa_eval.py` 调 `ask.answer(conn, q)`，**不开** `llm_parse`；
  · `web/test_api.py` 里 `q_nl2query(..., use_llm=False)`。
网页上用户勾选「用大模型理解」后走的是**完全没被测试覆盖**的那条路（`qlm.parse` →
`ask.understand`）。本脚本补上这一段。

两种模式
--------
`--mock`（默认，确定性、无网络、可进 CI）：
    用一个**桩 LLM**（`StubLLM`，预置 JSON），驱动 `qlm.validate()` 与 `ask.understand()`，
    验证「给定模型 JSON → 产出 QuerySpec」这一段的**字段落地正确性**（含校验/丢弃/降级），
    并盘点每条问句的「期望理解要点是否被表达、被谁表达、若没被表达则指出 schema 缺口」。

`--live`（可选，需本机配好大模型）：
    用 `solve/llm.py` 的真实 `LLM()` 跑同一批问句，打印
    「问句 → 模型原始 JSON → validate 后 spec → 命中篇数」，供人工核对。
    **绝不打印 `solve/data/llm_local.json` 的内容**；若 `llm.available()` 为假则跳过。

用法
----
    python tools/understand_eval.py                 # mock 模式（默认）
    python tools/understand_eval.py --allow-gaps    # 只以「字段落地断言」为门禁（已知 schema 缺口不算 FAIL）
    python tools/understand_eval.py --live          # 真实大模型（人工核对）
    python tools/understand_eval.py --list          # 列出用例
退出码：0 = 全部通过；1 = 有失败（--live 且模型不可用时按「跳过」处理，返回 0）。
"""
import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import ask as A                                                    # noqa: E402
import qlm                                                         # noqa: E402
import retrieve as R                                               # noqa: E402


# --------------------------------------------------------------------------- 桩 LLM
class StubLLM:
    """最小 LLM 桩：`available()` 恒真；`chat()` 返回预置 JSON（确定性、无网络）。"""

    def __init__(self, payload, name='stub:mock'):
        self.payload = payload
        self.name = name
        self.calls = 0

    def available(self):
        return True

    def chat(self, messages, temperature=0.0, max_tokens=400, **kw):
        self.calls += 1
        if isinstance(self.payload, str):
            return self.payload
        return json.dumps(self.payload, ensure_ascii=False)


# --------------------------------------------------------------------------- 判定小工具
def _tail_set(spec):
    got = set(R._vals(spec, 'tail'))
    lq = spec.line_q or {}
    if lq.get('pred'):
        k, v = lq['pred']
        if k == 'tail':
            got.add(v)
        elif k == 'tail_any':
            got |= set(v)
    return got


def has_tail(vals):
    return lambda s: set(vals) <= _tail_set(s)


def has_agg(gb, extreme=None):
    def f(s):
        a = s.agg or {}
        return a.get('group_by') == gb and (extreme is None or a.get('extreme') == extreme)
    return f


def has_order(metric, extreme):
    return lambda s: s.order_by == metric and s.extreme == extreme


def has_cipai(v):
    return lambda s: v in R._vals(s, 'cipai')


def has_title(v):
    return lambda s: v in R._vals(s, 'title')


def has_line_op(op, kind=None, k=None):
    def f(s):
        lq = s.line_q or {}
        if lq.get('op') != op:
            return False
        if kind is not None and (lq.get('pred') or (None,))[0] != kind:
            return False
        if k is not None and lq.get('k') != k:
            return False
        return True
    return f


def has_pz_exact_forall(v):
    def f(s):
        lq = s.line_q or {}
        if lq.get('op') != '∀':
            return False
        pred = lq.get('pred') or (None, None)
        return pred[0] == 'pz_exact' and pred[1] == v
    return f


def has_pz_exact(v):
    def f(s):
        if s.pz_exact == v:
            return True
        pred = (s.line_q or {}).get('pred') or (None, None)
        return pred[0] == 'pz_exact' and pred[1] == v
    return f


# --------------------------------------------------------------------------- 用例
def build_cases():
    return [
        dict(id='C1', q='句脚是灯或者声的清词',
             payload={'dynasty': '清', 'tail': ['灯', '声']},
             expects=[('句脚字 ∈ {灯,声}（多值并列）', has_tail(['灯', '声']))],
             landing=[('dynasty=清', lambda s: R._vals(s, 'dynasty') == ['清']),
                      ('tail_any ⊇ {灯,声}', lambda s: set(s.tail_any) >= {'灯', '声'})],
             gap='无（schema 有 tail 列表字段，可表达）'),

        dict(id='C2', q='没有任何一句句脚为愁的清词',
             payload={'dynasty': '清', 'tail': ['愁'],
                      'unparsed': ['没有任何一句（句级否定）']},
             expects=[('句级 NOT EXISTS（∄），谓词=句脚字愁',
                       has_line_op('∄', 'tail'))],
             landing=[('模型 schema 无 line_q 字段 → validate 后 line_q 应为 None',
                       lambda s: s.line_q is None)],
             gap='模型 schema（qlm.SYSTEM 字段表）**没有句级算子字段**（∄/∀/≥k/=k/占比/条数）：'
                 '模型只能给 tail=["愁"]（＝∃，语义**相反**）或塞进 unparsed。本句规则路能表达 ∄，'
                 '故被兜住；但这是「规则路兜底」，不是「模型路听懂」。'),

        dict(id='C3', q='至少两句句脚为愁的清词',
             payload={'dynasty': '清', 'tail': ['愁'], 'unparsed': ['至少两句']},
             expects=[('句级 COUNT ≥ 2（≥k, k=2）',
                       lambda s: (s.line_q or {}).get('op') == '≥k'
                                 and (s.line_q or {}).get('k') == 2)],
             landing=[('模型 schema 无 ≥k 字段 → validate 后 line_q 应为 None',
                       lambda s: s.line_q is None)],
             gap='模型 schema 无「句级数量量词」字段。规则路仅在「**有 N 句以上**」措辞下识别 ≥k；'
                 '「至少两句 / 至少 3 句」未识别（落词面残片），「至少有二句」被**误判为 ∃**（存在一句）'
                 '→ 该常见措辞下条件被错解或整条丢失（实测最终得到 794 篇＝「句脚为愁」，真值应为 33 篇）。'),

        dict(id='C4', q='哪个词人的词最多',
             payload={'agg': {'group_by': 'author', 'values': None,
                              'metric': 'count', 'extreme': 'max'}},
             expects=[('GROUP BY author + 取最多（agg.extreme=max）',
                       has_agg('author', 'max'))],
             landing=[('agg.group_by=author', lambda s: (s.agg or {}).get('group_by') == 'author'),
                      ('agg.extreme=max', lambda s: (s.agg or {}).get('extreme') == 'max')],
             gap='无（schema 有 agg 字段，可表达）'),

        dict(id='C5', q='哪一首仄声比例最高',
             payload={'order': {'metric': 'ze_ratio', 'dir': 'max'}},
             expects=[('ORDER BY ze_ratio 取 max', has_order('ze_ratio', 'max'))],
             landing=[('order_by=ze_ratio', lambda s: s.order_by == 'ze_ratio'),
                      ('extreme=max', lambda s: s.extreme == 'max')],
             gap='无（schema 有 order 字段，可表达）'),

        dict(id='C6', q='蝶恋花·四月一日感粤事是谁写的',
             payload={'cipais': ['蝶恋花'], 'unparsed': ['四月一日感粤事（题名）']},
             expects=[('词牌=蝶恋花', has_cipai('蝶恋花')),
                      ('题名=四月一日感粤事', has_title('四月一日感粤事'))],
             landing=[('cipai 落地=蝶恋花', lambda s: '蝶恋花' in R._vals(s, 'cipai')),
                      ('模型 schema 无 title 字段 → validate 后 title 为空',
                       lambda s: not R._vals(s, 'title'))],
             gap='模型 schema **没有题名（title/词题）字段**，只有 cipais → 题名条件模型路表达不了；'
                 '只能靠规则路（retrieve.title_any）补齐。'),

        dict(id='C7', q='每一句整句平仄串正好是仄仄平平仄的清词',
             payload={'dynasty': '清', 'pz': '仄仄平平仄',
                      'unparsed': ['每一句整句平仄串正好']},
             expects=[('∀ + 平仄串**全等**（pz_exact=仄仄平平仄）',
                       has_pz_exact_forall('仄仄平平仄'))],
             landing=[('模型 schema 的 pz 是**子串**语义 → validate 后 pz=仄仄平平仄（非全等）',
                       lambda s: s.pz == '仄仄平平仄' and s.pz_exact is None)],
             gap='模型 schema 只有 pz（**子串**语义），**没有 pz_exact（全等）也没有 ∀ 量词** → '
                 '「每一句都 / 正好是」这层语义模型路表达不了。规则路仅在**规范措辞**下可表达 '
                 '∀+pz_exact（如「每一句都整句平仄串正好是「仄仄平平仄」」——带「都」与「」）；'
                 '任务给定的口语措辞（无「都」、无「」）规则路亦未识别 → 属**词面鲁棒性**缺口。'),

        dict(id='C8', q='那里面哪个最短',
             payload={'unparsed': ['那里面哪个最短']},
             expects=[('引用**上一轮结果集**再取极值（会话/结果集指针）',
                       lambda s: False)],
             landing=[('模型 schema 无会话字段 → validate 后无任何条件',
                       lambda s: not (s.order_by or s.agg or s.dynasty_any or s.cipai_any
                                      or s.keywords))],
             gap='**已知缺口**：当前 schema 无「上一轮结果集」的引用字段（无会话/集合指针）→ '
                 '「那里面…」「它的后段呢」这类纯指代无法表达（规则路亦然）。'),
    ]


# --------------------------------------------------------------------------- validate 单测
def validate_checks(conn):
    """（离线）校验/丢弃/降级单测：给定脏 JSON，validate 该丢的丢、该降级的降级。"""
    checks = []
    obj = {'dynasty': '唐', 'authors': ['朱彝尊', '查无此人XX'],
           'tail': ['愁', '愁愁'], 'scene': '上升',
           'rng': {'ze_min': 45, 'foo': 1, 'len_max': 9999},
           'bogus_field': 1}
    spec, dropped, notes = qlm.validate(conn, obj, '校验单测')
    d = ' | '.join(dropped)
    checks.append(('语料外朝代→unsupported=唐', spec.unsupported == '唐'))
    checks.append(('库里无此人→丢弃', '查无此人XX' in d))
    checks.append(('非单字句脚→丢弃、单字保留', spec.tail_any == ['愁'] and '愁愁' in d))
    checks.append(('声情别名「上升」→后段上升', spec.scene == '后段上升'))
    checks.append(('rng 合法键落地 ze_min=45', spec.rng.get('ze_min') == 45))
    checks.append(('rng 未知键→丢弃', 'foo' in d))
    checks.append(('rng 越界→丢弃', 'len_max' in d))
    checks.append(('多余字段→记 note', any('bogus_field' in n for n in notes)))
    checks.append(('词人合法值落地', '朱彝尊' in spec.author_any))

    # order 白名单/方向
    s2, d2, _ = qlm.validate(conn, {'order': {'metric': 'ze_ratio', 'dir': '最高'}}, 'q')
    checks.append(('order 方向中文「最高」→max', s2.order_by == 'ze_ratio' and s2.extreme == 'max'))
    s3, d3, _ = qlm.validate(conn, {'order': {'metric': '不存在', 'dir': 'max'}}, 'q')
    checks.append(('order 非法指标→丢弃', any('排序指标' in x for x in d3)))
    return checks


# --------------------------------------------------------------------------- 输出
def _spec_line(spec):
    return spec.describe()


def _where(spec, rule, model, final):
    who = []
    if rule(spec):
        who.append('规则路')
    if model(spec):
        who.append('大模型(validate)')
    if final(spec):
        who.append('最终(understand)')
    return who


def run_mock(conn, cases, allow_gaps):
    print('=' * 78)
    print('理解回归（mock 模式）—— 桩 LLM 驱动 qlm.validate() + ask.understand()')
    print('=' * 78)
    fails = []
    gaps = []          # 触发「最终 spec 未表达」的用例
    structural = []    # 所有结构性 schema 缺口（含被规则路兜住的）

    for c in cases:
        print('-' * 78)
        print('【%s】%s' % (c['id'], c['q']))
        print('  模型 JSON：%s' % json.dumps(c['payload'], ensure_ascii=False))

        # 规则路
        rule_spec = R.parse_query(conn, c['q'])
        # 模型路（仅 validate，展示「模型 JSON → spec」的落地）
        model_spec, dropped, notes = qlm.validate(conn, c['payload'], c['q'])
        # 端到端（桩 LLM 驱动 understand）
        stub = StubLLM(c['payload'])
        final_spec, note = A.understand(conn, c['q'], llm=stub, llm_parse=True)

        try:
            ch = R.count_hits(conn, final_spec)
            cnt = '—（无硬条件）' if ch is None else '%d 篇' % ch
        except Exception as e:
            cnt = '计数出错：%s' % e

        print('  规则路 spec：%s' % _spec_line(rule_spec))
        print('  模型 spec（validate 后）：%s' % _spec_line(model_spec))
        if dropped:
            print('    丢弃项：%s' % '／'.join(dropped))
        print('  understand 最终 spec：%s' % _spec_line(final_spec))
        print('    来源：%s' % note.get('source'))
        print('    命中篇数：%s' % cnt)

        # 字段落地断言
        for desc, fn in c.get('landing', []):
            try:
                ok = bool(fn(model_spec))
            except Exception as e:
                ok = False
                desc = desc + '（断言异常：%s）' % e
            print('    落地断言：%s  %s' % ('✓' if ok else '✗', desc))
            if not ok:
                fails.append('%s 落地断言未过：%s' % (c['id'], desc))

        # 期望要点
        missing_here = []
        for desc, fn in c['expects']:
            ok_rule = fn(rule_spec)
            ok_model = fn(model_spec)
            ok_final = fn(final_spec)
            who = []
            if ok_rule:
                who.append('规则路')
            if ok_model:
                who.append('大模型')
            if ok_final:
                who.append('最终')
            mark = '✓' if ok_final else '✗'
            src = '／'.join(who) if who else '**无任何一路表达**'
            print('    期望要点：%s %s   ← 被谁表达：%s' % (mark, desc, src))
            if not ok_final:
                fails.append('%s 期望要点未被最终 spec 表达：%s' % (c['id'], desc))
                missing_here.append(desc)
        if missing_here:
            gaps.append((c['id'], c['q'], '／'.join(missing_here), c['gap']))
        if c.get('gap') and not c['gap'].startswith('无'):
            status = ('**两路均未表达（真缺口）**' if missing_here
                      else '已被规则路兜住（模型路表达不了）')
            structural.append((c['id'], c['q'], c['gap'], status))

    print('-' * 78)
    print('【校验/降级单测】（qlm.validate 脏字段）')
    for desc, ok in validate_checks(conn):
        print('    %s %s' % ('✓' if ok else '✗', desc))
        if not ok:
            fails.append('校验单测未过：%s' % desc)

    print('')
    print('=' * 78)
    print('schema 缺口清单（供架构重构输入）')
    print('=' * 78)
    if not structural:
        print('（无）')
    for cid, q, gap, status in structural:
        print('· [%s] %s' % (cid, status))
        print('    %s' % gap)
        print('    触发问句：%s' % q)

    print('')
    print('=' * 78)
    print('理解回归（mock）：%d 条用例；失败项 %d；结构性 schema 缺口 %d 类'
          % (len(cases), len(fails), len(structural)))
    if fails:
        blockers = fails if not allow_gaps else [f for f in fails if '落地断言' in f or '校验单测' in f]
        if blockers:
            print('✗ FAIL（%d）：' % len(blockers))
            for f in blockers:
                print('   - %s' % f)
            return 1
        print('⚠ --allow-gaps：仅「schema 缺口」未过，字段落地/校验断言全过 → 判通过')
    print('✓ PASS')
    return 0


def run_live(conn, cases):
    import llm as L
    client = L.LLM()
    print('=' * 78)
    print('理解回归（live 模式）—— 真实大模型；仅供人工核对，不做断言')
    print('=' * 78)
    print('模型：%s' % (client.name or '（不可用）'))
    if not client.available():
        print('SKIP：大模型不可用（未配置密钥/环境）—— live 模式跳过，返回 0。')
        print('      （本脚本绝不打印 solve/data/llm_local.json 的内容。）')
        return 0
    for c in cases:
        print('-' * 78)
        print('【%s】%s' % (c['id'], c['q']))
        q = qlm.parse(conn, client, c['q'])
        if q is None:
            print('  模型：未给出可解析 JSON（或不可用）')
            continue
        print('  模型原始 JSON：%s' % (q['raw'] or '').strip()[:400])
        print('  validate 后 spec：%s' % q['spec'].describe())
        if q['dropped']:
            print('    丢弃项：%s' % '／'.join(q['dropped']))
        try:
            ch = R.count_hits(conn, q['spec'])
            print('    命中篇数：%s' % ('—（无硬条件）' if ch is None else '%d 篇' % ch))
        except Exception as e:
            print('    计数出错：%s' % e)
        final_spec, note = A.understand(conn, c['q'], llm=client, llm_parse=True)
        print('  understand 最终 spec：%s（来源：%s）' % (final_spec.describe(), note.get('source')))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='「大模型有没有听懂」回归：mock（桩 LLM，可进 CI）/ live（真实模型，人工核对）。')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--mock', action='store_true', help='mock 模式（默认）')
    ap.add_argument('--live', action='store_true', help='live 模式（需本机配好大模型）')
    ap.add_argument('--allow-gaps', action='store_true',
                    help='仅以「字段落地/校验」断言为门禁；已知 schema 缺口记为告警不算 FAIL')
    ap.add_argument('--list', action='store_true', help='列出用例后退出')
    args = ap.parse_args(argv)

    cases = build_cases()
    if args.list:
        for c in cases:
            print('%s  %s' % (c['id'], c['q']))
        return 0

    if not os.path.isfile(args.db):
        print('✗ 找不到数据库：%s' % args.db)
        return 1
    conn = sqlite3.connect(args.db)
    try:
        if args.live:
            return run_live(conn, cases)
        return run_mock(conn, cases, args.allow_gaps)
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
