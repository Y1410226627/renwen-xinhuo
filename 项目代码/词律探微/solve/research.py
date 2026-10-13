# -*- coding: utf-8 -*-
"""research.py —— 研究库（`data/research.db`）：批次功能 6/7/8/12/13/15/18 的共同存储层。

**为什么单独一个库**（交接提示词硬约束 3）：`data/corpus.db` 是交付用的**只读**语料
（58,852 篇，任何新功能都不得往里写）。研究库是「用户自己的档案柜」：
文献摘录（功能 6）、研究事实（功能 7）、读音裁定（功能 8）、个人录入（功能 12）、
导入批次（功能 13）、文本版本链（功能 15）全在这里——**自带审计痕迹、绝不覆盖历史**。

**三条纪律**（整个模块围绕它们设计）：
  1. **写操作全部经 `_write()`**：底层是 `BEGIN IMMEDIATE` 事务 + 进程内
     `threading.Lock`——`http.server` 是多线程的，SQLite 需要一个明确的串行化点；
  2. **写操作统一支持 `client_token` 幂等**（功能 18）：同一个 token 重复提交
     **返回第一次的结果**、绝不重复执行——由 `run_idempotent()` 一处兜底，
     不靠各接口自己记得查重；
  3. **绝不覆盖历史**：材料修订 = 追加新版本（`material_revisions.parent_id` 成链）；
     文本 = 追加版本（`text_versions`）；元数据 = 追加修订（`meta_revisions`）；
     删除 = 撤回标记（行保留）；人工裁定 = 写**决策事件**（`decisions`），
     派生数据（如标定表）由决策事件**重新派生**，不许手改（功能 8 的红线）。

**术语**（对齐 `GLOSSARY.md`）：
  · 决策事件（decision event）——「谁 / 何时 / 对什么 / 做了什么 / 依据 / 为什么」一条记录；
  · 撤回（withdraw）——把一条记录标记为失效，但**行仍在**，且撤回本身也是决策事件。
"""
import hashlib
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import urlparse

from corpus import HAN_CLASS as _HAN_CLASS      # 汉字判定单一来源（与 pronounce/prosody 同口径）
from corpus import like_escape as _like_escape  # LIKE 通配转义单一来源（★ 审查 M1，2026-10-11）
from pronounce import Pronouncer, default_overrides_path   # 个人作品解析共用同一注音器
from prosody import Engine                          # 个人作品声律指标（与 build_corpus 同口径）

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(_ROOT, 'data', 'research.db')

_LOCK = threading.Lock()

# ---------------------------------------------------------------- 表结构
# 说明：全部 `IF NOT EXISTS`——研究库可能被多次打开，建表必须是幂等的。
SCHEMA = """
CREATE TABLE IF NOT EXISTS idempotency (
  token      TEXT PRIMARY KEY,          -- 客户端幂等键（唯一；重复提交靠它回读结果）
  endpoint   TEXT NOT NULL,             -- 首次执行时的接口名（诊断用）
  response   TEXT NOT NULL,             -- 首次执行的完整响应（JSON），重复提交原样返回
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           TEXT NOT NULL,
  actor        TEXT NOT NULL DEFAULT 'human',   -- human / import / derived…
  kind         TEXT NOT NULL,                   -- pronounce / material / fact / version / verify…
  subject      TEXT NOT NULL DEFAULT '',        -- 作用对象（pid|line|pos 等）
  action       TEXT NOT NULL,                   -- create / select / withdraw / revise…
  payload      TEXT,                            -- JSON：选了什么/改了什么
  basis        TEXT,                            -- 依据（来源、参考、比对结果）
  why          TEXT,                            -- 为什么（人话理由）
  prev_id      INTEGER,                         -- 撤回/修订指向的原决策 id（可空）
  client_token TEXT
);
CREATE INDEX IF NOT EXISTS ix_decisions_kind ON decisions(kind, subject);

CREATE TABLE IF NOT EXISTS materials (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at    TEXT NOT NULL,
  kind          TEXT NOT NULL DEFAULT 'book',   -- book / paper / web / archive…
  title         TEXT NOT NULL,
  author        TEXT,
  year          TEXT,
  source_url    TEXT,
  note          TEXT,
  withdrawn     INTEGER NOT NULL DEFAULT 0,     -- 删除=撤回标记（行保留）
  withdrawn_at  TEXT,
  withdrawn_why TEXT
);

CREATE TABLE IF NOT EXISTS material_revisions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  material_id INTEGER NOT NULL,
  parent_id   INTEGER,                          -- 父版本；首版为 NULL，成链
  created_at  TEXT NOT NULL,
  actor       TEXT NOT NULL DEFAULT 'human',
  content     TEXT NOT NULL,                    -- 摘录正文
  locator     TEXT,                             -- 页码/章节/行号等定位
  note        TEXT,
  content_sha TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mrev_material ON material_revisions(material_id, id);

CREATE TABLE IF NOT EXISTS facts (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at  TEXT NOT NULL,
  statement   TEXT NOT NULL,                    -- 可复核的陈述
  material_id INTEGER,                          -- 出处：材料（可空）
  locator     TEXT,                             -- 出处：材料内的定位
  poem_pid    TEXT,                             -- 出处：作品（可空）
  line_idx    INTEGER,                          -- 第几句（0 起）
  span_start  INTEGER,                          -- 字符区间（codepoint，半开）
  span_end    INTEGER,
  evidence    TEXT,                             -- 引文（必须与原文逐字一致，门禁验证）
  verified    INTEGER NOT NULL DEFAULT 0,       -- 是否已与原文/材料核对
  withdrawn   INTEGER NOT NULL DEFAULT 0,
  client_token TEXT
);
CREATE INDEX IF NOT EXISTS ix_facts_poem ON facts(poem_pid);

CREATE TABLE IF NOT EXISTS text_versions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  pid          TEXT NOT NULL,                   -- 作品 id（corpus pid 或 personal:<n>）
  scope        TEXT NOT NULL DEFAULT 'corpus',  -- corpus / personal
  parent_id    INTEGER,                         -- 父版本；首版为 NULL，成链
  version_type TEXT NOT NULL DEFAULT 'manual',  -- import / transcribe / correction / manual
  created_at   TEXT NOT NULL,
  actor        TEXT NOT NULL DEFAULT 'human',
  content      TEXT NOT NULL,
  content_sha  TEXT NOT NULL,
  note         TEXT
);
CREATE INDEX IF NOT EXISTS ix_tv_pid ON text_versions(scope, pid, id);

CREATE TABLE IF NOT EXISTS meta_revisions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  pid        TEXT NOT NULL,
  scope      TEXT NOT NULL DEFAULT 'corpus',
  created_at TEXT NOT NULL,
  actor      TEXT NOT NULL DEFAULT 'human',
  field      TEXT NOT NULL,                     -- author / title / cipai …
  old_value  TEXT,
  new_value  TEXT,
  basis      TEXT,
  why        TEXT
);
CREATE INDEX IF NOT EXISTS ix_mr_pid ON meta_revisions(scope, pid, id);

CREATE TABLE IF NOT EXISTS personal_works (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at         TEXT NOT NULL,
  author             TEXT,
  title              TEXT NOT NULL,
  cipai              TEXT,
  content            TEXT NOT NULL,
  verification_state TEXT NOT NULL DEFAULT 'draft',  -- draft / material_sample / source_matched
  source             TEXT,                           -- 来源说明（source_matched 必填）
  source_material_id INTEGER,
  source_locator     TEXT,
  checked_at         TEXT,
  checked_by         TEXT,
  withdrawn          INTEGER NOT NULL DEFAULT 0,     -- ★ 删除=撤回标记（行保留；M10）
  withdrawn_at       TEXT,
  withdrawn_why      TEXT
);

CREATE TABLE IF NOT EXISTS import_batches (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at   TEXT NOT NULL,
  tag          TEXT NOT NULL,                   -- 批次名（人给）
  manifest_sha TEXT NOT NULL,                   -- 清单/文件集合的哈希（对账）
  files        INTEGER NOT NULL DEFAULT 0,
  n_rows       INTEGER NOT NULL DEFAULT 0,
  status       TEXT NOT NULL DEFAULT 'committed',  -- committed / rolled_back
  note         TEXT
);

CREATE TABLE IF NOT EXISTS import_rows (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL,
  file     TEXT NOT NULL,
  row_key  TEXT NOT NULL,                       -- 行唯一键＝内容 sha（同内容第 n 次出现加 `#n`）
  row_sha  TEXT NOT NULL,
  payload  TEXT,
  work_ref INTEGER,                             -- 落到 personal_works.id（回滚据此连带撤下）
  UNIQUE(file, row_key)                         -- ★ 幂等的落点：同一文件同一行只存一次
);

-- ★ 2026-10-13 新增（吸收 cilyutanwei 的 argument_revisions 设计）：
--   **可编辑论证稿 + 修订链**。旧实现里论证草稿只是一段随答案返回的文本，**不是实体**，
--   既不能编辑、也不能留版本、更不能导出。这里把它落成实体：一篇稿 = 一行 draft，
--   每次编辑**追加**一条 revision（旧版永不覆盖），与「材料/事实/版本链」同一纪律。
CREATE TABLE IF NOT EXISTS argument_drafts (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at   TEXT NOT NULL,
  origin       TEXT NOT NULL DEFAULT 'answer_organized',  -- answer_organized / user_edited
  snapshot_id  TEXT,                                       -- 来源快照 id（可空；从快照整理时填）
  question     TEXT,                                       -- 来源问句（人可读）
  title        TEXT,                                       -- 稿题（人给或从问句生成）
  withdrawn    INTEGER NOT NULL DEFAULT 0,                 -- 删除=撤回标记（行保留）
  withdrawn_at TEXT,
  withdrawn_why TEXT
);

CREATE TABLE IF NOT EXISTS argument_revisions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id   INTEGER NOT NULL,
  revision   INTEGER NOT NULL,                  -- 从 1 起递增
  parent_id  INTEGER,                           -- 父修订；首版为 NULL，成链
  created_at TEXT NOT NULL,
  actor      TEXT NOT NULL DEFAULT 'human',
  data       TEXT NOT NULL,                     -- JSON：{thesis, claims[], limitations[], note}
  note       TEXT,
  data_sha   TEXT NOT NULL,                     -- 该修订内容的哈希（对账/去重）
  UNIQUE(draft_id, revision)
);
CREATE INDEX IF NOT EXISTS ix_argrev_draft ON argument_revisions(draft_id, revision);
"""


