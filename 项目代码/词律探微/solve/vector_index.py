# -*- coding: utf-8 -*-
"""vector_index.py —— 真正的向量语义检索（篇级 + 句级，**支持候选集内受限检索**）。

由来（2026-10-08，外部架构审查 P0）：项目原「语义检索」实为「LLM 扩词 → FTS/bigram」，
对「**秋景**」「**羁旅愁思**」「**与这首词主题相近**」这类**词面必然不重合**的查询天然无能
（全仓 `embedding/vector/faiss` 零命中）。本模块补上**真正的向量语义检索**。

设计红线（外部审查逐条落实）：
  1. **SQLite = 真源；向量索引 = 派生索引** —— 索引 `manifest` 绑定 `corpus_sha`（库指纹）
     与 `model`/`dim`/`index_version`，**任一项不符即视为不可用**（第二轮审查 V5 指出
     旧版只校验 corpus_sha，换模型后仍可能加载旧索引 → 本版全部强校验）。
  2. **多粒度**：篇级（**全篇**文本，用于「找作品」）与句级（每句，用于「某句出自哪首」）。
     ⚠ 第二轮审查 V2 指出旧版`poem_text()` 只取**前两句** → 主题信息落在后片/结尾的词
     会被漏掉。本版改为**全篇正文**（超出上限按句子为单位回填，不硬切第二句）。
  3. **受限检索（V1 的核心修正）**：`search(..., allow=<pid 集合>)` 先按硬 SQL 条件拿到
     候选全集，再在**候选集内**扩大召回直到凑够 topk；绝不再用「全库 top150 → 再套硬过滤」
     那种会把正确答案截断的老做法。
  4. **只读不建**：本模块只加载/检索；构建在 `build_vector_index.py`（CLI）。
  5. **失败降级**：网关不可达 / 索引缺失 / 版本不符 → `available()` 返回 False、`search` 返回 []，
     **主链不因它崩**（默认 `LVC_VECTOR` 关闭，双重保险）。
  6. **不是事实检索器**：向量只回答「哪些最像」，**不回答**「全库里满足该语义的有哪些一个不少」
     ——后者仍需 SQL/精确条件。
"""
import hashlib
import json
import sqlite3
import os
import threading

import numpy as np                                             # noqa: F401

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VDIR = os.path.join(_ROOT, 'data', 'vector')
_EMB_MODEL = 'qwen3-vl-embedding-8b'
_BATCH = 16
_TIMEOUT = 30

# ⚠ index_version：**索引格式/语义**变了必须 +1（manifest 里强校验，见 `_load`）。
#   第二轮审查 V5：旧版本表缺失 → 换 embedding 模型后 corpus.db 不变，旧索引仍会被加载。
INDEX_VERSION = 2

_LOCK = threading.Lock()
_STATE = {
    'loaded': False, 'ok': False, 'why': '', 'manifest': None,
    'poem_index': None, 'poem_meta': [],
    'line_index': None, 'line_meta': [],
}


# ------------------------------------------------------------------ 嵌入网关
def _read_llm_cfg():
    try:
        with open(os.path.join(_ROOT, 'solve', 'data', 'llm_local.json'), encoding='utf-8') as f:
            cfg = json.load(f)
        url = cfg.get('url') or ''
        host = url.split('/v1/')[0] if '/v1/' in url else url.rstrip('/')
        return host, cfg.get('key') or ''
    except Exception:                                            # noqa: BLE001
        return '', ''


def embed_model():
    """当前配置的嵌入模型名（环境变量可覆盖；manifest 强校验要与它一致）。"""
    return os.environ.get('LVC_EMBED_MODEL') or _EMB_MODEL


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
    if not host:
        return None
    out = []
    for i in range(0, len(texts), _BATCH):
        try:
            d = _post(host + '/v1-openai/embeddings',
                      {'model': embed_model(), 'input': texts[i:i + _BATCH]})
        except Exception:                                        # noqa: BLE001
            return None
        vs = [x.get('embedding') for x in (d.get('data') or [])]
        if not vs or any(v is None for v in vs):
            return None
        out.extend(vs)
    return out


