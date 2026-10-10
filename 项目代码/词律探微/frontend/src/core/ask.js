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
 * 对外：askHtml(j) / blockHtml(b) / researchBlockHtml(b) / renderErrorHtml(err)
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
    // 2026-10-10（P2-1 引用环）：source_note 优先（个人作品块用它标明「个人录入」）；
    //   语料块无此字段，回落到 pid，零回归。
    + '｜出处 ' + U.esc(b.source_note || b.pid) + '</div>'
    + (rows ? '<table><tr><th>句</th><th>原文</th><th>平仄（逐字）</th><th>句脚</th></tr>' + rows + '</table>' : '')
    + '</div>';
}

/* 2026-10-10（P2-2 引用环）：研究资料 / 研究事实证据块（独立键 research_evidence）。
 *   材料 / 事实块**没有** lines / pz / 句脚字段（不是诗体），不能套 blockHtml，
 *   这里单独按「标题 + 元数据 + 正文/陈述」摆。eid 前缀 M（材料）/ F（事实）。 */
function researchBlockHtml(b) {
  const isMat = String(b.eid || '').charAt(0) === 'M';
  const meta = [];
  if (b.author) { meta.push(U.esc(b.author)); }
  if (b.year) { meta.push(U.esc(String(b.year))); }
  if (b.locator) { meta.push('定位：' + U.esc(b.locator)); }
  if (b.source_url) { meta.push('来源：' + U.esc(b.source_url)); }
  let body = '';
  if (isMat) {
    const txt = String(b.content || '');
    body = '<div class="rbody">' + U.esc(txt)
      + (b.content_len > txt.length ? '……（全文 ' + b.content_len + ' 字，此处截 500 字）' : '')
      + '</div>';
  } else {
    const v = b.verified ? '已核对' : '未核对';
    body = '<div class="rbody"><b>陈述</b>：' + U.esc(b.statement || '')
      + (b.evidence ? ('<br><b>引文</b>：「' + U.esc(b.evidence) + '」') : '')
      + '<br><b>出处</b>：' + (b.source_desc ? U.esc(b.source_desc) : '—')
      + '（核验：' + v + '）</div>';
  }
  const label = isMat ? ('《' + U.esc(b.title) + '》') : U.esc(b.statement || '');
  return '<div class="e res"><b>[' + U.esc(b.eid) + ']</b> ' + label
    + '<div class="m">' + (meta.length ? (meta.join('　·　') + '｜') : '')
    + '出处 ' + U.esc(b.source_note || b.pid) + '</div>'
    + body + '</div>';
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
  // 2026-10-10（P2-1 引用环）：个人作品证据块以独立键 personal_evidence 到达
  //   （不进 blocks、不进 set_check），这里追加渲染，与语料证据同版式。
  h += (j.personal_evidence || []).map(blockHtml).join('');
  // 2026-10-10（P2-2 引用环）：研究资料/事实证据块以独立键 research_evidence 到达
  //   （不进 blocks、不进 set_check），用 researchBlockHtml 单独渲染。
  h += (j.research_evidence || []).map(researchBlockHtml).join('');
  return h;
}

/* 统一错误渲染。
   ⚠ 2026-10-04 修（代码审查 P2-8）：服务端异常时返回的是 {"error": "...", "trace": [...]}，
   旧版直接交给 askHtml（它只读 answer/verify/blocks）→ 页面显示**空白答案框**，
   用户看不到任何错误。这里先判 error，如实显示。 */
function renderErrorHtml(err) {
  return '<span class="bad">引擎出错：' + U.esc(err) + '</span>';
}

return { askHtml: askHtml, blockHtml: blockHtml, researchBlockHtml: researchBlockHtml,
         renderErrorHtml: renderErrorHtml };
}));
