# -*- coding: utf-8 -*-
"""verify_tune.py —— 「按词牌检索」的**独立真值 + 验收金标准**（QA 专用）。

为什么必须有它（本项目最大的门禁盲区）
--------------------------------------
1000 题（公开 700 + 保密 300）**全部不按词牌做筛选**——题目以
「甲：清·某某《词牌·题》（词牌"X"，首句"…"）」形式**描述**篇目，靠**首句/作者/题名**
定位。因此一旦改动「词牌匹配语义」（如把别名 `百字令` 归并到正名 `念奴娇`、
把粘连的 `壶中天题公曼仇史…` 切回 `壶中天`），**现有五道门禁一道也测不出好坏**。

本脚本**不经 `retrieve.py`**，直接读 `data/corpus.db`（只读），独立算出
「词牌 = X 的篇数」真值，并给出**逐词牌命中篇数差异表**——这是接入旁路覆盖表
（`data/title_cover.json`，开关 `LVC_TITLE_COVER`）时的**验收依据**。

三态口径（本脚本一次全部输出，便于对照）
----------------------------------------
1. **raw**    ：`SELECT COUNT(*) FROM poems WHERE cipai = ?`（语料原值，**不归并**）。
               —— 对应「覆盖表未启用」时引擎的命中篇数（`retrieve._sql` 的 `p.cipai IN (…)`）。
2. **alias**  ：把内置的**别名→正名**分组（正名 + 别名篇数求和）——纯数据推断的「应然」上界。
3. **cover**  ：读 `data/title_cover.json`（若就绪）**逐篇归一**后的真值。
               —— 对应「覆盖表已启用」时的命中篇数。文件/开关未就绪时**显式标 SKIP**。

设计红线
--------
- `data/corpus.db` **只读**（`mode=ro`，绝不写库）。
- **不 import** `retrieve` / `ask` / `corpus`（否则真值就被引擎口径污染，失去独立性）。
- 只新增本文件，不改 `solve/` 任何代码。

用法
----
    PY="D:/conda_envs/langchain-env/python.exe"
    "$PY" tools/verify_tune.py                 # 三态表（自动探测覆盖表）
    "$PY" tools/verify_tune.py --cover         # 强制启用覆盖表（未就绪则报 SKIP）
    "$PY" tools/verify_tune.py --no-cover      # 强制「未启用」态
    "$PY" tools/verify_tune.py --json out.json # 另存机器可读结果
    "$PY" tools/verify_tune.py --cover-file data/title_cover.json

退出码：0 = 正常产出；1 = 语料库缺失（环境不满足）。本脚本是**度量器**，
不因「差异非零」而判失败（差异正是要观测的对象）。
"""
import argparse
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'data', 'corpus.db')
COVER = os.path.join(ROOT, 'data', 'title_cover.json')

# ------------------------------------------------------------------ 正名 / 别名分组
# 分组来源：任务书给定的「正名 + 应归并别名」清单（验收口径）。
# 说明：`采桑子` 与 `采桑子慢` 是两个**不同**正名；`丑奴儿慢` 归 `采桑子慢`，
#       其余 `丑奴儿/丑奴儿令/罗敷媚` 归 `采桑子`。
CANONICAL = [
    '念奴娇', '贺新郎', '齐天乐', '采桑子', '采桑子慢', '阮郎归', '浣溪沙',
    '浣溪沙慢', '浪淘沙', '鹧鸪天', '望江南', '减字木兰花', '调笑令', '摸鱼儿',
    '菩萨蛮', '玉蝴蝶', '蝴蝶儿', '雨霖铃', '归国谣', '柳梢青', '薄幸',
    '满庭芳', '忆秦娥', '破阵子',
]
ALIASES = {
    '念奴娇':   ['百字令', '大江东去', '酹江月', '湘月', '壶中天'],
    '贺新郎':   ['金缕曲', '贺新凉', '貂裘换酒'],
    '齐天乐':   ['台城路'],
    '采桑子':   ['丑奴儿', '丑奴儿令', '罗敷媚'],
    '采桑子慢': ['丑奴儿慢'],
    '阮郎归':   ['醉桃源', '宴桃源'],
    '浣溪沙':   ['浣溪纱', '浣纱溪'],
    '浣溪沙慢': [],
    '浪淘沙':   ['卖花声'],
    '鹧鸪天':   ['思佳客'],
    '望江南':   ['谢秋娘'],
    '减字木兰花': ['减兰'],
    '调笑令':   ['转应曲'],
    '摸鱼儿':   ['摸鱼子'],
    '菩萨蛮':   ['菩萨鬘'],
    '玉蝴蝶':   ['玉胡蝶'],
    '蝴蝶儿':   ['胡蝶儿'],
    '雨霖铃':   ['雨零铃', '雨淋铃'],
    '归国谣':   ['归国遥'],
    '柳梢青':   ['柳稍青'],
    '薄幸':     ['薄悻'],
    '满庭芳':   ['浦庭芳'],
    '忆秦娥':   ['秦楼月'],
    '破阵子':   ['十拍子'],
}