# ---------------------------------------------------------------- 基础
def _now():
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


def _row(cur, r):
    """★ 2026-10-11（审查·低）：把一行结果转成 dict，**不假定** `row_factory`。

    `dict(r)` 只在 `row_factory=sqlite3.Row` 下成立；本项目**外部传入**的连接
    （门禁 / 脚本 / 其它模块）并不保证设了 row_factory——踩过一次坑（`row[0]` 才稳）。
    这里兜底：不是 Row 就按 `cur.description` 拼列名，两条路返回同一个结构。
    """
    if r is None:
        return None
    try:
        return dict(r)
    except (TypeError, ValueError):
        desc = getattr(cur, 'description', None) or []
        return {d[0]: r[i] for i, d in enumerate(desc)}


def content_sha(text):
    """内容哈希（前 16 位十六进制；版本链/幂等对账共用，稳定且够短）。"""
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()[:16]


def connect(path=None):
    """打开（必要时创建）研究库。调用方通常传项目根的 `data/research.db`。

    · `isolation_level=None` → 事务由本模块显式控制（`BEGIN IMMEDIATE`）；
    · WAL 模式允许「一写多读」并发；`busy_timeout` 等锁 8 秒而非立即报错；
    · 建表幂等（`IF NOT EXISTS`），打开即就绪。
    """
    p = path or DEFAULT_PATH
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(p, timeout=10, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=8000')
        conn.executescript(SCHEMA)
        _migrate(conn)
    except sqlite3.Error:
        conn.close()
        raise
    return conn


# ★ 2026-10-11（审查 M10）：**加列迁移**。`CREATE TABLE IF NOT EXISTS` 对**已存在**的库
#   不会补列，于是老库里的 `personal_works` 没有 `withdrawn` 三列——回滚只能物理删除。
#   这里显式补齐（幂等：列已存在则跳过），保证「删除=撤回标记（行保留）」这条纪律
#   对新库老库一视同仁。
_MIGRATIONS = (
    ('personal_works', 'withdrawn', 'INTEGER NOT NULL DEFAULT 0'),
    ('personal_works', 'withdrawn_at', 'TEXT'),
    ('personal_works', 'withdrawn_why', 'TEXT'),
)


def _migrate(conn):
    """补列迁移。**幂等**：列已存在就跳过（`CREATE TABLE IF NOT EXISTS` 对已存在的库不补列）。

    ⚠ 2026-10-11 二修：`PRAGMA table_info` 返回的列序是 `cid, name, type, notnull,
      dflt_value, pk`——**列名是第 2 个字段（`r[1]`）**，不是 `r[0]`（那是 cid 0/1/2…）。
      首版误取 `r[0]`，于是 `'withdrawn' not in [0,1,2,…]` 恒为真 → 每次 `connect()`
      都对**已有该列**的表执行 ALTER → `duplicate column name: withdrawn` →
      **研究库打不开**（首跑即崩，本轮 `web/test_api.py` 实测抓到）。
    """
    for tab, col, ddl in _MIGRATIONS:
        try:
            cur = conn.execute('PRAGMA table_info(%s)' % tab)
            cols = [r[1] for r in cur]
        except sqlite3.Error:
            continue
        if cols and col not in cols:
            conn.execute('ALTER TABLE %s ADD COLUMN %s %s' % (tab, col, ddl))


@contextmanager
def write_txn(conn):
    """写事务：进程内锁（串行化点）+ `BEGIN IMMEDIATE`（立即取库锁）。

    ⚠ 只允许在最外层调用；事务内的复合操作请用 `_write()`（它会识别
      `conn.in_transaction`，不会嵌套加锁）。
    """
    with _LOCK:
        conn.execute('BEGIN IMMEDIATE')
        try:
            yield conn
            conn.execute('COMMIT')
        except BaseException:
            try:
                conn.execute('ROLLBACK')
            except sqlite3.Error:
                pass
            raise


def _write(conn, fn):
    """在写事务里执行 `fn(conn)`；若已在事务内（如 `run_idempotent` 的回调里）则直接执行。"""
    if conn.in_transaction:
        return fn(conn)
    with write_txn(conn):
        return fn(conn)


# ---------------------------------------------------------------- 功能 18：幂等键
def run_idempotent(conn, token, endpoint, fn):
    """**幂等执行**（功能 18）：同一 `client_token` 只执行一次。

    · 首次：执行 `fn(conn)`（写业务行），把返回的 JSON 存进 `idempotency`，返回之；
    · 重复：**不再执行** `fn`，直接把第一次的响应原样返回（用户重试/网络重发安全）；
    · 并发：两线程同时提交同一 token → 进程内锁 + `BEGIN IMMEDIATE` 序列化，
      第二者必然在事务里先读到已存响应 → 返回同一结果；
    · 无 token（None/空）：不启用幂等，正常执行一次（调用方明确不要求去重时）。
    """
    if not token:
        return _write(conn, fn)
    token = str(token)[:128]

    def _run(conn2):
        # ★ 2026-10-11（审查 M8）：改前**只按 token 查**，`endpoint` 只写不查——
        #   前端部分 token 是确定性拼接（如 `pron:<pid>:<line>:<pos>:<reading>`、
        #   `wd:<decision_id>`），同一 token 换个接口/换参数提交 → 静默返回**首次的异构结果**
        #   （写的是 A 接口，拿回的是 B 接口的响应——最坏情况是用户以为操作成功了，其实没有）。
        #   改后：连带校验 endpoint；不符即**报冲突**（ValueError → 400），绝不静默复用。
        row = conn2.execute(
            'SELECT response, endpoint FROM idempotency WHERE token=?', (token,)).fetchone()
        if row is not None:
            prev = row['endpoint'] if isinstance(row, sqlite3.Row) else row[1]
            if prev is not None and endpoint is not None and prev != endpoint:
                raise ValueError('幂等键冲突：token %r 已用于接口 %s，本次却是 %s——'
                                 '请换一个 client_token（同键不得跨接口复用）'
                                 % (token, prev, endpoint))
            raw = row['response'] if isinstance(row, sqlite3.Row) else row[0]
            return json.loads(raw)
        res = fn(conn2)
        conn2.execute(
            'INSERT INTO idempotency(token, endpoint, response, created_at) VALUES(?,?,?,?)',
            (token, endpoint, json.dumps(res, ensure_ascii=False), _now()))
        return res

    return _write(conn, _run)


def get_idempotent(conn, token):
    """（诊断/门禁用）按 token 读出已存响应；不存在返回 None。"""
    if not token:
        return None
    _cur = conn.execute('SELECT response, endpoint, created_at FROM idempotency WHERE token=?',
                        (str(token)[:128],))
    row = _cur.fetchone()
    if row is None:
        return None
    # ★ 2026-10-11（审查·低）：这里原来直接 `row['...']`，与同文件其它读路径一样**假定了
    #   `row_factory=Row`**。诊断/门禁会拿外部连接来调本函数，缺了 row_factory 就是
    #   `TypeError: tuple indices must be integers`（把"查得到"变成"炸"）。改用统一的 `_row`。
    d = _row(_cur, row)
    return {'response': json.loads(d['response']), 'endpoint': d['endpoint'],
            'created_at': d['created_at']}


# ---------------------------------------------------------------- 决策事件（功能 8/12/15 共用）
def _insert_decision(c, kind, subject, action, payload=None, basis='', why='', actor='human',
                     prev_id=None, client_token=None):
    """**事务内**插入一条决策事件（不发事务；供其它写函数在同一事务里连带记录）。"""
    ts = _now()
    payload_s = json.dumps(payload, ensure_ascii=False) if payload is not None else None
    cur = c.execute(
        'INSERT INTO decisions(ts,actor,kind,subject,action,payload,basis,why,prev_id,client_token)'
        ' VALUES(?,?,?,?,?,?,?,?,?,?)',
        (ts, actor, kind, subject, action, payload_s, basis, why, prev_id, client_token))
    return {'decision_id': cur.lastrowid, 'ts': ts, 'kind': kind,
            'subject': subject, 'action': action}


def record_decision(conn, kind, subject, action, payload=None, basis='', why='',
                    actor='human', prev_id=None, client_token=None):
    """写一条**决策事件**：「谁 / 何时 / 对什么 / 做了什么 / 依据 / 为什么」。

    · `actor` 至少记录来源类别（`human` 人工 / `import` 导入 / `derived` 派生），
      与竞品「硬编码 local_researcher」区分——来源是**可核对的字段**，不是装饰；
    · 撤回也是一个动作（`action='withdraw'`，`prev_id` 指向被撤回的决策），
      **撤回本身留痕**（功能 8 验收：决策事件可完整回溯，含撤回本身）。
    """
    def fn(c):
        return _insert_decision(c, kind, subject, action, payload, basis, why, actor,
                                prev_id, client_token)

    if client_token:
        return run_idempotent(conn, client_token, 'decisions', fn)
    return _write(conn, fn)


def list_decisions(conn, kind=None, subject=None, limit=200):
    """按（可选）类别/对象列决策事件，新的在前。"""
    sql = 'SELECT * FROM decisions WHERE 1=1'
    args = []
    if kind:
        sql += ' AND kind=?'
        args.append(kind)
    if subject:
        sql += ' AND subject=?'
        args.append(subject)
    sql += ' ORDER BY id DESC LIMIT ?'
    args.append(int(limit))
    _cur = conn.execute(sql, args)
    return [_row(_cur, r) for r in _cur]


def get_decision(conn, decision_id):
    _cur = conn.execute('SELECT * FROM decisions WHERE id=?', (int(decision_id),))
    r = _cur.fetchone()
    return _row(_cur, r) if r else None


# ---------------------------------------------------------------- 功能 15：文本版本链 + 元数据修订史
def add_text_version(conn, pid, content, scope='corpus', version_type='manual',
                     actor='human', note='', parent_id=None, client_token=None):
    """追加一个**文本版本**（功能 15）：原文不可覆盖，每次修订成链。

    · `parent_id=None` 时自动挂到该 `pid` 的**当前最新版本**（首版则为 None）；
    · 返回体含 `content_sha` 与 `id`，供调用方展示与后续引用；
    · 支持 `client_token` 幂等（重复提交返回同一版本，不产生重复行）。
    """
    sha = content_sha(content)

    def fn(c):
        if parent_id is None:
            r = c.execute('SELECT id FROM text_versions WHERE pid=? AND scope=?'
                          ' ORDER BY id DESC LIMIT 1', (pid, scope)).fetchone()
            parent = r['id'] if r else None
        else:
            parent = int(parent_id)
        # ★ 2026-10-11（审查·低）：改前 INSERT 与返回体**各调一次** `_now()`——
        #   跨过整秒边界时，返回给前端的 `created_at` 与库里存的那一行**差 1 秒**，
        #   前端拿它回显、拿库值排序，就会「我刚提交的版本显示排在下一秒」。
        #   时间戳必须**一次取准、两处共用**。
        ts = _now()
        cur = c.execute(
            'INSERT INTO text_versions(pid,scope,parent_id,version_type,created_at,actor,'
            'content,content_sha,note) VALUES(?,?,?,?,?,?,?,?,?)',
            (pid, scope, parent, version_type, ts, actor, content, sha, note))
        return {'id': cur.lastrowid, 'pid': pid, 'scope': scope, 'parent_id': parent,
                'version_type': version_type, 'content_sha': sha,
                'created_at': ts}

    return run_idempotent(conn, client_token, 'text_versions', fn)


def list_text_versions(conn, pid, scope=None):
    """按 id 升序列出某篇的全部版本（旧→新），逐版带 parent_id 与 sha。"""
    sql = 'SELECT * FROM text_versions WHERE pid=?'
    args = [pid]
    if scope:
        sql += ' AND scope=?'
        args.append(scope)
    sql += ' ORDER BY id'
    _cur = conn.execute(sql, args)
    return [_row(_cur, r) for r in _cur]


def latest_text_version(conn, pid, scope=None):
    sql = 'SELECT * FROM text_versions WHERE pid=?'
    args = [pid]
    if scope:
        sql += ' AND scope=?'
        args.append(scope)
    sql += ' ORDER BY id DESC LIMIT 1'
    _cur = conn.execute(sql, args)
    r = _cur.fetchone()
    return _row(_cur, r) if r else None


def add_meta_revision(conn, pid, field, new_value, old_value=None, scope='corpus',
                      actor='human', basis='', why='', client_token=None):
    """追加一条**元数据修订**（作者/题名/词牌）：留旧值、新值、依据与理由。"""

    def fn(c):
        cur = c.execute(
            'INSERT INTO meta_revisions(pid,scope,created_at,actor,field,old_value,new_value,'
            'basis,why) VALUES(?,?,?,?,?,?,?,?,?)',
            (pid, scope, _now(), actor, field, old_value, new_value, basis, why))
        return {'id': cur.lastrowid, 'pid': pid, 'field': field,
                'old_value': old_value, 'new_value': new_value}

    return run_idempotent(conn, client_token, 'meta_revisions', fn)


def list_meta_revisions(conn, pid, scope=None):
    sql = 'SELECT * FROM meta_revisions WHERE pid=?'
    args = [pid]
    if scope:
        sql += ' AND scope=?'
        args.append(scope)
    sql += ' ORDER BY id'
    _cur = conn.execute(sql, args)
    return [_row(_cur, r) for r in _cur]


# ---------------------------------------------------------------- 功能 6：文献摘录库（append-only）

#: ★ 2026-10-11（审查 H4）：来源地址**只接受 http/https**。
#:   改前 `source_url` 原样入库、原样回吐，前端直接 `:href` → 存
#:   `javascript:alert(document.cookie)` 一点即执行（**点击型存储 XSS**；
#:   `rel="noopener"` 只防 `window.opener`，**防不住伪协议**）。
#:   故在**写入侧**就挡住（而不是渲染时悄悄改）——不符合的一律拒绝并说明原因，
#:   绝不静默改写用户填的内容。
URL_SCHEMES_OK = ('http', 'https')


def safe_url(u, field='source_url', required=False):
    """校验并返回来源地址；只放行 http/https。空串（不填）合法通过。

    `required=True` 时空串也报错（用于"这条材料必须有出处"的场景）。
    """
    s = (u or '').strip()
    if not s:
        if required:
            raise ValueError('%s 为必填' % field)
        return ''
    try:
        sc = (urlparse(s).scheme or '').lower()
    except Exception:                                            # noqa: BLE001
        raise ValueError('%s 无法解析，请填完整的 http(s) 链接' % field)
    if sc not in URL_SCHEMES_OK:
        raise ValueError('%s 只允许 http/https（收到「%s」）——`javascript:`、`data:` 等伪协议'
                         '会被浏览器当脚本执行，故在入库前挡住' % (field, sc or '无协议'))
    return s


def url_is_safe(u):
    """只读判定（**输出侧兜底**）：该地址能否安全渲染成链接。

    写入侧已挡住新数据，但**历史行**里可能已有不合规值——回吐时一律按这个判定，
    不安全的**原样当文本显示**（不生成 `<a href>`），保证"老数据也点不出脚本"。
    """
    s = (u or '').strip()
    if not s:
        return False
    try:
        return (urlparse(s).scheme or '').lower() in URL_SCHEMES_OK
    except Exception:                                            # noqa: BLE001
        return False


def add_material(conn, title, content, kind='book', author='', year='', source_url='',
                 note='', locator='', actor='human', client_token=None):
    """新建**文献摘录**：材料本体 + 首个版本一气呵成。

    append-only 纪律（功能 6 验收）：此后「编辑」一律走 `add_material_revision`
    （**追加新版本**，父版本保留），本模块不提供任何覆盖旧行的 update 路径；
    「删除」走 `withdraw_material`（标记撤回，行仍在）。
    """
    if not (title or '').strip() or not (content or '').strip():
        raise ValueError('title 与 content 为必填')
    # ★ 2026-10-11（审查 H4）：来源地址只放行 http/https（防 `javascript:` 伪协议的存储型 XSS）
    source_url = safe_url(source_url)

    def fn(c):
        cur = c.execute('INSERT INTO materials(created_at,kind,title,author,year,source_url,note)'
                        ' VALUES(?,?,?,?,?,?,?)',
                        (_now(), kind, title, author, year, source_url, note))
        mid = cur.lastrowid
        cur2 = c.execute('INSERT INTO material_revisions(material_id,parent_id,created_at,actor,'
                         'content,locator,note,content_sha) VALUES(?,?,?,?,?,?,?,?)',
                         (mid, None, _now(), actor, content, locator, note, content_sha(content)))
        return {'material_id': mid, 'revision_id': cur2.lastrowid,
                'content_sha': content_sha(content), 'version': 1}

    return run_idempotent(conn, client_token, 'materials', fn)


def add_material_revision(conn, material_id, content, locator='', note='', actor='human',
                          client_token=None):
    """**修订 = 追加新版本**（旧行不覆盖）：`parent_id` 自动挂到该材料的当前最新版本。"""
    if not (content or '').strip():
        raise ValueError('content 为必填')

    def fn(c):
        mid = int(material_id)
        _cm = c.execute('SELECT id, withdrawn FROM materials WHERE id=?', (mid,))
        mat = _row(_cm, _cm.fetchone())
        if mat is None:
            raise ValueError('材料 %s 不存在' % material_id)
        if mat['withdrawn']:
            raise ValueError('材料 %s 已撤回，不能再追加版本（如需恢复请新建材料）' % material_id)
        prev = c.execute('SELECT id FROM material_revisions WHERE material_id=?'
                         ' ORDER BY id DESC LIMIT 1', (mid,)).fetchone()
        parent = prev['id'] if prev else None
        cur = c.execute('INSERT INTO material_revisions(material_id,parent_id,created_at,actor,'
                        'content,locator,note,content_sha) VALUES(?,?,?,?,?,?,?,?)',
                        (mid, parent, _now(), actor, content, locator, note, content_sha(content)))
        n = c.execute('SELECT COUNT(1) FROM material_revisions WHERE material_id=?',
                      (mid,)).fetchone()[0]
        return {'material_id': mid, 'revision_id': cur.lastrowid, 'parent_id': parent,
                'content_sha': content_sha(content), 'version': n}

    return run_idempotent(conn, client_token, 'material_revisions', fn)


def withdraw_material(conn, material_id, why='', actor='human', client_token=None):
    """删除 = **撤回标记**（行保留）+ 决策事件留痕（撤回本身可回溯）。"""

    def fn(c):
        mid = int(material_id)
        _cm = c.execute('SELECT id, withdrawn FROM materials WHERE id=?', (mid,))
        mat = _row(_cm, _cm.fetchone())
        if mat is None:
            raise ValueError('材料 %s 不存在' % material_id)
        if mat['withdrawn']:
            return {'material_id': mid, 'withdrawn': True, 'note': '此前已撤回'}
        c.execute('UPDATE materials SET withdrawn=1, withdrawn_at=?, withdrawn_why=? WHERE id=?',
                  (_now(), why, mid))
        d = _insert_decision(c, 'material', 'material:%d' % mid, 'withdraw',
                             payload={'material_id': mid}, basis='用户操作', why=why, actor=actor)
        return {'material_id': mid, 'withdrawn': True, 'decision_id': d['decision_id']}

    return run_idempotent(conn, client_token, 'materials/withdraw', fn)


def list_materials(conn, include_withdrawn=False):
    """材料列表（新在前），每条带**版本数**与最新版本预览。"""
    sql = ('SELECT m.*,'
           ' (SELECT COUNT(1) FROM material_revisions r WHERE r.material_id=m.id) AS n_rev,'
           ' (SELECT r.content FROM material_revisions r WHERE r.material_id=m.id'
           '  ORDER BY r.id DESC LIMIT 1) AS latest_content,'
           ' (SELECT r.created_at FROM material_revisions r WHERE r.material_id=m.id'
           '  ORDER BY r.id DESC LIMIT 1) AS latest_at'
           ' FROM materials m')
    if not include_withdrawn:
        sql += ' WHERE m.withdrawn=0'
    sql += ' ORDER BY m.id DESC'
    # ★ 2026-10-11（审查 H4）：**输出侧兜底**——写入侧已挡住新数据，但历史行可能已有
    #   不合规值；这里在**出库的最后一米**再判一次，不安全的地址一律置空，
    #   并如实标注原因（`url_unsafe`），前端据此"当文本显示、不生成 <a href>"。
    _cur = conn.execute(sql)
    return [_sanitize_url_row(_row(_cur, r)) for r in _cur]


def _sanitize_url_row(row):
    """把一行里的 `source_url` 判安全后才保留；不合规 → 置空 + `url_unsafe` 标注。"""
    if not isinstance(row, dict):
        return row
    u = row.get('source_url') or ''
    if u and not url_is_safe(u):
        row['source_url'] = ''
        row['url_unsafe'] = True
    return row


def get_material_chain(conn, material_id):
    """材料 + **全部版本链**（旧→新，逐版带 parent_id / sha / 定位）。不存在返回 None。"""
    mid = int(material_id)
    _c0 = conn.execute('SELECT * FROM materials WHERE id=?', (mid,))
    mat = _c0.fetchone()
    if mat is None:
        return None
    _c1 = conn.execute('SELECT * FROM material_revisions WHERE material_id=? ORDER BY id',
                       (mid,))
    revs = _c1.fetchall()
    # ★ 2026-10-11（审查 H4）：与 `list_materials` 同一道输出侧兜底
    return {'material': _sanitize_url_row(_row(_c0, mat)),
            'revisions': [_row(_c1, r) for r in revs]}


# ---------------------------------------------------------------- 功能 7：研究事实库
def verify_fact_evidence(corpus_conn, poem_pid, line_idx, evidence,
                         span_start=None, span_end=None):
    """把「引文」与语料原文**逐字核对**（功能 7 硬约束：找不到出处的不许入库）。

    返回 `(ok, detail)`。核验口径（与 `corpus.db` 的 `lines`/`poems` 表直接对齐）：
      · 给了 `line_idx`：在该**句**里找（原样文本，含句末标点，句序从 0 起）；
      · 未给：在该篇 `raw` 全篇里找；
      · 给了 `span_start/span_end`：区间内容必须**恰等于**引文（最强定位，char 索引）。
    """
    try:
        if line_idx is not None:
            row = corpus_conn.execute('SELECT text FROM lines WHERE pid=? AND idx=?',
                                      (poem_pid, int(line_idx))).fetchone()
            text = row[0] if row else None      # 位置索引：调用方连接未必设 row_factory
            where = '第 %d 句' % (int(line_idx) + 1)
        else:
            row = corpus_conn.execute('SELECT raw FROM poems WHERE pid=?', (poem_pid,)).fetchone()
            text = row[0] if row else None
            where = '全篇'
    except Exception as e:                                        # noqa: BLE001
        return (False, '语料不可读：%r' % e)
    if not text:
        return (False, '篇/句不在语料中（pid=%s，%s）' % (poem_pid, where))
    if span_start is not None and span_end is not None:
        seg = text[int(span_start):int(span_end)]
        if seg != evidence:
            return (False, '区间内容与引文不一致：%r ≠ %r' % (seg, evidence))
        return (True, '区间逐字一致')
    if evidence and evidence in text:
        return (True, '%s内逐字命中' % where)
    return (False, '引文在%s中找不到（须逐字一致）' % where)


def add_fact(conn, statement, material_id=None, locator='', poem_pid=None, line_idx=None,
             span_start=None, span_end=None, evidence='', actor='human',
             corpus_conn=None, client_token=None):
    """登记一条**研究事实**：陈述 + 出处 + 定位（功能 7）。

    两条硬约束：
      1. **必须有出处**：`material_id` 或 `poem_pid` 至少给一个——
         「找不到出处的不许入库」，这里直接拒绝并说明原因；
      2. 给 `poem_pid` + `evidence` 时**逐字核验**：传了 `corpus_conn` 就真核验、
         不一致即拒绝入库；没传就**不假装核验过**（`verified=False` 并注明未核对）。
    """
    if not (statement or '').strip():
        raise ValueError('statement 为必填')
    if material_id is None and not poem_pid:
        raise ValueError('找不到出处的登记不许入库：material_id 或 poem_pid 至少给一个')
    verified, detail = 0, '未核对'
    if poem_pid and evidence and corpus_conn is not None:
        vok, detail = verify_fact_evidence(corpus_conn, poem_pid, line_idx, evidence,
                                           span_start, span_end)
        if not vok:
            raise ValueError('引文与原文不一致，拒绝入库：%s' % detail)
        verified = 1
    elif poem_pid and evidence:
        detail = '未核对（调用方未提供语料连接）'

    def fn(c):
        cur = c.execute(
            'INSERT INTO facts(created_at,statement,material_id,locator,poem_pid,line_idx,'
            'span_start,span_end,evidence,verified,client_token) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (_now(), statement, material_id, locator, poem_pid, line_idx, span_start,
             span_end, evidence, verified, client_token))
        return {'fact_id': cur.lastrowid, 'verified': bool(verified), 'verify_detail': detail}

    return run_idempotent(conn, client_token, 'facts', fn)


