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

    _CACHE.update({'forms': forms, 'by_tune': by_tune, 'alias2canon': alias2canon,
                   'registry': raw_reg})
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
    """体的精简摘要（列表展示用；不含逐句细节）。

    ★ 2026-10-10（词谱 UI/逻辑修复）：新增 `form_key` —— **体的唯一标识**。
      `form` 只是「该书内的第几体」，**钦定词谱体 1 与龙榆生词谱体 1 会撞号**；
      前端若只用 `form` 当 `:key` 与"当前选中"判据，就会出现
      「两个按钮同时高亮 / Vue 重复 key 报警 / 点 A 却选中 B」。故给出跨谱书唯一的 key。
    """
    return {'tune': f['tune'], 'authority': f['authority'], 'form': f['form'],
            'form_key': '%s|%d' % (f['authority'] or '?', f['form']), 'seq': f['seq'],
            'n_lines': f['n_lines'], 'n_chars': f['n_chars'], 'header': f['header'],
            'source_url': f['source_url']}


def form_detail(f):
    """体的完整信息（含逐句规则与例词）。"""
    d = form_brief(f)
    d['rules'] = [dict(x) for x in f['rules']]
    d['sentences'] = list(f['sentences'])
    return d


def coverage():
    """**谱库覆盖范围**（P2-4）：逐词牌列体数，并对照上游（竞品转写源）标称体数。

    用途：把「我们收了多少 / 上游有多少 / 边界在哪」一次说清，界面上明写
    **N 词牌 / M 体 · 参照来源：搜韵公开转写（未核原书）**，
    避免用户把本谱库当成「全量词谱」。

    返回体字段：
      · n_tunes / n_forms            —— 我方覆盖的词牌数 / 体数；
      · n_upstream_forms             —— 上游（钦定词谱+龙榆生词谱）侧标称体数合计；
      · authorities                  —— 我方按谱书分账的体数；
      · boundary_notes               —— 覆盖边界如实说明（含来源红线）；
      · tunes                        —— 逐词牌：别名 / 我方体数 / 上游标称体数 / 核验数 / 来源。
    """
    d = _load()
    reg = d.get('registry') or []
    by_tune = d['by_tune']

    auth_count = {}
    for f in d['forms']:
        a = f['authority'] or '（未标谱书）'
        auth_count[a] = auth_count.get(a, 0) + 1
    authorities = [{'name': k, 'n_forms': auth_count[k]}
                   for k in sorted(auth_count, key=lambda x: (-auth_count[x], x))]

    tunes = []
    n_upstream = 0
    for t in reg:
        canon = t.get('canonical_tune_name') or ''
        if not canon:
            continue
        aa = t.get('authority_availability') or {}
        raw_by_auth, raw = {}, 0
        for name, info in aa.items():
            rf = int((info or {}).get('raw_forms') or 0)
            raw_by_auth[name] = rf
            raw += rf
        n_upstream += raw
        fs = by_tune.get(canon) or []
        fs_auth = {}
        for f in fs:
            a = f['authority'] or '（未标谱书）'
            fs_auth[a] = fs_auth.get(a, 0) + 1
        tunes.append({
            'tune': canon,
            'aliases': sorted([a for a, cs in d['alias2canon'].items()
                               if canon in cs and a != canon]),
            'n_forms': len(fs),
            'n_forms_by_authority': fs_auth,
            'upstream_raw_forms': raw,
            'upstream_raw_by_authority': raw_by_auth,
            'verified_form_count': t.get('verified_form_count'),
            'available_normalized_form_count': t.get('available_normalized_form_count'),
            'source_url': t.get('source_url') or '',
        })
    tunes.sort(key=lambda x: (-x['n_forms'], x['tune']))

    n_forms = len(d['forms'])
    notes = [
        '谱库仅覆盖上游取数范围内的 %d 个词牌、%d 个体式；未收录词牌如实返回「未收录」'
        '与可用清单，绝不猜测。' % (len(tunes), n_forms),
        '参照来源为搜韵公开转写（未核原书）：体式与平仄规则未对照纸本原书，仅供研究参考。',
        '对照上游（钦定词谱 / 龙榆生词谱）侧标称可选体数合计 %d；我方已规范化 %d 体。'
        % (n_upstream, n_forms),
    ]
    return {'n_tunes': len(tunes), 'n_forms': n_forms, 'n_upstream_forms': n_upstream,
            'authorities': authorities, 'boundary_notes': notes,
            'tunes': tunes, 'source_note': SOURCE_NOTE}


