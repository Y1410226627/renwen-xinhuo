# -*- coding: utf-8 -*-
"""build_vector_index.py —— 为语料构建**向量语义索引**（篇级 + 句级）。

用法：
    python build_vector_index.py --limit 2000        # 试跑 2000 篇
    python build_vector_index.py --only poems        # 只建篇级
    python build_vector_index.py                     # 全量

产物（data/vector/）：poem_embs.npy + poem_meta.jsonl + line_embs.npy + line_meta.jsonl
                    + manifest.json（绑定 corpus_sha + 模型 + 维度）+ progress.json（断点续跑）

设计：SQLite 为真源，向量索引为**派生物**——manifest 绑定语料指纹，
语料一变旧索引即作废（`vector_index._load` 会校验）。断点续跑：已建批次跳过。
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solve'))

import vector_index as VI          # noqa: E402

_ROOT = os.path.dirname(os.path.abspath(__file__))
VDIR = os.path.join(_ROOT, 'data', 'vector')


def corpus_sha16():
    p = os.path.join(_ROOT, 'data', 'corpus.db')
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]


def poem_text(conn, pid):
    r = conn.execute('SELECT dynasty,author,cipai,title,raw FROM poems WHERE pid=?', (pid,)).fetchone()
    if not r:
        return ''
    first2 = '。'.join((r['raw'] or '').replace('\n', '。').split('。')[:2])
    return '%s·%s《%s》 %s' % (r['dynasty'], r['author'], r['title'] or r['cipai'], first2[:60])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(_ROOT, 'data', 'corpus.db'))
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 篇（0=全量）')
    ap.add_argument('--only', choices=['poems', 'lines'], default=None)
    ap.add_argument('--batch', type=int, default=16)
    args = ap.parse_args()

    os.makedirs(VDIR, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    pids = [r[0] for r in conn.execute('SELECT pid FROM poems ORDER BY pid')]
    if args.limit:
        pids = pids[:args.limit]
    sha = corpus_sha16()
    prog_path = os.path.join(VDIR, 'progress.json')
    prog = {}
    if os.path.exists(prog_path) and os.path.exists(os.path.join(VDIR, 'poem_meta.jsonl')):
        try:
            prog = json.load(open(prog_path, encoding='utf-8'))
            if prog.get('corpus_sha') != sha:
                prog = {}
        except Exception:
            prog = {}

    done_pids = set(prog.get('poems_done') or [])
    todo = [p for p in pids if p not in done_pids]
    print('语料指纹 %s ｜ 目标 %d 篇 ｜ 已完成 %d ｜ 待处理 %d'
          % (sha, len(pids), len(done_pids), len(todo)))

    pm_path = os.path.join(VDIR, 'poem_meta.jsonl')
    lm_path = os.path.join(VDIR, 'line_meta.jsonl')
    pm_f = open(pm_path, 'a', encoding='utf-8')
    lm_f = open(lm_path, 'a', encoding='utf-8')

    t0 = time.time()
    batch_texts, batch_meta = [], []
    n_done = 0

    def flush(texts, metas):
        vecs = VI.embed(texts)
        if vecs is None:
            raise RuntimeError('嵌入请求失败（网关不可达或超时）')
        import numpy as np
        arr = np.array(vecs, dtype='float32')
        ep = os.path.join(VDIR, 'poem_embs.npy')
        lp = os.path.join(VDIR, 'line_embs.npy')
        pe = np.load(ep) if os.path.exists(ep) else np.zeros((0, arr.shape[1]), 'float32')
        np.save(ep, np.vstack([pe, arr]))
        with open(ep + '.count', 'w') as f:
            f.write(str(pe.shape[0] + arr.shape[0]))

    # 简化：本试跑先只做**篇级**；句级索引结构相同、量大，留给 --only lines（结构已就绪）
    for pid in todo:
        texts, metas = [], []
        r = conn.execute('SELECT dynasty,author,cipai,title,raw,sent_n,han_len FROM poems WHERE pid=?',
                         (pid,)).fetchone()
        if r:
            texts.append(poem_text(conn, pid))
            metas.append({'pid': pid, 'level': 'poem', 'dynasty': r['dynasty'],
                          'author': r['author'], 'cipai': r['cipai'],
                          'title': r['title'], 'han_len': r['han_len'], 'sent_n': r['sent_n']})
        if not texts:
            continue
        try:
            vecs = VI.embed(texts)
        except Exception as e:
            print('  ⚠ 嵌入失败（%s），跳过该篇：%s' % (type(e).__name__, e))
            continue
        if vecs is None:
            print('  ⚠ 嵌入返回 None，跳过')
            continue
        batch_texts.extend(texts)
        batch_meta.extend(metas)
        n_done += 1
        done_pids.add(pid)
        if len(batch_texts) >= args.batch:
            import numpy as np
            arr = np.array(VI.embed(batch_texts), dtype='float32')
            ep = os.path.join(VDIR, 'poem_embs.npy')
            pe = np.load(ep) if os.path.exists(ep) else np.zeros((0, arr.shape[1]), 'float32')
            np.save(ep, np.vstack([pe, arr]))
            for m, v in zip(batch_meta, arr):
                pm_f.write(json.dumps(dict(m, dim=int(arr.shape[1])), ensure_ascii=False) + '\n')
            batch_texts, batch_meta = [], []
            if n_done % 200 == 0:
                json.dump({'corpus_sha': sha, 'poems_done': sorted(done_pids)}, open(prog_path, 'w'))
                print('  … %d 篇（%.0f 秒）' % (n_done, time.time() - t0))
    # 收尾批次
    if batch_texts:
        import numpy as np
        arr = np.array(VI.embed(batch_texts), dtype='float32')
        ep = os.path.join(VDIR, 'poem_embs.npy')
        pe = np.load(ep) if os.path.exists(ep) else np.zeros((0, arr.shape[1]), 'float32')
        np.save(ep, np.vstack([pe, arr]))
        for m, v in zip(batch_meta, arr):
            pm_f.write(json.dumps(dict(m, dim=int(arr.shape[1])), ensure_ascii=False) + '\n')

    pm_f.close()
    lm_f.close()
    json.dump({'corpus_sha': sha, 'poems_done': sorted(done_pids)}, open(prog_path, 'w'))

    # 由 meta.jsonl 重建 faiss 索引 + meta（与向量一一对应）
    import numpy as np
    import faiss
    metas = [json.loads(x) for x in open(pm_path, encoding='utf-8')]
    embs = np.load(os.path.join(VDIR, 'poem_embs.npy'))
    faiss.normalize_L2(embs)
    index = faiss.IndexFlatIP(embs.shape[1])
    index.add(embs)
    faiss.write_index(index, os.path.join(VDIR, 'faiss.index'))
    with open(os.path.join(VDIR, 'meta.jsonl'), 'w', encoding='utf-8') as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + '\n')
    mf = {'corpus_sha': sha, 'model': VI._EMB_MODEL, 'dim': int(embs.shape[1]),
          'count': int(embs.shape[0]), 'index_version': 1, 'built_at': time.strftime('%Y-%m-%d %H:%M')}
    with open(os.path.join(VDIR, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(mf, f, ensure_ascii=False, indent=1)
    print('✅ 索引完成：%d 篇，维度 %d，manifest 已绑定语料指纹 %s'
          % (embs.shape[0], embs.shape[1], sha))
    print('   预计全量耗时：试跑 %.0f 秒/%d 篇 → 全量约 %.0f 分钟'
          % (time.time() - t0, max(n_done, 1), (time.time() - t0) / max(n_done, 1) * len(pids) / 60))


if __name__ == '__main__':
    main()