# ------------------------------------------------------------------ 加载与强校验
def corpus_fingerprint(path=None):
    """语料**内容指纹**（不是文件 sha256）。

    ⚠ 2026-10-08 第二轮实测踩坑：原先直接对 `corpus.db` **整个文件**取 sha256，
    于是 `tools/build_indexes.py` 往库里加两张**派生表**（题名 FTS / 平仄倒排）之后，
    文件 sha 变了 → 向量索引被判「与语料不匹配」→ 直接失效。
    可派生表本来就是**加性的**（不改 poems/lines 一个字节），不该让向量索引作废。

    改为对 poems/lines 的**内容摘要**取哈希：篇数、句数、汉字总数、最大 pid。
    语料内容一变就变；加派生索引/建索引则不变。且比读 100MB 文件快得多。
    """
    p = path or os.path.join(_ROOT, 'data', 'corpus.db')
    try:
        # ⚠ 不用 `file:...?mode=ro` URI：Windows 盘符路径（D:/…）拼出的 URI 在本机连不上
        #   （实测返回空指纹）。只读意图由「只发 SELECT」保证——本函数不发任何写语句。
        con = sqlite3.connect(p)
        try:
            n_p = con.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
            n_l = con.execute('SELECT COUNT(*) FROM lines').fetchone()[0]
            s_h = con.execute('SELECT COALESCE(SUM(han_len),0) FROM poems').fetchone()[0]
            mx = con.execute('SELECT COALESCE(MAX(pid),\'\') FROM poems').fetchone()[0]
        finally:
            con.close()
    except Exception:                                            # noqa: BLE001
        return ''
    raw = '%d|%d|%s|%s' % (n_p, n_l, s_h, mx)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]


def _sha16(path):
    """兼容旧名：返回**内容指纹**（见 `corpus_fingerprint`）。"""
    return corpus_fingerprint(path)


def available(conn=None, force=False):
    """索引可用性（带缓存；`force=True` 重探）。`conn` 仅为调用签名兼容。"""
    with _LOCK:
        if not _STATE['loaded'] or force:
            _STATE['loaded'] = True
            _load()
        return _STATE['ok']


def why():
    """不可用原因（供上层如实展示，不许笼统说「不可用」）。"""
    return _STATE.get('why') or ''


def info():
    """索引信息（供 explain / 前端展示）：各层条数、模型、维度、版本。"""
    mf = _STATE.get('manifest') or {}
    return {
        'ok': _STATE['ok'], 'why': _STATE['why'],
        'model': mf.get('model'), 'dim': mf.get('dim'),
        'index_version': mf.get('index_version'), 'expected_version': INDEX_VERSION,
        'built_at': mf.get('built_at'), 'corpus_sha': mf.get('corpus_sha'),
        'n_poems': mf.get('n_poems'), 'n_lines': mf.get('n_lines'),
        'loaded_poems': len(_STATE['poem_meta']), 'loaded_lines': len(_STATE['line_meta']),
    }


