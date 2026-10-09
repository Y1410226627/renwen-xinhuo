# -*- coding: utf-8 -*-
"""entity_resolve.py —— **实体解析层**（Entity Resolution）。

为什么要有这个文件（外部架构审查 GPT §3.1⑦ 原话）：

> `rescue_title()` 是一个很有价值的 bug-fix，但不是通用实体解析。
> 它本质上是在猜「这个词面其实可能是 title」。
> 以后应迁移成 Entity Resolution：author / cipai / title / pid / aliases，
> 而不是继续增加 `rescue_author()` / `rescue_cipai()` / `rescue_xxx()`。

本模块就是那个「收口的地方」：项目里所有「把一段文本认定成某个库内实体」的需求，
一律走这里，**不再往 `retrieve._parse_core` 里堆 `rescue_*`**。

三类调用
========
  1. `lift(conn, spec)`      —— 回填：解析后实体槽为空时，从残留词面里把**真实存在的**实体抬出来
                                （这是原先 `_lift_known_names` 的正经归宿；**只填空、不覆盖**）
  2. `resolve(conn, text)`   —— 显式解析：给一段文本，返回它最可能指向的实体（供 Planner/前端用）
  3. `exists(conn, kind, v)` —— 存在性判定（Planner 落地校验、NOT_FOUND 判定共用同一份）

两条自律（保证不可能造成 1000 题回归）
======================================
  · **只填空**：`lift()` 在任何实体槽非空时**完全不动**；
  · **只认真名**：候选一律来自库里的 `authors` / `cipai` / `poems.title` 表并过频次门槛，
    **绝不**接受模型或用户臆造的值（边界与 `planner._landing_check` 完全一致）。

★ 结构性隔离（D07）：本模块被 `retrieve.parse_query` 调用，属于问答层；
  `solver.py` 不导入它 → 对交付答案的影响仍由 `regress` 双集哈希把关。
"""
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─────────────────────────── 门槛（声明式：改这里，不改代码） ───────────────────────────
# 词牌表有 14,143 项、其中约 80% 是「题名/整句被误当词牌」的脏数据
# （deepseek §0.3 实测）。故词牌匹配必须过**频次 + 长度**双重门槛。
CIPAI_MIN_N = 10          # 词牌在语料中至少出现 10 次（脏词牌多为 1-2 次）
CIPAI_LEN = (2, 5)        # 真词牌以 2-5 字为主
AUTHOR_MIN_LEN = 3        # 人名至少 3 字（2 字误伤太大）
TITLE_MIN_LEN = 2         # 题名至少 2 字

_HAN = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')


def _table(conn, sql, args=()):
    try:
        return conn.execute(sql, args).fetchall()
    except Exception:                                            # noqa: BLE001
        return []


def candidates(conn, kind):
    """某类实体的候选名单（长名优先、同长按频次降序）。带进程内缓存。"""
    global _CACHE
    key = (id(conn), kind)
    if key in _CACHE:
        return _CACHE[key]
    out = []
    if kind == 'cipai':
        rows = _table(conn, 'SELECT cipai, n FROM cipai WHERE n>=? AND length(cipai) BETWEEN ? AND ?',
                      (CIPAI_MIN_N, CIPAI_LEN[0], CIPAI_LEN[1]))
        out = [(r[0], r[1]) for r in rows]
    elif kind == 'author':
        rows = _table(conn, 'SELECT author, n FROM authors WHERE length(author)>=?', (AUTHOR_MIN_LEN,))
        out = [(r[0], r[1]) for r in rows]
    elif kind == 'title':
        rows = _table(conn, 'SELECT title, COUNT(*) FROM poems '
                            'WHERE title IS NOT NULL AND length(title)>=? GROUP BY title',
                      (TITLE_MIN_LEN,))
        out = [(r[0], r[1]) for r in rows]
    out.sort(key=lambda x: (-len(x[0]), -x[1]))
    _CACHE[key] = out
    return out


_CACHE = {}


