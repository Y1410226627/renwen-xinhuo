/* app_ask.js —— 「在线问答」页面的应用层（唯一实现；页面只负责摆结构）。
 *
 * 分工（贯穿全项目）：**数字归引擎、说法归大模型、出处归引用**。
 * 本文件只做三件事：把问题发给 /api/ask、把返回的 JSON 摆成人能读的样子、
 * 把「护栏校验 / 查询理解来源 / 命中总数 / 表述来源 / 大模型是否就绪」如实显示出来。
 *
 * 流式（2026-10-01）：SSE 事件 = status（进度）→ engine（**引擎答案先到**，含证据块）
 * → delta（大模型逐字增量）→ final（完整结果，与 /api/ask 同构）。
 * 「答案先到、说法后补」：引擎 0.1 秒内算完的结论与证据**立即显示**，
 * 大模型的「说明」随后边写边补——用户不再干等大模型整段写完。
 *
 * 对外：window.AskApp = { askHtml(j), blockHtml(b), mount(opts) }
 */
(function (root) {
  'use strict';
  var U = root.UI;

  function blockHtml(b) {
    var rows = (b.lines || []).map(function (L) {
      return '<tr class="' + (L.matched ? 'hit' : '') + '"><td>' + (L.idx + 1) + (L.matched ? ' ✳' : '')
        + '</td><td>' + U.esc(L.text) + '</td><td>' + U.hz(L.pz || '') + '</td><td>'
        + U.esc(L.tail || '') + '</td></tr>';
    }).join('');
    return '<div class="e"><b>[' + U.esc(b.eid) + ']</b> ' + U.esc(b.dynasty) + '·' + U.esc(b.author)
      + '《' + U.esc(b.title || b.cipai) + '》'
      + '<div class="m">' + b.sent_n + ' 句 / ' + b.han_len + ' 字，平 ' + b.ping + '、仄 ' + b.ze
      + '，仄声比例 ' + b.ze_ratio + '%，声情 ' + U.esc(b.scene)
      + (b.n_match ? ('｜命中条件的句：' + b.n_match + ' 句') : '')
      + '｜出处 ' + U.esc(b.pid) + '</div>'
      + (rows ? '<table><tr><th>句</th><th>原文</th><th>平仄（逐字）</th><th>句脚</th></tr>' + rows + '</table>' : '')
      + '</div>';
  }

  function askHtml(j) {
    var v = j.verify || {};
    var h = '<div class="a">' + U.esc(j.answer || '')
      + '<div class="m">护栏校验：<span class="' + (v.ok ? 'ok' : 'bad') + '">'
      + (v.ok ? '通过' : '未通过') + '</span>'
      + ((v.problems && v.problems.length) ? ('　问题：' + U.esc(v.problems.join('；'))) : '')
      + '　｜　问题类型：' + U.esc(j.kind || '—') + (j.refused ? '（已拒答）' : '')
      + (j.parse_source ? ('　｜　查询理解：' + U.esc(j.parse_source)) : '')
      + (typeof j.total === 'number' ? ('　｜　命中总数：' + j.total + ' 篇') : '')
      + ((j.cond_violations && j.cond_violations.length)
         ? ('　｜　条件复核异常：' + U.esc(j.cond_violations.join('；'))) : '')
      + '　｜　表述来源：' + U.esc(j.narrator || 'template')
      + (j.ms ? ('　｜　用时 ' + j.ms + ' ms') : '')
      + '</div></div>';
    // 去重：answer 正文里**已含**同一段大模型稿时不要再渲染一遍
    // （实测页面上同一段「论证表述」出现两次：一次在答案正文里、一次在说明块里）
    var _nt = (j.narrative && j.narrative.text) || '';
    var _dup = _nt && (j.answer || '').indexOf(_nt.slice(0, 24)) >= 0;
    if (j.narrative && j.narrative.ok && !_dup) {
      h += '<div class="a" style="background:var(--panel2)"><b>说明</b>（大模型 '
        + U.esc(j.narrative.model) + ' 写，数字仍由引擎给，已过四道护栏）<br>'
        + U.esc(j.narrative.text) + '</div>';
    } else if (j.narrative && !j.narrative.ok) {
      h += '<div class="m">大模型表述未通过护栏，已回退确定性模板'
        + (j.narrative.reason ? ('（' + U.esc(j.narrative.reason) + '）') : '') + '。</div>';
    }
    h += (j.blocks || []).map(blockHtml).join('');
    return h;
  }

  function mount(opts) {
    opts = opts || {};
    U.inject();
    var API = opts.api || '';
    var $ = function (id) { return document.getElementById(id); };
    var L = $('log');
    function add(html) { L.insertAdjacentHTML('beforeend', html); }
    // 多轮上下文（2026-10-01 深夜）：记住上一轮的「问句＋解析摘要」，
    // 下一次提问（勾选「用大模型理解问句」时）带上它 → 「那里面呢」这类指代可被补全；
    // 回答的查询理解里会如实注明「已结合上一轮上下文」。
    var lastTurn = null;

    // ---------- 流式：答案先到、说法后补 ----------
    // 原先点一下要干等 1.4~5 秒（大模型整段写完才返回）。现在走 SSE：
    //   status（进度）→ engine（**引擎算完的答案与证据，先显示**）
    //   → delta（大模型逐字增量）→ final（完整结果，与 /api/ask 同构）。
    // 流式不可用时**自动退回**普通端点，功能不降级（只是少了逐字效果）。
    function streamAsk(q, wid, useP, useL, useA, ctxv) {
      var box = document.getElementById(wid);
      if (!box) { return; }
      // 结构：外层 box 不动；里面三块（答案区 / 状态行 / 增量区），
      // 引擎结果一到就把答案区填上——状态行与增量区继续活着。
      box.innerHTML = '<div id="' + wid + '-ans">' + U.spinner('正在检索语料并核算…') + '</div>'
        + '<div class="m" id="' + wid + '-st">已收到问题，正在检索语料与核对数字…</div>'
        + '<div class="a" id="' + wid + '-nv" style="background:var(--panel2);display:none"></div>';
      var el = function (suf) { return document.getElementById(wid + suf); };
      var url = API + '/api/ask_stream?q=' + encodeURIComponent(q) + '&topk=3'
        + (useP ? '&parse=1' : '')                       // 勾选框真的生效（旧版硬编码 parse=1）
        + (useL ? '&narrate=1' : '')
        + (useA ? '&argument=1' : '')
        + (ctxv ? '&ctx=' + encodeURIComponent(ctxv) : '');
      function frame(txt) {
        var d; try { d = JSON.parse(txt); } catch (e) { return; }
        if (d.type === 'status') {
          var st = el('-st');
          if (st) { st.textContent = (d.text || '') + (d.model ? ('（大模型：' + d.model + '）') : ''); }
        } else if (d.type === 'engine') {
          // ⭐ 引擎结果先到：立刻显示答案、证据与护栏结论（不干等大模型）
          var ans = el('-ans');
          if (ans) { ans.innerHTML = askHtml(d); }
          var st2 = el('-st');
          if (st2 && (useL || useA)) {
            st2.textContent = '数字与证据已就绪（用时 ' + (d.ms || '…')
              + ' ms）；大模型正在补写' + (useA ? '论证草稿' : '说明') + '…';
          }
        } else if (d.type === 'delta') {
          var nv = el('-nv');
          if (nv) {
            nv.style.display = 'block';
            nv.dataset.acc = (nv.dataset.acc || '') + (d.text || '');
            nv.innerHTML = '<b>说明</b>（大模型正在写；数字仍由引擎给，写完还要过四道护栏）<br>'
              + U.esc(nv.dataset.acc);
          }
        } else if (d.type === 'final') {
          if (d.spec) { lastTurn = {q: q, spec: (typeof d.spec === 'string' ? d.spec : '')}; }
          var b = document.getElementById(wid);
          if (b) { b.outerHTML = askHtml(d); }
        } else if (d.type === 'error') {
          var b2 = document.getElementById(wid);
          if (b2) { b2.innerHTML = '<span class="bad">出错了：' + U.esc(d.error || '') + '</span>'; }
        }
      }
      function fallback() {                       // 流式不可用 → 退回普通端点
        var u2 = API + '/api/ask?q=' + encodeURIComponent(q);
        if (useP) { u2 += '&parse=1'; }
        if (useL || useA) { u2 += '&narrate=1'; }
        if (useA) { u2 += '&argument=1'; }
        if (ctxv) { u2 += '&ctx=' + encodeURIComponent(ctxv); }
        fetch(u2).then(function (r) { return r.json(); }).then(function (j) {
          var b = document.getElementById(wid);
          if (b) { b.outerHTML = askHtml(j); }
        }).catch(function (e) {
          var b3 = document.getElementById(wid);
          if (b3) { b3.innerHTML = '<span class="bad">出错了：' + U.esc(e) + '</span>'; }
        });
      }
      fetch(url).then(function (r) {
        if (!r.ok || !r.body || !r.body.getReader) { throw new Error('该浏览器不支持流式'); }
        var rd = r.body.getReader(), dec = new TextDecoder(), buf = '';
        function pump() {
          return rd.read().then(function (x) {
            if (x.done) { return; }
            buf += dec.decode(x.value, { stream: true });
            var parts = buf.split('\n\n');
            buf = parts.pop();
            for (var i = 0; i < parts.length; i++) {
              var ln = parts[i].trim();
              if (ln.indexOf('data:') !== 0) { continue; }
              var p = ln.slice(5).trim();
              if (p && p.indexOf('"done"') < 0) { frame(p); }
            }
            return pump();
          });
        }
        return pump();
      }).catch(fallback);
    }

    function go() {
      var q = $('q').value.trim();
      if (!q) { U.toast('先写一句问题'); return; }
      var useP = $('useParse').checked, useL = $('useLlm').checked, useA = $('useArg').checked;
      // 多轮上下文：把上一轮的「问句＋解析」带上（仅当勾选「用大模型理解问句」）；
      // 供「那里面呢」这类指代补全，答案里会如实注明是否用了上下文。
      var ctxv = '';
      if (useP && lastTurn) {
        ctxv = ('上一问：' + lastTurn.q + '｜上一轮解析为：' + lastTurn.spec).slice(0, 300);
      }
      add('<div class="q">问：' + (ctxv ? '（承上一轮）' : '') + U.esc(q) + '</div>');
      var wid = 'w' + Date.now();
      add('<div class="a" id="' + wid + '">' + U.spinner('正在检索语料并核算…') + '</div>');
      if ((useL || useA) && window.fetch) { streamAsk(q, wid, useP, useL, useA, ctxv); return; }
      var url = API + '/api/ask?q=' + encodeURIComponent(q);
      if (useP) { url += '&parse=1'; }
      if (useL || useA) { url += '&narrate=1'; }
      if (useA) { url += '&argument=1'; }
      if (ctxv) { url += '&ctx=' + encodeURIComponent(ctxv); }
      fetch(url).then(function (r) { return r.json(); }).then(function (j) {
        if (j && j.spec) { lastTurn = {q: q, spec: (typeof j.spec === 'string' ? j.spec : '')}; }
        var box = document.getElementById(wid);
        box.outerHTML = askHtml(j);
      }).catch(function (e) {
        var box2 = document.getElementById(wid);
        if (box2) { box2.innerHTML = '<span class="bad">出错了：' + U.esc(e) + '</span>'; }
      });
    }

    if ($('go')) { $('go').onclick = go; }
    if ($('q')) { $('q').onkeydown = function (e) { if (e.key === 'Enter') { go(); } }; }
    fetch(API + '/api/llm').then(function (r) { return r.json(); }).then(function (x) {
      if ($('llmTag')) { $('llmTag').textContent = x.available ? ('大模型就绪：' + x.model) : '大模型未接入（按模板作答）'; }
    });
    fetch(API + '/api/examples').then(function (r) { return r.json(); }).then(function (xs) {
      if ($('chips')) {
        $('chips').innerHTML = xs.map(function (s) {
          return '<span class="chip" data-q="' + U.attr(s) + '">' + U.esc(s) + '</span>';
        }).join('');
      }
    });
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (t && t.getAttribute && t.getAttribute('data-q') && $('q')) {
        $('q').value = t.getAttribute('data-q');
        go();
      }
    });
    var q0 = U.query();
    if (q0.q && $('q')) { $('q').value = q0.q; go(); }
    return { go: go, askHtml: askHtml };
  }

  var api = { askHtml: askHtml, blockHtml: blockHtml, mount: mount };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  root.AskApp = api;
}(typeof window !== 'undefined' ? window : this));