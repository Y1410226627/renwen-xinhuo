# -*- coding: utf-8 -*-
"""build_views.py —— 生成**离线自包含**的四个视图（M0/M12 演示层）+ 前端校验数据。

为什么要自包含：比赛现场可能没有外网、没有服务器；一个能双击打开的 HTML，
比一段「在我机器上能跑」的说明更有说服力。所有页面**不引用任何 CDN**。

架构（2026-09-30 重构，为的是消掉「同一个 bug 修一半」）：
    web/ui.js        页面外观 + 工具函数（CSS / 转义 / 上色 / 导出 / 页脚探针）——唯一来源
    web/app_parse.js 逐字解析 + 多条件检索的应用层（离线内嵌数据 / 在线走 /api/search 同一份代码）
    web/app_review.js 校订队列应用层（数据由 Python 的 csv 模块解析后内嵌，不再 split(',')）
    metrics.js       声律指标的前端独立实现（与 Python 引擎逐字段对照，见 verify_views.js）

产出（都在 data/ 下）：
    index.html      总览页（四个视图 + 复现命令）
    parse.html      视图一·逐字解析与检索（多条件：句脚字／声律模式／字数／仄比／声情…）
    graph.html      视图二·知识图谱（Python 定布局 → SVG；可筛选、悬停高亮）
    review.html     视图三·校订队列（可筛选、可排序、可导出）
    ui.js / app_parse.js / app_review.js / metrics.js
    web_poems.json  清词全库（篇级字段 + 原文；前端据此**自己算**数字）
    db_metrics.json Python 引擎侧导出（供 node 逐字段对照）
    expect_search.json 用 SQL 独立算出的「检索条件 → 命中篇数」（供前端门禁对照）
    graph.json      图谱数据（可被别的工具复用）

用法：python web/build_views.py [--db data/corpus.db] [--out data] [--limit-metrics 3000]
"""
import argparse
import csv as _csv
import io
import json
import math
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))
from pronounce import Pronouncer, default_overrides_path          # noqa: E402

METRIC_FIELDS = ('han_len', 'sent_n', 'ping', 'ze', 'ze_ratio', 'cut', 'f_ratio', 'b_ratio',
                 'change', 'abs_change', 'longest_len', 'threshold', 'scene')
SHARED_JS = ('ui.js', 'app_parse.js', 'app_review.js', 'app_ask.js')

NAV_ITEMS = [('index.html', '总览'), ('parse.html', '逐字解析与检索'),
             ('browse.html', '在线检索（需服务）'), ('graph.html', '知识图谱'),
             ('review.html', '校订队列')]


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def jdump(obj, **kw):
    """内嵌 <script> 用的 JSON 序列化。

    ⚠ 2026-10-04 修（代码审查 P3-8）：`json.dumps` **不转义** `/`，若任一原文含
    `</script>`（或 `<!--`），HTML 解析会在那里提前结束脚本 → 页面崩溃/可注入。
    这里把 `</` 统一转成 `<\/`（JSON 里合法、HTML 里不再构成结束标签）。
    """
    return json.dumps(obj, **kw).replace('</', '<\\/')


def esc_a(s):
    return esc(s).replace('"', '&quot;')


def nav(cur):
    tabs = ''.join('<a%s href="%s">%s</a>' % (' class="on"' if href == cur else '', href, label)
                   for href, label in NAV_ITEMS)
    return ('<header class="top"><div class="in"><div class="brand">词律探微'
            '<small>清代词律声情研究助手 · 本地离线视图</small></div>'
            '<nav class="tabs">%s</nav>'
            '<button id="theme" class="ghost" title="切换日间/夜间">☾ 夜间</button>'
            '</div></header>' % tabs)


def page(title, cur, body, foot, head_extra=''):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s</title>%s</head><body>%s<main>%s</main>%s</body></html>'
            % (title, head_extra, nav(cur), body, foot))


