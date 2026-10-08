# -*- coding: utf-8 -*-
"""serve.py —— **可以直接提问的本地网页应用**（只依赖 Python 标准库 + 本项目 solve/）。

为什么有它：`parse.html` / `graph.html` / `review.html` 是「看」的静态视图；
但评委（和主人）真正想干的是**问我一句、你答一句、还告诉我出处**。
那就得有一个能收问题的服务端 —— 这里用 `http.server`（标准库，装都不用装）。

页面：
    GET /                问答页（问题 → 引擎作答 → 证据块 → 护栏校验）
    GET /browse.html     在线检索页（多条件检索，条件由 SQLite 查；与离线页同一份前端）
    GET /parse.html      离线逐字解析页（同 /browse.html 的外观）
    GET /graph.html /review.html /index.html

接口（全部返回 JSON，字段即文档）：
    /api/ask?q=...&topk=3&parse=1&narrate=1&argument=1&ctx=...[&ctx_pids=p1,p2,...][&sid=...&carry=1]
                真实引擎作答（检索→证据块→护栏）
                （ctx＝上一轮「问句+解析」摘要；ctx_pids＝上一轮**命中的篇 id 集合**
                  （逗号分隔或重复参数），用于把「那里面……」的指代落到**真实结果集**上；
                  两者都只在 parse=1 时生效。返回体附 `ctx_pids.{received,consumed}`
                  如实回告服务端收到了几个 id、后端理解层是否已消费）
                ⚠ 2026-10-08 新增（外部审查 A/B 项）：
                  · `sid`   —— **服务端会话 id**。带上它，服务端把本轮**完整**结果集
                    （不截断，上限 20000）存进 `context.ContextStore`，下一轮由
                    `context.resolve()` 判「集合指代 / 单篇指代 / 条件继承」，**不再靠前端
                    把 pid 截到 200 后当全部**。返回体附 `session.{sid,turn,stored_pids,
                    result_total,truncated,ref_kind,used_context,note}` 如实回告；
                  · `carry` —— 保留的「承上一轮结果集」显式开关（勾选才承接；指代词命中时自动承接）；
                  · 返回体附 `set_check`（集合身份校验：独立复算命中集 vs 返回集，
                    差集/完整性/聚合复算见 `answer_verify.build_set_check`）与
                    `understanding_status`（'OK'/UNDERSTANDING_INCOMPLETE/KEYWORD_FREEFORM）。
                  · `ctx_pids` 仍保留为**兜底**（服务端会话不可用时用）：因 URL 长度所限，
                    它仍按 200 截断，界面上会明标「已降级」。
    /api/search?q=&author=&cipai=&tail=&tailPz=&pz=&minZe=&maxZe=&minLen=&maxLen=&minSent=
                &maxSent=&minLong=&changeMin=&changeMax=&thrMin=&thrMax=&scene=&dynasty=
                &authorMode=&cipaiMode=&sort=&page=&size=&agg=&pair=&order_by=
                结构化检索（含分面统计与 SQL 回显）。authorMode/cipaiMode 取 contains|exact|prefix；
                agg/pair/order_by 是 nl2query 的**跨篇意图**，本端点**不执行**，只在回包 `intent`
                里如实告知（unsupported_by_search + hint），由前端引导去问答页。
    /api/nl2query?q=...                                  大模型把问句听成**结构化条件**（可人工改后再检索）
    /api/summarize?<同 /api/search 的条件>&llm=1          把检索结果写成一段话（数字仍由引擎给，过四道护栏）
    /api/compare?group_by=dynasty&values=宋,清&metric=ze_ratio   分组对比（两种口径都给）
    /api/parse?pid=... /api/rand?dyn=清 /api/examples /api/llm

设计原则（贯穿全项目）：
    **数字归引擎、文料归检索、说法归大模型、出处归引用。**
    接不接大模型，答案里的数字一模一样；大模型只把同一批事实写成通顺的话，
    且整段还要再过「数字护栏 + 引用护栏 + 边界护栏 + 内容安全」，不过就整段丢弃并注明已回退。
退出：Ctrl+C
"""
import argparse
import json
import os
import random
import re
import sqlite3
import sys
import threading
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import aggregate as AGG                  # noqa: E402
import answer_verify as AVERIFY          # noqa: E402  （集合身份校验，2026-10-08 新增）
import ask as ASK                        # noqa: E402
import context as CONTEXT                # noqa: E402  （服务端会话语境，2026-10-08 新增）
import evidence as EV                    # noqa: E402
import gen as GEN                        # noqa: E402
import guard as GUARD                    # noqa: E402
import llm as LLM_MOD                    # noqa: E402
import retrieve as RT                    # noqa: E402
import safety as SAFETY                  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer   # noqa: E402
from urllib.parse import urlparse, parse_qs                          # noqa: E402

DB = os.path.join(ROOT, 'data', 'corpus.db')
DATA = os.path.join(ROOT, 'data')
# Vue3+Vite 构建产物（D15 前端架构）。问答页在 web/dist/ask/；离线四视图在 data/vue/。
DIST_ASK = os.path.join(HERE, 'dist', 'ask')
DIST_VIEWS = os.path.join(DATA, 'vue')
# ⚠ 2026-10-06 修（外部审查 P1-28/29）：并发模型重构（详见 get_conn 注释）。
#   LOCK 不再包裹任何 LLM / SSE / 长计算，只作临界区兜底。
LOCK = threading.Lock()
_TLS = threading.local()      # 线程本地连接（替代旧版共享单连接 CONN）
LLM = None
STAMP = time.strftime('%Y-%m-%d %H:%M:%S')

# ⚠ 2026-10-08 新增（外部审查 A 项）：**服务端会话语境**（`solve/context.py`）。
#   旧版多轮上下文全在前端（`lastTurn.pids.slice(0, 200)`），而 200 是**语义截断**——
#   上一轮命中 3000 首、下一轮问「其中字数最少的有哪些」，只在**前 200 篇**里找，改变了问题语义。
#   现由服务端按 `sid` 存**完整**结果集（每轮上限 20000，超限**如实**标记 truncated），
#   「集合指代 / 单篇指代 / 条件继承」由 `context.resolve()` 统一判定。
#   仅当请求带 `sid` 时才建会话 → 既有门禁（不带 sid）不产生会话、逐字不变。
SESSIONS = CONTEXT.ContextStore(dirpath=os.path.join(DATA, 'sessions'))

EXAMPLES = [
    '清 临江仙 仄声比例高于45%',
    '找后段下降的清词',
    '句脚是「愁」的清词有哪些',
    '句脚为平 清 临江仙',
    '朱彝尊的词里最长句超过9句的有哪些',
    '声律模式 仄仄平平仄',
    '宋 念奴娇 平仄比例',
    '宋词与清词总体来说仄声占比哪个更高',   # 聚合题：两种口径都要给
    '唐 李白 静夜思 的平仄',               # 语料外：必须拒答
    '明清之际词人创作风格的语义差异',       # 语义层：必须声明边界
]

# 排序白名单（**不放用户输入进 SQL**）
SORTS = {
    'pid': 'p.pid',
    'ze_desc': 'p.ze_ratio DESC, p.pid',
    'ze_asc': 'p.ze_ratio ASC, p.pid',
    'len_desc': 'p.han_len DESC, p.pid',
    'len_asc': 'p.han_len ASC, p.pid',
    'sent_desc': 'p.sent_n DESC, p.pid',
    'sent_asc': 'p.sent_n ASC, p.pid',
    'long_desc': 'p.longest_len DESC, p.pid',
    'long_asc': 'p.longest_len ASC, p.pid',
    'change_desc': 'p.change DESC, p.pid',
    'change_asc': 'p.change ASC, p.pid',
}
SORTS_PLAIN = {k: v.replace('p.', '') for k, v in SORTS.items()}   # 临时表内用（无别名）
SORT_LABEL = {'pid': '默认（按篇号）', 'ze_desc': '仄声比例 从高到低', 'ze_asc': '仄声比例 从低到高',
              'len_desc': '全篇字数 从多到少', 'len_asc': '全篇字数 从少到多',
              'sent_desc': '句数 从多到少', 'sent_asc': '句数 从少到多',
              'long_desc': '最长句 从长到短', 'long_asc': '最长句 从短到长',
              'change_desc': '变化值 从高到低', 'change_asc': '变化值 从低到高'}
RATIO_BUCKETS = [('0–25%', 0, 25), ('25–40%', 25, 40), ('40–50%', 40, 50),
                 ('50–65%', 50, 65), ('65–100%', 65, 1e9)]
