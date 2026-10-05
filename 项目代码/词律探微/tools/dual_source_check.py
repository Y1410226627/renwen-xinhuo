# -*- coding: utf-8 -*-
"""dual_source_check.py —— **「同一件事被两处定义」的机制性门禁**。

来历（2026-09-30）：外部审查（`AI优化建议.txt`）十轮逐行审出的问题里，**超过一半**有同一个根——
「同名同义的量在代码里出现两次」：汉字范围三套、比例算法两套、指标标签两套、注释与实现不符若干处。
前九轮的门禁都在测「单点正确」，这一份测**「两点一致」**：新增一处来源会被立刻发现。

两种断言（都做成**可执行**的）：
  ① 两点一致：两个定义在同名同义的输入上必须给出**相同输出**（或对象同一）。
  ② 承诺可实现：docstring 承诺的事，跑一句断言核实（抓「注释骗人」）。

比对项数为 0 即 FAIL。用法：python tools/dual_source_check.py
"""
import io
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import aggregate          # noqa: E402
import corpus             # noqa: E402
import guard              # noqa: E402
import pronounce as PR    # noqa: E402
import prosody            # noqa: E402
import qlm                # noqa: E402
import retrieve           # noqa: E402
import safety             # noqa: E402

DB = os.path.join(ROOT, 'data', 'corpus.db')
checks, fails, n_cmp = [], [], 0


def ck(name, ok, detail=''):
    global n_cmp
    checks.append(name)
    n_cmp += 1
    if not ok:
        fails.append('%s%s' % (name, ('：' + detail) if detail else ''))
    print('  %s %s%s' % ('ok  ' if ok else 'FAIL', name, ('：' + detail) if detail else ''))


