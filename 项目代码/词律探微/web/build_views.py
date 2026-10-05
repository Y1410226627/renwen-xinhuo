# -*- coding: utf-8 -*-
"""build_views.py —— 生成离线视图的**数据文件**（视图本体由前端框架产出）。

架构（2026-10-05 重构 · D15）：
    视图的**外观与交互**已迁到 Vue3 + Vite 组件（`frontend/`），构建产物落在
    `data/vue/`（HTML + assets）。本脚本不再拼 HTML 字符串，只负责**造数据**：

        data/vue/pack.js      逐字解析页的数据包（window.__PACK__ = {tonemap, rows}）
        data/vue/graph.json   知识图谱数据（词人／词牌／边）
        data/vue/rev.js       校订队列数据（window.__REV__ = [...]）
        data/web_poems.json   清词全库（前端自算数字用；门禁与工具复用）
        data/db_metrics.json  Python 引擎侧指标抽样（供 node 逐字段对照）
        data/expect_search.json  SQL 独立算出的「条件 → 命中篇数」（前端门禁标尺）

为什么要拆开：① HTML 里内嵌几 MB 的数据，改一个字要重生成整页；
② 页面结构写死在 Python 字符串里，改版式得动 Python（维护成本高，评审也难读）；
③ 拆开后，数据是数据、视图是视图——**同一份数据可被离线页与在线服务共用**。

用法：python web/build_views.py [--db data/corpus.db] [--out data/vue] [--limit-metrics 3000]
"""
import argparse
import csv as _csv
import io
import json
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


def jdump(obj, **kw):
    """内嵌 <script> 用的 JSON 序列化。

    ⚠ 2026-10-04 修（代码审查 P3-8）：`json.dumps` **不转义** `/`，若任一原文含
    `</script>`（或 `<!--`），HTML 解析会在那里提前结束脚本 → 页面崩溃/可注入。
    这里把 `</` 统一转成 `<\/`（JSON 里合法、HTML 里不再构成结束标签）。
    """
    return json.dumps(obj, **kw).replace('</', '<\\/')


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
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', 'vue'))
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

    # ---------- 6) 离线视图数据（视图本体由 Vue 产物提供，这里只造数据）----------
    # pack.js：逐字解析页的数据包。用 `window.__PACK__ = {...}` 的经典脚本，
    # 因为该页要在 **file://** 下双击可开——`fetch` 本地 JSON 会被浏览器同源策略拦掉。
    pack = {'tonemap': [chars, tones], 'rows': web}
    io.open(os.path.join(args.out, 'pack.js'), 'w', encoding='utf-8', newline='\n').write(
        '/* pack.js —— 逐字解析页数据包（由 web/build_views.py 生成，勿手改）。 */\n'
        'window.__PACK__ = %s;\n' % jdump(pack, ensure_ascii=False, separators=(',', ':')))

    # graph.json：图谱数据（两种取法都行：Vue 页 fetch 它，或直接读文件）
    w('graph.json', graph)

    # rev.js：校订队列数据（同样要 file:// 可开，故用经典脚本内嵌）
    io.open(os.path.join(args.out, 'rev.js'), 'w', encoding='utf-8', newline='\n').write(
        '/* rev.js —— 校订队列数据（由 web/build_views.py 生成，勿手改）。 */\n'
        'window.__REV__ = %s;\n' % jdump(review_rows, ensure_ascii=False,
                                          separators=(',', ':')))
    # review_rows.json：也给在线模式一份（fetch 用）
    w('review_rows.json', review_rows)

    # 页面生成时间探针：写 stamp.txt（排查用）与 stamp.js（页面页脚显示）。
    io.open(os.path.join(args.out, 'stamp.txt'), 'w', encoding='utf-8', newline='\n').write(
        stamp + '\n')
    io.open(os.path.join(args.out, 'stamp.js'), 'w', encoding='utf-8', newline='\n').write(
        '/* stamp.js —— 页面生成时间探针（由 web/build_views.py 生成）。 */\n'
        'window.__STAMP__ = %s;\n' % jdump(stamp))

    # 兼容：旧的 web_poems.json / db_metrics.json / expect_search.json 仍在 data/（门禁用）
    # 若 --out 不是 data/，额外把这三份写到 data/，保证门禁路径不变。
    data_dir = os.path.join(ROOT, 'data')
    if os.path.abspath(args.out) != os.path.abspath(data_dir):
        for name in ('web_poems.json', 'db_metrics.json', 'expect_search.json'):
            src = os.path.join(args.out, name)
            if os.path.exists(src):
                io.open(os.path.join(data_dir, name), 'w', encoding='utf-8', newline='\n').write(
                    io.open(src, encoding='utf-8').read())

    print('已生成数据文件（到 %s）：' % os.path.relpath(args.out, ROOT))
    print('  pack.js（%d 篇）/ graph.json（%d 词人 × %d 词牌，%d 边）/ rev.js（%d 工单）'
          % (len(web), len(au), len(cp), len(edges), len(review_rows)))
    print('  review_rows.json / stamp.txt')
    print('  （data/ 下另有 web_poems.json / db_metrics.json / expect_search.json 供门禁）')
    print('视图本体：先 `cd frontend && npm run build:views` 产出 data/vue/ 的 HTML+assets。')
    print('对照校验：node web/verify_views.js --n 3000 ；node web/test_render.js ；node web/test_ui.js')
    con.close()


if __name__ == '__main__':
    main()
