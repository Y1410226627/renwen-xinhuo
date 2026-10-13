# -*- coding: utf-8 -*-
"""tone_policy.py —— **声律双口径并存**：评测口径（普通话四声）与历史口径（《广韵》）。

为什么要这个模块
================
词律研究里，同一个字位的平仄**取决于用哪套音系**：
  · **评测口径**（本系统默认、也是赛事题库口径）：按**普通话四声**折平仄——
    阴平/阳平记平，上声/去声记仄，**不注入声、不划韵部**；
  · **历史口径**：《广韵》的**音韵地位**（声母/韵目/声调）所反映的中古平仄——
    与普通话口径**可能不同**（最典型：入声字在普通话里散入四声）。

两套口径**都不是错的**，它们回答的是不同的问题。本模块让它们**并存**：

  1. **默认口径一字不改**：`corpus.db` 的 `pz` 列与 `pronounce/prosody` 的全部行为**原样不动**
     → 交付答案（`answers_700`）零回归。历史口径是**并存的第二视角**，绝不回写语料。
  2. **差异如实列出**：逐字位给出「评测口径 / 历史口径 / 是否一致 / 原因」，
     **不取多数票、不互相覆盖、不擅自判定谁对**（见 `GLOSSARY.md`「口径」条与「核验深度分层」条）。
  3. **缺就是缺**：广韵未收录（本语料 7,711 字中收录 5,147 字）、或多候选未定，
     一律**如实标注**，不猜、不用普通话顶替。

数据来源
========
`data/rhyme/tshet_uinh.json`（由 `node tools/export_tshet_uinh.mjs` 从 vendor 的
推音 tshet-uinh 组件导出；MIT · Project NK2028）。**只作历史音韵参考，不是清代实际读音。**

用法
====
    python solve/tone_policy.py --pid ci.清.0001.base.json#0
    python solve/tone_policy.py --pid <pid> --json
"""
import argparse
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(_ROOT, 'data', 'corpus.db')
HISTORICAL_PATH = os.path.join(_ROOT, 'data', 'rhyme', 'tshet_uinh.json')

#: 口径标识（**并存**，不是替换关系）
POLICIES = ('mandarin', 'historical', 'both')

#: 对照结论四态
MATCH = 'match'            # 两口径一致
DIFFER = 'differ'          # 两口径不一致（**如实并列**，不判谁对）
HIST_MISSING = 'hist_missing'      # 广韵未收录该字
HIST_AMBIGUOUS = 'hist_ambiguous'  # 广韵多候选（未定）

_HAN_RE = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
_HIST_CACHE = None


def _historical():
    """懒加载《广韵》字头表（glyph → [条目]）。取不到返回空 dict（**如实降级**）。"""
    global _HIST_CACHE
    if _HIST_CACHE is None:
        try:
            with open(HISTORICAL_PATH, encoding='utf-8') as f:
                _HIST_CACHE = json.load(f) or {}
        except (OSError, ValueError):
            _HIST_CACHE = {}
    return _HIST_CACHE


def historical_available():
    """历史口径是否可用（数据在位）；不可用时调用方应**如实说明**而不是静默顶替。"""
    return bool(_historical())


def historical_of(ch):
    """某字的《广韵》条目列表（可能为空）。"""
    return _historical().get(ch) or []


def historical_pz(ch):
    """某字的**历史口径平仄**。返回 `(候选集合, 状态, 条目)`。

    · 状态 `match`/`differ` 由调用方与普通话口径比对得出，此处只回「历史侧」的结果：
      `ok`（唯一）/ `ambiguous`（多候选）/ `missing`（未收录）。
    """
    ents = historical_of(ch)
    if not ents:
        return set(), HIST_MISSING, []
    pzs = {e.get('pz') for e in ents if e.get('pz')}
    if not pzs:
        return set(), HIST_MISSING, ents
    if len(pzs) > 1:
        return pzs, HIST_AMBIGUOUS, ents
    return pzs, 'ok', ents


