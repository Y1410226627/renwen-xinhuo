# -*- coding: utf-8 -*-
"""cmp_truth.py —— 打印若干题的「真值 vs 引擎」关键量（快速回归用）。"""
import json, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'solve'))
import gen_q1000 as G, retrieve as R, ask as A
import audit_questions as Q

DB = os.path.join(ROOT, 'data', 'corpus.db')
QF = os.path.join(ROOT, 'data', 'questions_1000.jsonl')
rows = {json.loads(l)['id']: json.loads(l) for l in open(QF, encoding='utf-8')}
conn = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True)
ids = sys.argv[1:] or list(rows)[:0]
nok = 0
for qid in ids:
    r = rows[qid]; sig = tuple(r['sig'].split('｜')); p = dict(r['spec']); p.update(r.get('intent') or {})
    it = Q.one(conn, r)
    ok = it.get('ok')
    nok += 1 if ok else 0
    print('%s %s %-4s %s' % ('✔' if ok else '✘', qid, r['task'], r['sig']))
    print('   T:', json.dumps(it.get('truth'), ensure_ascii=False)[:150])
    if not ok:
        print('   BAD:', '; '.join(it['bad'])[:220])
print('通过 %d / %d' % (nok, len(ids)))
