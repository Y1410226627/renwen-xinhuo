# -*- coding: utf-8 -*-
"""llm_embed.py —— 嵌入（Embedder）与精排（Reranker）客户端（**只用 Python 标准库**）。

为什么单独一层（外部架构审查结论）
----------------------------------
审查确认：`retrieve.search()` 里所谓的「语义相关度」**不是 embedding**，而是
「大模型扩几个词 → 塞进 FTS/bigram」。这对「明月/秋风」这类**显性词**有效，
但对「**秋景**」「**羁旅愁思**」「**与这首词主题相近**」这类**词面必然不重合**的
问题天然无能——那是**结构缺失**，不是参数问题。本模块补上真正的向量检索所需的
两个原子能力：**文本嵌入**与**候选精排**。

设计原则（与 `llm.py` 同一口径）
--------------------------------
1. **只用标准库**（`urllib` + `json`），不引入第三方 SDK——与项目 `llm.py` 一致。
2. **安静降级、绝不抛未捕获异常**：断网 / 超时 / 非 200 → 返回 `None`/`[]` 并
   把原因写进线程本地的 `last_error`。**主链（问答）不因它崩**。
3. **线程安全**：`last_error` 落 `threading.local()`（与 `llm.py` 的 P0 修复同口径），
   探活结果与单例用 `threading.Lock` 保护。
4. **密钥不落源码**：读 `solve/data/llm_local.json` 的 `url`/`key`；环境变量优先。

端点（GPUStack 实测可用）
-------------------------
* 嵌入：`POST {base}/v1-openai/embeddings`，模型 `qwen3-vl-embedding-8b`，**4096 维**。
* 精排：`POST {base}/v1/rerank`，模型 `qwen3-reranker-4b`，
  body `{"model","query","documents":[...]}` → `{"results":[{"index","relevance_score"}]}`。

网络注意：本机 `curl` 走系统代理会 502，**必须**用 `urllib` + `ProxyHandler({})` 直连。

环境变量（优先级：显式参数 > 环境变量 > 本地配置 > 默认值）
--------------------------------------------------------
`LVC_EMBED_URL` / `LVC_EMBED_KEY` / `LVC_EMBED_MODEL` / `LVC_RERANK_MODEL`
（另支持 `LVC_RERANK_URL`、`LVC_EMBED_TIMEOUT` 作可选覆盖）。

用法
----
    python solve/llm_embed.py            # 连通性自检（维度 / 耗时 / 相似度对照）
"""
import json
import math
import os
import sys
import threading
import time
import urllib.error
import urllib.request

# 本地配置文件（**密钥不写进源码**）：与 llm.py 共用同一份 solve/data/llm_local.json
LOCAL_CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'llm_local.json')

DEFAULT_EMBED_PATH = '/v1-openai/embeddings'
DEFAULT_RERANK_PATH = '/v1/rerank'
DEFAULT_EMBED_MODEL = 'qwen3-vl-embedding-8b'
DEFAULT_RERANK_MODEL = 'qwen3-reranker-4b'
MAX_BATCH = 16                      # 单次嵌入请求 ≤16 条（审查建议；服务端亦友好）
_UA = 'cilv-tanwei/1.0'


def _read_local_conf():
    """读本地配置（密钥不落源码）；文件不存在或损坏时安静返回 {}。"""
    try:
        if os.path.isfile(LOCAL_CONF):
            with open(LOCAL_CONF, encoding='utf-8-sig') as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def _base_of(url):
    """取 `scheme://netloc`（去掉路径）；解析失败返回 None。"""
    try:
        from urllib.parse import urlsplit
        sp = urlsplit(url or '')
        if sp.scheme and sp.netloc:
            return '%s://%s' % (sp.scheme, sp.netloc)
    except Exception:
        pass
    return None


