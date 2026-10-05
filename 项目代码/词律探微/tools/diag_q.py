# -*- coding: utf-8 -*-
"""diag_q.py —— 单题诊断：把「独立真值口径」与「引擎口径」的 SQL 并列打印，定位口径差。"""
import json, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'solve'))
import gen_q1000 as G
import retrieve as R
import ask as A

DB = os.path.join(ROOT, 'data', 'corpus.db')
QF = os.path.join(ROOT, 'data', 'questions_1000.jsonl')

def main():
    ids = sys.argv[1:]
    rows = {json.loads(l)['id']: json.loads(l) for l in open(QF, encoding='utf-8')}
    conn = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True)
    for qid in ids:
        r = rows[qid]
        sig = tuple(r['sig'].split('｜'))
        p = dict(r['spec']); p.update(r.get('intent') or {})
        print('='*100)
        print(qid, '|', r['sig'], '| task=', r['task'])
        print('Q:', r['q'])
        print('SPEC:', json.dumps(r['spec'], ensure_ascii=False))
        tw, ta = G.scope_where(sig, p)
        print('TRUTH where :', tw)
        print('TRUTH args  :', ta)
        try:
            print('TRUTH count :', G.count_hits(conn, sig, p))
        except Exception as e:
            print('TRUTH err:', e)
        try:
            sp = R.parse_query(conn, r['q'])
            ew, ea = R._sql(sp)
            print('ENGINE where:', ew)
            print('ENGINE args :', ea)
            if ew:
                print('ENGINE count:', conn.execute('SELECT COUNT(*) FROM poems p WHERE '+ew, ea).fetchone()[0])
        except Exception as e:
            import traceback; print('ENGINE err:', traceback.format_exc(limit=4))
        try:
            res = A.answer(conn, r['q'], topk=3)
            print('ENGINE answer head:', (res.get('answer') or '').splitlines()[1:3])
            print('ENGINE agg:', json.dumps(res.get('agg'), ensure_ascii=False)[:400] if res.get('agg') else None)
        except Exception as e:
            print('ENGINE ans err:', e)

main()
