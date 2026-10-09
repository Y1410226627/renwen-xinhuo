# -*- coding: utf-8 -*-
"""build_corpus.py —— M1 语料入库（S0）

**吸收自第一份外部交付（`项目代码\\solve`）的 M1 设计，并按我方口径加强**：
语料从「每次跑题都现场加载 5.9 万首 JSON」升级为「一次入库、随时点查」，
这是从「答题器」走向「研究助手」的第一块地基。

与那份实现的差异（都是我需要的）：
  - 篇级 `poems`：把**引擎全套指标**落库（句数/平/仄/比例/前后段/变化/最长句/阈值/声情转向），
    数字与 `solve` 引擎**同源**（同一份代码算出来的），演示层点一首即可秒出。
  - 句级 `lines`：原文（含句末标点）+ 汉字数 + 平/仄 + **平仄串 `pz`**（声律模式检索的底座）+ 句脚字。
  - **二路全文索引**（M7）：
      · `lines_fts`：FTS5 默认分词，供**整句/短语级**检索；
      · `lines_bigram`：内容按**连续二字组**预切分后用 FTS5 建索引，
        使中文也能做「子串级」检索并复用 FTS5 自带的 BM25 排序
        （不做手写倒排表，省掉「每次取 df/dl 都回查数据库」的 N+1 开销）。
  - `authors` / `cipai` / `cipai_dyn`：查询理解用的名字表；`meta` 存计数与指纹。
  - `--verify N`：随机抽 N 首**重新用引擎算一遍**并逐字段比对（入库不能只信自己）。
  - 全程确定性：同一语料两次建库 → 行数、全部字段、内容指纹一致。

用法：
  python build_corpus.py --corpus <语料根> --db data/corpus.db [--verify 100] [--verify-hash]
"""
import argparse
import hashlib
import json
import os
import random
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'solve'))

from corpus import load_corpus                             # noqa: E402
from corpus import HAN_RE                                  # noqa: E402
from pronounce import Pronouncer, default_overrides_path   # noqa: E402
from prosody import Engine                                 # noqa: E402


def last_han(text):
    """句脚字 = 该句**最后一个汉字**（与引擎同一份汉字区间，单一来源）。

    为什么要跳过非汉字：语料里存在缺字占位符（■/○/□）与英文右括号收尾的句子，
    若直接取「去标点后的末字符」，会出现句脚字 = ■ / ) 这种没法做韵脚观察的值。
    """
    m = HAN_RE.findall(text or '')
    return m[-1] if m else ''

POEM_FIELDS = ('han_len', 'sent_n', 'ping', 'ze', 'ze_ratio', 'cut', 'f_ratio', 'b_ratio',
               'change', 'abs_change', 'longest_seq', 'longest_len', 'threshold', 'scene')

