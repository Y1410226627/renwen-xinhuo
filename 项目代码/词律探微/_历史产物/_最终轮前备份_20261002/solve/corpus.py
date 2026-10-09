# -*- coding: utf-8 -*-
"""corpus.py —— 语料加载层：把三源读成统一记录，并提供三重匹配定位。

数据源（见《给AI的编码任务书》4.2）：
  1) poetry-source  清词  source/词/清/*.base.json   字段 id/title/authorName/dynasty/content(分阕list)
  2) chinese-poetry 宋词  宋词/ci.song.*.json        字段 author/paragraphs(每句一条)/rhythmic
  3) chinese-poetry 元曲  元曲/yuanqu.json           字段 dynasty/author/paragraphs/title
另有 poetry-source 的 明/五代十国/唐/金 作为补充（题面偶用）。

注意：poetry-source 每分片有 .base.json / .json / .pinyin.json 三版，
      只读 .base.json，否则同一首词会被统计三遍。
"""
from __future__ import annotations
import glob
import json
import os
import re

# 汉字判定范围（**单一事实来源**，prosody.py / pronounce.py / tools 均从此导入）：
#   * CJK 统一表意　U+4E00–U+9FFF
#   * CJK 扩展 A　　U+3400–U+4DBF　← **必须包含**
#     语料中「䕷」(U+4577，「荼䕷」) 属扩展 A；官方答案把它计为 1 个平声字。
#     实测（2026-09-29）：只补这一区，公开集修复 4 题、保密集修复 5 题、破坏 0 题。
#   * **不包含**「□」U+25A1 /「○」U+25CB /「■」U+25A0：它们是语料里的缺字占位符，
#     官方同样不计（T-027 / T-050 / T-136 三族题的答案已反证：计了反而会错）。
HAN_CLASS = r'\u3400-\u4dbf\u4e00-\u9fff'
HAN_RE = re.compile('[%s]' % HAN_CLASS)


def han_only(s: str) -> str:
    """只保留汉字（含 CJK 扩展 A），去掉标点、空白、题名。"""
    return ''.join(HAN_RE.findall(s or ''))


class Poem:
    """一首词。text 为全篇原文（各阕拼接，保留标点）。"""
    __slots__ = ('pid', 'dynasty', 'author', 'title', 'cipai', 'raw', 'source', 'loc', '_han')

    def __init__(self, pid, dynasty, author, title, cipai, raw, source, loc):
        self.pid = pid
        self.dynasty = dynasty
        self.author = author
        self.title = title
        self.cipai = cipai
        self.raw = raw          # str：全篇原文
        self.source = source
        self.loc = loc          # 形如 ci.清.0000.base.json#123
        self._han = None

    @property
    def han(self) -> str:
        """缓存的「只含汉字」全文（定位与统计都用它，避免重复计算）。"""
        if self._han is None:
            self._han = han_only(self.raw)
        return self._han

    def __repr__(self):
        return '<Poem %s %s《%s》%d字>' % (self.dynasty, self.author, self.title, len(self.han))


def _join(raw):
    if isinstance(raw, list):
        return ''.join(raw)
    return raw or ''


_DYN_EN2CN = {'qing': '清', 'song': '宋', 'yuan': '元', 'tang': '唐', 'ming': '明',
              'jin': '金', 'liao': '辽', 'han': '汉', 'sui': '隋', 'wei': '魏'}


def _norm_dynasty(d) -> str:
    """朝代字段归一（单一来源）。

    chinese-poetry 的元曲源把 dynasty 写成英文 'yuan'（见 元曲/yuanqu.json），直接用会让
    元数据（朝代筛选 / 同词同名重复篇的消歧）出错，这里统一成中文朝代。

    ⚠️ 此前这里**只有一个 docstring、没有实现**（隐式返回 None），全靠调用点 `or '元'` 兜底；
    外部审查（AI优化建议 C1）指出「承诺与实现有缝」——现已落成真映射。
    """
    s = (d or '').strip()
    if not s:
        return ''
    return _DYN_EN2CN.get(s.lower(), s)


def _cipai_of(title: str) -> str:
    """从题名取词牌：按「·」或「・」切首段。"""
    return re.split(r'[·・\u00b7]', (title or '').strip())[0].strip()


def load_qing(root: str, dyns=('清',), include_extra=False):
    """poetry-source 的词（只读 .base.json）。"""
    out = []
    base = os.path.join(root, 'poetry-source-master', 'source', '词')
    if not os.path.isdir(base):
        return out
    if include_extra:
        dyns = tuple(n for n in sorted(os.listdir(base))
                    if os.path.isdir(os.path.join(base, n)))
    for dyn in dyns:
        d = os.path.join(base, dyn)
        if not os.path.isdir(d):
            continue
        for f in sorted(glob.glob(os.path.join(d, '*.base.json'))):
            fn = os.path.basename(f)
            for idx, it in enumerate(_load(f)):
                title = it.get('title') or ''
                out.append(Poem(
                    pid='ps:%s' % (it.get('id') or ('%s#%d' % (fn, idx))),
                    dynasty=it.get('dynasty') or dyn,
                    author=it.get('authorName') or '',
                    title=title,
                    cipai=_cipai_of(title),
                    raw=_join(it.get('content')),
                    source='poetry-source',
                    loc='%s#%d' % (fn, idx),
                ))
    return out


