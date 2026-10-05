# -*- coding: utf-8 -*-
"""official.py —— 官方题型（C1–C5「甲乙两篇对比」）的**识别 → 作答 → 渲染**。

为什么需要（2026-10-04 主人实测驱动）：本项目有**两条作答链路**，题型与口径完全不同——
  · 问答链（`ask.py` + `retrieve.py`）：面向「问答式」问句（清词里句脚为香的作品有多少篇…）；
  · 解题链（`solver.py` + `prosody.py`）：面向竞赛题库的 **甲乙两篇对比**题
    （同调全篇声律比例差 C1／跨篇分段变幅 C2／跨篇长句仄声密度 C3／跨篇后段排序 C4／景情互证 C5）。
把官方题面贴进问答页时，旧版把它当**检索题**解析：把「甲」的朝代、「乙」的词人、题面套话
统统当成检索条件 → 得到「共命中 0 篇」，与问题毫无关系（实测 V-001-V2C1）。

本模块把官方题型接进作答链：识别 → 定位（复用 `solver` 的宽容题面解析与 Locator 路径）→
调 `prosody` 的 c1..c5 → 按**官方标准答案的措辞**渲染成文本。
语料与引擎**懒加载 + 进程内缓存**（58852 首载入一次约数秒，之后逐题毫秒级）。
"""
from __future__ import annotations
import os
import re
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 语料根目录：环境变量 LVC_CORPUS 优先；否则按本仓库布局（…/数据/语料）相对定位
CORPUS = (os.environ.get('LVC_CORPUS') or os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '数据', '语料')))

# 类别关键词（取自官方题面的措辞；命中数最多者胜，平手按 C1→C5 优先）
_CLS_HINTS = (
    ('C1', ('两篇同用该调', '全文仄声比例', '相差', '个百分点')),
    ('C2', ('前段', '后段', '变化值', '绝对变幅', '前后半部分')),
    ('C3', ('平均句长', '阈值', '长句', '密度')),
    ('C4', ('后段原文', '排序', '差距', '最高与最低')),
    ('C5', ('景物', '感受', '节奏', '互证')),
)

_CTX_LOCK = threading.Lock()
_CTX = {}


def _ctx():
    """懒加载（语料 + 引擎），进程内缓存。返回 (poems, eng)；失败抛异常由调用方兜。"""
    with _CTX_LOCK:
        if 'eng' not in _CTX:
            from corpus import load_corpus
            from pronounce import Pronouncer, default_overrides_path
            from prosody import Engine
            poems = load_corpus(CORPUS)
            if not poems:
                raise RuntimeError('语料载入为 0 首（LVC_CORPUS=%s 路径不对？）' % CORPUS)
            _CTX['poems'] = poems
            _CTX['eng'] = Engine(Pronouncer(default_overrides_path()))
        return _CTX['poems'], _CTX['eng']


_TAG_SPLIT = re.compile(r'([甲乙丙])\s*[：:]')
_TITLE = re.compile(r'《([^》]{1,24})》')
_CMP_WORDS = ('哪一首', '哪一篇', '哪首', '哪篇', '更高', '更低', '较高', '较低', '相比', '对比',
              '两首', '两篇', '相差', '哪个高', '哪个低', '分别给出', '比较')


_PARTICLES = ('把', '将', '和', '与', '跟', '同', '及', '以及', '的', '请', '拿', '看',
              '对', '相比', '比较', '对比', '分别', '两首', '两篇', '这', '那', '是', '在', '了',
              '帮我', '以及', '、', '，', '。', '：', ':')


def _clean_author(s):
    """剥掉「把曾廉」「和石孝友」这类前缀，只留姓名（朝代·作者 的中点留给 Locator 处理）。"""
    s = (s or '').strip('·・、，。：: 　')
    changed = True
    while changed and len(s) > 2:          # 前缀：「把曾廉」「和石孝友」
        changed = False
        for w in _PARTICLES:
            if s.startswith(w) and len(s) > len(w):
                s = s[len(w):]
                changed = True
    while len(s) > 2 and s.endswith(('的', '之', '地', '得', '词', '那首', '这首')):
        s = s[:-1]                          # 后缀：「曾廉的」「石孝友之」
    return s.strip('·・、，。：: 　')