def withdraw_fact(conn, fact_id, why='', actor='human', client_token=None):
    """撤回一条事实（行保留 + 决策事件留痕）。"""

    def fn(c):
        fid = int(fact_id)
        _cf = c.execute('SELECT id, withdrawn FROM facts WHERE id=?', (fid,))
        row = _row(_cf, _cf.fetchone())
        if row is None:
            raise ValueError('事实 %s 不存在' % fact_id)
        if row['withdrawn']:
            return {'fact_id': fid, 'withdrawn': True, 'note': '此前已撤回'}
        c.execute('UPDATE facts SET withdrawn=1 WHERE id=?', (fid,))
        d = _insert_decision(c, 'fact', 'fact:%d' % fid, 'withdraw',
                             payload={'fact_id': fid}, basis='用户操作', why=why, actor=actor)
        return {'fact_id': fid, 'withdrawn': True, 'decision_id': d['decision_id']}

    return run_idempotent(conn, client_token, 'facts/withdraw', fn)


def list_facts(conn, poem_pid=None, material_id=None, include_withdrawn=False):
    """事实列表（新在前），可按作品/材料过滤。"""
    sql = 'SELECT * FROM facts WHERE 1=1'
    args = []
    if poem_pid:
        sql += ' AND poem_pid=?'
        args.append(poem_pid)
    if material_id is not None:
        sql += ' AND material_id=?'
        args.append(int(material_id))
    if not include_withdrawn:
        sql += ' AND withdrawn=0'
    sql += ' ORDER BY id DESC LIMIT 500'
    _cur = conn.execute(sql, args)
    return [_row(_cur, r) for r in _cur]


