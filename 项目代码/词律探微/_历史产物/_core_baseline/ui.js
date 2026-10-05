/* core/ui.js —— 页面外观与通用工具的**唯一实现**（Vue 组件、离线静态视图、本地服务、node 门禁共用）。
 *
 * 为什么要收成单一来源：四个视图 + 服务端问答页此前各写一套 CSS 与工具函数，
 * 「同一个 bug 修一半」的风险极高（实测：markdown 的星号漏进 HTML，三处只改了零处）。
 * 这里只有一份 CSS、一份 esc/hz/fmt，页面只负责摆结构。
 *
 * ⚠ 架构说明（D15）：本文件是**唯一真源**；`web/ui.js` 只是 `require` 本文件的薄转发。
 *
 * 对外接口（window.UI / ES import）：
 *   CSS / inject()            样式表（字符串 + 注入）
 *   esc / attr / hz / badge   转义、上色、徽章
 *   fmtInt / fmt1 / signed    数字格式
 *   csvText / download        导出
 *   toast / spinner           交互反馈
 *   query()                   取 URL 查询参数
 *   footer(stamp, src, n)     页脚「生成时间」探针（区分旧副本 vs 真出错）
 *   theme toggle: mountTheme()
 */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  if (root) { root.UI = api; }
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this),
  function () {
    'use strict';

    var DARK = '--bg:#151917;--panel:#1e2320;--panel2:#232a26;--ink:#e8e6df;--ink2:#a6ada5;'
      + '--line:#333b36;--accent:#7fc0ae;--accent2:#d6b985;--ping:#6fc3e2;--ze:#e9a06a;'
      + '--ok:#7dd39b;--warn:#f08a8a;--shadow:0 1px 2px rgba(0,0,0,.45),0 8px 22px rgba(0,0,0,.4)';

    var CSS = [
      ':root{--bg:#f7f5f0;--panel:#fffdf8;--panel2:#fbf8f1;--ink:#1f211e;--ink2:#5f6459;'
      + '--line:#e3dccb;--accent:#2f6b5f;--accent2:#8a6d3b;--ping:#0b6a8a;--ze:#b4470b;'
      + '--ok:#1c6b3a;--warn:#a33226;--shadow:0 1px 2px rgba(0,0,0,.05),0 8px 22px rgba(0,0,0,.06);'
      + '--r:10px;--mono:"Cascadia Mono","Consolas","Sarasa Mono SC",monospace}',
      '@media (prefers-color-scheme:dark){:root:not([data-theme=light]){' + DARK + '}}',
      'html[data-theme=dark]{' + DARK + '}',
      '*{box-sizing:border-box}',
      'body{margin:0;background:var(--bg);color:var(--ink);'
      + 'font:15px/1.75 "Microsoft YaHei","PingFang SC","Noto Sans SC",system-ui,serif}',
      'a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}',
      'header.top{position:sticky;top:0;z-index:9;background:linear-gradient(180deg,var(--panel),var(--panel2));'
      + 'border-bottom:1px solid var(--line);box-shadow:var(--shadow)}',
      'header.top .in{max-width:1180px;margin:0 auto;padding:10px 18px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}',
      '.brand{font-weight:700;letter-spacing:2px;font-size:17px}',
      '.brand small{font-weight:400;font-size:12px;color:var(--ink2);letter-spacing:0;margin-left:8px}',
      'nav.tabs{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}',
      'nav.tabs a{padding:5px 11px;border-radius:999px;border:1px solid var(--line);background:var(--panel);'
      + 'font-size:13.5px;color:var(--ink)}',
      'nav.tabs a.on{background:var(--accent);border-color:var(--accent);color:#fff}',
      'nav.tabs a:hover{text-decoration:none;border-color:var(--accent)}',
      'main{max-width:1180px;margin:0 auto;padding:18px 18px 60px}',
      'h1{font-size:21px;margin:6px 0 4px}h2{font-size:18px;margin:16px 0 6px}h3{font-size:15.5px;margin:12px 0 4px}',
      '.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);'
      + 'padding:14px 16px;margin:12px 0;box-shadow:var(--shadow)}',
      '.card.tight{padding:10px 12px}',
      '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}',
      '.row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}',
      '.f{display:flex;flex-direction:column;gap:3px;font-size:12.5px;color:var(--ink2)}',
      'input,select,button,textarea{font:inherit}',
      'input[type=text],input[type=number],select{padding:5px 8px;border:1px solid var(--line);'
      + 'border-radius:8px;background:var(--panel);color:var(--ink);min-width:80px}',
      'input:focus,select:focus{outline:2px solid color-mix(in srgb,var(--accent) 45%,transparent)}',
      'button,.btn{background:var(--accent);color:#fff;border:1px solid var(--accent);border-radius:8px;'
      + 'padding:6px 14px;cursor:pointer;transition:.15s}',
      'button:hover,.btn:hover{filter:brightness(1.08)}',
      'button.ghost,.btn.ghost{background:transparent;color:var(--accent)}',
      'button.ghost.on{background:var(--accent);color:#fff}',
      'button:disabled{opacity:.5;cursor:default}',
      'table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0}',
      'th,td{border-bottom:1px solid var(--line);padding:5px 9px;text-align:left;vertical-align:top}',
      'thead th{background:var(--panel2);position:sticky;top:0;z-index:3;font-weight:600;'
      + 'box-shadow:inset 0 -1px 0 var(--line)}',
      'tbody tr:nth-child(2n){background:color-mix(in srgb,var(--panel2) 55%,transparent)}',
      'tbody tr:hover{background:color-mix(in srgb,var(--accent) 10%,transparent)}',
      '.mono{font-family:var(--mono);letter-spacing:.5px}',
      '.ping{color:var(--ping);font-weight:600}.ze{color:var(--ze);font-weight:600}',
      '.dim{color:var(--ink2);font-size:12.5px}',
      '.ok{color:var(--ok);font-weight:600}.bad{color:var(--warn);font-weight:600}',
      '.chip{display:inline-block;margin:3px 6px 0 0;padding:3px 10px;border:1px solid var(--line);'
      + 'border-radius:999px;background:var(--panel);cursor:pointer;font-size:13px}',
      '.chip:hover{border-color:var(--accent)}',
      '.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;'
      + 'border:1px solid var(--line);background:var(--panel2);color:var(--ink2);margin-right:5px}',
      '.badge.acc{border-color:var(--accent);color:var(--accent)}',
      '.badge.warn{border-color:var(--warn);color:var(--warn)}',
      'pre,code,.code{font-family:var(--mono);font-size:12.5px}',
      'pre{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:10px;overflow:auto}',
      'code{background:var(--panel2);border-radius:4px;padding:1px 5px}',
      'tr.hit>td{background:color-mix(in srgb,var(--accent2) 22%,transparent)}',
      'mark{background:color-mix(in srgb,var(--accent2) 45%,transparent);color:inherit;border-radius:3px}',
      '.bar{position:sticky;bottom:0;background:var(--panel);border-top:1px solid var(--line);'
      + 'padding:8px 0;margin-top:10px}',
      '.q{background:var(--panel);border-left:4px solid var(--accent);padding:8px 12px;border-radius:6px;margin:10px 0}',
      '.a{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:11px 13px;margin:8px 0;white-space:pre-wrap}',
      '.m{color:var(--ink2);font-size:12.5px;margin-top:8px;border-top:1px dashed var(--line);padding-top:6px;white-space:normal}',
      '.e{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:7px 0;background:var(--panel2)}',
      'footer.foot{max-width:1180px;margin:26px auto 0;padding:10px 18px 34px;color:var(--ink2);font-size:12.5px;'
      + 'border-top:1px solid var(--line)}',
      '.toast{position:fixed;left:50%;transform:translateX(-50%);bottom:22px;background:var(--ink);color:var(--bg);'
      + 'padding:8px 16px;border-radius:999px;font-size:13.5px;opacity:0;transition:.25s;z-index:99}',
      '.toast.on{opacity:.94}',
      '.spin{display:inline-block;width:13px;height:13px;border:2px solid var(--line);border-top-color:var(--accent);'
      + 'border-radius:50%;animation:sp .7s linear infinite;vertical-align:-2px}',
      '@keyframes sp{to{transform:rotate(360deg)}}',
      '.scroll{overflow:auto;max-height:70vh}',
      '.chart{width:100%;height:auto;display:block}',
      '.chart .nd text{font-size:15px;paint-order:stroke;stroke:var(--panel);stroke-width:3px;'
      + 'stroke-linejoin:round;pointer-events:none}',
      '.chart .nd circle{stroke:var(--panel);stroke-width:2px}',
      '.chart .ed{transition:opacity .1s}',
      '.legend{display:flex;gap:16px;flex-wrap:wrap;align-items:center;font-size:13px;margin:4px 0}',
      '.legend i{display:inline-block;width:13px;height:13px;border-radius:50%;vertical-align:-2px;'
      + 'margin-right:5px}',
      '.legend u{display:inline-block;width:26px;height:3px;background:color-mix(in srgb,var(--accent) 55%,transparent);'
      + 'vertical-align:4px;margin-right:5px}',
      '.tip{position:fixed;z-index:60;background:var(--ink);color:var(--bg);border-radius:6px;'
      + 'padding:4px 9px;font-size:12.5px;pointer-events:none;opacity:0;transition:opacity .12s}',
      '.tip.on{opacity:.95}',
      '.kv{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;font-size:13px}',
      '.kv b{font-weight:600;color:var(--ink2)}',
      '@media print{header.top,nav.tabs,.bar,button{display:none}body{background:#fff}}',
      '@media (max-width:640px){main{padding:12px}thead th{position:static}.grid{grid-template-columns:1fr}}'
    ].join('\n');

    function inject(doc) {
      doc = doc || (typeof document !== 'undefined' ? document : null);
      if (!doc || doc.getElementById('ui-css')) { return; }
      var s = doc.createElement('style');
      s.id = 'ui-css';
      s.textContent = CSS;
      doc.head.appendChild(s);
    }

    function esc(s) {
      return String(s === null || s === undefined ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
    function attr(s) { return esc(s); }

    /* 平仄串 → 上色 HTML（只吃 平/仄 两个字符） */
    function hz(pz) {
      var o = '';
      for (var i = 0; i < (pz || '').length; i++) {
        var c = pz[i];
        o += c === '平' ? '<span class="ping">平</span>'
          : (c === '仄' ? '<span class="ze">仄</span>' : esc(c));
      }
      return o;
    }

    function badge(text, cls) { return '<span class="badge' + (cls ? ' ' + cls : '') + '">' + esc(text) + '</span>'; }

    function fmtInt(n) { return (n === null || n === undefined || n === '') ? '—' : String(n); }
    function fmt1(x) {
      if (x === null || x === undefined || x === '') { return '—'; }
      var v = Number(x);
      return isFinite(v) ? (Math.round(v * 10) / 10).toFixed(1) : '—';
    }
    function signed(x) { var v = Number(x); return (v > 0 ? '+' : '') + fmt1(v); }

    function csvText(rows) {
      return rows.map(function (r) {
        return r.map(function (c) {
          var s = (c === null || c === undefined) ? '' : String(c);
          return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
        }).join(',');
      }).join('\r\n');
    }

    function download(name, text, mime) {
      var b = new Blob(['\ufeff' + text], { type: (mime || 'text/csv') + ';charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(b);
      a.download = name;
      a.click();
    }

    function toast(msg, ms) {
      if (typeof document === 'undefined') { return; }
      var t = document.getElementById('ui-toast');
      if (!t) { t = document.createElement('div'); t.id = 'ui-toast'; t.className = 'toast'; document.body.appendChild(t); }
      t.textContent = msg;
      t.classList.add('on');
      setTimeout(function () { t.classList.remove('on'); }, ms || 1600);
    }

    function spinner(text) { return '<span class="spin"></span> ' + esc(text || '计算中…'); }

    function query(search) {
      var s = (search === undefined)
        ? ((typeof location !== 'undefined' && location.search) || '') : (search || '');
      var o = {};
      s.replace(/^\?/, '').split('&').forEach(function (kv) {
        if (!kv) { return; }
        var i = kv.indexOf('=');
        var k = i < 0 ? kv : kv.slice(0, i);
        var v = i < 0 ? '' : kv.slice(i + 1);
        try { o[decodeURIComponent(k)] = decodeURIComponent(v.replace(/\+/g, ' ')); } catch (e) { o[k] = v; }
      });
      return o;
    }

    /* 页脚「生成时间」探针：看到 NaN/空表却找不到这一行，说明打开的是旧副本 */
    function footer(stamp, source, n) {
      return '<footer class="foot">页面生成时间：' + esc(stamp || '—')
        + '　·　数据：' + esc(source || '—') + (n === undefined || n === null ? '' : ('（' + n + ' 篇）'))
        + '　·　若你看到 NaN 或空表格，说明打开的是旧副本：按 Ctrl+F5 强制刷新，'
        + '或重新跑 python web/build_views.py。</footer>';
    }

    function mountTheme(doc) {
      doc = doc || document;
      var b = doc.getElementById('theme');
      if (!b) { return; }
      b.onclick = function () {
        var cur = doc.documentElement.getAttribute('data-theme');
        var next = cur === 'dark' ? 'light' : 'dark';
        doc.documentElement.setAttribute('data-theme', next);
        b.textContent = next === 'dark' ? '☾ 夜间' : '☀ 日间';
        try { localStorage.setItem('theme', next); } catch (e) { /* 隐私模式 */ }
      };
      try {
        var saved = localStorage.getItem('theme');
        if (saved) { doc.documentElement.setAttribute('data-theme', saved); b.textContent = saved === 'dark' ? '☾ 夜间' : '☀ 日间'; }
      } catch (e) { /* 忽略 */ }
    }

    return { CSS: CSS, inject: inject, esc: esc, attr: attr, hz: hz, badge: badge,
             fmtInt: fmtInt, fmt1: fmt1, signed: signed, csvText: csvText,
             download: download, toast: toast, spinner: spinner, query: query,
             footer: footer, mountTheme: mountTheme };
  }));
