/* app_review.js —— 「校订队列」页面的应用层（唯一实现）。
 *
 * 数据由 build_views.py 用 Python 的 csv 模块解析后以 JSON 内嵌（**不再用 split(',')**：
 * 字段里只要出现一个半角逗号，整张表就会错位——这是本轮自检抓到的一类真 bug）。
 *
 * 对外：window.ReviewApp = { stats(rows), filter(rows, kw), sortRows(rows, key, dir), mount(rows) }
 */
(function (root) {
  'use strict';
  var U = root.UI;
  var COLS = ['pid', '阕', '句内位', '字', '引擎调', '引擎平仄', '语料调', '语料平仄', '证据', '状态'];

  function stats(rows) {
    var byChar = {}, byStatus = {};
    rows.forEach(function (r) {
      byChar[r['字']] = (byChar[r['字']] || 0) + 1;
      byStatus[r['状态']] = (byStatus[r['状态']] || 0) + 1;
    });
    var top = Object.keys(byChar).map(function (k) { return [k, byChar[k]]; })
      .sort(function (a, b) { return b[1] - a[1] || (a[0] < b[0] ? -1 : 1); });
    return { total: rows.length, chars: Object.keys(byChar).length, top: top };
  }

  function filter(rows, kw) {
    if (!kw) { return rows.slice(); }
    var k = kw.trim();
    return rows.filter(function (r) {
      return COLS.some(function (c) { return String(r[c] === undefined ? '' : r[c]).indexOf(k) >= 0; });
    });
  }

  function sortRows(rows, key, dir) {
    var s = rows.slice();
    s.sort(function (a, b) {
      var x = a[key], y = b[key];
      var nx = parseFloat(x), ny = parseFloat(y);
      var both = isFinite(nx) && isFinite(ny) && String(x).trim() !== '' && String(y).trim() !== '';
      var d = both ? (nx - ny) : (String(x) < String(y) ? -1 : (String(x) > String(y) ? 1 : 0));
      return dir === 'desc' ? -d : d;
    });
    return s;
  }

  function rowHtml(r) {
    var cells = COLS.map(function (c) {
      var v = r[c] === undefined ? '' : r[c];
      if (c === '引擎平仄') { return '<td class="ping">' + U.esc(v) + '</td>'; }
      if (c === '语料平仄') { return '<td class="ze">' + U.esc(v) + '</td>'; }
      if (c === '字') { return '<td><b>' + U.esc(v) + '</b></td>'; }
      if (c === '证据') { return '<td class="dim">' + U.esc(v) + '</td>'; }
      return '<td>' + U.esc(v) + '</td>';
    }).join('');
    return '<tr>' + cells + '</tr>';
  }

  function mount(rows, opts) {
    opts = opts || {};
    U.inject();
    var $ = function (id) { return document.getElementById(id); };
    var st = stats(rows), cur = rows.slice(), key = 'pid', dir = 'asc', page = 1, SIZE = 100;
    function paint() {
      var pages = Math.max(1, Math.ceil(cur.length / SIZE));
      if (page > pages) { page = pages; }
      var slice = cur.slice((page - 1) * SIZE, page * SIZE);
      $('meta').innerHTML = '工单 <b>' + cur.length + '</b> 条（总 ' + st.total + ' 条）· 第 ' + page + ' / ' + pages
        + ' 页　<span class="dim">点表头可排序；筛选支持任意字段，如填「长」只看该字</span>';
      $('rows').innerHTML = slice.map(rowHtml).join('');
      $('pager').innerHTML = pages > 1
        ? ('<button class="ghost" data-go="' + (page - 1) + '">上一页</button> <span class="dim">第 ' + page + '/' + pages
           + '</span> <button class="ghost" data-go="' + (page + 1) + '">下一页</button>') : '';
      if ($('chips')) {
        $('chips').innerHTML = st.top.slice(0, 14).map(function (kv) {
          return '<span class="chip" data-kw="' + U.attr(kv[0]) + '">' + U.esc(kv[0])
            + ' <span class="dim">' + kv[1] + '</span></span>';
        }).join('');
      }
    }
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (t && t.tagName === 'TH' && t.getAttribute('data-key')) {
        var k = t.getAttribute('data-key');
        dir = (k === key && dir === 'asc') ? 'desc' : 'asc';
        key = k; cur = sortRows(cur, key, dir); paint(); return;
      }
      if (t && t.getAttribute && t.getAttribute('data-go')) {
        page = parseInt(t.getAttribute('data-go'), 10) || 1; paint(); return;
      }
      if (t && t.getAttribute && t.getAttribute('data-kw')) {
        if ($('kw')) { $('kw').value = t.getAttribute('data-kw'); cur = filter(rows, $('kw').value); page = 1; paint(); }
      }
    });
    if ($('go')) { $('go').onclick = function () { cur = filter(rows, $('kw') ? $('kw').value : ''); page = 1; paint(); }; }
    if ($('kw')) { $('kw').onkeydown = function (e) { if (e.key === 'Enter' && $('go')) { $('go').onclick(); } }; }
    if ($('csv')) {
      $('csv').onclick = function () {
        var out = [COLS];
        cur.forEach(function (r) { out.push(COLS.map(function (c) {
          var v = r[c];
          return (v && typeof v === 'object') ? JSON.stringify(v) : v; })); });
        U.download('词律探微_校订工单.csv', U.csvText(out));
        U.toast('已导出 ' + cur.length + ' 条');
      };
    }
    var q = U.query();
    if (q.kw && $('kw')) { $('kw').value = q.kw; cur = filter(rows, q.kw); }
    paint();
    return { paint: paint, cur: function () { return cur; }, stats: st };
  }

  var api = { COLS: COLS, stats: stats, filter: filter, sortRows: sortRows, mount: mount };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  root.ReviewApp = api;
}(typeof window !== 'undefined' ? window : this));