def dual_view(conn, pid, limit=None):
    """**逐字位双口径对照**（只读；绝不改语料）。

    返回 dict：
      · `pid` / `lines`：逐句逐字位的对照；
      · `summary`：四态计数（match / differ / hist_missing / hist_ambiguous）；
      · `note`：口径声明（**必须**随结果一起展示）。
    每字位字段：`line` / `pos`（该句第几个汉字，0 起）/ `glyph` /
    `mandarin`（评测口径平仄）/ `historical`（历史口径平仄，多候选时用 `/` 连接）/
    `status` / `guangyun`（音韵地位简述，供人工判断）。
    """
    rows = conn.execute('SELECT idx, text, pz FROM lines WHERE pid=? ORDER BY idx',
                        (pid,)).fetchall()
    if not rows:
        return None
    lines_out, summary = [], {MATCH: 0, DIFFER: 0, HIST_MISSING: 0, HIST_AMBIGUOUS: 0}
    n = 0
    for r in rows:
        idx = r['idx'] if isinstance(r, sqlite3.Row) else r[0]
        text = (r['text'] if isinstance(r, sqlite3.Row) else r[1]) or ''
        pz = (r['pz'] if isinstance(r, sqlite3.Row) else r[2]) or ''
        cells = []
        k = 0
        for ch in text:
            if not _HAN_RE.match(ch):
                continue
            m_pz = pz[k] if k < len(pz) else ''
            hp, st, ents = historical_pz(ch)
            if st == HIST_MISSING:
                status, h_view = HIST_MISSING, ''
            elif st == HIST_AMBIGUOUS:
                status, h_view = HIST_AMBIGUOUS, '/'.join(sorted(hp))
            else:
                h_one = next(iter(hp))
                h_view = h_one
                status = MATCH if (m_pz and h_one == m_pz) else DIFFER
            summary[status] += 1
            cells.append({'pos': k, 'glyph': ch, 'mandarin': m_pz,
                          'historical': h_view, 'status': status,
                          'guangyun': '；'.join(
                              (e.get('desc') or '') for e in ents[:2]) if ents else ''})
            k += 1
            n += 1
            if limit and n >= limit:
                break
        lines_out.append({'idx': idx, 'text': text, 'cells': cells})
        if limit and n >= limit:
            break
    return {
        'pid': pid,
        'lines': lines_out,
        'summary': summary,
        'n_positions': n,
        'historical_available': historical_available(),
        'note': ('双口径并列：**评测口径**＝普通话四声折平仄（本系统默认、赛事题库口径）；'
                 '**历史口径**＝《广韵》音韵地位所反映的中古平仄（历史音韵参考，'
                 '**不是清代实际读音**）。两口径**各自成立、互不覆盖**；'
                 '不一致处**如实并列**，本系统**不判定谁对**。'
                 '广韵未收录 / 多候选的字位如实标注，**不用普通话顶替**。'),
    }


def compare(conn, pid):
    """只回对照统计（给摘要用）。"""
    v = dual_view(conn, pid)
    if v is None:
        return None
    s = v['summary']
    total = sum(s.values()) or 1
    return {'pid': pid, 'n_positions': v['n_positions'], 'summary': s,
            'agree_rate': round(100.0 * s[MATCH] / total, 1)}


def main():
    ap = argparse.ArgumentParser(description='声律双口径对照（评测口径 vs 广韵历史口径）')
    ap.add_argument('--db', default=DEFAULT_DB)
    ap.add_argument('--pid', required=True)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    v = dual_view(conn, args.pid, limit=args.limit or None)
    conn.close()
    if v is None:
        print('找不到该篇：%s' % args.pid)
        return 1
    if args.json:
        print(json.dumps(v, ensure_ascii=False, indent=1))
        return 0
    print('【双口径对照】%s' % args.pid)
    print('　　%s' % v['note'])
    print('　　逐字位 %d：一致 %d ｜ 不一致 %d ｜ 广韵未收录 %d ｜ 广韵多候选 %d'
          % (v['n_positions'], v['summary'][MATCH], v['summary'][DIFFER],
             v['summary'][HIST_MISSING], v['summary'][HIST_AMBIGUOUS]))
    for ln in v['lines']:
        marks = []
        for c in ln['cells']:
            if c['status'] == DIFFER:
                marks.append('%s(普%s/古%s)' % (c['glyph'], c['mandarin'] or '—',
                                               c['historical'] or '—'))
        if marks:
            print('　　第 %d 句差异：%s' % (ln['idx'] + 1, '、'.join(marks)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
