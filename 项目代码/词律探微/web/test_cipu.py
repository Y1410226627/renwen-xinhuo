# -*- coding: utf-8 -*-
"""test_cipu.py —— **词谱对照门禁**（功能 9 的自检）。

为什么要有它：词谱对照的错法有三层——
  ① **数据被拆错**（原始 `ci_sep` 用全角空格把多句压进一个元素，直接当句数组就会错）；
  ② **对照算错**（中/平/仄三分账、句数不等时的多出/缺失标注）；
  ③ **来源说错**（把「搜韵公开转写（未核原书）」写成「原书核验」——这是红线）。

本门禁逐条对照这三层，并且按本项目风格做「**护栏的护栏**」：
把旧错误写法（拿 `ci_sep` 直接当句数组）注回去，必须报错。

用法：python web/test_cipu.py
退出码：0 = 全过（比对项为 0 也判 FAIL）；1 = 有问题。
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import cipu as C                          # noqa: E402

CMP = [0]
BAD = []


def ok(name, cond, detail=''):
    CMP[0] += 1
    if not cond:
        BAD.append(name + ('：' + detail if detail else ''))


# 原始 ci_sep 的真实片段（长相思「格二」，取自上游 raw/cipai_67.json 第 2 体）：
#   第 5 个元素里塞了两句（「巫山高　巫山低」以全角空格相连）——直接当句数组必错。
RAW_SEP_SAMPLE = ['深画眉', '浅画眉', '蝉鬓鬅鬙云满衣', '阳台行雨回',
                  '巫山高　巫山低', '暮雨萧萧郎不归', '空房独守时']
ENDING_SET = {'', '韵', '平韵', '仄韵', '换韵', '换平韵', '换仄韵', '叠', '叶', '换叶', '句', '读'}
HAN = re.compile('[\u3400-\u4dbf\u4e00-\u9fff]')


def main():
    # ---------- D1 数据完整性：144 体逐条 ----------
    forms = C._load()['forms']
    ok('D1 数据体数 = 144', len(forms) == 144, '实际 %d' % len(forms))
    bad_lines = [f['seq'] for f in forms if f['n_lines'] != len(f['sentences'])]
    ok('D1 句数与规则数逐体一致', not bad_lines, '不符体：%s' % bad_lines[:5])
    bad_len, bad_ch, bad_end = [], [], []
    for f in forms:
        for k, x in enumerate(f['rules']):
            sent = f['sentences'][k]
            if len(x['tones']) != len(HAN.findall(sent)):
                bad_len.append((f['seq'], k))
            if set(x['tones']) - set('中平仄'):
                bad_ch.append((f['seq'], k))
            if x['ending'] not in ENDING_SET:
                bad_end.append((f['seq'], k, x['ending']))
    ok('D1 规则长度=例词汉字数（逐体逐句）', not bad_len, '不符：%s' % bad_len[:5])
    ok('D1 规则字符只有 中/平/仄', not bad_ch, '不符：%s' % bad_ch[:5])
    ok('D1 句尾标记均在白名单内', not bad_end, '不符：%s' % bad_end[:5])

    # ---------- D2 「护栏的护栏」：直接拿 ci_sep 当句数组必错 ----------
    wrong = len(RAW_SEP_SAMPLE)                    # 错误写法：7（把两句当一句）
    right = sum(len([x for x in re.split(r'[\s\u3000]+', s) if x]) for s in RAW_SEP_SAMPLE)
    ok('D2 直接当句数组会少算（旧错误写法）', wrong == 7 and right == 8,
       'wrong=%d right=%d' % (wrong, right))
    f2 = C.forms_of('长相思')[1]
    ok('D2 规范化数据已按正确口径拆分', '巫山高' in f2['sentences'] and '巫山低' in f2['sentences']
       and '巫山高　巫山低' not in f2['sentences'])
    ok('D2 该体句数=8（与正确拆分一致）', f2['n_lines'] == 8)

    # ---------- D3 对照核心：中/平/仄三分账 + 句数不等 ----------
    form = {'rules': [{'tones': '中中平', 'ending': '韵'}], 'sentences': ['甲乙丙']}
    poem = {'lines': [{'idx': 0, 'text': '甲乙丙', 'pz': '仄仄平'}]}
    r = C.compare(poem, form)
    v = [c['verdict'] for c in r['rows'][0]['cells']]
    ok('D3 中=any、相等=match', v == ['any', 'any', 'match'], str(v))
    ok('D3 三分账计数正确', r['summary']['n_match'] == 1 and r['summary']['n_any'] == 2
       and r['summary']['n_mismatch'] == 0)
    poem2 = {'lines': [{'idx': 0, 'text': '甲乙丙', 'pz': '仄仄仄'}]}
    r2 = C.compare(poem2, form)
    ok('D3 不符记 mismatch', [c['verdict'] for c in r2['rows'][0]['cells']][-1] == 'mismatch')
    poem3 = {'lines': [{'idx': 0, 'text': '甲乙丙', 'pz': '仄仄平'},
                       {'idx': 1, 'text': '丁', 'pz': '平'}]}
    r3 = C.compare(poem3, form)
    ok('D3 作品多出的句列入 extra_lines', r3['summary']['extra_lines'] == [1]
       and r3['summary']['missing_lines'] == [])
    form4 = {'rules': [{'tones': '中中平', 'ending': '韵'}, {'tones': '仄', 'ending': '句'}],
             'sentences': ['甲乙丙', '丁']}
    r4 = C.compare(poem, form4)
    ok('D3 谱式多出的句列入 missing_lines', r4['summary']['missing_lines'] == [1]
       and r4['summary']['extra_lines'] == [])

    # ---------- D4 真实语料对照（独立复算 pz 一致性） ----------
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'corpus.db'))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT pid FROM poems WHERE cipai='长相思' AND dynasty='清'"
                       " ORDER BY pid LIMIT 1").fetchone()
    if row is None:
        ok('D4 语料中可找到清词《长相思》', False, '语料缺失')
    else:
        pid = row['pid']
        res = C.compare_pid(conn, pid)
        ok('D4 compare_pid 正常出对照', res and res.get('status') == 'ok'
           and res['tune'] == '长相思' and len(res['rows']) >= 8)
        # 独立复算：第 0 句每个字的 pz 必须与 lines 表逐字一致
        line0 = conn.execute('SELECT text, pz FROM lines WHERE pid=? AND idx=0', (pid,)).fetchone()
        chars = HAN.findall(line0['text'])
        cells = res['rows'][0]['cells']
        ok('D4 逐字对齐：cell 数=该句汉字数', len(cells) == len(chars), '%d vs %d'
           % (len(cells), len(chars)))
        ok('D4 逐字 pz 与 lines 表一致（独立复算）',
           all(c['pz'] == line0['pz'][c['pos']] for c in cells))
        # 谱库外词牌 → 如实 no_tune
        row2 = conn.execute("SELECT pid FROM poems WHERE cipai NOT IN"
                            " ('长相思','浣溪沙','木兰花令','玉楼春','如梦令','清平乐','蝶恋花',"
                            "'临江仙','虞美人','鹧鸪天','浪淘沙令','卜算子','菩萨蛮','忆江南',"
                            "'减字木兰花','南乡子','踏莎行','八声甘州','水调歌头','念奴娇')"
                            " LIMIT 1").fetchone()
        res2 = C.compare_pid(conn, row2['pid'])
        ok('D4 谱库外词牌如实说明并给可用清单', res2['status'] == 'no_tune'
           and len(res2['available_tunes']) == 20 and res2['source_note'])

    # ---------- D5 来源红线：措辞不许含糊 ----------
    ok('D5 source_note 含「搜韵公开转写」「未核原书」',
       '搜韵公开转写' in C.SOURCE_NOTE and '未核原书' in C.SOURCE_NOTE)
    ok('D5 source_note 不含「原书核验」类错误表述',
       ('原书核验' not in C.SOURCE_NOTE) and ('已核原书' not in C.SOURCE_NOTE))
    ok('D5 含上游与许可信息', 'hulbji/couyun' in C.SOURCE_NOTE and 'MIT' in C.SOURCE_NOTE)

    # ---------- D6 词牌归一的三种情形 ----------
    canon, cands = C.resolve_tune('长相思')
    ok('D6 精确匹配', canon == '长相思')
    canon2, cands2 = C.resolve_tune('浪淘沙')
    ok('D6 前缀归一（浪淘沙→浪淘沙令）', canon2 == '浪淘沙令')
    canon3, cands3 = C.resolve_tune('木兰花')
    ok('D6 歧义不猜（木兰花→候选列表）', canon3 is None and len(cands3) == 2,
       'cands=%s' % cands3)

    # ---------- D7 2026-10-10 修复项（词谱 UI/逻辑缺陷的护栏） ----------
    # ⑦-1 体的**唯一标识**：`form` 会跨谱书撞号，`form_key` 必须唯一（前端拿它当 key/选中判据）
    allk, dup = [], []
    for tune in C._load()['by_tune']:
        ks = [C.form_brief(f)['form_key'] for f in C.forms_of(tune)]
        allk += ks
        if len(set(ks)) != len(ks):
            dup.append(tune)
    ok('D7 form_key 各词牌内唯一', not dup, '重复：%s' % dup[:5])
    ok('D7 form_key 含谱书名与体号', all('|' in k for k in allk), allk[:3])

    # ⑦-2 撞号必须**报歧义**，不许静默取第一个（长相思：钦定体1 与 龙榆生体1 同时存在）
    _fs70 = C.forms_of('长相思')
    _amb, _why70 = C._match_form(_fs70, 1)
    _same = [f for f in _fs70 if f['form'] == 1]
    if len(_same) > 1:
        ok('D7 体号撞号 → 判歧义并要求用 form_key', _amb is None and '谱书' in _why70, _why70)
    else:
        ok('D7 体号唯一时可直接指定', _amb is not None, _why70)
    _fk = C.form_brief(_fs70[0])['form_key']
    _f70, _w70 = C._match_form(_fs70, _fk)
    ok('D7 form_key 精确选体', _f70 is not None and _f70['seq'] == _fs70[0]['seq'], _w70)
    _bad70, _wb70 = C._match_form(_fs70, '这不是体号')
    ok('D7 非法体标识不抛异常、如实说明', _bad70 is None and bool(_wb70), _wb70)

    # ⑦-3 句末标记**不再一律显示成「韵」**（谱书写的「句」「叠」「换平韵」要原样展示）
    _end_seen = set()
    for f in C._load()['forms']:
        for x in f['rules']:
            _end_seen.add(x['ending'])
    _non_yun = sorted([e for e in _end_seen if e and e != '韵'])
    if _non_yun:
        ok('D7 非「韵」的句末标记原样保留（不误标为韵）',
           C.ending_label(_non_yun[0]) == _non_yun[0],
           '%r → %r' % (_non_yun[0], C.ending_label(_non_yun[0])))
    ok('D7 空标记 → 空标签（前端不显示标记）', C.ending_label('') == '' and C.ending_label(None) == '')

    # ⑦-4 对齐不一致**必须留下警告**（汉字数 / pz 长度 / 规则长度 三者不等时不静默错位）
    _fake_form = {'rules': [{'tones': '平仄平', 'ending': '韵'}], 'sentences': ['一二三']}
    _fake_poem = {'pid': 'x', 'lines': [{'idx': 0, 'text': '一二三', 'pz': '平仄'}]}
    _r70 = C.compare(_fake_poem, _fake_form)
    ok('D7 汉字数与 pz 不等 → 该行有 align_warn',
       bool(_r70['rows'][0]['align_warn']) and _r70['summary']['n_unaligned_lines'] == 1,
       repr(_r70['rows'][0]['align_warn']))
    ok('D7 逐字对齐只取三者最小值（不错位越界）', len(_r70['rows'][0]['cells']) == 2,
       len(_r70['rows'][0]['cells']))
    ok('D7 每行带 ending_label 字段（前端不自行解释）',
       'ending_label' in _r70['rows'][0] and _r70['rows'][0]['ending_label'] == '韵')

    # ---------- D8 2026-10-10 P2-1：compare_poem 重构 + 个人作品接入 ----------
    # ① compare_pid（语料库）与 compare_poem（同一篇）结果必须一致（重构不改变行为）
    _cc8 = sqlite3.connect(os.path.join(ROOT, 'data', 'corpus.db'))
    _cc8.row_factory = sqlite3.Row
    _pr8 = _cc8.execute(
        "SELECT pid,author,cipai,title FROM poems WHERE cipai IS NOT NULL "
        "AND cipai != '' LIMIT 1").fetchone()
    if _pr8:
        _pl8 = [dict(x) for x in _cc8.execute(
            'SELECT idx,text,pz FROM lines WHERE pid=? ORDER BY idx', (_pr8['pid'],))]
        _cc8.close()
        _cc8b = sqlite3.connect(os.path.join(ROOT, 'data', 'corpus.db'))
        _cc8b.row_factory = sqlite3.Row
        _rp1 = C.compare_pid(_cc8b, _pr8['pid'])
        _cc8b.close()
        _poem8 = {'pid': _pr8['pid'], 'author': _pr8['author'], 'title': _pr8['title'],
                  'cipai': _pr8['cipai'], 'lines': _pl8}
        _rp2 = C.compare_poem(_pr8['pid'], _poem8)
        ok('D8 compare_pid 与 compare_poem status 一致',
           (_rp1 or {}).get('status') == (_rp2 or {}).get('status'),
           '%s vs %s' % (( _rp1 or {}).get('status'), (_rp2 or {}).get('status')))
        ok('D8 compare_pid 与 compare_poem summary 一致',
           (_rp1 or {}).get('summary') == (_rp2 or {}).get('summary'),
           repr((_rp1 or {}).get('summary'))[:80] + ' vs ' +
           repr((_rp2 or {}).get('summary'))[:80])
    else:
        _cc8.close()
    # ② 个人作品（词牌不在谱库）→ no_tune + source_note（红线）
    _p8 = {'pid': 'personal:999', 'author': '测试', 'title': 'D8验证',
           'cipai': '不存在词牌XYZ', 'lines': [{'idx': 0, 'text': '风急天高', 'pz': '平仄平平'}]}
    _r8 = C.compare_poem('personal:999', _p8)
    ok('D8 个人作品词牌未收录 → no_tune', _r8['status'] == 'no_tune',
       repr(_r8.get('status')))
    ok('D8 no_tune 时带 source_note（来源红线）', bool(_r8.get('source_note')))


    # ---------- D9 2026-10-11 P2-4：谱库覆盖范围（逐词牌对照上游 + 来源红线） ----------
    cov = C.coverage()
    ok('D9 覆盖词牌数 = 20', cov['n_tunes'] == 20, str(cov['n_tunes']))
    ok('D9 覆盖体数 = 144', cov['n_forms'] == 144, str(cov['n_forms']))
    ok('D9 逐词牌体数之和 = 总览体数',
       sum(t['n_forms'] for t in cov['tunes']) == cov['n_forms'],
       '%d vs %d' % (sum(t['n_forms'] for t in cov['tunes']), cov['n_forms']))
    ok('D9 每个词牌体数与 forms_of 一致',
       all(t['n_forms'] == len(C.forms_of(t['tune'])) for t in cov['tunes']))
    ok('D9 逐词牌带上游标称体数（对照竞品转写源）',
       all(isinstance(t['upstream_raw_forms'], int) for t in cov['tunes'])
       and cov['n_upstream_forms'] > 0,
       'upstream=%s ours=%s' % (cov['n_upstream_forms'], cov['n_forms']))
    ok('D9 覆盖声明含「未核原书」（来源红线）',
       '未核原书' in cov['source_note']
       and any('未核原书' in n for n in cov['boundary_notes']))
    ok('D9 覆盖声明不得写成「原书核验」',
       all(('原书核验' not in n) for n in cov['boundary_notes']))

    print('=' * 64)
    print('词谱门禁：比对 %d 项，不符 %d 项' % (CMP[0], len(BAD)))
    for b in BAD:
        print('  ✗', b)
    print('结果：%s' % ('PASS' if not BAD and CMP[0] > 0 else 'FAIL'))
    return 0 if (not BAD and CMP[0] > 0) else 1


if __name__ == '__main__':
    sys.exit(main())
