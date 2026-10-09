# -*- coding: utf-8 -*-
"""cipai_clean.py —— 词牌**白名单**派生数据（外部审查 deepseek §0.3 的替代方案）。

背景：库内 `cipai` 去重后有 14,143 项，其中约八成疑为「题名/整句被误当词牌」的脏数据。
全量人工清洗需对照《钦定词谱》，赛期不现实；这里按**频次门槛**导出一份**只读白名单**，
供解析侧（`entity_resolve.CIPAI_MIN_N`）与前端筛选共用 —— **不改动 corpus.db 一个字节**。

产物：data/cipai_clean.json  {"min_n":N,"n_total":..,"n_kept":..,"cipai":[{name,n},...]}

用法：python tools/cipai_clean.py [--min-n 10]
"""
import argparse
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))
DB = os.path.join(ROOT, 'data', 'corpus.db')
OUT = os.path.join(ROOT, 'data', 'cipai_clean.json')


def main():
    ap = argparse.ArgumentParser(description='导出词牌频次白名单（只读派生数据）')
    ap.add_argument('--min-n', type=int, default=10)
    ap.add_argument('--db', default=DB)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    if not os.path.exists(a.db):
        print('✗ 缺语料库：%s' % a.db)
        return 1
    conn = sqlite3.connect(a.db)
    rows = conn.execute('SELECT cipai, COUNT(*) n FROM poems WHERE cipai IS NOT NULL '
                        'AND cipai<>"" GROUP BY cipai ORDER BY n DESC, cipai').fetchall()
    conn.close()
    kept = [{'name': r[0], 'n': r[1]} for r in rows if r[1] >= a.min_n]
    try:
        import vector_index as VI
        fp = VI.corpus_fingerprint(a.db)
    except Exception:                                            # noqa: BLE001
        fp = ''
    data = {'min_n': a.min_n, 'corpus_fingerprint': fp,
            'n_total': len(rows), 'n_kept': len(kept), 'cipai': kept}
    with io.open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print('✅ %s：词牌共 %d，频次≥%d 保留 %d（%.1f%%）'
          % (os.path.relpath(a.out, ROOT), len(rows), a.min_n, len(kept),
             100.0 * len(kept) / max(len(rows), 1)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