# 检索接口接受的参数**唯一清单**：处理函数、/api/search、/api/summarize、前端表单、门禁
# 全部以它为准。教训（2026-09-30 实测）：参数在 build_where 里支持了，却没加进处理函数
# 的清单 → 条件被**静默丢掉**（tailPz=平 返回全库 26742 篇，看着还像「有结果」）。
SEARCH_PARAMS = ('q', 'author', 'cipai', 'tail', 'tailPz', 'pz', 'minZe', 'maxZe', 'minLen',
                 'maxLen', 'minSent', 'maxSent', 'minLong', 'changeMin', 'changeMax',
                 'thrMin', 'thrMax', 'scene', 'sort', 'page', 'size', 'dynasty',
                 # ⚠ 2026-10-06 修（外部审查 P1，本轮第 1/2 项）：
                 #   改前 → 清单里**没有**这两对键：/api/search 用
                 #     `params = {k: g(k) for k in SEARCH_PARAMS}` 过滤，
                 #   · authorMode/cipaiMode：q_nl2query 回填的 `exact` 语义被**静默丢弃**，
                 #     服务端退回 contains，与 Ask 链的结构化等值语义不一致；
                 #   · agg/pair/order_by：nl2query 理解出的**跨篇意图**被静默吃掉，
                 #     用户看到普通列表却以为问题被回答了。
                 #   改后 → 收进清单：
                 #   · authorMode/cipaiMode 直接接给 build_where（它已支持 exact/contains/prefix）；
                 #   · agg/pair/order_by **不执行**（那是 ask.answer 的职责），只用于 q_search 的
                 #     intent 字段**如实告知**（见 search_intent()）。
                 'authorMode', 'cipaiMode', 'agg', 'pair', 'order_by')
SEARCH_FIELDS = ('pid', 'dynasty', 'author', 'cipai', 'title', 'sent_n', 'han_len', 'ping',
                 'ze', 'ze_ratio', 'change', 'scene', 'longest_len', 'threshold', 'raw')

# 「检索结果成文」用的提示词与边界句（写在这里，改起来看得见；仍然要过四道护栏）
SUM_SYS = ('你是清代词律声情研究助手的表述层。你只负责把给定的事实清单写成通顺的中文：'
           '不得添加清单之外的任何数字、人名、篇名或结论；不要给语料原文加引号；'
           '结尾必须包含「不能」这样的限定词，说明结论只反映形式与声调层面。')
SUM_TASK = ('请依据下面的事实清单写 2–4 句总结（客观、简洁，不必逐篇罗列），'
            '最后一句话说明推断边界。\n\n事实清单：\n')
SUM_BOUND = '以上只反映当前文本的形式与声调配置，不能直接推断作者意图、时代因果或作品优劣。'


def get_llm():
    global LLM
    if LLM is None:
        LLM = LLM_MOD.LLM()
    return LLM


def get_conn():
    """**线程本地连接**（每线程一条）。

    ⚠ 2026-10-06 修（外部审查 P1-28/29）：旧版是共享单连接 + check_same_thread=False，
    必须靠一把全局 LOCK 才能避免「线程 A 与线程 B 同时用同一条连接」；而该 LOCK 又被用来
    包住**含大模型调用的整段问答**（单次 1.4~5 秒）→ 所有请求被最慢的 LLM 串行化，
    ThreadingHTTPServer 的高并发形同虚设。
    现改为线程本地连接：问答链全程**只读**（ask.py 无任何写语句），读读天然可并发，
    共享连接的竞态从根上消失；LOCK 退化为临界区兜底，不再包 LLM / SSE / 长计算。
    """
    c = getattr(_TLS, 'conn', None)
    if c is None:
        c = sqlite3.connect(DB, check_same_thread=False)
        c.row_factory = sqlite3.Row
        _TLS.conn = c
    return c


def _num(v, cast=float):
    try:
        return cast(v)
    except (TypeError, ValueError):
        return None


def _tail_chars(s):
    return [c for c in re.split(r'[\s,，、;；]+', (s or '').strip()) if c][:20]


def _pz_glob(pat):
    """平仄模式 → SQLite GLOB 模式：平/仄 原样，`?`/`？` 为通配，**其余字符一律拒绝**。

    ⚠ 2026-10-06 修（外部审查 P1-34）：旧版把「不是 平/仄 的字符」**静默当通配符**，
    于是「平仄abc」被当成「平仄???」照常检索——用户打错却拿到一个看起来正常的答案；
    超长还静默截断到 40 位。现改为严格白名单：非法字符 / 超长 → 抛 ValueError，
    由路由层转成 400 INVALID_QUERY（与 Ask 链 validate_extras() 的白名单同一口径）。
    """
    pat = (pat or '').strip()
    if not pat:
        return None
    if len(pat) > 40:
        raise ValueError('声律模式过长（最多 40 位，当前 %d 位）' % len(pat))
    bad = sorted({c for c in pat if c not in '平仄?？'})
    if bad:
        raise ValueError('声律模式含非法字符「%s」——只允许「平」「仄」「?」「？」'
                         % ''.join(bad))
    return '*' + ''.join(c if c in '平仄' else '?' for c in pat) + '*'


_SYNC_CACHE = {}


def _tables_in_sync(conn):
    """去重表（cipai/authors）是否与 poems 完全一致。

    一致才能把 `p.cipai LIKE '%x%'` 改写成
    `p.cipai IN (SELECT cipai FROM cipai WHERE cipai LIKE '%x%')`——
    后者只在 1.4 万行的小表上做 LIKE，外层的 IN 走 `idx_poems_cipai` 索引，
    省掉 5.9 万行的全表扫描（实测单条件检索 460ms → 见报告）。不一致就退回 LIKE（语义永远等价）。
    """
    key = id(conn)
    hit = _SYNC_CACHE.get(key)
    if hit is None:
        try:
            ok = True
            for col, tab in (('cipai', 'cipai'), ('author', 'authors')):
                a = conn.execute('SELECT COUNT(DISTINCT %s) FROM poems' % col).fetchone()[0]
                b = conn.execute('SELECT COUNT(*) FROM %s' % tab).fetchone()[0]
                if a != b:
                    ok = False
                    break
            hit = ok
        except sqlite3.Error:
            hit = False
        _SYNC_CACHE[key] = hit
    return hit


def build_where(p, conn=None):
    """结构化条件 → (WHERE 子句, 参数)。**条件之间是「且」**；句级条件走 lines 表。"""
    # ⚠ 2026-10-06 修（外部审查 P1-32/33）：
    #   · dynasty/author/cipai 现支持**多值**（空格/逗号/分号分隔 → OR 并集）。旧版是单值
    #     `LIKE '%整串%'`，于是 nl2query 听出的多值（如「高旭和纳兰性德」）回填到表单后
    #     要么被丢成空、要么整串失配。
    #   · author/cipai 支持**三种匹配语义**（contains 默认 / exact / prefix）：与 Ask 链
    #     QuerySpec 的结构化等值语义可显式对齐（nl2query 回填时带 Mode=exact）。
    #   · 单值 + 默认 contains 时生成的 SQL 与旧版逐字等价（仅多一层括号，AND 连接下恒等）。
    def _multi(key, default=None):
        vals = [x for x in re.split(r'[\s,，;；]+', (p.get(key) or '').strip()) if x]
        return vals or ([default] if default else [])

    def _field(col, key, mode_key):
        vals = _multi(key)
        if not vals:
            return
        mode = (p.get(mode_key) or 'contains').strip()
        if mode == 'exact':
            where.append('(' + ' OR '.join('%s = ?' % col for _ in vals) + ')')
            args.extend(vals)
        elif mode == 'prefix':
            where.append('(' + ' OR '.join('%s LIKE ?' % col for _ in vals) + ')')
            args.extend(v + '%' for v in vals)
        else:                                  # contains（默认；向后兼容旧调用）
            where.append('(' + ' OR '.join('%s LIKE ?' % col for _ in vals) + ')')
            args.extend('%' + v + '%' for v in vals)

    _dyns = _multi('dynasty', '清')
    where = ['(' + ' OR '.join('p.dynasty = ?' for _ in _dyns) + ')']
    args = list(_dyns)
    q = (p.get('q') or '').strip()
    if q:
        where.append('(p.author LIKE ? OR p.cipai LIKE ? OR p.title LIKE ? OR p.raw LIKE ?)')
        args += ['%' + q + '%'] * 4
    # 实测（EXPLAIN QUERY PLAN）：`dynasty = '清'` 已让 SQLite 走 idx_poems_dyn，
    # 再把 LIKE 改写成 IN 子查询只是多一层、反而慢 25%（33ms vs 26ms）→ 保持 LIKE。
    _field('p.author', 'author', 'authorMode')
    _field('p.cipai', 'cipai', 'cipaiMode')
    chars = _tail_chars(p.get('tail'))
    if chars:
        where.append('EXISTS(SELECT 1 FROM lines l WHERE l.pid = p.pid AND l.tail IN (%s))'
                     % ','.join('?' * len(chars)))
        args += chars
    g = _pz_glob(p.get('pz'))
    if g:
        where.append('EXISTS(SELECT 1 FROM lines l WHERE l.pid = p.pid AND l.pz GLOB ?)')
        args.append(g)
    tp = (p.get('tailPz') or '').strip()
    if tp in ('平', '仄'):
        # 句脚平仄 = 该句平仄串的最后一个字（与 retrieve._sql 同一口径）
        where.append('EXISTS(SELECT 1 FROM lines l WHERE l.pid = p.pid AND substr(l.pz, -1, 1) = ?)')
        args.append(tp)
    for key, col, op in (('minLen', 'p.han_len', '>='), ('maxLen', 'p.han_len', '<='),
                         ('minSent', 'p.sent_n', '>='), ('maxSent', 'p.sent_n', '<='),
                         ('minZe', 'p.ze_ratio', '>='), ('maxZe', 'p.ze_ratio', '<='),
                         ('minLong', 'p.longest_len', '>='),
                         ('changeMin', 'p.change', '>='), ('changeMax', 'p.change', '<='),
                         ('thrMin', 'p.threshold', '>='), ('thrMax', 'p.threshold', '<=')):
        v = _num(p.get(key))
        if v is not None:
            where.append('%s %s ?' % (col, op))
            args.append(v)
    if (p.get('scene') or '').strip():
        where.append('p.scene = ?')
        args.append(p['scene'].strip())
    return ' AND '.join(where), args