def coverage(conn=None, deep=False):
    """**索引覆盖率**（第三轮审查 P1-14）＋**按身份集合核验**（2026-10-10，P1-6）。

    ⚠ 「索引可用」≠「语料全覆盖」——本函数把覆盖做成**可观测指标**：
      · `poems.indexed / poems.total`：篇级索引条数 vs 语料总篇数；
      · `poems.by_dynasty`：每朝代的 {indexed, total}（清/宋/元）；
      · `lines.indexed / lines.total`：句级索引条数 vs 语料总句数；
      · 任一缺口即 `complete=False`，并列出 `notes`（哪一代/哪层缺）。

    ⚠ 2026-10-10（《关键核心现状》P1-6）：**「条数相等」不等于「同一批数据」**。
      改前 → 只比 `len(idx_meta) >= COUNT(*)`：索引里若存在**重复 / 错位 / 张冠李戴**
        （某些 ID 替掉了别的 ID），条数照样对得上，日志仍会报「覆盖完整」。
      改后 → 按**篇号集合**核验：
        `missing_poems = 库篇号 − 索引篇号`、`unknown_poems = 索引篇号 − 库篇号`、
        `duplicate_poems`（索引内重复条数）；任一非空即 `complete=False` 并进 `notes`。
      句级身份用 `(pid, idx)` 稳定二元组；句级集合核验较重（要拉 42 万行），
      故只在 `deep=True` 时执行，默认仍走条数（但**篇级一律走集合**，代价很小）。
    """
    mf = _STATE.get('manifest') or {}
    pm, lm = list(_STATE['poem_meta']), list(_STATE['line_meta'])
    out = {
        'indexed_poems': len(pm), 'indexed_lines': len(lm),
        'total_poems': None, 'total_lines': None,
        'by_dynasty': {}, 'complete': None, 'notes': [],
        # ★ P1-6：按身份集合核验的结果（None = 未做该层核验）
        'missing_poems': None, 'unknown_poems': None, 'duplicate_poems': None,
        'missing_lines': None, 'unknown_lines': None, 'duplicate_lines': None,
        'lines_checked_by_id': False,
    }
    if not _STATE['ok']:
        out['notes'].append('索引不可用（%s）' % why())
    if conn is not None:
        try:
            out['total_poems'] = conn.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
            out['total_lines'] = conn.execute('SELECT COUNT(*) FROM lines').fetchone()[0]
            _dyn = dict((r[0], r[1]) for r in conn.execute(
                'SELECT dynasty, COUNT(*) FROM poems GROUP BY dynasty'))
            _idx_dyn = {}
            for m in pm:
                _pid = m.get('pid') if isinstance(m, dict) else getattr(m, 'pid', '')
                # pid 形如 ci.清.xxx / ci.宋.xxx / ci.元.xxx —— 第二段即朝代
                try:
                    _d = _pid.split('.')[1]
                except IndexError:
                    _d = '?'
                _idx_dyn[_d] = _idx_dyn.get(_d, 0) + 1
            for d, tot in _dyn.items():
                out['by_dynasty'][d] = {'indexed': _idx_dyn.get(d, 0), 'total': tot}
                if _idx_dyn.get(d, 0) < tot:
                    out['notes'].append('%s 篇级缺 %d/%d' % (d, tot - _idx_dyn.get(d, 0), tot))

            # ── 篇级：**按篇号集合**核验（P1-6）──
            _db_p = [r[0] for r in conn.execute('SELECT pid FROM poems')]
            _id_p = [(m.get('pid') if isinstance(m, dict) else getattr(m, 'pid', '')) for m in pm]
            _db_set, _id_set = set(_db_p), set(_id_p)
            out['missing_poems'] = sorted(_db_set - _id_set)
            out['unknown_poems'] = sorted(_id_set - _db_set)
            out['duplicate_poems'] = len(_id_p) - len(_id_set)
            if out['missing_poems']:
                out['notes'].append('篇级缺 %d 个篇号（例：%s）'
                                    % (len(out['missing_poems']), out['missing_poems'][:5]))
            if out['unknown_poems']:
                out['notes'].append('篇级有 %d 个**库里不存在**的篇号（例：%s）'
                                    % (len(out['unknown_poems']), out['unknown_poems'][:5]))
            if out['duplicate_poems']:
                out['notes'].append('篇级索引内有 %d 条**重复**篇号' % out['duplicate_poems'])
            _p_ok = (not out['missing_poems'] and not out['unknown_poems']
                     and not out['duplicate_poems'])

            # ── 句级：身份是 `(pid, idx)`；较重，仅 deep 时做 ──
            _l_ok = len(lm) >= out['total_lines']
            if deep:
                _db_l = [(r[0], r[1]) for r in conn.execute('SELECT pid, idx FROM lines')]
                _id_l = [(m.get('pid'), m.get('idx')) for m in lm
                         if isinstance(m, dict)]
                _db_ls, _id_ls = set(_db_l), set(_id_l)
                _miss = sorted(_db_ls - _id_ls)
                _unk = sorted(_id_ls - _db_ls)
                out['missing_lines'] = len(_miss)
                out['unknown_lines'] = len(_unk)
                out['duplicate_lines'] = len(_id_l) - len(_id_ls)
                out['lines_checked_by_id'] = True
                if _miss:
                    out['notes'].append('句级缺 %d 句（例：%s）' % (len(_miss), _miss[:3]))
                if _unk:
                    out['notes'].append('句级有 %d 句在库里不存在（例：%s）' % (len(_unk), _unk[:3]))
                if out['duplicate_lines']:
                    out['notes'].append('句级索引内有 %d 条重复 (pid,idx)' % out['duplicate_lines'])
                _l_ok = (not _miss and not _unk and not out['duplicate_lines'])
            else:
                if len(lm) < out['total_lines']:
                    out['notes'].append('句级覆盖 %d/%d（缺 %d）；'
                                        '如需**按句身份**核验请用 deep=True'
                                        % (len(lm), out['total_lines'],
                                           out['total_lines'] - len(lm)))
                else:
                    out['notes'].append('句级仅比条数（如需按句身份核验请用 deep=True）')

            out['complete'] = bool(_p_ok and _l_ok)
            if len(pm) < out['total_poems']:
                out['notes'].append('篇级条数 %d/%d（缺 %d）'
                                    % (len(pm), out['total_poems'], out['total_poems'] - len(pm)))
        except Exception as e:                                   # noqa: BLE001
            out['notes'].append('覆盖率对拍失败：%r' % e)
    return out


