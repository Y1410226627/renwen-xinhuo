# -*- coding: utf-8 -*-
"""pronounce.py —— 注音与平仄层。

规则（题面明示）：按普通话单字读音，第一、二声记为平，第三、四声记为仄；
                  轻声、无调（多音字未定调）一律记为平。

设计取舍：
  * 题库口径接近「逐字字典读音」，而非词内变调/短语消歧 —— 整句注音（pypinyin 短语模式）
    实测反而更差（47.5% vs 56.8%），故本实现坚持「逐字」取值。
  * 允许一张人工标定表 overrides（汉字 → 拼音），用于修正高频多音字的取音；
    标定表由 tools/calibrate.py 用公开集坐标下降得到，必须附词学/读音理由。
"""
from __future__ import annotations
import json
import os
import re

try:
    from pypinyin import pinyin, Style
except Exception as exc:  # pragma: no cover
    raise ImportError('需要 pypinyin：pip install pypinyin（%s）' % exc)

_TONE_RE = re.compile(r'([1-5])\s*$')
from corpus import HAN_CLASS as _KNOWN_CLASS       # noqa: E402
# 汉字范围单一来源在 corpus.py：含 CJK 扩展 A（U+3400–U+4DBF，如「䕷」U+4577），
# 不含缺字占位符「□」「○」「■」。改这里会直接影响平仄计数（见 corpus.HAN_CLASS 注释）。
_KNOWN_RE = re.compile('[%s]' % _KNOWN_CLASS)     # 预编译（逐字热路径，不再每次拼正则串）


class Pronouncer:
    """逐字注音 + 平仄判定（带缓存，保证确定性）。"""

    def __init__(self, overrides_path: str | None = None, overrides_table=None):
        """`overrides_table`：直接把覆写表当**内存字典**传入（校验逻辑与读文件完全同一份）。

        加这个入口是为了让单元自检不再落盘：原先 selftest 为了测「非法标定表被拒绝」，
        每次运行都要写一个 `data/_tmp_bad.json` 再删掉——在限制批量删除的环境里，
        连跑多遍会因「一次任务内删除次数超限」而**误判为自检失败**（实测第 37 遍起失败）。
        改为内存表后：无文件、无删除、更快，且走的是同一条校验路径。
        """
        self.overrides: dict[str, str] = {}
        self.overrides_path = overrides_path
        raw = None
        label = overrides_path or '<内存表>'
        if overrides_table is not None:
            raw = overrides_table
        elif overrides_path and os.path.isfile(overrides_path):
            with open(overrides_path, encoding='utf-8-sig') as f:
                raw = json.load(f)
        if raw is not None:
            self._load_overrides(raw, label)
        elif overrides_table is None and not overrides_path:
            # ⚠ 2026-10-04 修（代码审查 P2-11）：`Pronouncer()` 不传参时会**静默**退化成
            #   「无标定」——公开集实测 700/700 掉到 343/700（差约 50 个百分点），
            #   而 `Engine(Pronouncer())` 这种写法在仓库里完全合理。这里发一次 stderr 警告；
            #   需要"故意无标定基线"的调用（如 tools/measure_overrides.py）应显式写 `Pronouncer(None)`。
            sys.stderr.write('⚠ Pronouncer() 未加载标定表（覆写数为 0）：平仄判定会退化为无标定口径。'
                             '交付环境请用 Pronouncer.default() 或 Pronouncer(default_overrides_path())。\n')
        self._tone_cache: dict[str, int] = {}

    @classmethod
    def default(cls):
        """交付口径的构造入口：自动加载 `solve/data/pron_overrides.json`（找不到则等价于无标定）。"""
        return cls(default_overrides_path())

    def _load_overrides(self, raw, label):
        """校验并装载覆写表（文件路径与内存表共用，口径只写一处）。"""
        # 支持三种写法：{"长": "chang2"} / {"长": 2} / {"长": {"tone": 2, "pinyin": "chang2", "note": ...}}
        for k, v in raw.items():
            if isinstance(v, dict):
                # tone 优先（显式整数），否则退回 pinyin 字符串
                v = v['tone'] if 'tone' in v else (v.get('pinyin') or '')
            v = str(v)
            if not _TONE_RE.search(v):
                raise ValueError('标定表 %s 中「%s」的取音 %r 无合法声调（需 1-4）' % (label, k, v))
            if len(str(k)) != 1 or not _KNOWN_RE.match(str(k)):
                # ⚠ 2026-10-04 修（代码审查 P3-15）：旧版只查"长度=1"，非汉字键（如 "A"）
                #   会被静默收下却永远用不上（tone() 只对汉字查覆写）——属无声的坏数据，改为报错。
                raise ValueError('标定表 %s 的键「%s」不是单个汉字' % (label, k))
            self.overrides[str(k)] = v

    @property
    def n_overrides(self) -> int:
        return len(self.overrides)

    # -------------------------------------------------- 单字
    def tone(self, ch: str) -> int:
        """返回 1..4；轻声/无调/非汉字返回 0。1、2 声平，3、4 声仄，0 记平。"""
        if ch in self._tone_cache:
            return self._tone_cache[ch]
        t = 0
        if len(ch) == 1 and _KNOWN_RE.match(ch):
            py = self.overrides.get(ch)
            if py is None:
                try:
                    py = pinyin(ch, style=Style.TONE3, errors='default')[0][0]
                except Exception:
                    py = ''
            m = _TONE_RE.search(py or '')
            t = int(m.group(1)) if m else 0
            if t == 5:
                t = 0
        self._tone_cache[ch] = t
        return t

    def is_ze(self, ch: str) -> bool:
        return self.tone(ch) in (3, 4)

    # -------------------------------------------------- 逐字平仄串
    def ping_ze(self, text: str) -> str:
        """对 text 中的每个汉字返回「平」或「仄」，忽略标点空白。"""
        return ''.join('仄' if self.is_ze(c) else '平'
                       for c in (text or '') if _KNOWN_RE.match(c))

    def annotate(self, text: str):
        """逐字标注：[(汉字, 声调, 平/仄), ...]"""
        out = []
        for c in (text or ''):
            if _KNOWN_RE.match(c):
                t = self.tone(c)
                out.append((c, t, '仄' if t in (3, 4) else '平'))
        return out


def default_overrides_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, 'data', 'pron_overrides.json')
