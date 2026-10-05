/* core/ask.js —— 「在线问答」的**纯逻辑层**（零 DOM；Vue 组件与 node 门禁共用）。
 *
 * 分工（贯穿全项目）：**数字归引擎、说法归大模型、出处归引用**。
 * 本文件只做一件事：把 /api/ask 返回的 JSON 摆成人能读的 HTML 串。
 *
 * 流式（2026-10-01）：SSE 事件 = status（进度）→ engine（**引擎答案先到**，含证据块）
 * → delta（大模型逐字增量）→ final（完整结果，与 /api/ask 同构）。
 *
 * ⚠ 架构说明（D15）：本文件是**唯一真源**；`web/app_ask.js` 只是 `require` 本文件的薄转发。
 *   外壳用 UMD（经典脚本）：**既能在 node 的 `vm` 沙箱里直接加载**（旧门禁一行不改），
 *   也能被 Vite 打包进 Vue 组件（`frontend/src/core/index.mjs` 提供 ESM 桥接）。
 *
 * 对外：askHtml(j) / blockHtml(b) / renderErrorHtml(err)
 */
(function (root, factory) {
  var api = factory(root.UI);
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
  if (root) { root.AskApp = api; }
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this),
  function (U) {
  'use strict';

function blockHtml(b) {
  const rows = (b.lines || []).map((L) =>
    '<tr class="' + (L.matched ? 'hit' : '') + '"><td>' + (L.idx + 1) + (L.matched ? ' ✳' : '')
    + '</td><td>' + U.esc(L.text) + '</td><td>' + U.hz(L.pz || '') + '</td><td>'
    + U.esc(L.tail || '') + '</td></tr>').join('');
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
  const v = j.verify || {};
  let h = '<div class="a">' + U.esc(j.answer || '')
    + '<div class="m">护栏校验：<span class="' + (v.ok ? 'ok' : 'bad') + '">'
    + (v.ok ? '通过' : '未通过') + '</span>'
    + ((v.problems && v.problems.length) ? ('　问题：' + U.esc(v.problems.join('；'))) : '')
    + '　｜　问题类型：' + U.esc(j.kind || '—') + (j.refused ? '（已拒答）' : '')
    // ⚠ 2026-10-05 新增（朋友对照）：把「结论的理由」按**八态**显示——「查了没有」与
    //   「不支持」「来源不可得」「多解」分开，用户不必从整段文案里猜。
    + ((j.reason && j.reason.label) ? ('　｜　结论理由：' + U.esc(j.reason.label)) : '')
    + (j.parse_source ? ('　｜　查询理解：' + U.esc(j.parse_source)) : '')
    + (typeof j.total === 'number' ? ('　｜　命中总数：' + j.total + ' 篇') : '')
    + ((j.cond_violations && j.cond_violations.length)
       ? ('　｜　条件复核异常：' + U.esc(j.cond_violations.join('；'))) : '')
    + '　｜　表述来源：' + U.esc(j.narrator || 'template')
    + (j.ms ? ('　｜　用时 ' + j.ms + ' ms') : '')
    + '</div></div>';
  // 去重：answer 正文里**已含**同一段大模型稿时不要再渲染一遍
  // （实测页面上同一段「论证表述」出现两次：一次在答案正文里、一次在说明块里）
  const _nt = (j.narrative && j.narrative.text) || '';
  const _dup = _nt && (j.answer || '').indexOf(_nt.slice(0, 24)) >= 0;
  if (j.narrative && j.narrative.ok && !_dup) {
    h += '<div class="a" style="background:var(--panel2)"><b>说明</b>（大模型 '
      + U.esc(j.narrative.model) + ' 写，数字仍由引擎给，已过四道护栏）<br>'
      + U.esc(j.narrative.text) + '</div>';
  } else if (j.narrative && !j.narrative.ok) {
    // ⚠ 2026-10-04 修（代码审查 P3-9）：服务端 narrative 的键是 problems（数组），
    //   旧版读 `narrative.reason`（不存在）→ 回退原因永远显示为空。
    const _np = (j.narrative.problems || []).slice(0, 2).join('；');
    h += '<div class="m">大模型表述未通过护栏，已回退确定性模板'
      + (_np ? ('（' + U.esc(_np) + '）') : '') + '。</div>';
  }
  h += (j.blocks || []).map(blockHtml).join('');
  return h;
}

/* 统一错误渲染。
   ⚠ 2026-10-04 修（代码审查 P2-8）：服务端异常时返回的是 {"error": "...", "trace": [...]}，
   旧版直接交给 askHtml（它只读 answer/verify/blocks）→ 页面显示**空白答案框**，
   用户看不到任何错误。这里先判 error，如实显示。 */
function renderErrorHtml(err) {
  return '<span class="bad">引擎出错：' + U.esc(err) + '</span>';
}

return { askHtml: askHtml, blockHtml: blockHtml, renderErrorHtml: renderErrorHtml };
}));
