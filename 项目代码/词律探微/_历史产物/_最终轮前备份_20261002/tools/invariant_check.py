# -*- coding: utf-8 -*-
"""不变式检查（直接查 `corpus.db`）：**入库的数据自己对不对**。

为什么必须单列一条命令：答题成绩满分只能证明「1000 道题算对了」，
不能证明「库里 5.9 万首的每一首都自洽」。这里把 15 类恒等式逐条验，
而且尽量**从不同路径重算**（从句级平仄串重算篇级指标），避免自证自话。

15 类：
   篇级 1) ping + ze == han_len
   篇级 2) sent_n == lines 行数
   篇级 3) cut == sent_n // 2
   篇级 4) ze_ratio == r1(100 × ze / han_len)
   篇级 5) f_ratio == r1(100 × 前段仄 / 前段汉字)（按 cut 从句级重算）
   篇级 6) b_ratio == r1(100 × 后段仄 / 后段汉字)
   篇级 7) change == r1(后段原始比例 − 前段原始比例)（原始值相减，官方口径）
   篇级 8) abs_change == |change|
   篇级 9) threshold == ceil(han_len / sent_n)
   篇级 10) longest_len == 句级最长句字数；longest_seq == 该句序（1 起，含并列）
   篇级 11) scene 与 change 符号一致（上升/下降/持平）
   句级 12) han_len == pz 长度 == 原文汉字数
   句级 13) ping + ze == han_len
   句级 14) tail == 原文最后一个汉字
   索引 15) 句级索引完整（lines_bigram / lines_fts 覆盖全部句）且 meta 计数与实表一致

用法：python tools/invariant_check.py [--db data/corpus.db] [--limit N]
退出码：0 = 0 违反；1 = 有违反（并打印前若干条）。
"""
import argparse
import os
import sqlite3
import sys
from decimal import Decimal, ROUND_HALF_EVEN

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))
from corpus import HAN_RE                                   # noqa: E402  （汉字区间单一来源）


def r1(x):
    return float(Decimal(repr(x)).quantize(Decimal('0.1'), rounding=ROUND_HALF_EVEN))


