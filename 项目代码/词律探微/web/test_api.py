# -*- coding: utf-8 -*-
"""test_api.py —— **服务端门禁**：把 serve.py 的各个接口函数直接调起来（不需要起服务器、不联网）。

为什么要有它：网页端的错法有四层——引擎／数据库／页面渲染／交互。
`test_render.js` 管渲染、`test_ui.js` 管前端功能，这一份管**服务端与问答链**：

  一、结构化检索 /api/search：篇数与**独立写的 SQL** 对得上；分面求和 = 命中数；分页不重不漏；
      排序白名单挡住注入（`sort=1; DROP TABLE` 必须回落到默认排序而不是执行）；
      **表单与引擎的条件清单必须一一对应**（2026-09-30 实测：表单比引擎少好几个条件）。
  二、大模型理解层 /api/nl2query（不联网 → 自动回落规则解析）：
      回填的条件再走一遍检索，命中数必须与**问答链**给出的命中数一致（「理解 → 检索 → 计数」三段对齐）。
  三、检索结果成文 /api/summarize（不联网 → 回退模板）：必须如实报告「大模型未启用」，
      且事实清单里第一条是「查询条件（唯一权威）」。
  四、分组对比 /api/compare：两种口径都要有，且数字与 aggregate 模块独立复算一致。
  五、问答 /api/ask：护栏必须通过、正文不得出现 NaN、语料外问题必须拒答。
  六、逐字解析 /api/parse：句数 = lines 行数、每句 pz 长度 = 该句汉字数。
  七、流式问答 /api/ask_stream（2026-10-01 新增）：**「答案先到」契约**——
      事件序必须是 status → engine → delta → final；engine 携带护栏后的答案与证据块，
      且服务端计时 engine ≤ final；未接大模型时**不出** engine（旧行为不变）。
      用本地桩模型（不联网），因此本门禁可离线反复跑。

用法：python web/test_api.py
退出码：0 = 全过（比对项为 0 也判 FAIL）；1 = 有问题。
"""
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

# ⚠ 2026-10-09：快照隔离（功能 1）——本门禁会跑 q_ask，而 q_ask 现在会落「冻结快照」；
#   指向临时目录，避免污染真实 data/snapshots/（必须在 import serve 之前设置）。
os.environ.setdefault('LVC_SNAPSHOT_DIR', tempfile.mkdtemp(prefix='lvc_snap_gate_'))
# ⚠ 2026-10-10（P2-1）：研究库隔离——本门禁 personal 端点用例会写研究库；
#   指向临时文件，避免污染真实 data/research.db（必须在 import serve 之前设置）。
_LVC_RESEARCH_TMP = os.path.join(
    tempfile.mkdtemp(prefix='lvc_research_gate_'), 'research.db')
os.environ.setdefault('LVC_RESEARCH_DB', _LVC_RESEARCH_TMP)

import serve as S                        # noqa: E402
import aggregate as AGG                  # noqa: E402
import ask as ASK                        # noqa: E402

CMP = [0]
BAD = []
CFG = {'count': 0, 'show': 12}


def ok(name, cond, detail=''):
    CMP[0] += 1
    if not cond:
        BAD.append(name + ('：' + detail if detail else ''))


def sql_count(conn, where, args=()):
    return conn.execute('SELECT COUNT(1) FROM poems p WHERE %s' % where, list(args)).fetchone()[0]