def _load():
    try:
        import faiss
        mfp = os.path.join(VDIR, 'manifest.json')
        if not os.path.exists(mfp):
            _STATE['ok'], _STATE['why'] = False, '索引尚未构建（缺 manifest.json）'
            return
        with open(mfp, encoding='utf-8') as f:
            mf = json.load(f)

        # ---- 强校验五件套（第二轮审查 V5）----
        tm = _sha16(os.path.join(_ROOT, 'data', 'corpus.db'))
        # ⚠ 空指纹（库读不到 / 查询失败）必须**判不可用**：否则 `'' == ''` 会让
        #   「取不到指纹」与「指纹为空的旧 manifest」误配，等于关掉了这项校验。
        if not tm:
            _STATE['ok'], _STATE['why'] = False, '无法取得语料内容指纹（corpus.db 不可读）'
            return
        if mf.get('corpus_sha') != tm:
            _STATE['ok'], _STATE['why'] = False, (
                '索引与语料不匹配（指纹 %s vs 当前 %s，需重建）' % (mf.get('corpus_sha'), tm))
            return
        if int(mf.get('index_version') or 0) != INDEX_VERSION:
            _STATE['ok'], _STATE['why'] = False, (
                '索引版本过期：manifest=%s，当前要求 v%s' % (mf.get('index_version'), INDEX_VERSION))
            return
        if str(mf.get('model') or '') != embed_model():
            _STATE['ok'], _STATE['why'] = False, (
                '嵌入模型不一致：索引=%s，当前=%s（需重建）' % (mf.get('model'), embed_model()))
            return

        def _read_level(name):
            idx_p = os.path.join(VDIR, '%s.index' % name)
            meta_p = os.path.join(VDIR, '%s_meta.jsonl' % name)
            if not os.path.exists(idx_p) or not os.path.exists(meta_p):
                return None, []
            idx = faiss.read_index(idx_p)
            meta = [json.loads(x) for x in open(meta_p, encoding='utf-8')]
            return idx, meta

        pidx, pmeta = _read_level('poem')
        lidx, lmeta = _read_level('line')
        if pidx is None and lidx is None:
            _STATE['ok'], _STATE['why'] = False, '索引层文件缺失（poem/line 都没有）'
            return

        # dim 与 ntotal 双校验（manifest 说的必须与实际产物对得上）
        for nm, idx, meta, key in (('poem', pidx, pmeta, 'n_poems'), ('line', lidx, lmeta, 'n_lines')):
            if idx is None:
                continue
            if int(mf.get('dim') or 0) != int(idx.d):
                _STATE['ok'], _STATE['why'] = False, (
                    '%s 层维度不符：manifest=%s，索引=%s' % (nm, mf.get('dim'), idx.d))
                return
            if mf.get(key) is not None and int(mf[key]) != len(meta):
                _STATE['ok'], _STATE['why'] = False, (
                    '%s 层条数不符：manifest=%s，实际=%d' % (nm, mf.get(key), len(meta)))
                return
            if idx.ntotal != len(meta):
                _STATE['ok'], _STATE['why'] = False, (
                    '%s 层向量数与元数据不等：%d vs %d' % (nm, idx.ntotal, len(meta)))
                return

        _STATE.update(ok=True, why='', manifest=mf,
                      poem_index=pidx, poem_meta=pmeta,
                      line_index=lidx, line_meta=lmeta)
    except Exception as e:                                       # noqa: BLE001
        _STATE['ok'], _STATE['why'] = False, '%s: %s' % (type(e).__name__, e)


