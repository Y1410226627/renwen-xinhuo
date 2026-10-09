/* app_ask.js —— 「在线问答」页面的应用层（唯一实现；页面只负责摆结构）。
 *
 * 分工（贯穿全项目）：**数字归引擎、说法归大模型、出处归引用**。
 * 本文件只做三件事：把问题发给 /api/ask、把返回的 JSON 摆成人能读的样子、
 * 把「护栏校验 / 查询理解来源 / 命中总数 / 表述来源 / 大模型是否就绪」如实显示出来。
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
    if (j.narrative && j.narrative.ok) {
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

    function go() {
      var q = $('q').value.trim();
      if (!q) { U.toast('先写一句问题'); return; }
      var useP = $('useParse').checked, useL = $('useLlm').checked, useA = $('useArg').checked;
      add('<div class="q">问：' + U.esc(q) + '</div>');
      var wid = 'w' + Date.now();
      add('<div class="a" id="' + wid + '">' + U.spinner('正在检索语料并核算…') + '</div>');
      var url = API + '/api/ask?q=' + encodeURIComponent(q);
      if (useP) { url += '&parse=1'; }
      if (useL || useA) { url += '&narrate=1'; }
      if (useA) { url += '&argument=1'; }
      fetch(url).then(function (r) { return r.json(); }).then(function (j) {
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
