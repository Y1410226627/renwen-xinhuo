# -*- coding: utf-8 -*-
"""vector_index.py —— 真正的向量语义检索（篇级 + 句级）。

由来（2026-10-08，外部架构审查 P0）：项目原「语义检索」实为「LLM 扩词 → FTS/bigram」，
对「**秋景**」「**羁旅愁思**」「**与这首词主题相近**」这类**词面必然不重合**的查询天然无能
（全仓 `embedding/vector/faiss` 零命中）。本模块补上**真正的向量语义检索**。

设计要点（外部审查的红线，逐条落实）：
  1. **SQLite = 真源；向量索引 = 派生索引** —— 索引 `manifest` 绑定 `corpus_sha`（库指纹）
     与 `embed_model`/`index_version`，不匹配即视为不可用（避免「换了语料还用旧向量」）。
  2. **多粒度**：篇级（题名+作者+词牌+前两句，用于「找作品」）与句级（每句，用于「意象定位」）。
  3. **只读不建**：本模块只加载/检索；构建在 `build_vector_index.py`（CLI）。
  4. **失败降级**：网关不可达 / 索引缺失 / 维度不符 → `available()` 返回 False、`search` 返回 []，
     **主链不因它崩**（默认 `LVC_VECTOR` 关闭，双重保险）。
  5. **不是事实检索器**：向量只回答「哪些最像」，**不回答**「全库里满足该语义的有哪些一个不少」
     ——后者仍需 SQL/精确条件（外部审查 §6.5 的红线，写在注释里防止误用）。
"""
import hashlib
import json
import os
import threading
import time

import numpy as np  # noqa: F401  （faiss 依赖）

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VDIR = os.path.join(_ROOT, 'data', 'vector')
_URL_TPL = 'http://10.27.66.12'          # 由 llm_local.json 的 url 推导（host 部分）
_EMB_MODEL = 'qwen3-vl-embedding-8b'
_BATCH = 16
_TIMEOUT = 30

_LOCK = threading.Lock()
_STATE = {'loaded': False, 'ok': False, 'why': '', 'index': None, 'meta': [], 'dim': 0,
          'manifest': None, '_embedder': None}


def _read_llm_cfg():
    try:
        with open(os.path.join(_ROOT, 'solve', 'data', 'llm_local.json'), encoding='utf-8') as f:
            cfg = json.load(f)
        url = cfg.get('url') or ''
        host = url.split('/v1/')[0] if '/v1/' in url else url.rstrip('/')
        return host, cfg.get('key') or ''
    except Exception:
        return '', ''


def _post(url, body, timeout=_TIMEOUT):
    import urllib.request
    _, key = _read_llm_cfg()
    req = urllib.request.Request(
        url, data=json.dumps(body).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def embed(texts):
    """文本列表 → 向量列表（自动分批）。任一批失败 → 返回 None（调用方降级）。"""
    host, _ = _read_llm_cfg()
    out = []
    for i in range(0, len(texts), _BATCH):
        d = _post(host + '/v1-openai/embeddings',
                  {'model': _EMB_MODEL, 'input': texts[i:i + _BATCH]})
        vs = [x.get('embedding') for x in (d.get('data') or [])]
        if not vs or any(v is None for v in vs):
            return None
        out.extend(vs)
    return out


def available(conn=None, force=False):
    """网关探活 + 索引可用性（带缓存；`force=True` 重探）。

    ★ `conn` 参数：与 `retrieve._vector_channel` 的调用签名兼容（它把连接传进来），
      本模块建索引时已直接用过该连接，此处忽略即可。"""
    with _LOCK:
        if not _STATE['loaded'] or force:
            _STATE['loaded'] = True
            _load()
        return _STATE['ok']


def why():
    """不可用原因（供上层如实展示）。"""
    return _STATE.get('why') or ''


def _load():
    try:
        import faiss                                     # noqa: F401
        with open(os.path.join(VDIR, 'manifest.json'), encoding='utf-8') as f:
            mf = json.load(f)
        # 绑定语料指纹：corpus.db 变了 → 旧索引作废（防「换了语料还用旧向量」）
        sha = hashlib.sha256(open(os.path.join(_ROOT, 'data', 'corpus.db'), 'rb').read()
                             ).hexdigest()[:16] if os.path.exists(
            os.path.join(_ROOT, 'data', 'corpus.db')) else ''
        if mf.get('corpus_sha') != sha:
            _STATE['ok'], _STATE['why'] = False, '索引与语料不匹配（需重建）'
            return
        idx = faiss.read_index(os.path.join(VDIR, 'faiss.index'))
        meta = [json.loads(x) for x in open(os.path.join(VDIR, 'meta.jsonl'), encoding='utf-8')]
        _STATE.update(ok=True, why='', index=idx, meta=meta, dim=int(mf.get('dim') or 0),
                      manifest=mf)
    except Exception as e:                                   # noqa: BLE001
        _STATE['ok'], _STATE['why'] = False, '%s: %s' % (type(e).__name__, e)


def search(query, topk=10, conn=None):
    """语义查询 → [(pid, score)]（score 为余弦相似度，降序）。不可用返回 []。

    ★ `conn` 参数：与 `retrieve._vector_channel` 的调用签名兼容（忽略即可，
      本模块的索引 meta 已自带检索所需的元数据）。"""
    if not available():
        return []
    try:
        import faiss
        import numpy as np
        v = embed([query])
        if not v:
            return []
        q = np.array(v[0], dtype='float32').reshape(1, -1)
        faiss.normalize_L2(q)
        k = min(topk * 3, _STATE['index'].ntotal)
        D, I = _STATE['index'].search(q, k)
        out = []
        for sc, i in zip(D[0], I[0]):
            if i < 0 or i >= len(_STATE['meta']):
                continue
            m = _STATE['meta'][i]
            out.append((m['pid'], float(sc)))
            if len(out) >= topk:
                break
        return out
    except Exception as e:                                   # noqa: BLE001
        _STATE['why'] = '%s: %s' % (type(e).__name__, e)
        return []