def _free_parts(question):
    """自由措辞的两篇对比题：「曾廉《画堂春·清溪》和石孝友《画堂春》哪一首仄声比例更高？」

    从书名号里抽篇目（词牌 = 题名 `·` 前那一段），作者取紧邻书名号**前面**的汉字串。
    只有「≥2 篇 + 含对比词」才算（否则会误伤普通提问；本机自产 1000 题实测 0 命中的前提就是
    这两条同时成立——它们 0 处书名号）。
    """
    titles = list(_TITLE.finditer(question or ''))
    if len(titles) < 2:
        return {}
    if not any(w in (question or '') for w in _CMP_WORDS):
        return {}
    out = {}
    for i, m in enumerate(titles[:3]):
        title = m.group(1).strip()
        pre = (question or '')[:m.start()]
        ma = re.search(r'([\u4e00-\u9fff·\u00b7]{2,8})\s*$', pre)
        author = _clean_author(ma.group(1) if ma else '')
        cipai = re.split(r'[·\u00b7・/]', title)[0].strip()
        out['甲乙丙'[i]] = {'朝代': '', '作者': author, '题名': title,
                            '词牌': cipai, '首句': ''}
    return out


def _parse_parts(question):
    """题面 → {tag: {朝代,作者,题名,词牌,首句}}。

    三条路，依次放宽：
      ① 解题链的宽容解析（题面按行、`甲：` 起行——官方 jsonl 就是这个形态）；
      ② `甲：/乙：/丙：` 标记切分（用户把两篇粘成一行）；
      ③ 自由措辞：从「作者《词牌·题》」抽篇目（见 `_free_parts`）。
    识别不出第 ① ② 条时**不急着回退**，因为用户往往就是按自己的话问的。
    """
    import solver
    parts = solver.parse_question(question)
    got = [t for t in parts if parts[t].get('词牌') and (parts[t].get('首句') or parts[t].get('作者'))]
    if len(got) >= 2:
        return parts
    marks = list(_TAG_SPLIT.finditer(question or ''))
    if len(marks) >= 2:
        merged = {}
        for i, m in enumerate(marks):
            j = marks[i + 1].start() if i + 1 < len(marks) else len(question)
            seg = '%s：%s' % (m.group(1), (question[m.end():j]).strip())
            one = solver.parse_question(seg)
            for t, v in one.items():
                if v.get('词牌') and (v.get('首句') or v.get('作者')):
                    merged[t] = v
        if len(merged) >= 2:
            return merged
    free = _free_parts(question)
    if len(free) >= 2:
        return free
    return parts


def looks_official(question):
    """是否**两篇（及以上）具体作品对比题**——官方 C1–C5 与用户自由措辞都算。

    判据：至少两篇，且每篇能给出「词牌 + （首句或作者）」。
    认两篇而不是"含『甲：』就算"——避免把用户随手打的「甲：…」误判成对比题。
    """
    try:
        parts = _parse_parts(question)
    except Exception:
        return False
    got = [t for t in ('甲', '乙', '丙') if t in parts
           and parts[t].get('词牌') and (parts[t].get('首句') or parts[t].get('作者'))]
    return len(got) >= 2


def classify(question):
    """按官方题面措辞判类别（C1–C5）；判不出返回 None。"""
    best, best_n = None, 0
    for cls, kws in _CLS_HINTS:
        n = sum(1 for w in kws if w in (question or ''))
        if n > best_n:
            best, best_n = cls, n
    return best if best_n >= 2 else None       # 至少两条线索才算认出来


