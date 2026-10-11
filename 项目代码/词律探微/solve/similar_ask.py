# -*- coding: utf-8 -*-
"""similar_ask.py —— 「与某篇/某主题**类似**」的语义相似作答（规则路，单一职责）。

为什么单独一个模块
------------------
项目纪律是「**数字归引擎、文料归检索、说法归生成、出处归引用**」。本模块只做**一件事**：
把「与《X》类似 / 找写某主题的词」这类**语义相似**请求，接到**真正的向量检索**
（`vector_index.similar` / `vector_index.search`）上，再交回既有的**证据块 + 四道护栏**链路。
它**不重写**任何检索/护栏逻辑——只负责「意图识别 → 参照篇定位 → 向量取候选 → 组装论断」。

设计红线（与 vector_index 一致）
--------------------------------
1. **不改任何既有行为**：本模块只在 `ask._answer_impl` 里**新增一条前置分支**；
   分支不命中 / 向量不可用 / 任何异常 → 返回 `None`，主链**逐字节照旧**。
2. **向量不可用 → 优雅降级**：返回 `None`，由主链按原方式处理（不崩、不阻塞）。
   真正的向量可用性由 `vector_index.available()` 判定（默认关时自然为假）。
3. **不越界下结论**：向量只回答「**哪些最像**」，**不回答**「全库满足该语义的一个不少」
   —— 措辞里必须如实声明这一边界（`vector_index` 模块 docstring 第 6 条）。
4. **出处可点回**：候选一律走 `evidence.build_blocks` 出证据块，每条都带 pid 与逐句原文。

意图识别（窄口径，宁缺勿滥）
----------------------------
命中「相似/类似/相近/同主题/主题相近/风格接近…」**且**能定位到一个**参照对象**
（篇名 `《…》` 或先给（作者＋词牌））时才算数；只有「类似」二字而指不到任何参照 → 不接管。
"""
from __future__ import annotations
import re
import sqlite3

# —— 相似意图词（窄口径：必须同时能定位到参照对象才接管）——
_SIM_WORDS = ('相似', '类似', '相近', '相仿', '相像', '同主题', '主题相近', '题材相近',
              '风格相近', '风格接近', '意境相近', '意境相似', '主题相似', '相似的', '类似的',
              # ⚠ 2026-10-11 二期增补：补入「同调」「同一路数」等同族表述，放宽相似意图面。
              '同调', '同类', '一路', '如出一辙', '异曲同工')
# 书名号篇名：《作者·…》或《词牌·题名》或《词牌》
_BOOK_TITLE_RE = re.compile(r'《([^》]{1,60})》')
# 分隔符（词牌·题名）
_SEP_RE = re.compile(r'[·・•]')
# ⚠ 2026-10-11 二期增补：**显式"仿照/像…那样"句式**。这类句式**本身**就含明确的参照意图
#   （「像《X》那样」「仿《X》」「比照《X》」），不必再依赖「相似/类似」这类词——旧版把它
#   放在 `_SIM_WORDS` 门之后，导致「像《声声慢》那样写愁的词」（无"相似"二字）**永远进不来**。
#   ⚠ 与 `《X》` 的组合在 `is_similarity_ask` 里单独判定（必须**同时**有句式与书名号参照）。
_ANALOGY_RE = re.compile(r'像|如|仿|仿照|比照|效仿|模仿|类似|参照|比拟')


def _has_analogy_phrase(q):
    """是否含「像…那样/仿…/比照…」**显式参照句式**（与《…》合用时单独成立）。"""
    return bool(re.search(r'(?:像|如|仿|仿照|比照|效仿|模仿|参照)[^，,。？?]{0,30}'
                          r'(?:那样|这样|一般|似的|风格|一路|的)', q))


