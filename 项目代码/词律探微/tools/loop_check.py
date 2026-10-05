# -*- coding: utf-8 -*-
"""loop_check.py —— 把一条检查命令重复跑 N 遍，统计「通过率 / 耗时分布 / 首末差异 / 代码树冻结」。

为什么单独做一层（主人的要求）：改一处就要跑十遍，全改完要跑上百遍；
手敲 for 循环既不能统计也不能留证，且 Windows 的 Git Bash 没有 bc 做计时运算。

用法：
    python tools/loop_check.py --cmd "python solve/selftest.py" --n 10
    python tools/loop_check.py --cmd "python solve/selftest.py" --n 100 --expect "失败 0"
    python tools/loop_check.py --self "python solve/selftest.py" --n 10      # 用当前解释器
    python tools/loop_check.py --cmd "python solve/selftest.py" --n 1000 --jobs 8 \
        --quiet --freeze solve,tools --progress prog.txt

要点：
  · `--expect` 给出必须出现在输出里的子串（默认「失败 0」），缺失即判该遍失败；
  · 每遍都记录耗时，最后给 最小值/中位数/最大值/标准差 与总耗时；
  · `--jobs N`（N≥2）并发跑：每遍仍是**独立进程、独立判定**，
    只是把「等 I/O」的墙钟叠起来——自检是纯只读的（2026-10-01 实测 8 并发全过），
    所以并发不改变判定，只压缩总时长；并发时耗时统计按「完成时刻」记（吞吐口径）。
  · `--progress 文件`：每完成一遍就**覆盖写一行**「已完成 x/N 遍；失败 n；累计墙钟 …；指纹 …」，
    长跑（几百上千遍）时无需等待即可 cat 该文件查看进度。
  · **`--freeze 目录1,目录2`（本轮新增，重要）**：开始前对受控文件算指纹，全部跑完后重算；
    若源码在自检期间被改动 → 打印 ★「本次判定作废」并**退出码 2**。
    起因：2026-10-01 深夜一次 1000 遍里，**另一个 agent 会话在同一个目录改写 solve/**，
    于是 4 遍赶上了「调用方已传 context=、被调方还没加该参数」的 13 秒窗口而报 TypeError。
    没有这道护栏，「测试跑在会被改写的代码树上」这件事**不会被发现**——
    更糟的是它也可能给出**假通过**（改了代码但恰好都过）。
  · 末尾做一次「首末差异」：忽略耗时行后，首遍与末遍输出应逐字一致（确定性纪律）。
  · 退出码：0 = 全部遍通过且（若开启 freeze）代码树未变；1 = 有失败遍；2 = 代码树被改动（判定作废）。
"""
import argparse
import hashlib
import os
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

SKIP_DIRS = {'__pycache__', 'node_modules', '.git', '_历史产物', '_自检快照'}
HASH_EXTS = {'.py', '.js', '.json', '.jsonl', '.html', '.htm', '.css', '.sql', '.md', '.txt',
             '.yml', '.yaml', '.csv', '.tsv'}
# ⚠ 2026-10-04 修（代码审查 P2-15）：旧集合只含 `.json`，**漏了 `.jsonl`**——
#   题库 `data/questions_1000.jsonl`、参考答案 `answers_700.jsonl`、网页冻结参考
#   `web_ref_1000.jsonl` 全是 .jsonl，本该受冻结的输入文件在自检期间被改写**不会被发现**。
DB_EXTS = {'.db', '.sqlite', '.sqlite3'}
BIG = 4 * 1024 * 1024          # >4MB 的文件不逐字节哈希，改记「大小+mtime_ns」（足够发现改动）


def run_one(i, cmd, expect):
    t0 = time.time()
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    dt = time.time() - t0
    out = (r.stdout or '') + (r.stderr or '')
    ok = (r.returncode == 0) and (expect in out)
    return i, dt, ok, out