def cond_text(p):
    """把条件写成人话（回答里要如实显示「我到底按什么查的」）。

    ⚠ 2026-10-06 修（外部审查 P2，本轮第 3 项）：
      改前 → `if dynasty and dynasty != '清'` 只在**非清**时才写朝代；dynasty 为空或 '清' 时
        一个朝代字样都不写，末尾回退成「（无条件：全库）」。
        但 `build_where` 对空 dynasty 会默认补 `p.dynasty='清'`（见 `_multi('dynasty', '清')`，
        第 235 行），即 `q_search(conn, {})` 实际**只搜清词**。于是「解释口径（全库）」与
        「执行口径（仅清）」不符，会污染 /api/search、/api/summarize、调试日志与 LLM facts。
      改后 → 始终如实写出检索范围：未显式给 dynasty 写「朝代=清（默认）」，显式给就照实写。
      依据：`build_where` 的默认范围**恒为清**，当前不存在「跨全库」的检索路径，
        因此不再输出「全库」字样（末尾的兜底分支保留仅为防御，正常不可达）。
    """
    parts = []
    dyn = (p.get('dynasty') or '').strip()
    parts.append(('朝代=%s' % dyn) if dyn else '朝代=清（默认）')
    for k, label in (('q', '关键词'), ('author', '词人'), ('cipai', '词牌'), ('tail', '句脚字'),
                     ('tailPz', '句脚平仄'), ('pz', '声律模式'), ('scene', '声情')):
        if (p.get(k) or '').strip():
            parts.append('%s=%s' % (label, str(p[k]).strip()))
    rng = [('字数', p.get('minLen'), p.get('maxLen')), ('句数', p.get('minSent'), p.get('maxSent')),
           ('仄声比例', p.get('minZe'), p.get('maxZe')), ('最长句', p.get('minLong'), None),
           ('变化值', p.get('changeMin'), p.get('changeMax')),
           ('长句阈值', p.get('thrMin'), p.get('thrMax'))]
    for label, lo, hi in rng:
        if _num(lo) is not None or _num(hi) is not None:
            parts.append('%s∈[%s,%s]' % (label, lo if _num(lo) is not None else 0,
                                         hi if _num(hi) is not None else '∞'))
    return '　'.join(parts) or '（无条件：全库）'


def _intent_val(v):
    """把 HTTP 传来的意图串还原：能解析成 JSON 就还原对象，否则原样返回（None＝未给）。"""
    s = (v or '').strip() if isinstance(v, str) else v
    if not s:
        return None
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return s


def search_intent(p):
    """识别 nl2query 理解出、但 **/api/search 无权执行**的跨篇意图（分组统计/配对/排序）。

    ⚠ 2026-10-06 新增（外部审查 P1，本轮第 2 项）：
      改前 → `agg`/`pair`/`order_by` 根本没进 SEARCH_PARAMS：用户把 nl2query 的理解结果
        回填到检索表单后，这三类意图被**静默吃掉**——「哪个词人的词最多」退化成普通列表，
        用户看到结果还以为问题被回答了。
      改后 → 本函数如实识别并回吐 `intent`：`unsupported_by_search=True` + `hint`，
        前端据此提示「该问题属于分组统计/配对/排序题，请到问答页提问」。
      **规则**：宁可明确说「这里不执行」，也不要静默忽略导致用户看到错误结果。
      为什么不在 /api/search 里执行它们：那是 `ask.answer` 的职责（聚合链/配对链），
        在这里重实现会引入巨大重复实现，且答案口径会与问答页分叉。
    """
    agg = _intent_val(p.get('agg'))
    pair = _intent_val(p.get('pair'))
    order_by = (p.get('order_by') or '').strip() or None
    present = bool(agg or pair or order_by)
    hint = ''
    if present:
        what = []
        if agg:
            what.append('分组统计/对比')
        if pair:
            what.append('配对')
        if order_by:
            what.append('按指标排序取值')
        hint = ('本页是「多条件检索」，**不执行**%s——这类问题请到「问答页」提问（由 ask.answer '
                '负责）。本页仍按下方结构化条件返回一份**普通列表**，仅供参考，它不是该问题的答案。'
                % '／'.join(what))
    return {'agg': agg, 'pair': pair, 'order_by': order_by,
            'unsupported_by_search': present, 'hint': hint}


def q_search(conn, p):
    """结构化检索：命中总数 + 当前页 + 分面统计 + 回显 SQL（可溯源）。"""
    t0 = time.time()
    where, args = build_where(p, conn)
    page = max(1, _num(p.get('page'), int) or 1)
    size = min(200, max(1, _num(p.get('size'), int) or 50))
    sort = SORTS.get(p.get('sort') or 'pid', SORTS['pid'])
    # 写法选择（全部有实测依据，见优化报告）：
    #   · 合并聚合：5 个比例分桶 + count/avg/min/max 由原来 6 条各扫一遍 → **一条** SQL；
    #     author/cipai/scene 三个分面由 3 条 → **一条** UNION ALL（各自分支内 ORDER BY+LIMIT）。
    #   · 句脚分面用 `l.pid IN (子查询)` 而不是 JOIN：JOIN 的计划是 **SCAN lines**（全表 42 万行，
    #     实测 125~328 ms），IN 写法走 lines 的主键索引（小集合 0 ms、2.7 万篇 234 ms）。
    #   · 不再建临时表：实测 CREATE TEMP TABLE 本身要 172 ms（且大命中集拷贝更贵），
    #     而下面 4 条走索引的扫描在 439 篇命中时合计 < 5 ms。
    total = conn.execute('SELECT COUNT(1) FROM poems p WHERE %s' % where, args).fetchone()[0]
    rows = conn.execute('SELECT %s FROM poems p WHERE %s ORDER BY %s LIMIT ? OFFSET ?'
                        % (','.join('p.' + f for f in SEARCH_FIELDS), where, sort),
                        args + [size, (page - 1) * size]).fetchall()
    _fac = conn.execute(
        "SELECT * FROM (SELECT 'author' d, p.author v, COUNT(1) c FROM poems p WHERE %(w)s "
        'GROUP BY p.author ORDER BY 3 DESC, 2 LIMIT 12) '
        "UNION ALL SELECT * FROM (SELECT 'cipai', p.cipai, COUNT(1) FROM poems p WHERE %(w)s "
        'GROUP BY p.cipai ORDER BY 3 DESC, 2 LIMIT 12) '
        "UNION ALL SELECT * FROM (SELECT 'scene', p.scene, COUNT(1) FROM poems p WHERE %(w)s "
        'GROUP BY p.scene ORDER BY 3 DESC)' % {'w': where}, args + args + args).fetchall()
    f_tl = conn.execute(
        "SELECT l.tail, COUNT(1) c FROM lines l WHERE l.pid IN (SELECT pid FROM poems p WHERE %s) "
        "AND l.tail IS NOT NULL AND l.tail <> '' GROUP BY l.tail ORDER BY c DESC, l.tail LIMIT 12"
        % where, args).fetchall()
    _st_sql = ('SELECT COUNT(1), AVG(p.ze_ratio), MIN(p.ze_ratio), MAX(p.ze_ratio),'
               ' AVG(p.han_len), MAX(p.han_len),' + ','.join(
                   'SUM(CASE WHEN p.ze_ratio >= %s AND p.ze_ratio < %s THEN 1 ELSE 0 END)'
                   % (lo, hi) for _n, lo, hi in RATIO_BUCKETS) +
               ' FROM poems p WHERE %s' % where)
    st = conn.execute(_st_sql, args).fetchone()
    def _facet(dim, limit=None, tie=True):
        """把合并查询的结果拆回单维，并按**原实现的次序**复排：
        author/cipai 原为 `ORDER BY c DESC, v LIMIT 12`（并列按值升序），scene 原为 `ORDER BY c DESC`。
        UNION ALL 不保证分支内顺序，故这里显式复排，保证与旧实现逐字段一致。"""
        items = [[v, c] for d, v, c in _fac if d == dim]
        items.sort(key=(lambda t: (-t[1], t[0] if t[0] is not None else '')) if tie
                   else (lambda t: -t[1]))
        return items[:limit] if limit else items
    f_au = _facet('author', 12)
    f_cp = _facet('cipai', 12)
    f_sc = _facet('scene', None, tie=False)
    ratio = {RATIO_BUCKETS[i][0]: (st[6 + i] or 0) for i in range(len(RATIO_BUCKETS))}
    stats = {'n': st[0], 'ze_mean': round(st[1], 1) if st[1] is not None else None,
             'ze_min': st[2], 'ze_max': st[3],
             'len_mean': round(st[4], 1) if st[4] is not None else None, 'len_max': st[5]}
    return {'total': total, 'page': page, 'size': size,
            'rows': [dict(zip(SEARCH_FIELDS, r)) for r in rows],
            'facets': {'author': f_au, 'cipai': f_cp, 'tail': [[a, c] for a, c in f_tl],
                       'scene': f_sc, 'ratio': ratio},
            'stats': stats,
            'where': where, 'order_by': sort, 'cond_text': cond_text(p),
            'sorts': SORT_LABEL,
            # ⚠ 本轮第 2 项：如实回吐「识别到的、但 /api/search 不执行」的跨篇意图。
            #   纯附加字段（离线前端与门禁均按可选处理），零回归。
            'intent': search_intent(p),
            'ms': int((time.time() - t0) * 1000)}