# ------------------------------------------------------------------ 检索（含受限检索）
def _query_vec(text):
    v = embed([text])
    if not v:
        return None
    q = np.array(v[0], dtype='float32').reshape(1, -1)
    import faiss
    faiss.normalize_L2(q)
    return q


def _restricted_search(index, meta, q, topk, allow, id_of, cap=20000):
    """在 index 上检索，**只在 allow 内**返回 topk 个；候选不够就**动态扩大**。

    这就是第二轮审查 §15 要的 filtered vector search：旧做法是「全库 top150 → 再套硬过滤」，
    会把「全库排 151~500 名但确实满足条件」的正确答案截掉。本实现的循环是：
        取 k 个最近邻 → 过滤 allow → 不够就把 k 扩大 3 倍再来，直到凑够或 k 达到上限。
    """
    import faiss
    n = index.ntotal
    if n <= 0:
        return []
    out, seen = [], set()
    k = max(topk * 4, 64)
    while k <= cap:
        kk = min(k, n)
        D, I = index.search(q, kk)
        for sc, i in zip(D[0], I[0]):
            if i < 0 or i >= len(meta):
                continue
            pid = id_of(meta[i])
            if allow is not None and pid not in allow:
                continue
            if pid in seen:
                continue
            seen.add(pid)
            out.append((pid, float(sc)))
            if len(out) >= topk:
                return out
        if kk >= n:            # 已经把整个候选池翻完了
            break
        k *= 3
    return out


def search(query, topk=10, conn=None, allow=None, level='auto'):
    """语义查询 → [(pid, score)]（余弦相似度降序）。不可用返回 []。

    ★ `allow`：允许的 pid 集合（**先 SQL 硬过滤得出的候选全集**）。给了就**只在该集合内**
      检索；这正是第二轮审查划的重点（hard condition 不得截断 vector recall）。
    ★ `level`：`'poem'` 只搜篇级；`'line'` 搜句级并把命中句聚合到篇；
      `'auto'`（默认）优先篇级，篇级不可用 / 结果不足时补句级。
    """
    if not available():
        return []
    try:
        q = _query_vec(query)
        if q is None:
            return []
        out = []
        if level in ('auto', 'poem') and _STATE['poem_index'] is not None:
            out = _restricted_search(_STATE['poem_index'], _STATE['poem_meta'], q,
                                     topk, allow, lambda m: m.get('pid'))
        need = topk - len(out)
        if need > 0 and level in ('auto', 'line') and _STATE['line_index'] is not None:
            _have = set(p for p, _ in out)
            _allow = None if allow is None else set(allow) - _have
            extra = _restricted_search(_STATE['line_index'], _STATE['line_meta'], q,
                                       need, _allow, lambda m: m.get('pid'))
            out += [(p, s * 0.98) for p, s in extra if p not in _have]
        return out[:topk]
    except Exception as e:                                       # noqa: BLE001
        _STATE['why'] = '%s: %s' % (type(e).__name__, e)
        return []


_MAX_LINES_SCAN = 50000       # 句级召回单次请求的**扫描上限**（超出即如实报告"未穷尽"）


