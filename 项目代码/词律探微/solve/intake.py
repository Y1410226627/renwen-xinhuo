# -*- coding: utf-8 -*-
"""intake.py —— 录入输入体检（功能 11）：**只读**，不写任何库。

对一条「待录入作品」（题名 / 词牌 / 正文）做体检并返回问题清单，供录入预览用。
问题分三级：`error`（不入库就不对）/ `warn`（大概率是笔误）/ `info`（提示性信息）。

口径（与全站一致，不另起一套）：
  · **题名不得当正文**——与 `retrieve.rescue_title()` 同口径（历史 bug：输入题名
    「蝶恋花·清明同诸子集原白斋中」被当**词正文**检索 → 答非所问）；
  · **句读**——句末点按全站口径 `。？！`；句数与 `corpus.db` 的 `lines` 表、
    词谱的「句」同构（实测清词《长相思》8 句 ↔ 钦定词谱 8 句）；
  · **词牌体式**——复用 `cipu.pick_form()`（谱库收录 20 词牌 144 体；未收录则该检查
    如实跳过，**不装作查过**）；
  · **不误伤**：只查「题名与正文的关系」——正文里的「相思/落花/东风/明月」这类
    常见词**不做任何拦截**（它们本来就该出现在正文里）。
"""
import re

from corpus import HAN_CLASS as _HAN_CLASS      # 汉字判定单一来源

_HAN_RE = re.compile('[%s]' % _HAN_CLASS)
_SENT_SPLIT = re.compile(r'[。？！]')            # 全站句末点口径：。？！
_TITLE_SEP = re.compile(r'[·・.]')                # 「词牌·题名」写法


def split_sentences(content):
    """按句末点（。？！）切句；去掉空白段。返回句列表（保留原文，不含切点）。"""
    return [s.strip() for s in _SENT_SPLIT.split(content or '') if s.strip()]


def check(title, content, cipai=''):
    """体检。返回 `{'ok', 'issues', 'stats', 'tune_check'}`（只读，无副作用）。"""
    title = (title or '').strip()
    content = (content or '').strip()
    cipai = (cipai or '').strip()
    issues = []

    def issue(level, code, message):
        issues.append({'level': level, 'code': code, 'message': message})

    # ① 必填
    if not title:
        issue('error', 'TITLE_REQUIRED', '题名必填（缺题名的作品无法被稳定定位与引用）')
    if not content:
        issue('error', 'CONTENT_REQUIRED', '正文必填')

    sents = split_sentences(content)
    n_chars = len(_HAN_RE.findall(content))

    # ② 题名被当成正文（历史 bug 同口径）
    if title and content:
        t_probe = _TITLE_SEP.split(title)[-1].strip() if _TITLE_SEP.search(title) else title
        if t_probe and t_probe in content:
            first_sent = sents[0] if sents else content
            if t_probe in first_sent:
                issue('warn', 'TITLE_IN_BODY',
                      '题名「%s」出现在正文开头——疑似把题名当正文录入（与历史 bug 同口径）'
                      % t_probe)
            else:
                issue('info', 'TITLE_IN_BODY_MID',
                      '题名「%s」也出现在正文中段（若正文确实化用了题名，可忽略）' % t_probe)

    # ③ 句读
    if content:
        if not _SENT_SPLIT.search(content):
            issue('warn', 'NO_SENT_PUNCT',
                  '正文没有任何句末点（。？！）——句读缺失会直接影响断句与声律统计')
        long_sents = [s for s in sents if len(_HAN_RE.findall(s)) > 30]
        if long_sents:
            issue('warn', 'LONG_SENT',
                  '存在超长句（%d 字，如「%s…」）——请核对是否漏了句末点'
                  % (len(_HAN_RE.findall(long_sents[0])), long_sents[0][:15]))
        if title and sents and sents[0] == title:
            issue('warn', 'FIRST_SENT_IS_TITLE', '正文第一句就是题名——首句疑似被题名占据')

    # ④ 词牌体式匹配（谱库覆盖时；未收录 / 有歧义如实说明，不装作查过）
    tune_check = None
    if cipai and content:
        try:
            import cipu
            canon, cands = cipu.resolve_tune(cipai)
            if canon is None and not cands:
                issue('info', 'TUNE_NOT_IN_CIPU',
                      '词牌「%s」不在词谱库（当前收录 %d 个词牌），体式匹配检查跳过'
                      % (cipai, len(cipu.list_tunes())))
            elif canon is None:
                issue('info', 'TUNE_AMBIGUOUS',
                      '词牌「%s」有多个相近候选：%s——请确指后再查体式' % (cipai, '、'.join(cands)))
            else:
                f, why = cipu.pick_form(canon, len(sents) or None, n_chars)
                if f is None:
                    issue('info', 'TUNE_NO_FORM',
                          '词牌「%s」暂无可对照的体式' % canon)
                else:
                    d_chars = n_chars - f['n_chars']
                    d_lines = len(sents) - f['n_lines']
                    tune_check = {
                        'tune': canon, 'authority': f['authority'], 'form': f['form'],
                        'form_chars': f['n_chars'], 'form_lines': f['n_lines'],
                        'draft_chars': n_chars, 'draft_lines': len(sents),
                        'why': why,
                    }
                    if d_chars == 0 and d_lines == 0:
                        issue('info', 'TUNE_MATCH',
                              '与谱式一致：%s·格%d（%d 句 %d 字）'
                              % (canon, f['form'], f['n_lines'], f['n_chars']))
                    elif abs(d_chars) >= 5:
                        issue('warn', 'TUNE_CHARS_FAR',
                              '字数与最接近的谱式体相差 %+d 字（本稿 %d 字 / %s·格%d %d 字）'
                              '——请核对词牌或正文是否缺漏'
                              % (d_chars, n_chars, canon, f['form'], f['n_chars']))
                    else:
                        issue('info', 'TUNE_NEAR',
                              '与最接近的谱式体相差 %+d 字（本稿 %d 字 / %s·格%d %d 字），'
                              '属正常差异区间' % (d_chars, n_chars, canon, f['form'],
                                                  f['n_chars']))
        except Exception as e:                                 # noqa: BLE001
            issue('info', 'CIPU_UNAVAILABLE', '词谱库不可用，体式匹配检查跳过（%r）' % e)

    return {
        'ok': not any(x['level'] == 'error' for x in issues),
        'issues': issues,
        'stats': {'n_chars': n_chars, 'n_sents': len(sents)},
        'tune_check': tune_check,
    }