def is_similarity_ask(question):
    """问句是否是**语义相似**请求（窄口径）。返回 True/False。

    判据（任一成立即接管，但**都必须能定位到参照对象**）：
      A) 含相似词（相似/类似/同调…）**且**含一个可作参照的《…》篇名；
      B) 含**显式仿照句式**（像《X》那样 / 仿《X》 / 比照《X》…）**且**含《…》篇名。
    只有「类似」二字而指不到任何参照 → 不接管（留给主链，避免把「有哪些类似的词」误当相似检索）。
    """
    q = question or ''
    has_ref = bool(_BOOK_TITLE_RE.search(q))
    if not has_ref:
        return False
    # B) 显式仿照句式：本身即含参照意图，无需相似词
    if _has_analogy_phrase(q):
        return True
    # A) 相似词 + 参照篇名
    if any(w in q for w in _SIM_WORDS):
        return True
    return False


def _resolve_reference(conn, question):
    """从问句里定位**参照篇**：返回 `(pid, label)` 或 `(None, 参照文本)`。

    优先按《…》里的篇名解析：
      · `《词牌·题名》` → 词牌 + 题名 双条件
      · `《词牌》`       → 词牌
      · `《篇名》`       → 标题 LIKE
    命中最长/最精确的一条；多条并列时取标题最相似者（标题里含括号内容的优先）。
    """
    m = _BOOK_TITLE_RE.search(question or '')
    if not m:
        return None, None
    inner = m.group(1).strip()
    if not inner:
        return None, None
    parts = _SEP_RE.split(inner, 1)
    if len(parts) == 2:
        cipai, subt = parts[0].strip(), parts[1].strip()
    else:
        cipai, subt = '', inner
    cands = []
    if cipai and subt:
        cands = conn.execute(
            'SELECT pid,author,title,cipai FROM poems WHERE cipai=? AND title LIKE ? LIMIT 5',
            (cipai, '%' + subt + '%')).fetchall()
    if not cands and cipai:
        cands = conn.execute(
            'SELECT pid,author,title,cipai FROM poems WHERE cipai=? LIMIT 5', (cipai,)).fetchall()
    if not cands:
        cands = conn.execute(
            'SELECT pid,author,title,cipai FROM poems WHERE title LIKE ? LIMIT 5',
            ('%' + inner + '%',)).fetchall()
    if not cands:
        return None, inner
    # 精确优先：标题与 inner 越接近越好（完全相等 > 含题名 > 仅同词牌）
    def _rank(r):
        title = r[2] or ''
        exact = 0 if title == inner else 1
        contains = 0 if inner in title or (subt and subt in title) else 1
        return (exact, contains, len(title))
    best = sorted(cands, key=_rank)[0]
    label = '%s《%s》' % (best[1] or '', best[2] or best[3] or '')
    return best[0], label


