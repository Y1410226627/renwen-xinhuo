# -*- coding: utf-8 -*-
"""M8 证据块与片段级引用。

设计（《系统实现逻辑》M8）：**数字归引擎、文料归检索、说法归生成、出处归引用**。
每个证据块携带：可定位出处（pid = 文件名#数组下标）、引擎算出的数字、若干句级片段（原样）。

与外部交付的差异：证据块额外携带**逐字注音表**，且数字白名单按**字段**给出，
使护栏①能做「数字必须来自**被引证据块**的某个字段」的字段级校验。

字段命名与 `corpus.db` 同源：`sent_n` 句数、`han_len` 汉字数、`ping`/`ze` 平仄字数。
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import retrieve                                            # noqa: E402
from pronounce import Pronouncer, default_overrides_path   # noqa: E402

_ENG = None


def _engine():
    global _ENG
    if _ENG is None:
        from prosody import Engine
        _ENG = Engine(Pronouncer(default_overrides_path()))
    return _ENG


def char_table(text):
    """逐字表：[(字, 调, 平/仄)]（数字与平仄全部由引擎给出）。"""
    return _engine().p.annotate(text)


def poem_block(conn, pid, top_lines=1, spec=None):
    """单篇证据块：篇级统计 + 句级统计 + （可选）命中句标记。

    `spec` 给定时：**优先选满足行级条件（句脚字/句脚平仄/声律模式）的句**，
    并在每句上标 `matched` 与 `match_reasons`。
    ——旧行为（spec=None）逐字不变：取「仄声占比最高」的句（默认代表句）。
    """
    r = conn.execute(
        'SELECT pid,dynasty,author,cipai,title,source,sent_n,han_len,ping,ze,ze_ratio,'
        'scene,change,longest_len,threshold,raw FROM poems WHERE pid=?', (pid,)).fetchone()
    if not r:
        return None
    (pid, dyn, author, cipai, title, source, sent_n, han_len, ping, ze, ze_ratio,
     scene, change, longest_len, threshold, raw) = r
    with_cond = spec is not None and (retrieve.has_line_cond(spec)
                                      # ⚠ 2026-10-08：**提取型问题**（第 N 句第 M 字）本身没有
                                      #   句级**筛选**条件，但它必须让「被取字的那一句」进证据块
                                      #   （否则答案引用的句子无法逐字落地，护栏会判「引文未落地」）。
                                      #   故把 extract 也算作「需要选句展示」的一类。
                                      or bool(getattr(spec, 'extract', None)))
    # ⚠ 2026-10-08 新增（缺陷3 取舍）：`consist`（声情标注为 X 但实测前后段相反）是**篇级**量，
    #   不属于任何单句 → **不**放进 `line_satisfies`（否则会把全篇每一句都误标成「命中句」）。
    #   这里单列为**篇级命中理由**，供上层如实说明「本篇为何入选」。判据与 `retrieve._sql()`
    #   的 consist 编译口径一致（后段上升→change<0、后段下降→change>0、其余→|change|<1）。
    #
    # ── `poem_reasons` 数据结构契约（供 `ask.py` 等上层接入；2026-10-08） ──────────────────
    #   类型：`list[str]`（有序，可空）。每一项是一条**已成立的**「本篇为何入选」的**篇级**理由，
    #         是可直接展示给人看的中文短句，**不含**任何需要再计算的占位符（数字均已落地）。
    #   与 `lines[i]['match_reasons']` 的分工：
    #     · `match_reasons`（句级）：`list[str]`，挂在**具体某一句**上（`line_satisfies` 产出），
    #       含义＝「这一句满足了问句的哪条行级条件」（如「句脚字」「平仄串全等」「句级算子·满足句」）。
    #     · `poem_reasons`（篇级）：**不**属于任何单句的条件（如 `consist`：声情标注与实测前后段
    #       相反，是全篇声情走向）——若塞进句级会把全篇每一句都误标成命中句，故单列于此。
    #   产出位置：`poem_block()` 返回 dict 的 `'poem_reasons'` 键（与 `'n_match'`/`'lines'` 同级）。
    #   当前仅 `consist` 一类会写入；将来任何「无对应单句的篇级条件」都往这里追加即可（结构不变）。
    #   例：Q 问「…声情标注为后段下降但实测前后段相反的清词」，某篇 change=+3.2 被选中 →
    #       `poem_reasons == ['声情标注为后段下降但实测前后段相反（篇级命中理由）']`。
    # ──────────────────────────────────────────────────────────────────────────────────────
    poem_reasons = []
    _consist = getattr(spec, 'consist', None) if spec is not None else None
    if _consist:
        _ok_consist = (change is not None and (
            (_consist == '后段上升' and change < 0)
            or (_consist == '后段下降' and change > 0)
            or (_consist not in ('后段上升', '后段下降') and abs(change) < 1)))
        if _ok_consist:
            poem_reasons.append('声情标注为%s但实测前后段相反（篇级命中理由）' % _consist)
    if with_cond:
        rows = conn.execute(
            'SELECT idx,text,han_len,ping,ze,pz,tail FROM lines WHERE pid=? ORDER BY idx',
            (pid,)).fetchall()
        # ⚠ 2026-10-08（缺陷3）：`line_satisfies` 现已支持高级句级条件（line_q 谓词 / pz_exact /
        #   tail_each / parity），故传入该句的 `idx`（句位）与 `han_len`（句长）——否则句级算子
        #   命中的句算不出来，`m_idx` 为空 → 落到「按仄声占比最高」的句，展示与问句无关的句子。
        reasons = {r0[0]: retrieve.line_satisfies(r0[5], r0[6], spec, idx=r0[0], han_len=r0[2])
                   for r0 in rows}
        m_idx = [r0[0] for r0 in rows if reasons[r0[0]]]
        # 多值句脚题：**每个不同的句脚先各占一个位**，再按原序补——
        # 否则同一篇里满足了 5 句、展示只取前 2 句，被问的另一个句脚就又被埋了。
        if len(m_idx) > 1:
            tl_of = {r0[0]: r0[6] for r0 in rows}
            first, seen_t = [], set()
            for i in m_idx:
                t = tl_of.get(i)
                if t not in seen_t:
                    seen_t.add(t)
                    first.append(i)
            m_idx = first + [i for i in m_idx if i not in first]
        pick = [r0 for r0 in rows if r0[0] in set(m_idx[:top_lines])]
        # 仍有空位时用「仄声占比最高」的句补齐（与旧口径一致）
        if len(pick) < top_lines:
            rest = sorted([r0 for r0 in rows if r0[0] not in set(m_idx[:top_lines])],
                          key=lambda r0: (-(r0[4] / (r0[2] or 1.0)), r0[0]))
            pick += rest[:top_lines - len(pick)]
        # ⚠ 2026-10-08 新增：**提取型问题**（第 N 句第 M 字）必须让「被取字的那一句」
        #   出现在证据里 —— 否则答案里引用的那一句无法在证据块中**逐字落地**，
        #   护栏会正确地判「引文未落地」并把整条回答标为未通过（实测已拦下）。
        #   做法：把目标句**提到 pick 最前**（并去重），保证它一定被展示。
        _ex = getattr(spec, 'extract', None) if spec is not None else None
        if _ex:
            try:
                _sn = int(_ex.get('sent') or 0)
            except Exception:
                _sn = 0
            if _sn >= 1:
                _tgt = [r0 for r0 in rows if r0[0] == _sn - 1]
                if _tgt:
                    pick = _tgt + [r0 for r0 in pick if r0[0] != _tgt[0][0]]
        lines = [(r0[0], r0[1], r0[2], r0[3], r0[4], r0[5], r0[6], reasons[r0[0]])
                 for r0 in pick]
    else:
        lines = [(i, t, hl, p, z, pz, tl, []) for i, t, hl, p, z, pz, tl in conn.execute(
            'SELECT idx,text,han_len,ping,ze,pz,tail FROM lines WHERE pid=? '
            'ORDER BY CAST(ze AS REAL)/(han_len + 0.0) DESC, idx LIMIT ?',
            (pid, top_lines)).fetchall()]
    return {
        'pid': pid, 'dynasty': dyn, 'author': author, 'cipai': cipai, 'title': title,
        'source': source, 'sent_n': sent_n, 'han_len': han_len, 'ping': ping, 'ze': ze,
        'ze_ratio': ze_ratio, 'scene': scene, 'change': change, 'longest_len': longest_len,
        'threshold': threshold, 'raw': raw,
        'n_match': len([1 for _a, _b, _c, _d, _e, _f, _g, rs in lines if rs]) if with_cond else 0,
        'poem_reasons': poem_reasons,
        'lines': [{'idx': i, 'seq': i + 1, 'text': t, 'han_len': hl, 'ping': p, 'ze': z, 'pz': pz,
                   'tail': tl, 'matched': bool(rs), 'match_reasons': rs}
                  for i, t, hl, p, z, pz, tl, rs in lines],
    }


def build_blocks(conn, rows, with_lines=1, spec=None):
    """把 retrieve.search 的结果转成带编号的证据块（[E1][E2]…）。"""
    blocks = []
    for i, r in enumerate(rows, 1):
        b = poem_block(conn, r['pid'], top_lines=with_lines, spec=spec)
        if not b:
            continue
        b['eid'] = 'E%d' % i
        b['score'] = r.get('score')
        if 'contrib' in r:
            b['contrib'] = r['contrib']
        blocks.append(b)
    return blocks


def numbers_of(block):
    """单个证据块里**允许被引用的数字**（字段级白名单，含由字段派生的两种写法）。"""
    out = set()

    def add(v):
        out.add(str(v))
        try:
            f = float(v)
            out.add('%.1f' % f)
            out.add(str(int(f)) if f == int(f) else '%.1f' % f)
            out.add('%.1f' % abs(f))          # 「变化 -3.7」与「变化 3.7」同源
            out.add(str(int(abs(f))) if abs(f) == int(abs(f)) else '%.1f' % abs(f))
        except (TypeError, ValueError, OverflowError):     # inf 会抛 OverflowError（审查 B30）
            pass

    for k in ('sent_n', 'han_len', 'ping', 'ze', 'ze_ratio', 'change', 'longest_len', 'threshold'):
        if block.get(k) is not None:
            add(block[k])
    for L in block['lines']:
        for k in ('han_len', 'ping', 'ze'):
            add(L[k])
        add(L['idx'] + 1)          # 回答里写「第 N 句」用的是**从 1 起**的句序
        try:
            add(round(100.0 * L['ze'] / (L['han_len'] or 1), 1))
        except TypeError:
            pass
    return out


def texts_of(block):
    """单个证据块里**允许被引用的文料**：该篇标题 + 其句级片段（原样）。"""
    return {block['title']} | {L['text'] for L in block['lines']}


def all_numbers_phrase(blocks, extra=()):
    out = set()
    for b in blocks:
        out |= numbers_of(b)
    for v in extra:
        out.add(str(v))
        try:
            out.add('%.1f' % float(v))
        except (TypeError, ValueError):
            pass
    return out


def all_texts(blocks):
    out = set()
    for b in blocks:
        out |= texts_of(b)
    return out


def render_text(blocks, with_char=False):
    """纯文本排版（供人工阅读与落盘核对）。"""
    out = []
    for b in blocks:
        out.append('[%s] %s·%s《%s》（%s）' % (b['eid'], b['dynasty'], b['author'],
                                              b['title'], b['cipai']))
        out.append('     篇级：%d 句 / %d 字，平 %d、仄 %d，仄声比例 %.1f%%；声情 %s，变化 %.1f'
                   % (b['sent_n'], b['han_len'], b['ping'], b['ze'], b['ze_ratio'],
                      b['scene'], b['change']))
        for L in b['lines']:
            out.append('     第 %d 句：「%s」%d 字，平 %d 仄 %d，平仄 %s%s%s'
                       % (L['idx'] + 1, L['text'], L['han_len'], L['ping'], L['ze'], L['pz'],
                          '，句脚 ' + (L.get('tail') or '') if L.get('tail') else '',
                          '（命中问句条件）' if L.get('matched') else ''))
            if with_char:
                out.append('           逐字：%s' % ' '.join(
                    '%s/%s' % (c, z) for c, _t, z in char_table(L['text'])))
        out.append('     来源：%s（pid = 文件名#数组下标，可点回原文）' % b['source'])
    return '\n'.join(out)


if __name__ == '__main__':
    conn = sqlite3.connect(sys.argv[2] if len(sys.argv) > 2 else 'data/corpus.db')
    pid = sys.argv[1] if len(sys.argv) > 1 else 'ci.清.0000.base.json#0'
    print(render_text([dict(poem_block(conn, pid, top_lines=1), eid='E1')], with_char=True))
