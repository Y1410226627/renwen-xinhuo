# -*- coding: utf-8 -*-
"""answer_reason.py —— 把「为什么答不出/为什么是 0」**结构化成九态**。

（原为八态；2026-10-08 外部审查 P1 新增 `SAFETY_BLOCKED`——内容安全拒答此前被误并为
 「已检索、范围内为零」，见下方 `Reason` 枚举与 `classify` 的 ①'。）

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
    """九态枚举（对齐朋友 `ProviderResult.status`，落成中文标签）。

    ⚠ 2026-10-08 新增第 9 态 `SAFETY_BLOCKED`（外部审查 P1）：入向内容安全拦截此前被
      误归为 `NOT_FOUND`（「已检索、范围内为零」），业务语义完全错误——安全拒答**根本没执行检索**。
    """

    OK = 'ok'                                 # 有确切答案
    NOT_FOUND = 'not_found'                   # 查了，范围内 0 篇（0 是确切结果）
    UNSUPPORTED = 'unsupported'               # 不支持该能力/范围（如语料外朝代）
    SAFETY_BLOCKED = 'safety_blocked'         # 内容安全拦截（入向）：不允许的用途，未执行检索
    AMBIGUOUS = 'ambiguous'                   # 条件多解，未替用户选定
    CONFLICT = 'conflict'                     # 条件互相矛盾（交集为空且非单纯 0）
    INSUFFICIENT = 'insufficient_evidence'    # 范围非空，但该口径无可用数据
    UNAVAILABLE = 'unavailable'               # 链路/来源本次不可用（导入失败、超时等）
    UNKNOWN = 'unknown'                       # 兜底（不应出现；出现即需补规则）


LABELS = {
    Reason.OK: '有确切答案',
    Reason.NOT_FOUND: '已检索、范围内为零（零是确切结果）',
    Reason.UNSUPPORTED: '不支持该范围或能力',
    Reason.SAFETY_BLOCKED: '安全拦截：该请求属于不支持/不允许的用途，未执行检索',
    Reason.AMBIGUOUS: '条件多解，未替用户选定',
    Reason.CONFLICT: '条件互相矛盾',
    Reason.INSUFFICIENT: '范围非空但该口径无可用数据',
    Reason.UNAVAILABLE: '链路或来源本次不可用',
    Reason.UNKNOWN: '未归类',
}

# —— 判据（按**优先级**从上到下；用文案里的确定短语，不依赖模糊推测）——
_RULES = (
    # ⚠ 2026-10-08 新增（外部审查 P1）：内容安全拦截**优先**判——它压根没进检索，
    #   绝不能落到「已检索、范围内为零」。用 `safety.refusal()` 的固定短语兜底
    #   （结构化判据见 classify 的 ①'，两者互为补充；此处为兼容层）。
    (Reason.SAFETY_BLOCKED, (r'【内容安全】', r'不予回应')),
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

    判据优先顺序（外部审查 P2-56 后调整，从「纯文案反推」升级为「结构化优先」）：
      ① `res['reason']` —— `answer()` 已**直接给出**结构化理由时直接采用（最可靠）；
      ② **结构化字段**（如 `spec.unsupported`）—— 不再依赖文案猜测；
      ③ 文案判据 `_RULES` —— 兼容层（旧调用方/日志里只有文案时仍可用）。

    返回 `{'reason': Reason, 'label': 中文标签, 'refused': bool, 'total': int|None,
           'note': 一句话依据}`。
    """
    res = res or {}
    refused = bool(res.get('refused'))
    total = res.get('total')

    # ① answer() 直接给出的结构化理由（最可靠，优先采用）
    _direct = res.get('reason')
    if _direct:
        try:
            _r = _direct if isinstance(_direct, Reason) else Reason(_direct)
            return _mk(_r, refused, total, 'answer() 直接给出的结构化理由')
        except ValueError:
            pass
    # ①' 入向内容安全拦截（结构化，最可靠）——
    #   ⚠ 2026-10-08 新增（外部审查 P1）：`ask.answer()` 命中入向安全护栏时返回
    #   `kind='安全拦截'`、`refused=True`、`safety=sf`（`sf['ok']` 为假），**且未进检索**。
    #   改前它一路落到末尾 `if refused: return _mk(NOT_FOUND,…)` → 用户被误告「已检索、范围内为零」。
    #   改后优先命中本态。注意：**问句超长**那条（ask.py:1331-1337）`safety={'ok': True}` 且
    #   kind≠'安全拦截'，故不受影响，仍走文案判据归 UNSUPPORTED。
    _sf = res.get('safety')
    if res.get('kind') == '安全拦截' or (isinstance(_sf, dict) and _sf.get('ok') is False):
        return _mk(Reason.SAFETY_BLOCKED, refused, total, '内容安全拦截：未执行检索（非「范围内为零」）')
    # ② 结构化字段（spec.unsupported 等）——不依赖文案
    _sp = res.get('spec')
    if isinstance(_sp, dict) and _sp.get('unsupported'):
        return _mk(Reason.UNSUPPORTED, refused, total, 'spec.unsupported=%s' % _sp['unsupported'])

    text = str(res.get('answer') or '')

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


# ───────── 与 `answer_verify` 的五态对齐（2026-10-09） ─────────
# 为什么加：`answer_verify.set_check.status` 与本文的 `Reason` 是**两套字面**，
# 上层要合并展示时必须自己翻译。这里给一个**只读映射**（不改任何既有判定），
# 使「已验证／未验证／不支持／查无」在一条链上同名同义。
_STATUS_TO_REASON = {
    'VERIFIED_EXACT': 'ok',
    'VERIFIED_DERIVED': 'ok',
    'SEMANTIC_NOT_EXHAUSTIVE': 'not_found',   # 语义排序不存在可判定的完整命中集
    'NOT_CHECKED': 'partial',
    'FAILED': 'partial',
}


def reason_from_status(status):
    """`answer_verify.set_check.status` → 本模块 `Reason` 取值（未知状态返回 None）。"""
    return _STATUS_TO_REASON.get(status)
