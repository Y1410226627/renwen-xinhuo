# -*- coding: utf-8 -*-
"""web_verify.py —— 把 1000 题放进**网页端**（HTTP /api/ask，与页面同一条链路）逐题重问、
爬取答案、逐字核验。

为什么必须有这一层（2026-10-03 晚，主人实测「第四十题」驱动）：离线复核直调
`ASK.answer`（规则解析），而网页端默认走 HTTP 服务，勾选后还叠着**大模型理解层**。
两条链路任何一条出问题，用户在页面上看到的就不是复核过的那份答案——实测正是如此：
大模型听漏条件后空 spec 被照单执行，按语义相关度展示了全库残片。

两道检查：
  A（确定性链路，**逐字**）：/api/ask 不带 parse/narrate → 纯引擎。网页答案与
     **冻结参考**（离线 ASK.answer 逐字节）必须完全一致——一个字都不许差。
  B（大模型理解链路）：/api/ask?parse=1 → 执行 spec、命中总数、结论行、护栏结论
     必须与参考一致（理解层的修复保证：规则路已解析出的硬条件不因模型听漏而丢失；
     narrate 的模型稿另行过护栏，不参与逐字比对）。

用法（先生成参考，再跑轮次）：
  python tools/web_verify.py --make-ref                 # 第 0 步：离线逐题作答 → 冻结参考
  python tools/web_verify.py --rounds 10                 # A 检查 ×10 遍（逐字比对）
  python tools/web_verify.py --llm-round                # B 检查 ×1 遍（全量，走大模型理解）
  python tools/web_verify.py --llm-round --limit 100     # B 检查抽样（前 100 题）
  python tools/web_verify.py --narrate-sample 20        # 额外：parse=1&narrate=1 抽样
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QF = os.path.join(ROOT, 'data', 'questions_1000.jsonl')
REF = os.path.join(ROOT, 'data', 'web_ref_1000.jsonl')
REPORT = os.path.join(ROOT, '网页端逐题核验报告.md')


# ------------------------------------------------------------------ 基础
def load_questions():
    qs = []
    with open(QF, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                qs.append(json.loads(line))
    return qs


def load_ref():
    if not os.path.isfile(REF):
        sys.exit('找不到冻结参考 %s，请先跑 --make-ref' % REF)
    out = []
    with open(REF, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def ref_md5(refs):
    return hashlib.md5(''.join(x['answer'] for x in refs).encode('utf-8')).hexdigest()


def ask_web(base, q, parse=False, narrate=False, ctx=None, timeout=240):
    params = {'q': q, 'topk': 3}
    if parse:
        params['parse'] = '1'
    if narrate:
        params['narrate'] = '1'
    if ctx:
        params['ctx'] = ctx
    url = base + '/api/ask?' + urllib.parse.urlencode(params)
    last = None
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:                       # 网络抖动重试一次；再败就如实报错
            last = e
            time.sleep(1.0)
    raise last


# ⭐ **来源门禁**（2026-10-04 主人特别强调：「一定核验是网页端问出来的答案，而不是你自己跑出来的」）：
#    网页服务在回包里**追加**了 `ms`（服务端计时）与 `llm`（服务端模型可用性）两个字段——
#    离线直调 `ASK.answer` 的输出**没有**这两个键。所以：回包缺任一键 → 判定「不是网页端回的」，
#    按问题记录并计入报告。这条门禁把「退化成本地直调」这种可能从机制上排除掉。
WEB_MARKERS = ('ms', 'llm', 'answer')


def web_provenance(j):
    """回包是否**确实来自网页服务**（服务端字段齐备）。"""
    if not isinstance(j, dict):
        return False
    return all(k in j for k in WEB_MARKERS)


def evidence_dump(path, port, qid, url, j):
    """留痕：把网页端**原始回包**抽样写盘，供人工核对「答案确实出自网页接口」。"""
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'port': port, 'id': qid, 'url': url,
                            'ms': j.get('ms'), 'llm': j.get('llm'),
                            'spec': j.get('spec'), 'total': j.get('total'),
                            'verify': j.get('verify'), 'answer': j.get('answer')},
                           ensure_ascii=False) + '\n')


def chardiff(ref, web):
    """逐字 diff：返回 None 表示**完全一致**；否则给第一个不同字符的位置与上下文。"""
    if ref == web:
        return None
    n = min(len(ref), len(web))
    i = 0
    while i < n and ref[i] == web[i]:
        i += 1
    ctx = lambda s: s[max(0, i - 25):i + 25].replace('\n', '⏎')
    # 顺带定位第几行不同，便于人工复核
    ln = ref[:i].count('\n') + 1
    return '第 %d 行第 %d 字起不同（网页长 %d／参考长 %d）：网页「%s」≠ 参考「%s」' % (
        ln, i - (ref[:i].rfind('\n') if ref[:i].rfind('\n') >= 0 else 0),
        len(web), len(ref), ctx(web), ctx(ref))


def conclusion_of(text):
    for line in (text or '').split('\n'):
        if line.startswith('【结论】'):
            return line
    return None


def rep_append(text):
    with open(REPORT, 'a', encoding='utf-8') as f:
        f.write(text + '\n')
    print(text, flush=True)


# ------------------------------------------------------------------ 第 0 步：冻结参考
def make_ref():
    import sqlite3
    sys.path.insert(0, os.path.join(ROOT, 'solve'))
    import ask as A
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'corpus.db'))
    qs = load_questions()
    out, t0 = [], time.time()
    for i, r in enumerate(qs, 1):
        res = A.answer(conn, r['q'], topk=3)
        out.append({'id': r['id'], 'q': r['q'], 'answer': res['answer'],
                    'spec': res['spec'], 'total': res.get('total'),
                    'verify_ok': bool(res['verify'][0])})
        if i % 100 == 0:
            print('  … 参考已生成 %d/%d（%.0f 秒）' % (i, len(qs), time.time() - t0), flush=True)
    with open(REF, 'w', encoding='utf-8') as f:
        for x in out:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    print('冻结参考已写出 %s（%d 题，答案拼接 md5=%s）' % (REF, len(out), ref_md5(out)))


# ------------------------------------------------------------------ A：确定性链路（逐字）
def round_a(base, refs, qs, rounds, port=None):
    md5_ref = ref_md5(refs)
    rep_append('\n## A｜确定性链路（通过网页服务 HTTP GET %s/api/ask 逐题问、爬回包，与冻结参考逐字比对）'
               '——共 %d 遍' % (base, rounds))
    rep_append('- **来源门禁**：每个回包必须带服务端字段 `ms`/`llm`（离线直调不会产生）——'
               '证明答案确实来自网页端，而不是本地跑出来的。')
    ev = os.path.join(ROOT, '网页端原始回包_留痕.jsonl')
    all_ok = True
    for rd in range(1, rounds + 1):
        bad, n_web, t0 = [], 0, time.time()
        for i, (r, ref) in enumerate(zip(qs, refs), 1):
            j = ask_web(base, r['q'])
            if not web_provenance(j):
                bad.append({'id': r['id'], 'kind': 'E_NOT_WEB',
                            'detail': '回包缺少服务端字段（ms/llm），不能证明出自网页端'})
                continue
            n_web += 1
            if rd == 1 and i % 50 == 1:
                evidence_dump(ev, port, r['id'],
                              base + '/api/ask?q=' + urllib.parse.quote(r['q']), j)
            d = chardiff(ref['answer'], j.get('answer') or '')
            if d is not None:
                bad.append({'id': r['id'], 'kind': 'E_TEXT', 'detail': d})
            elif j.get('spec') != ref['spec']:
                bad.append({'id': r['id'], 'kind': 'E_SPEC',
                            'detail': '网页「%s」≠ 参考「%s」' % (j.get('spec'), ref['spec'])})
            elif j.get('total') != ref['total']:
                bad.append({'id': r['id'], 'kind': 'E_TOTAL',
                            'detail': '网页 %r ≠ 参考 %r' % (j.get('total'), ref['total'])})
            elif bool((j.get('verify') or {}).get('ok')) != bool(ref['verify_ok']):
                bad.append({'id': r['id'], 'kind': 'E_GUARD',
                            'detail': '护栏结论翻转：网页 %s／参考 %s'
                                      % ((j.get('verify') or {}).get('ok'), ref['verify_ok'])})
            if i % 100 == 0:
                print('  第 %d 遍 … %d/%d（%.0f 秒）' % (rd, i, len(qs), time.time() - t0), flush=True)
        line = ('- 第 %d 遍：逐字一致 %d / %d，问题 %d 项；'
                '**网页端回包（端口 %s）%d / %d 带服务端字段**（用时 %.0f 秒）'
                % (rd, len(qs) - len(bad), len(qs), len(bad), port, n_web, len(qs),
                   time.time() - t0))
        rep_append(line)
        for b in bad[:20]:
            rep_append('  - **%s %s**：%s' % (b['id'], b['kind'], b['detail']))
        if len(bad) > 20:
            rep_append('  - …… 其余 %d 项略（详见上方逐题输出）' % (len(bad) - 20))
        if bad:
            all_ok = False
    rep_append('**A 结论：%s**（参考 md5=%s；原始回包留痕 `网页端原始回包_留痕.jsonl`）'
               % ('全部 %d 遍逐字一致，0 问题' % rounds if all_ok
                  else '存在问题，见上', md5_ref))
    return all_ok


# ------------------------------------------------------------------ B：大模型理解链路
def round_b(base, refs, qs, limit=None, port=None):
    items = list(zip(qs, refs))[:limit] if limit else list(zip(qs, refs))
    rep_append('\n## B｜大模型理解链路（HTTP GET %s/api/ask?parse=1，执行 spec／命中数／结论行／护栏'
               ' 与参考比对；回包必带服务端字段 ms/llm）——共 %d 题' % (base, len(items)))
    bad, t0, n_web = [], time.time(), 0
    for i, (r, ref) in enumerate(items, 1):
        try:
            j = ask_web(base, r['q'], parse=True)
        except Exception as e:
            bad.append({'id': r['id'], 'kind': 'E_CRASH', 'detail': '%s: %s' % (type(e).__name__, e)})
            continue
        if not web_provenance(j):
            bad.append({'id': r['id'], 'kind': 'E_NOT_WEB',
                        'detail': '回包缺少服务端字段（ms/llm），不能证明出自网页端'})
            continue
        n_web += 1
        probs = []
        if j.get('spec') != ref['spec']:
            probs.append('执行 spec「%s」≠ 规则「%s」' % (j.get('spec'), ref['spec']))
        if j.get('total') != ref['total']:
            probs.append('命中 %r ≠ %r' % (j.get('total'), ref['total']))
        cw, cr = conclusion_of(j.get('answer') or ''), conclusion_of(ref['answer'])
        if cw != cr:
            probs.append('结论行不同：网页「%s」／参考「%s」' % (cw, cr))
        if bool((j.get('verify') or {}).get('ok')) is not True and ref['verify_ok']:
            probs.append('护栏未通过：%s' % ((j.get('verify') or {}).get('problems')))
        if probs:
            bad.append({'id': r['id'], 'kind': 'E_LLM', 'detail': '；'.join(probs)})
        if i % 50 == 0:
            print('  … B 已核 %d/%d（%.0f 秒）' % (i, len(items), time.time() - t0), flush=True)
    rep_append('- B 结果：一致 %d / %d，问题 %d 项；**网页端回包（端口 %s）%d / %d 带服务端字段**'
               '（用时 %.0f 秒）'
               % (len(items) - len(bad), len(items), len(bad), port, n_web, len(items),
                  time.time() - t0))
    for b in bad[:30]:
        rep_append('  - **%s %s**：%s' % (b['id'], b['kind'], b['detail']))
    if len(bad) > 30:
        rep_append('  - …… 其余 %d 项略' % (len(bad) - 30))
    return not bad


def round_d(base, refs, qs, limit=None, port=None):
    """D｜**多轮上下文链路**（HTTP GET /api/ask?parse=1&ctx=上一题）。

    为什么必须有这一段（2026-10-04 主人在页面里实测驱动）：网页在「有上一轮」时会带 ctx，
    这是主人实际用到的形态，而 B/C 都是**单问**形态——漏了这一条，于是「四到十句之间，
    没有任何一句句长在七到十一字之间…」在带上下文时被模型重复编码出一条篇级「阈值 7~11」，
    命中数 **3876 → 486 篇**。本段要求：**自足的问句带上上下文后，执行条件/命中数/结论行
    必须与单问一致**（问句自身已自足时，上下文不许改变答案）。
    """
    items = list(zip(qs, refs))[:limit] if limit else list(zip(qs, refs))
    rep_append('\n## D｜多轮上下文链路（/api/ask?parse=1&ctx=上一题，共 %d 题；'
               '回包必带服务端字段 ms/llm）' % len(items))
    bad, t0, n_web = [], time.time(), 0
    for i, (r, ref) in enumerate(items, 1):
        ctx = ('问：%s 答：共命中若干篇。' % qs[i - 2]['q']) if i >= 2 \
            else '问：清词里仄声比例高于百分之五十的作品有多少篇？答：共命中 1234 篇。'
        try:
            j = ask_web(base, r['q'], parse=True, ctx=ctx)
        except Exception as e:
            bad.append({'id': r['id'], 'kind': 'E_CRASH', 'detail': '%s: %s' % (type(e).__name__, e)})
            continue
        if not web_provenance(j):
            bad.append({'id': r['id'], 'kind': 'E_NOT_WEB',
                        'detail': '回包缺少服务端字段（ms/llm），不能证明出自网页端'})
            continue
        n_web += 1
        probs = []
        if j.get('spec') != ref['spec']:
            probs.append('带上下文后执行 spec「%s」≠ 单问「%s」' % (j.get('spec'), ref['spec']))
        if j.get('total') != ref['total']:
            probs.append('命中 %r ≠ 单问 %r' % (j.get('total'), ref['total']))
        cw, cr = conclusion_of(j.get('answer') or ''), conclusion_of(ref['answer'])
        if cw != cr:
            probs.append('结论行不同：带上下文「%s」／单问「%s」' % (cw, cr))
        if bool((j.get('verify') or {}).get('ok')) is not True and ref['verify_ok']:
            probs.append('护栏未通过：%s' % ((j.get('verify') or {}).get('problems')))
        if probs:
            bad.append({'id': r['id'], 'kind': 'E_CTX', 'detail': '；'.join(probs)})
        if i % 50 == 0:
            print('  … D 已核 %d/%d（%.0f 秒）' % (i, len(items), time.time() - t0), flush=True)
    rep_append('- D 结果：一致 %d / %d，问题 %d 项；**网页端回包（端口 %s）%d / %d 带服务端字段**'
               '（用时 %.0f 秒）'
               % (len(items) - len(bad), len(items), len(bad), port, n_web, len(items),
                  time.time() - t0))
    for b in bad[:30]:
        rep_append('  - **%s %s**：%s' % (b['id'], b['kind'], b['detail']))
    if len(bad) > 30:
        rep_append('  - …… 其余 %d 项略' % (len(bad) - 30))
    return not bad


def narrate_sample(base, refs, qs, n, port=None):
    import random
    random.seed(20261003)
    idx = sorted(random.sample(range(len(qs)), min(n, len(qs))))
    rep_append('\n## C｜大模型理解 + 表述链路（HTTP GET %s/api/ask?parse=1&narrate=1，抽样 %d 题；'
               '回包必带服务端字段 ms/llm）' % (base, len(idx)))
    bad, t0, n_web = [], time.time(), 0
    for k, i in enumerate(idx, 1):
        r, ref = qs[i], refs[i]
        try:
            j = ask_web(base, r['q'], parse=True, narrate=True)
        except Exception as e:
            bad.append({'id': r['id'], 'kind': 'E_CRASH', 'detail': '%s: %s' % (type(e).__name__, e)})
            continue
        if not web_provenance(j):
            bad.append({'id': r['id'], 'kind': 'E_NOT_WEB',
                        'detail': '回包缺少服务端字段（ms/llm），不能证明出自网页端'})
            continue
        n_web += 1
        probs = []
        if j.get('spec') != ref['spec']:
            probs.append('执行 spec「%s」≠ 规则「%s」' % (j.get('spec'), ref['spec']))
        if j.get('total') != ref['total']:
            probs.append('命中 %r ≠ %r' % (j.get('total'), ref['total']))
        if ref['verify_ok'] and (j.get('verify') or {}).get('ok') is not True:
            probs.append('护栏未通过：%s' % ((j.get('verify') or {}).get('problems')))
        if probs:
            bad.append({'id': r['id'], 'kind': 'E_NARRATE', 'detail': '；'.join(probs)})
        if k % 5 == 0:
            print('  … C 已核 %d/%d（%.0f 秒）' % (k, len(idx), time.time() - t0), flush=True)
    rep_append('- C 结果：一致 %d / %d，问题 %d 项；**网页端回包（端口 %s）%d / %d 带服务端字段**'
               '（用时 %.0f 秒）'
               % (len(idx) - len(bad), len(idx), len(bad), port, n_web, len(idx),
                  time.time() - t0))
    for b in bad:
        rep_append('  - **%s %s**：%s' % (b['id'], b['kind'], b['detail']))
    return not bad


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description='网页端逐题爬取核验（HTTP /api/ask）')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8200)
    ap.add_argument('--make-ref', action='store_true', help='第 0 步：生成冻结参考（离线逐题作答）')
    ap.add_argument('--rounds', type=int, default=0, help='A 检查遍数（确定性链路，逐字）')
    ap.add_argument('--llm-round', action='store_true', help='B 检查（大模型理解链路，全量）')
    ap.add_argument('--ctx-round', action='store_true',
                    help='D 检查（多轮上下文链路：带上一轮 ctx，全量）')
    ap.add_argument('--limit', type=int, default=None, help='B/C 检查只取前 N 题')
    ap.add_argument('--narrate-sample', type=int, default=0, help='C 检查抽样 N 题（parse+narrate）')
    ap.add_argument('--shard', default=None,
                    help='分片 "I/N"：只跑第 I 片（0 起）——只为提速（多个服务进程各持一把锁），'
                         '各片报告分开写，最后人工/脚本汇总。')
    a = ap.parse_args()
    global REPORT
    if a.shard:
        i, n = (int(x) for x in a.shard.split('/'))
        REPORT = os.path.join(ROOT, '网页端逐题核验报告_片%d_of_%d.md' % (i, n))
    base = 'http://%s:%d' % (a.host, a.port)
    if a.make_ref:
        make_ref()
        return 0
    qs, refs = load_questions(), load_ref()
    if len(qs) != len(refs):
        sys.exit('题目 %d 与参考 %d 数量不一致，请重新 --make-ref' % (len(qs), len(refs)))
    if a.shard:
        i, n = (int(x) for x in a.shard.split('/'))
        pick = [(q, r) for k, (q, r) in enumerate(zip(qs, refs)) if k % n == i]
        qs = [p[0] for p in pick]
        refs = [p[1] for p in pick]
        print('分片 %d/%d：本题集 %d 题，端口 %d' % (i, n, len(qs), a.port), flush=True)
    # 服务器必须活着（先探一下，别对着报错干跑）
    try:
        with urllib.request.urlopen(base + '/api/examples', timeout=10) as r:
            json.loads(r.read().decode('utf-8'))
    except Exception as e:
        sys.exit('网页服务未启动或不可达（%s）：请先启动 web/serve.py --port %d' % (e, a.port))
    ok = True
    if a.rounds:
        ok = round_a(base, refs, qs, a.rounds, port=a.port) and ok
    if a.llm_round:
        ok = round_b(base, refs, qs, a.limit, port=a.port) and ok
    if a.ctx_round:
        ok = round_d(base, refs, qs, a.limit, port=a.port) and ok
    if a.narrate_sample:
        ok = narrate_sample(base, refs, qs, a.narrate_sample, port=a.port) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