#: 句末标记 → 展示标签（★ 2026-10-10 修复：前端原先**把所有 ending 都显示成「韵」**，
#:   于是「句」「叠」「换平韵」被误报成押韵）。
#: ⚠ 这里**不做解释性翻译**——谱书写什么就显示什么（`读` 就是 `读`，不擅自写成「句内停顿」），
#:   「不把转写当定本」这条红线同样适用于逐字展示。
ENDING_LABEL = {}          # 预留：将来若上游统一了缩写，只在这里加映射，不改前端


def ending_label(ending):
    e = (ending or '').strip()
    if not e:
        return ''
    return ENDING_LABEL.get(e, e)


def compare(poem, form):
    """**三行对照**核心：`poem`（作品） vs `form`（谱式体）。

    `poem` 形如 `{'pid','author','title','cipai','lines':[{'idx','text','pz'},…]}`——
    其中 `pz` **必须来自 corpus.db 的 `lines` 表**（全站同一份预计算）。
    返回逐句逐字的 `rows` 与 `summary`（对/错/任意三分账 + 多出/缺失句如实列出）。

    ★ 2026-10-10（词谱逻辑修复）——**对齐必须可解释**：
      · 逐字对齐只取 `min(汉字数, pz 串长, 规则串长)` 三者；
      · 三者不等时**不再静默错位**：该行的 `align_warn` 会写明差在哪，
        并计入 `summary.n_unaligned_lines`（前端据此在行内给出提示）。
        （改前 → 只用 `min(汉字数, 规则长度)`，而 `pz[k]` 未参与下界判断：
          若 `pz` 与汉字数不等（含占位符/异体字），后面每个字都会**整体错位一格**，
          却没有任何提示——把「对齐失败」渲染成了「大量不符」。）
    """
    L = list(poem.get('lines') or [])
    R = form['rules']
    S = form['sentences']
    n = max(len(L), len(R))
    rows = []
    n_cell = n_match = n_mismatch = n_any = 0
    n_unaligned = 0
    for i in range(n):
        text = pz = None
        chars = []
        if i < len(L):
            text = (L[i].get('text') or '')
            pz = (L[i].get('pz') or '')
            chars = _HAN_RE.findall(text)
        tones = R[i]['tones'] if i < len(R) else ''
        ending = R[i]['ending'] if i < len(R) else None
        cells = []
        m = min(len(chars), len(pz or ''), len(tones))
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
        # 对齐诊断：汉字数 / pz 长度 / 规则长度 三者不一致时如实说明（不静默错位）
        _warn = ''
        if i < len(L) and (len(chars) != len(pz)):
            _warn = ('作品汉字 %d 个，但平仄串 %d 位——两者不等，逐字对齐只取前 %d 位'
                     % (len(chars), len(pz), m))
        if len(chars) and len(tones) and len(chars) != len(tones):
            _warn = ((_warn + '；') if _warn else '') + \
                    '作品 %d 字 vs 谱书 %d 字（字数不等）' % (len(chars), len(tones))
        if _warn:
            n_unaligned += 1
        rows.append({
            'line': i,
            'poem_text': text, 'poem_pz': pz,
            'rule_tones': tones or None,
            'ending': ending,
            'ending_label': ending_label(ending),
            'example': (S[i] if i < len(S) else None),
            'cells': cells,
            'n_chars_poem': len(chars),
            'n_chars_pz': len(pz or ''),
            'n_chars_rule': len(tones),
            'align_warn': _warn,
        })
    return {
        'rows': rows,
        'summary': {
            'n_cells': n_cell, 'n_match': n_match, 'n_mismatch': n_mismatch, 'n_any': n_any,
            'n_lines_poem': len(L), 'n_lines_rule': len(R),
            'n_unaligned_lines': n_unaligned,
            'extra_lines': [i for i in range(len(L)) if i >= len(R)],
            'missing_lines': [i for i in range(len(R)) if i >= len(L)],
        },
    }


