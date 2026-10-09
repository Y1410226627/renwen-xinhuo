# -*- coding: utf-8 -*-
"""review_diff.py —— 校订建议队列（功能④内核，第十一轮新增）

**吸收自第一份外部交付（`项目代码\\solve`）的 M11 设计**：语料自带一份逐字注音
（poetry-source 的 `*.pinyin.json`），它是**独立于我们引擎**的第三方标注。
把「引擎读音」与「语料标注」逐字对齐比对，差异就是**待裁定的校订工单**——
这正是「标注闭环」需要的东西：不预设谁对，先把分歧列出来、给出证据、留状态位。

为什么有价值：
  1. 引擎的平仄口径是从 1000 题反解出来的（长/别/绝 三个例外即来自此）；
     语料标注是另一条来源。二者的差集自然包含「我们的口径例外」与「语料本身注错」两类，
     正好是词学导师最该看一眼的地方。
  2. 全量数字可复算，不依赖题库（在隐藏数据上同样成立）。

产出：CSV（pid / 阕 / 句内位 / 字 / 引擎调 / 引擎平仄 / 语料调 / 语料平仄 / 证据）+ 汇总。
判据：**只报差异，不改任何数据**；字级频次表用来判断「值不值得进覆写表」。

用法：
  python tools/review_diff.py --corpus <语料根> --out data/reviews.csv [--dyn 清]
"""
import argparse
import csv
import glob
import io
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'solve'))

from pronounce import Pronouncer, default_overrides_path   # noqa: E402

# 声调符号 -> 调类（1 阴平 2 阳平 3 上 4 去；无符号 = 轻声/无调 = 0）
_TONE_MARKS = {
    'ā': 1, 'ē': 1, 'ī': 1, 'ō': 1, 'ū': 1, 'ǖ': 1,
    'á': 2, 'é': 2, 'í': 2, 'ó': 2, 'ú': 2, 'ǘ': 2,
    'ǎ': 3, 'ě': 3, 'ǐ': 3, 'ǒ': 3, 'ǔ': 3, 'ǚ': 3,
    'à': 4, 'è': 4, 'ì': 4, 'ò': 4, 'ù': 4, 'ǜ': 4,
}
_PUNCT = '，。！？；：、·「」『』（）《》〈〉“”‘’—… ,.!?;:()[]'


def tone_of_pinyin(syl):
    """从带调拼音（如 `cháng`）取调类；无调符返回 0。"""
    for ch in syl:
        if ch in _TONE_MARKS:
            return _TONE_MARKS[ch]
    return 0


def ping_ze(t):
    return '仄' if t in (3, 4) else '平'


def load_pinyin_records(source_root, dyn='清'):
    """读 poetry-source 的 `*.pinyin.json`（与 `.base.json` 一一对应，但多 `pinyin` 字段）。"""
    pats = [os.path.join(source_root, 'source', '词', dyn, '*.pinyin.json')]
    files = []
    for p in pats:
        files += glob.glob(p)
    for f in sorted(files):
        base = os.path.basename(f)
        for rec in json.load(io.open(f, encoding='utf-8')):
            yield base, rec


def iter_pairs(rec):
    """把 content（分阕正文）与 pinyin（分阕拼音串）逐字对齐，产出 (阕序, 数字, 音节数, [(位,字,调,音节)], None)。"""
    for zi, (content, pystr) in enumerate(zip(rec.get('content') or [], rec.get('pinyin') or [])):
        syllables = [t for t in _SYL.findall(pystr or '') if t]
        hans = [c for c in content if _is_han(c)]
        if len(syllables) != len(hans):
            yield ('未对齐', len(hans), len(syllables), [], None)
            continue
        pairs = [(k, c, tone_of_pinyin(syl), syl) for k, (c, syl) in enumerate(zip(hans, syllables))]
        yield (zi, len(hans), len(syllables), pairs, None)


def _is_han(c):
    return bool(_HAN.match(c))


_HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')
# 音节 token：ASCII 字母 + 带调元音（语料拼音里标点直接粘在音节后面，不能只按空白切）
_SYL = re.compile(r'[A-Za-z\u00c0-\u024f\u0100-\u01ff\u1e00-\u1eff\u0300-\u036f]+')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', required=True, help='语料根目录（其下有 poetry-source-master）')
    ap.add_argument('--out', default='data/reviews.csv')
    ap.add_argument('--dyn', default='清')
    ap.add_argument('--overrides', default=default_overrides_path())
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 篇（调试用）')
    args = ap.parse_args()

    root = os.path.join(args.corpus, 'poetry-source-master')
    if not os.path.isdir(root):
        print('❌ 找不到 %s' % root, file=sys.stderr)
        return 2

    p = Pronouncer(args.overrides)
    rows = []
    total_chars = 0
    n_poems = 0
    n_unaligned = 0
    by_char = Counter()
    by_char_pair = Counter()
    by_file_index = {}

    for base, rec in load_pinyin_records(root, args.dyn):
        n_poems += 1
        if args.limit and n_poems > args.limit:
            break
        idx = by_file_index.get(base, 0)
        by_file_index[base] = idx + 1
        pid = '%s#%d' % (base, idx)          # 与 corpus.py 的定位串口径一致（文件#数组下标）
        for zi, n_han, n_syl, pairs, _ in iter_pairs(rec):
            if zi == '未对齐':
                n_unaligned += 1
                continue
            for k, c, ct, syl in pairs:
                total_chars += 1
                et = p.tone(c)
                if et == ct:
                    continue
                if et == 0 or ct == 0:
                    # 轻声/无调（0）与「读不出」不判对错：口径上双方都记平，不算工单
                    if ping_ze(et) == ping_ze(ct):
                        continue
                ep, cp = ping_ze(et), ping_ze(ct)
                if ep == cp:
                    continue          # 调类不同但平仄一致 → 不影响本题口径，不入工单
                by_char[c] += 1
                by_char_pair['%s(%s→%s)' % (c, ct, et)] += 1
                rows.append({
                    'pid': pid, '阕': zi, '句内位': k, '字': c,
                    '引擎调': et, '引擎平仄': ep, '语料调': ct, '语料平仄': cp,
                    '证据': '%s 第%d阕第%d字 语料拼音 %s' % (base, zi + 1, k + 1, syl),
                    '状态': '待裁定',
                })

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or '.', exist_ok=True)
    with io.open(args.out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['pid', '阕', '句内位', '字', '引擎调', '引擎平仄',
                                          '语料调', '语料平仄', '证据', '状态'])
        w.writeheader()
        w.writerows(rows)

    print('===== 校订队列（引擎注音 vs 语料自带注音）=====')
    print('  篇数 %d（%s）／对齐汉字 %d 字' % (n_poems, args.dyn, total_chars))
    print('  未对齐阕 %d（音节数与汉字数不等，已计数跳过，不静默）' % n_unaligned)
    print('  平仄分歧工单 %d 条（%.3f%%）' % (len(rows), 100.0 * len(rows) / max(1, total_chars)))
    print('  涉及不同字 %d 个；TOP10：%s' % (len(by_char), by_char.most_common(10)))
    print('  TOP10（按「语料调→引擎调」细分）：%s' % by_char_pair.most_common(10))
    print('  已写出：%s' % args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