def q_nl2query(conn, question, use_llm=True):
    """把一句自然语言**听成**结构化条件（大模型理解层；字段逐个经引擎校验）。

    返回的 cond 与 /api/search 的参数一一对应，前端回填到表单里**可人工修改**再检索；
    落不到库上的字段与没听懂的片段一律如实带回（不静默丢）。
    """
    client = get_llm() if use_llm else None
    # ⚠ 2026-10-06 修（外部审查 P1-29）：不再持全局锁调用大模型（含 LLM，1~5 秒）。
    spec, note = ASK.understand(conn, question, llm=client, llm_parse=bool(use_llm))
    cond = {}
    if spec.tail_any:
        cond['tail'] = ' '.join(spec.tail_any)
    if spec.pz:
        cond['pz'] = spec.pz
    if spec.scene:
        cond['scene'] = spec.scene
    rng = spec.rng or {}
    for src, dst in (('ze_min', 'minZe'), ('ze_max', 'maxZe'), ('len_min', 'minLen'),
                     ('len_max', 'maxLen'), ('sent_min', 'minSent'), ('sent_max', 'maxSent')):
        if rng.get(src) is not None:
            cond[dst] = rng[src]
    # ⚠ 2026-10-06 修（外部审查 P1-33）：旧版「多值一律置空」把「高旭和纳兰性德」这类
    #   多值理解结果直接丢弃（只有恰好一个值才回填）。现按空格拼接保留**全部**值
    #   （build_where 已支持多值 OR），并显式声明 exact 语义以对齐 Ask 链（P1-32）。
    if spec.author_any:
        cond['author'] = ' '.join(spec.author_any)
        cond['authorMode'] = 'exact'
    if spec.cipai_any:
        cond['cipai'] = ' '.join(spec.cipai_any)
        cond['cipaiMode'] = 'exact'
    if spec.keywords:
        cond['q'] = ' '.join(spec.keywords)
    if spec.tail_pz:
        cond['tailPz'] = spec.tail_pz
    for src, dst in (('change_min', 'changeMin'), ('change_max', 'changeMax'),
                     ('thr_min', 'thrMin'), ('thr_max', 'thrMax')):
        if rng.get(src) is not None:
            cond[dst] = rng[src]
    if spec.dynasty_any:
        # 同上（P1-33）：保留全部朝代值（build_where 的 dynasty 已支持多值 OR）。
        cond['dynasty'] = ' '.join(spec.dynasty_any)
    return {'cond': cond, 'describe': spec.describe(), 'source': note.get('source'),
            'dropped': note.get('dropped') or [], 'notes': note.get('notes') or [],
            'unparsed': spec.unparsed or [], 'unsupported': spec.unsupported,
            'agg': spec.agg, 'pair': spec.pair, 'order_by': spec.order_by,
            'llm': {'available': bool(client and client.available()),
                    'model': (client.name if client else None)}}


def _spec_of(p):
    """把结构化条件转成 QuerySpec（只为让证据块**优先展示满足条件的句**）。

    为什么需要：引文护栏要求引号里的字串能在证据池里找到；
    若展示的句子不是「满足条件的那一句」，模型引一句句脚字就必定被护栏判为凭空引用。
    """
    sp = RT.QuerySpec()
    tc = _tail_chars(p.get('tail'))
    if tc:
        sp.tail_any = tc
    if (p.get('pz') or '').strip():
        sp.pz = p['pz'].strip()
    return sp if (tc or sp.pz) else None


def _llm_summary(client, spec_text, facts, blocks):
    """让大模型把事实清单写成一段话；返回 (文本, 未通过项)。**护栏不过就丢弃。**"""
    raw = client.chat([{'role': 'system', 'content': SUM_SYS},
                       {'role': 'user', 'content': SUM_TASK + facts}],
                      temperature=0.2, max_tokens=400)
    if not raw:
        return None, '大模型无返回：%s' % (getattr(client, 'last_error', '') or '未知原因')
    body = raw.strip() + '\n【推断边界｜数值型】' + SUM_BOUND
    probs = []
    sf = SAFETY.check(body, 'out')
    if not sf['ok']:
        probs.append('内容安全：%s' % sf['category'])
    allow = re.findall(r'\d+(?:\.\d+)?', spec_text) + [len(blocks)]
    for b in blocks:
        allow += re.findall(r'\d+', b.get('pid', ''))
    okg, p2 = GUARD.verify(body, blocks, boundary_kind='数值型', allow=allow)
    if not okg:
        probs += list(p2)[:3]
    return body, '；'.join(probs)


def q_summarize(conn, p, use_llm=True):
    """把一批检索结果写成一段话。

    **数字仍然全部由引擎给**：先把命中集合的客观事实列成清单，再让大模型只负责措辞；
    写出来的整段还要过「数字/引用/边界/内容安全」四道护栏，不过就丢掉并回退模板。
    连着网也能优雅降级：模型超时/断连（实测碰到过 RemoteDisconnected）就给出**确定性摘要**
    并如实注明原因，而不是让页面开天窗。
    """
    res = q_search(conn, p)
    st = res['stats']
    spec_text = ('%s；命中 %d 篇；仄声比例 篇均 %s%%、最低 %s%%、最高 %s%%；字数最多 %s 字'
                 % (res['cond_text'], res['total'], st['ze_mean'], st['ze_min'], st['ze_max'],
                    st['len_max']))
    fallback = ('【确定性摘要】%s。共命中 %d 篇；这些篇目的仄声比例平均 %s%%，'
                '区间 %s%%–%s%%；最长的一篇 %s 字。'
                % (res['cond_text'], res['total'], st['ze_mean'], st['ze_min'], st['ze_max'],
                   st['len_max']))
    pids = [r['pid'] for r in res['rows'][:3]]
    drows = []
    for x in pids:
        r0 = conn.execute('SELECT * FROM poems WHERE pid=?', (x,)).fetchone()
        if r0 is not None:
            drows.append(dict(r0))          # evidence.build_blocks 要的是 dict
    blocks = EV.build_blocks(conn, drows, with_lines=3, spec=_spec_of(p))
    facts_res = {'spec': spec_text, 'blocks': blocks,
                 'agg_facts': ['【集合统计】命中 %d 篇；仄声比例 篇均 %s%%、最低 %s%%、最高 %s%%；'
                               '篇均 %s 字'
                               % (res['total'], st['ze_mean'], st['ze_min'], st['ze_max'],
                                  st['len_mean'])]}
    out = {'total': res['total'], 'cond_text': res['cond_text'], 'stats': st,
           'facts': GEN.facts(facts_res), 'ok': False, 'text': fallback, 'model': None,
           'fallback': True, 'problems': ['未启用大模型或未就绪'], 'llm_available': False}
    client = get_llm() if use_llm else None
    if client is not None and client.available():
        out['llm_available'] = True
        text, why = None, '未尝试'
        # ⚠ 2026-10-06 修（外部审查 P0，本轮第 4 项）：**网络调用不持锁**。
        #   改前 → `for attempt in (1,2): with LOCK: text, why = _llm_summary(...)`。
        #     `_llm_summary` 会发大模型**网络请求**（最坏 2×25 秒），整段压在全局 LOCK 上 →
        #     期间任何人点「多条件检索」都被阻塞几十秒（ThreadingHTTPServer 形同虚设）。
        #   改后 → _llm_summary 全程**不持锁**。
        #   锁边界说明：本函数对数据库的访问只有上面的 `q_search(conn, p)` 与取 3 篇
        #     `SELECT ... WHERE pid=?`（均**只读**，且连接是线程本地 get_conn()）→
        #     读读天然可并发，无需 LOCK；纯计算（护栏/安全校验）更不需要。
        #     若将来在此引入**写**操作，必须只在该极小片段单独持锁（不要包网络调用）。
        for attempt in (1, 2):                       # 断连/超时就再试一次（实测碰到过）
            text, why = _llm_summary(client, spec_text, out['facts'], blocks)
            if text is not None and not why:
                break
        out.update({'ok': bool(text is not None and not why),
                    'model': client.name, 'problems': ([why] if why else [])})
        if text is not None and not why:
            out['text'] = text
            out['fallback'] = False
        else:
            out['text'] = fallback
            out['fallback'] = True
    return out


def q_compare(conn, group_by, values, metric):
    """分组对比：两种口径都给出（篇均＝各篇指标平均；加权＝组内总量之比）。"""
    gb = group_by if group_by in AGG.GROUPS else 'dynasty'
    mt = metric if metric in AGG.METRICS else 'ze_ratio'
    vals = [v for v in re.split(r'[,，\s]+', values or '') if v]
    if not vals:
        vals = ['宋', '清']
    with LOCK:
        rows = AGG.stats(conn, gb, vals, mt)
        cmp_ = AGG.compare(rows, mt)
    return {'group_by': gb, 'metric': mt, 'rows': rows, 'cmp': cmp_,
            'text': AGG.render(rows, cmp_, gb, mt)}