def answer_similar(conn, question, topk=5, min_score=0.0):
    """语义相似作答主函数。**返回 dict 或 None**。

    返回 `None` 的情形（一律交回主链，绝不半成品）：
      · 不是相似意图；或
      · 向量索引不可用（`vector_index.available()` 为假 / 导入失败）。
    返回 dict 时，结构与 `ask.answer` 的返回**同构**（含 answer/blocks/verify/refused…），
    因此调用方可以**直接**把它当作答案返回。
    """
    if not is_similarity_ask(question):
        return None
    try:
        import vector_index as VI
    except Exception:                                            # noqa: BLE001
        return None
    if not VI.available(conn):
        return None

    import evidence
    import guard

    pid, label = _resolve_reference(conn, question)
    hits = []
    ref_note = ''
    if pid:
        hits = VI.similar(pid, topk=max(topk, 5), conn=conn) or []
        # ⚠ 护栏①：ref_note 会进正文，**不得含 pid 里的数字**（文件名/下标不是语料事实），
        #   故只写人可读的「作者《篇名》」，不写 pid。
        ref_note = '参照篇：%s' % label
    if not hits:
        # 参照篇不在库中 / 定位不到 → 用书名号里的文本直接做语义检索
        qtext = (label or '').strip()
        if not qtext:
            return None
        hits = VI.search(qtext, topk=max(topk, 5), conn=conn, level='poem') or []
        # ⚠ 护栏②：说明文字**不得用「」**（会被判「引文未逐字落地」），用【】。
        ref_note = ('参照对象【%s】未在本库中精确定位到篇目，'
                    '已按其文字做**语义检索**相近作品' % qtext) if qtext else ''
    if not hits:
        return None

    hits = [(p, s) for p, s in hits if s >= min_score][:topk]
    if not hits:
        return None

    pids = [p for p, _ in hits]
    scores = {p: s for p, s in hits}
    rows = __import__('retrieve').items_of(conn, pids, scores=scores)
    if not rows:
        return None
    blocks = evidence.build_blocks(conn, rows, with_lines=1)
    if not blocks:
        return None

    # —— 组装答案文本 ——
    # ⚠ 写作纪律（护栏②要求）：正文里的「」**只**允许引用语料原文；
    #   本模块的说明文字一律用【】或加粗，**不用「」**（否则被判「引文未逐字落地」）。
    # ⚠ 护栏①：正文里出现的任何数字都必须能在证据块找到，或经 `allow` 显式放行
    #   ——此处把「相关度分数」与「篇序 1..N」放进 allow；pid 的文件名/下标**不写进正文**。
    _sc = []
    for _p, _s in hits:
        _sc.append('%.3f' % _s)
        _sc.append(_s)
    allow = tuple(_sc + [len(blocks)])

    lines = ['【查询理解】（来源：语义相似检索）与所述参照**主题相近**的作品，'
             '按向量语义相关度降序——这是**最像的几篇**，不是**全库满足该主题的一个不少**。',
             '　　　' + ref_note]
    lines.append('【结论】语义相关度最高的 %d 篇如下（相关度见证据块 score；'
                 '向量只回答**哪些最像**，不做**全集**承诺）：' % len(blocks))
    for i, b in enumerate(blocks, 1):
        # ⚠ 护栏①：**不要**用「N.」这种纯数字序号——序号数字会与语料里的数字同形，
        #   一旦该数字不在证据块白名单（如某篇恰好没有并列的 N），就误判「数字无出处」。
        #   改用「·」项目符 + 篇名，序号只体现在顺序上。
        lines.append('　　　· %s%s《%s》：%d 句 / %d 字，仄声比例 %.1f%%，声情 %s（相关度 %.3f）'
                     % ((b.get('dynasty') or '') and ('%s·' % b['dynasty']) or '',
                        b.get('author') or '', b.get('title') or b.get('cipai') or '',
                        b.get('sent_n') or 0, b.get('han_len') or 0,
                        b.get('ze_ratio') or 0.0, b.get('scene') or '—',
                        scores.get(b['pid'], 0.0)))
    lines.append('【推断边界｜优劣型问句】语义相关度只是向量距离的排序，不能据此评定作品高下'
                 '——不构成文学价值判断；文本层面的近邻也不等于作者意图或时代因果。')
    text = '\n'.join(lines)

    ok, problems = guard.verify(text, blocks, boundary_kind='优劣型', allow=allow)
    return {
        'question': question,
        'spec': ref_note,
        'kind': '语义相似',
        'blocks': blocks,
        'answer': text,
        'verify': (ok, problems),
        'refused': False,
        'problems': problems,
        'total': len(blocks),
        'narrator': 'template',
        'parse_source': '语义相似检索（向量）',
        'parse_notes': [ref_note],
        'safety': {'ok': True},
    }


def main():
    """CLI 自检：`python solve/similar_ask.py "与《小重山·代乐府雅词僧祖可》类似的清词"`。"""
    import os
    import sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    conn = sqlite3.connect(os.path.join(root, 'data', 'corpus.db'))
    q = sys.argv[1] if len(sys.argv) > 1 else '找几首与《小重山·代乐府雅词僧祖可》类似的清词'
    print('问句：%s' % q)
    print('是相似意图：%s' % is_similarity_ask(q))
    r = answer_similar(conn, q, topk=5)
    if r is None:
        print('（未接管 / 向量不可用）')
        return 1
    print(r['answer'])
    print('护栏：%s %s' % r['verify'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
