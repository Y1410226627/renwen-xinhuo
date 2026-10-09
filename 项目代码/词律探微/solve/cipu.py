# -*- coding: utf-8 -*-
"""cipu.py —— 词谱对照（功能 9）：**作品原字 / 规范 / 谱书例词** 三行对照。

数据（`data/cipu/`，随仓分发，来源与许可见 `THIRD_PARTY.md`）：
  · `normalized-rules.json` —— **144 体**：每体含例词句数组（`normalized_sentences`）、
    逐句平仄规则（`normalized_rules`：`tones` 只含 `中/平/仄`，`ending` 为句尾标记）、来源定位；
  · `tune-registry.json` —— **20 词牌**注册表：canonical 名、别名、体数。

三条红线（交接提示词功能 9）：
  1. **参照来源：搜韵公开转写（未核原书）**——返回体一律带 `SOURCE_NOTE`，
     **严禁**写成「钦定词谱原书核验」；
  2. 原始 `ci_sep` 用全角空格把多句压在同一个数组元素里，**不能直接当句数组**——
     本模块只读上游**已按正确口径拆好**的 `normalized-rules.json`，
     并在 `web/test_cipu.py` 里用「拿原始 `ci_sep` 当句数组必错」的反向用例钉死这一点；
  3. `中` 字位是「平仄皆可」——对照时记 `any`，**不参与**对/错统计（如实分账）。

对照逻辑（`compare`）：
  · 逐句对齐到 `min(作品句数, 谱式句数)`；多出的句在 `extra_lines` / `missing_lines` 里如实列出；
  · 句内逐字对齐：作品的平仄来自 `corpus.db` 的 `lines.pz`（**与全站同一份预计算**，
    绝不在这里另算一遍——避免「同一篇两个平仄」）；规则串的字位是 `中/平/仄`；
  · 判词：`rule='中'` → `any`；否则 `match`（相等）/ `mismatch`（不等）。
"""
import json
import os
import re

from corpus import HAN_CLASS as _HAN_CLASS      # 汉字判定单一来源

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CIPU_DIR = os.path.join(_ROOT, 'data', 'cipu')
_HAN_RE = re.compile('[%s]' % _HAN_CLASS)

#: 界面与返回体必须携带的来源声明（红线；改了要连 `web/test_cipu.py` 的断言一起改）。
SOURCE_NOTE = ('参照来源：搜韵公开转写（未核原书）· 上游 hulbji/couyun（MIT License）'
               '@1744e87f850c2205bc231bfdd858256036c0e4db')

_CACHE = {}


def _norm_sentence(s):
    """例词句的汉字数（全角空格不是汉字——上游核验文档第 29 行专门钉过这一点）。"""
    return len(_HAN_RE.findall(s or ''))


def _load():
    """懒加载并整形两份数据（模块级缓存；数据文件缺失时抛可读异常）。"""
    if _CACHE:
        return _CACHE
    p_rules = os.path.join(_CIPU_DIR, 'normalized-rules.json')
    p_reg = os.path.join(_CIPU_DIR, 'tune-registry.json')
    if not (os.path.isfile(p_rules) and os.path.isfile(p_reg)):
        raise RuntimeError('词谱数据缺失：请确认 data/cipu/ 下存在 normalized-rules.json 与'
                           ' tune-registry.json（见 THIRD_PARTY.md）')
    with open(p_rules, encoding='utf-8') as f:
        raw_rules = json.load(f)
    with open(p_reg, encoding='utf-8') as f:
        raw_reg = json.load(f)

    forms = []
    for i, r in enumerate(raw_rules):
        sents = r.get('normalized_sentences') or []
        rules = r.get('normalized_rules') or []
        tones_all = [x.get('tones') or '' for x in rules]
        forms.append({
            'seq': i,
            'tune': r.get('canonical_tune_name') or '',
            'authority': r.get('authority') or '',
            'form': int(r.get('form_number') or 1),
            'header': r.get('source_header') or '',
            'source_url': r.get('source_url') or '',
            'sentences': sents,
            'rules': [{'tones': t, 'ending': (rules[k].get('ending') or '')}
                      for k, t in enumerate(tones_all)],
            'n_lines': len(rules),
            'n_chars': sum(len(t) for t in tones_all),
        })
    by_tune = {}
    for f in forms:
        by_tune.setdefault(f['tune'], []).append(f)
    for k in by_tune:
        by_tune[k].sort(key=lambda f: (f['authority'] != '钦定词谱', f['form'], f['seq']))

    alias2canon = {}
    for t in raw_reg:
        canon = t.get('canonical_tune_name') or ''
        if not canon:
            continue
        for a in ([canon] + list(t.get('verified_aliases') or [])):
            alias2canon.setdefault(a, [])
            if canon not in alias2canon[a]:
                alias2canon[a].append(canon)

    _CACHE.update({'forms': forms, 'by_tune': by_tune, 'alias2canon': alias2canon})
    return _CACHE


