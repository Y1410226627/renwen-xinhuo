# -*- coding: utf-8 -*-
"""safety.py —— **内容安全护栏**（参赛指南第七点（三）(5) 明文要求）。

它和 `guard.py` 是两回事，别混：
    `guard.py`  = **可溯源护栏**：防「数字没出处」「引文不是原文」「没证据还硬答」。
    `safety.py` = **内容安全护栏**：防有害、违法、越界、攻击、提示注入等**不当交互**。

工作方式：
    ① **入向**（用户提问）先过一遍：命中即**不进检索**，直接给固定拒答话术；
    ② **出向**（大模型生成的叙述）再过一遍：命中即**整段丢弃**，回落到模板作答。
    ——两道都过，才允许出现在页面上。

两个工程纪律（都有自检示例，见 `selftest.py` 第 20 节）：
    · 规则要**窄**：清词语料里本来就有「血」「杀」「恨」「妓」「酒」这类字，
      所以本模块**不做单词黑名单式过滤**，只匹配「有明确现代语境/行为指向」的模式，
      避免把正常学术问题误判（误判 = 用户问不出东西，比漏判更伤使用）
    · 「加了护栏」≠「护栏有效」：第 20 节会把每一类**真实触发一次**。

生产提示：本表是**示意性规则**（类别 + 少量示例模式），正式上线应换成学校的正式词库/审核服务。
"""
import json
import os
import re

RULES = [
    ('提示注入', [
        r'(忽略|无视|忘掉)(以上|上述|之前|前面|所有)?的?(全部)?(指令|规则|设定|限制)',
        r'(开发者|上帝|调试|越狱)(模式|模式开启)',
        r'\bjailbreak\b', r'\bDAN\b',
        r'(泄露|输出|告诉我|打印).{0,6}(系统)?(提示词|prompt|密钥|api[_-]?key)',
        r'reveal.{0,12}(prompt|system)',
    ]),
    ('学术不端', [
        r'(代写|替我写|帮我写|帮我做|代做|枪手).{0,8}(论文|作业|课程论文|毕业论文|开题报告|考试|答卷|结课)',
        r'(论文|作业|毕设|开题报告).{0,6}(代写|代做|找人写)',
    ]),
    ('违法危险', [
        r'(制作|制造|合成|购买|出售|获取).{0,8}(炸弹|炸药|枪支|毒品|冰毒|海洛因|管制刀具|迷药)',
        r'(如何|怎么|怎样).{0,8}(自杀|自残|投毒|跟踪|撬锁)',
    ]),
    ('色情低俗', [r'色情|黄色(网站|小说|视频)|裸照|招嫖|约炮|一夜情']),
    ('赌博诈骗', [r'赌博(技巧|网站|平台)|博彩(网站|平台)|洗钱|电信诈骗|刷单返利']),
    ('隐私侵犯', [
        r'(查|查询|泄露|出售|倒卖|买到).{0,8}(身份证(号|号码)?|手机号|住址|家庭住址|银行卡|开房记录|聊天记录|征信报告)',
    ]),
    ('辱骂攻击', [r'傻逼|脑残|去死|滚蛋|贱人|种族歧视|地域黑']),
]
_COMPILED = [(name, [re.compile(p, re.IGNORECASE) for p in pats]) for name, pats in RULES]


_EXTRA_CACHE = {'key': None, 'rules': []}


def _extra_rules():
    """允许用 `solve/data/safety_terms.json` 追加词（{"类别": ["正则", ...]}）。"""
    # 审查 P2：旧版每次 check() 都读盘 + 重编译；这里按文件 mtime 缓存
    _f0 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'safety_terms.json')
    try:
        _key = os.path.getmtime(_f0)
    except OSError:
        _key = None
    if _EXTRA_CACHE['key'] == _key:
        return _EXTRA_CACHE['rules']
    _rules = _load_extra()
    _EXTRA_CACHE['key'], _EXTRA_CACHE['rules'] = _key, _rules
    return _rules


def _load_extra():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'safety_terms.json')
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding='utf-8-sig') as f:
            d = json.load(f)
    except Exception:
        return []
    out = []
    for name, pats in (d or {}).items():
        out.append((name, [re.compile(x, re.IGNORECASE) for x in pats]))
    return out


def check(text, direction='in'):
    """返回 {'ok': bool, 'category': str|None, 'matched': str|None, 'direction': str}。

    ⚠️ 审查 B28 指出：`direction`（'in' 入向 / 'out' 出向）**当前不改变判定**，
    入向与出向跑同一套规则；它只被**如实记录**在返回值里。不要据此以为两向有差异——
    真要差异化得先有独立的出向词库（那是内容安全团队的事）。这里写明，避免误读参数语义。
    """
    t = str(text or '')       # 非字符串输入不得抛 TypeError（审查 X3）
    for name, pats in _COMPILED + _extra_rules():
        for pat in pats:
            m = pat.search(t)
            if m:
                return {'ok': False, 'category': name, 'matched': m.group(0)[:40],
                        'direction': direction}
    return {'ok': True, 'category': None, 'matched': None, 'direction': direction}


def refusal(category):
    """固定拒答话术。

    ⚠️ 承诺要写准（审查 C20）：本话术满足 `guard.check_no_support` 里**「不含数字」与
    「不含引文」**两条，但**不含「未见支持」**那句——「未见支持」是**语料无据**的认账话术，
    内容安全拒答与它不同类，不该硬塞。类别名用【】不用「」：`check_no_support` 把成对「」
    判为引文，两者会互掐（审查 B24 实测）。
    """
    return ('【内容安全】该请求涉及【%s】，本系统不予回应。\n'
            '本系统只处理清代词律与声律声情（逐字平仄、句脚、声情转向、校订建议）等学术问题；'
            '请换一个学术问题再问。' % category)


def categories():
    return [name for name, _ in RULES] + [name for name, _ in _extra_rules()]


def main():
    import argparse
    ap = argparse.ArgumentParser(description='内容安全护栏（入向/出向）')
    ap.add_argument('--text', required=True)
    ap.add_argument('--out', action='store_true', help='按出向检查（大模型叙述）')
    a = ap.parse_args()
    r = check(a.text, 'out' if a.out else 'in')
    print(json.dumps(r, ensure_ascii=False))
    print('类别清单：%s' % '、'.join(categories()))
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