# ---------------------------------------------------------------- 功能 8：读音裁定（决策事件派生）
# 裁定主体：`(篇, 句序, 字位)` —— 字位 = 该句第几个**汉字**（0 起，跳过标点；与 pz 串下标一致）。
# 三条纪律（交接提示词功能 8）：
#   · 人工选定 / 撤回**一律写决策事件**（`decisions` 表，kind='pronounce'）——
#     不许手改 `solve/data/pron_overrides.json`（那是**字级基线表**，由 tools/calibrate.py
#     坐标下降得到，与「篇级人工裁定」是两层，互不覆盖）；
#   · 展示层（解析页 / 问答证据块）的「当前有效裁定」由决策事件**重放派生**
#     （`effective_pron_decisions`），撤回就是把 select 撤下、回到基线；
#   · **没做过裁定的篇逐字节不变**（零回归生命线）。
_PRON_SUBJECT_RE = re.compile(r'^(?P<pid>.+)\|line=(?P<line>\d+)\|pos=(?P<pos>\d+)$')
_HAN_RE = re.compile('[%s]' % _HAN_CLASS)


def pron_subject(pid, line_idx, char_pos):
    """裁定对象的规范键：`<pid>|line=<句序>|pos=<字位>`。"""
    return '%s|line=%d|pos=%d' % (pid, int(line_idx), int(char_pos))


def add_pron_decision(conn, pid, line_idx, char_pos, reading, tone, basis='', why='',
                      actor='human', client_token=None):
    """登记一条**读音裁定**（人工为「某篇某句某字」选定读音）。

    · `reading` 形如 `'chang2'`，`tone` ∈ 1..4，二者必须一致（声调写进两遍会对不上）；
    · 平仄由声调派生：1/2 声平、3/4 声仄（与题库口径、GLOSSARY 一致）；
    · 同一字位再次 `select` 即「**改选**」——旧裁定不删，历史仍在（重放取最新一条）；
    · 支持 `client_token` 幂等（重复提交返回同一决策 id）。
    """
    pid = str(pid or '').strip()
    if not pid:
        raise ValueError('pid 为必填')
    line_idx, char_pos, tone = int(line_idx), int(char_pos), int(tone)
    if line_idx < 0 or char_pos < 0:
        raise ValueError('line / pos 不能为负')
    if tone not in (1, 2, 3, 4):
        raise ValueError('tone 必须是 1..4（轻声/无调不是可裁定项）')
    reading = str(reading or '').strip()
    m = re.search(r'([1-4])\s*$', reading)
    if not m or int(m.group(1)) != tone:
        raise ValueError('reading（%r）与 tone（%d）不一致：读音末尾声调须与 tone 相同'
                         % (reading, tone))

    def fn(c):
        return _insert_decision(
            c, 'pronounce', pron_subject(pid, line_idx, char_pos), 'select',
            payload={'reading': reading, 'tone': tone,
                     'pz': '仄' if tone in (3, 4) else '平'},
            basis=basis, why=why, actor=actor)

    return run_idempotent(conn, client_token, 'pronounce/decide', fn)


