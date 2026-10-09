# -*- coding: utf-8 -*-
"""gen.py —— 「说法层」：让国产大模型把**引擎算好的事实**写成研究性叙述 / 论证草稿。

分工（这是本项目的核心纪律）：
    引擎（prosody/corpus）→ 算数字；检索（retrieve/evidence）→ 取证据与原文；
    **大模型（本模块）** → 只负责把它写成通顺的话；护栏（guard/safety）→ 逐行核对。

所以本模块的产出**不是「答案」**，而是「**表述**」：
    一律先经 `guard.verify()`（数字有出处 / 引文逐字 / 边界声明 / 引用落地）
    与 `safety.check()`（内容安全）；**任一不过就整段丢弃**，
    由调用方回落到确定性模板。宁可话糙，不可话说错。

用法（命令行等价）：
    python solve/gen.py --db data/corpus.db --question "清 临江仙 仄声比例高于45%"
    python solve/gen.py --db data/corpus.db --question "清 临江仙 仄声比例高于45%" --argument
"""
import argparse
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import guard                                                  # noqa: E402
import safety                                                 # noqa: E402

SYSTEM = (
    '你是「词律探微」的解释层，只负责把给定事实（FACTS）写成通顺的研究性说明。\n'
    '硬规则（违反任何一条，稿件都会被程序丢弃）：\n'
    '1) 只能使用 FACTS 里出现过的数字，**一个都不许自己算、四舍五入或补充**；\n'
    '2) 引用篇目必须写成 [E1]、[E2] 这样的标记，且只能引用 FACTS 里给出的编号；\n'
    '3) 要引词句时，必须**逐字照抄** FACTS 中「原文：」后面的整句，并用中文引号「」括起；\n'
    '4) 不得引入 FACTS 之外的任何史实、生平、版本或他人评价；\n'
    '5) 不得判断作品优劣，不得推测作者心理或创作意图；\n'
    '6) 不要输出表格、代码块、Markdown 标题或项目符号；\n'
    '7) 篇幅控制在 150—300 字，语气克制、学术化；\n'
    '8) 「【查询条件（唯一权威）】」里列出什么条件，就只说什么条件——'
    '提问里出现了但它没被解析进去（比如并列只说了一半），**不得提及、不得补充、不得推测**。'
)
TASK_NARRATE = (
    '请写一段面向研究者的说明：先用一句话点明这批结果的共同特征，再举 1—2 个具体篇目为例'
    '（带 [E#] 与必要数字），最后说明这些数字只在形式与声调层面成立。'
)
TASK_ARGUMENT = (
    '请写一段研究论证草稿，分四层写（用「主张：」「证据：」「可能的反证：」「局限：」开头）：'
    '主张（这批篇目在声律形式上的共性）／证据（引 FACTS 的数字与篇目，带 [E#]）／'
    '可能的反证（哪些情况会让这个形式规律不成立）／局限（本系统只提供形式层证据）。'
)


def _num(x, fmt='%.1f'):
    try:
        return fmt % float(x)
    except (TypeError, ValueError):
        return '—'


def facts(res):
    """把证据块里的**事实**列成清单（只有事实，没有评价）。

    第一条固定是「查询条件（唯一权威）」——清单是脚本从 spec 里抄出来的，
    不是让模型自己总结问题，从根上防「把没解析到的条件编进去」（2026-09-30 实测事故）。
    """
    out = ['【查询条件（唯一权威）】%s' % (res.get('spec') or '（无条件）')]
    for line in (res.get('agg_facts') or []):        # 聚合题：组级事实（同样来自原库）
        out.append(line)
    if res.get('extreme_fact'):                     # 极值题：问的是「哪一首…」，别写成「共同特征」
        out.append(res['extreme_fact'])
    if res.get('pair_fact'):                        # 配对题：答案是一批**对子**，不是「哪些篇满足条件」
        out.append(res['pair_fact'])
    for b in res.get('blocks') or []:
        out.append('[%s] %s·%s《%s》｜%d 句 / %d 字｜平 %d、仄 %d｜仄声比例 %s%%｜声情转向 %s｜出处 %s'
                   % (b['eid'], b['dynasty'], b['author'], b['title'] or b['cipai'],
                      b['sent_n'], b['han_len'], b['ping'], b['ze'], _num(b['ze_ratio']),
                      b['scene'], b['pid']))
        if b.get('change') is not None:
            out.append('    （前段与后段的变化值 %s，长句阈值 %s）'
                       % (_num(b['change']), b.get('threshold', '—')))
        for L in (b.get('lines') or []):
            out.append('    [%s] 第 %d 句 原文：%s（%d 字，平 %d、仄 %d，平仄串 %s）'
                       % (b['eid'], L.get('seq', L['idx'] + 1), L['text'], L['han_len'],
                          L['ping'], L['ze'], L['pz']))
    if not out:
        out.append('（无——本轮没有召回到任何篇目）')
    return '\n'.join(out)