def main():
    if not os.path.exists(S.DB):
        print('找不到语料库 %s' % S.DB)
        return 2
    conn = S.get_conn()

    # ---------- 一、结构化检索 ----------
    cases = [
        ({'author': '纳兰性德'}, "p.dynasty='清' AND p.author LIKE '%纳兰性德%'"),
        ({'tail': '愁'}, "p.dynasty='清' AND EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid AND l.tail='愁')"),
        ({'tail': '灯 声'},
         "p.dynasty='清' AND EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid AND l.tail IN ('灯','声'))"),
        ({'pz': '仄仄平平仄'},
         "p.dynasty='清' AND EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid AND l.pz GLOB '*仄仄平平仄*')"),
        ({'minZe': '60'}, "p.dynasty='清' AND p.ze_ratio>=60"),
        ({'minSent': '12', 'maxSent': '14'}, "p.dynasty='清' AND p.sent_n>=12 AND p.sent_n<=14"),
        ({'scene': '后段下降', 'minLen': '50'}, "p.dynasty='清' AND p.scene='后段下降' AND p.han_len>=50"),
    ]
    for cond, where in cases:
        r = S.q_search(conn, dict(cond, size='5'))
        want = sql_count(conn, where)
        ok('检索篇数 ' + json.dumps(cond, ensure_ascii=False), r['total'] == want,
           '接口 %d ≠ SQL %d' % (r['total'], want))
        ok('单页行数 ≤ size', len(r['rows']) <= 5)
        ok('行字段齐全 ' + json.dumps(cond, ensure_ascii=False),
           all(k in r['rows'][0] for k in ('pid', 'author', 'cipai', 'sent_n', 'han_len',
                                           'ze_ratio', 'scene', 'raw')) if r['rows'] else True)
        bucket_sum = sum(r['facets']['ratio'].values())
        ok('分面求和 = 命中数 ' + json.dumps(cond, ensure_ascii=False), bucket_sum == want,
           '%d ≠ %d' % (bucket_sum, want))
        scene_sum = sum(c for _, c in r['facets']['scene'])
        ok('声情分面求和 = 命中数', scene_sum == want, '%d ≠ %d' % (scene_sum, want))
        s0 = conn.execute('SELECT COUNT(1), AVG(p.ze_ratio), MIN(p.ze_ratio), MAX(p.ze_ratio) '
                          'FROM poems p WHERE %s' % where).fetchone()
        got = r['stats']
        ok('集合统计与 SQL 独立复算一致 ' + json.dumps(cond, ensure_ascii=False),
           got['n'] == s0[0]
           and abs((got['ze_mean'] or 0) - round(s0[1], 1)) < 0.11
           and got['ze_min'] == s0[2] and got['ze_max'] == s0[3],
           'stats=%s vs SQL=%s' % (got, tuple(s0)))

    # 分页不重不漏
    p1 = S.q_search(conn, {'minZe': '55', 'sort': 'ze_desc', 'size': '7', 'page': '1'})
    p2 = S.q_search(conn, {'minZe': '55', 'sort': 'ze_desc', 'size': '7', 'page': '2'})
    ids1 = [x['pid'] for x in p1['rows']]
    ids2 = [x['pid'] for x in p2['rows']]
    ok('分页两页不重复', not (set(ids1) & set(ids2)))
    ok('分页：第 1 页首篇的仄比 ≥ 第 2 页首篇',
       (not ids1 or not ids2) or (p1['rows'][0]['ze_ratio'] >= p2['rows'][0]['ze_ratio']))

    # 注入白名单
    bad_sort = S.q_search(conn, {'size': '3', 'sort': '1; DROP TABLE poems'})
    ok('排序白名单挡住注入', bad_sort['order_by'] == 'p.pid' and bad_sort['total'] > 0)
    weird = S.q_search(conn, {'q': "' OR 1=1 --", 'size': '3'})
    ok('关键词参数化（恶意串只当普通关键词）', weird['total'] >= 0 and weird['rows'] is not None)

    # 表单条件清单 ↔ 引擎：每一个参数都要能真的筛掉东西（拿两个取值的结果集不相等来验）
    extra = [
        ({'tailPz': '平'}, "p.dynasty='清' AND EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid "
                           "AND substr(l.pz,-1,1)='平')"),
        ({'tailPz': '仄'}, "p.dynasty='清' AND EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid "
                           "AND substr(l.pz,-1,1)='仄')"),
        ({'changeMin': '5'}, "p.dynasty='清' AND p.change>=5"),
        ({'changeMax': '-5'}, "p.dynasty='清' AND p.change<=-5"),
        ({'thrMin': '6'}, "p.dynasty='清' AND p.threshold>=6"),
        ({'thrMax': '4'}, "p.dynasty='清' AND p.threshold<=4"),
        ({'dynasty': '宋'}, "p.dynasty='宋'"),
        ({'author': '朱祖谋'}, "p.dynasty='清' AND p.author LIKE '%朱祖谋%'"),
        ({'cipai': '临江仙'}, "p.dynasty='清' AND p.cipai LIKE '%临江仙%'"),
    ]
    for cond, where in extra:
        r = S.q_search(conn, dict(cond, size='3'))
        want = sql_count(conn, where)
        ok('新条件检索篇数 ' + json.dumps(cond, ensure_ascii=False), r['total'] == want,
           '接口 %d ≠ SQL %d' % (r['total'], want))
        ok('新条件有区分度（否则等于没筛）', 0 < want < 58852)
    ok('条件清单：句脚平仄两个取值结果不同',
       sql_count(conn, "p.dynasty='清' AND EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid "
                      "AND substr(l.pz,-1,1)='平')")
       != sql_count(conn, "p.dynasty='清' AND EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid "
                         "AND substr(l.pz,-1,1)='仄')"))
    # 分面新增「句脚字 TOP」，且求和口径正确（句脚字是句级量，不能拿它跟篇数比）
    fs = S.q_search(conn, {'author': '纳兰性德', 'size': '3'})
    ok('分面含句脚字 TOP', isinstance(fs['facets'].get('tail'), list) and len(fs['facets']['tail']) > 0)
    n_na = sql_count(conn, "p.dynasty='清' AND p.author LIKE '%纳兰性德%'")
    f_na = S.q_search(conn, {'author': '纳兰性德', 'size': '3'})['facets']
    ok('句脚字分面的每个取值 ≤ 命中篇数（句级量不得超】篇级量）',
       all(c <= n_na for _t, c in f_na['tail']), json.dumps(f_na['tail'][:3], ensure_ascii=False))
    ok('分面「词人」求和 = 命中数',
       sum(c for _a, c in f_na['author']) == n_na)
    # 分页：第二页必须**真的有行**（旧前端 bug 的另一个面：页数字对但内容空）
    pg2 = S.q_search(conn, {'minZe': '40', 'size': '5', 'page': '2'})
    ok('服务端第二页有行（非空）', len(pg2['rows']) == 5, str(len(pg2['rows'])))
    # 处理函数的参数清单必须覆盖 build_where 支持的全部条件
    #（根因：条件支持了却没加进清单 → 被**静默丢掉**，返回全库看着还像有结果）
    src = open(os.path.join(HERE, 'serve.py'), encoding='utf-8').read()
    m2 = re.search(r'SEARCH_PARAMS = \(([^)]*)\)', src)
    listed = set(re.findall(r"'([A-Za-z]+)'", m2.group(1))) if m2 else set()
    for k in ('q', 'author', 'cipai', 'tail', 'tailPz', 'pz', 'minZe', 'maxZe', 'minLen',
              'maxLen', 'minSent', 'maxSent', 'minLong', 'changeMin', 'changeMax', 'thrMin',
              'thrMax', 'scene', 'sort', 'page', 'size', 'dynasty'):
        ok('处理函数参数清单含 ' + k, k in listed, sorted(listed))
    ok('参数清单被 /api/search 真正使用', '{k: g(k) for k in SEARCH_PARAMS}' in src)
    # 而且**每一个**参数都必须真的能过 HTTP 路由→筛选（不是只在清单里做样子）
    for k, v in (('tailPz', '平'), ('changeMin', '5'), ('thrMax', '4')):
        r1 = S.q_search(conn, {k: v, 'size': '3'})
        ok('参数 %s 真的筛掉了东西（不是全库）' % k, 0 < r1['total'] < 58852,
           '%s=%s → %s 篇 / cond_text=%s' % (k, v, r1['total'], r1['cond_text']))

    # ---------- 二、大模型理解层（不联网 → 回落规则解析） ----------
    Q = '句脚是「愁」的清词有哪些'
    nl = S.q_nl2query(conn, Q, use_llm=False)
    ok('理解层回填了句脚条件', (nl['cond'].get('tail') or '').find('愁') >= 0,
       json.dumps(nl['cond'], ensure_ascii=False))
    cond_search = S.q_search(conn, dict(nl['cond'], size='3'))
    ans = ASK.answer(conn, Q, topk=3)
    ok('「条件回填 → 检索 → 计数」与问答链一致',
       cond_search['total'] == ans['total'],
       '回填检索 %s vs 问答链 %s' % (cond_search['total'], ans['total']))
    ok('理解层声明了来源', bool(nl.get('source')))
    ok('理解层未静默丢字段（unparsed 为列表）', isinstance(nl.get('unparsed'), list))

    # ---------- 三、检索结果成文（不联网 → 回退模板） ----------
    su = S.q_summarize(conn, {'tail': '愁', 'size': '3'}, use_llm=False)
    ok('成文接口如实报告未启用大模型', su['ok'] is False and su['llm_available'] is False)
    ok('未启用时给出确定性回退文案（不让页面开天窗）',
       su['fallback'] is True and su['text'].startswith('【确定性摘要】'),
       su['text'][:60])
    ok('成文接口的命中数与检索一致', su['total'] == S.q_search(conn, {'tail': '愁'})['total'])
    ok('事实清单第一条是查询条件（唯一权威）',
       su['facts'].splitlines()[0].startswith('【查询条件（唯一权威）】'))
    ok('事实清单不含 NaN', 'NaN' not in su['facts'])

    # ---------- 四、分组对比 ----------
    cmp_ = S.q_compare(conn, 'dynasty', '宋,清', 'ze_ratio')
    ok('对比给了两种口径（篇均＋加权）',
       all(('mean' in r and 'weighted' in r) for r in cmp_['rows']))
    ok('对比结论非空', bool(cmp_['cmp'].get('winner')) or cmp_['cmp'].get('tie') is not None)
    indep = AGG.stats(conn, 'dynasty', ['宋', '清'], 'ze_ratio')
    ok('对比数字与 aggregate 独立复算一致',
       all(abs(a['weighted'] - b['weighted']) < 1e-9 for a, b in zip(cmp_['rows'], indep)))
    ok('对比成文不含 markdown 星号', '**' not in cmp_['text'])

    # ---------- 五、问答（护栏 / NaN / 拒答） ----------
    for q in ('清 临江仙 仄声比例高于45%', '找后段下降的清词', '句脚是「灯」或者「声」的清词有哪些'):
        r = S.q_ask(q, topk=3)
        ok('问答护栏通过：' + q, r['verify']['ok'], '；'.join(r['verify']['problems'])[:160])
        ok('问答正文无 NaN：' + q, 'NaN' not in r['answer'])
        ok('问答给了命中总数：' + q, isinstance(r.get('total'), int))
    refuse = S.q_ask('唐 李白 静夜思 的平仄', topk=3)
    ok('语料外问题必须拒答', bool(refuse.get('refused')), json.dumps(refuse.get('kind')))
    agg = S.q_ask('宋词与清词总体来说仄声占比哪个更高', topk=3)
    ok('聚合题走聚合链（给了分组统计而不是普通检索）', bool(agg.get('agg')),
       'kind=' + str(agg.get('kind')) + ' keys=' + ','.join(sorted(agg.keys())))
    # 配对题（「找出几对…平仄都相同的两首词」）：不能退回「筛篇」，必须给组/对与独立复核
    pr = S.q_ask('找出几对每个位置上的字平仄都相同的两首词', topk=3)
    ok('配对题给了组数与对数', bool(pr.get('pair')) and pr['pair']['n_groups'] > 0
       and pr['pair']['n_pairs'] > 0, json.dumps(pr.get('pair', {}) and {
           k: pr['pair'][k] for k in ('n_groups', 'n_pairs', 'scope_n')}, ensure_ascii=False))
    ok('配对题的独立复核数与主路一致',
       pr['pair']['audit']['n_groups'] == pr['pair']['n_groups']
       and pr['pair']['audit']['n_pairs'] == pr['pair']['n_pairs'])
    ok('配对题每一对都逐位相同', all(x['ok'] for x in pr['pair']['audit']['per_pair'])
       and len(pr['pair']['audit']['per_pair']) > 0)
    ok('配对题护栏通过', pr['verify']['ok'], '；'.join(pr['verify']['problems'])[:160])
    ok('配对题不得把「最高/排序最前」当答案', '排序最前者' not in pr['answer'])
    ok('配对题 JSON 可序列化（页面要用）',
       bool(json.dumps(pr['pair'], ensure_ascii=False)))

    # ---------- 六、逐字解析接口 ----------
    pid = conn.execute("SELECT pid FROM poems WHERE dynasty='清' AND sent_n>4 LIMIT 1").fetchone()[0]
    pj = S.q_parse(pid)
    ok('解析接口：句数 = lines 行数', pj['sent_n'] == len(pj['lines']),
       '%s vs %s' % (pj['sent_n'], len(pj['lines'])))
    ok('解析接口：每句 pz 长度 = 该句汉字数',
       all(len(L['pz']) == L['han_len'] for L in pj['lines']))
    ok('解析接口：句脚字是最后一个汉字',
       all(L['tail'] == re.sub(r'[^\u3400-\u4dbf\u4e00-\u9fff]', '', L['text'])[-1:]
           for L in pj['lines'] if L['han_len'] > 0))
    # ⚠ 2026-10-06 新增（历史缺陷回归护栏）：`longest_seq` 必须是**数字数组**。
    #   库里的存储形态是 JSON 字符串（build_corpus 用 json.dumps 写入，如 '[4]'），
    #   接口出口必须规范化成数组——旧版直出字符串，前端按「、」分隔解析得到
    #   Number('[4]')=NaN，页面显示「最长句第 NaN 句」（只有在线模式中招，离线自算为真数组）。
    _ls = pj.get('longest_seq') or []
    ok('解析接口：longest_seq 是数组（不是 JSON 字符串）',
       isinstance(pj.get('longest_seq'), list), repr(pj.get('longest_seq')))
    ok('解析接口：longest_seq 元素均为正整数',
       all(isinstance(x, int) and x > 0 for x in _ls), repr(_ls))
    ok('解析接口：longest_seq 指向的句长 == longest_len',
       (not _ls) or all(pj['lines'][i - 1]['han_len'] == pj['longest_len'] for i in _ls),
       '%s / longest_len=%s' % (_ls, pj['longest_len']))

    # ---------- 六-b、personal:<n> 端点（P2-1 个人作品解析） ----------
    # 写一行个人作品到临时研究库，走 q_parse('personal:<id>') 解析（绝不查 corpus.db）。
    import research as _RSCH
    _rc = _RSCH.connect(_LVC_RESEARCH_TMP)
    _wtest = _RSCH.add_personal_work(_rc, 'P21接口验证', '风急天高猿啸哀，渚清沙白鸟飞回。',
                                     author='P21', client_token='tok-api-p21')
    _pid_p = 'personal:%d' % _wtest['work_id']
    _pp = S.q_parse(_pid_p)
    ok('personal 解析：无 error 键', 'error' not in _pp, repr(_pp.get('error')))
    ok('personal 解析：pid 前缀正确', _pp.get('pid') == _pid_p, repr(_pp.get('pid')))
    ok('personal 解析：dynasty 为空', _pp.get('dynasty') == '')
    ok('personal 解析：sent_n 与 lines 行数一致',
       _pp.get('sent_n') == len(_pp.get('lines') or []),
       '%s vs %d' % (_pp.get('sent_n'), len(_pp.get('lines') or [])))
    ok('personal 解析：每句 pz 长度 = han_len',
       all(len(L['pz']) == L['han_len'] for L in (_pp.get('lines') or [])))
    # 不存在的 personal pid 返回 error（不是 500 异常）
    _pn = S.q_parse('personal:99999')
    ok('personal 解析：不存在 id 返回 error', 'error' in _pn, repr(_pn.get('error')))
    _rc.close()

    # ---------- 六-c、研究库引用进证据链（P2-2 引用环） ----------
    # 纪律：`material:<n>` / `fact:<n>` / `personal:<n>` 只做「证据块」，
    #   绝不进语料问答链（ASK.answer 的 ctx_pids）与集合身份校验（set_check）。
    import research as _RSCH2
    _rc2 = _RSCH2.connect(_LVC_RESEARCH_TMP)
    _mat = _RSCH2.add_material(_rc2, 'P22测试摘录', '临江仙一调，宋人多以此调写羁旅。',
                               kind='book', author='P22', year='2026',
                               source_url='https://example.org/p22',
                               client_token='tok-api-p22-m')
    _mid = _mat['material_id']
    _fact = _RSCH2.add_fact(_rc2, '清词《临江仙》仄声比例偏高者为多。',
                            material_id=_mid, locator='卷三·页12',
                            evidence='临江仙一调，宋人多以此调写羁旅。',
                            client_token='tok-api-p22-f')
    _fid = _fact['fact_id']
    _rc2.close()
    _mpid = 'material:%d' % _mid
    _fpid = 'fact:%d' % _fid
    _rr = S.q_ask('清 临江仙 仄声比例高于45%', topk=3, ctx_pids=[_mpid, _fpid])
    _re = _rr.get('research_evidence') or []
    ok('P2-2 引用：返回体带 research_evidence', len(_re) == 2, 'n=%d' % len(_re))
    _eids = [b['eid'] for b in _re]
    ok('P2-2 引用：eid 前缀 M/F 区分材料与事实',
       any(e.startswith('M') for e in _eids) and any(e.startswith('F') for e in _eids),
       repr(_eids))
    _mblk = next((b for b in _re if b['eid'].startswith('M')), {})
    ok('P2-2 引用：材料块含标题与正文',
       _mblk.get('title') == 'P22测试摘录' and bool(_mblk.get('content')),
       repr({k: _mblk.get(k) for k in ('title', 'content_len')}))
    _fblk = next((b for b in _re if b['eid'].startswith('F')), {})
    ok('P2-2 引用：事实块含陈述与核验状态',
       '临江仙' in (_fblk.get('statement') or '') and ('verified' in _fblk),
       repr({k: _fblk.get(k) for k in ('statement', 'verified')}))
    ok('P2-2 引用：来源如实标「研究库，非交付语料」',
       all('研究库' in (b.get('source_note') or '') for b in _re))
    # 红线：研究库 pid 绝不进语料链 blocks，也不送语料检索（ctx_pids.received=0）
    _bpid = [b.get('pid') for b in (_rr.get('blocks') or [])]
    ok('P2-2 引用：研究库 pid 不进语料 blocks',
       not any(str(p).startswith(('material:', 'fact:', 'personal:')) for p in _bpid),
       repr(_bpid[:5]))
    ok('P2-2 引用：研究库 pid 不送语料链（received=0）',
       (_rr.get('ctx_pids') or {}).get('received') == 0,
       repr(_rr.get('ctx_pids')))
    ok('P2-2 引用：护栏不受研究库引用影响仍通过',
       bool((_rr.get('verify') or {}).get('ok')),
       '；'.join((_rr.get('verify') or {}).get('problems') or [])[:160])
    # 不存在的 pid：跳过、不抛异常（证据块为空，主链照常）
    _rr2 = S.q_ask('清 临江仙 仄声比例高于45%', topk=3,
                   ctx_pids=['material:999999', 'fact:999999'])
    ok('P2-2 引用：不存在的 id 被跳过且不报错',
       not (_rr2.get('research_evidence') or [])
       and bool((_rr2.get('verify') or {}).get('ok')),
       're=%r' % (_rr2.get('research_evidence'),))



    # ---------- 六-d、模型/端点可指定 + 如实回显（P2-5） ----------
    _opts = S.q_llm_options()
    ok('P2-5 选项：带「仅限校内本地」约束声明',
       ('校内' in (_opts.get('constraint') or '')) and ('校外' in (_opts.get('constraint') or '')),
       repr(_opts.get('constraint')))
    ok('P2-5 选项：models / endpoints / allow_hosts 均为列表',
       isinstance(_opts.get('models'), list) and isinstance(_opts.get('endpoints'), list)
       and isinstance(_opts.get('allow_hosts'), list))
    # 用假默认客户端钉死两条规则（校外端点被拒 / 校内指定生效），不联网：
    _FAKE_URL = 'http://10.27.66.12/v1/chat/completions'

    class _FakeLocal:
        provider = 'ucass'
        model = 'qwen3.8-27b'
        url = _FAKE_URL
        label = '校内 Qwen'

        def available(self):
            return True

    _fake = _FakeLocal()
    _old_get = S.get_llm
    S.get_llm = lambda: _fake
    try:
        _c1, _i1 = S.get_llm_for(None, 'http://evil.example.com/v1/chat/completions')
        ok('P2-5 校外端点被拒并如实记录（回落默认）',
           _c1 is _fake and bool(_i1['rejected']) and _i1['specified'] is False, repr(_i1))
        _c2, _i2 = S.get_llm_for('qwen-test', _FAKE_URL)
        ok('P2-5 校内端点 + 模型指定生效',
           _c2 is not _fake and _i2['specified'] is True and _i2['model'] == 'qwen-test'
           and _i2['endpoint'] == _FAKE_URL, repr(_i2))
        ok('P2-5 端点白名单含默认主机', '10.27.66.12' in S.q_llm_options()['allow_hosts'],
           repr(S.q_llm_options()['allow_hosts']))
        _r25 = S.q_ask('清 临江仙 仄声比例高于45%', topk=3, model='qwen-test')
    finally:
        S.get_llm = _old_get
    _used = (_r25.get('llm') or {}).get('used') or {}
    ok('P2-5 问答如实回显本轮实际使用的模型',
       _used.get('specified') is True and _used.get('model') == 'qwen-test',
       repr(_used))

    # ---------- 七、流式问答（SSE）：「答案先到」契约（本地桩，不联网） ----------
    import time as _time

    class _StubLLM:
        """本地桩：可用=True；「理解层」回合法 JSON、「说法层」先推一段增量再返回。

        另外**记录每次收到的提示**（seen）：多轮上下文的断言要验证「ctx 真的进了提示」。
        """
        name = 'stub-llm'
        provider = 'stub'
        last_error = ''

        def __init__(self):
            self.seen = []

        def available(self):
            return True

        def chat(self, messages, **kw):
            self.seen.append(messages[-1].get('content', '') if messages else '')
            sys_msg = (messages[0].get('content', '') if messages else '')
            if '查询理解' in sys_msg:          # qlm 的 system 含「查询理解」→ 回 JSON 条件
                return '{"dynasty":"清","cipais":["临江仙"],"rng":{"ze_min":45}}'
            on_delta = kw.get('on_delta')
            if on_delta:
                on_delta('这是一段测试增量。')
            return '这是一段测试文字，用于验证事件顺序。'

    old_llm = S.LLM
    S.LLM = _StubLLM()
    try:
        events = []
        t_start = _time.time()
        for frame in S.q_ask_stream('清 临江仙 仄声比例高于45%', topk=3, narrate=True,
                                    parse=True, policy='auto'):
            for ln in frame.splitlines():
                if ln.startswith('data:'):
                    body = ln[5:].strip()
                    if not body or body == '{"type":"done"}':
                        continue
                    d = json.loads(body)
                    events.append((d.get('type'), d, _time.time() - t_start))
        kinds = [k for k, _d, _t in events]
        ok('SSE 事件序：status → engine → delta → final',
           ('status' in kinds and 'engine' in kinds and 'delta' in kinds and 'final' in kinds)
           and kinds.index('status') < kinds.index('engine') < kinds.index('delta')
           < kinds.index('final'), 'kinds=%s' % kinds)
        eng = next((d for k, d, _t in events if k == 'engine'), {})
        fin = next((d for k, d, _t in events if k == 'final'), {})
        ok('engine 事件带答案与证据块',
           bool(eng.get('answer')) and len(eng.get('blocks') or []) > 0,
           'answer=%d 字、blocks=%d' % (len(eng.get('answer') or ''), len(eng.get('blocks') or [])))
        ok('engine 是护栏后版本（正文含护栏结论一行）', '【护栏校验】' in (eng.get('answer') or ''))
        ok('engine 先到（服务端计时 ≤ final 且都给了 ms）',
           isinstance(eng.get('ms'), int) and isinstance(fin.get('ms'), int)
           and eng['ms'] <= fin['ms'], 'engine=%s ms / final=%s ms'
           % (eng.get('ms'), fin.get('ms')))
        ok('final 与 /api/ask 同构（关键字段齐全）',
           all(k in fin for k in ('answer', 'blocks', 'verify', 'kind', 'narrator', 'ms', 'llm')))
        ok('final 里大模型稿状态如实（ok 布尔 + 模型名）',
           isinstance((fin.get('narrative') or {}).get('ok'), bool))
        # 崩溃回归（2026-10-01 答案解析实测）：「组内极值」时规则路的 agg['values'] 是 None，
        # 而大模型没认出该意图时，旧版 '／'.join(None) 抛 TypeError → 整条问答变 500。
        # 桩模型返回普通条件（无 agg），正好逼出那条分支——这里断言**不崩且用规则路的聚合**。
        _rs, _nt = ASK.understand(S.get_conn(), '哪位词人的临江仙最多',
                                  llm=S.LLM, llm_parse=True)
        ok('组内极值不崩：规则路认出、大模型没认出 → 用规则路', bool(_rs.agg),
           'agg=%s notes=%s' % (_rs.agg, _nt.get('notes')))
        # 多轮上下文（2026-10-01 深夜）：ctx 必须真的进了「理解层」提示（桩记录到的用户消息里
        # 能看到），且理解层注记如实披露「结合了上下文」；不带 ctx 时不许出现该字样（控制变量）。
        _rs3, _nt3 = ASK.understand(
            S.get_conn(), '那里面句脚是灯的有哪些', llm=S.LLM, llm_parse=True,
            context='上一问：清 临江仙｜上一轮解析为：朝代=清；词牌=临江仙')
        ok('多轮上下文进了理解层提示', any('上一轮上下文' in x for x in S.LLM.seen),
           str(getattr(S.LLM, 'seen', [])[-1:])[:140])
        ok('理解层注记如实披露「结合上下文」', any('上下文' in x for x in (_nt3.get('notes') or [])),
           str(_nt3.get('notes'))[:140])
        _n0 = len(S.LLM.seen)                      # 只统计本次调用的消息（桩的 seen 是累积的）
        _rs4, _nt4 = ASK.understand(S.get_conn(), '那里面句脚是灯的有哪些', llm=S.LLM, llm_parse=True)
        ok('不带 ctx 时提示里没有「上一轮上下文」（控制变量）',
           not any('上一轮上下文' in x for x in S.LLM.seen[_n0:]) and
           not any('上下文' in x for x in (_nt4.get('notes') or [])))
        # serve 层：ctx 参数必须**贯通到理解层**——用流式端点把整条链跑通再验证提示内容。
        _n1 = len(S.LLM.seen)
        for _frame in S.q_ask_stream(
                '那里面句脚是灯的有哪些', topk=3, narrate=True, parse=True, policy='auto',
                ctx='上一问：清 临江仙｜上一轮解析为：朝代=清；词牌=临江仙'):
            pass
        ok('serve 的 ctx 参数贯通到理解层提示',
           any('上一轮上下文' in x for x in S.LLM.seen[_n1:]),
           str(S.LLM.seen[_n1:])[:140])
        # 未接大模型：不出 engine、final 照发（旧行为逐字不变）
        S.LLM = None
        kinds2 = []
        for frame in S.q_ask_stream('清 临江仙 仄声比例高于45%', topk=3, narrate=False,
                                    parse=False, policy='auto'):
            for ln in frame.splitlines():
                if ln.startswith('data:'):
                    body = ln[5:].strip()
                    if body and body != '{"type":"done"}':
                        kinds2.append(json.loads(body).get('type'))
        ok('未接大模型时不出 engine（不多余调用、旧行为不变）',
           'engine' not in kinds2 and 'final' in kinds2, 'kinds=%s' % kinds2)
    finally:
        S.LLM = old_llm

    # ---------- 八、内容 / 开放类问题的「文意解读」（桩模型，不联网；2026-10-09 新增） ----------
    # 口径（主人实测确立）：大模型能理解、原材料在数据中能找到的问题 → 默认给生成式回应；
    # 纪律：基于原文、标注非事实结论、过四道护栏，编造引文必须被拦下、不过即静默回退。
    import re as _re2

    class _ReadStub:
        """桩：模拟「文意解读层」——从 FACTS 里偷一句原文与一个数字，保证引用/数字合规。"""
        name = 'stub-read'
        provider = 'stub'
        last_error = ''

        def __init__(self, mode='ok'):
            self.mode = mode

        def available(self):
            return True

        def chat(self, messages, **kw):
            user = messages[-1].get('content', '') if messages else ''
            if self.mode == 'noread':
                return 'NO_READ'
            if self.mode == 'bad':              # 编造引文（材料里根本没有这句）
                return '这首词化用了“碧海青天夜夜心”的意境，情感深沉。'
            m = _re2.search(r'原文：([^\n（(]+)', user)
            quote = (m.group(1) if m else '').strip().strip('。')
            n = _re2.search(r'仄声比例\s*([\d.]+)%', user)
            return ('该篇以“%s”一句最为关键，似传达出含蓄的情绪；'
                    '材料给出的仄声比例为 %s%%，形式偏平缓。'
                    % (quote, n.group(1) if n else '0'))

    old3 = S.LLM
    try:
        S.LLM = _ReadStub('ok')
        o1 = S.q_ask('清 浣溪沙 主要内容是什么', topk=2, parse=False)
        ok('内容类问题默认生成「文意解读」（无需勾选）',
           '【文意解读' in (o1.get('answer') or '')
           and (o1.get('content_read') or {}).get('ok') is True)
        ok('解读段标注「非事实结论」', '非事实结论' in (o1.get('answer') or ''))
        S.LLM = _ReadStub('bad')
        o2 = S.q_ask('清 浣溪沙 主要内容是什么', topk=2, parse=False)
        ok('编造引文必须被拦下（无解读段、如实回退）',
           '【文意解读' not in (o2.get('answer') or '')
           and (o2.get('content_read') or {}).get('ok') is False)
        S.LLM = _ReadStub('ok')
        o3 = S.q_ask('清 浣溪沙 有什么作用', topk=2, parse=False)
        ok('开放提问不进入检索词面（不再「词面=作用」）',
           '作用' not in (o3.get('spec') or ''), 'spec=%s' % o3.get('spec'))
        ok('开放提问也走解读通道（逐条回应）', '【文意解读' in (o3.get('answer') or ''))
        S.LLM = _ReadStub('noread')
        o4 = S.q_ask('清 浣溪沙 主要内容是什么', topk=2, parse=False)
        ok('模型判定无法回应（NO_READ）→ 静默跳过解读段',
           '【文意解读' not in (o4.get('answer') or ''))
    finally:
        S.LLM = old3

    # ⑤ 无大模型（get_llm 返回 None）：内容类问题保持旧行为（模板兜底、零网络调用）
    _oldget = S.get_llm
    S.get_llm = lambda: None
    try:
        o5 = S.q_ask('清 浣溪沙 主要内容是什么', topk=2, parse=False)
        ok('无大模型时不出解读段（旧行为不变）',
           '【文意解读' not in (o5.get('answer') or '')
           and '【内容与情感】' in (o5.get('answer') or ''))
    finally:
        S.get_llm = _oldget

    # ---------- 汇报 ----------
    print('服务端门禁：比对项 %d 项，不符 %d 项' % (CMP[0], len(BAD)))
    for b in BAD[:20]:
        print('  ✗ ' + b)
    if CMP[0] == 0:
        print('✗ FAIL：比对项数为 0（防「空跑报通过」）')
        return 1
    print('✓ 检索／理解／成文／对比／问答／解析 六组服务端检查全部通过'
          if not BAD else '✗ 存在不一致')
    return 0 if not BAD else 1


if __name__ == '__main__':
    sys.exit(main())