def withdraw_pron_decision(conn, decision_id, why='', actor='human', client_token=None):
    """撤回一条读音裁定（**撤回本身也是决策事件**，`prev_id` 指向原裁定）。"""

    def fn(c):
        did = int(decision_id)
        _cd = c.execute('SELECT * FROM decisions WHERE id=?', (did,))
        d = _row(_cd, _cd.fetchone())
        if d is None:
            raise ValueError('决策 %s 不存在' % decision_id)
        if d['kind'] != 'pronounce':
            raise ValueError('决策 %s 不是读音裁定（kind=%s）' % (decision_id, d['kind']))
        if d['action'] != 'select':
            raise ValueError('只能撤回 select 类裁定（该条 action=%s）' % d['action'])
        _ce = c.execute("SELECT id FROM decisions WHERE kind='pronounce'"
                        " AND action='withdraw' AND prev_id=?", (did,))
        exists = _row(_ce, _ce.fetchone())
        if exists:
            return {'withdraw_id': exists['id'], 'prev_id': did, 'note': '此前已撤回'}
        try:
            payload = json.loads(d['payload'] or '{}')
        except ValueError:
            payload = {}
        w = _insert_decision(c, 'pronounce', d['subject'], 'withdraw', payload=payload,
                             basis='用户操作', why=why, actor=actor, prev_id=did)
        return {'withdraw_id': w['decision_id'], 'prev_id': did, 'subject': d['subject']}

    return run_idempotent(conn, client_token, 'pronounce/withdraw', fn)


def effective_pron_decisions(conn, pid=None):
    """重放读音决策事件 → **当前有效裁定**。

    规则：按 id 升序重放——`select` 置入（同字位后来者覆盖先前者）；
    `withdraw` 把 `prev_id` 指向的 **select 且仍生效** 的那条撤下（撤回旧版不影响新版）。
    `pid` 给定时只回该篇列表；否则回 `{pid: [...]}`。库/表缺失时如实返回空。
    """
    try:
        _cur = conn.execute(
            "SELECT id,subject,action,payload,prev_id,ts FROM decisions"
            " WHERE kind='pronounce' ORDER BY id")
        rows = [_row(_cur, r) for r in _cur]
    except sqlite3.Error:
        return [] if pid is not None else {}
    id2sub = {r['id']: (r['subject'] or '') for r in rows}
    active = {}                      # subject → 当前生效的 select 行
    for r in rows:
        if r['action'] == 'select' and r['subject']:
            active[r['subject']] = r
        elif r['action'] == 'withdraw':
            subj = id2sub.get(r['prev_id'])
            cur = active.get(subj) if subj else None
            if cur is not None and cur['id'] == r['prev_id']:
                del active[subj]
    by_pid = {}
    for r in active.values():
        m = _PRON_SUBJECT_RE.match(r['subject'] or '')
        if not m:
            continue
        try:
            payload = json.loads(r['payload'] or '{}')
        except ValueError:
            payload = {}
        by_pid.setdefault(m.group('pid'), []).append({
            'line': int(m.group('line')), 'pos': int(m.group('pos')),
            'reading': payload.get('reading') or '', 'tone': int(payload.get('tone') or 0),
            'decision_id': r['id'], 'ts': r['ts']})
    for k in by_pid:
        by_pid[k].sort(key=lambda d: (d['line'], d['pos']))
    if pid is None:
        return by_pid
    return by_pid.get(pid, [])


def apply_pron_to_lines(conn, pid, lines):
    """把「该篇读音裁定」应用到逐句数据上 → `(lines, applied)`。

    解析页（`/api/parse`）与问答证据块（`evidence.poem_block`）**共用**这一份实现。
    修正范围（如实，不越界）：
      · 句内第 `pos` 个汉字对应的 `pz` 字符、该句 `ping`/`ze` 计数；
      · `applied` 逐条记录「字、原平仄、新平仄、裁定 id」供界面展示；
      · **篇级指标（ze_ratio/change…）与语料库不重算、不回写**——那是交付口径，
        本函数只影响「展示出来的这一份 lines」。
    字位不存在（越界）时**安全跳过、绝不猜**；无裁定时原样返回（零回归）。
    """
    dec = effective_pron_decisions(conn, pid)
    if not dec:
        return lines, []
    idx2line = {}
    for L in lines:
        idx2line[L.get('idx')] = L
    applied = []
    for d in dec:
        L = idx2line.get(d['line'])
        if L is None:
            continue
        text = L.get('text') or ''
        k, ch = -1, None
        for c0 in text:
            if _HAN_RE.match(c0):
                k += 1
                if k == d['pos']:
                    ch = c0
                    break
        if ch is None:
            continue                       # 字位不存在 → 跳过（不猜）
        pz = L.get('pz') or ''
        if d['pos'] >= len(pz):
            continue
        new = '仄' if d['tone'] in (3, 4) else '平'
        old = pz[d['pos']]
        if old != new:
            L['pz'] = pz[:d['pos']] + new + pz[d['pos'] + 1:]
            p, z = int(L.get('ping') or 0), int(L.get('ze') or 0)
            if new == '仄':
                L['ping'], L['ze'] = max(0, p - 1), z + 1
            else:
                L['ping'], L['ze'] = p + 1, max(0, z - 1)
        applied.append({'line': d['line'], 'pos': d['pos'], 'char': ch,
                        'reading': d['reading'], 'tone': d['tone'],
                        'before': old, 'after': new, 'changed': old != new,
                        'decision_id': d['decision_id']})
    return lines, applied


def list_pron_decisions(conn, pid):
    """某篇的读音决策**全史**（select 与 withdraw 都列，新在前）——验收「完整回溯」用。"""
    # ★ 2026-10-11（审查 M1 同类）：`pid` 进了 LIKE 模式就必须**先转义** `%`/`_`
    #   （否则 `pid` 里带 `_` 会把「某篇的裁定史」扩成「一批篇的裁定史」——
    #   这不是注入，是**语义被通配符悄悄放大**，与检索页 M1 同一个坑）；
    #   末尾的 `%` 才是**有意**的前缀匹配通配，必须在转义**之后**追加。
    subj_prefix = _like_escape(str(pid)) + '|line=%'
    try:
        _cur = conn.execute(
            "SELECT * FROM decisions WHERE kind='pronounce' AND subject LIKE ? ESCAPE '\\'"
            " ORDER BY id DESC", (subj_prefix,))
        return [_row(_cur, r) for r in _cur]
    except sqlite3.Error:
        return []


# ---------------------------------------------------------------- 功能 12：个人录入（来源核验三态）
# 状态机（功能 12）：`draft`（草稿）→ `material_sample`（材料样例）→ `source_matched`（已对上来源）。
# 约定（重要）：`data/corpus.db` 里的既有 58,852 篇是**既有语料**，其状态**恒为**
# `source_matched`（来源 = chinese-poetry / poetry-source）——那是**展示约定**，
# 不是本表的行；本表只收「用户新录入」的作品，默认 `draft`。**绝不改 corpus.db 的表结构。**
VERIFY_STATES = ('draft', 'material_sample', 'source_matched')
_VERIFY_LABELS = {'draft': '草稿', 'material_sample': '材料样例', 'source_matched': '已对上来源'}


def add_personal_work(conn, title, content, author='', cipai='', verification_state='draft',
                      source='', source_material_id=None, source_locator='',
                      actor='human', client_token=None):
    """录入一篇**个人作品**（新录入默认 `draft`；`source_matched` 必须给来源说明）。"""
    if not (title or '').strip() or not (content or '').strip():
        raise ValueError('title 与 content 为必填')
    st = str(verification_state or 'draft')
    if st not in VERIFY_STATES:
        raise ValueError('verification_state 必须是 %s 之一' % '／'.join(VERIFY_STATES))
    if st == 'source_matched' and not (source or '').strip():
        raise ValueError('「已对上来源」必须写明来源（source 不得为空）——不许空口自证')

    def fn(c):
        cur = c.execute(
            'INSERT INTO personal_works(created_at,author,title,cipai,content,'
            'verification_state,source,source_material_id,source_locator,checked_at,checked_by)'
            ' VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (_now(), author, title, cipai, content, st, source, source_material_id,
             source_locator, _now() if st != 'draft' else None, actor if st != 'draft' else None))
        return {'work_id': cur.lastrowid, 'verification_state': st,
                'label': _VERIFY_LABELS.get(st, st)}

    return run_idempotent(conn, client_token, 'works', fn)


def set_work_verification(conn, work_id, state, source='', source_material_id=None,
                          source_locator='', why='', actor='human', client_token=None):
    """流转一篇作品的**来源核验状态**（同时留一条决策事件，可回溯）。"""
    st = str(state or '')
    if st not in VERIFY_STATES:
        raise ValueError('state 必须是 %s 之一' % '／'.join(VERIFY_STATES))

    def fn(c):
        wid = int(work_id)
        _cw2 = c.execute('SELECT * FROM personal_works WHERE id=?', (wid,))
        w = _row(_cw2, _cw2.fetchone())
        if w is None:
            raise ValueError('作品 %s 不存在' % work_id)
        src = (source if source not in (None, '') else (w['source'] or '')) if st == 'source_matched' \
            else source
        if st == 'source_matched' and not (src or '').strip():
            raise ValueError('「已对上来源」必须写明来源（source 不得为空）')
        c.execute('UPDATE personal_works SET verification_state=?, source=?,'
                  ' source_material_id=?, source_locator=?, checked_at=?, checked_by=?'
                  ' WHERE id=?',
                  (st, src, source_material_id if source_material_id is not None
                   else w['source_material_id'],
                   source_locator, _now(), actor, wid))
        d = _insert_decision(c, 'verify', 'work:%d' % wid, 'set_state',
                             payload={'work_id': wid, 'from': w['verification_state'],
                                      'to': st, 'source': src},
                             basis='来源核验', why=why, actor=actor)
        return {'work_id': wid, 'from': w['verification_state'], 'to': st,
                'label': _VERIFY_LABELS.get(st, st), 'decision_id': d['decision_id']}

    return run_idempotent(conn, client_token, 'works/verify', fn)


def list_personal_works(conn, state=None):
    """个人作品列表（新在前）；`state` 可视需要过滤（三态之一）。

    ★ M10：默认**不含已撤回**（批量导入回滚撤下）的作品——它们只是被撤下，行仍在库里，
    但不再出现在列表与解析入口（避免"撤了还能用"）。
    """
    sql = 'SELECT * FROM personal_works WHERE withdrawn=0'
    args = []
    if state:
        if state not in VERIFY_STATES:
            raise ValueError('state 必须是 %s 之一' % '／'.join(VERIFY_STATES))
        sql += ' AND verification_state=?'
        args.append(state)
    sql += ' ORDER BY id DESC LIMIT 500'
    _cur = conn.execute(sql, args)
    return [_row(_cur, r) for r in _cur]


