# -*- coding: utf-8 -*-
"""review_titles.py —— 题名审核流水线（**大模型逐条判定**；程序只做搬运 / 缓存 / 断点）。

为什么要有它
------------
题名的正确结构是「词牌名（必有）+ 词题（可省）+ 小序（可省）」。但语料里三个来源
（清 poetry-source / 宋·元 chinese-poetry）字段结构不同，导致系统性错误：

  · 宋：`百字谣・念奴娇`、`秦楼月・忆秦娥` —— 中点两侧**都是词牌名**（异名并列）；
  · 元：`尾・对着盏半明不灭的孤灯双眉皱…` —— 中点后是**唱词**，不是词题；
        另有 `诈妮子调风月・仙吕/点绛唇`（剧目・宫调/曲牌）；
  · 清：`望江南白门漫兴`、`二十字令咏便面上栀子花…` —— 词牌与词题**粘连无分隔符**。

这些切分是**语义判断**，任何正则都不可靠（「念奴娇」与「忆秦娥」哪个是正名、
「尾・」后是唱词还是题，都要懂词学才能判）。故本脚本**不做任何判定**，只负责：

  ① 从 `data/corpus.db`（**只读**）取题名与上下文（朝代 / 作者 / 正文首句）；
  ② 把每一条喂给大模型；
  ③ **原样记录大模型自己的判断**（append-only JSONL，按 pid 断点续跑）；
  ④ 失败重试、并发、进度打印。

**判定 100% 来自大模型**，程序不含任何「怎么切」的规则。这是用户明确要求的执行方式。

用法
----
    python tools/review_titles.py --scope pilot --limit 20   # 小样试跑（验通路）
    python tools/review_titles.py --scope pilot              # 试点：问题最重的三类
    python tools/review_titles.py --scope all --workers 8    # 全量 58,852（并发）
    python tools/review_titles.py --show 20                  # 看已有结果
    python tools/review_titles.py --dry-run                  # 只打印一条的 prompt

输出：`data/title_review.jsonl`（每行一条判定；该文件同时充当缓存 → 重跑自动续）。
环境：`UCASS_LLM_URL` / `UCASS_LLM_MODEL` 可覆盖端点与模型（默认校内 Qwen）。
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'data', 'corpus.db')
OUT = os.path.join(ROOT, 'data', 'title_review.jsonl')


def _load_conf():
    """端点/模型/密钥的解析（与端点无关，便于在 Qwen / DeepSeek 间切换）。

    优先级：环境变量 LVC_LLM_* > 本任务专用配置 data/_title_review_llm.json
            > 项目 solve/data/llm_local.json（默认）。
    本任务专用配置用「_」前缀 → 被 .gitignore 的 `**/data/_*` 排除，**不会进仓库**。
    """
    for p in (os.path.join(ROOT, 'data', '_title_review_llm.json'),
              os.path.join(ROOT, 'solve', 'data', 'llm_local.json')):
        try:
            with open(p, encoding='utf-8') as f:
                return json.load(f)
        except Exception:                               # noqa: BLE001
            continue
    return {}


_CONF = _load_conf()
LLM_URL = (os.environ.get('LVC_LLM_URL') or os.environ.get('UCASS_LLM_URL')
           or _CONF.get('url') or 'https://api.deepseek.com/chat/completions')
LLM_MODEL = (os.environ.get('LVC_LLM_MODEL') or os.environ.get('UCASS_LLM_MODEL')
             or _CONF.get('model') or 'deepseek-chat')
LLM_KEY = (os.environ.get('LVC_LLM_KEY') or os.environ.get('DEEPSEEK_API_KEY')
           or _CONF.get('key') or '')

# 已知高频词牌（仅作 prompt 参考，帮助模型区分「词牌」与「词题」；非穷举）
_CIPAI_REF = ('浣溪沙、菩萨蛮、满江红、鹧鸪天、蝶恋花、水调歌头、念奴娇、临江仙、'
              '虞美人、清平乐、卜算子、如梦令、忆秦娥、忆江南、望江南、长相思、'
              '木兰花、玉楼春、踏莎行、南乡子、八声甘州、贺新郎、沁园春、西江月、'
              '浪淘沙、渔家傲、青玉案、点绛唇、一剪梅、醉落魄、一斛珠、阮郎归')

PROMPT = """你是词学专家，精通词牌、词题与小序的区分。请判断下面这条作品题名的结构。

【朝代】{dynasty}
【作者】{author}
【原始题名】{title}
【正文首句】{head}