DDL = """
DROP TABLE IF EXISTS poems;
DROP TABLE IF EXISTS lines;
DROP TABLE IF EXISTS lines_fts;
DROP TABLE IF EXISTS lines_bigram;
DROP TABLE IF EXISTS authors;
DROP TABLE IF EXISTS cipai;
DROP TABLE IF EXISTS meta;
CREATE TABLE poems (
    pid        TEXT PRIMARY KEY,     -- 定位串：文件名#数组下标
    source     TEXT,                 -- poetry-source / chinese-poetry
    dynasty    TEXT,
    author     TEXT,
    cipai      TEXT,
    title      TEXT,
    raw        TEXT,
    han_len    INTEGER,              -- 全篇汉字数
    sent_n     INTEGER,              -- 句数
    ping       INTEGER,              -- 平声字数
    ze         INTEGER,              -- 仄声字数
    ze_ratio   REAL,                 -- 仄声比例（官方口径：一位小数，银行家舍入）
    cut        INTEGER,              -- 前段句数 = 前 floor(n/2) 句
    f_ratio    REAL,                 -- 前段仄声比例
    b_ratio    REAL,                 -- 后段仄声比例
    change     REAL,                 -- 变化 = 后段 - 前段（原始值相减后一位小数）
    abs_change REAL,
    longest_seq TEXT,                -- 最长句序（JSON 数组，可能多句并列）
    longest_len INTEGER,
    threshold  INTEGER,              -- 长句阈值 = ceil(汉字数 / 句数)
    scene      TEXT                  -- 声情转向（后段上升 / 后段下降 / 前后持平）
);
CREATE INDEX idx_poems_author ON poems(author);
-- 复合索引（2026-10-01）：检索的默认条件链是「朝代 + 〔词牌/词人/仄声比例〕」，
-- 单列索引只能吃第一个条件，其余 2.6 万行仍要逐行过滤（实测每次 25 ms × 5 遍 ≈ 130 ms/请求）。
-- 复合索引让常用组合直接落到索引区间上。
CREATE INDEX IF NOT EXISTS idx_poems_dyn_cipai ON poems(dynasty, cipai);
CREATE INDEX IF NOT EXISTS idx_poems_dyn_author ON poems(dynasty, author);
CREATE INDEX IF NOT EXISTS idx_poems_dyn_ze ON poems(dynasty, ze_ratio);
CREATE INDEX idx_poems_cipai  ON poems(cipai);
CREATE INDEX idx_poems_dyn    ON poems(dynasty);
CREATE INDEX idx_poems_ze     ON poems(ze_ratio);
CREATE INDEX idx_poems_len    ON poems(han_len);
CREATE INDEX idx_poems_scene  ON poems(scene);
CREATE TABLE lines (
    pid     TEXT,
    idx     INTEGER,                 -- 句序（从 0 起）
    text    TEXT,                    -- **原样**（含句末标点）
    han_len INTEGER,
    ping    INTEGER,
    ze      INTEGER,
    pz      TEXT,                    -- 平仄串（只含 平/仄）
    tail    TEXT,                    -- 句脚字（该句**最后一个汉字**，韵脚观察用）
    PRIMARY KEY (pid, idx)
);
CREATE TABLE authors (author TEXT PRIMARY KEY, n INTEGER);
CREATE TABLE cipai   (cipai  TEXT PRIMARY KEY, n INTEGER);
CREATE TABLE meta    (k TEXT PRIMARY KEY, v TEXT);
"""


