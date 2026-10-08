# -*- coding: utf-8 -*-
"""context.py —— **服务端会话语境**（多轮「结果集」指代的落地点）。

为什么要有它（2026-10-08，外部架构审查 A 项）：
    旧版多轮上下文完全靠前端 `AskView.vue` 的 `lastTurn = {q, spec, pids}`，
    而下一轮把 pid 集合 `slice(0, 200)` 之后当作「上一轮的全部结果」发给后端。
    **200 是语义截断，不是性能截断** —— 上一轮若命中 3000 首，下一轮问
    「其中字数最少的有哪些」，系统实际只在**前 200 篇**里找 → 改变了问题语义。
    更根本的是：前端 API 看不到 pid 时多轮直接失效；「集合指代」（这些/其中）
    与「单篇指代」（那首/它）也从未区分。

本模块提供三件事：
  1. `Session` / `ContextStore`：把**完整**结果集（不截断）与服务端会话绑定，
     存内存字典，可**可选**落盘到 `data/sessions/`（JSON）；
  2. `resolve(session, question)`：**指代分类**（本模块的核心）——把「这些/其中/那里面/它们」
     判成集合指代、「那首/它/这首/这篇」判成单篇指代（多篇时如实报 ambiguous）、
     「改成宋词呢/再加一句」判成条件继承；无指代则 none；
  3. `pid_chunks(pids, size=900)`：SQL 变量上限分块（配合 `spec.ctx_pids` 使用）。

纪律（与外部审查 A 项一致）：
  · 每轮存**完整** pid 集合；仅当超过硬上限（每轮 20000 个）时才截断，
    并且**必须**留下 `truncated: True` 标记 + 真实 total —— **绝不静默截断**；
  · 指代判据写成**显式词表 + 纯函数**，便于单测（见 `classify_reference`）。

★ 结构性隔离（D07）：本模块只被 `web/serve.py` 调用，不进 `ask`/`solver`，
  对 1000 题交付答案**零影响**。
"""

import json
import os
import re
import threading
import time

# ─────────────────────────── 上限（外部审查 A 项给定） ───────────────────────────
MAX_SESSIONS = 50            # 最多保留 50 个会话（超出按最近使用淘汰）
MAX_TURNS = 20               # 每个会话最多保留 20 轮（超出丢最旧）
MAX_PIDS_PER_TURN = 20000    # 每轮 pid 上限；超出→截断并标记 truncated: True

# ───────── 结果集合的**语义类型**（2026-10-08 第二轮审查 §22 新增） ─────────
# 旧版把「上一轮结果集」当成一种东西，实际上两种**可追问性完全不同**：
#   EXACT_SET             ：由 SQL 硬条件得出的**完整命中集**（如「清代字数>50 的词」共 3000 篇）。
#                           追问「其中最短的」是在**全集**里找 —— 语义正确。
#   SEMANTIC_RANKED_SET   ：由向量/FTS 相似度排出来的 **top-k**（如「写秋景的词」展示 5 篇）。
#                           它不是「全部写秋景的词」，只是**排序最前的 k 篇**；
#                           追问「其中最短的」只能在这 k 篇里找 —— 必须**如实说明**，
#                           否则用户会以为「系统查了全库却只给我 5 篇」或反之误以为 5 篇即全部。
RESULT_KIND_EXACT = 'EXACT_SET'
RESULT_KIND_SEMANTIC = 'SEMANTIC_RANKED_SET'
RESULT_KINDS = (RESULT_KIND_EXACT, RESULT_KIND_SEMANTIC)


def kind_of_answer(total, shown, hard):
    """由答案形态反推结果集类型（供上层标注，不必自己判断语义）。

    `hard`=True（有可精确判定的 SQL 条件）且 `total` 已知 → 精确集；否则是语义排序集。
    """
    return RESULT_KIND_EXACT if hard else RESULT_KIND_SEMANTIC

# ─────────────────────────── 指代判据（显式词表，可单测） ───────────────────────────
# 集合指代：问的是「上一轮那**一批**」。
SET_REF_WORDS = (
    '它们', '这些', '那些', '这其中', '其中', '那里面', '这里面', '上面那些', '上述',
    '前述', '刚才那些', '刚才那批', '先前那些', '这批', '那批', '这一批', '那一批',
)
# 单篇指代：问的是「上一轮那**一首**」。`它` 单独列，并用 `它(?!们)` 排除「它们」。
SINGLE_REF_WORDS = (
    '那一首', '这一首', '那首', '这首', '那一篇', '这一篇', '那篇', '这篇',
    '此篇', '该篇', '那一阕', '这一阕', '那一闋', '这一闋', '它',
)
# 条件继承：把上一轮的**条件**换个取值/再加一条，而不是换结果集。
INHERIT_MARKERS = (
    '改成', '换成', '改为', '换为', '换一下', '再加', '再加上', '再补', '补上',
    '继续', '接着', '同样地', '照样', '再来一次', '再来', '在这个基础上', '在此基础上',
    '换个词牌', '换个朝代', '再加一句', '再问一句',
)