# --- 个人作品声律解析（与 build_corpus.py 同一引擎、同一口径）
# 背景（P2-1）：让「个人录入」的作品也能被解析 / 词谱对照 / 引用。
# 关键纪律：
#   · pid 用 `personal:<n>` 前缀（沿用本文件 L111 既有约定），与语料库 pid **物理隔离**——
#     个人作品**绝不写入** data/corpus.db（那是只读交付语料，58,852 篇）。
#   · 注音器 `Pronouncer` 模块级懒缓存（构造需读标定表，避免每次解析重读文件）；
#     但 `Engine` **每次新建**——它的 `_lines_memo` 是「单条缓存」，多线程共享同一实例
#     会把甲篇的切句结果串给乙篇（serve 是 ThreadingHTTPServer）。
#   · `dynasty` 置空：personal_works 表**没有朝代字段**，不猜。
#   · 返回体与 `/api/parse` 出口**同形**（19 个篇级键 + lines + raw），解析页 / 词谱对照 /
#     问答引用链共用这一份，谁拿到都是同一口径。
_PRON_CACHE = None


def _pronouncer():
    """注音器懒缓存（模块级单例）。"""
    global _PRON_CACHE
    if _PRON_CACHE is None:
        _PRON_CACHE = Pronouncer(default_overrides_path())
    return _PRON_CACHE


def _last_han(text):
    """句脚字 = 该句**最后一个汉字**（与 build_corpus.last_han 同口径；无汉字给空串）。"""
    m = _HAN_RE.findall(text or '')
    return m[-1] if m else ''


def analyze_work(conn, work_id):
    """对一篇**个人作品**做声律解析（与建库同一引擎、同一口径）。

    返回体与 `/api/parse` 出口同形（19 个篇级键 + lines + raw）：
      · `pid` = `personal:<n>`（前缀标识，供解析页深链 / 词谱对照 / 问答引用分流）；
      · `dynasty` 置空（个人录入无朝代字段，不猜）；
      · `longest_seq` 直接给**真数组**（空篇为 `[]`），省去调用方的字符串再解析；
      · `lines` 每行 `{idx,text,han_len,ping,ze,pz,tail}`，`han_len = len(pz)`（与建库同口径）；
      · 末尾对该篇（`personal:<n>`）套用「人工读音裁定」（与语料库同等待遇，无裁定原样返回）。
    作品不存在时抛 ValueError（由调用方转成友好错误）。
    """
    # ★ 2026-10-11 二修：本函数会拿到**外部传入**的连接（`/api/parse` 走只读连接；
    #   门禁也会自建连接），不能再假定 `row_factory=Row`——统一经 `_row` 归一。
    _cw = conn.execute('SELECT * FROM personal_works WHERE id=?', (int(work_id),))
    w = _row(_cw, _cw.fetchone())
    if w is None:
        raise ValueError('个人作品 %s 不存在' % work_id)
    # ★ M10：已撤回的作品**不再被解析**（但行保留 → 引用不悬空，且错误文案说清原因，
    #   而不是像"物理删除"那样只报「不存在」，让人以为从没导入过）。
    if int(w['withdrawn'] or 0):
        raise ValueError('个人作品 %s 已撤回（%s）；行仍保留，可重新导入恢复'
                         % (work_id, (w['withdrawn_why'] or '批量导入回滚') or '未注明原因'))
    pid = 'personal:%d' % int(w['id'])
    content = w['content'] or ''
    eng = Engine(_pronouncer())
    sents, pzs = eng.lines(content)
    h = eng.halves(content)
    lg = eng.longest(content)
    ratio = eng.ratio(content)
    ld = eng.long_density(content)
    scene = eng.scene_emotion(content)['转向']
    lines = [{'idx': k, 'text': s, 'han_len': len(pz),
              'ping': pz.count('平'), 'ze': pz.count('仄'), 'pz': pz,
              'tail': _last_han(s)} for k, (s, pz) in enumerate(zip(sents, pzs))]
    out = {
        'pid': pid, 'dynasty': '', 'author': w['author'] or '',
        'title': w['title'], 'cipai': w['cipai'] or '',
        'sent_n': len(sents), 'han_len': ratio['总字'],
        'ping': ratio['平'], 'ze': ratio['仄'], 'ze_ratio': ratio['仄声比例'],
        'f_ratio': h['前段比例'], 'b_ratio': h['后段比例'],
        'change': h['变化'], 'abs_change': h['绝对变幅'],
        'longest_seq': [int(x) for x in lg['最长句序']],
        'longest_len': lg['最长句字数'], 'threshold': ld['阈值'], 'scene': scene,
        'raw': content, 'lines': lines,
    }
    _ls2, _adj = apply_pron_to_lines(conn, pid, lines)
    if _adj:
        out['lines'] = _ls2
        out['pron_adjusted'] = _adj
    return out


# ---------------------------------------------------------------- 功能 13：批量导入（manifest + 批次对账）
def _row_sha(row):
    return content_sha(json.dumps(row, ensure_ascii=False, sort_keys=True))


def _manifest_sha(files):
    """文件集合的清单哈希：`name|sha|n` 排序拼接后取 sha（同内容必同哈希）。"""
    h = hashlib.sha256()
    for name, fsha, n in sorted(files):
        h.update(('%s|%s|%d\n' % (name, fsha, n)).encode('utf-8'))
    return h.hexdigest()[:16]


def import_rows(conn, tag, files, actor='import', note='', client_token=None):
    """批量导入（功能 13）：**manifest（文件+哈希+条数）→ 批次 → 幂等落行**。

    `files`：`[{'name': '文件名', 'rows': [ {作品字段}, … ]}, …]`——
    行字段用 `personal_works` 的口径（`title`/`content` 必填，其余可选）。

    幂等与对账口径：
      · **同内容重复导入**（manifest_sha 相同且批次仍 committed）→ 直接返回既有批次
        （`already=True`，零新增）；
      · **部分重叠**（同文件同行 key）→ 该行跳过（`skipped` 计数），不产生重复行；
      · 返回值记 `inserted / skipped / manifest_sha / batch_id`，供对账。
    """
    files = list(files or [])
    if not tag:
        raise ValueError('tag（批次名）为必填')
    if not files:
        raise ValueError('files 为空：没有可导入的内容')
    prepared = []
    meta = []
    for f in files:
        name = str(f.get('name') or 'inline.jsonl')
        rows = list(f.get('rows') or [])
        for i, r in enumerate(rows):
            if not isinstance(r, dict):
                raise ValueError('%s 第 %d 行不是 JSON 对象' % (name, i + 1))
            if not str(r.get('title') or '').strip() or not str(r.get('content') or '').strip():
                raise ValueError('%s 第 %d 行缺 title 或 content（导入行必须可成篇）'
                                 % (name, i + 1))
        fsha = content_sha('\n'.join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                                     for r in rows))
        # ★ 2026-10-11（审查·低）：**同文件内两行内容完全相同**曾被静默丢掉一行
        #   （改前 `row_key` 就是内容哈希——第二行撞 key 即被判「重复」跳过）。
        #   但「内容相同」不等于「同一条录入」：同一首词在素材里出现两次、
        #   或两处引文恰好一字不差，都是**合法的两条**。静默丢数据比重复更严重。
        #   处置：`row_key` = 内容哈希 + **该文件内第几次出现**（`#0`、`#1`…）。
        #   · 同内容的两行 → 两个不同的 key → **都导入**；
        #   · 同一份文件重导 → 出现次序不变 → key 不变 → **幂等照旧**，不会重复灌入。
        seen = {}
        keys = []
        for r in rows:
            rs = _row_sha(r)
            k = seen.get(rs, 0)
            seen[rs] = k + 1
            keys.append(rs if k == 0 else '%s#%d' % (rs, k))
        prepared.append((name, rows, keys))
        meta.append((name, fsha, len(rows)))
    msha = _manifest_sha(meta)

    def fn(c):
        prev = c.execute("SELECT * FROM import_batches WHERE manifest_sha=? AND status='committed'",
                         (msha,)).fetchone()
        if prev is not None:
            return {'batch_id': prev['id'], 'already': True, 'inserted': 0, 'skipped': 0,
                    'manifest_sha': msha, 'note': '同内容批次已导入过（manifest 哈希一致）'}
        cur = c.execute('INSERT INTO import_batches(created_at,tag,manifest_sha,files,n_rows,'
                        'status,note) VALUES(?,?,?,?,?,?,?)',
                        (_now(), tag, msha, len(meta), 0, 'committed', note))
        bid = cur.lastrowid
        inserted = skipped = 0
        for name, rows, keys in prepared:
            for r, rkey in zip(rows, keys):
                rsha = _row_sha(r)
                ex = c.execute('SELECT id FROM import_rows WHERE file=? AND row_key=?',
                               (name, rkey)).fetchone()
                if ex is not None:
                    skipped += 1
                    continue
                w = c.execute(
                    'INSERT INTO personal_works(created_at,author,title,cipai,content,'
                    'verification_state,source,source_material_id,source_locator)'
                    ' VALUES(?,?,?,?,?,?,?,?,?)',
                    (_now(), str(r.get('author') or ''), str(r.get('title') or '').strip(),
                     str(r.get('cipai') or ''), str(r.get('content') or ''),
                     'draft', str(r.get('source') or ''), r.get('source_material_id'),
                     str(r.get('source_locator') or ''))).lastrowid
                c.execute('INSERT INTO import_rows(batch_id,file,row_key,row_sha,payload,work_ref)'
                          ' VALUES(?,?,?,?,?,?)',
                          (bid, name, rkey, rsha, json.dumps(r, ensure_ascii=False), w))
                inserted += 1
        c.execute('UPDATE import_batches SET n_rows=? WHERE id=?', (inserted, bid))
        c.execute('UPDATE import_batches SET note=? WHERE id=?',
                  (note or ('导入 %d 行，跳过 %d 行' % (inserted, skipped)), bid))
        _insert_decision(c, 'import', 'batch:%d' % bid, 'commit',
                         payload={'batch_id': bid, 'tag': tag, 'manifest_sha': msha,
                                  'inserted': inserted, 'skipped': skipped},
                         basis='批量导入', why=note, actor=actor)
        return {'batch_id': bid, 'already': False, 'inserted': inserted, 'skipped': skipped,
                'manifest_sha': msha, 'n_files': len(meta)}

    return run_idempotent(conn, client_token, 'import', fn)


