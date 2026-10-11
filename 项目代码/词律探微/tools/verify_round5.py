# -*- coding: utf-8 -*-
"""verify_round5.py —— 第五轮审查 P0-4/P1-1/P1-2 的验收对拍（临时验收器，跑完可留档）。"""
import io
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'solve'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, errors='ignore')

import queryplan as QP
import retrieve

OK = True


def chk(name, got, want):
    global OK
    ok = (got == want)
    OK = OK and ok
    print('%s %-52s 得到 %r ／ 期望 %r' % ('✓' if ok else '✗', name, got, want))


def _tree(op, val, field='han_len'):
    return {'field': field, 'op': op, 'value': val}


# ── P0-4：数值比较符逐短语绑定 ──────────────────────────────────────────
def _norm(question, leaves):
    """leaves: [(op, value)] → and 树；返回归一后的 op 列表。"""
    tree = {'and': [_tree(op, v) for op, v in leaves]}
    QP.normalize_ops(tree, question)
    return [c['op'] for c in tree['and']]


chk('P0-4① 字数至少 50 字 → >=',
    _norm('找出字数至少 50 字的词', [('>', 50)]), ['>='])
chk('P0-4② 字数少于 100 字 → <（不归一）',
    _norm('找出字数少于 100 字的词', [('<', 100)]), ['<'])
chk('P0-4③ 字数严格大于 50 字 → >（保留）',
    _norm('找字数严格大于 50 字的词', [('>', 50)]), ['>'])
chk('P0-4④ 至少 50 且少于 100 → >=50 AND <100',
    _norm('找出字数至少 50 字、同时少于 100 字的词', [('>', 50), ('<', 100)]),
    ['>=', '<'])
chk('P0-4⑤ 不少于 50 / 低于 60% 互不影响',
    _norm('字数不少于 50、仄声比例低于 60% 的词', [('>', 50), ('<', 60)], ),
    ['>=', '<'])
chk('P0-4⑥ 超过 45（基准 NL001 口径）→ >=',
    _norm('仄声比例超过 45 个百分点的词', [('>', 45)]), ['>='])
chk('P0-4⑦ 大于 50（无含界词）→ > 保留',
    _norm('字数大于 50 字的词', [('>', 50)]), ['>'])

# ── P1-1：空值确定语义 ────────────────────────────────────────────────
conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', 'data', 'corpus.db'))
sql, args = retrieve._leaf_sql({'field': 'cipai', 'op': 'in', 'value': []})
chk('P1-1① cipai=[] 正向 → 恒假', (sql, args), ('1=0', []))
sql, args = retrieve._leaf_sql({'field': 'cipai', 'op': 'not_in', 'value': []})
chk('P1-1② cipai=[] 否定 → 恒真', (sql, args), ('1=1', []))
sql, args = retrieve._leaf_sql({'field': 'title', 'op': 'contains', 'value': ''})
chk('P1-1③ title="" → 恒假', (sql, args), ('1=0', []))
sql, args = retrieve._leaf_sql({'field': 'lines.text', 'op': 'contains', 'value': '  '})
chk('P1-1④ lines.text 空白串 → 恒假', (sql, args), ('1=0', []))
okp, probs = QP.validate(dict(QP.empty_plan(), filters={'field': 'cipai', 'op': '=', 'value': []}),
                         conn)
chk('P1-1⑤ validate 对空集合显式报 problem', okp, False)

# ── P1-2：title 算子语义 ──────────────────────────────────────────────
sql, args = retrieve._leaf_sql({'field': 'title', 'op': '=', 'value': '清明'})
chk('P1-2① title = → 精确等值', (sql, args), ('p.title IN (?)', ['清明']))
sql, args = retrieve._leaf_sql({'field': 'title', 'op': 'contains', 'value': '清明'})
chk('P1-2② title contains → 子串', (sql[:11], args), ('(p.title LI', ['%清明%']))
# 真值对拍：= 与 contains 的命中集必须不同（库里确有含「清明」子串的非全等题名）
_hit_eq = set(r[0] for r in conn.execute('SELECT pid FROM poems WHERE title = ?', ('清明',)))
_hit_ct = set(r[0] for r in conn.execute("SELECT pid FROM poems WHERE title LIKE '%清明%'"))
sql, args = retrieve._leaf_sql({'field': 'title', 'op': '=', 'value': '清明'})
_eng = set(r[0] for r in conn.execute('SELECT pid FROM poems p WHERE %s' % sql, args))
chk('P1-2③ title= 引擎与独立 SQL 逐篇一致', _eng, _hit_eq)
chk('P1-2④ title= 比 contains 更严（命中集⊆且≠）',
    (_eng <= _hit_ct, _eng != _hit_ct), (True, True))
sql, args = retrieve._leaf_sql({'field': 'title', 'op': '=', 'value': '清明'})
chk('P1-2⑤ title = 多值 → IN 集合',
    retrieve._leaf_sql({'field': 'title', 'op': '=', 'value': ['清明', '冬至']})[0],
    'p.title IN (?,?)')
conn.close()
print('----')
print('验收：%s' % ('全部通过' if OK else '存在失败'))
sys.exit(0 if OK else 1)