def _alt(words, wrap_ta=False):
    """把词表编成「最长优先」的交替正则：**先匹配更长的词**，避免「那首」被「那」抢先。"""
    ws = sorted(set(words), key=len, reverse=True)
    parts = []
    for w in ws:
        if wrap_ta and w == '它':
            parts.append(r'它(?!们)')          # 「它们」是集合指代，别被「它」抢走
        else:
            parts.append(re.escape(w))
    return re.compile('|'.join(parts)) if parts else None


_SET_RE = _alt(SET_REF_WORDS)
_SINGLE_RE = _alt(SINGLE_REF_WORDS, wrap_ta=True)


def _first_match(rx, text):
    """返回 `(命中词, 起始下标)`；无命中返回 None。"""
    if rx is None:
        return None
    m = rx.search(text or '')
    return (m.group(0), m.start()) if m else None


def classify_reference(question):
    """**纯函数**：问句 → 指代类别（可单测）。

    返回 dict（至少含 `kind`）：
      · `{'kind': 'set', 'marker': 命中词}`      —— 集合指代（这些/其中/那里面/它们/刚才那些）
      · `{'kind': 'single', 'marker': 命中词}`   —— 单篇指代（那首/它/这首/这篇）
      · `{'kind': 'inherit', 'marker': 命中词}`  —— 条件继承（改成宋词呢/再加一句）
      · `{'kind': 'none'}`                       —— 无指代

    判据（确定性、可复现）：
      1. 同时含集合词与单篇词时，取**位置更靠后**的那个（问句的焦点通常在宾语位，
         如「这些里面最短的**那首**」→ 单篇；「那首词在**其中**排第几」→ 集合）；
      2. 否则单篇优先于集合；
      3. 都没有再看条件继承词表；
      4. 都没有 → none。
    """
    q = str(question or '')
    if not q.strip():
        return {'kind': 'none'}
    ms = _first_match(_SET_RE, q)
    mm = _first_match(_SINGLE_RE, q)
    if ms and mm:
        if mm[1] >= ms[1]:
            return {'kind': 'single', 'marker': mm[0]}
        return {'kind': 'set', 'marker': ms[0]}
    if mm:
        return {'kind': 'single', 'marker': mm[0]}
    if ms:
        return {'kind': 'set', 'marker': ms[0]}
    for w in INHERIT_MARKERS:
        if w in q:
            return {'kind': 'inherit', 'marker': w}
    return {'kind': 'none'}


# ─────────────────────────── SQL 变量上限分块 ───────────────────────────
def pid_chunks(pids, size=900):
    """把 pid 列表切成「每块 ≤ size」的列表（**配合 `spec.ctx_pids` 供上层循环查询**）。

    为什么需要：`retrieve._sql()` 把 `spec.ctx_pids` 编成**单条** `p.pid IN (?,…)`，
    没有内部分块；一旦 pid 个数逼近 SQLite 的宿主变量上限（旧版 999，新版 32766），
    就会 `too many SQL variables`。上层在把大集合交给 SQL 前，用本函数切块逐块查询。
    默认 size=900：贴着**旧版 999 上限**留余量（本项目实测解释器 SQLite ≥ 32766，
    但仍按最保守的 999 设计，便于换机复用）。

    返回 list[list[str]]；`pids` 为空时返回 []。
    """
    seq = [p for p in (pids or []) if p]
    if not seq:
        return []
    n = max(1, int(size or 900))
    return [seq[i:i + n] for i in range(0, len(seq), n)]


# ─────────────────────────── 会话 ───────────────────────────
def _dedup(seq):
    """去重、保序（pid 是字符串）。"""
    seen, out = set(), []
    for x in (seq or []):
        s = str(x).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _new_sid():
    """会话 id：时间戳（36 进制）+ 随机后缀（跨进程也不易撞）。"""
    return 's' + format(int(time.time() * 1000), 'x') + os.urandom(3).hex()


