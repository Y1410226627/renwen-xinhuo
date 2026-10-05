# -*- coding: utf-8 -*-
"""answer_reason.py —— 把「为什么答不出/为什么是 0」**结构化成八态**。

由来（2026-10-05，朋友项目对照）：
    我们的 `guard.py` 护栏③「无据即认账」原本只有**一刀**——`refused` 是布尔值
    （已拒答 / 未拒答）。可「答不出」其实有**好几种不同的原因**，混作一团时，
    用户（和评委）追问「为什么答不出」只能去读整段文案猜。

    朋友的 `ProviderResult.status` 把这层拆开：
        ok / partial / not_found / unavailable / unsupported / ambiguous /
        conflict / insufficient_evidence
    最值得学的是**把「没有数据」和「不好」拆开**：
        · not_found（查了，没有） ≠ unavailable（来源暂不可得） ≠ unsupported（不支持该能力）；
        · 执行失败（超时）与业务不确定（多解）也分开。

本模块是**纯附加层**：只读 `answer()` 返回的 dict，推断一个 `Reason`，**不改任何答句**。
因此它可以安全地接在网页/日志侧，且**绝不影响双集零回归哈希**（不 import 进 solver）。
"""

from __future__ import annotations
import re
from enum import Enum


class Reason(str, Enum):
    """八态枚举（对齐朋友 `ProviderResult.status`，落成中文标签）。"""

    OK = 'ok'                                 # 有确切答案
    NOT_FOUND = 'not_found'                   # 查了，范围内 0 篇（0 是确切结果）
    UNSUPPORTED = 'unsupported'               # 不支持该能力/范围（如语料外朝代）
    AMBIGUOUS = 'ambiguous'                   # 条件多解，未替用户选定
    CONFLICT = 'conflict'                     # 条件互相矛盾（交集为空且非单纯 0）
    INSUFFICIENT = 'insufficient_evidence'    # 范围非空，但该口径无可用数据
    UNAVAILABLE = 'unavailable'               # 链路/来源本次不可用（导入失败、超时等）
    UNKNOWN = 'unknown'                       # 兜底（不应出现；出现即需补规则）


LABELS = {
    Reason.OK: '有确切答案',
    Reason.NOT_FOUND: '已检索、范围内为零（零是确切结果）',
    Reason.UNSUPPORTED: '不支持该范围或能力',
    Reason.AMBIGUOUS: '条件多解，未替用户选定',
    Reason.CONFLICT: '条件互相矛盾',
    Reason.INSUFFICIENT: '范围非空但该口径无可用数据',
    Reason.UNAVAILABLE: '链路或来源本次不可用',
    Reason.UNKNOWN: '未归类',
}

# —— 判据（按**优先级**从上到下；用文案里的确定短语，不依赖模糊推测）——
_RULES = (
    # 语料外 / 不支持
    (Reason.UNSUPPORTED, (r'语料外范围', r'只含清/宋/元', r'不支持', r'问句过长',
                          r'未给出可解析的条件', r'官方题型')),
    # 链路不可用
    (Reason.UNAVAILABLE, (r'链路不可用', r'未能完成定位', r'请检查语料目录', r'出错了')),
    # 多解
    (Reason.AMBIGUOUS, (r'多解', r'有歧义', r'请先指定', r'请指明篇目', r'请核对')),
    # 范围非空、但该口径无数据
    (Reason.INSUFFICIENT, (r'没有可用于该统计量的数据', r'没有可用数据', r'样本不足',
                           r'指标缺失', r'不拿看似像答案的数字来充数')),
    # 矛盾
    (Reason.CONFLICT, (r'互相矛盾', r'条件互相冲突', r'不可能同时满足')),
)


def classify(res) -> dict:
    """从 `answer()` 的结果 dict 推断结构化理由。

    返回 `{'reason': Reason, 'label': 中文标签, 'refused': bool, 'total': int|None,
           'note': 一句话依据}`。
    """
    text = str((res or {}).get('answer') or '')
    refused = bool((res or {}).get('refused'))
    total = (res or {}).get('total')

    for reason, pats in _RULES:
        for p in pats:
            if re.search(p, text):
                return _mk(reason, refused, total, '文案命中判据 /%s/' % p)

    # 没有硬条件、也不是拒答 → 语义排序（有结果但非确切答案）
    if total is None and not refused:
        return _mk(Reason.OK, refused, total, '未给结构化条件，按语义相关度排序（非确切答案）')
    # 明确报 0 篇
    if total == 0 and not refused:
        return _mk(Reason.NOT_FOUND, refused, total, '范围内命中为零，零为确切结果')
    if refused:
        return _mk(Reason.NOT_FOUND, refused, total, '既未命中判据、已拒答（按未召回归类）')
    return _mk(Reason.OK, refused, total, '有确切答案')


def _mk(reason, refused, total, note):
    return {'reason': reason.value, 'label': LABELS[reason], 'refused': refused,
            'total': total, 'note': note}


if __name__ == '__main__':
    # 自证：几条代表性命中
    import json
    for t in ('现有语料未见支持：问句涉及语料外范围（唐诗）…',
              '在条件〔朝代=清〕下共命中 0 篇：…',
              '在条件〔…〕下共命中 6 篇；但按本题要求的统计口径，这些篇目里没有可用于该统计量的数据…'):
        r = classify({'answer': t, 'refused': '语料外' in t, 'total': 0 if '0 篇' in t else None})
        print(json.dumps(r, ensure_ascii=False))