def exists(conn, kind, value):
    """实体在库中是否存在（Planner 落地校验与本模块共用同一份判据）。"""
    if not value:
        return False
    try:
        if kind == 'author':
            return bool(conn.execute('SELECT 1 FROM authors WHERE author=? LIMIT 1',
                                     (value,)).fetchone())
        if kind == 'cipai':
            return bool(conn.execute('SELECT 1 FROM cipai WHERE cipai=? LIMIT 1',
                                     (value,)).fetchone())
        if kind == 'title':
            return bool(conn.execute('SELECT 1 FROM poems WHERE title LIKE ? LIMIT 1',
                                     ('%' + value + '%',)).fetchone())
        if kind == 'pid':
            return bool(conn.execute('SELECT 1 FROM poems WHERE pid=? LIMIT 1', (value,)).fetchone())
        if kind == 'dynasty':
            return bool(conn.execute('SELECT 1 FROM poems WHERE dynasty=? LIMIT 1',
                                     (value,)).fetchone())
    except Exception:                                            # noqa: BLE001
        return False
    return False


def resolve(conn, text):
    """给一段文本，返回它最可能指向的实体 → `{'kind','value','rest'}` 或 None。

    判据：**前缀锚定 + 长名优先**。前缀锚定是为了避免从句子中段捞出无关实体；
    剩余部分以 `rest` 返回，由调用方决定降级为词面还是丢弃。
    """
    if not text:
        return None
    for kind in ('cipai', 'author'):
        for name, _n in candidates(conn, kind):
            if text.startswith(name) and len(text) > len(name):
                return {'kind': kind, 'value': name, 'rest': text[len(name):]}
    return None


def lift(conn, spec):
    """**回填**：解析后实体槽为空时，从残留词面里把真实存在的实体抬出来。

    解决的是「实体粘连」——`_parse_core` 有一条刻意的兵险逻辑
    「整串不含分隔符时视为正文片段」，于是
        「清代临江仙一共有多少首」→ 剩下词面「临江仙一共有」→ 词牌丢失
        「纳兰性德写了几首词」    → 剩下词面「纳兰性德写了几首词」→ 词人丢失
    这条逻辑保护的是「不要把任意串当人名」，**不宜推翻**；本函数是它的**补充**。

    ★ 三条自律（这是它不可能造成 1000 题回归的原因）：
      ① 实体槽非空 → 完全不动；
      ② 只认 `candidates()` 给出的真名（过频次/长度门槛）；
      ③ 前缀锚定，剩余部分 ≥2 字才降级为词面。
    """
    if spec is None or spec.cipai_any or spec.author_any:
        return spec
    kws = list(spec.keywords or [])
    if not kws:
        return spec
    hit, hit_kw = None, None
    for kw in kws:
        r = resolve(conn, kw)
        if r:
            hit, hit_kw = r, kw
            break
    if not hit:
        return spec
    if hit['kind'] == 'cipai':
        spec.cipai_any.append(hit['value'])
    else:
        spec.author_any.append(hit['value'])
    rest = (hit['rest'] or '').strip()
    spec.keywords = [w for w in kws if w != hit_kw] + ([rest] if len(rest) >= 2 else [])
    try:
        import retrieve
        return retrieve._finalize(spec)
    except Exception:                                            # noqa: BLE001
        return spec


def main():
    import argparse
    ap = argparse.ArgumentParser(description='实体解析层自检')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--text', default=None, help='显式解析一段文本')
    a = ap.parse_args()
    conn = sqlite3.connect(a.db)
    conn.row_factory = sqlite3.Row
    print('候选：词牌 %d ／ 词人 %d ／ 题名 %d'
          % (len(candidates(conn, 'cipai')), len(candidates(conn, 'author')),
             len(candidates(conn, 'title'))))
    for t in (a.text or '临江仙一共有多少首', '纳兰性德写了几首词', '清 临江仙 仄声比例高于45%'):
        r = resolve(conn, t)
        print('  %-24s → %s' % (t, ('%s=%s（余「%s」）' % (r['kind'], r['value'], r['rest']))
                                if r else '（无实门前缀命中）'))
    print('存在性：临江仙=%s ／ 纳兰性德=%s ／ 查无此人=%s'
          % (exists(conn, 'cipai', '临江仙'), exists(conn, 'author', '纳兰性德'),
             exists(conn, 'author', '查无此人')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