判定要求：
1. 题名 = 词牌名 + 词题（词题可省）。**词牌名必须有**（它规定格律）；词题是内容标题，可省略。
2. 无词题时，题名**只写词牌名**（如《水调歌头》《浣溪沙》）。
3. 小序（说明写作背景的散文）若混在题名里，请分离到 xu。
4. 特别处理：
   - 中点（· 或 ・）两侧**都是词牌名**（异名并列，如「百字谣・念奴娇」「秦楼月・忆秦娥」）
     → 取**正名**，另一名放 aliases。
   - 元曲题名形如「曲牌・唱词首句」（如「尾・对着盏半明不灭的孤灯…」）→ 唱词**不是**题名，
     须剥离，只留曲牌；形如「剧目・宫调/曲牌」（如「诈妮子调风月・仙吕/点绛唇」）→ 曲牌取斜杠后部分。
   - 词牌与词题**粘连无分隔**（如「望江南白门漫兴」「二十字令咏便面上栀子花」）→ 切分出词牌与词题。
   - 「失调名」= 词牌未详 → cipai 留空、title 保留「失调名」。
   - 「同前」→ 题名待定，cipai 留空。
   - 双中点「··」是录入错误 → 规范为单个「·」。
5. 常见词牌参考（非穷举）：{cipai_ref}

