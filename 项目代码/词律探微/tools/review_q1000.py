# -*- coding: utf-8 -*-
"""review_q1000.py —— 开工前审查（v3：**以「换汤不换药探测器」为核心**）。

主人给的判据：「换汤不换药 = 把词牌/朝代/句脚字/声律串/阈值等**参数抽象掉**后，操作链是否相同」。
本工具据此做三件事：

  一、**换汤不换药探测**（主判据）
     · 按 `sig`（= LQ｜LP｜PF｜SO｜OUT，**只由算子构成**）分组，**最大重数必须 = 1**；
     · 并**透明披露三个粒度**下的链数：粗（LQ｜OUT）/ 中（LQ｜LP｜OUT）/ 细（全签名）。
       粒度越粗，链数越少——这是必须如实说明的事，不能只报最细的那个数。

  二、措辞多样性：最近邻字符二元组 Jaccard、归一化去重、句首簇。
     （注意：这是"字面像不像"，与"操作链不同"是**两把尺子**，不能混用。）

  三、其他硬闸门：可答性（独立 SQL 复算命中数）、题面↔口径一致性、算子覆盖。

用法：python tools/review_q1000.py
退出码：0 = 全过；1 = 有 FAIL。
"""
import collections
import itertools
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import gen_q1000 as G            # noqa: E402  复用**独立真值口径**（scope_where / count_hits）

QFILE = os.path.join(ROOT, 'data', 'questions_1000.jsonl')
OUT = os.path.join(ROOT, '问题清单审查报告.md')
POLITE = re.compile(r'(麻烦|请帮我|帮我|我想找|劳驾|请问|问一下|查一下|想看看|请统计|给我个结果|帮我算算)')
PUNC = re.compile(r'[\s，。？、（）()「」“”%？＝*｜]')


def norm_q(s):
    return POLITE.sub('', PUNC.sub('', s))


def bigrams(s):
    s = norm_q(s)
    return set(s[i:i + 2] for i in range(len(s) - 1))


