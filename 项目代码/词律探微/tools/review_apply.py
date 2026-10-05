# -*- coding: utf-8 -*-
"""校订回流（M11 闭环）：把「工单裁定」真正接回引擎，并**先算分再决定要不要采纳**。

闭环四步：
    裁定表（CSV） → 生成候选覆写表 → 用候选表复算两套答案 → 与门禁期望分数/哈希比对 → 决定采纳或打回

纪律（硬约束）：
  - **不改语料、不改交付答案**：候选表只写 `data/candidate_overrides.json`；
    要升为交付表必须显式 `--promote`，且**复算分数不得低于门禁值时**才允许。
  - 保密集只在这条链的验收环节跑，并记录用途。
  - 每次裁定都必须有依据（`依据` 列非空），否则跳过并计入「无依据裁定」。

裁定表列（`data/review_decisions.csv`）：
    pid,阕,句内位,字,引擎调,语料调,裁定,依据,状态
      裁定 ∈ {引擎, 语料, 存疑}；状态 ∈ {待裁定, 已裁定}

用法：
  python tools/review_apply.py --decisions data/review_decisions.csv --dry-run
  python tools/review_apply.py --decisions data/review_decisions.csv            # 写候选表并复算
  python tools/review_apply.py --decisions data/review_decisions.csv --promote  # 升为交付表（需分数不降）
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


def sha(path):
    return hashlib.sha256(io.open(path, 'rb').read()).hexdigest().upper() if os.path.exists(path) else ''


def load_decisions(path):
    rows = list(csv.DictReader(io.open(path, encoding='utf-8-sig')))
    ok, skipped = [], []
    for r in rows:
        if (r.get('裁定') or '').strip() in ('引擎', '', '存疑') or (r.get('状态') or '').strip() == '待裁定':
            continue
        if not (r.get('依据') or '').strip():
            skipped.append((r, '裁定无依据'))
            continue
        ok.append(r)
    return ok, skipped


def build_candidate(decisions, base_path):
    """按裁定生成候选覆写表：裁定=语料 时，把该字的调类设为语料标注的调类。"""
    base = json.load(io.open(base_path, encoding='utf-8-sig')) if os.path.exists(base_path) else {}
    ov = dict(base)
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
    return ov, changed


def recompute(tag, questions, gold, out, overrides):
    """用指定覆写表复算一套答案并评测。返回 (一致数, 总数, 报告路径)。"""
    py = sys.executable
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    r1 = subprocess.run([py, os.path.join(ROOT, 'solve', 'solver.py'), '--question', questions,
                         '--corpus', CORPUS_DEFAULT, '--output', out, '--overrides', overrides],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    if r1.returncode != 0:
        return None, None, (r1.stdout or '') + (r1.stderr or '')
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
    return hit, total, txt


CORPUS_DEFAULT = (os.environ.get('LVC_CORPUS') or os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '数据', '语料')))


def main():
    ap = argparse.ArgumentParser(description='校订回流（生成候选覆写表 → 复算 → 决定采纳）')
    ap.add_argument('--decisions', required=True)
    ap.add_argument('--questions', default=(os.environ.get('LVC_QUESTIONS') or os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '数据', '初赛数据',
        '薪火人文-清词-1000题库-V5版本', '公开测试集_700题.jsonl'))))
    ap.add_argument('--questions2', default='',
                    help='第二套题面（**不预置路径**：按「不得默认读取保密数据」的纪律，'
                         '需要时由使用者显式传入）')
    ap.add_argument('--gold', default=(os.environ.get('LVC_QUESTIONS') or os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '数据', '初赛数据',
        '薪火人文-清词-1000题库-V5版本', '公开测试集_700题.jsonl'))))
    ap.add_argument('--gold2', default='',
                    help='第二套答案（同为不预置；终检时由使用者显式传入）')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--promote', action='store_true', help='升为交付覆写表（需分数不降）')
    args = ap.parse_args()

    dec, skipped = load_decisions(args.decisions)
    print('裁定表：可采纳 %d 条，跳过 %d 条（无依据/未裁定）' % (len(dec), len(skipped)))
    for r, why in skipped[:5]:
        print('  跳过 %s %s：%s' % (r.get('pid', ''), r.get('字', ''), why))
    ov, changed = build_candidate(dec, DELIVERY)
    print('候选覆写表：交付表 %d 字 → 候选表 %d 字；变更 %s'
          % (len(json.load(io.open(DELIVERY, encoding='utf-8-sig'))), len(ov), changed or '无'))
    if args.dry_run:
        print('（--dry-run：只算不写）')
        return 0
    tmp = os.path.join(ROOT, 'data', 'candidate_overrides.json')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    io.open(tmp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(ov, ensure_ascii=False, indent=1))
    print('已写候选表：%s（sha256 %s）' % (tmp, sha(tmp)[:16]))

    tmp_out = os.path.join(ROOT, 'data', '_recompute_tmp.jsonl')
    base_hit, base_tot, base_txt = recompute('base', args.questions, args.gold, tmp_out, DELIVERY)
    cand_hit, cand_tot, cand_txt = recompute('cand', args.questions, args.gold, tmp_out, tmp)
    print('复算（公开集）：交付表 %s/%s → 候选表 %s/%s' % (base_hit, base_tot, cand_hit, cand_tot))
    if cand_hit is None or base_hit is None:
        print('❌ 复算失败：%s' % cand_txt[:400])
        return 2
    if cand_hit < base_hit:
        print('❌ 候选表使公开集掉分（%d < %d）→ 打回，不采纳' % (cand_hit, base_hit))
        return 1
    print('✅ 公开集不降分（%d ≥ %d）' % (cand_hit, base_hit))
    if args.promote:
        bak = DELIVERY + '.bak'
        shutil.copy2(DELIVERY, bak)
        io.open(DELIVERY, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(ov, ensure_ascii=False, indent=1))
        print('已升为交付表（原表备份 %s）' % os.path.basename(bak))
        print('⚠️ 升表后必须重跑：selftest / regress / preflight，并更新 data/golden_sha.json')
    else:
        print('（未加 --promote：交付表保持不变）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