def _file_digest(fp):
    try:
        st = os.stat(fp)
    except OSError:
        return None
    if st.st_size <= BIG:
        h = hashlib.sha256()
        try:
            with open(fp, 'rb') as f:
                for chunk in iter(lambda: f.read(1 << 16), b''):
                    h.update(chunk)
            return 'h:' + h.hexdigest()
        except OSError:
            return None
    return 'm:%d:%d' % (st.st_size, st.st_mtime_ns)


def _manifest(paths):
    """受控文件 → 摘要。目录递归；代码类逐字节哈希，数据库类记大小+mtime。"""
    m = {}
    for root in paths:
        root = root.strip()
        if not root:
            continue
        if os.path.isfile(root):
            d = _file_digest(root)
            if d is not None:
                m[os.path.abspath(root)] = d
            continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in HASH_EXTS and ext not in DB_EXTS:
                    continue
                d = _file_digest(os.path.join(dp, fn))
                if d is not None:
                    m[os.path.abspath(os.path.join(dp, fn))] = d
    return m


def _fingerprint(m):
    h = hashlib.sha256()
    for k in sorted(m):
        h.update(os.path.basename(k).encode('utf-8', 'replace'))
        h.update(b'=')
        h.update(m[k].encode())
        h.update(b'\n')
    return h.hexdigest()[:16]


def _norm(out):
    """去掉含耗时/秒数的行，便于首末逐字比对（这些行天然每次不同）。"""
    return '\n'.join(ln for ln in out.splitlines()
                     if ('秒' not in ln) and ('耗时' not in ln))