def list_tunes():
    """谱库覆盖的词牌一览：`[{'tune','aliases','n_forms'}]`（按体数降序）。"""
    d = _load()
    out = []
    for tune, fs in d['by_tune'].items():
        aliases = sorted([a for a, cs in d['alias2canon'].items() if tune in cs and a != tune])
        out.append({'tune': tune, 'aliases': aliases, 'n_forms': len(fs)})
    out.sort(key=lambda x: (-x['n_forms'], x['tune']))
    return out


def resolve_tune(name):
    """作品词牌名 → 谱库 canonical 名。返回 `(canon 或 None, candidates)`。

    匹配顺序：① 精确（canonical/别名）；② 双向前缀（差 ≤ 2 字，如「浪淘沙」↔「浪淘沙令」）。
    多个候选（如「木兰花」同时近「木兰花令」「玉楼春」）时 **canon=None**、候选如实列出——
    「不许猜」纪律在词牌层的落点。
    """
    d = _load()
    name = (name or '').strip()
    if not name:
        return None, []
    if name in d['alias2canon']:
        cs = d['alias2canon'][name]
        if len(cs) == 1:
            return cs[0], cs
        return None, cs
    cand = []
    for canon in d['by_tune']:
        if (name.startswith(canon) and len(name) - len(canon) <= 2) or \
           (canon.startswith(name) and len(canon) - len(name) <= 2):
            cand.append(canon)
    if len(cand) == 1:
        return cand[0], cand
    return None, cand


def forms_of(tune):
    """某词牌的全部体（钦定词谱在前、form 升序）。"""
    return list(_load()['by_tune'].get(tune, []))


def pick_form(tune, n_lines=None, n_chars=None):
    """按「句数 + 字数」替作品选最贴近的体；优先完全匹配，其次句数相同、字数最近。

    返回 (form 或 None, why：选择理由人话)。找不到该词牌时 (None, '谱库未收录')。
    """
    fs = forms_of(tune)
    if not fs:
        return None, '谱库未收录该词牌'
    if n_lines is None:
        return fs[0], '未提供句数，取该词牌首体'
    exact = [f for f in fs if f['n_lines'] == n_lines and (n_chars is None
                                                           or f['n_chars'] == n_chars)]
    if exact:
        return exact[0], '句数与字数都与作品一致'
    same_lines = [f for f in fs if f['n_lines'] == n_lines]
    if same_lines:
        if n_chars is None:
            return same_lines[0], '句数与作品一致（字数未比）'
        f = min(same_lines, key=lambda x: (abs(x['n_chars'] - n_chars), x['form']))
        return f, '句数一致、字数最接近（差 %d 字）' % abs(f['n_chars'] - n_chars)
    f = min(fs, key=lambda x: (abs(x['n_lines'] - n_lines),
                               abs(x['n_chars'] - (n_chars or 0)), x['form']))
    return f, '无句数相同的体，取最接近的一体（差 %d 句）' % abs(f['n_lines'] - n_lines)


def form_brief(f):
    """体的精简摘要（列表展示用；不含逐句细节）。"""
    return {'tune': f['tune'], 'authority': f['authority'], 'form': f['form'],
            'n_lines': f['n_lines'], 'n_chars': f['n_chars'], 'header': f['header'],
            'source_url': f['source_url']}


def form_detail(f):
    """体的完整信息（含逐句规则与例词）。"""
    d = form_brief(f)
    d['rules'] = [dict(x) for x in f['rules']]
    d['sentences'] = list(f['sentences'])
    return d