def _ro_conn(path):
    """只读打开语料库（红线：绝不写库）。"""
    return sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True)


def raw_counts(conn):
    """语料原值：每个 cipai 字符串的精确篇数。"""
    rows = conn.execute(
        "SELECT cipai, COUNT(*) FROM poems WHERE cipai IS NOT NULL AND cipai <> '' "
        "GROUP BY cipai").fetchall()
    return {r[0]: r[1] for r in rows}


def glued_counts(conn, name):
    """诊断用：`cipai` **以 name 开头但不等** 的篇数（粘连/带题名，非真值）。"""
    return conn.execute(
        "SELECT COUNT(*) FROM poems WHERE cipai IS NOT NULL AND cipai LIKE ? "
        "AND cipai <> ?", (name + '%', name)).fetchone()[0]


def load_cover(path):
    """容错加载覆盖表，返回 (kind, payload)。

    kind ∈ {'per_pid', 'alias_map', None}
      · per_pid  : {pid: {'cipai':…, 'title':…, …}}  → 逐篇归一
      · alias_map: {别名: 正名} 或 {'alias2canon': {…}} → 查询期扩展
    兼容常见外壳（如 {'items': [...]} / {'cover': {...}}），只做**只读**解析。
    """
    if not os.path.exists(path):
        return None, None
    try:
        with io.open(path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:                                       # noqa: BLE001
        return 'error', '%s: %s' % (type(e).__name__, e)
    if not isinstance(data, dict):
        return 'error', '顶层不是对象（%s）' % type(data).__name__
    # 外壳：items 列表 / cover 字典
    if isinstance(data.get('items'), list):
        m = {}
        for it in data['items']:
            if isinstance(it, dict) and it.get('pid'):
                m[it['pid']] = it
        return ('per_pid', m) if m else ('error', 'items 里没有 pid')
    if isinstance(data.get('cover'), dict):
        data = data['cover']
    # alias2canon 显式键
    for k in ('alias2canon', 'aliases', 'alias_map'):
        if isinstance(data.get(k), dict):
            return 'alias_map', data[k]
    # 逐篇：值多为 dict 且含 cipai
    vals = [v for v in data.values() if isinstance(v, dict)]
    if vals and any(('cipai' in v or 'title' in v) for v in vals):
        return 'per_pid', {k: v for k, v in data.items() if isinstance(v, dict)}
    # 退化：纯 {别名: 正名} 字符串映射
    if data and all(isinstance(v, str) for v in data.values()):
        return 'alias_map', data
    return 'error', '无法识别覆盖表结构（键示例：%s）' % list(data)[:5]


def cover_counts(conn, kind, payload, raw):
    """按覆盖表归一后的逐词牌真值。

    per_pid：把每篇的 cipai 替换为覆盖表 cipai（缺失则沿用原值），再统计。
    alias_map：查询期扩展——正名 X 的命中 = X + 所有映射到 X 的别名（篇数求和）。
    返回 (counts, detail)。
    """
    if kind == 'per_pid':
        over = payload
        counts = {}
        n_over = 0
        for cipai, pid, in conn.execute(
                "SELECT cipai, pid FROM poems WHERE cipai IS NOT NULL AND cipai <> ''"):
            rec = over.get(pid)
            if rec and rec.get('cipai'):
                cipai = rec['cipai']
                n_over += 1
            counts[cipai] = counts.get(cipai, 0) + 1
        return counts, {'n_overridden': n_over, 'n_cover_pids': len(over)}
    if kind == 'alias_map':
        a2c = {k: v for k, v in payload.items() if isinstance(v, str)}
        counts = {}
        # 先并入原始计数
        for k, v in raw.items():
            counts[a2c.get(k, k)] = counts.get(a2c.get(k, k), 0) + v
        return counts, {'n_alias_rules': len(a2c)}
    return raw, {}


def _fmt_table(rows, header):
    widths = [max(len(str(r[i])) for r in ([header] + rows)) for i in range(len(header))]
    line = '  '.join('%-*s' % (w, h) for w, h in zip(widths, header))
    out = [line, '-' * len(line)]
    for r in rows:
        out.append('  '.join('%-*s' % (w, c) for w, c in zip(widths, r)))
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description='按词牌检索的独立真值 / 验收金标准')
    ap.add_argument('--db', default=DB)
    ap.add_argument('--cover-file', default=COVER)
    ap.add_argument('--cover', action='store_true', help='强制启用覆盖表（未就绪则报 SKIP）')
    ap.add_argument('--no-cover', action='store_true', help='强制「未启用」态')
    ap.add_argument('--json', default=None, help='另存机器可读结果到该路径')
    a = ap.parse_args()

    if not os.path.exists(a.db):
        print('✗ 缺语料库：%s' % a.db)
        return 1
    conn = _ro_conn(a.db)

    # 开关判定：--no-cover > --cover > env LVC_TITLE_COVER > 文件是否存在
    env = (os.environ.get('LVC_TITLE_COVER') or '').strip().lower()
    env_on = env not in ('', '0', 'false', 'no', 'off')
    if a.no_cover:
        want_cover = False
    elif a.cover:
        want_cover = True
    elif env:
        want_cover = env_on
    else:
        want_cover = os.path.exists(a.cover_file)

    raw = raw_counts(conn)
    kind, payload = load_cover(a.cover_file)

    print('=' * 78)
    print('词律探微 · 「按词牌检索」独立真值 / 验收金标准')
    print('语料库：%s（只读）' % os.path.relpath(a.db, ROOT))
    print('覆盖表：%s' % os.path.relpath(a.cover_file, ROOT))
    print('开关  ：LVC_TITLE_COVER=%s  →  本次口径：%s'
          % (env or '(未设)', '启用覆盖表' if want_cover else '未启用覆盖表'))
    if want_cover:
        if kind in ('per_pid', 'alias_map'):
            print('覆盖表状态：✅ 已就绪（形态=%s，%s）'
                  % (kind, payload if isinstance(payload, str) else
                     ('%d 条' % len(payload))))
        else:
            print('覆盖表状态：· SKIP —— %s' % (payload or '文件不存在'))
    else:
        print('覆盖表状态：· 未启用（按未启用态输出；raw 列即引擎命中口径）')
    print('=' * 78)

    # 覆盖表归一计数（仅当就绪且需要）
    cc, cdetail = {}, {}
    if want_cover and kind in ('per_pid', 'alias_map'):
        cc, cdetail = cover_counts(conn, kind, payload, raw)

    rows, recs = [], []
    tot_raw = tot_alias = tot_cover = 0
    for canon in CANONICAL:
        al = ALIASES.get(canon, [])
        raw_c = raw.get(canon, 0)
        alias_c = raw_c + sum(raw.get(x, 0) for x in al)
        cover_c = cc.get(canon, 0) if cc else None
        glue = glued_counts(conn, canon)
        delta = (alias_c - raw_c)
        rows.append((canon, raw_c, alias_c, ('%+d' % delta) if delta else '0',
                     (cover_c if cover_c is not None else '—'),
                     ('%+d' % (cover_c - raw_c)) if cover_c is not None else '—',
                     glue))
        tot_raw += raw_c
        tot_alias += alias_c
        if cover_c is not None:
            tot_cover += cover_c
        recs.append({'cipai': canon, 'aliases': al, 'raw': raw_c,
                     'alias_merged': alias_c, 'cover': cover_c, 'glued_like': glue})

    print('\n【逐词牌命中篇数差异表】')
    print(_fmt_table(
        [(str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5]), str(r[6]))
         for r in rows],
        ['正名', 'raw(未启用)', 'alias(归并)', 'Δalias', 'cover(启用)', 'Δcover', '粘连类*']))
    print('\n* 粘连类 = `cipai` 以正名开头但不等于正名（带题名/切分未净，诊断用，非真值）')
    print('  合计：raw=%d ｜ alias归并=%d ｜ cover=%s'
          % (tot_raw, tot_alias, (tot_cover if cc else '—')))

    # 别名明细
    print('\n【别名明细（raw 篇数；0 = 语料中无此串）】')
    for canon in CANONICAL:
        al = ALIASES.get(canon, [])
        if not al:
            continue
        parts = ['%s=%d' % (x, raw.get(x, 0)) for x in al]
        print('  %-8s ← %s' % (canon, '  '.join(parts)))

    # 结论提示
    print('\n【读法】')
    print('  · 未启用态：查询「词牌=X」的命中篇数 = raw 列（引擎现口径 p.cipai IN (X)）。')
    print('  · 启用态  ：命中 = cover 列（逐篇归一）或 alias 列（查询期扩展）。')
    print('  · Δ>0 且来自别名 → **修正**（别名归并）；来自粘连 → **修正**（粘连切分）。')
    print('  · 若某正名 Δ 与别名表对不上（如把 A 误并进 B）→ **风险**，需人工复核。')

    if a.json:
        with io.open(a.json, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'db': os.path.relpath(a.db, ROOT),
                       'cover_file': os.path.relpath(a.cover_file, ROOT),
                       'cover_state': ('on' if want_cover else 'off'),
                       'cover_kind': kind, 'cover_detail': cdetail,
                       'totals': {'raw': tot_raw, 'alias_merged': tot_alias,
                                  'cover': (tot_cover if cc else None)},
                       'rows': recs}, f, ensure_ascii=False, indent=1)
        print('\n✅ 已写机器可读结果：%s' % os.path.relpath(a.json, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
