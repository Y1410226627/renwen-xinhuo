/* core/parse.js —— 「逐字解析 + 多条件检索」的**纯逻辑层**（零 DOM；Vue 组件与 node 门禁共用）。
 *
 * 两种运行方式，**同一份代码**：
 *   · 离线（data/parse.html）：数据内嵌在页面里（window.EMBED_PACK），全部在浏览器本地算；
 *   · 在线（/browse.html）：条件发给 /api/search，由 SQLite 查（行级条件用 lines 表）。
 * 数字口径一律走 core/metrics.js（与 Python 引擎同一套，见 web/verify_views.js）。
 *
 * ⚠ 架构说明（D15）：本文件是**唯一真源**；`web/app_parse.js` 只是 `require` 本文件的薄转发。
 *   外壳用 UMD（经典脚本）：**既能在 node 的 `vm` 沙箱里直接加载**（旧门禁一行不改），
 *   也能被 Vite 打包进 Vue 组件（`frontend/src/core/index.mjs` 提供 ESM 桥接）。
 *
 * 对外接口（纯函数，不碰 DOM，可被 node 直接断言；`detailHtml` 的**字符串格式是硬契约**，
 * 被 web/test_render.js 逐串比对）：
 *   setData(pack) / setLive(base) / isLive() / analyze(text) / info(row) / matchCond(info, cond, row)
 *   splitSents / pzOf / tailOf / pzTest / searchOffline / detailHtml / listRow / facets / condText
 *   highlight / pageSlice / resetCache
 */
(function (root, factory) {
  var api = factory(root.Metrics, root.UI);
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  if (root) { root.ParseApp = api; }
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this),
  function (M, U) {
  'use strict';

const HAN = M.HAN;
let TMAP = {};
let ROWS = null;
let LIVE = null;                 // {base:'/api'} 时走在线搜索
let CACHE = [];

function splitSents(t) {
  /* 与 solve/prosody.py 的 Engine.split **逐字对齐**（重要，实测踩过）：
   *   ① 先去掉换行；② 在句末标点【之后】切（标点留在前句，引文才能原样回定位）；
   *   ③ 丢掉「没有汉字」的碎片（如单独一个标点／空白）——旧版漏了③，
   *      遇到含此类碎片的篇目，前端句数会比引擎多 1，前后段比例跟着全错。
   * 这一条是「全库对照」门禁（verify_views.js --all）抓出来的，抽样门禁没抓到。 */
  const raw = String(t || '').replace(/\n/g, '');
  const out = [];
  let cur = '';
  for (let i = 0; i < raw.length; i++) {
    const c = raw[i];
    cur += c;
    if ('。？！'.indexOf(c) >= 0) { if (M.hanOnly(cur).length) { out.push(cur.trim()); } cur = ''; }
  }
  if (cur && M.hanOnly(cur).length) { out.push(cur.trim()); }
  return out;
}

function pzOf(s) {
  let o = '';
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (HAN.test(c)) { o += (TMAP[c] === '2') ? '仄' : '平'; }
  }
  return o;
}

function tailOf(s) {                       // 句脚字 = 该句最后一个**汉字**
  for (let i = s.length - 1; i >= 0; i--) { if (HAN.test(s[i])) { return s[i]; } }
  return '';
}

function analyze(text) {
  const sents = splitSents(text || '');
  const lines = sents.map((s) => ({ text: s, pz: pzOf(s), tail: tailOf(s) }));
  return { sents, lines, metrics: M.compute(lines) };
}

function setData(pack) {
  ROWS = pack.rows;
  TMAP = {};
  const ch = pack.tonemap[0], tn = pack.tonemap[1];
  for (let i = 0; i < ch.length; i++) { TMAP[ch[i]] = tn[i]; }
  CACHE = [];
  return ROWS.length;
}

function setLive(base) { LIVE = { base: base || '' }; }
function isLive() { return !!LIVE; }
function resetCache() { CACHE = []; }

/* 行 → 全部指标（离线自算，缓存；与库中字段同口径） */
function info(row, i) {
  if (i === undefined) { i = ROWS ? ROWS.indexOf(row) : -1; }
  if (i >= 0 && CACHE[i]) { return CACHE[i]; }
  const a = analyze(row[5]);
  const o = { lines: a.lines, metrics: a.metrics, tails: a.lines.map((L) => L.tail),
              pzAll: a.lines.map((L) => L.pz) };
  if (i >= 0) { CACHE[i] = o; }
  return o;
}

/* 声律模式白名单：整串只允许「平」「仄」「?」「？」（与 solve/retrieve.py 的 PZ_RE
   以及 web/serve.py 的 _pz_glob 同一口径）。 */
const PZ_OK = /^[平仄?？]+$/;

/* 平仄模式：平/仄 原样，?/？ = 任意一字。
   ⚠ 旧版把「不是 平/仄 的字符」一律改成 '.'（通配符）→「平仄abc」被当成「平仄???」
   照常检索，用户打错却拿到一个看起来正常的答案。现改为严格白名单：只要有非法字符就
   返回 null（表示「非法输入」），**不静默当通配符**（对齐 web/serve.py:_pz_glob，P1-34）。 */
function pzTest(pat) {
  if (!pat) { return null; }
  const s = String(pat).trim();
  if (!s || !PZ_OK.test(s)) { return null; }
  let body = '';
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    body += (c === '平' || c === '仄') ? c : '.';
  }
  return new RegExp(body);
}