def bigrams(text):
    """连续二字组（含跨标点的字序对？不含：只取汉字序列的相邻二字）。"""
    han = [c for c in text if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf']
    if len(han) < 2:
        return han
    return [han[i] + han[i + 1] for i in range(len(han) - 1)]


def build(poems, eng, db, with_fts=True):
    os.makedirs(os.path.dirname(os.path.abspath(db)) or '.', exist_ok=True)
    con = sqlite3.connect(db)
    con.executescript(DDL)
    nline = 0
    au, cp = {}, {}
    for p in poems:
        sents, pzs = eng.lines(p.raw)        # 切句与逐句平仄只算一次（下文全部复用）
        h = eng.halves(p.raw)
        lg = eng.longest(p.raw)
        ratio = eng.ratio(p.raw)
        scene = eng.scene_emotion(p.raw)['转向']
        con.execute('INSERT INTO poems VALUES (%s)' % ','.join(['?'] * 21), (
            p.loc, getattr(p, 'source', ''), p.dynasty, p.author, p.cipai, p.title, p.raw,
            len(p.han), len(sents), ratio['平'], ratio['仄'], ratio['仄声比例'],
            h['cut'], h['前段比例'], h['后段比例'], h['变化'], h['绝对变幅'],
            json.dumps(lg['最长句序'], ensure_ascii=False), lg['最长句字数'],
            eng.long_density(p.raw)['阈值'], scene,
        ))
        au[p.author] = au.get(p.author, 0) + 1
        cp[p.cipai] = cp.get(p.cipai, 0) + 1
        for k, (s, pz) in enumerate(zip(sents, pzs)):
            con.execute('INSERT INTO lines VALUES (?,?,?,?,?,?,?,?)', (
                p.loc, k, s, len(pz), pz.count('平'), pz.count('仄'), pz,
                last_han(s)))
        nline += len(sents)
    con.executemany('INSERT INTO authors VALUES (?,?)', list(au.items()))
    con.executemany('INSERT INTO cipai VALUES (?,?)', list(cp.items()))
    con.commit()
    if with_fts:
        con.executescript(
            "CREATE VIRTUAL TABLE lines_fts USING fts5(text, content='lines', content_rowid='rowid');"
            "INSERT INTO lines_fts(rowid, text) SELECT rowid, text FROM lines;")
        # 二字组索引：查询侧同样切成二字组后 MATCH，等价于子串检索，但走 FTS5 的 BM25。
        con.execute("CREATE VIRTUAL TABLE lines_bigram USING fts5(big, content='')")
        rows = con.execute('SELECT rowid, text FROM lines').fetchall()
        con.executemany('INSERT INTO lines_bigram(rowid, big) VALUES (?,?)',
                        [(rid, ' '.join(bigrams(t))) for rid, t in rows if bigrams(t)])
        con.commit()
    n = con.execute('SELECT COUNT(*) FROM poems').fetchone()[0]
    con.execute("INSERT INTO meta VALUES ('poems',?)", (str(n),))
    con.execute("INSERT INTO meta VALUES ('lines',?)", (str(nline),))
    con.execute("INSERT INTO meta VALUES ('authors',?)", (str(len(au)),))
    con.execute("INSERT INTO meta VALUES ('cipai',?)", (str(len(cp)),))
    con.execute("INSERT INTO meta VALUES ('overrides_sha',?)",
                (hashlib.sha256(open(eng.p.overrides_path, 'rb').read()).hexdigest().upper()
                 if getattr(eng.p, 'overrides_path', None) else '',))
    con.commit()
    # —— 句级索引与优化器统计（2026-10-01 深夜，响应速度；数字见优化报告）：
    #   idx_lines_tail     ：句脚字条件（「句脚是愁」）2,948 ms → 65 ms；
    #   idx_lines_tailpz   ：句脚平仄 substr(pz,-1,1) 的表达式索引（子查询侧走索引）；
    #   idx_poems_dyn_scene：声情条件（「后段下降」）174 ms → 24 ms；
    #   ANALYZE            ：写 sqlite_stat1，让优化器按**真实选择性**选索引——
    #                        缺统计时它曾错选 idx_poems_dyn_ze（287 ms），正确索引只要 2 ms。
    # 必须放在**全部插入之后**：先建索引再灌 42 万行会显著拖慢建库。
    con.execute('CREATE INDEX IF NOT EXISTS idx_lines_tail ON lines(tail)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_lines_tailpz ON lines(substr(pz, -1, 1))')
    con.execute('CREATE INDEX IF NOT EXISTS idx_poems_dyn_scene ON poems(dynasty, scene)')
    con.execute('ANALYZE')
    con.commit()
    con.close()
    return n, nline


def fingerprint(db):
    """库内容指纹（与构建顺序无关：按 pid 排序逐行拼接）。"""
    con = sqlite3.connect(db)
    h = hashlib.sha256()
    for row in con.execute('SELECT * FROM poems ORDER BY pid'):
        h.update(('|'.join('' if v is None else str(v) for v in row) + '\n').encode('utf-8'))
    for row in con.execute('SELECT * FROM lines ORDER BY pid, idx'):
        h.update(('|'.join('' if v is None else str(v) for v in row) + '\n').encode('utf-8'))
    con.close()
    return h.hexdigest().upper()


def verify(poems, eng, db, n):
    """抽 n 首用引擎复算，与库中逐字段比对（真验证，不是自我声明）。"""
    con = sqlite3.connect(db)
    cols = [d[0] for d in con.execute('SELECT * FROM poems LIMIT 0').description]
    bad = 0
    n_cmp = 0
    for p in random.Random(11).sample(poems, min(n, len(poems))):
        r = dict(zip(cols, con.execute('SELECT * FROM poems WHERE pid=?', (p.loc,)).fetchone()))
        h = eng.halves(p.raw)
        lg = eng.longest(p.raw)
        rt = eng.ratio(p.raw)
        checks = [
            ('han_len', r['han_len'], len(p.han)),
            ('sent_n', r['sent_n'], len(eng.split(p.raw))),
            ('ping', r['ping'], rt['平']),
            ('ze', r['ze'], rt['仄']),
            ('ze_ratio', r['ze_ratio'], rt['仄声比例']),
            ('cut', r['cut'], h['cut']),
            ('f_ratio', r['f_ratio'], h['前段比例']),
            ('b_ratio', r['b_ratio'], h['后段比例']),
            ('change', r['change'], h['变化']),
            ('abs_change', r['abs_change'], h['绝对变幅']),
            ('longest_seq', r['longest_seq'], json.dumps(lg['最长句序'], ensure_ascii=False)),
            ('longest_len', r['longest_len'], lg['最长句字数']),
            ('threshold', r['threshold'], eng.long_density(p.raw)['阈值']),
            ('scene', r['scene'], eng.scene_emotion(p.raw)['转向']),
        ]
        for name, got, want in checks:
            n_cmp += 1
            if got != want:
                bad += 1
                print('  ✗ %s %s：库=%s 引擎=%s' % (p.loc, name, got, want))
        # 句级：逐句比 平仄串 与句脚
        for k, s in enumerate(eng.split(p.raw)):
            row = con.execute('SELECT pz, tail FROM lines WHERE pid=? AND idx=?', (p.loc, k)).fetchone()
            n_cmp += 2
            if row is None or row[0] != eng.p.ping_ze(s):
                bad += 1
                print('  ✗ %s 第%d句 pz 不符' % (p.loc, k))
            if row is None or row[1] != last_han(s):
                bad += 1
                print('  ✗ %s 第%d句 tail 不符' % (p.loc, k))
    con.close()
    print('抽样复核：比对 %d 项，不符 %d 处 → %s' % (n_cmp, bad, 'PASS' if bad == 0 else 'FAIL'))
    if n_cmp == 0:
        print('  ✗ FAIL：一项都没比对（不许这样报 PASS）')
        return 1
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--db', default='data/corpus.db')
    ap.add_argument('--verify', type=int, default=0, help='随机抽 N 首用引擎复算比对')
    ap.add_argument('--verify-hash', action='store_true')
    ap.add_argument('--no-fts', action='store_true')
    ap.add_argument('--overrides', default=default_overrides_path())
    args = ap.parse_args()

    poems = load_corpus(args.corpus)
    if not poems:
        print('❌ 语料载入为 0 首（--corpus %s 路径不对）' % args.corpus, file=sys.stderr)
        return 2
    eng = Engine(Pronouncer(args.overrides))
    if getattr(eng.p, 'n_overrides', None) == 0:
        print('⚠️ 标定表为空：入库指标会整体偏错，请先检查 %s' % args.overrides, file=sys.stderr)
    n, nline = build(poems, eng, args.db, with_fts=not args.no_fts)
    size = os.path.getsize(args.db) / 1048576.0
    print('入库完成：poems %d 行 / lines %d 行 / %.1f MB -> %s' % (n, nline, size, args.db))
    if args.verify_hash:
        print('内容指纹：%s' % fingerprint(args.db))
    rc = 0
    if args.verify:
        rc = verify(poems, eng, args.db, args.verify)
    return rc


if __name__ == '__main__':
    sys.exit(main())