def build_tonemap():
    """字 → 平/仄（'1' 平、'2' 仄）。与引擎**同一份口径**（逐字字典口径）。

    ⚠️ 必须显式传标定表路径：`Pronouncer()` 不传参就**不带标定表**，
    页面数字会与引擎差一个字数（曾实际发生：「绝」被当平声 → 平 59 而非 58）。
    ⚠️ 映射值必须是**单字符**编码；直接把声调数字或字典转成字符串拼进去，
    会让 chars/tones 两个串错位（曾实际发生：错位 708 个字符，页面静默算错）。
    """
    ov = default_overrides_path()
    p = Pronouncer(ov)
    chars, codes = [], []
    for cp in range(0x3400, 0xA000):
        if not (0x3400 <= cp <= 0x4DBF or 0x4E00 <= cp <= 0x9FFF):
            continue
        ch = chr(cp)
        pz = p.ping_ze(ch)
        if pz:
            chars.append(ch)
            codes.append('2' if pz == '仄' else '1')
    assert len(chars) == len(codes)
    tm = dict(zip(chars, codes))
    ov_map = json.load(io.open(ov, encoding='utf-8-sig')) if ov and os.path.exists(ov) else {}
    for zi, v in ov_map.items():
        want = v.get('tone') if isinstance(v, dict) else v
        want = '2' if int(want) in (3, 4) else '1'
        if tm.get(zi) != want:
            raise SystemExit('✗ 标定字未按标定表进映射：%s（映射 %s，期望 %s）'
                             % (zi, tm.get(zi), want))
    return ''.join(chars), ''.join(codes)


def expect_search(con):
    """用 SQL **独立**算出一批「检索条件 → 命中篇数」，给前端门禁当标尺。

    前端（JS）与这里（SQL）是两套实现；两边对不上就说明有一侧的判定写错了。
    """
    cases = [
        ({'q': '纳兰性德'}, "author='纳兰性德'"),
        ({'tail': '愁'}, "EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid AND l.tail='愁')"),
        ({'tail': '灯 声'},
         "EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid AND l.tail IN ('灯','声'))"),
        ({'pz': '仄仄平平仄'},
         "EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid AND l.pz LIKE '%仄仄平平仄%')"),
        ({'minZe': 60}, 'ze_ratio>=60'),
        ({'maxZe': 20}, 'ze_ratio<=20'),
        ({'minLen': 60}, 'han_len>=60'),
        ({'maxSent': 3}, 'sent_n<=3'),
        ({'minLong': 12}, 'longest_len>=12'),
        ({'scene': '后段下降'}, "scene='后段下降'"),
        ({'cipai': '临江仙'}, "cipai LIKE '%临江仙%'"),
        ({'tail': '愁', 'minZe': 50},
         "ze_ratio>=50 AND EXISTS(SELECT 1 FROM lines l WHERE l.pid=p.pid AND l.tail='愁')"),
    ]
    out = []
    for cond, where in cases:
        sql = ('SELECT COUNT(1) FROM poems p WHERE p.dynasty=? AND %s' % where)
        n = con.execute(sql, ('清',)).fetchone()[0]
        out.append({'cond': cond, 'where': where, 'expect': n})
    return out