/* 条件是否命中（离线与在线**同一张判定表**；在线由 SQL 负责等价实现） */
function matchCond(inf, cond, row) {
  const m = inf.metrics;
  const c = cond || {};
  if (row) {
    if (c.dynasty && String(row[1]) !== c.dynasty) { return false; }
    if (c.author && String(row[2]).indexOf(c.author) < 0) { return false; }
    if (c.cipai && String(row[3]).indexOf(c.cipai) < 0) { return false; }
  }
  /* 数值条件一律用「显式判空 + Number()」：旧版写 `c.minLen && ...`，
     当 minLen=0（用户明确想「字数≥0」或分面点击写入 0）时被当成空值静默跳过。
     与下面 minZe/maxZe 的写法统一（`!== undefined && !== ''`）。 */
  if (c.minLen !== undefined && c.minLen !== '' && m.han_len < Number(c.minLen)) { return false; }
  if (c.maxLen !== undefined && c.maxLen !== '' && m.han_len > Number(c.maxLen)) { return false; }
  if (c.minSent !== undefined && c.minSent !== '' && m.sent_n < Number(c.minSent)) { return false; }
  if (c.maxSent !== undefined && c.maxSent !== '' && m.sent_n > Number(c.maxSent)) { return false; }
  if (c.minZe !== undefined && c.minZe !== '' && m.ze_ratio < Number(c.minZe)) { return false; }
  if (c.maxZe !== undefined && c.maxZe !== '' && m.ze_ratio > Number(c.maxZe)) { return false; }
  if (c.minLong !== undefined && c.minLong !== '' && m.longest_len < Number(c.minLong)) { return false; }
  if (c.changeMin !== undefined && c.changeMin !== '' && m.change < Number(c.changeMin)) { return false; }
  if (c.changeMax !== undefined && c.changeMax !== '' && m.change > Number(c.changeMax)) { return false; }
  if (c.thrMin !== undefined && c.thrMin !== '' && m.threshold < Number(c.thrMin)) { return false; }
  if (c.thrMax !== undefined && c.thrMax !== '' && m.threshold > Number(c.thrMax)) { return false; }
  if (c.scene && m.scene !== c.scene) { return false; }
  if (c.tailPz) {                       // 句脚平仄 = 该句平仄串的最后一个字（与引擎同一口径）
    let pzOk = false;
    for (let q = 0; q < inf.pzAll.length; q++) {
      const p1 = inf.pzAll[q];
      if (p1 && p1.charAt(p1.length - 1) === c.tailPz) { pzOk = true; break; }
    }
    if (!pzOk) { return false; }
  }
  if (c.tail) {
    const want = String(c.tail).replace(/[\s，,、;；]+/g, '').split('');
    let ok = false;
    for (let i = 0; i < want.length; i++) {
      for (let j = 0; j < inf.tails.length; j++) {
        if (inf.tails[j] && inf.tails[j] === want[i]) { ok = true; break; }
      }
      if (ok) { break; }
    }
    if (!ok) { return false; }
  }
  if (c.pz) {
    const re = pzTest(c.pz);
    if (!re) { return false; }            // 含非法字符 / 空串：显式判为「不命中」，不静默当通配符
    let hit = false;
    for (let k = 0; k < inf.pzAll.length; k++) { if (re.test(inf.pzAll[k])) { hit = true; break; } }
    if (!hit) { return false; }
  }
  return true;
}

