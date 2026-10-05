# -*- coding: utf-8 -*-
"""带备份的安全追加（专治「读写同一路径」这类事故）。

教训（2026-09-30，真实发生）：有人把追加写成
    io.open(p,'w').write(io.open(p, encoding='utf-8').read() + 新增段)
`open(p,'w')` 先把文件**截断**，内层 read 于是读到空 → 整份文档只剩新增段。
正确做法：**先读进变量，再写**；并且写之前先备份。

用法：
    python tools/append_md.py <目标文件> <要追加的文本文件|-> [--backup-dir <目录>]
    python tools/append_md.py solve/README.md new_section.md
"""
import argparse
import io
import os
import shutil
import sys
import time


def append(path, text, backup_dir=None):
    old = ''
    if os.path.exists(path):
        with io.open(path, encoding='utf-8') as f:      # 先读完（不提前打开写句柄）
            old = f.read()
    if backup_dir and old:
        os.makedirs(backup_dir, exist_ok=True)
        stamp = time.strftime('%Y%m%d_%H%M%S')
        dst = os.path.join(backup_dir, '%s.bak.%s' % (os.path.basename(path), stamp))
        shutil.copy2(path, dst)
        print('已备份 → %s' % dst)
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(old.rstrip() + text)
    os.replace(tmp, path)                                # 原子替换，断电也不会写半个文件
    return len(old), len(old.rstrip() + text)


def main():
    ap = argparse.ArgumentParser(description='安全追加（先读→备份→原子写）')
    ap.add_argument('path')
    ap.add_argument('text_file', help='要追加的文本文件；- 表示从标准输入读')
    ap.add_argument('--backup-dir', default=None)
    a = ap.parse_args()
    if a.text_file == '-':
        text = sys.stdin.read()
    else:
        with io.open(a.text_file, encoding='utf-8') as f:
            text = f.read()
    if text and not text.startswith('\n'):
        text = '\n\n' + text
    n0, n1 = append(a.path, text, a.backup_dir)
    print('%s：%d → %d 字符' % (a.path, n0, n1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