def main():
    ap = argparse.ArgumentParser(description='生成离线自包含四视图 + 前端校验数据')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'data'))
    ap.add_argument('--limit-metrics', type=int, default=3000)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    con = sqlite3.connect(args.db)

    # ---------- 1) 字→调映射 ----------
    chars, tones = build_tonemap()
    print('字→调映射：%d 个汉字' % len(chars))
    w = lambda name, obj: io.open(os.path.join(args.out, name), 'w', encoding='utf-8',
                                  newline='\n').write(
        jdump(obj, ensure_ascii=False, separators=(',', ':')))

    # ---------- 2) 清词全库（前端自算数字用）----------
    rows = con.execute(
        'SELECT pid,dynasty,author,cipai,title,raw FROM poems WHERE dynasty=? ORDER BY pid',
        ('清',)).fetchall()
    web = [[pid, dyn, au, cp, ti, raw] for pid, dyn, au, cp, ti, raw in rows]
    w('web_poems.json', {'fields': ['pid', 'dyn', 'author', 'cipai', 'title', 'text'],
                         'tonemap': [chars, tones], 'rows': web})

    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    foot = ('<footer class="foot">页面生成时间：%s　·　数据：<code>data/corpus.db</code>'
            '（清词 %d 首，由 <code>web/build_views.py</code> 生成）　·　'
            '若你看到 NaN 或空表格，说明打开的是旧副本：按 Ctrl+F5 强制刷新，'
            '或重新跑 <code>python web/build_views.py</code>。</footer>' % (stamp, len(web)))

    # ---------- 3) Python 侧指标导出（抽样，供 node 对照）----------
    allrows = con.execute(
        'SELECT pid,%s FROM poems WHERE dynasty=? ORDER BY pid'
        % ','.join(METRIC_FIELDS), ('清',)).fetchall()
    step = max(1, len(allrows) // max(1, args.limit_metrics))
    sample = [dict(zip(('pid',) + METRIC_FIELDS, r)) for r in allrows[::step]]
    w('db_metrics.json', sample)

    # ---------- 3b) 检索条件 → 命中篇数（SQL 独立算，供前端门禁对照）----------
    exp = expect_search(con)
    w('expect_search.json', {'note': 'where 里的 SQL 是独立实现；前端 JS 必须给出同样的篇数',
                             'dynasty': '清', 'cases': exp})
    print('检索标尺：%d 条条件（SQL 独立算出）' % len(exp))

    # ---------- 4) 图谱（词人 ↔ 词牌 二部图）----------
    # 布局：**两列**（词人在左、词牌在右）而不是同心圆——同心圆上 45 个标签必然挤成一团
    # （实测：内圈标签间距只有 21px，字又小，根本看不清）。两列布局的间距是**算好**的：
    # 行高 24px、字 15px，标签不会重叠；颜色也分开（词人蓝 / 词牌橙）。
    au = con.execute('SELECT author,COUNT(*) c FROM poems WHERE dynasty=? GROUP BY author '
                     'ORDER BY c DESC LIMIT 45', ('清',)).fetchall()
    cp = con.execute('SELECT cipai,COUNT(*) c FROM poems WHERE dynasty=? GROUP BY cipai '
                     'ORDER BY c DESC LIMIT 45', ('清',)).fetchall()
    au_set = {a for a, _ in au}
    cp_set = {c for c, _ in cp}
    edges = con.execute('SELECT author,cipai,COUNT(*) c FROM poems WHERE dynasty=? '
                        'GROUP BY author,cipai ORDER BY c DESC', ('清',)).fetchall()
    edges = [(a, c, n) for a, c, n in edges if a in au_set and c in cp_set]
    graph = {'dynasty': '清', 'authors': au, 'cipai': cp, 'edges': edges}
    w('graph.json', graph)

    # ---------- 5) 校订队列（用 csv 模块解析，不用 split(',')）----------
    csv_path = os.path.join(ROOT, 'data', 'review_diff.csv')
    review_rows, review_head, summary = [], [], []
    if os.path.exists(csv_path):
        rdr = list(_csv.DictReader(io.open(csv_path, encoding='utf-8-sig', newline='')))
        review_head = list(rdr[0].keys()) if rdr else []
        review_rows = [{k: (r.get(k) or '') for k in review_head} for r in rdr]
        cnt = {}
        for r in review_rows:
            cnt[r['字']] = cnt.get(r['字'], 0) + 1
        top = sorted(cnt.items(), key=lambda kv: -kv[1])[:20]
        summary = [('工单总数', len(review_rows)), ('涉及字数', len(cnt)),
                   ('TOP1', '%s（%d 条）' % (top[0][0], top[0][1]) if top else '—')]

    # ---------- 6) 共享前端文件拷进 data/ ----------
    for name in SHARED_JS + ('metrics.js',):
        src = os.path.join(HERE, name)
        io.open(os.path.join(args.out, name), 'w', encoding='utf-8',
                newline='\n').write(io.open(src, encoding='utf-8').read())

    # ---------- 7) 总览页 ----------
    body = """
<div class="card">
  <h1>词律探微 · 清代词律声情研究助手</h1>
  <p>本页是<b>离线自包含</b>演示：不引用任何 CDN、不需要服务器，双击即可打开。
     页面上的每一个数字都由页面内 JavaScript 用同一套口径<b>自己重算</b>一遍，
     可与 Python 引擎逐字段对照（<code>node web/verify_views.js</code>）。</p>
  <p class="dim">一句话分工：<b>数字归引擎、文料归检索、说法归大模型、出处归引用</b>。</p>
</div>
<div class="grid">
  <div class="card"><h3>视图一 · 逐字解析与检索</h3>
    <p class="dim">26,742 首清词，逐字平仄 + 句脚字 + 声律模式；支持多条件相与、分页、导出。</p>
    <p><a class="btn" href="parse.html">进入</a></p></div>
  <div class="card"><h3>在线检索（需本地服务）</h3>
    <p class="dim">同一套条件改由本地 SQLite 引擎执行（含句级条件与分面统计），还可让大模型把一句话听成条件。</p>
    <p><a class="btn" href="http://127.0.0.1:8000/browse.html">打开 browse.html</a></p>
    <p class="dim">启动：<code>python web/serve.py</code></p></div>
  <div class="card"><h3>视图二 · 知识图谱</h3>
    <p class="dim">词人 ↔ 词牌二部图（取作数前 45），可筛选、悬停高亮、可截图进 PPT。</p>
    <p><a class="btn" href="graph.html">进入</a></p></div>
  <div class="card"><h3>视图三 · 校订队列</h3>
    <p class="dim">把语料自带拼音标注当独立第三方，与引擎逐字比对，分歧进工单等词学裁定。</p>
    <p><a class="btn" href="review.html">进入</a></p></div>
  <div class="card"><h3>在线问答（需本地服务）</h3>
    <p class="dim">问一句、答一句、每处数字带出处；大模型只负责「说法」，数字仍由引擎给。</p>
    <p><a class="btn" href="http://127.0.0.1:8000/">打开 http://127.0.0.1:8000/</a></p>
    <p class="dim">启动：<code>python web/serve.py</code></p></div>
</div>
<div class="card"><h3>复现命令</h3>
<pre>python build_corpus.py --corpus &lt;语料根&gt; --db data/corpus.db
python web/build_views.py            # 生成本目录四个离线视图
python web/serve.py                  # 启动在线问答（默认 127.0.0.1:8000）
python reproduce.py                  # 一键复现全部门禁（含前端渲染门禁）</pre></div>
"""
    io.open(os.path.join(args.out, 'index.html'), 'w', encoding='utf-8', newline='\n').write(
        page('词律探微 · 离线视图', 'index.html', body, foot))

    # ---------- 8) 视图一：逐字解析与检索 ----------
    pack = {'tonemap': [chars, tones], 'rows': web}
    parse_body = """
<div class="card">
  <div class="row">
    <label class="f">朝代
      <select id="dynasty"><option>清</option><option>宋</option><option>元</option></select></label>
    <label class="f">关键词（题名／原文）
      <input id="q" type="text" size="14" placeholder="如：江南"></label>
    <label class="f">词人
      <input id="author" type="text" size="10" placeholder="如：纳兰性德"></label>
    <label class="f">词牌
      <input id="cipai" type="text" size="9" placeholder="如：临江仙"></label>
    <label class="f">句脚字（可多字，取并集）
      <input id="tail" type="text" size="6" placeholder="愁 灯"></label>
    <label class="f">句脚平仄
      <select id="tailPz"><option value="">不限</option><option>平</option><option>仄</option></select></label>
    <label class="f">声律模式（? = 任意）
      <input id="pz" type="text" size="9" placeholder="仄仄平平仄"></label>
    <label class="f">字数 ≥ <input id="minLen" type="number" size="4"></label>
    <label class="f">字数 ≤ <input id="maxLen" type="number" size="4"></label>
    <label class="f">句数 ≥ <input id="minSent" type="number" size="3"></label>
    <label class="f">句数 ≤ <input id="maxSent" type="number" size="3"></label>
    <label class="f">仄比 ≥% <input id="minZe" type="number" size="4"></label>
    <label class="f">仄比 ≤% <input id="maxZe" type="number" size="4"></label>
    <label class="f">最长句 ≥ <input id="minLong" type="number" size="3"></label>
    <label class="f">变化值 ≥ <input id="changeMin" type="number" step="0.1" size="5"></label>
    <label class="f">变化值 ≤ <input id="changeMax" type="number" step="0.1" size="5"></label>
    <label class="f">长句阈值 ≥ <input id="thrMin" type="number" size="3"></label>
    <label class="f">长句阈值 ≤ <input id="thrMax" type="number" size="3"></label>
    <label class="f">声情
      <select id="scene"><option value="">不限</option><option>后段上升</option>
        <option>后段下降</option><option>前后持平</option></select></label>
    <label class="f">排序
      <select id="sort"><option value="pid">篇号</option><option value="ze_desc">仄比 高→低</option>
        <option value="ze_asc">仄比 低→高</option><option value="len_desc">字数 多→少</option>
        <option value="len_asc">字数 少→多</option>
        <option value="sent_desc">句数 多→少</option><option value="sent_asc">句数 少→多</option>
        <option value="long_desc">最长句 长→短</option><option value="long_asc">最长句 短→长</option>
        <option value="change_desc">变化值 大→小</option>
        <option value="change_asc">变化值 小→大</option></select></label>
    <label class="f">每页
      <select id="size"><option>20</option><option selected>50</option><option>100</option>
        <option>200</option></select></label>
    <button id="go">检索</button>
    <button id="reset" class="ghost">清空</button>
    <button id="csv" class="ghost">导出 CSV</button>
  </div>
  <p class="dim">共 <b id="cnt"></b> 首清词（全库）。条件之间是「且」；句脚字与声律模式在
    <b>句</b>一级判定（句脚字＝该句最后一个汉字，句脚平仄＝该句平仄串的末字）。也可用链接参数直达：
    <code>parse.html?tail=愁&amp;minZe=50</code> 或 <code>parse.html?pid=&lt;篇号&gt;</code>。</p>
</div>
<div class="card tight"><div id="meta"></div><div id="facets"></div></div>
<div class="card">
  <div class="scroll"><table>
    <thead><tr><th>#</th><th>词人</th><th>题名</th><th>词牌</th><th>句数</th><th>字数</th>
      <th>仄比</th><th>声情</th><th>操作</th></tr></thead>
    <tbody id="rows"></tbody></table></div>
  <div id="pager"></div>
</div>
<div class="card"><h2>逐字解析</h2>
  <div id="detail"><p class="dim">点上面任意一行的「逐字解析」看逐字平仄表；命中条件的句子会高亮
    （✳ 句脚字命中、〜 声律模式命中）。</p></div>
</div>
<script src="metrics.js"></script><script src="ui.js"></script>
<script>var EMBED_PACK=@@DATA@@;</script>
<script src="app_parse.js"></script>
<script>ParseApp.setData(EMBED_PACK);ParseApp.mount();UI.mountTheme();</script>
"""
    offline = parse_body.replace('@@DATA@@', jdump(
        pack, ensure_ascii=False, separators=(',', ':')))
    io.open(os.path.join(args.out, 'parse.html'), 'w', encoding='utf-8', newline='\n').write(
        page('逐字解析与检索 · 词律探微', 'parse.html', offline, foot))
    # 在线版（同一个表单、同一份前端代码，只是数据改由本地 SQLite 引擎执行）
    live = parse_body.replace('<script>var EMBED_PACK=@@DATA@@;</script>\n', '')
    live = live.replace('ParseApp.setData(EMBED_PACK);', "ParseApp.setLive('');")
    live = live.replace('共 <b id="cnt"></b> 首清词（全库）。',
                        '在线模式：条件由本地 SQLite 引擎执行（句脚字／声脚平仄／声律模式在 lines 表上判定）；'
                        '离线视图只含清词，这里可选朝代（清／宋／元）。')
    live = live.replace('<option>清</option><option>宋</option><option>元</option>',
                        '<option>清</option><option>宋</option><option>元</option>')
    foot_live = foot.replace('<footer class="foot">',
                             '<footer class="foot">在线检索由 web/serve.py 提供；')
    io.open(os.path.join(args.out, 'browse.html'), 'w', encoding='utf-8', newline='\n').write(
        page('在线多条件检索 · 词律探微', 'browse.html', live, foot_live))

    # ---------- 9) 视图二：图谱（Python 定布局 → SVG，可筛选/悬停高亮）----------
    W = 1180
    ROW, TOP = 24.0, 74.0
    n_row = max(len(au), len(cp))
    H = int(TOP + ROW * n_row + 34)
    XA, XC = 250.0, W - 250.0
    mx = max([n for _a, _c, n in edges] or [1])
    r_of = lambda cnt: 4.0 + 22.0 * math.sqrt(cnt / float(max(au[0][1], cp[0][1], 1)))
    pos = {}
    for i, (a, cnt) in enumerate(au):
        pos[('a', a)] = (XA, TOP + ROW * (i + 0.5))
    for i, (c, cnt) in enumerate(cp):
        pos[('c', c)] = (XC, TOP + ROW * (i + 0.5))
    svg = ['<svg id="g" class="chart" xmlns="http://www.w3.org/2000/svg" '
           'viewBox="0 0 %d %d" width="%d" height="%d" '
           'font-family="Microsoft YaHei,serif">' % (W, H, W, H)]
    for a, c, n in edges:
        x1, y1 = pos[('a', a)]
        x2, y2 = pos[('c', c)]
        mx1 = (x1 + x2) / 2
        svg.append('<path class="ed" data-a="%s" data-c="%s" data-n="%d" '
                   'd="M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f" fill="none" '
                   'stroke="#5b86b8" stroke-opacity="0.35" stroke-width="%.2f"/>'
                   % (esc_a(a), esc_a(c), n, x1, y1, mx1, y1, mx1, y2, x2, y2,
                      0.5 + 3.2 * n / mx))
    for a, cnt in au:
        x, y = pos[('a', a)]
        svg.append('<g class="nd" data-k="%s" data-kind="词人" data-n="%d">'
                   '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#1f6fb2"/>'
                   '<text x="%.1f" y="%.1f" text-anchor="end" fill="#1b4f80">%s '
                   '<tspan fill="#7a8b9a">%d</tspan></text></g>'
                   % (esc_a(a), cnt, x, y, r_of(cnt), x - 10, y + 5, esc(a), cnt))
    for c, cnt in cp:
        x, y = pos[('c', c)]
        svg.append('<g class="nd" data-k="%s" data-kind="词牌" data-n="%d">'
                   '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#c2691a"/>'
                   '<text x="%.1f" y="%.1f" text-anchor="start" fill="#8a4a10">%s '
                   '<tspan fill="#7a8b9a">%d</tspan></text></g>'
                   % (esc_a(c), cnt, x, y, r_of(cnt), x + 10, y + 5, esc(c), cnt))
    svg.append('<text x="%.1f" y="30" text-anchor="middle" font-size="16">'
               '词律探微 · 清代词人 ↔ 词牌 二部图（作数前 %d）</text>' % (XA, len(au)))
    svg.append('<text x="%.1f" y="52" text-anchor="middle" font-size="13" fill="#6b7a88">'
               '左：词人　右：词牌　线：二者共有的篇数（越粗越多）</text>' % (XA,))
    svg.append('</svg>')
    graph_body = ('<div class="card"><h1>视图二 · 知识图谱</h1>'
                  '<p class="dim">节点 %d（词人）＋ %d（词牌），边 %d。布局在 Python 侧算好'
                  '（无随机数），两列排版：字号 15px、行距 24px，不会重叠；可筛选、悬停高亮；'
                  '也可截图进 PPT。</p>'
                  '<div class="legend"><span><i style="background:#1f6fb2"></i>词人</span>'
                  '<span><i style="background:#c2691a"></i>词牌</span>'
                  '<span><u></u>线宽＝共有篇数</span><span>圆大小＝篇数多少（右侧数字）</span></div>'
                  '<div class="row"><label class="f">只看包含'
                  '<input id="gq" type="text" placeholder="如：纳兰 / 浣溪沙"></label>'
                  '<button id="gclr" class="ghost">清空</button>'
                  '<span class="dim" id="gmeta">悬停节点可高亮其连线、看篇数</span></div></div>'
                  '<div class="card">%s</div>' % (len(au), len(cp), len(edges), ''.join(svg)))
    graph_js = """
<script src="ui.js"></script><script>
UI.inject();UI.mountTheme();
var g=document.getElementById('g'),nodes=[].slice.call(g.querySelectorAll('.nd')),
    edges=[].slice.call(g.querySelectorAll('.ed'));
var tip=document.createElement('div');tip.className='tip';document.body.appendChild(tip);
function paint(kw,hl){
  kw=(kw||'').trim();
  nodes.forEach(function(n){var on=!kw||n.getAttribute('data-k').indexOf(kw)>=0;
    n.style.opacity=on?1:0.10;n.style.fontWeight=(hl&&n.getAttribute('data-k')===hl)?'700':'400';});
  edges.forEach(function(e){var on=true;
    if(kw){var ka=e.getAttribute('data-a').indexOf(kw)>=0,kc=e.getAttribute('data-c').indexOf(kw)>=0;on=ka||kc;}
    if(hl){on=on&&(e.getAttribute('data-a')===hl||e.getAttribute('data-c')===hl);}
    e.style.opacity=on?0.85:0.04;});
}
function showTip(n,e){var k=n.getAttribute('data-k'),kind=n.getAttribute('data-kind'),c=n.getAttribute('data-n');
  tip.textContent=kind+' '+k+'：共 '+c+' 篇';tip.classList.add('on');
  tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-28)+'px';}
nodes.forEach(function(n){n.style.cursor='pointer';
  n.addEventListener('mouseover',function(e){paint(document.getElementById('gq').value,n.getAttribute('data-k'));showTip(n,e);});
  n.addEventListener('mousemove',function(e){tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-28)+'px';});
  n.addEventListener('mouseout',function(){paint(document.getElementById('gq').value,null);tip.classList.remove('on');});});
document.getElementById('gq').addEventListener('input',function(){paint(this.value,null);});
document.getElementById('gclr').onclick=function(){document.getElementById('gq').value='';paint('',null);};
</script>"""
    io.open(os.path.join(args.out, 'graph.html'), 'w', encoding='utf-8', newline='\n').write(
        page('知识图谱 · 词律探微', 'graph.html', graph_body + graph_js, foot))

    # ---------- 10) 视图三：校订队列 ----------
    if review_rows:
        rev_body = ('<div class="card"><h1>视图三 · 校订队列（标注闭环）</h1>'
                    '<p class="dim">把语料自带拼音标注当作<b>独立第三方</b>，与引擎逐字比对，'
                    '分歧进工单等词学裁定。汇总：%s</p>'
                    '<div class="row"><label class="f">筛选（任意字段）'
                    '<input id="kw" type="text" placeholder="如：长 / 绝 / ci.清.0000"></label>'
                    '<button id="go">筛选</button><button id="csv" class="ghost">导出当前结果 CSV</button>'
                    '</div><p id="chips"></p></div>'
                    '<div class="card tight"><div id="meta"></div></div>'
                    '<div class="card"><div class="scroll"><table><thead><tr>%s</tr></thead>'
                    '<tbody id="rows"></tbody></table></div><div id="pager"></div></div>'
                    % ('；'.join('%s = %s' % (k, v) for k, v in summary),
                       ''.join('<th data-key="%s">%s</th>' % (esc_a(h), esc(h)) for h in review_head)))
        rev_body += ('<script src="ui.js"></script><script>var REV=@@ROWS@@;</script>'
                     '<script src="app_review.js"></script>'
                     '<script>ReviewApp.mount(REV);UI.mountTheme();</script>')
        rev_body = rev_body.replace('@@ROWS@@', jdump(review_rows, ensure_ascii=False,
                                                          separators=(',', ':')))
    else:
        rev_body = '<div class="card"><h1>视图三 · 校订队列</h1><p>未找到 data/review_diff.csv，' \
                   '请先跑 <code>python tools/review_diff.py</code></p></div>'
    if not review_rows:
        rev_body += '<script src="ui.js"></script>'
    io.open(os.path.join(args.out, 'review.html'), 'w', encoding='utf-8', newline='\n').write(
        page('校订队列 · 词律探微', 'review.html', rev_body, foot))

    print('已生成：index.html / parse.html / browse.html / graph.html / review.html / '
          + ' / '.join(SHARED_JS) + ' / metrics.js / web_poems.json / db_metrics.json / '
          'graph.json / expect_search.json')
    print('对照校验：node web/verify_views.js --n 3000 ；node web/test_render.js ；node web/test_ui.js')
    con.close()


if __name__ == '__main__':
    main()