function textHit(row, q) {
  if (!q) { return true; }
  return row[2].indexOf(q) >= 0 || row[3].indexOf(q) >= 0
      || row[4].indexOf(q) >= 0 || row[5].indexOf(q) >= 0;
}

function facets(hits) {
  const byAu = {}, byCp = {}, byTl = {},
        bucket = { '0–25%': 0, '25–40%': 0, '40–50%': 0, '50–65%': 0, '65–100%': 0 }, bySc = {};
  hits.forEach((h) => {
    const r = h.row, m = h.info.metrics;
    byAu[r[2]] = (byAu[r[2]] || 0) + 1;
    byCp[r[3]] = (byCp[r[3]] || 0) + 1;
    bySc[m.scene] = (bySc[m.scene] || 0) + 1;
    (h.info.tails || []).forEach((t) => { if (t) { byTl[t] = (byTl[t] || 0) + 1; } });
    const z = m.ze_ratio;
    bucket[z < 25 ? '0–25%' : z < 40 ? '25–40%' : z < 50 ? '40–50%' : z < 65 ? '50–65%' : '65–100%']++;
  });
  const top = (o) => Object.keys(o).map((k) => [k, o[k]])
      .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1)).slice(0, 12);
  return { author: top(byAu), cipai: top(byCp), tail: top(byTl), ratio: bucket, scene: top(bySc) };
}

function cmpFor(sort) {
  const G = (a) => a.info.metrics;
  const cmp = {
    ze_desc: (a, b) => G(b).ze_ratio - G(a).ze_ratio,
    ze_asc: (a, b) => G(a).ze_ratio - G(b).ze_ratio,
    len_desc: (a, b) => G(b).han_len - G(a).han_len,
    len_asc: (a, b) => G(a).han_len - G(b).han_len,
    sent_desc: (a, b) => G(b).sent_n - G(a).sent_n,
    sent_asc: (a, b) => G(a).sent_n - G(b).sent_n,
    long_desc: (a, b) => G(b).longest_len - G(a).longest_len,
    long_asc: (a, b) => G(a).longest_len - G(b).longest_len,
    change_desc: (a, b) => G(b).change - G(a).change,
    change_asc: (a, b) => G(a).change - G(b).change
  };
  return cmp[sort] || null;
}

function searchOffline(rows, cond) {
  const t0 = Date.now();
  const hits = [];
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    if (!textHit(row, cond.q)) { continue; }
    const inf = info(row, i);
    if (!matchCond(inf, cond, row)) { continue; }
    hits.push({ row: row, info: inf });
  }
  const cmp = cmpFor(cond.sort);
  /* 与在线一致：web/serve.py 的 SORTS 每个排序都是 `metric DESC/ASC, p.pid`，
     即指标并列时按 pid 升序兜底。这里补上同一条 tie-break（pid 是文本主键，
     SQL 的 ORDER BY p.pid 走字典序，故用 < /> 字符串比较，语义完全对齐）。 */
  if (cmp) {
    hits.sort((a, b) => cmp(a, b)
      || (a.row[0] < b.row[0] ? -1 : a.row[0] > b.row[0] ? 1 : 0));
  }
  return { total: hits.length, hits: hits, facets: facets(hits), ms: Date.now() - t0 };
}