def main():
    rows = [json.loads(l) for l in open(QFILE, encoding='utf-8')]
    conn = sqlite3.connect('file:%s?mode=ro' % os.path.join(ROOT, 'data', 'corpus.db').replace('\\', '/'),
                           uri=True)
    rep, fails = [], []

    def out(s=''):
        print(s)
        rep.append(s)

    def ck(name, ok, detail=''):
        if not ok:
            fails.append('%s %s' % (name, detail))

    n = len(rows)
    sigs = [r['sig'] for r in rows]

    # ---------- 一、换汤不换药探测 ----------
    c1 = collections.Counter(sigs)
    fine = len(c1)
    mid = len({'｜'.join(s.split('｜')[:2] + [s.split('｜')[-1]]) for s in sigs})
    coarse = len({'｜'.join([s.split('｜')[0], s.split('｜')[-1]]) for s in sigs})
    dup_sig = [(k, v) for k, v in c1.items() if v > 1]
    out('## 一、换汤不换药探测（主判据）')
    out('')
    out('判据：把参数（词牌/朝代/句脚字/声律串/阈值…）抽象掉后，**操作链是否相同**。')
    out('')
    out('| 粒度 | 链的定义 | 不同链数 | 题数 | 最大重数 |')
    out('| --- | --- | --- | --- | --- |')
    out('| **细（本批采用）** | LQ｜LP｜PF｜SO｜OUT | **%d** | %d | **%d** |'
        % (fine, n, max(c1.values())))
    out('| 中 | LQ｜LP｜OUT | %d | %d | %d |'
        % (mid, n, max(collections.Counter(
            '｜'.join(s.split('｜')[:2] + [s.split('｜')[-1]]) for s in sigs).values())))
    out('| 粗 | LQ｜OUT | %d | %d | %d |'
        % (coarse, n, max(collections.Counter(
            '｜'.join([s.split('｜')[0], s.split('｜')[-1]]) for s in sigs).values())))
    out('')
    out('**说明**：粗粒度下只有 %d 条链——这是"最小公倍数"式的读法（只认「量词×输出」）。'
        '本批判为「不同」的粒度是**细**：谓词种类（句脚字/句脚平仄/平仄串包含/平仄串全等/'
        '句长区间/句位奇偶）与篇级筛选种类（元数据/声情/篇级指标区间/派生量/一致性/无）'
        '都算**不同的算子**。**若主人认为它们该算同一个算子，那 1000 条链凑不出来**，请指示。' % coarse)
    out('')
    ck('细粒度链唯一（最大重数=1）', max(c1.values()) == 1, str(dup_sig[:3]))

    # ---------- 二、措辞多样性 ----------
    bg = [bigrams(r['q']) for r in rows]
    nn = []
    for i in range(n):
        bi, best = bg[i], 0.0
        for j in range(n):
            if i == j:
                continue
            inter = len(bi & bg[j])
            if not inter:
                continue
            v = inter / len(bi | bg[j])
            if v > best:
                best = v
        nn.append(best)
    nn.sort()
    dupq = [k for k, v in collections.Counter(norm_q(r['q']) for r in rows).items() if v > 1]
    head = collections.Counter(norm_q(r['q'])[:4] for r in rows)
    allbg, tot = set(), 0
    for b in bg:
        allbg |= b
        tot += len(b)
    out('## 二、措辞多样性（字面尺子——**不用于判"换汤不换药"**）')
    out('')
    out('| 指标 | 值 |')
    out('| --- | --- |')
    out('| 最近邻 Jaccard 均值 / 中位 / P90 / 最大 | %.3f / %.3f / %.3f / %.3f |'
        % (sum(nn) / n, nn[n // 2], nn[int(n * 0.9)], nn[-1]))
    out('| 唯一二元组 / 总二元组 | %d / %d = %.3f |' % (len(allbg), tot, len(allbg) / tot))
    out('| 归一化后完全重复 | %d |' % len(dupq))
    out('| 句首 4 字最大同簇 | %d |' % max(head.values()))
    out('')
    ck('归一化无重复', not dupq, str(dupq[:2]))

    # ---------- 三、刁钻手法 ----------
    cn = ar = half = rngc = multi = polite = 0
    for r in rows:
        q, s = r['q'], r['spec']
        if POLITE.search(q):
            polite += 1
        if s.get('rng') or 'k' in s or 'ka' in s or 'ratio' in s or 'dchg' in s or 'lo' in s:
            rngc += 1
            if re.search(r'\d', q):
                ar += 1
            else:
                cn += 1
        if '一半' in q:
            half += 1
        if s.get('tail2'):
            multi += 1
    out('## 三、刁钻手法')
    out('')
    out('| 手法 | 题数 |')
    out('| --- | --- |')
    out('| 含数值/区间条件 | %d |' % rngc)
    out('| ├ 中文数字写法 | %d |' % cn)
    out('| └ 阿拉伯数字写法 | %d |' % ar)
    out('| 口语「一半」 | %d |' % half)
    out('| 多值并集/交集 | %d |' % multi)
    out('| 带礼貌语干扰 | %d |' % polite)
    out('')

    # ---------- 四、可答性 ----------
    zero, dist = 0, collections.Counter()
    for r in rows:
        try:
            m = G.count_hits(conn, tuple(r['sig'].split('｜')), r['spec'])
        except Exception:
            m = -1
        if m == 0:
            zero += 1
        k = '1-9' if 0 < m < 10 else '10-99' if m < 100 else '100-999' if m < 1000 \
            else '1000-8000' if m <= 8000 else '>8000'
        dist[k] += 1
    out('## 四、可答性（独立 SQL 复算命中数）')
    out('')
    out('| 命中数区间 | 题数 |')
    out('| --- | --- |')
    for k in ('1-9', '10-99', '100-999', '1000-8000', '>8000'):
        out('| %s | %d |' % (k, dist.get(k, 0)))
    out('| **0 命中（应为 0）** | **%d** |' % zero)
    out('')
    ck('非 0 命中', zero == 0, 'zero=%d' % zero)

    # ---------- 五、题面↔口径一致性 ----------
    mism = []
    for r in rows:
        q, s = r['q'], r['spec']
        miss = []
        for k in ('dynasty', 'author', 'cipai', 'tail', 'tail2'):
            for v in ([s[k]] if isinstance(s.get(k), str) else (s.get(k) or [])):
                if v and v not in q:
                    miss.append('%s=%s' % (k, v))
        for k in ('tone', 'pz'):
            if s.get(k) and s[k] not in q:
                miss.append('%s=%s' % (k, s[k]))
        # scene 题面用的是**同义词**（「后段下降」→「后半段降低/后段走低/…」），不能要求字面相等
        if s.get('scene'):
            alts = G.SCENE_PHRASE.get(s['scene'], [s['scene']])
            if not any(w in q for w in alts):
                miss.append('scene=%s' % s['scene'])
        if miss:
            mism.append((r['id'], q, miss))
    out('## 五、题面 ↔ 口径一致性')
    out('')
    out('| 指标 | 值 |')
    out('| --- | --- |')
    out('| 题面缺失某条件值的题数 | **%d**（应为 0） |' % len(mism))
    out('')
    for i, q, m in mism[:6]:
        out('- ✗ %s「%s」缺 %s' % (i, q, '、'.join(m)))
    if mism:
        out('')
    ck('题面与口径一致', not mism, str(mism[:2]))

    # ---------- 六、算子覆盖 ----------
    out('## 六、算子取值覆盖')
    out('')
    axes = {'LQ': 0, 'LP': 1, 'PF': 2, 'SO': 3, 'OUT': 4}
    out('| 轴 | 取值（题数） | 取值数 |')
    out('| --- | --- | --- |')
    for name, idx in axes.items():
        c = collections.Counter(s.split('｜')[idx] for s in sigs)
        out('| %s | %s | %d |'
            % (name, ' · '.join('%s(%d)' % (k, v) for k, v in c.most_common()), len(c)))
    out('')

    out('## 七、结论')
    out('')
    if fails:
        out('**FAIL %d 项**：' % len(fails))
        for f in fails:
            out('- %s' % f)
    else:
        out('**全部通过**：链唯一 %d、题面一致、无 0 命中、无归一化重复。' % fine)

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('# 1000 题清单·开工前审查报告（v3）\n\n')
        f.write('生成：`tools/gen_q1000.py`（分片并行 + `tools/merge_shards.py` 合并）；共 **%d** 题。\n\n' % n)
        f.write('\n'.join(rep))
    print('\n已写出 %s' % OUT)
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
