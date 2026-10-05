# -*- coding: utf-8 -*-
"""校订回流（M11 闭环）：把「工单裁定」真正接回引擎，并**先算分再决定要不要采纳**。

闭环四步：
    裁定表（CSV） → 生成候选覆写表 → 用候选表复算两套答案 → 与门禁期望分数/哈希比对 → 决定采纳或打回

纪律（硬约束）：
  - **不改语料、不改交付答案**：候选表只写 `data/candidate_overrides.json`；
    要升为交付表必须显式 `--promote`，且**两套题的逐题零回归 + 总分不降**同时满足才允许。
  - 保密集只在这条链的验收环节跑，并记录用途；第二套路径**不预置**，须由使用者显式传入。
  - 每次裁定都必须有依据（`依据` 列非空），否则跳过并计入「无依据裁定」。

⚠️ **本候选表是「全局字级近似模型」**：覆写表以「字」为键、全局生效，
   同一字在**全库所有出现位置**都会被改成同一调类，**无法表达上下文多音字**
   （如某字作动词读仄、作名词读平）。因此凡涉及上下文多音字的裁定，
   不能只依赖本表得出结论，必须在报告里显式声明这一局限。
   同理，若同一字被裁定出**互相冲突**的目标调类，工具会打印 `CONFLICT` 并拒绝继续。

裁定表列（`data/review_decisions.csv`）：
    pid,阕,句内位,字,引擎调,语料调,裁定,依据,状态
      裁定 ∈ {引擎, 语料, 存疑}；状态 ∈ {待裁定, 已裁定}

用法：
  python tools/review_apply.py --decisions data/review_decisions.csv --dry-run
  python tools/review_apply.py --decisions data/review_decisions.csv            # 写候选表并复算
  python tools/review_apply.py --decisions data/review_decisions.csv --promote  # 升为交付表
  python tools/review_apply.py --decisions data/review_decisions.csv \
      --questions2 <第二套题面> --gold2 <第二套答案>                            # 两套同时验收
"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'solve'))

DELIVERY = os.path.join(ROOT, 'solve', 'data', 'pron_overrides.json')
CANDIDATE = os.path.join(ROOT, 'data', 'candidate_overrides.json')
CORPUS_DEFAULT = r'D:\桌面\人文薪火\数据\语料'

# 全库通用声明（写入 stdout，提示覆写表的口径局限）
GLOBAL_MODEL_NOTICE = (
    '⚠️ 说明：本候选覆写表是**全局字级近似模型**——同字全局生效，'
    '无法表达上下文多音字（同一字不同上下文读不同调）。'
    '涉及上下文多音字的裁定不能只靠本表，须在报告中显式声明该局限。')


def sha(path):
    return hashlib.sha256(io.open(path, 'rb').read()).hexdigest().upper() if os.path.exists(path) else ''


def load_decisions(path):
    """读裁定表：返回 (可采纳行, 跳过行)。每行附内部字段 `_lineno`（CSV 原始行号，从 2 起）。"""
    rows = list(csv.DictReader(io.open(path, encoding='utf-8-sig')))
    ok, skipped = [], []
    for i, r in enumerate(rows, start=2):
        r['_lineno'] = i
        if (r.get('裁定') or '').strip() in ('引擎', '', '存疑') or (r.get('状态') or '').strip() == '待裁定':
            continue
        if not (r.get('依据') or '').strip():
            skipped.append((r, '裁定无依据'))
            continue
        ok.append(r)
    return ok, skipped


def build_candidate(decisions, base_path):
    """按裁定生成候选覆写表：裁定=语料 时，把该字的调类设为语料标注的调类。

    返回 (候选覆写表, 变更明细, 冲突字典)。冲突 = 同一字被裁定成**不同目标调类**
    （「后覆盖前」会静默丢信息，故先收集再拒绝，不继续）。
    """
    base = json.load(io.open(base_path, encoding='utf-8-sig')) if os.path.exists(base_path) else {}
    ov = dict(base)

    # —— 第一步：收集「同一字 + 不同 target tone」的冲突集合
    per_zi = {}                       # 字 -> [(tone, pid, 依据, 行号), ...]
    for r in decisions:
        zi = (r.get('字') or '').strip()
        ct = (r.get('语料调') or '').strip()
        if not zi or not ct.isdigit():
            continue
        per_zi.setdefault(zi, []).append((int(ct), r.get('pid', ''),
                                          r.get('依据', ''), r.get('_lineno', '')))
    conflicts = {}
    for zi, items in per_zi.items():
        if len({t for t, _, _, _ in items}) > 1:
            conflicts[zi] = items

    # —— 第二步：无冲突才按行生成覆写表
    changed = []
    for r in decisions:
        zi = (r.get('字') or '').strip()
        ct = (r.get('语料调') or '').strip()
        if not zi or not ct.isdigit():
            continue
        tone = int(ct)
        if ov.get(zi) != tone:
            ov[zi] = tone
            changed.append((zi, tone, r.get('依据', '')))
    return ov, changed, conflicts


def recompute(tag, questions, gold, out, overrides, corpus):
    """用指定覆写表复算一套答案并评测。返回 (一致数, 总数, 报告文本, 答案文件路径)。"""
    py = sys.executable
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    r1 = subprocess.run([py, os.path.join(ROOT, 'solve', 'solver.py'), '--question', questions,
                         '--corpus', corpus, '--output', out, '--overrides', overrides],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    if r1.returncode != 0:
        return None, None, (r1.stdout or '') + (r1.stderr or ''), out
    r2 = subprocess.run([py, os.path.join(ROOT, 'solve', 'eval.py'), '--pred', out,
                         '--gold', gold], capture_output=True, text=True, encoding='utf-8',
                        errors='replace', env=env)
    txt = r2.stdout or ''
    hit = total = 0
    for ln in txt.splitlines():
        if ln.startswith('合计'):
            parts = ln.split()
            # ⚠ 2026-10-04 修：eval.py 的「合计」行列序是 (合计, 题数, 一致数, …)，
            #   旧版写成 `hit, total = parts[1], parts[2]` —— 把两个数**取反**，
            #   于是下面 `cand_hit < base_hit` 比的是两次的**题数**（恒等），
            #   门禁永远不触发，「掉分即打回」形同虚设（代码审查 P0-1）。
            total, hit = int(parts[1]), int(parts[2])
    return hit, total, txt, out


def _load_answers(path):
    d = {}
    for l in io.open(path, encoding='utf-8-sig'):
        if l.strip():
            r = json.loads(l)
            d[r.get('题号')] = r
    return d


def per_question_regression(base_out, cand_out, gold_path):
    """逐题比对基线答案与候选答案（T2：不允许 A 题 +1 / B 题 −1 相互抵消）。

    判据：**基线原本正确的题**，在候选里必须
      ① 仍判为正确，且 ② `答案` 字段逐字节/逐值完全相同；
    只要有一条不满足，即记为「回归题」并拒绝晋升。
    返回 (回归明细列表, 基线正确题数)。
    """
    import eval as ev
    gold = {}
    for l in io.open(gold_path, encoding='utf-8-sig'):
        if l.strip():
            q = json.loads(l)
            if q.get('题号'):
                gold[q['题号']] = q
    base = _load_answers(base_out)
    cand = _load_answers(cand_out)
    bad, n_base_ok = [], 0
    for pid, br in base.items():
        gq = gold.get(pid)
        if gq is None:
            continue
        cls = br.get('类别')
        bans = br.get('答案') or {}
        if not bans:
            continue                       # 基线未命中 → 不算「原本正确」
        g = ev.parse_gold(cls, gq.get('标准答案', ''))
        b_ok, _ = ev.compare(cls, bans, g)
        if not b_ok:
            continue                       # 基线本身就错 → 候选怎么改都不算回归
        n_base_ok += 1
        cr = cand.get(pid)
        cans = (cr or {}).get('答案') or {}
        if cans != bans:
            bad.append('%s（答案字段变化）' % pid)
            continue
        c_ok, _ = ev.compare(cls, cans, g)
        if not c_ok:
            bad.append('%s（基线正确→候选判错）' % pid)
    return bad, n_base_ok


def evaluate_dataset(label, questions, gold, corpus, base_out, cand_out, delivery, candidate):
    """对一套题跑 base/cand 复算，并做逐题零回归比对。

    返回 dict：{'ok': 是否满足门禁, 'reason': 失败原因, 以及 'base_hit'/'cand_hit' 等}。
    """
    base_hit, base_tot, base_txt, _ = recompute('base', questions, gold, base_out, delivery, corpus)
    cand_hit, cand_tot, cand_txt, _ = recompute('cand', questions, gold, cand_out, candidate, corpus)
    res = {'label': label, 'base_hit': base_hit, 'base_tot': base_tot,
           'cand_hit': cand_hit, 'cand_tot': cand_tot, 'ok': False, 'reason': ''}
    if base_hit is None or cand_hit is None:
        res['reason'] = '复算失败：%s' % (cand_txt or base_txt)[:400]
        print('复算（%s）：❌ 失败' % label)
        return res
    print('复算（%s）：交付表 %s/%s → 候选表 %s/%s' % (label, base_hit, base_tot, cand_hit, cand_tot))

    bad, n_base_ok = per_question_regression(base_out, cand_out, gold)
    res['regressions'] = bad
    res['n_base_ok'] = n_base_ok
    if bad:
        shown = bad[:20]
        res['reason'] = ('逐题零回归未通过：%d 道原本正确的题发生变化（共 %d 道基线正确）'
                         % (len(bad), n_base_ok))
        print('  ❌ %s' % res['reason'])
        for x in shown:
            print('     - 回归题 %s' % x)
        if len(bad) > len(shown):
            print('     … 其余 %d 道略' % (len(bad) - len(shown)))
        return res
    print('  ✅ 逐题零回归通过（基线正确 %d 道，答案逐字段未变）' % n_base_ok)

    if cand_hit < base_hit:
        res['reason'] = '总分下降（%d < %d）→ 打回' % (cand_hit, base_hit)
        print('  ❌ %s' % res['reason'])
        return res
    print('  ✅ 总分不降（%d ≥ %d）' % (cand_hit, base_hit))
    res['ok'] = True
    return res


def main():
    ap = argparse.ArgumentParser(description='校订回流（生成候选覆写表 → 复算 → 决定采纳）')
    ap.add_argument('--decisions', required=True)
    # T5：语料路径改为「环境变量优先 → 本机默认兜底」
    ap.add_argument('--corpus', default=os.environ.get('LVC_CORPUS') or CORPUS_DEFAULT,
                    help='语料根（默认取环境变量 LVC_CORPUS，缺省用本机默认路径）')
    ap.add_argument('--questions', default=r'D:\桌面\人文薪火\数据\初赛数据'
                                          r'\薪火人文-清词-1000题库-V5版本\公开测试集_700题.jsonl')
    ap.add_argument('--questions2', default='',
                    help='第二套题面（**不预置路径**：按「不得默认读取保密数据」的纪律，'
                         '需要时由使用者显式传入）')
    ap.add_argument('--gold', default=r'D:\桌面\人文薪火\数据\初赛数据'
                                     r'\薪火人文-清词-1000题库-V5版本\公开测试集_700题.jsonl')
    ap.add_argument('--gold2', default='',
                    help='第二套答案（同为不预置；终检时由使用者显式传入）')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--promote', action='store_true', help='升为交付覆写表（需两套均零回归且不降分）')
    args = ap.parse_args()

    print(GLOBAL_MODEL_NOTICE)

    dec, skipped = load_decisions(args.decisions)
    print('裁定表：可采纳 %d 条，跳过 %d 条（无依据/未裁定）' % (len(dec), len(skipped)))
    for r, why in skipped[:5]:
        print('  跳过 %s %s：%s' % (r.get('pid', ''), r.get('字', ''), why))
    ov, changed, conflicts = build_candidate(dec, DELIVERY)

    # T3：同字冲突 → 打印 CONFLICT 并拒绝继续（不写候选表）
    if conflicts:
        print('❌ CONFLICT：同一字被裁定出互相冲突的目标调类（后覆盖前会静默丢信息，故拒绝继续）：')
        for zi, items in sorted(conflicts.items()):
            vals = sorted({t for t, _, _, _ in items})
            print('  字「%s」目标调类 %s：' % (zi, vals))
            for t, pid, basis, lineno in items:
                print('     调类 %d ← 行 %s pid=%s 依据=%s' % (t, lineno, pid, basis))
        return 3

    print('候选覆写表：交付表 %d 字 → 候选表 %d 字；变更 %s'
          % (len(json.load(io.open(DELIVERY, encoding='utf-8-sig'))), len(ov), changed or '无'))
    if args.dry_run:
        print('（--dry-run：只算不写）')
        return 0
    tmp = CANDIDATE
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    io.open(tmp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(ov, ensure_ascii=False, indent=1))
    print('已写候选表：%s（sha256 %s）' % (tmp, sha(tmp)[:16]))

    # 两套题各自复算；晋升要求「两套同时满足」（零回归 + 不降分）
    datasets = [('公开集', args.questions, args.gold,
                 os.path.join(ROOT, 'data', '_recompute_base.jsonl'),
                 os.path.join(ROOT, 'data', '_recompute_cand.jsonl'))]
    if args.questions2 and args.gold2:
        datasets.append(('第二套', args.questions2, args.gold2,
                         os.path.join(ROOT, 'data', '_recompute_base2.jsonl'),
                         os.path.join(ROOT, 'data', '_recompute_cand2.jsonl')))
    else:
        print('（未同时提供 --questions2 与 --gold2：本次只验收公开集）')

    results = []
    for label, q, g, b_out, c_out in datasets:
        results.append(evaluate_dataset(label, q, g, args.corpus, b_out, c_out, DELIVERY, tmp))

    failed = [r for r in results if not r['ok']]
    if failed:
        for r in failed:
            print('❌ %s 未过门禁：%s' % (r['label'], r['reason']))
        print('❌ 候选表不予采纳')
        return 1
    print('✅ 全部 %d 套题均通过（逐题零回归 + 总分不降）' % len(results))

    if args.promote:
        # T4：原子写 —— 先写 .tmp → flush + fsync → os.replace，备份保留原表
        bak = DELIVERY + '.bak'
        shutil.copy2(DELIVERY, bak)
        dest_tmp = DELIVERY + '.tmp'
        with io.open(dest_tmp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(ov, ensure_ascii=False, indent=1))
            f.flush()
            os.fsync(f.fileno())
        os.replace(dest_tmp, DELIVERY)
        print('已升为交付表（原子写：%s → %s；原表备份 %s）'
              % (os.path.basename(dest_tmp), os.path.basename(DELIVERY), os.path.basename(bak)))
        print('⚠️ 升表后必须重跑：selftest / regress / preflight，并更新 data/golden_sha.json')
    else:
        print('（未加 --promote：交付表保持不变）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