class Session:
    """一次会话（一条「线」）：按轮记录问句、解析摘要、**完整**结果集与总数。

    每轮字段（dict）：
      · `question`     本轮问句
      · `spec_desc`    本轮解析摘要（`QuerySpec.describe()`）
      · `result_pids`  本轮命中篇号 —— **完整**（仅超 `MAX_PIDS_PER_TURN` 时才截断）
      · `result_total` 本轮命中总数（真值）
      · `truncated`    `result_pids` 是否被截断（超上限时为 True）
      · `created_at`   该轮时间戳
    """

    def __init__(self, sid=None, turns=None, prev_single=None, created_at=None, updated_at=None):
        self.sid = sid or _new_sid()
        self.turns = list(turns or [])
        self.prev_single = prev_single          # 上一轮若只有一篇，记其 pid
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at

    # ---- 写 ----
    def add_turn(self, question, spec_desc, result_pids, result_total,
                 max_pids=MAX_PIDS_PER_TURN, result_kind=None):
        """追加一轮；返回该轮 dict。

        截断纪律：`result_pids` 超过 `max_pids` 时**截断并置 `truncated=True`**
        （调用方据此提示「上一轮结果过多，仅保留前 M 篇参与追问」）——绝不静默。

        `result_kind`：见模块常量 `RESULT_KIND_EXACT / RESULT_KIND_SEMANTIC`。
        **不传则按「是否截断」以外的信息无法判定，默认 `EXACT_SET`**（向后兼容旧调用方）；
        但上层若知道这一轮是语义排序的结果，**必须显式传 `SEMANTIC_RANKED_SET`**，
        否则下一轮追问会被当成「在完整集合里找」。
        """
        pids = _dedup(result_pids)
        truncated = False
        if max_pids and len(pids) > max_pids:
            pids = pids[:max_pids]
            truncated = True
        if result_kind not in RESULT_KINDS:
            result_kind = RESULT_KIND_EXACT
        exhaustive = (result_kind == RESULT_KIND_EXACT) and not truncated
        turn = {'question': question or '', 'spec_desc': spec_desc or '',
                'result_pids': pids, 'result_total': result_total,
                'truncated': truncated, 'created_at': time.time(),
                'result_kind': result_kind, 'exhaustive': exhaustive}
        self.turns.append(turn)
        if len(self.turns) > MAX_TURNS:         # 只留最近 MAX_TURNS 轮
            self.turns = self.turns[-MAX_TURNS:]
        # 「上一轮唯一篇」：只有**恰好一篇且未被截断**时才可作单篇指代的目标。
        # ⚠ 语义排序集即使只有一篇，那也只是「最像的一篇」，仍可作为指代目标
        #   （用户说「那首」指的就是屏幕上那一首），故不因 result_kind 而禁用。
        self.prev_single = pids[0] if (len(pids) == 1 and not truncated) else None
        self.updated_at = turn['created_at']
        return turn

    def last_turn(self):
        return self.turns[-1] if self.turns else None

    # ---- 序列化 ----
    def to_dict(self):
        return {'sid': self.sid, 'turns': self.turns, 'prev_single': self.prev_single,
                'created_at': self.created_at, 'updated_at': self.updated_at}

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            return None
        return cls(sid=d.get('sid'), turns=d.get('turns') or [],
                   prev_single=d.get('prev_single'),
                   created_at=d.get('created_at'), updated_at=d.get('updated_at'))