def _opener():
    """**直连**打开器（`ProxyHandler({})`）——本机 curl 走代理会 502。"""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _cos(a, b):
    """余弦相似度（自检用；空向量返回 0）。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class _Base(object):
    """嵌入 / 精排客户端共同基类：密钥读取、线程本地 last_error、探活缓存。"""

    def __init__(self, url=None, key=None, model=None, timeout=None):
        conf = _read_local_conf()
        conf_base = _base_of(conf.get('url')) or ''
        self.key = (key or os.environ.get('LVC_EMBED_KEY') or conf.get('key'))
        self.timeout = int(timeout or os.environ.get('LVC_EMBED_TIMEOUT') or 30)
        self._lock = threading.Lock()
        self._tls = threading.local()          # 线程私有的瞬时调用状态（last_error）
        self._probed = None                    # 探活结果缓存（None=未探；True/False）
        self._probe_err = None
        self._base = conf_base
        self._init_url_model(url, model, conf_base)

    # 子类覆写：决定 url / model 的来源
    def _init_url_model(self, url, model, conf_base):
        raise NotImplementedError

    # —— 线程安全（与 llm.py 口径一致：last_error 落线程本地，不跨请求串号）——
    @property
    def last_error(self):
        """本线程**最近一次**调用的失败原因（成功为 None）。线程隔离。"""
        return getattr(self._tls, 'last_error', None)

    @last_error.setter
    def last_error(self, value):
        self._tls.last_error = value

    def available(self, force=False):
        """探活并缓存：可用返回 True；不可用返回 False（**失败结果缓存**，避免每次重试）。

        探活 = 发一次最小请求（1 条文本 / 1 对 query-doc）。失败原因留在 `last_error`。
        """
        with self._lock:
            if self._probed is not None and not force:
                return self._probed
        ok = self._probe()
        with self._lock:
            self._probed = ok
        return ok

    def _probe(self):
        raise NotImplementedError

    def _post(self, url, payload):
        """POST 一段 JSON；返回解析后的 dict；失败返回 None 并写 last_error。**绝不抛**。"""
        try:
            body = json.dumps(payload).encode('utf-8')
        except Exception as e:                                  # 极少数不可序列化对象
            self.last_error = '序列化失败: %s: %s' % (type(e).__name__, e)
            return None
        req = urllib.request.Request(url, data=body, method='POST', headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % (self.key or ''),
            'User-Agent': _UA,
        })
        try:
            with _opener().open(req, timeout=self.timeout) as r:
                raw = r.read().decode('utf-8')
            self.last_error = None
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            detail = ''
            try:
                detail = e.read().decode('utf-8', 'replace')[:200]
            except Exception:
                pass
            self.last_error = 'HTTP %s %s' % (e.code, detail)
        except Exception as e:                                   # 超时 / 断网 / DNS / JSON
            self.last_error = '%s: %s' % (type(e).__name__, e)
        return None


class Embedder(_Base):
    """文本嵌入客户端。`available()` 为假时调用方应**完全跳过**向量路。"""

    def _init_url_model(self, url, model, conf_base):
        self.url = (url or os.environ.get('LVC_EMBED_URL')
                    or (conf_base + DEFAULT_EMBED_PATH if conf_base else None))
        self.model = model or os.environ.get('LVC_EMBED_MODEL') or DEFAULT_EMBED_MODEL
        self.dim = None                     # 首次成功嵌入后记录（服务端返回 4096）

    def _probe(self):
        if not self.url or not self.key:
            self.last_error = ('缺少嵌入端配置（url/key）——环境变量 LVC_EMBED_URL/LVC_EMBED_KEY '
                               '或 %s' % os.path.relpath(LOCAL_CONF))
            return False
        r = self._post(self.url, {'model': self.model, 'input': ['ping']})
        if not r:
            return False
        try:
            vec = r['data'][0]['embedding']
            self.dim = len(vec)
            return bool(self.dim)
        except Exception as e:
            self.last_error = '响应结构异常: %s' % e
            return False

    def embed(self, texts):
        """把一批文本嵌入为向量列表（顺序与输入一致）。

        * **自动分批**，每批 ≤ `MAX_BATCH`（16）。
        * **任一批失败 → 整次返回 None**（不返回半截结果）：半截列表会与调用方的
          `texts` 下标**静默错位**，那比「拿不到向量」危险得多。失败原因在 `last_error`。
        """
        texts = list(texts or [])
        if not texts:
            return []
        if not self.available():
            if not self.last_error:
                self.last_error = '嵌入端不可用'
            return None
        out = []
        for i in range(0, len(texts), MAX_BATCH):
            chunk = texts[i:i + MAX_BATCH]
            r = self._post(self.url, {'model': self.model, 'input': chunk})
            if not r:
                return None                                 # 整批失败 → 整次 None（见 docstring）
            try:
                data = r['data']
                # OpenAI 兼容响应带 index；按 index 归位，防止服务端乱序返回
                data = sorted(data, key=lambda d: d.get('index', 0))
                vecs = [d['embedding'] for d in data]
                if len(vecs) != len(chunk):
                    self.last_error = '返回条数不符（请求 %d、返回 %d）' % (len(chunk), len(vecs))
                    return None
                self.dim = len(vecs[0])
                out.extend(vecs)
            except Exception as e:
                self.last_error = '响应结构异常: %s: %s' % (type(e).__name__, e)
                return None
        return out


class Reranker(_Base):
    """候选精排客户端。不可用时 `rerank()` 返回 `[]`（调用方应**原序返回**）。"""

    def _init_url_model(self, url, model, conf_base):
        # rerank 端点的 base 优先取自 `LVC_RERANK_URL`，其次由嵌入 base 推导（同一网关）。
        base = _base_of(os.environ.get('LVC_RERANK_URL') or '')
        self.url = (url or os.environ.get('LVC_RERANK_URL')
                    or (base + DEFAULT_RERANK_PATH if base else
                        (conf_base + DEFAULT_RERANK_PATH if conf_base else None)))
        self.model = model or os.environ.get('LVC_RERANK_MODEL') or DEFAULT_RERANK_MODEL

    def _probe(self):
        if not self.url or not self.key:
            self.last_error = ('缺少精排端配置（url/key）——环境变量 LVC_RERANK_URL/'
                               'LVC_EMBED_KEY 或 %s' % os.path.relpath(LOCAL_CONF))
            return False
        r = self._post(self.url, {'model': self.model, 'query': 'ping',
                                  'documents': ['ping']})
        return bool(r and 'results' in r)

    def rerank(self, query, docs, topk=None):
        """对 `docs` 按与 `query` 的相关度重排，返回 `[(原下标, 分数)]`（降序）。

        失败（不可用 / 断网 / 结构异常）返回 `[]`——调用方据此**保持原序**。
        """
        docs = list(docs or [])
        if not docs:
            return []
        if not self.available():
            return []
        r = self._post(self.url, {'model': self.model, 'query': query, 'documents': docs})
        if not r:
            return []
        try:
            items = r['results']
            pairs = [(int(it['index']), float(it['relevance_score'])) for it in items]
            pairs.sort(key=lambda x: (-x[1], x[0]))
            return pairs[:topk] if topk else pairs
        except Exception as e:
            self.last_error = '响应结构异常: %s: %s' % (type(e).__name__, e)
            return []


# —— 进程内单例（供 vector_index / fusion 复用；探活结果随之缓存一次）——
_EMB = None
_RRK = None
_SINGLETON_LOCK = threading.Lock()


def default_embedder():
    global _EMB
    with _SINGLETON_LOCK:
        if _EMB is None:
            _EMB = Embedder()
        return _EMB


def default_reranker():
    global _RRK
    with _SINGLETON_LOCK:
        if _RRK is None:
            _RRK = Reranker()
        return _RRK


def main():
    print('==' * 30)
    print('词律探微 · 嵌入/精排连通性自检')
    print('==' * 30)
    emb = default_embedder()
    print('嵌入端点：%s' % emb.url)
    print('嵌入模型：%s' % emb.model)
    t = time.time()
    ok = emb.available()
    print('嵌入探活：%s（%.2f 秒）%s' % ('✓ 可用' if ok else '✗ 不可用',
                                        time.time() - t,
                                        '' if ok else '原因=' + str(emb.last_error)))
    if ok:
        texts = ['明月几时有，把酒问青天', '碧云天，黄叶地，秋色连波', '今天天气真不错']
        t = time.time()
        vs = emb.embed(texts)
        dt = time.time() - t
        if vs:
            print('嵌入 %d 条：维度=%d 耗时=%.2f 秒（%.3f 秒/条）'
                  % (len(vs), len(vs[0]), dt, dt / len(vs)))
            print('相似度对照（对「明月几时有，把酒问青天」）：')
            for txt, v in zip(texts[1:], vs[1:]):
                print('    cos=%.4f  %s' % (_cos(vs[0], v), txt))
        else:
            print('✗ 嵌入失败：%s' % emb.last_error)
    rrk = default_reranker()
    print('-' * 60)
    print('精排端点：%s' % rrk.url)
    print('精排模型：%s' % rrk.model)
    t = time.time()
    ok2 = rrk.available()
    print('精排探活：%s（%.2f 秒）%s' % ('✓ 可用' if ok2 else '✗ 不可用',
                                        time.time() - t,
                                        '' if ok2 else '原因=' + str(rrk.last_error)))
    if ok2:
        q = '写秋景的词'
        docs = ['碧云天，黄叶地，秋色连波', '独在异乡为异客', '春眠不觉晓']
        t = time.time()
        res = rrk.rerank(q, docs, topk=None)
        print('精排「%s」耗时 %.2f 秒：' % (q, time.time() - t))
        for idx, sc in res:
            print('    %.4f  %s' % (sc, docs[idx]))
    return 0 if (ok or ok2) else 1


if __name__ == '__main__':
    sys.exit(main())