def _clean_ask_result(res, client, t0):
    """把问答结果整理成前端 JSON（**q_ask 与流式端点共用**，避免两处走样）。"""
    res['blocks'] = [{k: v for k, v in b.items() if k != 'raw'} for b in res['blocks']]
    res['verify'] = {'ok': res['verify'][0], 'problems': res['verify'][1]}
    # ⚠ 2026-10-05 新增（朋友对照）：把「为什么是这个结论/为什么答不出」**结构化成八态**，
    #   附在结果里（纯附加字段，不改既有答句、进不了 solver → 零回归安全）。
    try:
        import answer_reason as _AR
        res['reason'] = _AR.classify(res)
    except Exception:
        res['reason'] = None
    if res.get('spec') and hasattr(res['spec'], 'get'):
        res['spec'] = {k: v for k, v in res['spec'].items()
                       if isinstance(v, (str, int, float, list, type(None)))}
    if res.get('narrative'):
        res['narrative'] = {k: v for k, v in res['narrative'].items() if k != 'raw'}
    if res.get('extreme'):
        ei = dict(res['extreme'])
        ei['ties'] = [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in ei['ties']]
        res['extreme'] = ei
    if res.get('pair'):                    # 配对题：组数/对数与独立复核结果一并回吐
        pj = dict(res['pair'])
        pj['by_dyn'] = [list(x) for x in (pj.get('by_dyn') or [])]
        res['pair'] = pj
    res['llm'] = {'available': bool(client and client.available()),
                  'model': (client.name if client else None)}
    res['ms'] = int((time.time() - t0) * 1000)
    return res


def _split_ctx_pids(raw, limit=200):
    """把 `ctx_pids` 的原始入参归一成「去重、保序、≤limit 个」的 pid 列表。

    入参形态（前端/HTTP 都可能给）：
      · 逗号或空白分隔的字符串："p1,p2" / "p1 p2"；
      · 重复参数（parse_qs 给了 list）：["p1,p2", "p3"]；
      · None / 空 → []。
    上限 200 个：多轮上下文只需「上一轮结果集」的规模信息，防超长 URL 与无关膨胀。
    """
    items = []

    def _eat(v):
        if v is None:
            return
        if isinstance(v, (list, tuple)):
            for x in v:
                _eat(x)
            return
        items.extend([t for t in re.split(r'[,，\s]+', str(v)) if t])

    _eat(raw)
    seen, out = set(), []
    for pid in items:
        if pid not in seen:
            seen.add(pid)
            out.append(pid)
            if len(out) >= limit:
                break
    return out


def _answer_accepts_ctx_pids():
    """特性探测：`ask.answer` 是否已经有 `ctx_pids` 形参。

    背景（多轮「结果集」通路，2026-10-08）：前端把上一轮命中的 pid 集合经 `ctx_pids` 送到
    服务端，最终要写进 `spec.ctx_pids`。但 `ask.answer` 的该形参由**另一条战线**负责加——
    在对方改完之前硬传会 `TypeError`。故这里做一次**特性探测**：支持才透传，不支持就
    **一字不传**（旧行为逐字不变、不报错、不回归）。
    """
    try:
        import inspect as _inspect
        return 'ctx_pids' in _inspect.signature(ASK.answer).parameters
    except (TypeError, ValueError):
        return False


# 模块加载时探测一次（改 ask.py 后重启服务即重新探测）
_ASK_HAS_CTX_PIDS = _answer_accepts_ctx_pids()


def _ctx_pids_kwargs(ctx_pids):
    """返回透传用的关键字参数：请求带了 id 且后端已支持时给 {'ctx_pids': [...]}，否则 {}。"""
    pids = _split_ctx_pids(ctx_pids)
    if pids and _ASK_HAS_CTX_PIDS:
        return {'ctx_pids': pids}, pids
    return {}, pids


# 服务端会话可交给 `ask.answer` 的 pid 上限：贴 SQLite 宿主变量上限（本机 32766）留足余量。
# 会话自身每轮上限 20000（见 context.MAX_PIDS_PER_TURN），故正常不会触发这里的截断。
MAX_CTX_PIDS = 20000


def _pids_to_answer_kwargs(pids):
    """把「服务端会话解析出的完整 pid 集」编成 `ask.answer` 的透传参数。

    与前端兜底的 `_ctx_pids_kwargs`（≤200）不同：这里承载的是**完整集合**，
    因此不做 200 截断；仅在超过 SQLite 宿主变量上限时**如实**截断（由调用方在
    `session.ctx_truncated` 上标记），绝不静默。
    """
    seq, seen = [], set()
    for x in (pids or []):
        s = str(x).strip()
        if s and s not in seen:
            seen.add(s)
            seq.append(s)
    cut = False
    if len(seq) > MAX_CTX_PIDS:
        seq = seq[:MAX_CTX_PIDS]
        cut = True
    if seq and _ASK_HAS_CTX_PIDS:
        return {'ctx_pids': seq}, seq, cut
    return {}, seq, cut


def _resolve_context(session, resolved, carry, ctx_arg, pids_arg):
    """把「会话指代分类结果 + 显式勾选 + 前端兜底」合成本轮实际使用 `(ctx, pids, info)`。

    · 指代命中（set/single/inherit）→ **服务端会话**为准（完整集合 / 单篇 / 条件继承）；
    · `ambiguous`（上一轮多篇却用「那首」）→ 不承接，如实附上说明（`info['note']`）；
    · 无指代 → 仅在用户**显式勾选**「承上一轮结果集」时才承接（保留既有语义）；
    · 会话不可用（sid 缺失/无历史）→ **退回前端 `ctx_pids` 兜底机制**（≤200，明标降级）。
    """
    info = {'ref_kind': resolved.get('kind') if resolved else 'none',
            'used_context': False, 'pids_used': 0, 'fallback': False,
            'truncated': None, 'note': None}
    ctx_v = ctx_arg or ''
    fallback = list(pids_arg or [])                       # 前端兜底（旧机制，保留）
    pids_v = list(fallback)
    if fallback:
        info['fallback'] = True
    kind = (resolved or {}).get('kind', 'none')
    if kind == 'set':
        pids_v = list(resolved.get('pids') or [])
        info['used_context'] = True
        info['truncated'] = bool(resolved.get('truncated'))
        if not pids_v:
            # 上一轮确实 0 篇：如实说明「集合落空」，不退回兜底（否则会把范围换成别的东西）。
            info['fallback'] = False
            info['note'] = ('上一轮命中 0 篇（集合为空），集合指代落空——本轮按原问题作答，'
                            '未附加任何结果集范围。')
    elif kind == 'single':
        pids_v = [resolved['pid']]
        info['used_context'] = True
        info['fallback'] = False
    elif kind == 'ambiguous':
        pids_v = []
        info['fallback'] = False
        info['note'] = resolved.get('reason')
    elif kind == 'inherit':
        pids_v = []                                       # 条件继承不锁范围，只补条件
        info['fallback'] = False
        prev_q = resolved.get('question') or ''
        prev_s = resolved.get('spec_desc') or ''
        if prev_q or prev_s:
            ctx_v = ('上一问：%s｜上一轮解析为：%s' % (prev_q, prev_s))[:300]
            info['used_context'] = True
    else:                                                 # none
        if carry and session is not None and session.turns:
            last = session.turns[-1]
            pids_v = list(last.get('result_pids') or [])
            info['used_context'] = True
            info['fallback'] = False
            info['truncated'] = bool(last.get('truncated'))
        elif not fallback:
            pids_v = []
    info['pids_used'] = len(pids_v)
    info['ctx_chars'] = len(ctx_v or '')
    return ctx_v, pids_v, info


def _derive_understanding(q, parse, client, policy, ctx_v, pids_v):
    """**独立再理解一次**，取回本轮所用的 `QuerySpec` 对象与 `note`（供集合身份复核与
    未理解状态）。

    为什么要再理解一次：`ask.answer()` 的返回体里**没有** spec 对象（只有 `spec.describe()`
    字符串），而集合身份校验（外部审查 B）必须有可编译成 SQL 的 spec。这里用与 `answer`
    **完全相同的参数**再走一遍理解层，取得 spec。**不改 ask.py**。
    ⚠ 代价与边界（如实声明）：
      · 若 `parse=1` 且大模型可用，本函数会**多调一次大模型理解**（延迟增加，结论不变）；
      · `ask.answer` 在理解之后还会对 spec 做「题名降级 / 题名兜底」等调整，本函数**不复现**
        那两步 → 极少数含题名条件的问句上，复核所用 spec 可能与检索实际略有差异
        （此时 `set_check` 会给出一条「命中总数不一致」的**信息**，供人工判读）。
    失败一律静默降级（不改动答案本体）。
    """
    try:
        conn = get_conn()
        if parse and client is not None and getattr(client, 'available', lambda: False)():
            spec, note = ASK.understand(conn, q, llm=client, llm_parse=True,
                                        llm_policy=policy, context=ctx_v or None,
                                        ctx_pids=(pids_v or None))
        else:
            spec = RT.parse_query(conn, q)
            if pids_v:
                spec.ctx_pids = list(pids_v)
                RT._finalize(spec)
            status, _msg = ASK._understanding_status(spec)
            note = {'understanding_status': status, 'source': '规则解析'}
            if ctx_v:
                note['notes'] = ['本轮未启用大模型理解；上下文（ctx）只在理解层生效，规则路不受其影响']
        return spec, (note if isinstance(note, dict) else {})
    except Exception as exc:                              # 复核失败绝不影响作答
        return None, {'understanding_status': None,
                      'error': '%s: %s' % (type(exc).__name__, exc)}