只输出一个 JSON（不要任何多余文字、不要 markdown 代码块）：
{{"cipai": "词牌正名", "ti": "词题，无则 null", "xu": "小序，无则 null", "title": "规范题名", "aliases": ["异名"], "confidence": 0.95, "note": "一句理由"}}
"""


def first_sentence(raw):
    """正文首句（截断），作为判定上下文。"""
    s = (raw or '').strip()
    if not s:
        return ''
    return re.split(r'[。？！]', s, maxsplit=1)[0][:40]


def extract_json(text):
    """从大模型输出里抠出第一个平衡的 JSON 对象（容忍代码块/前后杂字）。"""
    s = (text or '').strip()
    s = re.sub(r'^```(?:json)?|```$', '', s, flags=re.M).strip()
    start = s.find('{')
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start:i + 1])
                except Exception:                       # noqa: BLE001
                    return None
    return None


def call_llm(prompt, timeout=120, retries=4):
    body = json.dumps({
        'model': LLM_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 1200,
        'temperature': 0,
    }).encode('utf-8')
    last = None
    headers = {'Content-Type': 'application/json'}
    if LLM_KEY:
        headers['Authorization'] = 'Bearer %s' % LLM_KEY
    for i in range(retries):
        try:
            req = urllib.request.Request(LLM_URL, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                r = json.loads(resp.read().decode('utf-8'))
            msg = r['choices'][0]['message']
            content = msg.get('content') or msg.get('reasoning_content') or ''
            if content.strip():
                return content
            last = 'EMPTY'
        except Exception as e:                          # noqa: BLE001
            last = '%s: %s' % (type(e).__name__, e)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError('LLM 调用失败：%s' % last)


def judge(row):
    """把一条记录交给大模型判定，返回可落盘的记录（含大模型原始判断）。"""
    head = first_sentence(row['raw'])
    prompt = PROMPT.format(dynasty=row['dynasty'], author=row['author'],
                           title=row['title'], head=head, cipai_ref=_CIPAI_REF)
    text = call_llm(prompt)
    obj = extract_json(text)
    if obj is None:
        return {'pid': row['pid'], 'dynasty': row['dynasty'], 'author': row['author'],
                'orig_title': row['title'], 'orig_cipai': row['cipai'],
                'error': 'JSON_PARSE_FAILED', 'raw_llm': (text or '')[:400],
                'model': LLM_MODEL, 'ts': time.strftime('%Y-%m-%d %H:%M:%S')}
    def _s(v):
        return '' if v in (None, 'null', 'None') else str(v).strip()
    aliases = obj.get('aliases') or []
    if isinstance(aliases, str):
        aliases = [aliases]
    return {
        'pid': row['pid'], 'dynasty': row['dynasty'], 'author': row['author'],
        'orig_title': row['title'], 'orig_cipai': row['cipai'],
        'cipai': _s(obj.get('cipai')), 'ti': _s(obj.get('ti')), 'xu': _s(obj.get('xu')),
        'title': _s(obj.get('title')) or row['title'],
        'aliases': [a for a in (_s(x) for x in aliases) if a],
        'confidence': obj.get('confidence'), 'note': _s(obj.get('note')),
        'model': LLM_MODEL, 'ts': time.strftime('%Y-%m-%d %H:%M:%S'),
    }


SCOPE_SQL = {
    'all': "SELECT pid,dynasty,author,title,cipai,raw FROM poems",
    'pilot': ("SELECT pid,dynasty,author,title,cipai,raw FROM poems WHERE "
              "(dynasty='宋' AND title LIKE '%・%') OR "
              "(dynasty='元' AND title LIKE '%・%') OR "
              "(dynasty='清' AND title NOT LIKE '%·%' AND title NOT LIKE '%・%' "
              "AND LENGTH(title)>=6)"),
}


def load_done():
    """已判定的 pid 集合（断点续跑）。"""
    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            for ln in f:
                try:
                    done.add(json.loads(ln)['pid'])
                except Exception:                       # noqa: BLE001
                    pass
    return done


def main():
    ap = argparse.ArgumentParser(description='题名审核流水线（大模型逐条判定）')
    ap.add_argument('--scope', choices=['all', 'pilot'], default='pilot')
    ap.add_argument('--limit', type=int, default=0, help='只跑前 N 条（0=全部）')
    ap.add_argument('--workers', type=int, default=6, help='并发数')
    ap.add_argument('--where', default=None, help='自定义 SQL WHERE（覆盖 --scope）')
    ap.add_argument('--dry-run', action='store_true', help='只打印一条 prompt，不调用')
    ap.add_argument('--show', type=int, default=0, help='显示已有结果 N 条')
    ap.add_argument('--next', type=int, default=0, help='打印下一批 N 条待判定（逐条交大模型判定）')
    ap.add_argument('--ingest', default=None, help='并入判定结果 JSONL → data/title_review.jsonl')
    ap.add_argument('--db', default=DB)
    args = ap.parse_args()

    if args.ingest:
        cur = {}
        if os.path.exists(OUT):
            with open(OUT, encoding='utf-8') as f:
                for ln in f:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        d = json.loads(ln)
                    except Exception:                   # noqa: BLE001
                        continue
                    cur[d['pid']] = d
        n = 0
        with open(args.ingest, encoding='utf-8') as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                if ln.startswith('{'):
                    try:
                        d = json.loads(ln)
                    except Exception:                   # noqa: BLE001
                        continue
                    cur[d['pid']] = d
                    n += 1
                else:
                    # 空白/逗号分隔的裸 pid 列表 → 全部标记「已核验、无需改动」
                    for p in ln.replace(',', ' ').split():
                        cur[p] = {'pid': p, 'verified': True}
                        n += 1
        with open(OUT, 'w', encoding='utf-8') as o:
            for d in cur.values():
                o.write(json.dumps(d, ensure_ascii=False) + '\n')
        print('已并入 %d 条（现有 %d 条，按 pid 去重后写回）→ %s' % (n, len(cur), OUT))
        return 0

    if args.show:
        if not os.path.exists(OUT):
            print('（尚无结果）')
            return 0
        with open(OUT, encoding='utf-8') as f:
            for i, ln in enumerate(f):
                if i >= args.show:
                    break
                d = json.loads(ln)
                print('  [%s] %-30s → cipai=%-8s ti=%-14s title=%s'
                      % (d.get('dynasty'), (d.get('orig_title') or '')[:30],
                         d.get('cipai') or '-', (d.get('ti') or '-')[:14],
                         d.get('title') or '-'))
        return 0

    conn = sqlite3.connect('file:%s?mode=ro' % args.db, uri=True)
    conn.row_factory = sqlite3.Row
    sql = SCOPE_SQL[args.scope] if not args.where else (
        'SELECT pid,dynasty,author,title,cipai,raw FROM poems WHERE ' + args.where)
    rows = [dict(r) for r in conn.execute(sql)]

    if args.next:
        done = load_done()
        remain = [r for r in rows if r['pid'] not in done]
        for i, r in enumerate(remain[:args.next], 1):
            print('%d\t%s\t%s\t%s\t%s\t%s' % (i, r['pid'], r['dynasty'], r['author'],
                                              r['title'], first_sentence(r['raw'])))
        print('=== 本批 %d 条 ｜ 剩余未判定 %d 条 ===' % (min(len(remain), args.next), len(remain)))
        return 0

    if args.dry_run:
        r = rows[0]
        print(PROMPT.format(dynasty=r['dynasty'], author=r['author'], title=r['title'],
                            head=first_sentence(r['raw']), cipai_ref=_CIPAI_REF))
        return 0

    done = load_done()
    todo = [r for r in rows if r['pid'] not in done]
    if args.limit:
        todo = todo[:args.limit]
    print('范围 %s：命中 %d 条，已判定 %d 条，本次待办 %d 条（并发 %d）'
          % (args.scope, len(rows), len(done), len(todo), args.workers))
    if not todo:
        print('全部已完成。')
        return 0

    lock = threading.Lock()
    fout = open(OUT, 'a', encoding='utf-8')
    n_ok = n_err = 0
    t0 = time.time()
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(judge, r): r for r in todo}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            try:
                rec = fut.result()
            except Exception as e:                      # noqa: BLE001
                r = futs[fut]
                rec = {'pid': r['pid'], 'dynasty': r['dynasty'], 'author': r['author'],
                       'orig_title': r['title'], 'orig_cipai': r['cipai'],
                       'error': '%s: %s' % (type(e).__name__, e), 'model': LLM_MODEL,
                       'ts': time.strftime('%Y-%m-%d %H:%M:%S')}
            with lock:
                fout.write(json.dumps(rec, ensure_ascii=False) + '\n')
                if i % 20 == 0:
                    fout.flush()
                if rec.get('error'):
                    n_err += 1
                else:
                    n_ok += 1
                if i % 25 == 0 or i == len(todo):
                    el = time.time() - t0
                    print('  … %d/%d（ok=%d err=%d，%.0f 秒，%.1f 条/秒）'
                          % (i, len(todo), n_ok, n_err, el, i / max(el, 0.1)), flush=True)
    fout.close()
    print('完成：ok=%d err=%d，写入 %s' % (n_ok, n_err, OUT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