def solve(question, cls=None):
    """官方题型作答。返回 dict：ok / cls / ans / located / parts / errors / paths。

    为什么不用 `solver.solve_one` 一把梭：它内部的题面解析是**按行**的窄解析，用户把
    甲/乙 粘成一行时就只认出一篇（实测）。这里用 `_parse_parts`（窄解析 + 单行兜底），
    但**定位与计算全部复用解题链的函数**（`locate_one_safe` / `Engine.c1..c5`），
    所以数值与交付答案同源、不会分叉。
    """
    import solver
    cls = cls or classify(question) or 'GEN'      # 判不出官方类别 → 走「通用两篇对比」
    parts = _parse_parts(question)
    poems, eng = _ctx()
    from corpus import get_locator
    loc = get_locator(poems)
    located, errors, paths = {}, [], {}
    for tag in ('甲', '乙', '丙'):
        spec = parts.get(tag)
        if not spec or not spec.get('词牌'):
            continue
        poem = None
        if spec.get('首句'):
            poem = solver.locate_one_safe(poems, spec)
            if poem is not None:
                try:
                    _, path = solver.locate_one_traced_safe(poems, spec)
                    paths[tag] = path
                    if not str(path).startswith('A4'):
                        errors.append('%s 定位低置信：[%s] %s《%s》'
                                      % (tag, path, spec['作者'], spec['题名']))
                except Exception:
                    paths[tag] = '（路径未记录）'
            else:
                errors.append('%s 定位失败：%s《%s》首句 %s'
                              % (tag, spec['作者'], spec['题名'], spec['首句'][:12]))
        else:
            # 没给首句：按「作者 ∩ 词牌」唯一定位（Locator 恰一条才返回，不猜）；
            # 多条时用题名（`·` 之后那段）消歧；仍不唯一 → 如实要首句。
            poem = loc.find_by_author_cipai(spec.get('作者', ''), spec['词牌'],
                                            spec.get('朝代', ''))
            if poem is None:
                cands = loc.find(spec.get('作者', ''), spec['词牌'], '', require=2,
                                 dyn=spec.get('朝代', '')) or []
                tail = spec['题名'].split('·')[-1] if '·' in spec['题名'] else ''
                if tail:
                    hit = [c[1] for c in cands if tail in (c[1].title or '')]
                    if len(hit) == 1:
                        poem = hit[0]
                if poem is None:
                    errors.append('%s 无法唯一定位（%s《%s》）：该作者此词牌%s，请补首句'
                                  % (tag, spec.get('作者') or '（未给作者）', spec['题名'],
                                     '有 %d 篇' % len(cands) if cands else '在语料中未找到'))
                    continue
            paths[tag] = 'B1 作者+词牌（+题名）唯一定位'
        located[tag] = poem
    ans = {}
    if cls in ('C1', 'C2', 'C3', 'C5') and '甲' in located and '乙' in located:
        ans = getattr(eng, cls.lower())(located['甲'].raw, located['乙'].raw)
    elif cls == 'C4' and len(located) >= 2:
        ans = eng.c4({k: v.raw for k, v in located.items()})
    elif cls == 'GEN' and len(located) >= 2:
        for tag, p_ in ((t, located[t]) for t in ('甲', '乙') if t in located):
            r_ = eng.ratio(p_.raw)
            lg_ = eng.longest(p_.raw)
            ans[tag] = {'句数': r_['句数'], '最长句序': lg_['最长句序'],
                        '最长句字数': lg_['最长句字数'], '平': r_['平'], '仄': r_['仄'],
                        '仄声比例': r_['仄声比例']}
        if '甲' in ans and '乙' in ans:
            d_ = round(abs(ans['甲']['仄声比例'] - ans['乙']['仄声比例']), 1)
            ans['比例差'] = d_
            ans['较高'] = ('甲' if ans['甲']['仄声比例'] > ans['乙']['仄声比例'] else
                          ('乙' if ans['乙']['仄声比例'] > ans['甲']['仄声比例'] else '两篇'))
    else:
        errors.append('数据不足，无法计算（缺少 %s）' % cls)
    return {'ok': not errors and bool(ans), 'cls': cls, 'ans': ans,
            'located': {k: v.loc for k, v in located.items()},
            'parts': parts, 'errors': errors, 'paths': paths}


def _seq(seqs):
    return '、'.join(str(x) for x in seqs)


def _signed(v):
    return ('%+.1f' % v)