def compare(poem, form):
    """**三行对照**核心：`poem`（作品） vs `form`（谱式体）。

    `poem` 形如 `{'pid','author','title','cipai','lines':[{'idx','text','pz'},…]}`——
    其中 `pz` **必须来自 corpus.db 的 `lines` 表**（全站同一份预计算）。
    返回逐句逐字的 `rows` 与 `summary`（对/错/任意三分账 + 多出/缺失句如实列出）。
    """
    L = list(poem.get('lines') or [])
    R = form['rules']
    S = form['sentences']
    n = max(len(L), len(R))
    rows = []
    n_cell = n_match = n_mismatch = n_any = 0
    for i in range(n):
        text = pz = None
        chars = []
        if i < len(L):
            text = (L[i].get('text') or '')
            pz = (L[i].get('pz') or '')
            chars = _HAN_RE.findall(text)
        tones = R[i]['tones'] if i < len(R) else ''
        cells = []
        m = min(len(chars), len(tones))
        for k in range(m):
            rule = tones[k]
            pzc = pz[k] if k < len(pz) else ''
            if rule == '中':
                verdict = 'any'
                n_any += 1
            elif pzc == rule:
                verdict = 'match'
                n_match += 1
            else:
                verdict = 'mismatch'
                n_mismatch += 1
            n_cell += 1
            cells.append({'pos': k, 'char': chars[k], 'pz': pzc, 'rule': rule,
                          'verdict': verdict})
        rows.append({
            'line': i,
            'poem_text': text, 'poem_pz': pz,
            'rule_tones': tones or None,
            'ending': (R[i]['ending'] if i < len(R) else None),
            'example': (S[i] if i < len(S) else None),
            'cells': cells,
            'n_chars_poem': len(chars),
            'n_chars_rule': len(tones),
        })
    return {
        'rows': rows,
        'summary': {
            'n_cells': n_cell, 'n_match': n_match, 'n_mismatch': n_mismatch, 'n_any': n_any,
            'n_lines_poem': len(L), 'n_lines_rule': len(R),
            'extra_lines': [i for i in range(len(L)) if i >= len(R)],
            'missing_lines': [i for i in range(len(R)) if i >= len(L)],
        },
    }


def compare_pid(conn, pid, tune=None, form=None):
    """按作品 pid 出对照：自动匹配词牌与体（也可显式指定 `tune` / `form`）。

    返回体一律带 `source_note`（红线）。词牌未收录 / 有歧义时如实返回 `status` 与候选。
    """
    r = conn.execute('SELECT pid,author,cipai,title,raw FROM poems WHERE pid=?',
                     (pid,)).fetchone()
    if r is None:
        return None
    lines = [dict(x) for x in conn.execute(
        'SELECT idx,text,pz FROM lines WHERE pid=? ORDER BY idx', (pid,))]
    n_chars = sum(len(_HAN_RE.findall(x.get('text') or '')) for x in lines)
    name = (tune or r['cipai'] or '').strip()
    canon, cands = resolve_tune(name)
    if canon is None:
        return {'status': 'no_tune', 'pid': pid, 'cipai': r['cipai'], 'asked': name,
                'candidates': cands, 'source_note': SOURCE_NOTE,
                'available_tunes': [t['tune'] for t in list_tunes()],
                'note': ('词牌「%s」不在谱库（当前收录 %d 个词牌）'
                         % (name, len(list_tunes()))) if not cands else
                        ('词牌「%s」有多个相近候选，请显式指定：%s'
                         % (name, '、'.join(cands)))}
    if form is not None:
        fs = [f for f in forms_of(canon) if f['form'] == int(form) or f['seq'] == int(form)]
        f, why = (fs[0], '按指定体') if fs else pick_form(canon, len(lines), n_chars)
    else:
        f, why = pick_form(canon, len(lines), n_chars)
    res = compare({'pid': pid, 'author': r['author'], 'title': r['title'],
                   'cipai': r['cipai'],
                   'lines': lines}, f)
    res.update({'status': 'ok', 'pid': pid, 'cipai': r['cipai'], 'tune': canon,
                'form': form_brief(f), 'form_why': why, 'source_note': SOURCE_NOTE})
    return res
