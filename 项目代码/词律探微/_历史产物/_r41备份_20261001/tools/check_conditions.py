# -*- coding: utf-8 -*-
"""check_conditions.py —— **条件一致性门禁**（专治「解析了条件，但没落到检索/展示上」这一类错）。

由来（2026-09-30 实测）：问「句脚是「愁」的清词有哪些」，系统答「共召回 3 篇」，
展示的却是「仄声占比最高」的句（句脚是 否/中/头）——
① 检索其实生效了（真值 794 篇），但 ② **展示的句子与问句条件无关**，③ **「共 N 篇」用了 top-k 而不是真值**。
三者都不会崩溃、都不会触发旧护栏，属于「静默答非所问」。本门禁把这一类**逐条程序化**：

  一、**条件覆盖率**：问句解析出的每一个条件，都必须在检索 SQL 里出现（字段→片段映射表逐条核）。
  二、**结果复核**：返回的每一篇，用**另一条路径**（Python 侧逐条比对）复核确实满足全部条件。
  三、**展示复核**：行级条件题（句脚字/句脚平仄/声律模式）展示的句必须**就是命中的句**。
  四、**计数复核**：「共命中 N 篇」的 N 必须等于真值（不是 top-k、不是 0）。
  五、**空结果复核**：无命中必须拒答且不带数字/引文（防「拿语义相近的篇凑数」）。

用法：python tools/check_conditions.py [--db data/corpus.db] [--topk 3]
退出码：0 = 全过；1 = 有 FAIL（**比对项数为 0 也判 FAIL**）。
"""
import argparse
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import ask as A            # noqa: E402
import retrieve as R       # noqa: E402

# 行级条件在检索 SQL 里的痕迹（供人工对照；一、条件覆盖率按字段逐条核）
RNG_COLS = {'ze_min': 'p.ze_ratio', 'ze_max': 'p.ze_ratio', 'len_min': 'p.han_len',
            'len_max': 'p.han_len', 'sent_min': 'p.sent_n', 'sent_max': 'p.sent_n',
            'change_min': 'p.change', 'change_max': 'p.change',
            'thr_min': 'p.threshold', 'thr_max': 'p.threshold'}

CASES = [
    # (问句, 必查的行级字段/其他说明)
    ('句脚是「愁」的清词有哪些', 'tail'),
    ('句脚是「灯」或者「声」的清词有哪些', 'tail_any'),   # 2026-09-30 主人实测：并列条件被吞掉一半
    ('清 句脚=愁', 'tail'),
    ('句脚为平 清 临江仙', 'tail_pz'),
    ('声律模式 仄仄平平仄', 'pz'),
    ('清 临江仙 或者 念奴娇', 'cipai_any'),              # 词牌并列
    ('清 临江仙 仄声比例高于45%', None),
    ('找后段下降的清词', None),
    ('朱彝尊 桂殿秋', None),
    ('清 字数少于30的词', None),
    ('宋 念奴娇 平仄比例', None),
    ('纳兰性德 长相思', None),
    ('唐 李白 静夜思 的平仄', None),         # 语料外 → 拒答
    ('句脚是「龘」的清词', 'tail'),           # 0 命中 → 拒答
    ('后段下降 清 句脚为仄', 'tail_pz'),
    ('清 临江仙 句脚是「愁」', 'tail'),
]
# 若上面这些问句解析出了词面条件，不得是连接词/虚词残渣（「或者」曾被当词面条件）
BAD_KEYWORDS = set(R.CONNECTORS) | {'模式', '比例', '的词', '水平', '阈值'}