def _attach_checks(out, conn, spec, note, result_pids, agg_result=None):
    """把 `set_check` / `understanding_status` 挂到返回体上（有则给、失败则如实标注）。"""
    shown = len([p for p in (result_pids or []) if p])
    _tot = out.get('total')
    try:
        out['set_check'] = AVERIFY.build_set_check(
            conn, spec, result_pids,
            total=(_tot if isinstance(_tot, int) and not isinstance(_tot, bool) else None),
            shown=shown, agg_result=agg_result)
    except Exception as exc:
        out['set_check'] = {'ok': None, 'checked': False,
                            'reason': '集合校验未执行：%s: %s' % (type(exc).__name__, exc)}
        if isinstance(note, dict) and note.get('error'):
            out['set_check']['reflect'] = note['error']
    out['understanding_status'] = (note or {}).get('understanding_status')
    return out


def _result_pids_of(out):
    """从返回体取「结果里给出的 pid 集」：优先显式 `pid`（第 N 名等），否则 `blocks[].pid`。"""
    if out.get('pid'):
        return [out['pid']]
    return [b.get('pid') for b in (out.get('blocks') or []) if b and b.get('pid')]


def _store_turn(session, q, spec, out, result_pids):
    """把本轮落到会话：**完整**结果集（独立复算的命中集优先）、解析摘要、总数。"""
    if session is None:
        return None
    full = None
    try:
        full = AVERIFY.hit_pids(get_conn(), spec)
    except Exception:
        full = None
    store_pids = full if (full is not None) else list(result_pids or [])
    _tot = out.get('total')
    if not (isinstance(_tot, int) and not isinstance(_tot, bool)):
        _tot = len(store_pids) if store_pids else None
    return SESSIONS.add_turn(session, q, (spec.describe() if spec is not None else ''),
                             store_pids, _tot)


def q_ask(q, topk=3, narrate=False, argument=False, parse=False, policy='always', ctx=None,
          ctx_pids=None, sid=None, carry=False):
    t0 = time.time()
    conn = get_conn()
    client = get_llm() if (narrate or argument or parse) else None
    # ① 服务端会话 + 指代分类（外部审查 A）：带 sid 时才建会话。
    session = SESSIONS.get_or_create(sid) if sid else None
    resolved = CONTEXT.resolve(session, q) if session is not None else {'kind': 'none'}
    _fb_pids = _split_ctx_pids(ctx_pids)                  # 前端兜底（≤200）
    ctx_v, pids_v, cinfo = _resolve_context(session, resolved, carry, ctx, _fb_pids)
    # ② 独立再理解一次（取 spec 供复核；见 _derive_understanding 的代价声明）
    spec, note = _derive_understanding(q, parse, client, policy, ctx_v, pids_v)
    # ③ 作答（透传完整集合；仅当后端支持该形参时）
    extra, pids_sent, cut = _pids_to_answer_kwargs(pids_v)
    cinfo['ctx_truncated_send'] = cut
    # ⚠ 2026-10-06 修（外部审查 P1-29）：原先这里 `with LOCK:` 包住整个 ASK.answer（含 LLM，
    #   单次 1.4~5 秒）→ 所有并发问答被串行化。改用线程本地连接后无需持锁。
    res = ASK.answer(conn, q, topk=topk, llm=client,
                     narrate=narrate, argument=argument, llm_parse=parse,
                     llm_policy=policy, context=(ctx_v or None), **extra)
    out = _clean_ask_result(res, client, t0)
    out['ctx_pids'] = {'received': len(pids_sent), 'consumed': bool(extra),
                       'from_session': bool(cinfo.get('used_context'))}
    # ④ 集合身份校验 + 未理解状态
    _attach_checks(out, conn, spec, note, _result_pids_of(out), agg_result=out.get('agg'))
    # ⑤ 会话落盘（完整集合，供下一轮指代）
    turn = _store_turn(session, q, spec, out, _result_pids_of(out))
    out['sid'] = (session.sid if session is not None else (sid or ''))
    if turn is not None:
        out['session'] = {'sid': session.sid, 'turn': len(session.turns),
                          'stored_pids': len(turn['result_pids']),
                          'result_total': turn['result_total'],
                          'truncated': bool(turn['truncated']),
                          'ref_kind': cinfo.get('ref_kind'),
                          'used_context': bool(cinfo.get('used_context')),
                          'from_fallback': bool(cinfo.get('fallback')),
                          'pids_used': cinfo.get('pids_used'),
                          'note': cinfo.get('note')}
    return out


def q_ask_stream(q, topk=3, narrate=True, argument=False, parse=True, policy='auto', ctx=None,
                 ctx_pids=None, sid=None, carry=False):
    """**SSE 流式问答**：把「进度」与「大模型逐字增量」实时推给浏览器。

    为什么要流式：原先网页点一下要**干等 1.4~5 秒**（大模型整段写完才返回）。
    现在 0.1 秒内先给一行状态；**引擎一旦算完（通常 0.05~0.3 秒）就把答案先发出去**
    （engine 事件：结论/证据/护栏，措辞还是模板版），大模型再边写边补「说明」。
    事件类型：status（进度）／engine（**引擎答案先到**）／delta（大模型增量）／
    final（完整 JSON，与 /api/ask 同构）／error。

    ⚠ 2026-10-06 修（外部审查 P1-30）：旧版客户端断开后**后台线程仍会跑完整段 LLM**
    （仅靠 wfile.write 抛 BrokenPipe 被动发现，无任何取消机制；队列还是无界的，连续操作会
    不断堆积）。现版：①每次请求生成 request_id 供日志关联；②队列改**有界**（满则丢弃增量帧，
    绝不阻塞 worker）；③生成器捕获 GeneratorExit / 写失败时置 cancel 事件，worker 在关键点
    检查后尽快收尾（不再 emit、不再堆积）。
    局限（如实声明）：llm.py 的底层 HTTP 请求不支持中途中断，因此**已在飞行中的单次模型调用
    仍会跑完**——但不会再产生级联积压，线程会在该次调用返回后立刻结束。
    """
    import queue as _queue
    import threading as _threading
    import uuid as _uuid
    rid = _uuid.uuid4().hex[:12]
    out = _queue.Queue(maxsize=256)          # 有界：断开后不再无限堆积（见上）
    cancelled = _threading.Event()

    def emit(kind, payload):
        if cancelled.is_set():
            return
        try:
            out.put_nowait((kind, payload))
        except _queue.Full:                  # 消费端已消失/积压：丢最旧一帧，保证新帧能进
            try:
                out.get_nowait()
                out.put_nowait((kind, payload))
            except Exception:
                pass

    def work():
        t0 = time.time()
        try:
            conn = get_conn()
            client = get_llm() if (narrate or argument or parse) else None
            # ① 服务端会话 + 指代分类（与 q_ask 同一套，外部审查 A）。
            session = SESSIONS.get_or_create(sid) if sid else None
            resolved = CONTEXT.resolve(session, q) if session is not None else {'kind': 'none'}
            _fb_pids = _split_ctx_pids(ctx_pids)          # 前端兜底（≤200）
            ctx_v, pids_v, cinfo = _resolve_context(session, resolved, carry, ctx, _fb_pids)
            emit('status', {'text': '正在理解问句…',
                            'model': (client.name if client and client.available() else None)})
            # ② 独立再理解一次（取 spec 供 set_check / understanding_status）
            spec, note = _derive_understanding(q, parse, client, policy, ctx_v, pids_v)
            extra, pids_sent, _cut = _pids_to_answer_kwargs(pids_v)
            _cp = {'received': len(pids_sent), 'consumed': bool(extra),
                   'from_session': bool(cinfo.get('used_context'))}

            def _emit_engine(d):
                eng = _clean_ask_result(dict(d), client, t0)
                eng['ctx_pids'] = dict(_cp)
                _attach_checks(eng, conn, spec, note, _result_pids_of(eng),
                               agg_result=eng.get('agg'))
                emit('engine', eng)

            # ⚠ 2026-10-06 修（P1-29）：不再持全局锁调用 ASK.answer（含 LLM）。
            res = ASK.answer(conn, q, topk=topk, llm=client,
                             narrate=narrate, argument=argument, llm_parse=parse,
                             llm_policy=policy, context=(ctx_v or None),
                             on_delta=lambda t: emit('delta', {'text': t}),
                             # 答案先到：确定性结论一算完即推 engine 事件（前端立即渲染），
                             # 大模型随后只补「说明」——用户不再干等模型整段写完。
                             on_engine=_emit_engine,
                             **extra)
            fin = _clean_ask_result(res, client, t0)
            fin['ctx_pids'] = dict(_cp)
            # ③ 集合身份校验 + 未理解状态；④ 会话落盘（完整集合，供下一轮指代）
            _attach_checks(fin, conn, spec, note, _result_pids_of(fin), agg_result=fin.get('agg'))
            turn = _store_turn(session, q, spec, fin, _result_pids_of(fin))
            fin['sid'] = (session.sid if session is not None else (sid or ''))
            if turn is not None:
                fin['session'] = {'sid': session.sid, 'turn': len(session.turns),
                                  'stored_pids': len(turn['result_pids']),
                                  'result_total': turn['result_total'],
                                  'truncated': bool(turn['truncated']),
                                  'ref_kind': cinfo.get('ref_kind'),
                                  'used_context': bool(cinfo.get('used_context')),
                                  'from_fallback': bool(cinfo.get('fallback')),
                                  'pids_used': cinfo.get('pids_used'),
                                  'note': cinfo.get('note')}
            emit('final', fin)
        except Exception as exc:
            sys.stderr.write('[sse][%s] worker 异常：%s: %s\n' % (rid, type(exc).__name__, exc))
            emit('error', {'error': '%s: %s' % (type(exc).__name__, exc)})
        finally:
            try:
                out.put_nowait(('__end__', None))
            except _queue.Full:
                pass

    _threading.Thread(target=work, daemon=True, name='ask-stream-%s' % rid).start()
    yield _sse('status', {'text': '已收到问题，正在检索语料与核对数字…', 'request_id': rid})
    try:
        while True:
            kind, payload = out.get()
            if kind == '__end__':
                break
            yield _sse(kind, payload)
    except GeneratorExit:                    # 客户端断开（浏览器关闭 / 切页）
        cancelled.set()
        sys.stderr.write('[sse][%s] 客户端断开，已请求后台任务收尾\n' % rid)
        raise
    yield 'data: {"type":"done"}\n\n'