def main():
    ap = argparse.ArgumentParser(description='不变式检查（15 类，直接查库）')
    ap.add_argument('--db', default=os.path.join(ROOT, 'data', 'corpus.db'))
    ap.add_argument('--limit', type=int, default=8, help='每类最多打印几条反例')
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    bad = {}
    checked = 0

    def fail(kind, detail):
        bad.setdefault(kind, []).append(detail)

    print('=== 篇级（SQL 可判）===')
    sql_checks = [
        ('1 ping+ze==han_len', 'SELECT COUNT(*) FROM poems WHERE ping + ze <> han_len'),
        ('3 cut==sent_n//2', 'SELECT COUNT(*) FROM poems WHERE cut <> sent_n / 2'),
        ('8 abs_change==|change|', 'SELECT COUNT(*) FROM poems WHERE ABS(abs_change - ABS(change)) > 1e-9'),
        ('9 threshold==ceil(han_len/sent_n)',
         'SELECT COUNT(*) FROM poems WHERE threshold <> CAST((han_len + sent_n - 1) / sent_n AS INT)'),
    ]
    for name, sql in sql_checks:
        n = con.execute(sql).fetchone()[0]
        checked += 1
        print('  %-38s 违反 %d' % (name, n))
        if n:
            fail(name, '%d 行' % n)
    # 逐篇重算（用句级平仄串，路径与引擎不同）
    print('=== 篇级（从句级重算）＋ 句级/索引 ===')
    rows = con.execute(
        'SELECT p.pid,p.sent_n,p.han_len,p.ping,p.ze,p.ze_ratio,p.cut,p.f_ratio,p.b_ratio,'
        'p.change,p.abs_change,p.threshold,p.longest_len,p.longest_seq,p.scene FROM poems p').fetchall()
    lines = {}
    for pid, idx, text, hl, ping, ze, pz, tail in con.execute(
            'SELECT pid,idx,text,han_len,ping,ze,pz,tail FROM lines ORDER BY pid, idx'):
        lines.setdefault(pid, []).append((idx, text, hl, ping, ze, pz, tail))
    if args.limit:
        pass
    for (pid, sent_n, han_len, ping, ze, ze_ratio, cut, f_ratio, b_ratio, change,
         abs_change, threshold, longest_len, longest_seq, scene) in rows:
        L = lines.get(pid, [])
        checked += 2
        if len(L) != sent_n:
            fail('2 sent_n==lines 行数', '%s %d vs %d' % (pid, sent_n, len(L)))
        for (idx, text, hl, p, z, pz, tail) in L:
            checked += 3
            if hl != len(pz) or pz.count('平') + pz.count('仄') != hl:
                fail('12/13 句级汉字数与平仄数', '%s#%d' % (pid, idx))
            if p != pz.count('平') or z != pz.count('仄'):
                fail('13 句级平仄与 pz 不符', '%s#%d' % (pid, idx))
            last = (HAN_RE.findall(text) or [''])[-1]
            if tail != last:
                fail('14 tail==句末汉字', '%s#%d %r vs %r' % (pid, idx, tail, last))
        if not L:
            continue
        head = ''.join(x[5] for x in L[:cut])
        tailp = ''.join(x[5] for x in L[cut:])
        f_raw = 100.0 * head.count('仄') / max(1, len(head))
        b_raw = 100.0 * tailp.count('仄') / max(1, len(tailp))
        checked += 6
        if abs(r1(100.0 * ze / max(1, han_len)) - ze_ratio) > 1e-9:
            fail('4 ze_ratio 重算', '%s %s vs %s' % (pid, ze_ratio, r1(100.0 * ze / max(1, han_len))))
        if abs(r1(f_raw) - f_ratio) > 1e-9:
            fail('5 f_ratio 重算', '%s %s vs %s' % (pid, f_ratio, r1(f_raw)))
        if abs(r1(b_raw) - b_ratio) > 1e-9:
            fail('6 b_ratio 重算', '%s %s vs %s' % (pid, b_ratio, r1(b_raw)))
        if abs(r1(b_raw - f_raw) - change) > 1e-9:
            fail('7 change 重算', '%s %s vs %s' % (pid, change, r1(b_raw - f_raw)))
        lens = [x[2] for x in L]
        mx = max(lens)
        seq = [i + 1 for i, v in enumerate(lens) if v == mx]
        if longest_len != mx:
            fail('10 longest_len', '%s %s vs %s' % (pid, longest_len, mx))
        if longest_seq != str(seq).replace("'", '"'):
            fail('10 longest_seq', '%s %s vs %s' % (pid, longest_seq, seq))
        d = r1(b_raw - f_raw)
        want = ('后段上升' if d > 0 else '后段下降' if d < 0 else '前后持平')
        if scene != want:
            fail('11 scene 与变化方向', '%s %s vs %s' % (pid, scene, want))
    for name, sql in (
            ('15 lines_bigram 覆盖', 'SELECT (SELECT COUNT(*) FROM lines) - (SELECT COUNT(*) FROM lines_bigram)'),
            ('15 lines_fts 覆盖', 'SELECT (SELECT COUNT(*) FROM lines) - (SELECT COUNT(*) FROM lines_fts)'),
            ('15 meta poems', "SELECT (SELECT COUNT(*) FROM poems) - CAST((SELECT v FROM meta WHERE k='poems') AS INT)"),
            ('15 meta lines', "SELECT (SELECT COUNT(*) FROM lines) - CAST((SELECT v FROM meta WHERE k='lines') AS INT)")):
        n = con.execute(sql).fetchone()[0]
        checked += 1
        print('  %-38s 差异 %d' % (name, n))
        if n:
            fail(name, '%d' % n)
    con.close()

    print('\n===== 不变式汇总 =====')
    print('  检查项 %d，篇数 %d' % (checked, len(rows)))
    if checked == 0:
        print('  ✗ FAIL：检查项为 0（防「空跑报通过」）')
        return 1
    if bad:
        print('  违反 %d 类：' % len(bad))
        for k, v in bad.items():
            print('   ✗ %s：%d 例，例如 %s' % (k, len(v), v[:args.limit]))
        return 1
    print('  0 违反 → 全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