def resolve(session, question):
    """**指代分类 + 取值**（本模块核心）。返回 dict，`kind` 之一：

      · `{'kind':'set', 'pids':[...], 'total':N, 'truncated':bool, 'marker':w}`
        集合指代 → 上一轮**完整**集合（不截断；若库里存的就是截断过的，如实体现在
        `truncated` 上，绝不假装完整）；
      · `{'kind':'single', 'pid':p, 'marker':w}`
        单篇指代 → 上一轮唯一篇；上一轮多篇 → `{'kind':'ambiguous', 'reason':...}`；
      · `{'kind':'inherit', 'spec_desc':..., 'question':..., 'marker':w}`
        条件继承 → 上一轮的解析摘要（供上层拼进 `ctx`）；
      · `{'kind':'none'}` 无指代（或没有历史）。

    无会话/无历史一律回 `{'kind':'none'}`（不臆造上下文）。
    """
    cls = classify_reference(question)
    kind = cls.get('kind', 'none')
    if kind == 'none' or session is None or not getattr(session, 'turns', None):
        return {'kind': 'none'}
    last = session.turns[-1]
    if kind == 'set':
        pids = list(last.get('result_pids') or [])
        rk = last.get('result_kind') or RESULT_KIND_EXACT
        out = {'kind': 'set', 'pids': pids, 'total': last.get('result_total'),
               'truncated': bool(last.get('truncated')), 'marker': cls.get('marker'),
               'result_kind': rk, 'exhaustive': bool(last.get('exhaustive', True))}
        if rk == RESULT_KIND_SEMANTIC:
            # ★ 语义排序集：追问范围只等于「上一轮**展示出来的**那些」，不是全库里所有相关的篇。
            #   这句话必须由上层说给用户听（GPT §22：「不能都叫上一轮结果集」）。
            out['scope_note'] = (
                '上一轮是**语义相关度排序**的结果，并非「满足该主题的全体作品」；'
                '本轮只在其中 %d 篇（展示出来的那些）里进一步找。'
                % len(pids))
        elif last.get('truncated'):
            out['scope_note'] = ('上一轮命中过多，仅保留前 %d 篇参与追问（共 %s 篇）。'
                                 % (len(pids), tot_of(last.get('result_total'))))
        return out
    if kind == 'single':
        pid = getattr(session, 'prev_single', None)
        if pid is None:
            pids = list(last.get('result_pids') or [])
            if len(pids) == 1:
                pid = pids[0]
        if pid is None:
            _tot = last.get('result_total')
            _tot = '未知' if _tot is None else tot_of(_tot)
            return {'kind': 'ambiguous', 'marker': cls.get('marker'),
                    'total': last.get('result_total'),
                    'reason': ('上一轮命中 %s 篇，「%s」无法确定指哪一篇；'
                               '请写出篇名，或用「其中…」这类集合问法。'
                               % (_tot, cls.get('marker') or '那首'))}
        return {'kind': 'single', 'pid': pid, 'marker': cls.get('marker')}
    # inherit
    return {'kind': 'inherit', 'spec_desc': last.get('spec_desc') or '',
            'question': last.get('question') or '', 'marker': cls.get('marker')}


def tot_of(n):
    """仅用于把数字安全地嵌进文案（None/非数 → '未知'）。"""
    try:
        return int(n)
    except (TypeError, ValueError):
        return '未知'


class ContextStore:
    """会话仓库：内存字典 + **可选**磁盘持久化（`data/sessions/<sid>.json`）。

    淘汰策略：会话数 > `max_sessions` 时按 `updated_at` 淘汰最旧的。
    持久化尽力而为：写失败（只读盘/配额）只记 warning，不影响内存可用。
    """

    def __init__(self, dirpath=None, max_sessions=MAX_SESSIONS,
                 max_turns=MAX_TURNS, max_pids=MAX_PIDS_PER_TURN, persist=None):
        self.max_sessions = max(1, int(max_sessions or MAX_SESSIONS))
        self.max_turns = max(1, int(max_turns or MAX_TURNS))
        self.max_pids = max(1, int(max_pids or MAX_PIDS_PER_TURN))
        self.dirpath = dirpath
        # persist=None → 给定了目录就落盘；persist=False 强制不落盘（测试用）
        self.persist = bool(dirpath) if persist is None else bool(persist and dirpath)
        self.sessions = {}
        self._lock = threading.Lock()

    # ---- 读 ----
    def get(self, sid):
        if not sid:
            return None
        with self._lock:
            return self.sessions.get(sid)

    def get_or_create(self, sid):
        """按 sid 取会话；不存在则（用该 sid）新建。sid 为空则新建一个。"""
        with self._lock:
            s = self.sessions.get(sid) if sid else None
            if s is None:
                s = self.load_one(sid) if (sid and self.persist) else None
            if s is None:
                s = Session(sid=sid) if sid else Session()
                self.sessions[s.sid] = s
            self._evict_locked()
            return s

    def new(self):
        with self._lock:
            s = Session()
            self.sessions[s.sid] = s
            self._evict_locked()
            return s

    def count(self):
        with self._lock:
            return len(self.sessions)

    # ---- 写 ----
    def add_turn(self, session, question, spec_desc, result_pids, result_total,
                 result_kind=None):
        if session is None:
            session = self.new()
        turn = session.add_turn(question, spec_desc, result_pids, result_total,
                                max_pids=self.max_pids, result_kind=result_kind)
        with self._lock:
            self.sessions[session.sid] = session
            self._evict_locked()
        self.save(session)
        return turn

    def prune_turns(self, session):
        if session is not None and len(session.turns) > self.max_turns:
            session.turns = session.turns[-self.max_turns:]

    def _evict_locked(self):
        if len(self.sessions) <= self.max_sessions:
            return
        order = sorted(self.sessions.values(), key=lambda s: (s.updated_at or 0))
        for s in order[:len(self.sessions) - self.max_sessions]:
            self.sessions.pop(s.sid, None)
            self._remove_file(s.sid)

    # ---- 持久化 ----
    def _path(self, sid):
        return os.path.join(self.dirpath, '%s.json' % sid) if self.dirpath else None

    def load_one(self, sid):
        p = self._path(sid)
        if not p or not os.path.exists(p):
            return None
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return Session.from_dict(json.load(f))
        except Exception:
            return None

    def load(self):
        """从磁盘目录载入全部会话（启动时调用）。失败静默（内存仍可用）。"""
        if not self.persist or not os.path.isdir(self.dirpath):
            return 0
        n = 0
        try:
            for name in os.listdir(self.dirpath):
                if not name.endswith('.json'):
                    continue
                s = self.load_one(name[:-5])
                if s is not None:
                    self.sessions[s.sid] = s
                    n += 1
        except Exception:
            return n
        with self._lock:
            self._evict_locked()
        return n

    def save(self, session):
        if not self.persist or session is None:
            return False
        try:
            os.makedirs(self.dirpath, exist_ok=True)
            p = self._path(session.sid)
            tmp = p + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False)
            os.replace(tmp, p)
            return True
        except Exception:
            return False

    def _remove_file(self, sid):
        p = self._path(sid)
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