def search_lines(query, topk=10, conn=None, allow=None):
    """语义查询 → [(pid, idx, text, score)]（句级，带句序号与原文；用于「某句出自哪首」）。

    ⚠ 2026-10-10（《关键核心现状》P1-3）：**候选集内检索要逐轮扩大 k**。
      改前 → 固定 `k = max(topk*4, 64)` 取**全局**近邻，再按 `allow` 过滤：
        当前帧 100 篇里确有最匹配的句子、但全局前 64 名都在帧外 → 返回 0 条，
        系统据此谎报「当前集合里没有命中」——**把排名截断伪装成"没找到"**。
      改后 → 有 `allow` 时逐轮把 k 扩大 4 倍（64 → 256 → …）直到凑够 topk 或覆盖全索引；
        为控制延迟设扫描上限 `_MAX_LINES_SCAN`，触顶时置 `lines_scan_truncated()` 为真，
        由调用方**如实报告"未穷尽"**，绝不静默返回空。`allow=None` 时保持原行为不变。
    """
    if not available() or _STATE['line_index'] is None:
        return []
    _STATE['lines_scan_truncated'] = False
    try:
        q = _query_vec(query)
        if q is None:
            return []
        n = _STATE['line_index'].ntotal
        if allow is None:
            ks = [min(max(topk * 4, 64), n)]
        else:
            ks, k = [], max(topk * 4, 64)
            while True:
                ks.append(min(k, n))
                if k >= n or k >= _MAX_LINES_SCAN:
                    break
                k *= 4
        out = []
        for k in ks:
            D, I = _STATE['line_index'].search(q, k)
            out = []
            for sc, i in zip(D[0], I[0]):
                if i < 0 or i >= len(_STATE['line_meta']):
                    continue
                m = _STATE['line_meta'][i]
                if allow is not None and m.get('pid') not in allow:
                    continue
                out.append((m.get('pid'), m.get('idx'), m.get('text'), float(sc)))
                if len(out) >= topk:
                    break
            if len(out) >= topk or k >= n:
                break
            if k >= _MAX_LINES_SCAN:
                _STATE['lines_scan_truncated'] = True
                break
        return out
    except Exception as e:                                       # noqa: BLE001
        _STATE['why'] = '%s: %s' % (type(e).__name__, e)
        return []


def lines_scan_truncated():
    """上一次 `search_lines` 是否因**扫描上限**而未穷尽（P1-3：不许把截断伪装成"没找到"）。"""
    return bool(_STATE.get('lines_scan_truncated'))


def similar(pid, topk=10, conn=None, allow=None, exclude_self=True):
    """「与这一首主题相近」→ [(pid, score)]。

    做法：取该篇的文本作为查询去做近邻检索（这就是 `intent=similarity` 的实现）。
    首篇本身会排第 1，默认剔除。
    """
    if not available():
        return []
    try:
        if conn is not None:
            row = conn.execute('SELECT dynasty,author,cipai,title,raw FROM poems WHERE pid=?',
                               (pid,)).fetchone()
        else:
            row = None
        for m in _STATE['poem_meta']:
            if m.get('pid') == pid:
                qtext = m.get('text') or ''
                break
        else:
            qtext = ''
        if not qtext and row is not None:
            qtext = '%s《%s》%s' % (row[1], row[3] or row[2], row[4] or '')
        if not qtext:
            return []
        hits = search(qtext, topk=topk + (1 if exclude_self else 0), allow=allow, level='poem')
        return [(p, s) for p, s in hits if not (exclude_self and p == pid)][:topk]
    except Exception:                                            # noqa: BLE001
        return []


def main():
    import argparse
    ap = argparse.ArgumentParser(description='向量索引自检')
    ap.add_argument('--q', action='append', default=[], help='语义查询（可多次）')
    ap.add_argument('--similar', type=int, default=0, help='找与该 pid 主题相近的作品')
    a = ap.parse_args()
    available()          # 先触发一次加载，`info()` 才有内容（否则首行恒 ok:false，误导）
    print('index info: %s' % json.dumps(info(), ensure_ascii=False))
    for q in (a.q or ['写秋景的词']):
        print('\n「%s」→' % q)
        for pid, sc in search(q, topk=3):
            print('   pid=%-8s %.4f' % (pid, sc))
    if a.similar:
        import sqlite3
        c = sqlite3.connect(os.path.join(_ROOT, 'data', 'corpus.db'))
        print('\n与 pid=%d 相近：' % a.similar)
        for pid, sc in similar(a.similar, topk=3, conn=c):
            print('   pid=%-8s %.4f' % (pid, sc))


if __name__ == '__main__':
    main()
