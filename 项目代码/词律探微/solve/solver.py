# -*- coding: utf-8 -*-
"""solver.py —— 主程序：读题面 jsonl → 定位原文 → 调引擎 → 输出答案 jsonl。

用法：
  python solver.py --question 公开测试集_700题.jsonl --corpus <语料根目录> --output answers.jsonl
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus import load_corpus, locate_one, get_locator    # noqa: E402
from pronounce import Pronouncer, default_overrides_path    # noqa: E402
from prosody import Engine                                  # noqa: E402

CLS_MAP = {
    '同调全篇声律比例差': 'C1',
    '跨篇分段变幅比较': 'C2',
    '跨篇长句仄声密度比较': 'C3',
    '跨篇后段排序与比例差距': 'C4',
    '跨篇景情节奏互证': 'C5',
}

# 题面解析要宽容格式：行首允许空白，甲／乙／丙 与冒号之间允许空格与全角空格（\s 已涵盖 U+3000）。
# 第九轮 fuzz 实测：`甲 ：` 这种写法会让旧正则整行不匹配 → 定位全变（700/700）。
LINE_RE = re.compile(r'^\s*([甲乙丙])\s*[：:]\s*(.+)$')
# 审查 B39：题面也可能用空格分隔（「清 周容《小重山》」），此前只认「·」
DYN_AU_RE = re.compile(r'^([^·\u00b7\s]+?)\s*(?:[·\u00b7]|\s)\s*([^《]+)')
TITLE_RE = re.compile(r'《([^》]+)》')
# 审查 B38：题面可能用「」『』（此前只认 ASCII/弯引号，改一处漏一处）
CIPAI_RE = re.compile(r'词牌\s*[\u201c"「『]([^\u201d"」』]+)[\u201d"」』]')
HEAD_RE = re.compile(r'首句\s*[\u201c"「『]([^\u201d"」』]+)[\u201d"」』]')


def parse_question(text: str):
    """从题面解析出 甲/乙/丙 各篇的 (朝代, 作者, 题名, 词牌, 首句)。"""
    out = {}
    for line in (text or '').replace('\\n', '\n').split('\n'):
        m = LINE_RE.match(line.strip())
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        ma = DYN_AU_RE.match(body)
        dynasty = ma.group(1).strip() if ma else ''
        author = ma.group(2).strip() if ma else ''
        titles = TITLE_RE.findall(body)
        title = titles[-1] if titles else ''
        mc = CIPAI_RE.search(body)
        mh = HEAD_RE.search(body)
        out[tag] = {'朝代': dynasty, '作者': author, '题名': title,
                    '词牌': mc.group(1) if mc else title,
                    '首句': mh.group(1) if mh else ''}
    return out


def solve_one(q, poems, eng, strict_locate=False):
    cls = CLS_MAP.get(q.get('类别'), '')
    suffix = (q.get('题号') or '')[-2:]
    mismatch = ''
    if cls and suffix and cls != suffix:
        # 类别与题号后缀不一致：以类别为准，但记下警告（防「题面忽变而静默错算」）
        mismatch = '类别(%s) 与题号后缀(%s) 不一致，按类别计算' % (cls, suffix)
    if not cls:
        cls = suffix
    parts = parse_question(q.get('问题', ''))
    need = ['甲', '乙'] + (['丙'] if '丙' in parts else [])
    located, errs = {}, []
    for tag in need:
        spec = parts.get(tag)
        if not spec:
            errs.append('%s 题面解析失败' % tag)
            continue
        poem = locate_one_safe(poems, spec)
        if poem is None:
            errs.append('%s 定位失败：%s《%s》首句 %s' % (tag, spec['作者'], spec['题名'], spec['首句'][:12]))
            continue
        located[tag] = poem

    ans = {}
    paths = {}
    for tag in need:
        spec = parts.get(tag)
        if not spec or tag not in located:
            continue
        _, path = locate_one_traced_safe(poems, spec)
        paths[tag] = path
        if not path.startswith('A4'):
            # 低置信不得静默当作确定答案（采纳自另一 AI 版本的 errors 标注设计）：
            # 1000 题实测全走 A4，故本标注不改变任何一条交付答案。
            errs.append('%s 定位低置信：[%s] %s《%s》' % (tag, path, spec['作者'], spec['题名']))
    # ⚠ 2026-10-06 修（外部审查 P1-26）：低置信定位原先**仍继续计算并给出答案**——对竞赛题，
    #   「错误定位」比「定位失败」危险得多（一个错答案比一个明确的"算不出"更糟）。
    #   新增 strict 开关（**默认关**，故交付答案逐字节不变）：开启后低置信篇目一律不参与计算
    #   （等价 insufficient_evidence），宁可拒答也不拿错定位的数值充数。
    if strict_locate:
        _low = sorted(t for t in located if not paths.get(t, '').startswith('A4'))
        if _low:
            for _t in _low:
                located.pop(_t, None)
            ans = {}
    if cls == 'C1' and '甲' in located and '乙' in located:
        ans = eng.c1(located['甲'].raw, located['乙'].raw)
    elif cls == 'C2' and '甲' in located and '乙' in located:
        ans = eng.c2(located['甲'].raw, located['乙'].raw)
    elif cls == 'C3' and '甲' in located and '乙' in located:
        ans = eng.c3(located['甲'].raw, located['乙'].raw)
    elif cls == 'C4' and len(located) >= 2:
        ans = eng.c4({k: v.raw for k, v in located.items()})
    elif cls == 'C5' and '甲' in located and '乙' in located:
        ans = eng.c5(located['甲'].raw, located['乙'].raw)
    else:
        errs.append('数据不足，无法计算（缺少 %s）' % cls)

    return {
        '题号': q.get('题号'),
        '类别': cls,
        '定位': {k: v.loc for k, v in located.items()},
        '答案': ans,
        'errors': errs,
        'warnings': ([mismatch] if mismatch else []),
        '路径': paths,
    }


def locate_one_safe(poems, spec):
    return locate_one(poems, spec['作者'], spec['词牌'], spec['首句'], spec.get('朝代', ''))


def locate_one_traced_safe(poems, spec):
    """带路径的定位（第十轮）：返回 (poem, path)。"""
    return get_locator(poems).find_one_traced(
        spec['作者'], spec['词牌'], spec['首句'], spec.get('朝代', ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--question', required=True)
    ap.add_argument('--corpus', default=r'D:\桌面\人文薪火\数据\语料')
    ap.add_argument('--output', required=True)
    ap.add_argument('--overrides', default=default_overrides_path())
    ap.add_argument('--limit', type=int, default=0)
    # ⚠ 2026-10-06 新增（外部审查 P1-26/27）：两个**默认关**的显式开关——既满足
    #   「低置信不作答 / error 即失败」的严格诉求，又保证默认路径与交付答案逐字节一致。
    ap.add_argument('--strict-locate', action='store_true',
                    help='低置信定位（非 A4）时不作答（默认关：保持交付答案不变）')
    ap.add_argument('--fail-on-error', action='store_true',
                    help='存在 error 时以非 0 退出码结束（供 CI/批处理区分 fatal 与 warning）')
    args = ap.parse_args()

    poems = load_corpus(args.corpus)
    if not poems:
        print('❌ 错误：语料载入为 0 首（--corpus %s 路径不对或缺少三源目录）。'
              '预期包含 poetry-source-master/source/词/<朝代>/*.base.json 与 '
              'chinese-poetry-master/{宋词,元曲}/。' % args.corpus, file=sys.stderr)
        return 2
    print('语料载入：%d 首' % len(poems), file=sys.stderr)
    eng = Engine(Pronouncer(args.overrides))
    # 交付级护栏：标定表缺失/为空是最容易「静默掉 30 分」的坑（实测空表仅 47.4%）
    nov = eng.p.n_overrides
    if nov == 0:
        print('⚠️ 警告：标定表为空或不可读（%s）：逐字取音将全走默认读音，'
              '公开集分数会从约 88%% 掉到约 47%%。若确为有意（对照实验），请忽略本提示。'
              % args.overrides, file=sys.stderr)
    else:
        print('标定表：%d 字（%s）' % (nov, args.overrides), file=sys.stderr)

    qs = [json.loads(l) for l in open(args.question, encoding='utf-8-sig') if l.strip()]
    if args.limit:
        qs = qs[:args.limit]

    nerr = 0
    nwarn = 0
    ncls = {}
    with open(args.output, 'w', encoding='utf-8') as f:
        for i, q in enumerate(qs, 1):
            r = solve_one(q, poems, eng, strict_locate=args.strict_locate)
            ncls[r['类别']] = ncls.get(r['类别'], 0) + 1
            if r['errors']:
                nerr += 1
            if r.get('warnings'):
                nwarn += 1
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
            if i % 50 == 0:
                print('  ... %d/%d' % (i, len(qs)), file=sys.stderr)
    print('类别分布：%s' % dict(sorted(ncls.items())), file=sys.stderr)
    print('完成：%d 题，其中 %d 题有 error、%d 题有 warning -> %s' % (len(qs), nerr, nwarn, args.output),
          file=sys.stderr)
    # ⚠ 2026-10-06 修（外部审查 P1-27）：原先无论有多少 error 都 exit 0——「日志写着 error、
    #   进程却成功」，CI 会一路绿灯。新增 --fail-on-error 开关显式区分 fatal 与 warning。
    if args.fail_on_error and nerr:
        print('❌ --fail-on-error：%d 题有 error，以非 0 退出' % nerr, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
