/* app_parse.js —— 「逐字解析 + 多条件检索」页面的应用层（唯一实现）。
 *
 * 两种运行方式，**同一份代码**：
 *   · 离线（data/parse.html）：数据内嵌在页面里（window.EMBED_ROWS），全部在浏览器本地算；
 *   · 在线（本服务 /browse.html）：条件发给 /api/search，由 SQLite 查（行级条件用 lines 表）。
 * 数字口径一律走 Metrics.compute()（与 Python 引擎同一套，见 web/verify_views.js）。
 *
 * 对外接口（window.ParseApp）——**纯函数部分不碰 DOM，可被 node 直接测**：
 *   setData(pack) / setLive(base) / analyze(text) / info(row) / matchCond(info, cond)
 *   searchOffline(rows, cond) / detailHtml(row, info, cond) / resultRows(...) / csvOf(...)
 *   mount(opts)  ← 只有它碰 DOM
 */
(function (root) {
  'use strict';
  var M = root.Metrics;
  var U = root.UI;
  var HAN = M.HAN;
  var TMAP = {};
  var ROWS = null;
  var LIVE = null;                 // {base:'/api'} 时走在线搜索
  var CACHE = [];

  function splitSents(t) {
    /* 与 solve/prosody.py 的 Engine.split **逐字对齐**（重要，实测踩过）：
     *   ① 先去掉换行；② 在句末标点【之后】切（标点留在前句，引文才能原样回定位）；
     *   ③ 丢掉「没有汉字」的碎片（如单独一个标点／空白）——旧版漏了③，
     *      遇到含此类碎片的篇目，前端句数会比引擎多 1，前后段比例跟着全错。
     * 这一条是「全库对照」门禁（verify_views.js --all）抓出来的，抽样门禁没抓到。 */
    var raw = String(t || '').replace(/\n/g, '');
    var out = [], cur = '';
    for (var i = 0; i < raw.length; i++) {
      var c = raw[i];
      cur += c;
      if ('。？！'.indexOf(c) >= 0) { if (M.hanOnly(cur).length) { out.push(cur.trim()); } cur = ''; }
    }
    if (cur && M.hanOnly(cur).length) { out.push(cur.trim()); }
    return out;
  }
  function pzOf(s) {
    var o = '';
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (HAN.test(c)) { o += (TMAP[c] === '2') ? '仄' : '平'; }
    }
    return o;
  }
  function tailOf(s) {                       // 句脚字 = 该句最后一个**汉字**
    for (var i = s.length - 1; i >= 0; i--) { if (HAN.test(s[i])) { return s[i]; } }
    return '';
  }
  function analyze(text) {
    var sents = splitSents(text || '');
    var lines = sents.map(function (s) { return { text: s, pz: pzOf(s), tail: tailOf(s) }; });
    return { sents: sents, lines: lines, metrics: M.compute(lines) };
  }

  function setData(pack) {
    ROWS = pack.rows;
    TMAP = {};
    var ch = pack.tonemap[0], tn = pack.tonemap[1];
    for (var i = 0; i < ch.length; i++) { TMAP[ch[i]] = tn[i]; }
    CACHE = [];
    return ROWS.length;
  }
  function setLive(base) { LIVE = { base: base || '' }; }
  function isLive() { return !!LIVE; }

  /* 行 → 全部指标（离线自算，缓存；与库中字段同口径） */
  function info(row, i) {
    if (i === undefined) { i = ROWS ? ROWS.indexOf(row) : -1; }
    if (i >= 0 && CACHE[i]) { return CACHE[i]; }
    var a = analyze(row[5]);
    var o = { lines: a.lines, metrics: a.metrics, tails: a.lines.map(function (L) { return L.tail; }),
              pzAll: a.lines.map(function (L) { return L.pz; }) };
    if (i >= 0) { CACHE[i] = o; }
    return o;
  }

  function pzTest(pat) {                     // 平仄模式：? = 任意一字
    if (!pat) { return null; }
    var body = '';
    for (var i = 0; i < pat.length; i++) {
      var c = pat[i];
      body += (c === '平' || c === '仄') ? c : '.';
    }
    return new RegExp(body);
  }

  /* 条件是否命中（离线与在线**同一张判定表**；在线由 SQL 负责等价实现） */
  function matchCond(inf, cond, row) {
    var m = inf.metrics;
    var c = cond || {};
    if (row) {
      if (c.dynasty && String(row[1]) !== c.dynasty) { return false; }
      if (c.author && String(row[2]).indexOf(c.author) < 0) { return false; }
      if (c.cipai && String(row[3]).indexOf(c.cipai) < 0) { return false; }
    }
    if (c.minLen && m.han_len < c.minLen) { return false; }
    if (c.maxLen && m.han_len > c.maxLen) { return false; }
    if (c.minSent && m.sent_n < c.minSent) { return false; }
    if (c.maxSent && m.sent_n > c.maxSent) { return false; }
    if (c.minZe !== undefined && c.minZe !== '' && m.ze_ratio < Number(c.minZe)) { return false; }
    if (c.maxZe !== undefined && c.maxZe !== '' && m.ze_ratio > Number(c.maxZe)) { return false; }
    if (c.minLong && m.longest_len < c.minLong) { return false; }
    if (c.changeMin !== undefined && c.changeMin !== '' && m.change < Number(c.changeMin)) { return false; }
    if (c.changeMax !== undefined && c.changeMax !== '' && m.change > Number(c.changeMax)) { return false; }
    if (c.thrMin !== undefined && c.thrMin !== '' && m.threshold < Number(c.thrMin)) { return false; }
    if (c.thrMax !== undefined && c.thrMax !== '' && m.threshold > Number(c.thrMax)) { return false; }
    if (c.scene && m.scene !== c.scene) { return false; }
    if (c.tailPz) {                       // 句脚平仄 = 该句平仄串的最后一个字（与引擎同一口径）
      var pzOk = false;
      for (var q = 0; q < inf.pzAll.length; q++) {
        var p1 = inf.pzAll[q];
        if (p1 && p1.charAt(p1.length - 1) === c.tailPz) { pzOk = true; break; }
      }
      if (!pzOk) { return false; }
    }
    if (c.tail) {
      var want = String(c.tail).replace(/[\s，,、;；]+/g, '').split('');
      var ok = false;
      for (var i = 0; i < want.length; i++) {
        for (var j = 0; j < inf.tails.length; j++) {
          if (inf.tails[j] && inf.tails[j] === want[i]) { ok = true; break; }
        }
        if (ok) { break; }
      }
      if (!ok) { return false; }
    }
    if (c.pz) {
      var re = pzTest(c.pz);
      var hit = false;
      for (var k = 0; k < inf.pzAll.length; k++) { if (re.test(inf.pzAll[k])) { hit = true; break; } }
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
    var byAu = {}, byCp = {}, byTl = {}, bucket = { '0–25%': 0, '25–40%': 0, '40–50%': 0, '50–65%': 0, '65–100%': 0 }, bySc = {};
    hits.forEach(function (h) {
      var r = h.row, m = h.info.metrics;
      byAu[r[2]] = (byAu[r[2]] || 0) + 1;
      byCp[r[3]] = (byCp[r[3]] || 0) + 1;
      bySc[m.scene] = (bySc[m.scene] || 0) + 1;
      (h.info.tails || []).forEach(function (t) { if (t) { byTl[t] = (byTl[t] || 0) + 1; } });
      var z = m.ze_ratio;
      bucket[z < 25 ? '0–25%' : z < 40 ? '25–40%' : z < 50 ? '40–50%' : z < 65 ? '50–65%' : '65–100%']++;
    });
    var top = function (o) {
      return Object.keys(o).map(function (k) { return [k, o[k]]; })
        .sort(function (a, b) { return b[1] - a[1] || (a[0] < b[0] ? -1 : 1); }).slice(0, 12);
    };
    return { author: top(byAu), cipai: top(byCp), tail: top(byTl), ratio: bucket, scene: top(bySc) };
  }

  function cmpFor(sort) {
    var M = function (a) { return a.info.metrics; };
    var cmp = {
      ze_desc: function (a, b) { return M(b).ze_ratio - M(a).ze_ratio; },
      ze_asc: function (a, b) { return M(a).ze_ratio - M(b).ze_ratio; },
      len_desc: function (a, b) { return M(b).han_len - M(a).han_len; },
      len_asc: function (a, b) { return M(a).han_len - M(b).han_len; },
      sent_desc: function (a, b) { return M(b).sent_n - M(a).sent_n; },
      sent_asc: function (a, b) { return M(a).sent_n - M(b).sent_n; },
      long_desc: function (a, b) { return M(b).longest_len - M(a).longest_len; },
      long_asc: function (a, b) { return M(a).longest_len - M(b).longest_len; },
      change_desc: function (a, b) { return M(b).change - M(a).change; },
      change_asc: function (a, b) { return M(a).change - M(b).change; }
    };
    return cmp[sort] || null;
  }

  function searchOffline(rows, cond) {
    var t0 = Date.now();
    var hits = [];
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      if (!textHit(row, cond.q)) { continue; }
      var inf = info(row, i);
      if (!matchCond(inf, cond, row)) { continue; }
      hits.push({ row: row, info: inf });
    }
    var cmp = cmpFor(cond.sort);
    if (cmp) { hits.sort(cmp); }
    return { total: hits.length, hits: hits, facets: facets(hits), ms: Date.now() - t0 };
  }

  /* 逐字解析面板（纯函数，返回 HTML 字符串；node 可直接断言） */
  function detailHtml(row, inf, cond) {
    var m = inf.metrics, L = inf.lines, c = cond || {};
    var re = pzTest(c.pz);
    var tails = c.tail ? String(c.tail).replace(/[\s，,、;；]+/g, '').split('') : [];
    var h = '<h2>' + U.esc(row[2]) + '《' + U.esc(row[4]) + '》'
      + '<span class="dim">（' + U.esc(row[3]) + ' · ' + U.esc(row[0]) + '）</span></h2>';
    h += '<p>全篇 ' + m.sent_n + ' 句 / ' + m.han_len + ' 字：平 ' + m.ping + '、仄 ' + m.ze
      + '，仄声比例 ' + m.ze_ratio + '%；前段 ' + m.f_ratio + '% → 后段 ' + m.b_ratio
      + '%（变化 ' + m.change + '），声情 ' + m.scene + '；最长句第 ' + m.longest_seq.join('、')
      + ' 句；阈值 ' + m.threshold + '</p>';
    h += '<table><tr><th>句</th><th>原文</th><th>逐字平仄</th><th>平/仄</th><th>句脚</th></tr>';
    L.forEach(function (L1, i) {
      var hitTail = tails.length && tails.indexOf(L1.tail) >= 0;
      var hitPz = re ? re.test(L1.pz) : false;
      var cs = '', k = 0;
      for (var j = 0; j < L1.text.length; j++) {
        var ch = L1.text[j];
        if (HAN.test(ch)) {
          cs += '<span class="' + (L1.pz[k] === '仄' ? 'ze' : 'ping') + '">' + U.esc(ch) + '</span>';
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
    var t = U.esc(text);
    if (!q) { return t; }
    var e = U.esc(q).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return t.replace(new RegExp(e, 'g'), function (s) { return '<mark>' + s + '</mark>'; });
  }

  function listRow(item, no, cond) {
    var r = item.row, m = item.info.metrics;
    return '<tr><td class="dim">' + no + '</td><td>' + highlight(r[2], cond.q) + '</td><td>'
      + highlight(r[4], cond.q) + '</td><td class="dim">' + highlight(r[3], cond.q) + '</td><td>'
      + m.sent_n + '</td><td>' + m.han_len + '</td><td>' + m.ze_ratio + '%</td><td class="dim">'
      + m.scene + '</td><td><button class="ghost" data-pid="' + U.attr(r[0]) + '">逐字解析</button></td></tr>';
  }

  function condText(cond) {
    var p = [];
    if (cond.dynasty) { p.push('朝代=' + cond.dynasty); }
    if (cond.q) { p.push('关键词=' + cond.q); }
    if (cond.author) { p.push('词人=' + cond.author); }
    if (cond.cipai) { p.push('词牌=' + cond.cipai); }
    if (cond.tail) { p.push('句脚字∈' + cond.tail); }
    if (cond.tailPz) { p.push('句脚平仄=' + cond.tailPz); }
    if (cond.pz) { p.push('声律模式=' + cond.pz); }
    if (cond.minLen || cond.maxLen) { p.push('字数∈[' + (cond.minLen || 0) + ',' + (cond.maxLen || '∞') + ']'); }
    if (cond.minSent || cond.maxSent) { p.push('句数∈[' + (cond.minSent || 0) + ',' + (cond.maxSent || '∞') + ']'); }
    if (cond.minZe !== '' && cond.minZe !== undefined) { p.push('仄比≥' + cond.minZe + '%'); }
    if (cond.maxZe !== '' && cond.maxZe !== undefined) { p.push('仄比≤' + cond.maxZe + '%'); }
    if (cond.minLong) { p.push('最长句≥' + cond.minLong + ' 字'); }
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
    var total = res.total || 0;
    var pages = Math.max(1, Math.ceil(total / size));
    if (page > pages) { page = pages; }
    if (page < 1) { page = 1; }
    var hits = alreadyPaged ? (res.hits || [])
      : (res.hits || []).slice((page - 1) * size, page * size);
    return { page: page, pages: pages, hits: hits, total: total };
  }

  var LAST = [], LASTCOND = {};

  function mount(opts) {
    opts = opts || {};
    U.inject();
    var $ = function (id) { return document.getElementById(id); };
    var PAGE = 1, SIZE = 50;

    function readCond() {
      var v = function (id) { var e = $(id); return e ? e.value.trim() : ''; };
      var n = function (id) { var s = v(id); return s === '' ? '' : Number(s); };
      return { dynasty: v('dynasty') || '清', q: v('q'), author: v('author'), cipai: v('cipai'),
               tail: v('tail'), tailPz: v('tailPz'), pz: v('pz'),
               minLen: n('minLen'), maxLen: n('maxLen'), minSent: n('minSent'), maxSent: n('maxSent'),
               minZe: n('minZe'), maxZe: n('maxZe'), minLong: n('minLong'),
               changeMin: n('changeMin'), changeMax: n('changeMax'),
               thrMin: n('thrMin'), thrMax: n('thrMax'),
               scene: v('scene'), sort: v('sort') };
    }

    function paint(res, cond, alreadyPaged) {
      LAST = res.hits; LASTCOND = cond;
      var pg = pageSlice(res, PAGE, SIZE, !!alreadyPaged);
      PAGE = pg.page;
      var slice = pg.hits, total = pg.total, pages = pg.pages;
      $('meta').innerHTML = '命中 <b>' + total + '</b> 篇 · 本页显示 ' + slice.length + ' 篇 · 第 '
        + PAGE + ' / ' + pages + ' 页 · 用时 ' + res.ms + ' ms'
        + '<br><span class="dim">条件：' + U.esc(condText(cond)) + '</span>';
      $('rows').innerHTML = slice.map(function (it, i) { return listRow(it, (PAGE - 1) * SIZE + i + 1, cond); }).join('');
      $('pager').innerHTML = pages > 1
        ? ('<button class="ghost" data-go="1">首页</button> <button class="ghost" data-go="' + (PAGE - 1)
           + '">上一页</button> <span class="dim">第 ' + PAGE + ' / ' + pages + ' 页</span> <button class="ghost" data-go="'
           + (PAGE + 1) + '">下一页</button> <button class="ghost" data-go="' + pages + '">末页</button>') : '';
      var f = res.facets;
      if (f && $('facets')) {
        /* 分面→条件：每个分面都有**自己的**字段（旧版词人/词牌都往「关键词」里塞，
           于是分面标签看着像「标签」，点下去却变成了全文关键词、结果对不上）。 */
        var chip = function (arr, field) {
          return (arr || []).map(function (kv) {
            return '<span class="chip" data-set="' + field + '" data-val="' + U.attr(kv[0]) + '">'
              + U.esc(kv[0]) + ' <span class="dim">' + kv[1] + '</span></span>';
          }).join('');
        };
        var buckets = { '0–25%': [0, 25], '25–40%': [25, 40], '40–50%': [40, 50],
                        '50–65%': [50, 65], '65–100%': [65, 100] };
        var ratio = Object.keys(f.ratio || {}).map(function (k) {
          var b = buckets[k] || [0, 100];
          return '<span class="chip" data-set2="minZe" data-val2="' + b[0]
            + '" data-set3="maxZe" data-val3="' + b[1] + '">' + U.esc(k)
            + ' <span class="dim">' + f.ratio[k] + '</span></span>';
        }).join('');
        $('facets').innerHTML = '<div class="grid"><div><h3>词人 TOP</h3>' + chip(f.author, 'author')
          + '</div><div><h3>词牌 TOP</h3>' + chip(f.cipai, 'cipai')
          + '</div><div><h3>句脚字 TOP</h3>' + chip(f.tail, 'tail')
          + '</div><div><h3>仄声比例分布（点区间即筛）</h3>' + ratio
          + '<h3 style="margin-top:8px">声情转向</h3>' + chip(f.scene, 'scene') + '</div></div>';
      }
      var dl = $('csv');
      if (dl) { dl.onclick = function () { exportCsv(); }; }
    }

    function run(page) {
      PAGE = page || 1;
      var cond = readCond();
      if (isLive()) {
        $('meta').innerHTML = U.spinner('正在向本地引擎检索…');
        var qs = Object.keys(cond).map(function (k) {
          return (cond[k] === '' || cond[k] === null || cond[k] === undefined) ? null
            : (encodeURIComponent(k) + '=' + encodeURIComponent(cond[k]));
        }).filter(Boolean).join('&');
        fetch(LIVE.base + '/api/search?' + qs + '&page=' + PAGE + '&size=' + SIZE)
          .then(function (r) { return r.json(); })
          .then(function (j) {
            if (j.error) { $('meta').innerHTML = '<span class="bad">出错：' + U.esc(j.error) + '</span>'; return; }
            // 在线：行内数字来自库，直接摆；详情面板用 /api/parse 取逐字
            var hits = (j.rows || []).map(function (r) {
              return { row: [r.pid, r.dynasty, r.author, r.cipai, r.title, r.raw || ''],
                       info: { metrics: r } };
            });
            // ★ 服务端**已经分好页** → 不能再切一刀（否则第二页永远空）
            paint({ total: j.total, hits: hits, facets: j.facets, ms: j.ms }, cond, true);
            if ($('meta') && j.where) {
              $('meta').insertAdjacentHTML('beforeend', '<br><span class="dim">SQL 条件：'
                + U.esc(j.where) + '；ORDER BY ' + U.esc(j.order_by || '') + '</span>');
            }
          })
          .catch(function (e) { $('meta').innerHTML = '<span class="bad">出错：' + U.esc(e) + '</span>'; });
        return;
      }
      paint(searchOffline(ROWS, cond), cond, false);
    }

    function showDetail(pid) {
      var box = $('detail');
      if (isLive()) {
        box.innerHTML = U.spinner('取逐字解析…');
        fetch(LIVE.base + '/api/parse?pid=' + encodeURIComponent(pid)).then(function (r) { return r.json(); })
          .then(function (j) {
            if (j.error) { box.innerHTML = '<span class="bad">' + U.esc(j.error) + '</span>'; return; }
            var lines = (j.lines || []).map(function (L) { return { text: L.text, pz: L.pz, tail: L.tail }; });
            var row = [j.pid, j.dynasty, j.author, j.cipai, j.title, j.raw || ''];
            // 库里的 longest_seq 是文本（如「1、2」），页面这里要数组，否则 join 会报错
            var jm = {};
            for (var kk in j) { if (Object.prototype.hasOwnProperty.call(j, kk)) { jm[kk] = j[kk]; } }
            jm.longest_seq = String(j.longest_seq === undefined || j.longest_seq === null ? '' : j.longest_seq)
              .split(/[、,，]/).filter(function (x) { return x !== ''; }).map(Number);
            box.innerHTML = detailHtml(row, { lines: lines, metrics: jm,
                                              tails: lines.map(function (L) { return L.tail; }) }, LASTCOND);
          });
        return;
      }
      for (var i = 0; i < ROWS.length; i++) {
        if (ROWS[i][0] === pid) { box.innerHTML = detailHtml(ROWS[i], info(ROWS[i], i), LASTCOND); return; }
      }
      box.innerHTML = '<span class="bad">没有这一篇：' + U.esc(pid) + '</span>';
    }

    function exportCsv() {
      var rows = [['pid', '朝代', '词人', '词牌', '题名', '句数', '字数', '平', '仄', '仄声比例%', '声情', '变化值', '阈值', '原文']];
      LAST.forEach(function (it) {
        var r = it.row, m = it.info.metrics;
        rows.push([r[0], r[1], r[2], r[3], r[4], m.sent_n, m.han_len, m.ping, m.ze, m.ze_ratio, m.scene, m.change, m.threshold, r[5]]);
      });
      if (rows.length === 1) { U.toast('没有可导出的结果'); return; }
      U.download('词律探微_检索结果.csv', U.csvText(rows));
      U.toast('已导出 ' + (rows.length - 1) + ' 行');
    }

    // ---- 事件 ----
    if ($('go')) { $('go').onclick = function () { run(1); }; }
    if ($('reset')) {
      $('reset').onclick = function () {
        ['q', 'author', 'cipai', 'tail', 'tailPz', 'pz', 'minLen', 'maxLen', 'minSent', 'maxSent',
         'minZe', 'maxZe', 'minLong', 'changeMin', 'changeMax', 'thrMin', 'thrMax',
         'scene'].forEach(function (id) {
          if ($(id)) { $(id).value = ''; }
        });
        run(1);
      };
    }
    if ($('q')) { $('q').onkeydown = function (e) { if (e.key === 'Enter') { run(1); } }; }
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (t && t.getAttribute && t.getAttribute('data-go')) {
        var p = parseInt(t.getAttribute('data-go'), 10);
        if (p >= 1) { run(p); window.scrollTo(0, 0); }
        return;
      }
      if (t && t.getAttribute && t.getAttribute('data-pid')) { showDetail(t.getAttribute('data-pid')); return; }
      if (t && t.getAttribute && t.getAttribute('data-set')) {
        var f = t.getAttribute('data-set'), v = t.getAttribute('data-val');
        if ($(f)) { $(f).value = v; }
        var f2 = t.getAttribute('data-set2');
        if (f2 && $(f2)) { $(f2).value = t.getAttribute('data-val2'); }
        var f3 = t.getAttribute('data-set3');
        if (f3 && $(f3)) { $(f3).value = t.getAttribute('data-val3'); }
        run(1);
      }
    });
    if ($('size')) { $('size').onchange = function () { SIZE = parseInt(this.value, 10) || 50; run(1); }; }

    // 深链：?q= / ?pid= / 条件参数
    var q0 = U.query();
    ['dynasty', 'author', 'cipai', 'tail', 'tailPz', 'pz', 'minLen', 'maxLen', 'minSent', 'maxSent',
     'minZe', 'maxZe', 'minLong', 'changeMin', 'changeMax', 'thrMin', 'thrMax',
     'scene'].forEach(function (k) {
      if (q0[k] !== undefined && $(k)) { $(k).value = q0[k]; }
    });
    if (q0['q'] !== undefined && $('q')) { $('q').value = q0['q']; }
    if (q0['size'] && $('size')) { $('size').value = q0['size']; SIZE = parseInt(q0['size'], 10) || SIZE; }
    if (q0['sort'] && $('sort')) { $('sort').value = q0['sort']; }
    if ($('cnt') && ROWS) { $('cnt').textContent = ROWS.length; }
    run(1);
    if (q0.pid) { showDetail(q0.pid); }
    return { run: run, showDetail: showDetail, readCond: readCond, exportCsv: exportCsv };
  }

  var api = { setData: setData, setLive: setLive, isLive: isLive, analyze: analyze, info: info,
              splitSents: splitSents, pzOf: pzOf, tailOf: tailOf, matchCond: matchCond,
              pzTest: pzTest, searchOffline: searchOffline, detailHtml: detailHtml, listRow: listRow,
              facets: facets, condText: condText, highlight: highlight, pageSlice: pageSlice,
              mount: mount };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  root.ParseApp = api;
}(typeof window !== 'undefined' ? window : this));
