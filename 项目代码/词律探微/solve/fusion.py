# -*- coding: utf-8 -*-
"""fusion.py —— 多路候选融合（RRF）与候选精排（Reranker）。

为什么单列一层
--------------
`retrieve.search()` 现在是**加权求和**融合（各路得分归一后乘权重相加）。它要求各路
得分**同尺度、可比**；而向量检索给出的只有「名次」（余弦相似度与 BM25 等根本不是
同一把尺）。硬把它的分数塞进加权求和的第 6 路，会**继续**依赖「权重调参」，正是
外部审查批评的「名义语义、实为调参」。故新增本层：以**名次**为准的 RRF 融合。

RRF（Reciprocal Rank Fusion，Cormack et al. 2009）
--------------------------------------------------
    score(pid) = Σ_路 1 / (k + rank_路(pid))          # rank 从 1 起
**为什么不用固定权重**：各路（二字组 / 元数据 / 全文 / 数值 / 声律 / 向量）的
**排名尺度不同**——元数据路是「命中即 1.0」的离散集合，数值路是 0~1 的连续量，
向量路是余弦相似度（本语料实测集中在 0.3~0.7）。用固定权重做线性组合，等于假设
「0.6 的余弦相似度」与「0.6 的归一化 BM25」对答案是等价的，这个假设没有任何依据，
只会把调参压力转嫁给运维。RRF 只看**名次**，天然免疫量纲问题，且无需调参（k 取
经验值 60，对结果不敏感）。

精排（cross-encoder）
--------------------
RRF 是「无序特征」的融合，仍可能把「字面/声律相近但主题不符」的篇排前。`rerank_block`
用交叉编码器（qwen3-reranker）对候选做**逐对**打分后重排——**仅在 reranker 可用时**
生效，不可用/失败一律**原序返回**（绝不因精排失败改动结果）。

⚠ 实测提醒（2026-10-08）：本机网关上的 `qwen3-reranker-4b` 在**单文档**下能正确响应
query（`rerank('枯藤老树昏鸦',['枯藤老树昏鸦'])`→0.86 vs `rerank('春眠不觉晓',['枯藤老树昏鸦'])`
→0.32），但**多文档**同批请求时分数近乎**与 query 无关**（同一篇目在不同 query 下恒居首位）。
故精排在本项目里**默认关闭**（`LVC_RERANK=1` 才启用），先保「不劣化」。详见交付报告。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_embed import default_reranker     # noqa: E402


def rrf(channels, k=60):
    """Reciprocal Rank Fusion：把**多路已排序的 pid 列表**融成一个 `{pid: 分数}`。

    参数
    ----
    channels : list[list[pid]]   每一路是**按名次从优到劣**排列的 pid 列表（不是字典）。
    k        : RRF 常数（经验值 60；越大越平滑，对结果不敏感）。

    返回 `{pid: score}`（分越高越靠前）。**同一 pid 出现在多路**会累加——这正是 RRF
    奖励「多路共识」的机制。
    """
    scores = {}
    for ch in channels or []:
        for rank, pid in enumerate(ch or [], 1):
            if pid is None:
                continue
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (k + rank)
    return scores


def ranked(score_map, limit=None):
    """把 `{pid: score}` 转成**按分降序**的 pid 列表（RRF 的输入格式）。

    排序键带 (score, pid) 兜底，保证**确定性**（同分时按 pid 字典序，绝不因哈希序抖动）。
    """
    items = sorted((score_map or {}).items(), key=lambda kv: (-kv[1], kv[0]))
    pids = [pid for pid, _s in items]
    return pids[:limit] if limit else pids


def _cand_texts(conn, pids):
    """候选篇的**精排文本**：`朝代·作者《词牌·题名》` + 前 2 句正文。

    为什么带前两句而不是整篇：精排是**逐对**代价，长调全篇会拖慢且稀释信号；
    「标题 + 起拍」已足够判断主题（与人读词的直觉一致）。
    """
    out = {}
    pids = list(pids or [])
    for i in range(0, len(pids), 500):
        chunk = pids[i:i + 500]
        qs = ','.join('?' * len(chunk))
        for r in conn.execute(
                'SELECT pid,dynasty,author,cipai,title,raw FROM poems WHERE pid IN (%s)' % qs,
                chunk):
            pid, dyn, au, cp, ti, raw = r[0], r[1] or '', r[2] or '', r[3] or '', r[4] or '', r[5] or ''
            head = (raw.split('\n') if raw else [])[:2]
            head = ' '.join(head).strip()
            label = '%s·%s《%s·%s》' % (dyn, au, cp, ti)
            out[pid] = (label + ' ' + head).strip()
    # 保序，缺失者以空串占位（与原序对齐，绝不因缺文本错位）
    return [out.get(p, '') for p in pids]


def rerank_block(conn, query, pids, topk=None):
    """对候选 `pids` 用 Reranker 精排，返回重排后的 pid 列表。

    · Reranker **不可用 / 失败 / 返回空** → **原序返回**（精排只可能改善，绝不因它崩或乱排）；
    · `topk` 给定时截断（None = 全留）。
    """
    pids = list(pids or [])
    if not pids:
        return []
    rrk = default_reranker()
    if not rrk.available():
        return pids[:topk] if topk else pids
    docs = _cand_texts(conn, pids)
    if not any(docs):
        return pids[:topk] if topk else pids
    res = rrk.rerank(query, docs, topk=None)
    if not res:
        return pids[:topk] if topk else pids
    order = [pids[i] for i, _s in res if 0 <= i < len(pids)]
    seen = set(order)
    order += [p for p in pids if p not in seen]      # 兜底：未被打分者按原序补回
    return order[:topk] if topk else order


def rerank_enabled():
    """精排是否启用（默认关闭；`LVC_RERANK=1` 开启）。见模块 docstring 的实测提醒。"""
    return os.environ.get('LVC_RERANK') == '1'
