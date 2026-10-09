# -*- coding: utf-8 -*-
"""loop_check.py —— 把一条检查命令重复跑 N 遍，统计「通过率 / 耗时分布 / 首末差异」。

为什么单独做一层（主人的要求）：改一处就要跑十遍，全改完要跑上百遍；
手敲 for 循环既不能统计也不能留证，且 Windows 的 Git Bash 没有 bc 做计时运算。

用法：
    python tools/loop_check.py --cmd "python solve/selftest.py" --n 10
    python tools/loop_check.py --cmd "python solve/selftest.py" --n 100 --expect "失败 0"
    python tools/loop_check.py --self "python solve/selftest.py" --n 10      # 用当前解释器

要点：
  · `--expect` 给出必须出现在输出里的子串（默认「失败 0」），缺失即判该遍失败；
  · 每遍都记录耗时，最后给 最小值/中位数/最大值/标准差 与总耗时；
  · 退出码：0 = 全部遍通过；1 = 有失败遍（并打印其输出尾部）。
"""
import argparse
import statistics
import subprocess
import sys
import time


def main():
    ap = argparse.ArgumentParser(description='把一条检查重复跑 N 遍并统计')
    ap.add_argument('--cmd', required=True, help='要重复运行的命令')
    ap.add_argument('--n', type=int, default=10, help='重复遍数')
    ap.add_argument('--expect', default='失败 0', help='输出中必须出现的子串（判通过）')
    ap.add_argument('--tail', type=int, default=6, help='失败时打印输出尾部行数')
    ap.add_argument('--quiet', action='store_true', help='只打印汇总')
    ap.add_argument('--jobs', type=int, default=1,
                    help='并发进程数（本机 16 核；串行 1000 遍要 ~4 小时，12 并发约 20 分钟）')
    args = ap.parse_args()

    times, fails = [], []
    t_all = time.time()

    def once(i):
        t0 = time.time()
        r = subprocess.run(args.cmd, shell=True, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        dt = time.time() - t0
        out = (r.stdout or '') + (r.stderr or '')
        ok = (r.returncode == 0) and (args.expect in out)
        return (i, dt, ok, r.returncode, out)

    jobs = max(1, int(args.jobs))
    if jobs == 1:
        for i in range(1, args.n + 1):
            i, dt, ok, _rc, out = once(i)
            times.append(dt)
            if not ok:
                fails.append((i, _rc, out))
            if not args.quiet:
                print('第 %3d/%d 遍：%7.2f 秒  %s' % (i, args.n, dt, '通过' if ok else '★未通过'))
    else:
        # **并发**：每遍仍是独立的完整子进程（判据、遍数与串行完全一致），只是同时跑
        from concurrent.futures import ThreadPoolExecutor
        done = 0
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            for i, dt, ok, rc, out in ex.map(once, range(1, args.n + 1)):
                done += 1
                times.append(dt)
                if not ok:
                    fails.append((i, rc, out))
                if not args.quiet and (done % max(1, args.n // 10) == 0 or not ok):
                    print('  已完成 %d/%d（本遍 %.2f 秒，%s）'
                          % (done, args.n, dt, '通过' if ok else '★未通过'))

    print()
    print('=' * 68)
    print('重复 %d 遍（并发 %d）：通过 %d，失败 %d'
          % (args.n, max(1, int(args.jobs)), args.n - len(fails), len(fails)))
    if times:
        print('单遍耗时：最小 %.2f / 中位 %.2f / 最大 %.2f 秒（标准差 %.2f）'
              % (min(times), statistics.median(times), max(times),
                 statistics.stdev(times) if len(times) > 1 else 0.0))
        print('总耗时：%.1f 秒（墙钟；并发 %d，单遍中位 %.2f 秒）'
              % (time.time() - t_all, max(1, int(args.jobs)), statistics.median(times)))
        print('折算串行耗时：约 %.1f 秒' % (sum(times)))
    for i, rc, out in fails[:3]:
        print('--- 第 %d 遍失败（exit=%s）输出尾部 ---' % (i, rc))
        for line in out.strip().splitlines()[-args.tail:]:
            print('    ' + line)
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
