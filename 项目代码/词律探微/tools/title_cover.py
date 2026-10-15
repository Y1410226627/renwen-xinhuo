# -*- coding: utf-8 -*-
"""title_cover.py —— 生成「题名旁路覆盖表」（**只读工具**，绝不写 corpus.db）。

为什么要有它
------------
全库 58,852 条题名已由大模型**逐条审核**，产出 `data/title_review.jsonl`：

  · **结构化判定 2,842 条**：含 `cipai / ti / xu / title / aliases / confidence / note`；
  · **压缩格式 56,012 条**：`{"pid": "...", "verified": true}` —— 含义是
    「**已核验、题名无需改动**」（**不是**「词牌为空」）。

审核表 pid 与 `corpus.db` 已实测对齐（见 `DECISIONS.md` D62）。本工具把结构化判定里
**对 `cipai`/`title` 有实质改动**的条目抽出来，写成**旁路覆盖表** `data/title_cover.json`，
供 `solve/retrieve.py` 的 `items_of` 在 `LVC_TITLE_COVER` **开启时**做展示层覆盖
（**默认关闭 → 逐字节如旧**）。这落实 `DECISIONS.md` D63 的前置条件 3。

「实质改动」的口径
------------------
以 `corpus.db` 的 `poems.cipai/title` 为**权威基线**，审核结果的 `cipai`/`title` 与之
**逐字段比较**：任一不等即为「实质改动」（`cipai_only` / `title_only` / `both`）。
审核里明确「保留原名」的条目（与库中一致）**不进**覆盖表。

置信度门槛与隔离
----------------
默认只保留 `confidence >= 0.7` 的改动（`--threshold` 可调）。低于门槛的另存
`data/title_cover_lowconf.json`（**仅供人工复核，不接入**）——审核为**大模型判定**，
未经领域专家抽检，低置信条目宁缺勿滥（见 D63 第 3 条「风险不对称」）。

此外，**与「字数形态」矛盾的判定**另存 `data/title_cover_quarantine.json` 并**不进覆盖表**
（判据见 `_is_suspect`；2026-10-15 由 qa-lead 复核发现，见 `DECISIONS.md` D65）。

红线
----
  · `corpus.db` **只读**（只发 `SELECT`，绝不 `INSERT/UPDATE/DELETE`）；
  · 不改 `solve/data/golden_sha.json`；
  · 不改 `solve/` 下交付链（`corpus.py`/`pronounce.py`/`prosody.py`）；
  · 产出只落 `data/`（旁路表），**绝不写回语料库**。

用法
----
    python tools/title_cover.py                 # 生成 data/title_cover.json + 统计
    python tools/title_cover.py --threshold 0.8 # 提高置信门槛
    python tools/title_cover.py --dry-run       # 只统计、不落盘
    python tools/title_cover.py --verify        # 用 corpus.db 复核已生成覆盖表的每条改动
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'data', 'corpus.db')
REVIEW = os.path.join(ROOT, 'data', 'title_review.jsonl')
COVER = os.path.join(ROOT, 'data', 'title_cover.json')
LOWCONF = os.path.join(ROOT, 'data', 'title_cover_lowconf.json')
QUARANTINE = os.path.join(ROOT, 'data', 'title_cover_quarantine.json')

DEFAULT_THRESHOLD = 0.7


def _is_suspect(db_cipai, cover_cipai):
    """**隔离**与「字数形态」矛盾的 LLM 判定（不进 cover，另存 quarantine 供人工复核）。

    2026-10-15（qa-lead 复核发现）：DB `cipai` 含「宴桃源」的 **21** 条，LLM 一律判为
    「阮郎归」（47 字体）；但其中 **17 条 `han_len=33`（如梦令体）**、仅 4 条为 47 字
    ——「宴桃源／如梦令」本属同一词牌（如梦令别名），归并方向与字数矛盾 → 隔离。
    （对照：DB=浪淘沙 的 5 条，4 条 133 字=浪淘沙慢体、1 条 55 字=令体，与 LLM 判定**一致**，
     故**不**隔离——见 `DECISIONS.md` D65 复核记录。）
    """
    return ('宴桃源' in (db_cipai or '')) and cover_cipai == '阮郎归'


def _open_ro(path):
    """**只读**打开语料库（Windows 盘符路径用 `file:...?mode=ro` URI 连不上，
    故用普通 connect + `PRAGMA query_only` 双保险，且本工具只发 SELECT）。"""
    con = sqlite3.connect(path)
    try:
        con.execute('PRAGMA query_only=1')
    except Exception:                                            # noqa: BLE001
        pass
    return con


def _read_corpus_titles(con):
    """pid → {dynasty, cipai, title}（语料库**权威基线**）。"""
    out = {}
    for pid, dyn, cipai, title in con.execute(
            'SELECT pid, dynasty, cipai, title FROM poems'):
        out[pid] = {'dynasty': dyn or '', 'cipai': cipai or '', 'title': title or ''}
    return out


def load_review(path=REVIEW):
    """读审核表，返回 (structured, compressed_count)。

    `structured` 为**有结构化字段**（含 `cipai`）的条目列表；压缩格式只计数。
    """
    structured, compressed = [], 0
    with open(path, encoding='utf-8') as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except Exception:                                    # noqa: BLE001
                continue
            if 'cipai' in o:
                structured.append(o)
            else:
                compressed += 1
    return structured, compressed


def build(threshold=DEFAULT_THRESHOLD, db=DB, review=REVIEW):
    """构建覆盖表。返回 (cover, lowconf, stats, orphans)。

    cover    : {pid: {cipai, title, ti, xu, aliases, confidence}}（改动且 conf>=门槛）
    lowconf  : 同上结构（改动但 conf<门槛）——仅供人工复核
    quarantine: 同上结构（改动但**与字数形态矛盾**，见 `_is_suspect`）——仅供人工复核
    stats    : 统计字典
    orphans  : 结构化条目里 pid **不在** corpus.db 的清单
    """
    con = _open_ro(db)
    try:
        base = _read_corpus_titles(con)
    finally:
        con.close()

    structured, compressed = load_review(review)
    cover, lowconf, quarantine, orphans = {}, {}, {}, []
    by_dynasty, by_type = {}, {'cipai_only': 0, 'title_only': 0, 'both': 0}
    dup_pids = 0
    seen = set()

    for o in structured:
        pid = o.get('pid')
        if pid in seen:
            dup_pids += 1
        seen.add(pid)
        if pid not in base:
            orphans.append(pid)
            continue
        b = base[pid]
        nc = (o.get('cipai') or '').strip()
        nt = (o.get('title') or '').strip()
        ch = nc != b['cipai'].strip()
        th = nt != b['title'].strip()
        if not (ch or th):
            continue                                    # 「保留原名」→ 无实质改动
        entry = {
            'cipai': o.get('cipai') or '',
            'title': o.get('title') or '',
            'ti': o.get('ti') or '',
            'xu': o.get('xu') or '',
            'aliases': list(o.get('aliases') or []),
            'confidence': o.get('confidence'),
        }
        conf = o.get('confidence')
        if _is_suspect(b['cipai'], nc):
            quarantine[pid] = entry                     # 与字数形态矛盾 → 隔离，不进 cover
        elif conf is not None and conf >= threshold:
            cover[pid] = entry
            d = b['dynasty']
            by_dynasty[d] = by_dynasty.get(d, 0) + 1
            if ch and th:
                by_type['both'] += 1
            elif ch:
                by_type['cipai_only'] += 1
            else:
                by_type['title_only'] += 1
        else:
            lowconf[pid] = entry

    real = len(cover) + len(lowconf) + len(quarantine)
    stats = {
        'structured_total': len(structured),
        'compressed_total': compressed,
        'corpus_total': len(base),
        'orphan_total': len(orphans),
        'duplicate_pid_in_review': dup_pids,
        'real_changes': real,
        'kept': len(cover),
        'dropped_lowconf': len(lowconf),
        'quarantined': len(quarantine),
        'threshold': threshold,
        'by_dynasty': by_dynasty,
        'by_type': by_type,
    }
    return cover, lowconf, quarantine, stats, orphans


def write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write('\n')


def verify(cover_path=COVER, db=DB):
    """用 corpus.db 复核已生成覆盖表：每条改动必须**确实**与库中不同。"""
    with open(cover_path, encoding='utf-8') as f:
        cover = json.load(f)
    con = _open_ro(db)
    try:
        base = _read_corpus_titles(con)
    finally:
        con.close()
    bad = []
    for pid, e in cover.items():
        if pid not in base:
            bad.append((pid, 'pid 不在库中'))
            continue
        b = base[pid]
        if (e.get('cipai') or '').strip() == b['cipai'].strip() and \
           (e.get('title') or '').strip() == b['title'].strip():
            bad.append((pid, '与库中一致（非改动）'))
    return cover, bad


def main():
    ap = argparse.ArgumentParser(description='生成题名旁路覆盖表（只读工具）')
    ap.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD,
                    help='置信度门槛（默认 %.2f）' % DEFAULT_THRESHOLD)
    ap.add_argument('--db', default=DB)
    ap.add_argument('--review', default=REVIEW)
    ap.add_argument('--out', default=COVER)
    ap.add_argument('--lowconf-out', default=LOWCONF)
    ap.add_argument('--quarantine-out', default=QUARANTINE)
    ap.add_argument('--dry-run', action='store_true', help='只统计、不落盘')
    ap.add_argument('--verify', action='store_true', help='复核已生成的覆盖表')
    a = ap.parse_args()

    if a.verify:
        cover, bad = verify(a.out, a.db)
        print('复核覆盖表：%s' % a.out)
        print('  条目 %d，异常 %d' % (len(cover), len(bad)))
        for pid, why in bad[:20]:
            print('   ⚠ %s：%s' % (pid, why))
        return 1 if bad else 0

    cover, lowconf, quarantine, stats, orphans = build(a.threshold, a.db, a.review)
    print('=== 题名覆盖表构建 ===')
    print('语料库篇数            : %d' % stats['corpus_total'])
    print('审核结构化判定        : %d' % stats['structured_total'])
    print('审核压缩（无需改动）  : %d' % stats['compressed_total'])
    print('结构化 pid 不在库中   : %d %s' % (stats['orphan_total'],
                                           ('例：%s' % orphans[:3]) if orphans else ''))
    print('审核表内重复 pid      : %d' % stats['duplicate_pid_in_review'])
    print('实质改动（cipai/title 与库不同）: %d' % stats['real_changes'])
    print('  · 保留（conf>=%.2f） : %d' % (a.threshold, stats['kept']))
    print('  · 剔除（conf<%.2f）  : %d  → %s' % (a.threshold, stats['dropped_lowconf'],
                                               a.lowconf_out))
    print('  · 隔离（与字数形态矛盾）: %d  → %s' % (stats['quarantined'], a.quarantine_out))
    print('保留条目按朝代        : %s' % json.dumps(stats['by_dynasty'], ensure_ascii=False))
    print('保留条目按类型        : %s' % json.dumps(stats['by_type'], ensure_ascii=False))
    if a.dry_run:
        print('（--dry-run：未落盘）')
        return 0
    write_json(a.out, cover)
    write_json(a.lowconf_out, lowconf)
    write_json(a.quarantine_out, quarantine)
    print('已写：%s（%d 条）' % (a.out, len(cover)))
    print('已写：%s（%d 条，仅供人工复核）' % (a.lowconf_out, len(lowconf)))
    print('已写：%s（%d 条，与字数矛盾·仅供人工复核）' % (a.quarantine_out, len(quarantine)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