def _sse(kind, payload):
    """SSE 帧。

    ⚠ 2026-10-04 修（代码审查 P2-14）：旧版在 `json.dumps` 之后又 `.replace('\\n','\\\\n')`，
    而 `json.dumps` 已经把字符串内的换行转义成 `\\n` 两个字符，抛出的帧里**不含字面换行**
    —— 那句 replace 是死代码（注释宣称的"防拆帧"并未由它生效，实际靠的是 json.dumps）。
    """
    body = dict(payload or {})
    body['type'] = kind
    return 'data: ' + json.dumps(body, ensure_ascii=False) + '\n\n'


def q_parse(pid):
    c = get_conn()
    with LOCK:
        row = c.execute('SELECT * FROM poems WHERE pid=?', (pid,)).fetchone()
        if row is None:
            return {'error': '没有这一篇：%s' % pid}
        d = dict(row)
        lines = [dict(r) for r in c.execute(
            'SELECT idx,text,han_len,ping,ze,pz,tail FROM lines WHERE pid=? ORDER BY idx', (pid,))]
    out = {k: d.get(k) for k in ('pid', 'dynasty', 'author', 'title', 'cipai', 'sent_n', 'han_len',
                                 'ping', 'ze', 'ze_ratio', 'f_ratio', 'b_ratio', 'change',
                                 'abs_change', 'longest_seq', 'longest_len', 'threshold', 'scene')}
    # ⚠ 2026-10-06 修（在线「逐字解析」显示「最长句第 NaN 句」的根因）：
    #   库里 `longest_seq` 存的是 **JSON 数组字面量的字符串**（`build_corpus.py` 用
    #   `json.dumps` 写入，如 `'[4]'` / `'[1, 3]'`），而前端曾按「、／，」纯文本分隔解析 →
    #   `'[4]'.split(/[、,，]/)` = `['[4]']` → `Number('[4]')` = `NaN` → 渲染成「第 NaN 句」。
    #   这里在**服务端出口统一规范化成真数组**（一处收口，所有消费者拿到同一形态）；
    #   离线路径本就走前端自算（真数组），故只有在线页面中招。
    #   注：`SEARCH_FIELDS` 不含 longest_seq，故检索列表页不受影响。
    _ls = out.get('longest_seq')
    if isinstance(_ls, str):
        try:
            _ls = json.loads(_ls)
        except Exception:
            _ls = [int(x) for x in re.split(r'[、,，\s]+', _ls) if x.strip().isdigit()]
    out['longest_seq'] = [int(x) for x in _ls] if isinstance(_ls, (list, tuple)) else []
    out['lines'] = lines
    out['raw'] = d.get('raw')
    return out


def q_rand(dyn=''):
    c = get_conn()
    with LOCK:
        # 原实现把**全部 58,852 个 pid 取回 Python** 再 random.choice（实测约 50 ms 的纯搬运，
        # 且每次请求都重复分配一个大列表）。改成「先数总数（走索引）→ 随机 OFFSET 取一行」，
        # 由 SQLite 直接定位（LIMIT 1 OFFSET n），内存与时间都与库大小无关。
        where = ' WHERE dynasty=?' if dyn else ''
        args = [dyn] if dyn else []
        n = c.execute('SELECT COUNT(1) FROM poems' + where, args).fetchone()[0]
        if not n:
            return {'error': '没有符合条件的篇目'}
        row = c.execute('SELECT pid FROM poems' + where + ' LIMIT 1 OFFSET ?',
                        args + [random.randrange(n)]).fetchone()
    if not row:
        return {'error': '随机取样失败（请重试）'}
    return q_parse(row[0])


_ASK_HTML_CACHE = {'mtime': None, 'text': None}


def page_ask_html():
    """问答页 HTML（Vue 构建产物）。

    ⚠ 2026-10-05（D15）：问答页已由 Vue3+Vite 重建，产物在 `web/dist/ask/ask.html`。
    本函数负责读取产物并**就地替换生成时间戳探针**（`__STAMP__` → 真实时间），
    保持与离线视图一致的「页面生成时间」约定。产物缺失时给出明确的构建提示，
    而不是白屏——评审机上跑起来「能看到一句话」比「什么都没有」重要。
    """
    idx = os.path.join(DIST_ASK, 'ask.html')
    try:
        mt = os.path.getmtime(idx)
    except OSError:
        return ('<!doctype html><meta charset="utf-8"><title>词律探微</title>'
                '<body style="font:15px/1.8 system-ui;padding:40px;max-width:760px;margin:auto">'
                '<h1>问答页尚未构建</h1>'
                '<p>请先构建前端：</p>'
                '<pre>cd frontend\nnpm install\nnpm run build</pre>'
                '<p>或直接运行 <code>python web/build_views.py</code> 生成离线视图。</p>'
                '</body>')
    if _ASK_HTML_CACHE['mtime'] != mt:
        with open(idx, 'r', encoding='utf-8') as f:
            _ASK_HTML_CACHE['text'] = f.read()
        _ASK_HTML_CACHE['mtime'] = mt
    # 占位符用 @@STAMP@@（**不要**用 __STAMP__：那会连 JS 变量名一起替换掉，见 2026-10-05 实测）。
    return _ASK_HTML_CACHE['text'].replace('@@STAMP@@', STAMP)