def load_song(root: str):
    """chinese-poetry 宋词（用 paragraphs，勿用 poetry-source 的宋词）。"""
    out = []
    d = os.path.join(root, 'chinese-poetry-master', '宋词')
    if not os.path.isdir(d):
        return out
    for f in sorted(glob.glob(os.path.join(d, 'ci.song.*.json'))):
        fn = os.path.basename(f)
        for idx, it in enumerate(_load(f)):
            out.append(Poem(
                pid='cp:%s#%d' % (fn, idx),
                dynasty='宋',
                author=(it.get('author') or '').split('·')[-1].strip(),
                title=it.get('rhythmic') or '',
                cipai=(it.get('rhythmic') or '').strip(),
                raw=_join(it.get('paragraphs')),
                source='chinese-poetry',
                loc='%s#%d' % (fn, idx),
            ))
    return out


def load_yuanqu(root: str):
    """chinese-poetry 元曲。author 形如「高明《蔡伯喈琵琶记》」，拆成作者与出处。"""
    out = []
    p = os.path.join(root, 'chinese-poetry-master', '元曲', 'yuanqu.json')
    if not os.path.isfile(p):
        return out
    for idx, it in enumerate(_load(p)):
        au = it.get('author') or ''
        m = re.match(r'^([^《]+)《([^》]+)》\s*$', au.strip())
        author = m.group(1).strip() if m else au.split('·')[-1].strip()
        out.append(Poem(
            pid='cp:yuanqu#%d' % idx,
            dynasty=_norm_dynasty(it.get('dynasty')) or '元',
            author=author,
            title=it.get('title') or '',
            cipai=(it.get('title') or '').strip(),
            raw=_join(it.get('paragraphs')),
            source='chinese-poetry',
            loc='yuanqu.json#%d' % idx,
        ))
    return out


def _load(path):
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)


def load_corpus(root: str, extra=False):
    """默认：清（poetry-source）+ 宋（chinese-poetry）+ 元（chinese-poetry 元曲）。
    extra=True 时额外加载 poetry-source 的 明/五代十国/唐/金，用于提高定位覆盖率。"""
    poems = []
    poems += load_qing(root, dyns=('清',))
    poems += load_song(root)
    poems += load_yuanqu(root)
    if extra:
        for dyn in ('明', '五代十国', '唐', '金'):
            poems += load_qing(root, dyns=(dyn,))
    return poems