def _write_progress(path, done, n, nfail, t0, last_dt, fp=None):
    """覆盖写一行进度（cat 即最新态）。任何写入异常都吞掉，绝不影响自检判定。"""
    if not path:
        return
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('已完成 %d/%d 遍；失败 %d；累计墙钟 %.1f 秒；最近一遍 %.2f 秒%s\n'
                    % (done, n, nfail, time.time() - t0, last_dt,
                       ('；代码指纹 %s' % fp) if fp else ''))
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description='把一条检查重复跑 N 遍并统计')
    ap.add_argument('--cmd', required=True, help='要重复运行的命令')
    ap.add_argument('--n', type=int, default=10, help='重复遍数')
    ap.add_argument('--progress', default=None,
                    help='进度文件路径：每完成一遍就覆盖写一行「已完成/总数 失败数 累计耗时 指纹」，'
                         '便于长跑时随时 cat 查看（--quiet 模式强烈建议配它）')
    ap.add_argument('--freeze', default=None,
                    help='逗号分隔的目录/文件：全程监控其摘要，若自检期间被改动则判定作废（退出码 2）')
    ap.add_argument('--jobs', type=int, default=1, help='并发进程数（默认 1＝串行；≥2 为并发）')
    ap.add_argument('--expect', default='失败 0', help='输出中必须出现的子串（判通过）')
    ap.add_argument('--tail', type=int, default=6, help='失败时打印输出尾部行数')
    ap.add_argument('--quiet', action='store_true', help='只打印汇总')
    args = ap.parse_args()

    freeze_paths = [p for p in (args.freeze or '').split(',') if p.strip()]
    man0 = _manifest(freeze_paths) if freeze_paths else None
    fp0 = _fingerprint(man0) if man0 is not None else None
    if fp0:
        print('代码树冻结基线：指纹 %s（受控文件 %d 个；目录 %s）'
              % (fp0, len(man0), ','.join(freeze_paths)))

    times, fails, outs = [], [], []
    t_all = time.time()
    _write_progress(args.progress, 0, args.n, 0, t_all, 0.0, fp0)

    if args.jobs <= 1:
        for i in range(1, args.n + 1):
            i, dt, ok, out = run_one(i, args.cmd, args.expect)
            times.append(dt)
            outs.append((i, out))
            if not ok:
                fails.append((i, out))
            _write_progress(args.progress, len(times), args.n, len(fails), t_all, dt, fp0)
            if not args.quiet:
                print('第 %3d/%d 遍：%7.2f 秒  %s' % (i, args.n, dt, '通过' if ok else '★未通过'))
                sys.stdout.flush()
    else:
        # 并发：每遍独立进程、独立判定；用 as_completed 保证进度按「真实完成」递增
        done = 0
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = [ex.submit(run_one, i, args.cmd, args.expect) for i in range(1, args.n + 1)]
            for fut in as_completed(futs):
                i, dt, ok, out = fut.result()
                times.append(dt)
                outs.append((i, out))
                done += 1
                if not ok:
                    fails.append((i, out))
                _write_progress(args.progress, done, args.n, len(fails), t_all, dt, fp0)
                if not args.quiet and (done % max(1, args.n // 20) == 0 or not ok):
                    print('已完成 %4d/%d 遍（并发 %d）…… %s'
                          % (done, args.n, args.jobs, '' if ok else '★有未通过'))
                    sys.stdout.flush()

    print()
    print('=' * 68)
    print('重复 %d 遍：通过 %d，失败 %d%s'
          % (args.n, args.n - len(fails), len(fails),
             ('（并发 %d 份）' % args.jobs) if args.jobs > 1 else ''))
    if times:
        print('单遍耗时：最小 %.2f / 中位 %.2f / 最大 %.2f 秒（标准差 %.2f）'
              % (min(times), statistics.median(times), max(times),
                 statistics.stdev(times) if len(times) > 1 else 0.0))
        print('总耗时：%.1f 秒（含进程启动开销%s）'
              % (time.time() - t_all,
                 '；并发下为吞吐口径' if args.jobs > 1 else ''))

    # 首末差异：同一命令两遍应给出逐字一致的结论（忽略耗时行）——确定性纪律
    outs.sort(key=lambda t: t[0])
    if len(outs) >= 2:
        a, b = _norm(outs[0][1]), _norm(outs[-1][1])
        if a == b:
            print('首末一致性：第 1 遍与第 %d 遍输出逐字一致（已忽略耗时行）✔' % outs[-1][0])
        else:
            la, lb = a.splitlines(), b.splitlines()
            j = next((k for k in range(min(len(la), len(lb))) if la[k] != lb[k]),
                     min(len(la), len(lb)))
            print('★首末一致性：两遍输出存在差异 —— 自第 %d 行起不同' % (j + 1))
            print('    首遍：' + (la[j] if j < len(la) else '<无>'))
            print('    末遍：' + (lb[j] if j < len(lb) else '<无>'))

    # 代码树冻结校验：源码在自检期间被改动 → 结果不可信
    tainted = False
    if man0 is not None:
        man1 = _manifest(freeze_paths)
        fp1 = _fingerprint(man1)
        if fp1 == fp0:
            print('代码树冻结校验：%d 个受控文件全程未变（指纹 %s）✔' % (len(man0), fp0))
        else:
            tainted = True
            changed = [k for k in man1 if k in man0 and man0[k] != man1[k]]
            removed = [k for k in man0 if k not in man1]
            added = [k for k in man1 if k not in man0]
            print('★代码树冻结校验：自检期间源码被改动，本次判定作废！')
            print('    基线指纹 %s → 结束指纹 %s' % (fp0, fp1))
            for k in (changed + removed)[:5]:
                print('    改/删：' + k)
            for k in added[:5]:
                print('    新增：' + k)
            print('    处置：确认写者已停止后，重新跑一遍；否则本批数字不得引用。')

    _write_progress(args.progress, args.n, args.n, len(fails), t_all,
                    times[-1] if times else 0.0, fp0)

    for i, out in fails[:3]:
        print('--- 第 %d 遍失败输出尾部 ---' % i)
        for line in out.strip().splitlines()[-args.tail:]:
            print('    ' + line)
    if tainted:
        return 2
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
