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

    /* —— 纸墨朱红设计系统（2026-10-09 移植竞品 `cilyutanwei` 的视觉语言）——
     * 三色克制：纸底 / 墨字 / 朱红；字体分层：楷（标题·词正文）/ 仿宋（正文）/ 宋（控件·表）/ Georgia（数字）。
     * 仅调「外观」，不改任何类名与 DOM，故不影响门禁的文本断言与页面审计。 */
    var ROOT = ':root{--bg:#f5f1e8;--panel:#fbf8f1;--panel2:#f6f0e4;--panel3:#fcf9f4;'
      + '--ink:#292722;--ink2:#746e62;--ink3:#8a6a53;--line:#d2caba;--line2:#d8cdbc;'
      + '--accent:#a64333;--accent-d:#9b4332;--accent2:#8a6a53;--ping:#2f5d7c;--ze:#9b4332;'
      + '--ok:#2f6b41;--warn:#8e3025;'
      + '--shadow:0 1px 2px rgba(74,58,38,.05),0 8px 24px rgba(74,58,38,.07);'
      + '--r:4px;--mono:"Cascadia Mono","Consolas","Sarasa Mono SC",monospace;'
      + '--kai:LocalKai,"KaiTi","STKaiti","Kaiti SC","楷体",serif;'
      + '--fang:LocalFang,"FangSong","STFangsong","FangSong_GB2312","仿宋",serif;'
      + '--song:"SimSun","Songti SC","宋体",serif;'
      + '--num:Georgia,"Times New Roman",serif}';
    /* 楷/仿宋走本机字体（@font-face + local()），缺失时自然回落到 serif，不下载任何字体文件。 */
    var FONT = '@font-face{font-family:LocalKai;src:local("KaiTi"),local("STKaiti"),'
      + 'local("Kaiti SC"),local("DFKai-SB"),local("楷体")}'
      + '@font-face{font-family:LocalFang;src:local("FangSong"),local("STFangsong"),'
      + 'local("FangSong_GB2312"),local("仿宋")}';

    var DARK = '--bg:#191512;--panel:#211c17;--panel2:#272119;--panel3:#241f19;'
      + '--ink:#ece5d6;--ink2:#a99d89;--ink3:#c9ab8c;--line:#3a332a;--line2:#443c31;'
      + '--accent:#cd7a63;--accent-d:#d98a70;--accent2:#c9ab8c;--ping:#8fb6d4;--ze:#d98a70;'
      + '--ok:#8fce9f;--warn:#e6a08f;'
      + '--shadow:0 1px 2px rgba(0,0,0,.45),0 8px 22px rgba(0,0,0,.42)';

    var CSS = [
      FONT,
      ROOT,
      '@media (prefers-color-scheme:dark){:root:not([data-theme=light]){' + DARK + '}}',
      'html[data-theme=dark]{' + DARK + '}',
      '*{box-sizing:border-box}',
      'body{margin:0;background:var(--bg);color:var(--ink);'
      + 'font:16px/1.7 var(--fang),"Microsoft YaHei","PingFang SC",system-ui,serif}',
      'a{color:var(--accent-d);text-decoration:none}a:hover{text-decoration:underline}',
      'header.top{position:sticky;top:0;z-index:9;background:var(--bg);'
      + 'border-bottom:1px solid var(--line)}',
      'header.top .in{max-width:1240px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}',
      '.brand{font-family:var(--kai);font-weight:700;letter-spacing:.18em;font-size:20px}',
      '.brand small{font-family:var(--fang);font-weight:400;font-size:12px;color:var(--ink2);letter-spacing:0;margin-left:8px}',
      'nav.tabs{margin-left:auto;display:flex;gap:2px;flex-wrap:wrap}',
      'nav.tabs a{padding:6px 12px;border-radius:var(--r);border:1px solid transparent;background:transparent;'
      + 'font-family:var(--song);font-size:14px;color:var(--ink2);transition:color .12s,border-color .12s}',
      'nav.tabs a.on{border-color:var(--line);color:var(--accent);'
      + 'box-shadow:inset 0 -2px 0 var(--accent)}',
      'nav.tabs a:hover{text-decoration:none;color:var(--accent)}',
      'main{max-width:1240px;margin:0 auto;padding:22px 20px 60px}',
      'h1,h2,h3{font-family:var(--kai);font-weight:600}',
      'h1{font-size:27px;letter-spacing:.12em;margin:10px 0 6px}'
      + 'h2{font-size:22px;letter-spacing:.08em;margin:20px 0 8px}'
      + 'h3{font-size:18px;letter-spacing:.05em;margin:14px 0 6px}',
      '.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);'
      + 'padding:18px 20px;margin:12px 0}',
      '.card.tight{padding:12px 14px}',
      '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}',
      '.row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}',
      '.f{display:flex;flex-direction:column;gap:3px;font-size:12.5px;color:var(--ink2)}',
      'input,select,button,textarea{font:inherit}',
      'input[type=text],input[type=number],select{padding:6px 9px;border:1px solid var(--line);'
      + 'border-radius:var(--r);background:var(--panel3);color:var(--ink);min-width:80px;'
      + 'font-family:var(--song)}',
      'input:focus,select:focus,textarea:focus{border-color:var(--accent)}',
      'a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,'
      + 'textarea:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px}',
      'button,.btn{background:var(--accent);color:#fdf9f2;border:1px solid var(--accent-d);'
      + 'border-radius:var(--r);padding:6px 15px;cursor:pointer;font-family:var(--song);'
      + 'transition:background .12s,color .12s,border-color .12s}',
      'button:hover,.btn:hover{background:var(--accent-d);border-color:var(--accent-d)}',
      'button.ghost,.btn.ghost{background:transparent;color:var(--accent)}',
      'button.ghost:hover,.btn.ghost:hover{background:transparent;border-color:var(--accent)}',
      'button.ghost.on{background:var(--accent);color:#fdf9f2}',
      'button:disabled{opacity:.5;cursor:default}',
      'table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0;font-family:var(--song)}',
      'th,td{border-bottom:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}',
      'thead th{background:var(--panel2);position:sticky;top:0;z-index:3;font-weight:600;'
      + 'box-shadow:inset 0 -1px 0 var(--line);font-family:var(--song);letter-spacing:.04em}',
      'tbody tr:nth-child(2n){background:color-mix(in srgb,var(--panel2) 45%,transparent)}',
      'tbody tr:hover{background:color-mix(in srgb,var(--accent) 7%,transparent)}',
      '.mono{font-family:var(--mono);letter-spacing:.5px}',
      '.ping{color:var(--ping);font-weight:600}.ze{color:var(--ze);font-weight:600}',
      '.dim{color:var(--ink2);font-size:12.5px}',
      '.ok{color:var(--ok);font-weight:600}.bad{color:var(--warn);font-weight:600}',
      '.chip{display:inline-block;margin:3px 6px 0 0;padding:3px 10px;border:1px solid var(--line);'
      + 'border-radius:var(--r);background:var(--panel3);cursor:pointer;font-size:13px}',
      '.chip:hover{border-color:var(--accent);color:var(--accent)}',
      '.badge{display:inline-block;padding:1px 8px;border-radius:3px;font-size:12px;'
      + 'border:1px solid var(--line);background:var(--panel2);color:var(--ink2);margin-right:5px}',
      '.badge.acc{border-color:var(--accent);color:var(--accent)}',
      '.badge.warn{border-color:var(--warn);color:var(--warn)}',
      'pre,code,.code{font-family:var(--mono);font-size:12.5px}',
      'pre{background:var(--panel2);border:1px solid var(--line);border-radius:var(--r);padding:10px;overflow:auto}',
      'code{background:var(--panel2);border-radius:3px;padding:1px 5px}',
      'tr.hit>td{background:color-mix(in srgb,var(--accent2) 18%,transparent)}',
      'mark{background:color-mix(in srgb,var(--accent) 18%,transparent);color:inherit;border-radius:3px}',
      '.bar{position:sticky;bottom:0;background:var(--bg);border-top:1px solid var(--line);'
      + 'padding:8px 0;margin-top:10px}',
      '.q{background:var(--panel);border-left:3px solid var(--accent);padding:9px 13px;'
      + 'border-radius:var(--r);margin:10px 0;font-family:var(--kai);font-size:16px}',
      '.a{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);'
      + 'padding:12px 14px;margin:8px 0;white-space:pre-wrap}',
      '.m{color:var(--ink2);font-size:12.5px;margin-top:8px;border-top:1px dashed var(--line);padding-top:6px;white-space:normal}',
      '.e{border:1px solid var(--line);border-radius:var(--r);padding:9px 11px;margin:7px 0;background:var(--panel3)}',
      'footer.foot{max-width:1240px;margin:26px auto 0;padding:10px 20px 34px;color:var(--ink2);font-size:12.5px;'
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
      /* —— 以下为 2026-10-09 新增的「纸墨」组件（只增不改，旧页面不受影响）—— */
      '.masthead{font-family:var(--kai);letter-spacing:.32em;text-align:center;'
      + 'padding:14px 0 4px;font-size:13px;color:var(--ink3)}',
      '.seal{display:inline-block;font-family:var(--kai);font-size:12px;letter-spacing:.18em;'
      + 'color:var(--accent);border:1.5px solid var(--accent);border-radius:3px;padding:2px 8px;'
      + 'transform:rotate(-3deg);opacity:.9;white-space:nowrap;line-height:1.4}',
      '.tiny-seal{display:inline-block;writing-mode:vertical-rl;font-family:var(--kai);font-size:11px;'
      + 'letter-spacing:.2em;color:var(--accent);border:1px solid var(--accent);border-radius:2px;'
      + 'padding:4px 2px;line-height:1;opacity:.85}',
      '.seg{display:inline-flex;border:1px solid var(--line);border-radius:var(--r);overflow:hidden;'
      + 'background:var(--panel3)}',
      '.seg>button,.seg>label{background:transparent;border:none;border-right:1px solid var(--line);'
      + 'color:var(--ink2);padding:5px 13px;border-radius:0;font-family:var(--song);cursor:pointer;'
      + 'transition:background .12s,color .12s}',
      '.seg>button:last-child,.seg>label:last-child{border-right:none}',
      '.seg>button:hover,.seg>label:hover{color:var(--accent)}',
      '.seg>button.on,.seg>label.on{background:#38362f;color:#f6f0e4}',
      '.cellrow{display:flex;flex-wrap:wrap;gap:6px}',
      '.cell{width:54px;min-height:54px;border:1px solid var(--line);border-radius:var(--r);'
      + 'background:var(--panel3);display:flex;flex-direction:column;align-items:center;'
      + 'justify-content:center;gap:1px;padding:3px 0}',
      '.cell b{font-family:var(--kai);font-weight:600;font-size:32px;line-height:1}',
      '.cell i{font-style:normal;font-size:11px;color:var(--ink2);line-height:1}',
      '.cell u{text-decoration:none;font-size:10px;color:var(--ink3);line-height:1}',
      '.cell.on b{text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px}',
      '.cell.mismatch b{text-decoration:underline dashed var(--warn)}',
      '.ev{border-left:2px solid var(--accent2);padding:2px 0 2px 12px;margin:8px 0;'
      + 'color:var(--ink2);font-family:var(--fang);font-size:14.5px}',
      '.ev cite{display:block;font-style:normal;font-size:12px;color:var(--ink3);margin-top:4px}',
      '.metric-strip{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line);'
      + 'border-radius:var(--r);overflow:hidden;background:var(--panel3);margin:10px 0}',
      '.metric-strip>div{padding:10px 14px;border-right:1px solid var(--line)}',
      '.metric-strip>div:last-child{border-right:none}',
      '.metric-strip b{display:block;font-family:var(--num);font-size:24px;line-height:1.3;color:var(--accent)}',
      '.metric-strip span{font-size:12px;color:var(--ink2)}',
      '@media print{header.top,nav.tabs,.bar,button{display:none}body{background:#fff}}',
      '@media (max-width:640px){main{padding:12px}thead th{position:static}'
      + '.grid{grid-template-columns:1fr}.metric-strip{grid-template-columns:repeat(2,1fr)}'
      + '.metric-strip>div:nth-child(2n){border-right:none}}'
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

    /* 导出 JSON（2026-10-09 新增）：与 download 分开，因为 **JSON 不能带 BOM**——
     * 带 BOM 的文件用 `json.load()` / `JSON.parse` 读取会报「Unexpected token」，
     * 而 CSV 带 BOM 是为了让 Excel 认 UTF-8。两者需求相反，故各留一个入口。 */
    function downloadJson(name, obj) {
      var text = (typeof obj === 'string') ? obj : JSON.stringify(obj, null, 2);
      var b = new Blob([text], { type: 'application/json;charset=utf-8' });
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
             download: download, downloadJson: downloadJson, toast: toast,
             spinner: spinner, query: query,
             footer: footer, mountTheme: mountTheme };
  }));
