# -*- coding: utf-8 -*-
"""build_vector_index.py —— 为语料构建**向量语义索引**（篇级全篇 + 句级每句）。

用法：
    python build_vector_index.py --limit 2000        # 试跑 2000 篇
    python build_vector_index.py --only poems        # 只建篇级
    python build_vector_index.py --only lines        # 只建句级
    python build_vector_index.py                     # 全量（篇级 + 句级）

产物（data/vector/）：poem_embs.npy / poem.index / poem_meta.jsonl
                    line_embs.npy  / line.index  / line_meta.jsonl
                    manifest.json（绑定 corpus_sha + 模型 + 维度 + 版本）
                    progress.json（断点续跑）

━━ 第二轮审查修的四处 ━━
V2  旧版 `poem_text()` 只取**前两句** → 主题落在后片/结尾的词会被漏掉（审查原话：
    「很多词的真正主题信息可能在后片 / 结尾 / 转折 / 中段」）。本版改为**全篇正文**。
V3  `--only lines` 形同虚设（主循环永远 SELECT pid FROM poems）。本版两个 level 各自
    独立的循环 + 独立的 progress 段。
V4  旧版对每个 poem 先 `embed(texts)` 一次、凑满 batch 后**又** `embed(batch_texts)`
    一次 → **同一批文本被嵌入两遍**（双倍 API 调用 / 双倍时间 / 双倍成本）；
    且定义了 `flush()` 却从未调用。本版**全文 embark_batch 一次**，绝不重复。
V5  manifest 强校验所需的字段（model/dim/index_version/各层条数）由这里写入，
    由 `vector_index._load()` 强校验（换模型而语料不变时旧索引会被判作废）。
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solve'))

import vector_index as VI                      # noqa: E402

_ROOT = os.path.dirname(os.path.abspath(__file__))
VDIR = os.path.join(_ROOT, 'data', 'vector')

# 嵌入模型的输入上限（中文字符）。超过就「按句回填」到上限为止——不硬切前两句、
# 也不 truncation 到半句。超过上限的长调另由**句级索引**兜住，语义不会丢。
MAX_TEXT = 1200
LINE_TEXT_MAX = 200


def corpus_sha16():
    # ★ 用**内容指纹**而非文件 sha256：派生表（题名 FTS / 平仄倒排）是加性的，
    #   不该让向量索引作废（详见 `vector_index.corpus_fingerprint`）。
    return VI.corpus_fingerprint(os.path.join(_ROOT, 'data', 'corpus.db'))


def _sentences(raw):
    """正文 → 句子列表（与语料切句口径一致：`。？！`）"""
    import re
    return [s for s in re.split(r'[。？！]', (raw or '').replace('\n', '。')) if s.strip()]


def poem_text(row):
    """篇级嵌入文本：**头信息 + 全篇正文**（V2 修正版）。

    头信息（朝代·作者《词牌·题名》）让元数据也可被语义匹配；正文取**全部**句子，
    到 MAX_TEXT 为止。旧版 `[:2]` 只看前两句。
    """
    head = '%s·%s《%s》' % (row['dynasty'], row['author'], row['title'] or row['cipai'])
    body, n = '', 0
    for s in _sentences(row['raw']):
        if n + len(s) > MAX_TEXT:
            break
        body += s + '。'
        n += len(s) + 1
    return ('%s %s' % (head, body)).strip()


# ------------------------------------------------------------------ 通用：分批嵌入 + 写盘
class _Writer:
    """增量写 <level>_embs.npy（V4 修正：**每批文本只 embed 一次**）。"""

    def __init__(self, level):
        self.level = level
        self.path = os.path.join(VDIR, '%s_embs.npy' % level)
        self._buf, self._meta, self.n = [], [], 0

    def add(self, text, meta):
        self._buf.append(text)
        self._meta.append(meta)

    def need_flush(self, batch):
        return len(self._buf) >= batch

    def flush(self):
        """嵌入当前批次并落盘。**对本批文本只调用 `embed` 一次**（旧版会调两次）。"""
        if not self._buf:
            return 0
        import numpy as np
        vecs = VI.embed(self._buf)
        if vecs is None:
            raise RuntimeError('嵌入请求失败（网关不可达或超时）')
        arr = np.array(vecs, dtype='float32')
        arr = np.ascontiguousarray(arr)
        old = np.load(self.path) if os.path.exists(self.path) else np.zeros(
            (0, arr.shape[1]), 'float32')
        np.save(self.path, np.vstack([old, arr]))
        mf = open(meta_path(self.level), 'a', encoding='utf-8')
        try:
            for m in self._meta:
                mf.write(json.dumps(dict(m, dim=int(arr.shape[1])), ensure_ascii=False) + '\n')
        finally:
            mf.close()
        got = len(self._buf)
        self.n += got
        self._buf, self._meta = [], []
        return got


def meta_path(level):
    return os.path.join(VDIR, '%s_meta.jsonl' % level)


def load_progress(sha):
    p = os.path.join(VDIR, 'progress.json')
    if not os.path.exists(p):
        return {}
    try:
        d = json.load(open(p, encoding='utf-8'))
        return d if d.get('corpus_sha') == sha else {}
    except Exception:                                            # noqa: BLE001
        return {}


def save_progress(d):
    json.dump(d, open(os.path.join(VDIR, 'progress.json'), 'w'), ensure_ascii=False)


def build_level(conn, level, pids, sha, batch, only=None):
    """建某一层的索引。返回 (处理条数, 秒数)。"""
    if only and only != level:
        return 0, 0.0
    prog = load_progress(sha)
    done = set(prog.get('%s_done' % level) or [])
    mp = meta_path(level)
    # 进度与产物不一致时（例如上次中断在 embed 之后、progress 之前），以产物为准重建已完成集合
    if os.path.exists(mp):
        for line in open(mp, encoding='utf-8'):
            try:
                done.add(json.loads(line).get('key'))
            except Exception:                                    # noqa: BLE001
                pass
    t0 = time.time()
    w = _Writer(level)

    if level == 'poem':
        rows = conn.execute(
            'SELECT pid,dynasty,author,cipai,title,raw,han_len,sent_n FROM poems ORDER BY pid')
        for r in rows:
            if r['pid'] not in pids:
                continue
            if r['pid'] in done:
                continue
            txt = poem_text(r)
            if not txt.strip():
                continue
            w.add(txt, {'key': r['pid'], 'pid': r['pid'], 'level': 'poem',
                        'dynasty': r['dynasty'], 'author': r['author'], 'cipai': r['cipai'],
                        'title': r['title'], 'han_len': r['han_len'], 'sent_n': r['sent_n'],
                        'text': txt})
            if w.need_flush(batch):
                w.flush()
                prog['%s_done' % level] = sorted(set(prog.get('%s_done' % level) or []) | done)
                prog['corpus_sha'] = sha
                save_progress(prog)
    else:  # level == 'line'
        q = conn.execute('SELECT l.pid,l.idx,l.text,l.tail,l.pz,l.han_len FROM lines l '
                         'ORDER BY l.pid,l.idx')
        for r in q:
            key = '%s#%d' % (r['pid'], r['idx'])    # pid 是字符串（如 ci.清.0001…#723）
            if r['pid'] not in pids or key in done:
                continue
            txt = (r['text'] or '').strip()
            if len(txt) < 2:                 # 太短的句没有语义信息，且会污染召回
                continue
            w.add(txt[:LINE_TEXT_MAX], {'key': key, 'pid': r['pid'], 'idx': r['idx'],
                                        'level': 'line', 'text': txt, 'tail': r['tail'],
                                        'pz': r['pz'], 'han_len': r['han_len']})
            if w.need_flush(batch):
                w.flush()
                prog['%s_done' % level] = sorted(set(prog.get('%s_done' % level) or []) | done)
                prog['corpus_sha'] = sha
                save_progress(prog)
    try:
        w.flush()
    except RuntimeError as e:
        print('  ✗ %s：%s（已建 %d 条，可重跑续建）' % (e, level, w.n))
        return w.n, time.time() - t0
    prog['%s_done' % level] = sorted(set(prog.get('%s_done' % level) or []) | done)
    prog['corpus_sha'] = sha
    save_progress(prog)
    return w.n, time.time() - t0


def write_manifest(sha):
    """由 npy + meta 重建 faiss 索引并写 manifest（带全字段 + 强校验所需的计数）。"""
    import numpy as np
    import faiss
    mf = {'corpus_sha': sha, 'model': VI.embed_model(), 'index_version': VI.INDEX_VERSION,
          'built_at': time.strftime('%Y-%m-%d %H:%M:%S'),
          'max_text': MAX_TEXT, 'levels': []}
    dim = None
    for level in ('poem', 'line'):
        np_path = os.path.join(VDIR, '%s_embs.npy' % level)
        mp = meta_path(level)
        if not os.path.exists(np_path) or not os.path.exists(mp):
            continue
        embs = np.load(np_path)
        metas = [json.loads(x) for x in open(mp, encoding='utf-8')]
        if embs.shape[0] != len(metas):
            print('  ✗ %s 层向量数(%d) ≠ 元数据数(%d)，跳过该层'
                  % (level, embs.shape[0], len(metas)))
            continue
        embs = np.ascontiguousarray(embs, dtype='float32')
        faiss.normalize_L2(embs)
        idx = faiss.IndexFlatIP(embs.shape[1])
        idx.add(embs)
        faiss.write_index(idx, os.path.join(VDIR, '%s.index' % level))
        dim = dim or int(embs.shape[1])
        mf['n_%ss' % level] = int(embs.shape[0])
        mf['levels'].append(level)
        print('  %s 层：%d 条，维度 %d' % (level, embs.shape[0], embs.shape[1]))
    mf['dim'] = dim or 0
    if not mf['levels']:
        print('  ✗ 没有可用的索引层，manifest 未写入')
        return False
    json.dump(mf, open(os.path.join(VDIR, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
    print('  manifest 已写入：model=%s dim=%s version=%s levels=%s'
          % (mf['model'], mf['dim'], mf['index_version'], mf['levels']))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(_ROOT, 'data', 'corpus.db'))
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 篇（0=全量）')
    ap.add_argument('--only', choices=['poems', 'lines'], default=None)
    ap.add_argument('--dynasty', default=None,
                    help='只建该朝代（如「清」）——目标域优先，避免试跑落在别的朝代')
    ap.add_argument('--batch', type=int, default=16)
    ap.add_argument('--rebuild-index', action='store_true',
                    help='已有 npy/meta 时重建 faiss 与 manifest（不重新嵌入）')
    args = ap.parse_args()

    os.makedirs(VDIR, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    # ⚠ `--dynasty`：本项目的**目标域是清词**，而「按 pid 取前 N 篇」会先落到宋词
    #   （pid 升序时 ci.宋… < ci.清…），实测 3000 篇试跑索引里**一首清词都没有**
    #   → 受限检索（allow=清词）恒为空。加此开关即可只建目标域。
    if args.dynasty:
        pids = [r[0] for r in conn.execute(
            'SELECT pid FROM poems WHERE dynasty=? ORDER BY pid', (args.dynasty,))]
    else:
        pids = [r[0] for r in conn.execute('SELECT pid FROM poems ORDER BY pid')]
    if args.limit:
        pids = pids[:args.limit]
    pids = set(pids)
    sha = corpus_sha16()

    if args.rebuild_index:
        write_manifest(sha)
        return

    only_map = {'poems': 'poem', 'lines': 'line'}
    only_level = only_map.get(args.only)
    print('语料指纹 %s ｜ 目标 %d 篇 ｜ 层：%s' % (sha, len(pids), only_level or 'poem+line'))
    t0 = time.time()
    n_p = t_p = n_l = t_l = 0
    if only_level in (None, 'poem'):
        n_p, t_p = build_level(conn, 'poem', pids, sha, args.batch, only_level)
        print('  篇级：%d 条 / %.0f 秒' % (n_p, t_p))
    if only_level in (None, 'line'):
        n_l, t_l = build_level(conn, 'line', pids, sha, args.batch, only_level)
        print('  句级：%d 条 / %.0f 秒' % (n_l, t_l))
    if write_manifest(sha):
        print('✅ 索引完成（总耗时 %.0f 秒）' % (time.time() - t0))
    if args.limit:
        per = (time.time() - t0) / max(len(pids), 1)
        total = len([r[0] for r in conn.execute('SELECT pid FROM poems')])
        print('   试跑外推：全量 %d 篇约 %.0f 分钟' % (total, per * total / 60))


if __name__ == '__main__':
    main()
