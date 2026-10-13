# -*- coding: utf-8 -*-
"""_sem_probe.py —— 跨朝代语义问答实测（二期能力增补 ② 的效果验证）。

一次性探针（不入库、不进 selftest），用于人工核对：
  · 主题问（清/宋/元）：是否走向量主导、首位是否切题；
  · 相似问（仿照句式）：是否被 similar_ask 接管、是否过护栏；
  · 正式条件问：**不得**被语义意图误吞（回归防线）。
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'solve'))

import ask                      # noqa: E402
import similar_ask as SA        # noqa: E402
import vector_index as VI       # noqa: E402


def main():
    conn = sqlite3.connect(os.path.join(ROOT, 'data', 'corpus.db'))
    conn.row_factory = sqlite3.Row
    print('向量可用：%s  %s' % (VI.available(force=True), VI.why()))
    i = VI.info()
    print('索引：篇级=%s / 模型=%s / 维度=%s' % (i.get('loaded_poems'), i.get('model'), i.get('dim')))
    print('=' * 78)

    topics = [
        '找几首写羁旅愁思的清词',
        '找几首写秋景的清词',
        '找几首表达隐逸闲适的清词',
        '找几首意境苍凉的宋词',
        '找几首咏梅的宋词',
        '找几首写离别愁绪的词',
        '找几首描写边塞风雪的宋词',
        '找几首写闺怨的词',
        '找几首写人生感慨的元词',
    ]
    print('【主题问】（看首篇是否切题 + 是否声明检索范围）')
    for q in topics:
        r = ask.answer(conn, q, topk=3)
        blk = r.get('blocks') or []
        first = ''
        if blk:
            b0 = blk[0]
            first = '%s·%s《%s》' % (b0.get('dynasty') or '', b0.get('author') or '',
                                    b0.get('title') or b0.get('cipai') or '')
        print('  Q: %s' % q)
        print('     kind=%s total=%s 首篇=%s' % (r.get('kind'), r.get('total'), first or '（无）'))

    print('=' * 78)
    print('【相似问】（仿照句式是否接管）')
    sims = [
        '与《念奴娇·赤壁怀古》主题相近的词',
        '像《声声慢》那样写愁的词',
        '仿《蝶恋花》风格的词',
        '比照《雨霖铃》的词',
    ]
    for q in sims:
        r = ask.answer(conn, q, topk=3)
        print('  Q: %s' % q)
        print('     kind=%s refused=%s blocks=%d guard=%s'
              % (r.get('kind'), r.get('refused'), len(r.get('blocks') or []), r['verify'][0]))

    print('=' * 78)
    print('【回归防线】正式条件问不得被语义意图误吞')
    for q in ['清 临江仙 仄声比例高于45%', '《临江仙》有多少首', '句脚是「愁」的清词有哪些']:
        print('  Q: %-26s 相似意图=%s' % (q, SA.is_similarity_ask(q)))


if __name__ == '__main__':
    main()
