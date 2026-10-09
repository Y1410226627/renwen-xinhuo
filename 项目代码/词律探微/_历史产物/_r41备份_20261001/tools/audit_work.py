# -*- coding: utf-8 -*-
"""audit_work.py —— 用**不受机器负载影响**的口径度量一次运行做了多少活。

为什么需要（2026-10-01 实测教训）：这台机器上同时跑着别的重活时，同一个版本的墙钟在
1.5 倍范围内抖动（selftest 单遍 7.4s~15.2s、/api/search 460ms~1557ms），
**用时间做优化指引会把人带到沟里**。稳定的口径是「工作量」：
    · SQL 语句条数
    · 从 SQLite 取回的行数 —— 最贴近实际 I/O 与计算量
这些数在同一份数据上**逐次完全一致**，可以直接用来证明「这次改动真的少干活了」。

实现：用代理对象包住 `sqlite3.Connection/Cursor`（C 类型不可打补丁，只能代理），
统计 execute/executemany/executescript 的条数，以及 fetchall/fetchone/fetchmany/**迭代**的行数。

用法：
    python tools/audit_work.py --cmd "python solve/selftest.py"
    python tools/audit_work.py --cmd "…" --save data/work_baseline.json
    python tools/audit_work.py --cmd "…" --baseline data/work_baseline.json   # 回归护栏
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

WRAPPER = "\n".join([
    "import collections, json, os, sqlite3, sys",
    "STATS = collections.Counter()",
    "",
    "class CurProxy:",
    "    __slots__ = ('_c', '_key')",
    "    def __init__(self, cur):",
    "        object.__setattr__(self, '_c', cur)",
    "    def fetchall(self):",
    "        r = self._c.fetchall(); STATS['rows'] += len(r)",
    "        k = getattr(self, '_key', '')",
    "        if k: STATS['r::' + k] += len(r)",
    "        return r",
    "    def fetchone(self):",
    "        r = self._c.fetchone(); STATS['rows'] += 1 if r is not None else 0; return r",
    "    def fetchmany(self, n=1):",
    "        r = self._c.fetchmany(n); STATS['rows'] += len(r); return r",
    "    def __iter__(self):",
    "        k = getattr(self, '_key', '')",
    "        for row in self._c:",
    "            STATS['rows'] += 1",
    "            if k: STATS['r::' + k] += 1",
    "            yield row",
    "    def __getattr__(self, k):",
    "        return getattr(self._c, k)",
    "",
    "class ConnProxy:",
    "    def __init__(self, conn):",
    "        object.__setattr__(self, '_c', conn)",
    "    def execute(self, sql, *a):",
    "        STATS['sql'] += 1",
    "        k = ' '.join(sql.split())[:64]",
    "        STATS['k::' + k] += 1",
    "        cur = CurProxy(self._c.execute(sql, *a))",
    "        cur._key = k",
    "        return cur",
    "    def executemany(self, sql, seq):",
    "        STATS['sql'] += 1",
    "        return CurProxy(self._c.executemany(sql, seq))",
    "    def executescript(self, sql):",
    "        STATS['sql'] += 1",
    "        return CurProxy(self._c.executescript(sql))",
    "    def cursor(self, *a, **kw):",
    "        return CurProxy(self._c.cursor(*a, **kw))",
    "    def __setattr__(self, k, v):",
    "        setattr(self._c, k, v)",
    "    def __getattr__(self, k):",
    "        return getattr(self._c, k)",
    "",
    "_connect = sqlite3.connect",
    "sqlite3.connect = lambda *a, **kw: ConnProxy(_connect(*a, **kw))",
    "",
    "target = os.environ['AW_TARGET']",
    "args = os.environ.get('AW_ARGS', '')",
    "sys.argv = [target] + (args.split() if args else [])",
    "try:",
    "    code = open(target, encoding='utf-8').read()",
    "    try:",
    "        exec(compile(code, target, 'exec'), {'__name__': '__main__', '__file__': target})",
    "    except SystemExit:",
    "        pass",
    "except Exception as e:",
    "    STATS['error'] = 1",
    "    sys.stderr.write('%s: %s\\n' % (type(e).__name__, e))",
    "print(json.dumps({'sql': STATS['sql'], 'rows': STATS['rows'], 'error': STATS.get('error', 0),",
    "                  'by_sql': {k[3:]: v for k, v in STATS.items() if k.startswith('r::')}}))",
])


def main():
    ap = argparse.ArgumentParser(description='工作量口径度量（不受负载影响）')
    ap.add_argument('--cmd', required=True, help='要度量的命令（形如 "python xxx.py"）')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--baseline', default=None, help='基线 JSON：比对并报告增减')
    ap.add_argument('--save', default=None, help='把本次结果写入 JSON（建基线）')
    ap.add_argument('--top', type=int, default=0, help='按语句模式列出取回行数最多的前 N 条')
    args = ap.parse_args()

    m = re.match(r'\s*(\S+)\s+(.*)$', args.cmd.strip())
    if not m:
        print('命令至少要包含「解释器 + 脚本路径」')
        return 2
    interp, rest = m.group(1), m.group(2).strip().split()
    target = rest[0] if os.path.isabs(rest[0]) else os.path.join(ROOT, rest[0])
    if not os.path.exists(target):
        print('找不到脚本：%s' % target)
        return 2
    wrapper = os.path.join(HERE, '_audit_work_wrap.py')
    io.open(wrapper, 'w', encoding='utf-8', newline='\n').write(WRAPPER)
    env = dict(os.environ)
    env['AW_TARGET'] = target
    env['AW_ARGS'] = ' '.join(rest[1:])
    t0 = time.perf_counter()
    try:
        r = subprocess.run([interp, wrapper], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', env=env, cwd=ROOT)
    finally:
        if os.path.exists(wrapper):
            os.remove(wrapper)
    dt = time.perf_counter() - t0
    line = [l for l in (r.stdout or '').strip().splitlines() if l.startswith('{')]
    if not line:
        print('度量失败：\n%s\n%s' % ((r.stdout or '')[-600:], (r.stderr or '')[-600:]))
        return 1
    cur = json.loads(line[-1])
    out = {'cmd': args.cmd, 'sql': cur['sql'], 'rows': cur['rows'], 'error': cur['error'],
           'wall_ref_only': round(dt, 2), 'by_sql': cur.get('by_sql') or {}}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print('命令：%s' % args.cmd)
        print('  SQL 语句                      %8d 条' % out['sql'])
        print('  取回行数                      %8d 行   ← 主指标（同数据下逐次一致）' % out['rows'])
        print('  出错                          %8d' % out['error'])
        print('  墙钟（仅参考，受同机负载影响）    %.2f 秒' % out['wall_ref_only'])
    if args.top and out.get('by_sql'):
        print('\n取回行数 TOP %d（按语句模式聚合）：' % args.top)
        for k, v in sorted(out['by_sql'].items(), key=lambda kv: -kv[1])[:args.top]:
            print('  %9d 行  %s' % (v, k))
    if args.save:
        io.open(args.save, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(out, ensure_ascii=False, indent=1) + '\n')
        print('  已写入基线：%s' % args.save)
    if args.baseline and os.path.exists(args.baseline):
        base = json.load(io.open(args.baseline, encoding='utf-8'))
        print('\n与基线 %s 比对：' % os.path.basename(args.baseline))
        for k, label in (('sql', 'SQL 语句'), ('rows', '取回行数')):
            b, c = base.get(k, 0), out[k]
            d = c - b
            pct = (100.0 * d / b) if b else 0.0
            print('  %-8s 基线 %8d → 现在 %8d  （%+d，%+.1f%%）%s'
                  % (label, b, c, d, pct, '✓ 更省' if d < 0 else ('持平' if d == 0 else '★更多')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
