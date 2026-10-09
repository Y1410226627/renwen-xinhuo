# -*- coding: utf-8 -*-
"""fetch_vector_index.py —— 一键拿到**篇级向量索引**（免去重跑 2.6 万次嵌入）。

为什么需要它
    向量索引约 438 MB，虽已纳入 **Git LFS 随仓库分发**，但总有人没装 LFS 客户端、
    或用的是 `zip` 下载（拿到的只是 LFS 指针文件）。本脚本按**优先级**把索引准备好：

      1) `data/vector/manifest.json` 已存在且 `vector_index.available()` 为真 → 直接可用；
      2) 环境变量 `LVC_VECTOR_SRC` 指向一个含 `poem.index` 的目录（另一份副本 / 移动硬盘）
         → 校验指纹一致后复制；
      3) 同机器的**相邻副本**（如 `D:\桌面\人文薪火\项目代码\词律探微\data\vector`）→ 自动发现；
      4) 以上都不行 → 打印重建指引（`python build_vector_index.py --dynasty 清`，需嵌入端点）。

关键前提（为什么可以跨机复用）
    `manifest.json` 绑定的是**语料内容指纹**（篇数 / 句数 / 汉字总数 / 最大 pid），
    只要 `corpus.db` **内容相同**，索引就直接可用 —— 与机器、路径无关。

用法：
    python tools/fetch_vector_index.py            # 取索引（必要时复制）
    python tools/fetch_vector_index.py --check    # 只体检，不复制
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'solve'))
VDIR = os.path.join(ROOT, 'data', 'vector')
FILES = ('poem.index', 'poem_meta.jsonl', 'manifest.json')


def _ok(verbose=True):
    """当前 `data/vector/` 是否可用（复用 vector_index 的强校验）。"""
    try:
        import vector_index as VI
        ok = VI.available(force=True)
        if verbose:
            print('%s 索引可用性：%s%s' % ('✓' if ok else '✗', ok,
                                          ('（%s）' % VI.why()) if not ok else ''))
            if ok:
                i = VI.info()
                print('   模型=%s 维度=%s 篇级=%s 版本=%s 语料指纹=%s'
                      % (i.get('model'), i.get('dim'), i.get('loaded_poems'),
                         i.get('index_version'), i.get('corpus_sha')))
        return ok
    except Exception as e:                                       # noqa: BLE001
        if verbose:
            print('✗ 体检异常：%s: %s' % (type(e).__name__, e))
        return False


def _fingerprint():
    try:
        import vector_index as VI
        return VI.corpus_fingerprint()
    except Exception:                                            # noqa: BLE001
        return ''


def _candidates():
    out = []
    env = os.environ.get('LVC_VECTOR_SRC')
    if env:
        out.append(env)
        out.append(os.path.join(env, 'data', 'vector'))
    # 相邻副本：把路径里的仓库名做有限替换
    parent = os.path.dirname(ROOT)                 # …/项目代码
    grand = os.path.dirname(parent)                # …/<仓库名>
    for sib in ('人文薪火', '人文薪火-开源版', 'renwen-xinhuo'):
        out.append(os.path.join(os.path.dirname(grand), sib, '项目代码', '词律探微', 'data', 'vector'))
    return [p for p in out if p and os.path.isdir(p)]


def main():
    ap = argparse.ArgumentParser(description='一键获取篇级向量索引（跨机复用，免重建）')
    ap.add_argument('--check', action='store_true', help='只体检，不复制')
    a = ap.parse_args()

    print('本机语料指纹：%s' % _fingerprint())
    if _ok():
        return 0
    if a.check:
        return 1

    for src in _candidates():
        mf = os.path.join(src, 'manifest.json')
        if not os.path.exists(os.path.join(src, 'poem.index')) or not os.path.exists(mf):
            continue
        try:
            src_sha = json.load(open(mf, encoding='utf-8')).get('corpus_sha')
        except Exception:                                        # noqa: BLE001
            continue
        if src_sha and src_sha != _fingerprint():
            print('跳过 %s（指纹不符：%s ≠ %s）' % (src, src_sha, _fingerprint()))
            continue
        print('从 %s 复制……' % src)
        os.makedirs(VDIR, exist_ok=True)
        for n in FILES:
            if os.path.exists(os.path.join(src, n)):
                shutil.copy2(os.path.join(src, n), os.path.join(VDIR, n))
        print('复制完成，复核：')
        if _ok():
            print('✅ 索引就绪。启动服务时设 `LVC_VECTOR=1` 即启用语义检索。')
            return 0
        print('✗ 复制后仍不可用，请检查上面的原因。')

    print('\n未能自动取得索引。请二选一：')
    print('  A) 装 Git LFS 后重新 clone（索引随仓库分发）：'
          '\n       git lfs install && git clone <仓库地址>')
    print('  B) 用嵌入端点重建（本机需能访问嵌入网关）：')
    print('       python build_vector_index.py --dynasty 清')
    print('     或把别处的 data/vector 目录指给本脚本：')
    print('       set LVC_VECTOR_SRC=<含 poem.index 的目录> && python tools/fetch_vector_index.py')
    return 1


if __name__ == '__main__':
    sys.exit(main())
