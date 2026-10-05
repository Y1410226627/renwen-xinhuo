# -*- coding: utf-8 -*-
"""dump_metrics_all.py —— 把 Python 引擎的**全库**篇级字段导到 data/_db_metrics_all.json，
供 `node web/verify_views.js --all` 逐篇对照。

为什么要有它：原先把对照样本限在 3000 篇（抽样间隔 8），**抽样会漏掉个别口径不一致**。
实测教训（2026-09-30）：页面 JS 的切句少了「丢掉无汉字碎片」这一步，
全库有若干部篇目的句数比引擎多 1（前后段比例跟着全错），而抽样门禁一条都没报。

用法：python tools/dump_metrics_all.py [--db data/corpus.db] [--dynasty 清]
产物：data/_db_metrics_all.json（QA 临时产物，可删除；删了则 --all 会提示先重建）
"""
import argparse
import io
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ['pid', 'han_len', 'sent_n', 'ping', 'ze', 'ze_ratio', 'cut', 'f_ratio', 'b_ratio',
          'change', 'abs_change', 'longest_len', 'threshold', 'scene']


def main():
    ap = argparse.ArgumentParser(description='导出全库引擎字段供前端逐篇对照')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'data', '_db_metrics_all.json'))
    ap.add_argument('--dynasty', default='清')
    a = ap.parse_args()
    if not os.path.exists(a.db):
        print('找不到语料库 %s' % a.db)
        return 2
    con = sqlite3.connect(a.db)
    rows = con.execute('SELECT %s FROM poems WHERE dynasty=? ORDER BY pid' % ','.join(FIELDS),
                       (a.dynasty,)).fetchall()
    out = [dict(zip(FIELDS, r)) for r in rows]
    io.open(a.out, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    print('已导出 %s 全库字段：%d 篇 → %s（%.1f MB）'
          % (a.dynasty, len(out), a.out, os.path.getsize(a.out) / 1048576.0))
    print('对照：node web/verify_views.js --all')
    return 0


if __name__ == '__main__':
    sys.exit(main())