def render(res):
    """把引擎答案按**官方标准答案的措辞**渲染成文本（措辞照抄题库，不自创词形）。"""
    a, b = res['ans'].get('甲'), res['ans'].get('乙')
    cls = res['cls']
    if cls == 'C1':
        return ('甲共%d句，最长为第%s句、各%d字，全文平%d、仄%d，仄声比例%.1f%%；'
                '乙共%d句，最长为第%s句、各%d字，全文平%d、仄%d，仄声比例%.1f%%。'
                '两篇全文仄声比例相差%.1f个百分点，%s较高。'
                '这些数值只说明当前文本的形式与声调配置，不能单独判定作者意图或作品优劣。'
                % (a['句数'], _seq(a['最长句序']), a['最长句字数'], a['平'], a['仄'], a['仄声比例'],
                   b['句数'], _seq(b['最长句序']), b['最长句字数'], b['平'], b['仄'], b['仄声比例'],
                   res['ans']['比例差'], res['ans']['较高']))
    if cls == 'C2':
        return ('甲仄声比例由%.1f%%变为%.1f%%，变化%s个百分点，绝对变幅%.1f个百分点；'
                '乙仄声比例由%.1f%%变为%.1f%%，变化%s个百分点，绝对变幅%.1f个百分点。'
                '两篇变幅相差%.1f个百分点，%s较大。'
                '变幅只能说明分段节奏配置的变化，不能直接推定情感强度或作者意图。'
                % (a['前段比例'], a['后段比例'], _signed(a['变化']), a['绝对变幅'],
                   b['前段比例'], b['后段比例'], _signed(b['变化']), b['绝对变幅'],
                   res['ans']['变幅差'], res['ans']['较大']))
    if cls == 'C3':
        return ('甲阈值%d字，入选第%s句，合计平%d、仄%d，仄声比例%.1f%%；'
                '乙阈值%d字，入选第%s句，合计平%d、仄%d，仄声比例%.1f%%。'
                '两篇长句区段仄声密度相差%.1f个百分点，%s较高。'
                '该比较仅限题定长句区段，不能代替文学价值判断。'
                % (a['阈值'], _seq(a['入选句序']), a['平'], a['仄'], a['比例'],
                   b['阈值'], _seq(b['入选句序']), b['平'], b['仄'], b['比例'],
                   res['ans']['密度差'], res['ans']['较高']))
    if cls == 'C4':
        order = res['ans']['排序']
        return ('甲后段可引“%s”，仄声比例%.1f%%；乙后段可引“%s”，仄声比例%.1f%%。'
                '排序为%s，最高与最低相差%.1f个百分点。'
                '该排序只反映题定后段的声调数量，不能直接推断作者意图、跨体裁高下或文学价值。'
                % (a['后段引文'], a['后段比例'], b['后段引文'], b['后段比例'],
                   '＞'.join(order), res['ans']['比例差']))
    if cls == 'C5':
        return ('甲前段景物线索：%s；后段主观感受线索：%s；仄声比例变化%s个百分点，节奏转向为%s。\n'
                '乙前段景物线索：%s；后段主观感受线索：%s；仄声比例变化%s个百分点，节奏转向为%s。\n'
                '解释边界：%s\n'
                '语义验证状态：未验证；景物/感受归类及互证解释仅作候选，不作为语义金标准。'
                % (a['前段引文'], a['后段引文'], _signed(a['变化']), a['转向'],
                   b['前段引文'], b['后段引文'], _signed(b['变化']), b['转向'],
                   res['ans'].get('边界声明', '')))
    if cls == 'GEN':
        segs = []
        for tag in ('甲', '乙'):
            d = res['ans'].get(tag)
            if not d:
                continue
            segs.append('%s：%d句，最长句第%s句（%d字），全文平%d、仄%d，仄声比例%.1f%%'
                        % (tag, d['句数'], _seq(d['最长句序']), d['最长句字数'],
                           d['平'], d['仄'], d['仄声比例']))
        txt = '；'.join(segs) + '。'
        if '比例差' in res['ans']:
            txt += ('两篇全文仄声比例相差%.1f个百分点，%s较高。'
                    % (res['ans']['比例差'], res['ans']['较高']))
        txt += ('本回答列出的是形式层面可逐项核对的指标（句数／最长句／平仄计数／仄声比例）；'
                '若要按「前后段变幅、长句仄声密度、后段排序、景情互证」等口径比较，请指明按哪一项。')
        return txt
    return '（未实现的类别：%s）' % cls


def main():
    import argparse
    ap = argparse.ArgumentParser(description='官方题型（C1–C5）作答：题面 → 答案文本')
    ap.add_argument('--question', required=True)
    ap.add_argument('--cls', default=None)
    a = ap.parse_args()
    r = solve(a.question, a.cls)
    print('类别：%s' % r.get('cls'))
    print('定位：%s' % r.get('located'))
    if r.get('errors'):
        print('errors：%s' % r['errors'])
    print(render(r) if r.get('ok') else '（未能作答）')


if __name__ == '__main__':
    main()
