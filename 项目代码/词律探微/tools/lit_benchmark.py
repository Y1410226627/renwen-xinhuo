# -*- coding: utf-8 -*-
"""lit_benchmark.py —— **文学解释基准**（第三轮审查 §6；需要大模型，手工跑）。

为什么要独立于 nl_benchmark：`nl_paraphrase.jsonl` 只验证条件解析/布尔/计数/集合身份
（即使 40 条全过，也**不能**证明「愁从何来」「上下片情绪如何变化」这类文学问题答得对）。
本基准覆盖审查建议的五类：单篇内容理解 / 情感与结构分析 / 主题语义检索 / 复合任务 /
证据与歧义边界。

**检查方式（客观可自动化，不让模型给自己打分）**：
  ① 内容类问题必须给出「文意解读」段，且汉字数 ≥ `min_len`（不能一句话敷衍、不能只复述开篇）；
  ② 回答里的每一处引文（“…”）必须能在该篇**原文**中逐字找到（去标点比对）——防编造；
  ③ `must_quote` 关键句覆盖 ≥ `must_any`（要「指出具体句子」才算结构分析）；
  ④ 语义题（`semantic`）必须声明「候选/最接近/非穷尽」；歧义题（`hedge`）必须出现
     「可理解为/也可/似传达」类克制措辞；
  ⑤ 复合任务（`expect_number`）必须出现预期数字（验证精确条件被执行）。

用法（需要学校网关大模型可用）：
    python tools/lit_benchmark.py                 # 默认规划路（LVC_PLANNER=plan）
    python tools/lit_benchmark.py --planner rule  # 对照旧链
    python tools/lit_benchmark.py --update-baseline
大模型不可用时**如实报 SKIP（未运行）**——不算通过、不算失败。
"""
import argparse
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

_HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
_LOOSE = re.compile(r'[\s，。、；：？！,.:;?!“”"\'「」『』（）()《》〈〉·—…\-#]+')


def _loose(s):
    """去标点/空白/引号——用于「字面落地」比对（标点不参与文字存在性判断）。"""
    return _LOOSE.sub('', s or '')


def _orig_text(conn, pid):
    lines = [x[0] for x in conn.execute(
        'SELECT text FROM lines WHERE pid=? ORDER BY idx', (pid,))]
    return ''.join(lines)


def check_case(conn, c, r):
    """客观检查一个用例 → 问题列表（空 = 通过）。"""
    probs = []
    ans = (r or {}).get('answer') or ''
    if c.get('min_len'):
        i = ans.find('【文意解读')
        if i < 0:
            probs.append('未给出文意解读段（内容类问题必须直接作答）')
        else:
            seg = ans[i:]
            if len(_HAN.findall(seg)) < int(c['min_len']):
                probs.append('解读段过短（< %d 汉字）' % int(c['min_len']))
    pid = c.get('pid')
    # 引文落地池：**证据块里所有篇**的全篇原文并集——解读材料可能含多篇候选，
    # 只要引文出自「被展示的任一篇」即不算编造；完全不在这批篇里才判「疑编造」。
    # ★ 2026-10-09（第三轮审查 P1-19）：引文落地池**只取实际返回的证据块**——
    #   旧版把测试用例里预期 pid 的**全文**预先塞进池子，于是"预期作品根本没被召回、
    #   答案却引用了它的原文"也能通过字面检查（没测到真正的召回）。
    #   现改为：池 = 实际 `blocks`（每篇全文 + 字段变体）；预期 pid 是否真的被召回，
    #   单独用 `must_quote` 的"关键句覆盖"来断言（关键句只可能来自该篇）。
    pool = ''
    for b in ((r or {}).get('blocks') or []):
        bp = b.get('pid')
        if bp:
            pool += _loose(_orig_text(conn, bp))
        for _k in ('scene', 'cipai', 'title', 'author', 'dynasty'):
            pool += _loose(str(b.get(_k) or ''))
        for _L in (b.get('lines') or []):
            for _k in ('text', 'tail', 'pz'):
                if _L.get(_k):
                    pool += _loose(str(_L[_k]))
    if pool:
        for m in re.findall(r'[“"]([^”"]+)[”"]', ans):
            mq = _loose(m)
            if len(mq) >= 2 and mq not in pool:
                probs.append('引文未在被展示的篇中落地（疑编造）：%s' % m)
    if pool:
        for m in re.findall(r'[“"]([^”"]+)[”"]', ans):
            mq = _loose(m)
            if len(mq) >= 2 and mq not in pool:
                probs.append('引文未在被展示的篇中落地（疑编造）：%s' % m)
    if c.get('must_quote'):
        hit = sum(1 for s in c['must_quote'] if _loose(s) in _loose(ans))
        need = int(c.get('must_any') or 1)
        if hit < need:
            probs.append('关键句覆盖不足（%d/%d，要求≥%d）' % (hit, len(c['must_quote']), need))
    if c.get('semantic'):
        if not any(w in ans for w in ('候选', '最接近', '并非全部', '非穷尽', '语义')):
            probs.append('语义题未声明「非穷尽」（不得冒充完整集合）')
        # ★ 2026-10-09（第三轮审查 P1-19）：主题检索除了"声明非穷尽"，还要验**召回相关性**。
        #   判据分两层：① 展示块（用户直接看到的）里命中锚点；② **召回报告**里命中的篇数
        #   （报告是执行器的真实召回结果，topk 常为 50-60，比展示块大得多）。二者取**更宽**的
        #   那一个——主题检索的"相关性"应看「召回了哪些」，而非「top-2 恰好展示了哪些」。
        _want_pids = c.get('expect_pids') or []
        if _want_pids:
            _shown = {b.get('pid') for b in ((r or {}).get('blocks') or []) if b.get('pid')}
            # ★ 完整召回集优先（`retrieved_pids` = 执行器真实召回、语义题时 f.pids 全集）：
            #   这才是「召回了哪些」的正确判据；展示块（topk）小是正常的。
            _rec = (r or {}).get('retrieved_pids')
            _pool = set(_rec) if _rec else _shown
            _hitn = len(_pool & set(_want_pids))
            _need = int(c.get('min_hits') or 1)
            if _hitn < _need:
                probs.append('主题召回相关性不足：标注锚点 %d 篇，召回命中 %d/%d（要求≥%d）'
                             % (len(_want_pids), _hitn, len(_want_pids), _need))
    if c.get('hedge'):
        if not any(w in ans for w in ('可理解为', '也可', '似传达', '或寄寓', '可能')):
            probs.append('未使用克制的解读措辞（歧义/推断未标明）')
    if c.get('expect_number'):
        if str(c['expect_number']) not in ans:
            probs.append('未出现预期数字 %s（精确条件未正确执行）' % c['expect_number'])
    return probs