/* 逐字解析面板（纯函数，返回 HTML 字符串；node 可直接断言） */
function detailHtml(row, inf, cond) {
  const m = inf.metrics, L = inf.lines, c = cond || {};
  const re = pzTest(c.pz);
  const tails = c.tail ? String(c.tail).replace(/[\s，,、;；]+/g, '').split('') : [];
  let h = '<h2>' + U.esc(row[2]) + '《' + U.esc(row[4]) + '》'
    + '<span class="dim">（' + U.esc(row[3]) + ' · ' + U.esc(row[0]) + '）</span></h2>';
  h += '<p>全篇 ' + m.sent_n + ' 句 / ' + m.han_len + ' 字：平 ' + m.ping + '、仄 ' + m.ze
    + '，仄声比例 ' + m.ze_ratio + '%；前段 ' + m.f_ratio + '% → 后段 ' + m.b_ratio
    + '%（变化 ' + m.change + '），声情 ' + m.scene + '；最长句第 ' + m.longest_seq.join('、')
    + ' 句；阈值 ' + m.threshold + '</p>';
  h += '<table><tr><th>句</th><th>原文</th><th>逐字平仄</th><th>平/仄</th><th>句脚</th></tr>';
  L.forEach((L1, i) => {
    const hitTail = tails.length && tails.indexOf(L1.tail) >= 0;
    const hitPz = re ? re.test(L1.pz) : false;
    let cs = '', k = 0;
    for (let j = 0; j < L1.text.length; j++) {
      const ch = L1.text[j];
      if (HAN.test(ch)) {
        /* ⭐ 2026-10-10：给每个**汉字**带上坐标（句序 / 字位）——
           解析页据此支持「点字 → 读音候选 + 人工选读」（字位 = 该句第几个汉字，0 起）。
           坐标与后端 `/api/pronounce/candidates` 的 line/pos 口径一致（跳过标点）。 */
        cs += '<span class="' + (L1.pz[k] === '仄' ? 'ze' : 'ping')
          + '" data-li="' + i + '" data-pos="' + k + '">' + U.esc(ch) + '</span>';
        k++;
      } else { cs += U.esc(ch); }
    }
    h += '<tr class="' + ((hitTail || hitPz) ? 'hit' : '') + '"><td>' + (i + 1)
      + (hitTail ? ' ✳' : (hitPz ? ' 〜' : '')) + '</td><td>' + cs
      + '</td><td>' + L1.pz + '</td><td>' + M.count(L1.pz, '平') + '/' + M.count(L1.pz, '仄')
      + '</td><td>' + U.esc(L1.tail) + (hitTail ? ' ✳' : '') + '</td></tr>';
  });
  return h + '</table>';
}

function highlight(text, q) {
  const t = U.esc(text);
  if (!q) { return t; }
  const e = U.esc(q).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return t.replace(new RegExp(e, 'g'), (s) => '<mark>' + s + '</mark>');
}

function listRow(item, no, cond) {
  const r = item.row, m = item.info.metrics;
  return '<tr><td class="dim">' + no + '</td><td>' + highlight(r[2], cond.q) + '</td><td>'
    + highlight(r[4], cond.q) + '</td><td class="dim">' + highlight(r[3], cond.q) + '</td><td>'
    + m.sent_n + '</td><td>' + m.han_len + '</td><td>' + m.ze_ratio + '%</td><td class="dim">'
    + m.scene + '</td><td><button class="ghost" data-pid="' + U.attr(r[0]) + '">逐字解析</button></td></tr>';
}