def _allow(res):
    """说法层允许出现的数字。

    审查 B5：聚合题（blocks=[]）里，FACTS 是唯一的数字来源，旧版没把 FACTS 数字放进白名单
    → 模型照抄 FACTS 立刻被判「数字无出处」→ **聚合题的说法层从未生效**。
    FACTS 全部由引擎产出（含组级统计、极值复核、配对复核），放行它们不降低严格度。
    """
    allow = re.findall(r'\d+(?:\.\d+)?', res.get('spec') or '')
    allow.append(len(res.get('blocks') or []))
    for b in res.get('blocks') or []:
        allow += [str(int(n)) for n in re.findall(r'\d+', b['pid'])]
    allow += re.findall(r'\d+(?:\.\d+)?', facts(res))
    return allow


def produce(llm, res, kind, boundary, argument=False, max_tokens=700, temperature=0.2,
            on_delta=None):
    """生成「说法层」文本并过护栏。返回 dict（ok=False 时调用方必须回落到模板）。"""
    model = getattr(llm, 'name', None) or '未知模型'
    if not (llm and llm.available()):
        return {'ok': False, 'model': model, 'text': '', 'raw': '',
                'problems': ['大模型不可用（无密钥或未联网），回落到模板作答']}
    user = ('【问句】%s\n【查询理解】%s\n【问句类型】%s\n【FACTS】\n%s\n【任务】%s'
            % (res.get('question', ''), res.get('spec', ''), kind, facts(res),
               TASK_ARGUMENT if argument else TASK_NARRATE))
    kw = {'temperature': temperature, 'max_tokens': max_tokens}
    if on_delta is not None:
        kw['on_delta'] = on_delta            # 网页端可边生成边显示（首字延迟 ~0.4 秒）
    raw = llm.chat([{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
                   **kw)
    if not raw:
        return {'ok': False, 'model': model, 'text': '', 'raw': '',
                'problems': ['大模型无返回：%s' % (getattr(llm, 'last_error', '') or '未知原因')]}
    body = raw.strip() + ('\n【推断边界｜%s问句】%s' % (kind, boundary))
    problems = []
    sf = safety.check(body, 'out')
    if not sf['ok']:
        problems.append('生成文本命中内容安全规则（%s）' % sf['category'])
    ok_g, probs = guard.verify(body, res.get('blocks') or [], boundary_kind=kind,
                               allow=_allow(res))
    if not ok_g:
        problems += probs[:4]
    ok = (not problems) and ok_g
    return {'ok': ok, 'model': model, 'text': body if ok else raw.strip(), 'raw': raw.strip(),
            'problems': problems}


def main():
    ap = argparse.ArgumentParser(description='说法层：大模型写叙述 / 论证草稿（必须过护栏）')
    ap.add_argument('--db', required=True)
    ap.add_argument('--question', required=True)
    ap.add_argument('--topk', type=int, default=3)
    ap.add_argument('--argument', action='store_true')
    ap.add_argument('--provider', default=None)
    args = ap.parse_args()
    import ask as ASK
    import llm as L
    client = L.LLM(provider=args.provider)
    conn = sqlite3.connect(args.db)
    res = ASK.answer(conn, args.question, topk=args.topk, llm=client,
                     narrate=not args.argument, argument=args.argument)
    conn.close()
    print('模型：%s（可用=%s）' % (client.name or '无', client.available()))
    print('─' * 60)
    print(res['answer'])
    r = res.get('narrative') or {}
    print('─' * 60)
    print('说法层结果：%s' % ('已采用' if r.get('ok') else '已丢弃（回落模板）'))
    for p in r.get('problems') or []:
        print('  · %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