def main():
    ap = argparse.ArgumentParser(description='条件一致性门禁')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--topk', type=int, default=3)
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)

    checks, fails = [], []
    n_cmp = 0                    # **实际比对项数**（0 即 FAIL）

    def ck(name, ok, detail=''):
        checks.append(name)
        print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, ('：' + detail) if detail else ''))
        if not ok:
            fails.append('%s %s' % (name, detail))

    for q, _hint in CASES:
        print('· %s' % q)
        spec = R.parse_query(conn, q)
        where, sargs = R._sql(spec)
        # 零、多值/并列必须落成 SQL 的 IN（或单值 =），且词面不得残留连接词
        vals = {a: R._vals(spec, a) for a in ('dynasty', 'author', 'cipai', 'tail')}
        for a, lst in vals.items():
            if not lst:
                continue
            n_cmp += 1
            col = {'dynasty': 'p.dynasty', 'author': 'p.author', 'cipai': 'p.cipai'}.get(a)
            if a == 'tail':
                ok_sql = ('l.tail = ?' in where) or ('l.tail IN (' in where)
            else:
                ok_sql = ('%s = ?' % col in where) or ('%s IN (' % col in where)
            ck('零·多值落成 SQL（%s=%s）：%s' % (a, '／'.join(lst), q), ok_sql, where)
        n_cmp += 1
        bad_kw = [k for k in spec.keywords if k in BAD_KEYWORDS]
        ck('零·词面不含连接词/虚词残渣：%s' % q, not bad_kw, str(bad_kw))
        # 一、条件覆盖率
        n_cmp += 1
        missing = []
        for a, col in (('dynasty', 'p.dynasty'), ('author', 'p.author'), ('cipai', 'p.cipai')):
            if vals[a] and not (('%s = ?' % col in where) or ('%s IN (' % col in where)):
                missing.append(a)
        if spec.scene and 'p.scene = ?' not in where:
            missing.append('scene')
        if vals['tail'] and not (('l.tail = ?' in where) or ('l.tail IN (' in where)):
            missing.append('tail')
        if spec.tail_pz and 'substr(l.pz, -1, 1) = ?' not in where:
            missing.append('tail_pz')
        if spec.pz and 'l.pz LIKE ?' not in where:
            missing.append('pz')
        for k in spec.rng:
            if RNG_COLS[k] not in where:
                missing.append(k)
            n_cmp += 1
        ck('一·条件都进了检索 SQL：%s' % q, not missing,
           ('条件 %s 未出现在 SQL（SQL=%s）' % (missing, where)) if missing else
           '条件 %s' % (spec.describe() or '（无）'))

        res = A.answer(conn, q, topk=args.topk)
        refused = res['refused']
        # 五、空结果 / 语料外
        if spec.unsupported or not res['blocks']:
            n_cmp += 1
            ok = refused and '未见支持' in res['answer'] and not re.search(r'\d', res['answer'].replace('【查询理解】', ''))
            ck('五·无命中即认账（不带数字）：%s' % q, ok,
               'refused=%s' % refused if not ok else '拒答文本合规')
            continue
        # 二、结果复核（另一条路径）
        bad = []
        for b in res['blocks']:
            n_cmp += 1
            v = R.verify_spec_on_poem(conn, b['pid'], spec)
            if v:
                bad.append('%s %s' % (b['eid'], v))
        ck('二·返回篇目确实满足条件：%s' % q, not bad, '；'.join(bad))
        ck('二·接口自报条件复核为空：%s' % q, not res.get('cond_violations'),
           str(res.get('cond_violations')))
        # 三、展示复核（行级条件题）
        if R.has_line_cond(spec):
            n_cmp += 1
            worst = []
            for b in res['blocks']:
                first = b['lines'][0] if b['lines'] else None
                if not (first and first.get('matched')):
                    worst.append('%s 展示句未命中（展示第 %s 句）'
                                 % (b['eid'], (first['idx'] + 1) if first else '—'))
            ck('三·展示的句就是命中的句：%s' % q, not worst, '；'.join(worst))
        # 四、计数复核
        truth = R.count_hits(conn, spec)
        m = re.search(r'共命中\s*(\d+)\s*篇', res['answer'])
        n_cmp += 1
        got = int(m.group(1)) if m else None
        ck('四·命中篇数写的是真值：%s' % q, (truth is None and got is None) or (got == truth),
           '答案写 %s，真值 %s' % (got, truth))
        # 四·补：真值 = 独立重算（不复用 count_hits 的 SQL：自己拼一条 WHERE 数一遍）
        if vals['tail']:
            n_cmp += 1
            w2, a2 = [], []

            def _in(col, lst):
                if len(lst) == 1:
                    w2.append('%s = ?' % col); a2.append(lst[0])
                else:
                    w2.append('%s IN (%s)' % (col, ','.join('?' * len(lst)))); a2.extend(lst)

            for a, col in (('dynasty', 'p.dynasty'), ('cipai', 'p.cipai'), ('author', 'p.author')):
                if vals[a]:
                    _in(col, vals[a])
            if spec.scene:
                w2.append('p.scene = ?'); a2.append(spec.scene)
            _in('l.tail', vals['tail'])
            n_ind = conn.execute(
                'SELECT COUNT(DISTINCT p.pid) FROM poems p JOIN lines l ON l.pid = p.pid '
                'WHERE ' + ' AND '.join(w2), a2).fetchone()[0]
            ck('四·真值可独立复算：%s' % q, n_ind == truth,
               '独立数 %d，count_hits %s' % (n_ind, truth))
        # 四·补：答案里出现的篇数不能超过真值
        n_cmp += 1
        ck('四·展示篇数不超过真值：%s' % q, truth is not None and len(res['blocks']) <= truth,
           '展示 %d，真值 %s' % (len(res['blocks']), truth))
        # 六、展示覆盖（多值题：**每个被查取值都要举例**——主人实测“问两个句脚只举一个”）
        cov_fields = R.cover_fields(spec)
        if cov_fields:
            n_cmp += 1
            m = re.search(r'【展示覆盖】([^\n]*)', res['answer'])
            ck('六·有展示覆盖说明：%s' % q, bool(m), (m.group(1)[:60] if m else '缺【展示覆盖】行'))
            for attr in cov_fields:
                for v in cov_fields[attr]:
                    n_cmp += 1
                    shown = sum(1 for b in res['blocks']
                                if R.poem_has_value(conn, b['pid'], attr, v))
                    tv = R.count_for_value(conn, spec, attr, v)
                    ok = bool(shown) or tv == 0          # 库里真没例才能不举
                    ck('六·取值有例（%s=%s）：%s' % (attr, v, q), ok,
                       '展示 %d 篇，库中真值 %d 篇' % (shown, tv))
                    if shown:
                        n_cmp += 1
                        # 展示覆盖行里的数字必须与自己数的一致
                        mm = re.search(r'%s\s+(\d+)\s*篇' % re.escape(v), m.group(1) if m else '')
                        ck('六·覆盖数字与实展相符（%s=%s）：%s' % (attr, v, q),
                           bool(mm) and int(mm.group(1)) == shown,
                           '文中 %s，实展 %d' % (mm.group(1) if mm else '缺', shown))

    print('\n===== 条件一致性汇总 =====')
    print('  检查项 %d，比对项 %d，FAIL %d' % (len(checks), n_cmp, len(fails)))
    if n_cmp == 0 or not checks:
        print('  ✗ FAIL：比对项数为 0（防「空跑报通过」）')
        return 1
    if fails:
        for f in fails:
            print('   ✗ %s' % f)
        return 1
    print('  全部通过')
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