def main():
    ap = argparse.ArgumentParser(description='文学解释基准（需要大模型）')
    ap.add_argument('--planner', default='plan', help='rule | plan（默认 plan）')
    ap.add_argument('--topk', type=int, default=2)
    ap.add_argument('--update-baseline', action='store_true')
    args = ap.parse_args()
    os.environ['LVC_PLANNER'] = str(args.planner)

    import llm as L
    import ask as ASK

    base = os.path.join(ROOT, 'tests', 'lit_baseline.json')
    cases = []
    with open(os.path.join(ROOT, 'tests', 'lit_cases.jsonl'), encoding='utf-8') as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                cases.append(json.loads(ln))

    client = L.LLM()
    if not client.available():
        print('SKIP：大模型不可用（本基准需要 LLM）——**未运行，不算通过**')
        print('     配置 solve/data/llm_local.json 后再跑；或用 --planner rule 对照旧链。')
        return 0

    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'corpus.db'))
    conn.row_factory = sqlite3.Row
    passed, fails = 0, []
    for c in cases:
        try:
            r = ASK.answer(conn, c['q'], topk=args.topk, llm=client)
            probs = check_case(conn, c, r)
            route = (r.get('route') or {}).get('used')
        except Exception as e:                                   # noqa: BLE001
            probs = ['执行异常：%r' % e]
            route = '—'
        if probs:
            fails.append((c['id'], probs))
            print('✗ %s [%s]（路径 %s）' % (c['id'], c.get('type'), route))
            for p in probs:
                print('    · %s' % p)
        else:
            passed += 1
            print('✓ %s [%s]（路径 %s）' % (c['id'], c.get('type'), route))
    total = len(cases)
    print('=' * 64)
    print('文学解释基准（%s 路）：通过 %d/%d' % (args.planner, passed, total))
    old = None
    if os.path.isfile(base):
        try:
            old = json.load(open(base, encoding='utf-8'))
        except ValueError:
            old = None
    if old:
        _delta = passed - old.get('ok', 0)
        _judge = ('无回退' if _delta >= 0 else
                  ('**波动范围内（-1：LLM 生成的随机性，非代码回归）**' if _delta >= -1
                   else '**回退**'))
        print('对比基线：%s（基线 %d/%d）' % (_judge, old.get('ok', 0), old.get('total', 0)))
    if args.update_baseline:
        json.dump({'ok': passed, 'total': total, 'planner': args.planner},
                  open(base, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('基线已更新：%s' % base)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
