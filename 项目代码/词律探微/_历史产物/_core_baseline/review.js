/* core/review.js —— 「校订队列」的**纯逻辑层**（零 DOM；Vue 组件与 node 门禁共用）。
 *
 * 数据由 build_views.py 用 Python 的 csv 模块解析后以 JSON 内嵌（**不再用 split(',')**：
 * 字段里只要出现一个半角逗号，整张表就会错位——这是本轮自检抓到的一类真 bug）。
 *
 * ⚠ 架构说明（D15）：本文件是**唯一真源**；`web/app_review.js` 只是 `require` 本文件的薄转发。
 *
 * 对外：COLS / stats(rows) / filter(rows, kw) / sortRows(rows, key, dir) / rowHtml(r)
 */
(function (root, factory) {
  var api = factory(root.UI);
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  if (root) { root.ReviewApp = api; }
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this),
  function (U) {
  'use strict';

const COLS = ['pid', '阕', '句内位', '字', '引擎调', '引擎平仄', '语料调', '语料平仄', '证据', '状态'];

function stats(rows) {
  const byChar = {}, byStatus = {};
  rows.forEach((r) => {
    byChar[r['字']] = (byChar[r['字']] || 0) + 1;
    byStatus[r['状态']] = (byStatus[r['状态']] || 0) + 1;
  });
  const top = Object.keys(byChar).map((k) => [k, byChar[k]])
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
  return { total: rows.length, chars: Object.keys(byChar).length, top: top };
}

function filter(rows, kw) {
  if (!kw) { return rows.slice(); }
  const k = kw.trim();
  return rows.filter((r) =>
    COLS.some((c) => String(r[c] === undefined ? '' : r[c]).indexOf(k) >= 0));
}

function sortRows(rows, key, dir) {
  const s = rows.slice();
  s.sort((a, b) => {
    const x = a[key], y = b[key];
    const nx = parseFloat(x), ny = parseFloat(y);
    const both = isFinite(nx) && isFinite(ny) && String(x).trim() !== '' && String(y).trim() !== '';
    const d = both ? (nx - ny) : (String(x) < String(y) ? -1 : (String(x) > String(y) ? 1 : 0));
    return dir === 'desc' ? -d : d;
  });
  return s;
}

/* 行 → HTML 串（校订表格单元上色；旧实现的字符串格式保留，供离线渲染复用） */
function rowHtml(r) {
  const cells = COLS.map((c) => {
    const v = r[c] === undefined ? '' : r[c];
    if (c === '引擎平仄') { return '<td class="ping">' + U.esc(v) + '</td>'; }
    if (c === '语料平仄') { return '<td class="ze">' + U.esc(v) + '</td>'; }
    if (c === '字') { return '<td><b>' + U.esc(v) + '</b></td>'; }
    if (c === '证据') { return '<td class="dim">' + U.esc(v) + '</td>'; }
    return '<td>' + U.esc(v) + '</td>';
  }).join('');
  return '<tr>' + cells + '</tr>';
}

return { COLS: COLS, stats: stats, filter: filter, sortRows: sortRows, rowHtml: rowHtml };
}));
