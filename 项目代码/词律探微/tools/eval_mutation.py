# -*- coding: utf-8 -*-
"""eval_mutation.py —— 评测台变异测试（第十轮新增，常设门禁）

**为什么需要它**：评测台自己也会骗人。若某个字段解析不出来（或比对太宽松），
评测台就会对它「静默免考」——我上一轮就栽在这里：官方并列写「两篇」，我的正则
只收「甲乙」，于是 34 道题从没被比对过，却报出「700/700」。

**做法**：逐题、**逐个叶子字段**把标准答案改错，然后要求评测台必须报出「不符」。
只要有一个字段改错而评测台不报，就是**静默免考**，退出码非 0。
（注意：一次性把所有字段都改错是**弱测试**——只要报出任意一个字段就算「捕获」，
会掩盖未校验的字段。所以本工具做的是逐字段。）

**豁免**：自由文本字段（`前段引文` / `后段引文` / `边界声明`，以及 gold 侧下划线开头的
解释性字段如 `_boundary`）按官方口径不参与逐字比对（引文「任一句皆可」、边界声明逐题异文），
故对它们不计漏报，但会单独统计。

用法：
  python tools/eval_mutation.py --gold <题面.jsonl> --pred <答案.jsonl>
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'solve'))

from eval import parse_gold, compare  # noqa: E402

FREE_TEXT_SUFFIX = ('引文',)          # 官方代理评分只查可定位性，不比对语义
FREE_TEXT_EXACT = ('边界声明',)        # 逐题异文散文
# gold 侧的**解释性字段**（`eval.py` 的约定：字段名以下划线开头 ⇒ 官方原文的解释/说明文字，
# 不参与逐字比对，与引文同理）。典型例子：C5 官方答案末尾的「解释边界：…」被解析成 `_boundary`。
# 2026-10-02 修：豁免清单原来只认**我方输出**的字段名（「边界声明」），漏了 **gold 侧**的
# `_boundary`，于是它进了变异循环、改错后评测台照判「一致」→ 被当成「静默免考」误报 FAIL。
# 按上述约定识别（**不是**因为报错就放水），并且照旧**单独计数**，不掩盖真问题。
FREE_TEXT_PREFIX = ('_',)


def is_free_text(key):
    return (key.endswith(FREE_TEXT_SUFFIX) or key in FREE_TEXT_EXACT
            or key.startswith(FREE_TEXT_PREFIX))


def mutations_of(value):
    """给一个叶子值生成若干「错值」。要求：与原值不同，且仍是同类型（保证可比）。"""
    out = []
    if isinstance(value, bool):
        out.append(not value)
    elif isinstance(value, int):
        out.extend([value + 7, value - 3, 0])
    elif isinstance(value, float):
        out.extend([round(value + 7.0, 1), round(value - 3.0, 1), 0.0])
    elif isinstance(value, str):
        out.extend([value + 'X改错X', 'X改错X'])
        if value in ('甲', '乙', '丙', '两篇', '前后持平'):
            for alt in ('甲', '乙', '丙', '两篇'):
                if alt != value:
                    out.append(alt)
    elif isinstance(value, list):
        if value:
            out.append(list(reversed(value)))                    # 逆序
            if len(value) >= 2:
                sw = list(value)
                sw[0], sw[1] = sw[1], sw[0]
                out.append(sw)                                   # 换位（同集合！旧口径会漏报）
            out.append(value + [value[-1]])                      # 多一项
            out.append(value[:-1] if len(value) > 1 else [])     # 少一项
    return [m for m in out if m != value]


def walk(mutate_one):
    """对 parsed gold 生成 (字段路径, 变异后的 gold, 原值) 序列。"""
    def rec(path, node, parent, key):
        if isinstance(node, dict):
            for k, v in node.items():
                for item in rec(path + [k], v, node, k):
                    yield item
        else:
            if is_free_text(path[-1]):
                return
            for m in mutations_of(node):
                yield ('.'.join(map(str, path)), m, node, parent, key, path)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gold', required=True, help='题面 jsonl（含「标准答案」）')
    ap.add_argument('--pred', required=True, help='参赛答案 jsonl')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    gold = {}
    for l in io.open(args.gold, encoding='utf-8-sig'):
        if l.strip():
            q = json.loads(l)
            gold[q['题号']] = q
    mine = {}
    for l in io.open(args.pred, encoding='utf-8-sig'):
        if l.strip():
            r = json.loads(l)
            mine[r['题号']] = r

    total = caught = 0
    holes = {}
    free_skipped = [0]
    nomine = 0
    for qid, q in gold.items():
        r = mine.get(qid)
        if r is None:
            nomine += 1
            continue
        cls = (r.get('类别') or qid[-2:])
        g = parse_gold(cls, q.get('标准答案', ''))
        if not g:
            continue
        ans = r.get('答案') or {}
        # 逐个叶子字段制造变异副本
        def rec(node, path):
            if isinstance(node, dict):
                for k in list(node.keys()):
                    if is_free_text(k):
                        free_skipped[0] += 1
                        continue
                    yield from rec(node[k], path + [k])
            else:
                yield path, node
        for path, orig in rec(g, []):
            for m in mutations_of(orig):
                mut = json.loads(json.dumps(g, ensure_ascii=False))
                cur = mut
                for k in path[:-1]:
                    cur = cur[k]
                cur[path[-1]] = m
                total += 1
                ok, diffs = compare(cls, ans, mut)
                if ok is False and diffs:
                    caught += 1
                else:
                    holes.setdefault('.'.join(map(str, path)), 0)
                    holes['.'.join(map(str, path))] += 1
                    if not args.quiet:
                        print('  ✗ 静默免考：%s 字段 %s（改错后评测台仍判「一致」）'
                              % (qid, '.'.join(map(str, path))))
    print('\n===== 评测台变异测试 =====')
    print('  覆盖题目 %d（缺答案 %d 题，跳过）' % (len(gold) - nomine, nomine))
    print('  变异总数 %d，评测台捕获 %d，漏报 %d' % (total, caught, total - caught))
    print('  自由文本字段跳过 %d 处（引文/边界声明，官方口径不逐字比对）' % free_skipped[0])
    if total == 0:
        print('  ✗ FAIL：一个变异都没造出来——“0 漏报”不能这样报（空比对照样 PASS 是假通过）')
        return 1
    if holes:
        print('  ✗ 存在静默免考的字段：')
        for k, c in sorted(holes.items(), key=lambda x: -x[1]):
            print('     %-30s %d 次' % (k, c))
    else:
        print('  ✓ 无静默免考：任何字段改错都会被评测台判为「不符」')
    return 1 if holes else 0


if __name__ == '__main__':
    sys.exit(main())