def list_import_batches(conn):
    """批次对账（功能 13）：承诺条数（n_rows）vs **现存行数**（rollback 会减少），逐批状态。"""
    out = []
    _cur = conn.execute('SELECT * FROM import_batches ORDER BY id DESC LIMIT 200')
    for r in _cur:
        d = _row(_cur, r)
        d['rows_now'] = conn.execute('SELECT COUNT(1) FROM import_rows WHERE batch_id=?',
                                     (d['id'],)).fetchone()[0]
        d['works_now'] = conn.execute(
            'SELECT COUNT(1) FROM personal_works WHERE id IN'
            ' (SELECT work_ref FROM import_rows WHERE batch_id=? AND work_ref IS NOT NULL)',
            (d['id'],)).fetchone()[0]
        out.append(d)
    return out


def rollback_import_batch(conn, batch_id, why='', actor='human', client_token=None):
    """**回滚一个导入批次**：撤下该批的行与作品（行保留 import_batches 状态与决策事件留痕）。

    ⚠ 口径说明：回滚删的是「**本批导入产生**的行」——`import_rows` 明细与对应的
    `personal_works`（经 `work_ref` 关联）都撤下；批次记录本身**保留**（status='rolled_back'），
    决策事件留痕。原始文件在用户手上，随时可重新导入（幂等保证不会重复）。
    """

    def fn(c):
        bid = int(batch_id)
        _cb = c.execute('SELECT * FROM import_batches WHERE id=?', (bid,))
        b = _row(_cb, _cb.fetchone())
        if b is None:
            raise ValueError('批次 %s 不存在' % batch_id)
        if b['status'] != 'committed':
            return {'batch_id': bid, 'status': b['status'], 'removed': 0, 'note': '此前已回滚'}
        # ★ 2026-10-11（审查 M10）：改前 `DELETE FROM personal_works`——**物理删除**，
        #   与模块 docstring「删除=撤回标记（行保留）」的纪律相悖，且会让指向
        #   `personal:<n>` 的读音裁定 / 研究事实 / 问答引用变成**悬空引用**
        #   （回滚后再去解析/对照这些 id 会失败，且无从追溯"它曾经存在过")。
        #   改后：作品**标记撤回**（行保留），引用不会悬空；`import_rows` 明细是本批对账用，
        #   仍随批次撤下（批次记录与决策事件都保留，随时可查"撤了什么"）。
        wids = [r[0] for r in c.execute(
            'SELECT work_ref FROM import_rows WHERE batch_id=? AND work_ref IS NOT NULL',
            (bid,))]
        _ts = _now()
        for wid in wids:
            c.execute('UPDATE personal_works SET withdrawn=1, withdrawn_at=?, withdrawn_why=?'
                      ' WHERE id=? AND withdrawn=0',
                      (_ts, (why or '批量导入回滚')[:200], wid))
        removed_rows = c.execute('DELETE FROM import_rows WHERE batch_id=?', (bid,)).rowcount
        c.execute("UPDATE import_batches SET status='rolled_back', note=COALESCE(note,'') || ?"
                  " WHERE id=?", ('\n[已回滚] %s' % (why or ''), bid))
        _insert_decision(c, 'import', 'batch:%d' % bid, 'rollback',
                         payload={'batch_id': bid, 'removed_rows': removed_rows,
                                  'removed_works': len(wids)},
                         basis='用户操作', why=why, actor=actor)
        return {'batch_id': bid, 'status': 'rolled_back', 'removed_rows': removed_rows,
                'removed_works': len(wids)}

    return run_idempotent(conn, client_token, 'import/rollback', fn)


# ---------------------------------------------------------------- 论证稿（2026-10-13 新增）
# 吸收 cilyutanwei 的 `argument_revisions`：论证稿是**实体**（可编辑、留修订链、可导出），
# 不是「随答案返回的一段文本」。与材料/事实/版本链同一纪律：**追加，不覆盖**。
ARG_ORIGINS = ('answer_organized', 'user_edited')
_ARG_MAX_CLAIMS = 12
_ARG_MAX_LIST = 8


def _arg_norm(data):
    """规整论证稿数据：**只保留已知字段**（防任意注入），并做长度与条数上限。"""
    if not isinstance(data, dict):
        raise ValueError('论证稿必须是 JSON 对象')
    thesis = str(data.get('thesis') or '').strip()
    if not thesis:
        raise ValueError('论证稿缺少 thesis（总论点）')
    claims_in = data.get('claims')
    if not isinstance(claims_in, list) or not claims_in:
        raise ValueError('论证稿缺少 claims（分论点，至少一条）')
    claims = []
    for i, c in enumerate(claims_in[:_ARG_MAX_CLAIMS]):
        if not isinstance(c, dict):
            raise ValueError('claims[%d] 不是对象' % i)
        claim = str(c.get('claim') or '').strip()
        if not claim:
            raise ValueError('claims[%d] 缺少 claim' % i)
        claims.append({
            'claim': claim[:1200],
            'bridge': str(c.get('bridge') or '').strip()[:1200],
            'assessment': (str(c.get('assessment') or 'insufficient').strip().lower()
                           if str(c.get('assessment') or '').strip().lower() in
                           ('supported', 'mixed', 'insufficient', 'unresolved')
                           else 'insufficient'),
            'alternatives': [str(x).strip()[:400] for x in (c.get('alternatives') or [])
                             if str(x).strip()][:_ARG_MAX_LIST],
            'gaps': [str(x).strip()[:400] for x in (c.get('gaps') or [])
                     if str(x).strip()][:_ARG_MAX_LIST],
            'evidence': [str(x).strip()[:32] for x in (c.get('evidence') or [])
                         if str(x).strip()][:_ARG_MAX_LIST],
        })
    limits = [str(x).strip()[:400] for x in (data.get('limitations') or [])
              if str(x).strip()][:_ARG_MAX_LIST]
    return {'thesis': thesis[:2000], 'claims': claims, 'limitations': limits,
            'note': str(data.get('note') or '').strip()[:1000]}


def _insert_arg_revision(c, draft_id, data, note, actor, parent_id):
    """在**已有事务**里追加一条论证修订，返回 revision 号。"""
    row = c.execute('SELECT COALESCE(MAX(revision), 0) AS r FROM argument_revisions '
                    'WHERE draft_id=?', (draft_id,)).fetchone()
    rev = (row['r'] if row is not None else 0) + 1
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    c.execute('INSERT INTO argument_revisions'
              '(draft_id, revision, parent_id, created_at, actor, data, note, data_sha) '
              'VALUES(?,?,?,?,?,?,?,?)',
              (draft_id, rev, parent_id, _now(), actor, payload, note or '',
               content_sha(payload)))
    return rev


def add_argument(conn, data, snapshot_id=None, question='', title='', actor='human',
                 client_token=None):
    """**新建**论证稿（通常由「把回答整理成论证」触发），返回 `{draft_id, revision}`。"""
    norm = _arg_norm(data)

    def fn(c):
        cur = c.execute('INSERT INTO argument_drafts'
                        '(created_at, origin, snapshot_id, question, title) VALUES(?,?,?,?,?)',
                        (_now(), 'answer_organized', snapshot_id, (question or '')[:500],
                         (title or '')[:200]))
        did = cur.lastrowid
        rev = _insert_arg_revision(c, did, norm, norm.get('note', ''), actor, None)
        c.execute('INSERT INTO decisions(ts, actor, kind, subject, action, payload, basis, why) '
                  'VALUES(?,?,?,?,?,?,?,?)',
                  (_now(), actor, 'argument', str(did), 'create',
                   json.dumps({'draft_id': did, 'revision': rev,
                               'snapshot_id': snapshot_id}, ensure_ascii=False),
                   '人工整理', '从回答整理为论证稿'))
        return {'draft_id': did, 'revision': rev}

    return run_idempotent(conn, client_token, 'argument/create', fn)


def revise_argument(conn, draft_id, data, expected_revision, note='', actor='human',
                    client_token=None):
    """**追加**一条修订（乐观锁：`expected_revision` 不符即 409 语义的 ValueError）。"""
    norm = _arg_norm(data)

    def fn(c):
        row = c.execute('SELECT id, withdrawn FROM argument_drafts WHERE id=?',
                        (draft_id,)).fetchone()
        if row is None:
            raise KeyError('论证稿不存在：%s' % draft_id)
        if row['withdrawn']:
            raise ValueError('论证稿已撤回，不能修订')
        cur = c.execute('SELECT COALESCE(MAX(revision), 0) AS r FROM argument_revisions '
                        'WHERE draft_id=?', (draft_id,)).fetchone()
        latest = cur['r'] if cur is not None else 0
        if int(expected_revision) != latest:
            raise ValueError('修订号不符（当前 %d，请求基于 %s）——请刷新后重试'
                             % (latest, expected_revision))
        pid = c.execute('SELECT id FROM argument_revisions WHERE draft_id=? AND revision=?',
                        (draft_id, latest)).fetchone()
        parent = pid['id'] if pid is not None else None
        rev = _insert_arg_revision(c, draft_id, norm, note or norm.get('note', ''), actor, parent)
        c.execute('INSERT INTO decisions(ts, actor, kind, subject, action, payload, basis, why) '
                  'VALUES(?,?,?,?,?,?,?,?)',
                  (_now(), actor, 'argument', str(draft_id), 'revise',
                   json.dumps({'draft_id': draft_id, 'revision': rev}, ensure_ascii=False),
                   '人工编辑', note or '编辑论证稿'))
        return {'draft_id': draft_id, 'revision': rev}

    return run_idempotent(conn, client_token, 'argument/revise', fn)