def rd(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def main():
    conn = sqlite3.connect(DB)
    print('· 一点一致（同名同义的两个定义必须给出同一结果）')

    # 1 汉字范围：retrieve / pronounce / prosody 必须都用 corpus.HAN_CLASS
    chars = ['一', '䕷', '平', '□', '○', 'a', '，', '𠀀']
    bad = [c for c in chars if retrieve.is_hanzi(c) != bool(corpus.HAN_RE.fullmatch(c))]
    ck('汉字判定 retrieve == corpus.HAN_RE', not bad, str(bad))
    p = PR.Pronouncer(PR.default_overrides_path())
    ck('注音层各字注音可用（构造 Pronouncer 成功）', bool(p.ping_ze('天地')))
    ck('注音层汉字范围同源（pronounce._KNOWN_RE 用 corpus.HAN_CLASS）',
       'HAN_CLASS' in rd('solve/pronounce.py') or 'corpus' in rd('solve/pronounce.py'),
       'pronounce.py 未引用 corpus 的汉字范围')
    ck('「䕷」(U+4577, 扩展 A) 三处都算汉字',
       retrieve.is_hanzi('䕷') and corpus.HAN_RE.fullmatch('䕷') and corpus.han_only('䕷') == '䕷')
    ck('「□」(U+25A1 缺字占位符) 三处都不算汉字',
       not retrieve.is_hanzi('□') and not corpus.HAN_RE.match('□') and corpus.han_only('□') == '')

    # 2 比例算法：pct() 必须等于 r1(raw_pct())
    cases = [(263, 750), (56, 100), (1, 3), (0, 0), (224, 400), (1, 8)]
    bad = [(z, t, prosody.pct(z, t), prosody.r1(prosody.raw_pct(z, t))) for z, t in cases
           if abs(prosody.pct(z, t) - prosody.r1(prosody.raw_pct(z, t))) > 1e-9]
    ck('prosody.pct == r1(raw_pct)（Decimal 单一口径）', not bad, str(bad))
    ck('比例用银行家舍入（56.25→56.2，审查 B14 的 .x5 边界）',
       prosody.pct(9, 16) == 56.2, str(prosody.pct(9, 16)))
    ck('aggregate 的比例数字与 prosody.pct 同源（promise: 全项目一套比例口径）',
       abs(aggregate.prosody.pct(1, 3) - prosody.pct(1, 3)) < 1e-9)

    # 3 数值区间：规则路与大模型路共用一份
    ck('RNG_BOUNDS 单一来源（qlm 引用 retrieve 的同一份）',
       qlm.RNG_BOUNDS is retrieve.RNG_BOUNDS or qlm.RNG_BOUNDS == retrieve.RNG_BOUNDS,
       '%s vs %s' % (qlm.RNG_BOUNDS, retrieve.RNG_BOUNDS))

    # 4 指标标签：aggregate 与 retrieve 不许各写一份（审查 C16）
    share2 = {'share', 'unspecified'}
    common = set(aggregate.METRICS) & set(retrieve.AGG_METRICS_LABEL)
    diff = {k: (aggregate.METRICS[k], retrieve.AGG_METRICS_LABEL[k]) for k in common
            if aggregate.METRICS[k] != retrieve.AGG_METRICS_LABEL[k]}
    ck('指标标签两处一致（共通键的取值必须相同）', not diff, str(diff))
    ck('指标标签覆盖同一集合（差集只允许 %s）' % sorted(share2),
       set(aggregate.METRICS) ^ set(retrieve.AGG_METRICS_LABEL) <= share2,
       str(set(aggregate.METRICS) ^ set(retrieve.AGG_METRICS_LABEL)))

    # 5 句脚字判定：SQL 用 substr(l.pz,-1,1)，Python 用 pz[-1:]，必须同源
    rows = conn.execute('SELECT idx,text,han_len,pz,tail FROM lines WHERE pid=? ORDER BY idx',
                        ('ci.清.0000.base.json#46',)).fetchall()
    # 不变量：pz 串长度 == 句内汉字数；句脚平仄 = pz 末位；句脚字 = 句内末个汉字
    bad = [(r[0], len(r[3]), r[2], corpus.han_only(r[1])[-1:], r[4]) for r in rows
           if len(r[3]) != r[2] or corpus.han_only(r[1])[-1:] != r[4]]
    ck('句级不变量：len(pz)==汉字数 且 句脚字==句内末个汉字', not bad, str(bad[:3]))
    bad2 = [(r[0], r[3][-1:]) for r in rows if r[3][-1:] not in ('平', '仄')]
    ck('句脚平仄只用 平/仄 两个字', not bad2, str(bad2[:3]))

    # 6 _quote / quote 公开别名同一实现
    ck('prosody.quote 是 _quote 的公开别名（审查 T7）',
       prosody.quote is prosody._quote or prosody.quote('天。') == prosody._quote('天。'))

    print('· 二点承诺（docstring 承诺的事，跑一句核实）')

    # 7 _norm_dynasty 的承诺：英文朝代 → 中文（审查 C1：此前 docstring 有、实现空）
    ck('_norm_dynasty("yuan") == "元"（docstring 承诺可执行）',
       corpus._norm_dynasty('yuan') == '元', corpus._norm_dynasty('yuan'))
    ck('_norm_dynasty 对中文朝代原样返回',
       corpus._norm_dynasty('清') == '清' and corpus._norm_dynasty('') == '')

    # 8 safety.refusal 的承诺：能直接过 guard.check_no_support
    for cat in safety.categories()[:3]:
        _t = safety.refusal(cat)
        # 内容安全拒答 ≠ 语料无据拒答，「未见支持」不适用；docstring 承诺的是
        # 「不含数字与引文」这两条（审查 B24/C20），这里就核这两条。
        ck('safety.refusal(%s) 不含数字与引文（审查 B24/C20）' % cat,
           (not guard.NUM_RE.search(guard.EID_RE.sub(' ', _t))) and '「' not in _t
           and '"' not in _t, _t[:60])
    ck('categories() 包含追加规则（审查 B29）',
       set(safety.categories()) >= {name for name, _ in safety.RULES})

    # 9 count_hits 的语义承诺：无硬条件 None / 有硬条件 0（审查 C8）
    sp_none = retrieve.QuerySpec()
    sp_hard = retrieve.QuerySpec()
    sp_hard.author_any = ['不存在的词人甲乙丙']
    retrieve._finalize(sp_hard)
    ck('count_hits 无硬条件返回 None', retrieve.count_hits(conn, sp_none) is None)
    ck('count_hits 有硬条件零命中返回 0', retrieve.count_hits(conn, sp_hard) == 0)

    # 10 语料载入的承诺：pid 唯一（审查 B11：缺 id 时曾全部变成 ps:None）
    # 10 语料载入的承诺：pid 唯一（审查 B11：缺 id 时曾全部变成 ps:None）
    # ⚠ 2026-10-04 修（代码审查 P2-15）：旧版路径写成 `dirname(DB)/语料` = `data/语料`（并不存在），
    #   于是这条防回归检查**永远走 else 只打印提示**、不计入失败——形同虚设。
    #   现在：语料目录可用 CLI/环境变量指定，找不到就**明确失败**（不再静默跳过）。
    corpus_dir = (os.environ.get('LVC_CORPUS')
                  or os.path.join(os.path.dirname(os.path.dirname(DB)), '语料'))
    if not os.path.isdir(corpus_dir):
        corpus_dir = r'D:\桌面\人文薪火\数据\语料'          # 本机默认（换机请用 LVC_CORPUS）
    ps = corpus.load_qing(corpus_dir)
    if ps:
        pids = [x.pid for x in ps]
        ck('poetry-source 篇目 pid 唯一（缺 id 时不得都叫 ps:None）',
           len(pids) == len(set(pids)) and 'ps:None' not in pids,
           '%d 篇 / %d 个不同 pid' % (len(pids), len(set(pids))))
    else:
        ck('poetry-source 篇目 pid 唯一（缺 id 时不得都叫 ps:None）', False,
           '语料目录不可用：%s（用 LVC_CORPUS 指定；**不再静默跳过**）' % corpus_dir)

    # 11 数据文件里「同一件事只写一处」的显式清单（新增重复来源会在这条上现形）
    for rel, pat, note in (
            ('solve/retrieve.py', r"HAN_CLASS as _HAN_CLASS", 'retrieve 用 corpus.HAN_CLASS'),
            ('solve/prosody.py', r"from corpus import han_only", 'prosody 用 corpus.han_only'),
            ('solve/aggregate.py', r"import prosody", 'aggregate 用 prosody.pct/r1'),
    ):
        ck('单一来源：%s' % note, pat in rd(rel))

    print('\n===== 双来源一致性汇总 =====')
    print('  检查项 %d，比对项 %d，FAIL %d' % (len(checks), n_cmp, len(fails)))
    if n_cmp == 0 or not checks:
        print('  ✗ FAIL：比对项数为 0（防「空跑报通过」）')
        return 1
    if fails:
        for f in fails:
            print('   ✗ %s' % f)
        return 1
    print('  全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