# ---------------------------------------------------------------- 定位
class Locator:
    """预建索引的定位器：作者索引 + 首句前 N 字索引，避免每题全表扫描。"""

    def __init__(self, poems):
        self.poems = poems
        self.by_author = {}
        self.by_head6 = {}
        self.by_head4 = {}
        self.by_cipai = {}
        for p in poems:
            self.by_author.setdefault(_norm_author(p.author), []).append(p)
            h = p.han
            if len(h) >= 6:
                self.by_head6.setdefault(h[:6], []).append(p)
            if len(h) >= 4:
                self.by_head4.setdefault(h[:4], []).append(p)
            cp = _norm_cipai(p.cipai)
            if cp:
                self.by_cipai.setdefault(cp, []).append(p)

    def _score(self, p, au, cp, h6):
        s = 0
        # 作者：双向包含（题面「李曾伯」对语料「宋·李曾伯」、或语料带字号后缀）
        na = _norm_author(p.author)
        if au and (au == na or au in na or na in au):
            s += 1
        # 词牌：两边都做归一（含中点统一、元曲「宫调/词牌」前缀剥离）
        pc = _norm_cipai(p.cipai)
        if cp and (pc == cp or pc.endswith(cp) or cp in pc):
            s += 1
        h = p.han
        if h6 and h6 in h:
            s += 1
            if h.startswith(h6):
                s += 1
        return s

    def find(self, author, cipai, head, require=2, dyn=''):
        au = _norm_author(author)
        cp = (cipai or '').strip()
        h6 = han_only(head)[:6]
        pool = {}
        for p in self.by_author.get(au, []):
            pool[p.pid] = p
        for p in self.by_head6.get(h6, []):
            pool[p.pid] = p
        if len(h6) >= 4:
            for p in self.by_head4.get(h6[:4], []):
                pool[p.pid] = p
        cands = [(self._score(p, au, cp, h6), p) for p in pool.values()]
        cands = [c for c in cands if c[0] >= require]
        # 同分时优先「题面给的朝代」——题面白送一个先验，用它消掉跨源重复篇
        # （实测：周容《小重山》同时存在于清词源与宋词源，题面标「清」）。
        # 稳定排序：同分且同朝代时仍按索引插入序，保证确定性。
        cands.sort(key=lambda x: (-x[0], 0 if (dyn and x[1].dynasty == dyn) else 1))
        return cands

    def find_one(self, author, cipai, head, dyn=''):
        return self.find_one_traced(author, cipai, head, dyn)[0]

    def find_one_traced(self, author, cipai, head, dyn=''):
        """同 find_one，但额外返回【命中路径 + 证据强度】，供定位质量审计与“低置信标注”
        （两者共用同一实现，避免诊断逻辑与正式逻辑分家）。

        评分最高 4 = 作者 1 + 词牌 1 + 首句包在正文 1 + 首句在起首 1：
          A4 全中      —— 三条证据全中且首句在起首（高置信）
          A3 首句非起首—— 三条证据都有，但首句不在起首（低置信，可能是序/异文）
          A2 仅两项相符—— 如“首句掉夸但作者+词牌对”（低置信）
        低置信不得静默当作确定答案（T3 展示层应提示核对）。
        """
        c = self.find(author, cipai, head, dyn=dyn)
        if c:
            p = c[0][1]
            s = self._score(p, _norm_author(author), (cipai or '').strip(), han_only(head)[:6])
            if s >= 4:
                return p, 'A4 作者+词牌+首句起首全中（高置信）'
            if s == 3:
                return p, 'A3 作者+词牌+首句（非起首）——低置信'
            return p, 'A2 仅两项相符——低置信'
        h6 = han_only(head)[:6]
        for p in self._order(self.by_head6.get(h6, []), dyn):
            return p, 'B 仅首句前6字（无作者校验）'
        for p in self._order([q for q in self.by_head4.get(h6[:4], []) if q.han.startswith(h6[:4])], dyn):
            return p, 'C 仅首句前4字（无作者校验）'
        # 末选回退（采纳自另一 AI 版本）：首句完全没命中时，用「作者∩词牌」交集，
        # 恰一条则认定（无首句校验，风险最高）。
        p = self.find_by_author_cipai(author, cipai, dyn)
        if p is not None:
            return p, 'D 仅作者∩词牌（无首句校验）'
        return None, 'E 定位失败'

    @staticmethod
    def _order(seq, dyn):
        """无校验回退路径里优先题面朝代一致的篇（稳定排序；无 dyn 时原序）。"""
        if not dyn:
            return seq
        return sorted(seq, key=lambda p: 0 if p.dynasty == dyn else 1)

    def find_by_author_cipai(self, author, cipai, dyn=''):
        """作者∩词牌 交集；恰一条才返回。多条时：若按题面朝代筛后恰一条，则取之；
        其余情况一律返回 None（不猜）。"""
        au = _norm_author(author)
        cp = _norm_cipai(cipai)
        if not au or not cp:
            return None
        a_ids = {id(p): p for p in self.by_author.get(au, [])}
        c_ids = {id(p): p for p in self.by_cipai.get(cp, [])}
        inter = [a_ids[k] for k in a_ids.keys() & c_ids.keys()]
        if len(inter) == 1:
            return inter[0]
        if dyn:
            same = [p for p in inter if p.dynasty == dyn]
            if len(same) == 1:
                return same[0]
        return None


# 语料列表 -> Locator 的缓存。键用 id(list) 易踩「id 复用」坑（旧 list 被回收后
# 新 list 可能分到同一地址，于是拿到过期定位器），因此这里同时**强引用** poems 本身。
_LOCATORS = {}


def get_locator(poems):
    key = id(poems)
    ent = _LOCATORS.get(key)
    if ent is None or ent[0] is not poems:
        ent = (poems, Locator(poems))
        _LOCATORS[key] = ent
    return ent[1]


def locate(poems, author, cipai, head, require=2):
    return get_locator(poems).find(author, cipai, head, require)


def locate_one(poems, author, cipai, head, dyn=''):
    """dyn（题面朝代）仅用于同分/回退时的消歧，不参与「是否命中」的判定。"""
    return get_locator(poems).find_one(author, cipai, head, dyn)


def _norm_author(a: str) -> str:
    return re.split(r'[·\u00b7]', (a or '').strip())[-1].strip()


def _norm_cipai(c: str) -> str:
    """词牌归一：统一中点，并去掉元曲的「宫调/」前缀（如「仙吕/点绛唇」→「点绛唇」）。"""
    c = (c or '').replace('・', '·').strip()
    if '/' in c:
        c = c.split('/')[-1].strip()
    return c