function condText(cond) {
  const p = [];
  /* 显式判空：与 matchCond 同一口径，值为 0 也要如实回显（旧版用 `|| 0` 会把 0 当空）。 */
  const has = (v) => v !== undefined && v !== null && v !== '';
  if (cond.dynasty) { p.push('朝代=' + cond.dynasty); }
  if (cond.q) { p.push('关键词=' + cond.q); }
  if (cond.author) { p.push('词人=' + cond.author); }
  if (cond.cipai) { p.push('词牌=' + cond.cipai); }
  if (cond.tail) { p.push('句脚字∈' + cond.tail); }
  if (cond.tailPz) { p.push('句脚平仄=' + cond.tailPz); }
  if (cond.pz) { p.push('声律模式=' + cond.pz + (pzTest(cond.pz) ? '' : '（含非法字符）')); }
  if (has(cond.minLen) || has(cond.maxLen)) {
    p.push('字数∈[' + (has(cond.minLen) ? cond.minLen : 0) + ',' + (has(cond.maxLen) ? cond.maxLen : '∞') + ']');
  }
  if (has(cond.minSent) || has(cond.maxSent)) {
    p.push('句数∈[' + (has(cond.minSent) ? cond.minSent : 0) + ',' + (has(cond.maxSent) ? cond.maxSent : '∞') + ']');
  }
  if (cond.minZe !== '' && cond.minZe !== undefined) { p.push('仄比≥' + cond.minZe + '%'); }
  if (cond.maxZe !== '' && cond.maxZe !== undefined) { p.push('仄比≤' + cond.maxZe + '%'); }
  if (has(cond.minLong)) { p.push('最长句≥' + cond.minLong + ' 字'); }
  if (cond.changeMin !== '' && cond.changeMin !== undefined) { p.push('变化值≥' + cond.changeMin); }
  if (cond.changeMax !== '' && cond.changeMax !== undefined) { p.push('变化值≤' + cond.changeMax); }
  if (cond.thrMin !== '' && cond.thrMin !== undefined) { p.push('阈值≥' + cond.thrMin); }
  if (cond.thrMax !== '' && cond.thrMax !== undefined) { p.push('阈值≤' + cond.thrMax); }
  if (cond.scene) { p.push('声情=' + cond.scene); }
  return p.length ? p.join('　') : '（无条件：全库）';
}

/* 表格分页：**在线模式服务端已经分好页**（再切一刀会把第二页切成空表——实测 bug）。
   所以这里把「是否已分页」当显式参数，而不是靠调用方记得。*/
function pageSlice(res, page, size, alreadyPaged) {
  const total = res.total || 0;
  const pages = Math.max(1, Math.ceil(total / size));
  if (page > pages) { page = pages; }
  if (page < 1) { page = 1; }
  const hits = alreadyPaged ? (res.hits || [])
    : (res.hits || []).slice((page - 1) * size, page * size);
  return { page: page, pages: pages, hits: hits, total: total };
}

/* 供测试与「行对象」构造用：把 (rows, i) 全量算成 hits（离线检索入口） */
function allHits() { return ROWS || []; }

const _internals = {
  get TMAP() { return TMAP; },
  get ROWS() { return ROWS; },
  get LIVE() { return LIVE; },
  get CACHE() { return CACHE; },
  reset: function () { TMAP = {}; ROWS = null; LIVE = null; CACHE = []; }
};

return { setData: setData, setLive: setLive, isLive: isLive, analyze: analyze, info: info,
         splitSents: splitSents, pzOf: pzOf, tailOf: tailOf, matchCond: matchCond,
         pzTest: pzTest, PZ_OK: PZ_OK, searchOffline: searchOffline, detailHtml: detailHtml, listRow: listRow,
         facets: facets, condText: condText, highlight: highlight, pageSlice: pageSlice,
         textHit: textHit, resetCache: resetCache, allHits: allHits, _internals: _internals };
}));