# ─────────────────────────── 自测（python solve/context.py） ───────────────────────────
def _selftest():
    cases = [
        ('其中字数最少的有哪些', 'set'),
        ('这些里面最短的', 'set'),
        ('它们里哪个最长', 'set'),
        ('那里面句脚是灯的有哪些', 'set'),
        ('刚才那些里有没有纳兰性德的', 'set'),
        ('那首最短吗', 'single'),
        ('它呢', 'single'),
        ('这篇的声情是什么', 'single'),
        ('这首词有几个仄声', 'single'),
        ('这些里面最短的那首', 'single'),
        ('那首词在其中排第几', 'set'),
        ('改成宋词呢', 'inherit'),
        ('再加一句关于句脚的', 'inherit'),
        ('换成清 临江仙试试', 'inherit'),
        ('清 临江仙 仄声比例高于45%', 'none'),
        ('宋词与清词哪个更高', 'none'),
        ('', 'none'),
    ]
    bad = 0
    for q, want in cases:
        got = classify_reference(q)['kind']
        flag = 'OK ' if got == want else 'BAD'
        if got != want:
            bad += 1
        print('%-4s %-28s → %-8s（期望 %s）' % (flag, q or '（空）', got, want))

    # resolve 的四类
    s = Session(sid='testsess')
    print('\n-- resolve --')
    r = resolve(s, '其中最短的')
    print('无历史 set →', r)
    s.add_turn('清 临江仙 仄声比例高于45%', '朝代=清；词牌=临江仙；仄声比例≥45', ['p%d' % i for i in range(59)], 59)
    print('集合指代 →', {k: (v if k != 'pids' else '%d 篇' % len(v)) for k, v in resolve(s, '其中最短的').items()})
    print('单篇指代(59篇) →', resolve(s, '那首最短吗'))
    print('条件继承 →', resolve(s, '改成宋词呢'))
    print('无指代 →', resolve(s, '宋 念奴娇 平仄比例'))
    s.add_turn('朱彝尊的词里最长句超过9句的有哪些', '词人=朱彝尊', ['Q0001'], 1)
    print('单篇指代(1篇) →', resolve(s, '它最短吗'))

    # pid_chunks
    ch = pid_chunks(['p%d' % i for i in range(2500)], size=900)
    print('\npid_chunks(2500, 900) → 块数=%d 各块=%s' % (len(ch), [len(x) for x in ch]))

    # Session 截断如实标记
    big = Session()
    t = big.add_turn('q', 'spec', ['x%d' % i for i in range(25000)], 25000, max_pids=20000)
    print('截断标记 → truncated=%s 存=%d total=%d' % (t['truncated'], len(t['result_pids']), t['result_total']))

    print('\n指代分类不符 %d 项' % bad)
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    import sys
    sys.exit(_selftest())