def _match_form(fs, form):
    """把请求里的 `form` 解析成**唯一一体**。返回 `(form 或 None, 说明)`。

    ★ 2026-10-10（词谱逻辑修复）：接受三种写法，且**不再静默挑第一个**——
      · `form_key`（`钦定词谱|1`，前端首选，跨谱书唯一）；
      · 纯数字：若**多本谱书撞号**（钦定 1 + 龙榆生 1）则视为歧义，返回 None 并说明；
      · `#<seq>` 或纯 seq 兜底（内部定位用）。
    """
    if form is None or form == '':
        return None, '未指定体'
    s = str(form).strip()
    for f in fs:
        if s == '%s|%d' % (f['authority'] or '?', f['form']):
            return f, '按 form_key 指定'
    if s.startswith('#'):
        s = s[1:]
    if s.isdigit():
        hits = [f for f in fs if f['form'] == int(s)]
        if len(hits) == 1:
            return hits[0], '按体号指定（该体号在本词牌内唯一）'
        if len(hits) > 1:
            return None, ('体号 %s 在**多本谱书**里同时存在（%s）——请改用 form_key 指定，'
                          '以免张冠李戴' % (s, '、'.join('%s体%d' % (h['authority'], h['form'])
                                                        for h in hits)))
        hits2 = [f for f in fs if f['seq'] == int(s)]
        if len(hits2) == 1:
            return hits2[0], '按全局序号指定'
        return None, '体号 %s 不在本词牌内' % s
    return None, '无法识别的体标识：%r' % (form,)


def compare_poem(pid, poem, tune=None, form=None):
    """对**一篇作品**出词谱对照（自动匹配词牌与体，也可显式指定 `tune` / `form`）。

    `poem` 形态（与 `/api/parse` / 建库 lines 同形）：
      `{'pid':…, 'author':…, 'title':…, 'cipai':…, 'lines': [{'idx','text','pz'…},…]}`
    抽出来是为了**让个人作品也能走词谱对照**（P2-1）：语料库走 `compare_pid`（从 poems/lines
    取行组 poem），个人作品走 `research.analyze_work`（组同一形态的 poem），两条路汇入这一处，
    对照逻辑**只有一份**。返回体一律带 `source_note`（红线）。词牌未收录 / 有歧义时
    如实返回 `status` 与候选。
    """
    lines = poem.get('lines') or []
    n_chars = sum(len(_HAN_RE.findall(x.get('text') or '')) for x in lines)
    cipai = poem.get('cipai') or ''
    name = (tune or cipai).strip()
    canon, cands = resolve_tune(name)
    if canon is None:
        return {'status': 'no_tune', 'pid': pid, 'cipai': cipai, 'asked': name,
                'candidates': cands, 'source_note': SOURCE_NOTE,
                'available_tunes': [t['tune'] for t in list_tunes()],
                'note': ('词牌「%s」不在谱库（当前收录 %d 个词牌）'
                         % (name, len(list_tunes()))) if not cands else
                        ('词牌「%s」有多个相近候选，请显式指定：%s'
                         % (name, '、'.join(cands)))}
    # ★ 2026-10-10 修复：体标识解析**失败也要如实说**，不再「静默回落自动匹配」
    #   （旧版 `int(form)` 遇到非数字会直接抛异常 → 500；且撞号时静默取第一个）。
    f, why = _match_form(forms_of(canon), form)
    form_note = ''
    if f is None:
        _auto, _awhy = pick_form(canon, len(lines), n_chars)
        if str(form or '').strip() != '':
            form_note = '指定的体未能采用（%s）——本次按自动匹配给出：%s' % (why, _awhy)
        f, why = _auto, _awhy
    res = compare({'pid': pid, 'author': poem.get('author'), 'title': poem.get('title'),
                   'cipai': cipai, 'lines': lines}, f)
    res.update({'status': 'ok', 'pid': pid, 'cipai': cipai, 'tune': canon,
                'form': form_brief(f), 'form_why': why, 'form_note': form_note,
                'source_note': SOURCE_NOTE})
    return res


def compare_pid(conn, pid, tune=None, form=None):
    """按**语料库**作品 pid 出对照：从 poems/lines 取行组 poem，委托 `compare_poem`。

    返回体一律带 `source_note`（红线）。词牌未收录 / 有歧义时如实返回 `status` 与候选。
    """
    r = conn.execute('SELECT pid,author,cipai,title FROM poems WHERE pid=?',
                     (pid,)).fetchone()
    if r is None:
        return None
    lines = [dict(x) for x in conn.execute(
        'SELECT idx,text,pz FROM lines WHERE pid=? ORDER BY idx', (pid,))]
    poem = {'pid': pid, 'author': r['author'], 'title': r['title'],
            'cipai': r['cipai'], 'lines': lines}
    return compare_poem(pid, poem, tune=tune, form=form)
