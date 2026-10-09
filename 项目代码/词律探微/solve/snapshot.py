# -*- coding: utf-8 -*-
"""snapshot.py —— **冻结式问答快照**（功能 1）：每轮问答落地一份不可变快照。

快照内容（一条不落）：问句原文、理解结果（人类可读 + 结构化）、实际检索条件、
**口径版本指纹**（语料/标定表/答案基线）、命中集合（完整 pid + 指纹）、答案正文、
证据块、护栏结论、集合身份校验、理解状态。

三条纪律（功能 1 验收的原话）：
  1. **冻结**：回查直接读 JSON 原文——**绝不用现在的引擎重算历史**；
  2. **陈旧标注**：语料或口径变化后，`load()` 对照当前指纹给出 `stale=true` 与差在哪儿，
     但**不静默改写旧答案**（旧答案原样返回，只加标注）；
  3. 落盘在 `data/snapshots/`（**本地运行数据**，含用户问句，不入开源仓）。

口径指纹三项（与快照逐项比对）：
  · `corpus`    —— 语料内容指纹（篇数|句数|汉字总数|最大 pid，与 `vector_index` 同式同值）；
  · `overrides` —— 读音标定表 `solve/data/pron_overrides.json` 的内容 sha16；
  · `golden`    —— 双集答案基线 `solve/data/golden_sha.json` 的内容 sha16。
"""
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 快照目录可用 `LVC_SNAPSHOT_DIR` 覆盖（门禁测试指向临时目录，避免污染真实档案）。
_DIR = os.environ.get('LVC_SNAPSHOT_DIR') or os.path.join(_ROOT, 'data', 'snapshots')
_LOCK = threading.Lock()
_ID_RE = re.compile(r'^snap-[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$')     # 严格 id 形态（防路径穿越）


def _sha16(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()[:16]


def _read_sha16(path):
    try:
        with open(path, 'rb') as f:
            return _sha16(f.read())
    except OSError:
        return ''


def fingerprint(conn=None):
    """当前口径指纹（三项；取不到即为空串——**空串不与任何快照相等**，不会误判「未陈旧」）。"""
    fp = {}
    try:
        if conn is not None:
            con, own = conn, False
        else:
            con = sqlite3.connect(os.path.join(_ROOT, 'data', 'corpus.db'))
            own = True
        try:
            n_p = con.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
            n_l = con.execute('SELECT COUNT(*) FROM lines').fetchone()[0]
            s_h = con.execute('SELECT COALESCE(SUM(han_len),0) FROM poems').fetchone()[0]
            mx = con.execute("SELECT COALESCE(MAX(pid),'') FROM poems").fetchone()[0]
            fp['corpus'] = _sha16('%d|%d|%s|%s' % (n_p, n_l, s_h, mx))
        finally:
            if own:
                con.close()
    except Exception:                                              # noqa: BLE001
        fp['corpus'] = ''
    fp['overrides'] = _read_sha16(os.path.join(_ROOT, 'solve', 'data', 'pron_overrides.json'))
    fp['golden'] = _read_sha16(os.path.join(_ROOT, 'solve', 'data', 'golden_sha.json'))
    return fp


def _jsonable(v):
    """把 QuerySpec 字段值转成可 JSON 化的形态（过滤不可序列化的内部对象）。"""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, set):
        return sorted(str(x) for x in v)
    return None


def _spec_dict(spec):
    """QuerySpec 对象 → 结构化 dict（只保留可 JSON 化的字段）。"""
    if spec is None:
        return None
    if isinstance(spec, dict):
        return _jsonable(spec)
    try:
        return {k: _jsonable(v) for k, v in vars(spec).items() if not k.startswith('_')}
    except TypeError:
        return None


def capture(out, question, result_pids, spec=None, sid=None, turn_no=None, conn=None):
    """把一轮问答的**整体**冻进一份快照，返回 `snapshot_id`。

    只做「抄录 + 落盘」——不重新理解、不重新检索、不重新计算（冻结的根据就在这里）。
    调用方（serve.py）用 try/except 包住：快照失败**绝不拖垮问答**。
    """
    pids = list(result_pids or [])
    snap = {
        'snapshot_id': None,                       # 落盘前回填
        'ts': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'question': question or '',
        'sid': sid or None,
        'turn': turn_no,
        'spec': out.get('spec'),                   # 人类可读（serve 已整理为 str）
        'spec_struct': _spec_dict(spec),           # 结构化（逐字段抄录）
        'result': {'pids': pids, 'n': len(pids),
                   'total': out.get('total'),
                   'pids_sha': _sha16('|'.join(pids)) if pids else None},
        'answer': out.get('answer'),
        'refused': bool(out.get('refused')),
        'reason': _jsonable(out.get('reason')),
        'blocks': _jsonable(out.get('blocks')),
        'verify': _jsonable(out.get('verify')),
        'set_check': _jsonable(out.get('set_check')),
        'understanding_status': out.get('understanding_status'),
        'fingerprint': fingerprint(conn),
    }
    sid_id = 'snap-%s-%s' % (time.strftime('%Y%m%d-%H%M%S'), uuid.uuid4().hex[:6])
    snap['snapshot_id'] = sid_id
    os.makedirs(_DIR, exist_ok=True)
    with _LOCK:
        with open(os.path.join(_DIR, sid_id + '.json'), 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False)
        with open(os.path.join(_DIR, 'index.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps({'snapshot_id': sid_id, 'ts': snap['ts'],
                                'question': snap['question'], 'total': snap['result']['total'],
                                'sid': sid, 'turn': turn_no}, ensure_ascii=False) + '\n')
    return sid_id


def list_recent(n=20):
    """最近 n 条快照摘要（新在前）；索引缺失时返回空表（如实，不臆造）。"""
    p = os.path.join(_DIR, 'index.jsonl')
    if not os.path.isfile(p):
        return []
    try:
        with open(p, encoding='utf-8') as f:
            lines = [x for x in f.read().splitlines() if x.strip()]
    except OSError:
        return []
    out = []
    for ln in lines[-max(1, int(n)):]:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    out.reverse()
    return out


def load(snapshot_id):
    """回查一份快照（**原文返回，不重算**）+ 陈旧标注。

    返回 `None`（不存在）或快照 dict，附加：
      · `stale` / `stale_fields` / `stale_note`——依赖是否已陈旧、差在哪儿；
      · `current_fingerprint`——当前口径指纹（对照用）。
    旧答案**原样保留**：本函数绝不用现在的引擎重跑历史。
    """
    sid = str(snapshot_id or '')
    if not _ID_RE.match(sid):
        return None
    p = os.path.join(_DIR, sid + '.json')
    if not os.path.isfile(p):
        return None
    with open(p, encoding='utf-8') as f:
        snap = json.load(f)
    cur = fingerprint()
    old = snap.get('fingerprint') or {}
    diffs = [k for k in ('corpus', 'overrides', 'golden')
             if cur.get(k) and old.get(k) != cur.get(k)]
    snap['stale'] = bool(diffs)
    snap['stale_fields'] = diffs
    snap['current_fingerprint'] = cur
    if diffs:
        names = {'corpus': '语料', 'overrides': '读音标定表', 'golden': '答案基线'}
        snap['stale_note'] = ('依赖已陈旧：%s 在本快照之后发生了变化；'
                              '**旧答案原样保留、未经重算**（如需新口径，请重新提问）。'
                              % '、'.join(names.get(k, k) for k in diffs))
    return snap