def get_argument(conn, draft_id, revision=None):
    """取论证稿（指定修订或**最新**修订）。返回 dict 或 None（不存在/已撤回）。"""
    d = conn.execute('SELECT * FROM argument_drafts WHERE id=?', (draft_id,)).fetchone()
    if d is None:
        return None
    dr = dict(d)
    if dr.get('withdrawn'):
        return None
    if revision is None:
        r = conn.execute('SELECT * FROM argument_revisions WHERE draft_id=? '
                         'ORDER BY revision DESC LIMIT 1', (draft_id,)).fetchone()
    else:
        r = conn.execute('SELECT * FROM argument_revisions WHERE draft_id=? AND revision=?',
                         (draft_id, revision)).fetchone()
    if r is None:
        return None
    rv = dict(r)
    try:
        rv['data'] = json.loads(rv.get('data') or '{}')
    except (ValueError, TypeError):
        rv['data'] = {}
    return {'draft': {'id': dr['id'], 'created_at': dr['created_at'], 'origin': dr['origin'],
                      'snapshot_id': dr['snapshot_id'], 'question': dr['question'],
                      'title': dr['title'], 'withdrawn': bool(dr['withdrawn'])},
            'revision': {'revision': rv['revision'], 'parent_id': rv['parent_id'],
                         'created_at': rv['created_at'], 'actor': rv['actor'],
                         'note': rv['note'], 'data': rv['data'], 'data_sha': rv['data_sha']}}


def list_arguments(conn, include_withdrawn=False):
    """列论证稿（每篇附最新修订号）。"""
    sql = ('SELECT d.id, d.created_at, d.origin, d.snapshot_id, d.question, d.title, '
           'd.withdrawn, (SELECT MAX(revision) FROM argument_revisions r WHERE r.draft_id=d.id) '
           'AS revision FROM argument_drafts d')
    if not include_withdrawn:
        sql += ' WHERE d.withdrawn=0'
    sql += ' ORDER BY d.id DESC LIMIT 500'
    out = []
    for r in conn.execute(sql):
        d = dict(r)
        d['withdrawn'] = bool(d.get('withdrawn'))
        out.append(d)
    return out


def withdraw_argument(conn, draft_id, why='', actor='human', client_token=None):
    """撤回论证稿（**行保留**，与材料/事实/作品同一纪律）。"""
    def fn(c):
        row = c.execute('SELECT id FROM argument_drafts WHERE id=?', (draft_id,)).fetchone()
        if row is None:
            raise KeyError('论证稿不存在：%s' % draft_id)
        c.execute('UPDATE argument_drafts SET withdrawn=1, withdrawn_at=?, withdrawn_why=? '
                  'WHERE id=?', (_now(), why or '', draft_id))
        c.execute('INSERT INTO decisions(ts, actor, kind, subject, action, payload, basis, why) '
                  'VALUES(?,?,?,?,?,?,?,?)',
                  (_now(), actor, 'argument', str(draft_id), 'withdraw',
                   json.dumps({'draft_id': draft_id}, ensure_ascii=False), '人工撤回', why or ''))
        return {'draft_id': draft_id, 'withdrawn': True}

    return run_idempotent(conn, client_token, 'argument/withdraw', fn)


_ASSESS_CN = {'supported': '支持', 'mixed': '部分支持',
              'insufficient': '证据不足', 'unresolved': '未决'}


def render_argument_md(data, title='', meta=None):
    """把论证稿渲染成 **Markdown**（导出用；与网页展示同一份内容）。"""
    d = _arg_norm(data)
    lines = ['# %s' % (title or '论证稿'), '']
    if meta:
        for k, v in meta.items():
            lines.append('- %s：%s' % (k, v))
        lines.append('')
    lines.append('**主张**：%s' % d['thesis'])
    lines.append('')
    for i, c in enumerate(d['claims'], 1):
        lines.append('## 分论点 %d：%s' % (i, c['claim']))
        lines.append('')
        lines.append('- **桥梁**：%s' % (c['bridge'] or '（未填写）'))
        lines.append('- **评估**：%s（%s）' % (c['assessment'], _ASSESS_CN.get(c['assessment'], '')))
        if c['evidence']:
            lines.append('- **证据**：%s' % '、'.join('[%s]' % e for e in c['evidence']))
        if c['alternatives']:
            lines.append('- **替代解释**：%s' % '；'.join(c['alternatives']))
        if c['gaps']:
            lines.append('- **缺证**：%s' % '；'.join(c['gaps']))
        lines.append('')
    if d['limitations']:
        lines.append('## 局限')
        lines.append('')
        for x in d['limitations']:
            lines.append('- %s' % x)
        lines.append('')
    if d.get('note'):
        lines.append('> 备注：%s' % d['note'])
    return '\n'.join(lines)


def _xml_esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def render_argument_docx(data, title='', meta=None):
    """生成 **最小 OOXML** 的 `.docx` 字节（**纯标准库 zipfile**，不引第三方库）。

    结构：`[Content_Types].xml` + `_rels/.rels` + `word/document.xml`
    + `word/_rels/document.xml.rels` + `docProps/core.xml`（5 个 part）。
    只做「标题 / 小标题 / 段落 / 项目符号」四类，够用且**不丢中文与码点**。
    """
    import zipfile
    import io as _io
    d = _arg_norm(data)
    paras = []
    paras.append(('Title', title or '论证稿'))
    if meta:
        for k, v in meta.items():
            paras.append(('Meta', '%s：%s' % (k, v)))
    paras.append(('H1', '主张'))
    paras.append(('Body', d['thesis']))
    for i, c in enumerate(d['claims'], 1):
        paras.append(('H1', '分论点 %d：%s' % (i, c['claim'])))
        paras.append(('Body', '桥梁：%s' % (c['bridge'] or '（未填写）')))
        paras.append(('Body', '评估：%s（%s）' % (c['assessment'],
                                                 _ASSESS_CN.get(c['assessment'], ''))))
        if c['evidence']:
            paras.append(('Body', '证据：%s' % '、'.join('[%s]' % e for e in c['evidence'])))
        if c['alternatives']:
            paras.append(('Body', '替代解释：%s' % '；'.join(c['alternatives'])))
        if c['gaps']:
            paras.append(('Body', '缺证：%s' % '；'.join(c['gaps'])))
    if d['limitations']:
        paras.append(('H1', '局限'))
        for x in d['limitations']:
            paras.append(('Bullet', x))
    if d.get('note'):
        paras.append(('Body', '备注：%s' % d['note']))

    def _p(style, text):
        if style == 'Title':
            rpr = '<w:rPr><w:rFonts w:eastAsia="楷体"/><w:b/><w:sz w:val="36"/></w:rPr>'
            ppr = '<w:pPr><w:jc w:val="center"/></w:pPr>'
        elif style == 'H1':
            rpr = '<w:rPr><w:rFonts w:eastAsia="楷体"/><w:b/><w:sz w:val="28"/></w:rPr>'
            ppr = ''
        elif style == 'Meta':
            rpr = '<w:rPr><w:sz w:val="20"/><w:color w:val="666666"/></w:rPr>'
            ppr = ''
        elif style == 'Bullet':
            rpr = '<w:rPr><w:sz w:val="24"/></w:rPr>'
            ppr = '<w:pPr><w:ind w:left="420"/></w:pPr>'
        else:
            rpr = '<w:rPr><w:sz w:val="24"/></w:rPr>'
            ppr = ''
        return ('<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
                % (ppr, rpr, _xml_esc(text)))

    body = ''.join(_p(s, t) for s, t in paras)
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body>%s<w:sectPr/></w:body></w:document>' % body)
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:title>%s</dc:title><dc:creator>词律探微</dc:creator>'
            '</cp:coreProperties>' % _xml_esc(title or '论证稿'))
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels)
        z.writestr('word/document.xml', document)
        z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr('docProps/core.xml', core)
    return buf.getvalue()


# ---------------------------------------------------------------- 只读连接（展示层专用）
_RO_TLS = threading.local()


def readonly_conn(path=None):
    """线程本地**只读**连接；**库不存在返回 None**（展示层绝不为读而创建文件）。

    供解析页 / 证据块等高频展示路径使用：连接缓存在线程本地，避免每次重开；
    库「从无到有」时自动生效（None 结果不缓存）。SQLite WAL 下，
    缓存的连接每个新查询都能看到最新提交（不会看不到刚写入的裁定）。
    """
    p = path or DEFAULT_PATH
    c = getattr(_RO_TLS, 'conn', None)
    if c is not None and getattr(_RO_TLS, 'path', None) == p:
        return c
    if not os.path.exists(p):
        return None
    try:
        conn = sqlite3.connect(p, timeout=5, isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA busy_timeout=5000')
        _RO_TLS.conn = conn
        _RO_TLS.path = p
        return conn
    except sqlite3.Error:
        return None


def close_readonly():
    """★ 2026-10-11（审查·低）：**显式关闭**本线程的只读连接。

    `readonly_conn` 把连接缓存在 `threading.local` 里长期复用（省去每次重开），
    但 `web/serve.py` 跑的是 `ThreadingHTTPServer`——**每来一个请求新起一条线程**，
    线程结束前那条连接一直挂着，FD 只靠 GC 兜底回收，长跑服务里会攒下一批句柄。
    这里给出显式收口：请求处理完由 `serve.py` 在 `finally` 里调一次，
    语义仍是「读路径绝不创建文件」，只是不再等 GC。
    """
    c = getattr(_RO_TLS, 'conn', None)
    _RO_TLS.conn = None
    _RO_TLS.path = None
    if c is not None:
        try:
            c.close()
        except sqlite3.Error:                                  # noqa: BLE001
            pass


# ---------------------------------------------------------------- 概况（诊断用）
def summary(conn):
    """各表行数一览（前端「研究库概况」与服务端诊断用）。"""
    out = {}
    for t in ('materials', 'material_revisions', 'facts', 'decisions',
              'text_versions', 'meta_revisions', 'personal_works',
              'import_batches', 'import_rows', 'idempotency'):
        try:
            out[t] = conn.execute('SELECT COUNT(1) FROM %s' % t).fetchone()[0]
        except sqlite3.Error:
            out[t] = None
    return out
