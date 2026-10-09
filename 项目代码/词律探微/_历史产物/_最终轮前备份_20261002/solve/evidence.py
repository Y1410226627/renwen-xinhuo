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
    with_cond = spec is not None and retrieve.has_line_cond(spec)
    if with_cond:
        rows = conn.execute(
            'SELECT idx,text,han_len,ping,ze,pz,tail FROM lines WHERE pid=? ORDER BY idx',
            (pid,)).fetchall()
        reasons = {r0[0]: retrieve.line_satisfies(r0[5], r0[6], spec) for r0 in rows}
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