class H(BaseHTTPRequestHandler):
    server_version = 'cilv-tanwei/1.0'

    def _send(self, body, ctype='application/json; charset=utf-8', code=200):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        raw = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')      # 免得浏览器拿旧页面报「假 bug」
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *a):
        sys.stderr.write('  · %s\n' % (fmt % a))

    def do_GET(self):
        # ⚠ 2026-10-04：`_sse_started` 是「本连接已发过 SSE 响应头」的标记（见 except 处）。
        #   HTTP keep-alive 下同一连接会服务多个请求，必须在每个请求开头复位——
        #   否则「SSE 之后同一连接上的下一个请求出错」会被误判成"不能再发响应"而静默挂住。
        self._sse_started = False
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        g = lambda k, d='': (qs.get(k, [d])[0] if qs.get(k) else d)
        try:
            if u.path in ('/', '/index_ask.html', '/ask.html'):
                return self._send(page_ask_html(), 'text/html; charset=utf-8')
            # Vue 构建产物的静态资源（JS/CSS/字体），相对 ./assets/ 引用。
            # 问答页资源在 web/dist/ask/assets/；离线四视图资源在 data/vue/assets/。
            # 两处都找，都找不到才 404。
            if u.path.startswith('/assets/'):
                # ⚠ 2026-10-06 修（外部审查 P0-1）：本分支此前**没有任何路径约束**——
                #   `os.path.join(base, 'assets/../../xxx')` 会被 OS 解析掉 `..`，
                #   从而把 assets 目录之外的源码/配置/数据库/模型配置当静态文件回给客户端
                #   （Windows 下 `..\` 同样有效，且 urlparse 不做归一化）。
                #   现统一用 realpath + commonpath 收口：解析后的真实路径必须仍在 base 之内。
                rel = u.path.lstrip('/')
                for base in (DIST_ASK, DIST_VIEWS):
                    b = os.path.realpath(base)
                    p = os.path.realpath(os.path.join(b, rel))
                    try:
                        inside = (p == b) or (os.path.commonpath([b, p]) == b)
                    except ValueError:          # 不同盘符（Windows）：必在 base 之外
                        inside = False
                    if not inside:
                        continue                # 越界一律跳过（连 404 都不区分，避免探测反馈）
                    if os.path.isfile(p):
                        ct = ('text/javascript' if p.endswith('.js') else
                              'text/css' if p.endswith('.css') else 'application/octet-stream')
                        with open(p, 'rb') as f:
                            return self._send(f.read(), ct + '; charset=utf-8')
                return self._send({'error': 'not found: %s' % u.path}, code=404)
            if u.path == '/api/ask':
                b = lambda k: g(k).lower() in ('1', 'true', 'yes', 'on')
                topk = min(10, max(1, _num(g('topk'), int) or 3))
                return self._send(q_ask(g('q'), topk=topk, narrate=b('narrate') or b('llm'),
                                        argument=b('argument'), parse=b('parse'),
                                        ctx=(g('ctx') or '')[:300] or None,
                                        # 多轮「结果集」：支持逗号分隔或重复参数（见 _split_ctx_pids）
                                        ctx_pids=qs.get('ctx_pids'),
                                        # 服务端会话（外部审查 A）：带 sid 时用服务端完整结果集
                                        sid=((g('sid') or '').strip() or None),
                                        carry=b('carry')))
            if u.path == '/api/ask_stream':
                # 流式问答：**不能用 _send**（那会带 Content-Length，浏览器要等整包）
                b = lambda k: g(k).lower() in ('1', 'true', 'yes', 'on')
                topk = min(10, max(1, _num(g('topk'), int) or 3))
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('X-Accel-Buffering', 'no')
                self.end_headers()
                # ⚠ 2026-10-04 修（代码审查 P2-14）：响应头已发出，此后**不能再发第二个响应**。
                #   打标记，供下面的 except 判断（旧版：客户端中断导致 wfile.write 抛
                #   BrokenPipeError，被外层 except 捕获后又 _send(500) —— 对半开连接重发状态行）。
                self._sse_started = True
                for frame in q_ask_stream(g('q'), topk=topk, narrate=b('narrate') or b('llm'),
                                          argument=b('argument'), parse=b('parse'),
                                          policy=g('policy') or 'auto',
                                          ctx=(g('ctx') or '')[:300] or None,
                                          # 多轮「结果集」：支持逗号分隔或重复参数
                                          ctx_pids=qs.get('ctx_pids'),
                                          # 服务端会话（外部审查 A）
                                          sid=((g('sid') or '').strip() or None),
                                          carry=b('carry')):
                    self.wfile.write(frame.encode('utf-8'))
                    self.wfile.flush()
                return
            if u.path == '/api/search':
                params = {k: g(k) for k in SEARCH_PARAMS}
                # ⚠ 2026-10-06 修（外部审查 P1-34）：声律模式先做白名单校验，非法输入
                #   返回 400 INVALID_QUERY（而不是被静默当成通配符照常检索）。
                try:
                    _pz_glob(params.get('pz'))
                except ValueError as ve:
                    return self._send({'error': str(ve), 'code': 'INVALID_QUERY'}, code=400)
                # ⚠ 2026-10-06 修（外部审查 P1，本轮第 5 项）：**去掉该端点上的全局锁**。
                #   改前 → `with LOCK: return self._send(q_search(get_conn(), params))`。
                #   依据（先确认再改，不盲动）：
                #     ① 连接已是**线程本地**（见 get_conn 注释），不存在「两线程共用一条连接」的竞态；
                #     ② 检索链**全程只读**（q_search 只跑 SELECT/COUNT/GROUP BY）；
                #     ③ 本进程**不存在并发写**（服务只读；建库在离线 build_corpus.py 里做），
                #        故 SQLite 的并发读无需应用层串行化——该锁只会把并发搜索串行化。
                #   保留说明：LOCK 仍留给 q_parse/q_rand 等端点作临界区兜底（本轮不在范围内，未动）。
                return self._send(q_search(get_conn(), params))
            if u.path == '/api/nl2query':
                return self._send(q_nl2query(get_conn(), g('q'),
                                             use_llm=g('llm', '1') not in ('0', 'false', 'no')))
            if u.path == '/api/summarize':
                params = {k: g(k) for k in SEARCH_PARAMS if k != 'page'}
                return self._send(q_summarize(
                    get_conn(), params,
                    use_llm=g('llm', '1') not in ('0', 'false', 'no')))
            if u.path == '/api/compare':
                return self._send(q_compare(get_conn(), g('group_by'), g('values'), g('metric')))
            if u.path == '/api/llm':
                c = get_llm()
                return self._send({'available': c.available(), 'model': c.name,
                                   'provider': c.provider,
                                   'hint': '未就绪：设 ZAI_API_KEY / DEEPSEEK_API_KEY / DASHSCOPE_API_KEY'
                                           if not c.available() else '就绪'})
            if u.path == '/api/parse':
                return self._send(q_parse(g('pid')))
            if u.path == '/api/rand':
                return self._send(q_rand(g('dyn')))
            if u.path == '/api/examples':
                return self._send(EXAMPLES)
            # 静态视图：优先提供 Vue 构建产物（data/vue/），回退旧版手写视图（data/*.html）。
            # 两种产物文件同名，因此「构建了就自动用新版」，评审机没跑构建也不至于 404。
            for name in ('parse.html', 'browse.html', 'graph.html', 'review.html', 'index.html'):
                if u.path == '/' + name:
                    for base in (DIST_VIEWS, DATA):
                        p = os.path.join(base, name)
                        if os.path.exists(p):
                            with open(p, 'rb') as f:
                                body = f.read()
                            return self._send(body, 'text/html; charset=utf-8')
            # 离线视图的数据脚本（pack.js / rev.js / stamp.js）与数据文件（graph.json）。
            # 路径白名单，防目录穿越。（/assets/ 已在上面处理。）
            if u.path in ('/pack.js', '/rev.js', '/stamp.js', '/graph.json', '/review_rows.json'):
                rel = u.path.lstrip('/')
                p = os.path.join(DIST_VIEWS, rel)
                if os.path.exists(p):
                    ct = 'application/json' if rel.endswith('.json') else 'text/javascript'
                    with open(p, 'rb') as f:
                        return self._send(f.read(), ct + '; charset=utf-8')
            # 数据与共享脚本（离线视图用；Vue 产物不依赖它们，但旧视图与门禁需要）
            for name in ('web_poems.json', 'metrics.js', 'ui.js', 'app_parse.js', 'app_ask.js',
                         'app_review.js', 'db_metrics.json', 'graph.json', 'expect_search.json'):
                if u.path == '/' + name:
                    p = os.path.join(DATA, name)
                    if os.path.exists(p):
                        ct = ('application/json' if name.endswith('.json') else 'text/javascript')
                        with open(p, 'rb') as f:
                            return self._send(f.read(), ct + '; charset=utf-8')
            return self._send({'error': 'not found: %s' % u.path}, code=404)
        except Exception as exc:                                   # 不让页面白屏
            import traceback
            import uuid as _uuid
            rid = _uuid.uuid4().hex[:12]
            # ⚠ 2026-10-06 修（外部审查 P1-31）：正式部署不应把内部 traceback 回给客户端
            #   （会泄漏本机路径 / 目录结构 / 内部模块名 / 数据库位置 / 配置细节）。
            #   改为：完整堆栈只写服务端日志（按 rid 可查），客户端仅拿 request_id；
            #   本地调试需要细节时设 LVC_DEBUG=1。
            sys.stderr.write('[error][%s] %s: %s\n%s\n'
                             % (rid, type(exc).__name__, exc, traceback.format_exc()))
            if getattr(self, '_sse_started', False):
                # SSE 已发响应头：只能如实记日志，**不能再发第二个响应**（见上方注释）
                sys.stderr.write('[sse][%s] 连接中断或写失败：%s\n' % (rid, type(exc).__name__))
                return
            if os.environ.get('LVC_DEBUG'):
                return self._send({'error': '%s: %s' % (type(exc).__name__, exc),
                                   'trace': traceback.format_exc().splitlines()[-4:],
                                   'request_id': rid}, code=500)
            return self._send({'error': '内部错误（请把 request_id 提供给维护者以定位日志）',
                               'request_id': rid}, code=500)


def main():
    ap = argparse.ArgumentParser(description='词律探微 · 本地问答网页应用')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--no-open', action='store_true')
    a = ap.parse_args()
    if not os.path.exists(DB):
        print('找不到语料库 %s，请先跑：python build_corpus.py --corpus <语料根> --db data/corpus.db'
              % DB)
        return 2
    get_conn()
    # 服务端会话：载入 data/sessions/ 的历史（失败静默，内存仍可用）。
    try:
        _n_sess = SESSIONS.load()
        if _n_sess:
            print('已载入会话 %d 个（data/sessions/）' % _n_sess)
    except Exception as _se:
        print('会话载入跳过：%s: %s' % (type(_se).__name__, _se))
    # 启动预热：首问原要 238 ms（首次编译 + SQLite 页缓存冷），预热后稳定在 40~50 ms。
    # 预热失败不影响启动（只影响首个请求的快慢）。
    try:
        _warm = get_conn()
        _warm.execute('SELECT COUNT(1) FROM poems').fetchone()
        q_search(_warm, {'cipai': '临江仙'})
        q_ask('清 临江仙 仄声比例高于50%', topk=3)
        print('预热完成（首个提问不再吃 200+ ms 的冷启动）')
    except Exception as _e:
        print('预热跳过：%s: %s' % (type(_e).__name__, _e))
    srv = None
    for p in range(a.port, a.port + 10):          # 端口被占就顺延，别让主人对着报错发呆
        try:
            srv = ThreadingHTTPServer((a.host, p), H)
            if p != a.port:
                print('端口 %d 被占用，改用 %d' % (a.port, p))
            a.port = p
            break
        except OSError as exc:
            print('端口 %d 不可用（%s），换一个' % (p, exc))
    if srv is None:
        print('从 %d 起连续 10 个端口都被占用，请用 --port 指定其他端口' % a.port)
        return 2
    url = 'http://%s:%d/' % (a.host, a.port)
    print('词律探微 · 问答应用已启动：%s' % url)
    print('  问答页 %s　多条件检索 %sbrowse.html' % (url, url))
    print('（Ctrl+C 结束；答案带出处与证据块；大模型默认不参与，勾选后才用）')
    if not a.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
    return 0


if __name__ == '__main__':
    sys.exit(main())
