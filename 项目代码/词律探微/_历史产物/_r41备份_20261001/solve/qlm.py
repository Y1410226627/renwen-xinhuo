# -*- coding: utf-8 -*-
"""qlm.py —— 「查询理解层」（大模型路）：把口语问句解成**结构化条件**，再由引擎校验与执行。

分工纪律（与 gen.py 一致，不越界）：
    大模型**只负责把话听明白**，不负责算数、不负责下结论、不负责引用；
    它给出的每个字段都要在这里过一遍**能落地校验**（必须能在数据库上复算）：
      · dynasty  ∈ {清,宋,元} 且库里有篇目；库外朝代（唐/汉…）→ 记 pending → 拒答；
      · author / cipai  必须在库里存在（不存在 → 丢弃并记明原因）；
      · tail  必须是**单个汉字**（含 CJK 扩展 A）；tail_pz ∈ {平,仄}；
      · pz  只能由 平/仄/？ 组成；scene ∈ {后段上升,后段下降,前后持平}；
      · rng  只认 10 个键，且数值在合理区间；
      · keywords **一律丢弃**（自由文本不许进 SQL）。
    校验不过的字段**不静默丢**：写进 `dropped`，由回答正文如实说明。
    无密钥 / 断网 / JSON 不合法 → 返回 None，调用方回落到规则解析（`retrieve.parse_query`）。

为什么需要它：规则解析对并列/口语（「句脚是「灯」或者「声」」「前段比后段更仄的」）不敏感，
2026-09-30 主人实测抓到「或者」被当词面条件、后半个条件被丢掉。大模型理解 + 引擎校验 = 既听得懂，
又不许它改数、不许它编条件。

用法（自检/演示）：
    python solve/qlm.py --db data/corpus.db --question "句脚是「灯」或者「声」的清词有哪些"
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aggregate                                              # noqa: E402
import retrieve                                               # noqa: E402

DYN_OK = ('清', '宋', '元')
RNG_KEYS = ('ze_min', 'ze_max', 'len_min', 'len_max', 'sent_min', 'sent_max',
            'change_min', 'change_max', 'thr_min', 'thr_max')
RNG_BOUNDS = {'ze_min': (0, 100), 'ze_max': (0, 100), 'len_min': (1, 500), 'len_max': (1, 500),
              'sent_min': (1, 80), 'sent_max': (1, 80), 'change_min': (-100, 100),
              'change_max': (-100, 100), 'thr_min': (1, 60), 'thr_max': (1, 60)}
SCENE_OK = ('后段上升', '后段下降', '前后持平')
SCENE_ALIAS = {'上升': '后段上升', '升高': '后段上升', '下降': '后段下降', '降低': '后段下降',
               '持平': '前后持平', '不变': '前后持平', '前段更高': '后段下降', '后段更高': '后段上升'}

SYSTEM = (
    '你是「词律探微」（清代词律声情研究助手）的**查询理解**模块。\n'
    '你的唯一任务：把研究者的自然语言提问，翻译成一个 JSON 对象，供检索程序执行。\n'
    '只输出这个 JSON 对象本身，不要解释、不要代码块、不要多余文字。\n'
    '\n'
    'JSON 字段（没有的写 null，列表写 []）：\n'
    '  "dynasty": 朝代，只能取 "清"、"宋"、"元"；语料不含别的朝代（如唐宋之外一律 null）。\n'
    '  "authors": 词人姓名列表（如 ["朱彝尊"]；不确定就写 []）。\n'
    '  "cipais":  词牌名列表（如 ["临江仙"]）。\n'
    '  "tail":    句脚字列表，每个元素必须是**一个字**（如 ["灯","声"]）。\n'
    '  "tail_pz": 句脚平仄，只能 "平" 或 "仄"。\n'
    '  "pz":      声律模式，只由「平」「仄」「？」组成且长度≥3（如 "仄仄平平仄"）。\n'
    '  "scene":   声情转向，只能 "后段上升"、"后段下降"、"前后持平"。\n'
    '  "rng":     数值条件对象，可用键：\n'
    '             ze_min/ze_max（仄声比例百分数）、len_min/len_max（汉字数）、\n'
    '             sent_min/sent_max（句数）、change_min/change_max（变化值）、\n'
    '             thr_min/thr_max（长句阈值）。如 {"ze_min": 45}。\n'
    '  "unparsed": 你无法映射成上述条件的短语列表（如实填写，不许硬凑）。\n'
    '  "order":  **极值／排序**意图（问「哪一首…最高/最低/最多/最长」时）。形如\n'
    '             {"metric":"ze_ratio"|"ping_ratio"|"han_len"|"sent_n"|"longest_len"|"change",\n'
    '              "dir":"max"|"min"}。不是极值题就写 null（千万不要把「最高」硬凑成条件）。\n'
    '  "pair":   **配对题**（问「找出几对…每个位置上的平仄都相同的两首词」时）写 true，\n'
    '             可选 "pair_dim":"tone"（平仄）或 "text"（字面）。不是配对题就写 null。\n'
    '             ★ 配对题**不要**填 pz／tail 等条件——它要的不是「筛篇」而是「配对」。\n'
    '  "agg":     **分组对比/统计**题专用（问「哪一类更高/更大/更多」时）。形如\n'
    '             {"group_by":"dynasty"|"author"|"cipai", "values":["宋","清"],\n'
    '              "metric":"ze_ratio"|"ping_ratio"|"han_len"|"sent_n"}。\n'
    '             不是对比题就写 null。写了 agg 就**不要**再填 dynasty/authors/cipais\n'
    '             （那些是**组名**，不是检索限定）。\n'
    '\n'
    '规则：\n'
    '1) **并列/选择要拆成列表**：「句脚是灯或者声的」→ "tail": ["灯","声"]；\n'
    '   「清或宋的」→ 这类跨朝代并列写 "dynasty": "清" 并把「或宋」放进 "unparsed"。\n'
    '2) 只翻译**条件**，不要翻译「有哪些」「请列举」这类语气词，也不要输出任何检索词。\n'
    '3) 不许臆造条件：问句没提的字段一律 null/[]。\n'
    '4) 数字原样照抄（45% → 45）。\n'
)


def _json_block(text):
    """从模型输出里抠出第一个配对完整的 JSON 对象（字符串内的括号不计数）。"""
    if not text:
        return None
    i = text.find('{')
    if i < 0:
        return None
    depth, in_str, esc = 0, False, False
    for j in range(i, len(text)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i:j + 1])
                except ValueError:
                    return None
    return None


def _as_list(v):
    if v is None or v == '':
        return []
    if isinstance(v, (list, tuple)):
        return [x for x in v if x not in (None, '') and isinstance(x, str)]
    if isinstance(v, str):
        return [v]
    return []          # 数字/布尔等标量不是条件（审查 B32：「朝代=0」曾会被当成条件）


def validate(conn, obj, question=''):
    """把模型给的 JSON 校验成 QuerySpec。返回 (spec, dropped, notes)。"""
    dropped, notes = [], []
    spec = retrieve.QuerySpec()
    spec.raw = question
    spec.source = '大模型'
    spec.unparsed = [str(x) for x in _as_list(obj.get('unparsed'))]

    # 朝代：**宽容接受列表**（模型常把并列朝代写成列表）——但列表不能在检索层使用，
    # 它要么是「对比题的两个组」（交给 agg 处置），要么是模型自作主张（记 note）。
    dyn_list = [str(x).strip() for x in _as_list(obj.get('dynasty'))]
    ok_dyn = [d for d in dyn_list if d in DYN_OK]
    bad_dyn = [d for d in dyn_list if d not in DYN_OK]
    multi_dyn = []
    if len(dyn_list) >= 2 and len(ok_dyn) >= 2:
        multi_dyn = ok_dyn
        notes.append('朝代给了多个值（%s）：本系统不做跨朝代并列检索，'
                     '对比题请用 agg 字段；已按下文处置' % '／'.join(ok_dyn))
    elif len(ok_dyn) == 1:
        dyn = ok_dyn[0]
        n = conn.execute('SELECT COUNT(*) FROM poems WHERE dynasty=?', (dyn,)).fetchone()[0]
        if n:
            spec.dynasty_any = [dyn]
        else:
            dropped.append('朝代=%s（库里没有）' % dyn)
    if bad_dyn:                                   # 语料外朝代 → 走拒答路径
        # 不能循环覆盖、只留最后一个（审查 B17：问「唐诗与汉代」曾只报「汉」）
        spec.unsupported = '／'.join(bad_dyn)
        for d in bad_dyn:
            notes.append('朝代=%s 不在语料范围' % d)

    # 模型可能把 authors 写成显式 null、值放在 author 里（审查 B33）
    au = [str(x).strip() for x in _as_list(obj.get('authors') or obj.get('author'))]
    real = {r[0] for r in conn.execute('SELECT author FROM authors')}
    for a in au:
        if a in real:
            spec.author_any.append(a)
        else:
            dropped.append('词人=%s（库中没有此人）' % a)

    cp = [str(x).strip() for x in _as_list(obj.get('cipais', obj.get('cipai')))]
    realc = {r[0] for r in conn.execute('SELECT cipai FROM cipai')}
    for c in cp:
        if c in realc:
            spec.cipai_any.append(c)
        else:
            dropped.append('词牌=%s（库中没有此调）' % c)

    tl = [str(x).strip() for x in _as_list(obj.get('tail'))]
    for ch in tl:
        if len(ch) == 1 and retrieve.is_hanzi(ch):
            spec.tail_any.append(ch)
        else:
            dropped.append('句脚字=%s（不是一个汉字）' % ch)

    tp = obj.get('tail_pz')
    if tp in ('平', '仄'):
        spec.tail_pz = tp
    elif tp:
        dropped.append('句脚平仄=%s（只能是平/仄）' % tp)

    pz = obj.get('pz')
    if pz:
        pzs = str(pz).strip()
        if retrieve.PZ_RE.match(pzs):
            spec.pz = pzs
        else:
            dropped.append('声律模式=%s（只能由平/仄/？组成且≥3 位）' % pzs)

    sc = obj.get('scene')
    if sc:
        sc = SCENE_ALIAS.get(str(sc).strip(), str(sc).strip())
        if sc in SCENE_OK:
            spec.scene = sc
        else:
            dropped.append('声情=%s（只能是后段上升/后段下降/前后持平）' % sc)

    rng = obj.get('rng') or {}
    if isinstance(rng, dict):
        for k, v in rng.items():
            if v is None or v == '':        # 模型常把所有键都列出来、没给的写 null
                continue
            if k not in RNG_KEYS:
                dropped.append('数值条件 %s（不认识）' % k)
                continue
            try:
                f = float(v)
            except (TypeError, ValueError):
                dropped.append('数值条件 %s=%s（不是数字）' % (k, v))
                continue
            lo, hi = RNG_BOUNDS[k]
            if not (lo <= f <= hi):
                dropped.append('数值条件 %s=%s（超出合理区间 %s–%s）' % (k, v, lo, hi))
                continue
            spec.rng[k] = int(f) if f.is_integer() and k.startswith(('len', 'sent', 'thr')) else f
    elif rng:
        dropped.append('rng 字段不是对象')

    for k in obj:
        if k not in ('dynasty', 'authors', 'author', 'cipais', 'cipai', 'tail', 'tail_pz',
                     'pz', 'scene', 'rng', 'unparsed', 'agg', 'order', 'sort', 'pair',
                     'pair_dim'):
            notes.append('模型多给的字段 %s 已忽略' % k)

    # 分组对比（聚合）题：组名同样要**逐个在库上验**（落不了库的进 dropped）
    ag = obj.get('agg')
    if isinstance(ag, dict) and ag:
        gb = str(ag.get('group_by') or '').strip()
        mt = str(ag.get('metric') or 'ze_ratio').strip()
        # ⭐ 组内极值：「哪个词人/词牌…最多」——问句里没有组名，靠 extreme 标记方向
        _extreme = str(ag.get('extreme') or '').strip().lower() or None
        if _extreme not in ('max', 'min'):
            _extreme = None
        vals = [str(x).strip() for x in _as_list(ag.get('values'))]
        # 模型常把组名放错地方（写了 agg 却把 ["宋","清"] 放进 dynasty）——
        # 宽容：按 group_by 从对应字段里回填，但要经库上逐个校验后才生效。
        if not vals:
            vals = {'dynasty': multi_dyn or spec.dynasty_any,
                    'author': [a for a in au if a in real],
                    'cipai': [c for c in cp if c in realc]}.get(gb, [])
            if vals:
                notes.append('agg.values 未给，已按 %s 从问句解析的组名回填（%s）'
                             % (gb, '／'.join(vals)))
        if gb not in aggregate.GROUPS:
            dropped.append('agg.group_by=%s（只能是 dynasty/author/cipai）' % gb)
        elif mt not in aggregate.METRICS:
            dropped.append('agg.metric=%s（只能是 ze_ratio/ping_ratio/han_len/sent_n/share/count）' % mt)
        elif len(vals) < 2 and _extreme:
            # ⭐ **组内极值**：没有组名是这类问法的**正常形态**（「哪个词人的词最多」）。
            #    只清空 group_by 自己那一维的筛选（避免把「作者=某某」当限定），
            #    其它维度（朝代/词牌/句脚…）**照旧当筛选条件**——这一点很关键：
            #    「句脚为平 清 临江仙…哪个词人最多」里的 清/临江仙/句脚平 全是筛选。
            spec.agg = {'group_by': gb, 'values': None, 'metric': mt, 'text': question,
                        'extreme': _extreme, 'note': ''}
            if gb == 'author':
                spec.author_any, spec.author = [], None
            elif gb == 'cipai':
                spec.cipai_any, spec.cipai = [], None
            elif gb == 'dynasty':
                spec.dynasty_any, spec.dynasty = [], None
            notes.append('按%s分组做**组内极值**统计（取%s）'
                         % (gb, '最多' if _extreme == 'max' else '最少'))
        elif len(vals) < 2:
            dropped.append('agg.values（对比题至少要两个组；组内极值请写 "extreme":"max"/"min"）')
        else:
            col = {'dynasty': 'dynasty', 'author': 'author', 'cipai': 'cipai'}[gb]
            ok = []
            for v in vals:
                n = conn.execute('SELECT COUNT(*) FROM poems WHERE %s=?' % col, (v,)).fetchone()[0]
                if n:
                    ok.append(v)
                else:
                    dropped.append('对比组 %s=%s（库里没有）' % (gb, v))
            if len(ok) >= 2:
                spec.agg = {'group_by': gb, 'values': ok, 'metric': mt, 'text': question,
                            'extreme': None, 'note': ''}
                # 组名不是检索限定：清空单值字段，避免两义相混
                spec.dynasty_any, spec.dynasty = [], None
                spec.author_any, spec.author = [], None
                spec.cipai_any, spec.cipai = [], None
                spec.keywords = []
            else:
                dropped.append('agg（可比的组不足两个，未启用分组统计）')
    elif ag:
        dropped.append('agg 字段不是对象')

    # 极值／排序意图（「哪一首…最高/最低」）：**指标走白名单**，方向只认 max/min。
    # ⚠ 实测踩过（2026-09-30 主人第七炮续）：模型只听了「词人=高旭」、**没听出「最高」**，
    # 而 `ask.understand` 当时只给朝代/语料外朝代/对比题加了安全网，没给排序加——
    # 于是规则路已识别的排序被丢掉，答案又从「极值篇」退回「融合排序最前者」。
    # 这里接受模型给的排序（白名单校验），**模型没给也不打紧**：调用方会用规则解析补回。
    od = obj.get('order', obj.get('sort'))
    if isinstance(od, dict) and od:
        mt = str(od.get('metric') or '').strip()
        dv = str(od.get('dir') or 'max').strip().lower()
        dv = {'high': 'max', 'desc': 'max', 'descending': 'max', '最高': 'max', '取高': 'max',
              'low': 'min', 'asc': 'min', 'ascending': 'min', '最低': 'min', '取低': 'min'}.get(dv, dv)
        if mt not in retrieve.ORDER_COLS:
            dropped.append('排序指标=%s（只能是 %s）'
                           % (mt, '／'.join(retrieve.ORDER_COLS)))
        elif dv not in ('max', 'min'):
            dropped.append('排序方向=%s（只能是 max/min）' % dv)
        else:
            col, label, flip = retrieve.ORDER_COLS[mt]
            asc = (dv == 'min') != bool(flip)
            spec.order_by, spec.order_col = mt, col
            spec.order_dir, spec.extreme = ('asc' if asc else 'desc'), dv
            spec.order_label, spec.order_src = label, '大模型'
    elif od:
        dropped.append('order 字段不是对象')

    # 配对题（「找出几对…平仄都相同的两首词」）：这不是「筛篇」而是「配对」，绝不能允许
    # 把问句本身当成词面/声律条件（实测：旧版从问句里捏出「声律模式=平仄平仄平仄平仄」）。
    # 本层只认「pair=true」这个声明；真正的判定量（全篇平仄串）由 `pairing` 模块算，
    # 模型没听出来也不打紧——`ask.understand` 会用规则路补回。
    if obj.get('pair'):
        dim = str(obj.get('pair_dim') or 'tone').strip().lower()
        dims = ('tone',) if dim in ('tone', 'pz', 'ping_ze', '声调', '平仄') else \
            ('text',) if dim in ('text', '字面', '用字', '字词') else ('tone',)
        if dim not in ('tone', 'pz', 'ping_ze', '声调', '平仄', 'text', '字面', '用字', '字词'):
            dropped.append('配对维度=%s（只能是 tone/text）' % dim)
        spec.pair = {'dims': dims, 'n_frame': 1}
        spec.pair_label = '全篇逐位平仄完全相同' if dims == ('tone',) else '不支持的维度'
        spec.keywords = []
    return retrieve._finalize(spec), dropped, notes


def parse(conn, llm, question, temperature=0.0, max_tokens=400):
    """大模型理解问句。失败一律返回 None（调用方回落规则解析）。"""
    if not (llm and llm.available()):
        return None
    # 流式 + **见到完整 JSON 即断开**：理解路的输出就是一个小 JSON 对象，
    # 实测首字 0.34~0.47 秒、完整对象约 1.6~2.2 秒返回，且不必为多余的尾巴继续等。
    kw = {'temperature': temperature, 'max_tokens': max_tokens}
    try:
        _sig = llm.chat.__code__.co_varnames
        if 'expect_json' in _sig:
            kw['expect_json'] = True
    except Exception:
        pass
    raw = llm.chat([{'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': '问句：%s' % question}], **kw)
    obj = _json_block(raw)
    if obj is None:
        return None
    spec, dropped, notes = validate(conn, obj, question)
    spec.source = '大模型 %s' % (getattr(llm, 'name', '') or '未知模型')
    return {'spec': spec, 'dropped': dropped, 'notes': notes,
            'model': getattr(llm, 'name', '') or '未知模型', 'raw': raw or ''}


def main():
    ap = argparse.ArgumentParser(description='查询理解（大模型路）：问句 → 结构化条件（引擎校验）')
    ap.add_argument('--db', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'data', 'corpus.db'))
    ap.add_argument('--question', required=True)
    ap.add_argument('--provider', default=None)
    args = ap.parse_args()
    import llm as L
    conn = sqlite3.connect(args.db)
    client = L.LLM(provider=args.provider)
    print('模型：%s（可用=%s）' % (client.name or '无', client.available()))
    rs = parse(conn, client, args.question)
    if rs is None:
        print('大模型不可用或输出不是合法 JSON → 规则解析：%s'
              % retrieve.parse_query(conn, args.question).describe())
        return 1
    print('大模型原始输出：%s' % rs['raw'])
    print('校验后条件：%s' % rs['spec'].describe())
    print('丢弃项：%s' % (rs['dropped'] or '无'))
    print('提示：%s' % (rs['notes'] or '无'))
    print('未理解片段：%s' % (rs['spec'].unparsed or '无'))
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
