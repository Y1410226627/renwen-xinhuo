<script setup>
/* AppShell.vue —— 应用外壳（五个视图共用）：顶部导航、主题按钮、页脚。
 * DOM 结构、class 名、锚点 id 与旧模板保持一致
 * （header.top / .in / .brand / nav.tabs / button#theme / main / footer.foot），
 * 这样 core/ui.js 的样式与门禁的页面审计都能对准。
 */
import { computed } from 'vue';
import { theme, toggleTheme, themeLabel } from '../stores/theme.js';

const props = defineProps({
  active: { type: String, default: '' },       // 当前视图 key：ask/browse/parse/graph/review/index
  stamp: { type: String, default: '' },        // 页面生成时间探针
  dataNote: { type: String, default: 'data/corpus.db' },
  dataN: { type: Number, default: null },
  online: { type: Boolean, default: false }    // true = 走本地服务（链接指向服务根）
});

/* 导航项：**链接形态与旧版一致**（相对路径），保证 file:// 双击也能跳转。*/
const tabs = [
  { key: 'index', href: 'index.html', label: '总览' },
  { key: 'parse', href: 'parse.html', label: '逐字解析' },
  { key: 'browse', href: 'browse.html', label: '多条件检索' },
  { key: 'graph', href: 'graph.html', label: '知识图谱' },
  { key: 'review', href: 'review.html', label: '校订队列' },
  { key: 'ask', href: 'ask.html', label: '声情问答' }
];

/* 页脚探针：优先用调用方传入的 stamp；否则读构建时注入的 window.__STAMP__
   （离线视图由 build_views.py 生成 stamp.js；在线服务由 serve.py 注入）。
   ⚠ SSR 下 window 可能不存在，故加 typeof 守卫。 */
const stampText = computed(() => {
  if (props.stamp) { return props.stamp; }
  if (typeof window !== 'undefined' && window.__STAMP__) { return String(window.__STAMP__); }
  return '—';
});
const noteText = computed(() =>
  props.dataNote + (props.dataN === null || props.dataN === undefined ? '' : `（${props.dataN} 篇）`));
</script>

<template>
  <header class="top">
    <div class="in">
      <div class="brand">词律探微
        <small>清代词律声情研究助手 · 答案可溯源</small>
      </div>
      <nav class="tabs" aria-label="主导航">
        <a v-for="t in tabs" :key="t.key" :href="t.href"
           :class="{ on: t.key === active }"
           :aria-current="t.key === active ? 'page' : null">{{ t.label }}</a>
      </nav>
      <button id="theme" class="ghost" type="button"
              :data-mode="theme.mode"
              :title="theme.mode === 'dark' ? '当前：夜间 —— 点击切到日间' : '当前：日间 —— 点击切到夜间'"
              aria-label="切换日间 / 夜间主题"
              @click="toggleTheme">{{ themeLabel() }}</button>
    </div>
  </header>

  <main><slot /></main>

  <footer class="foot">
    <div class="foot-main">
      <span>页面生成时间：{{ stampText }}</span>
      <span class="sep">·</span>
      <span>数据：{{ noteText }}</span>
    </div>
    <div class="foot-note">
      数字全部由本地引擎算出（逐字注音 → 平仄 → 比例 → 声情）；
      若你看到 NaN 或空表格，说明打开的是旧副本：按 Ctrl+F5 强制刷新，
      或重新跑 <code>python web/build_views.py</code>。
    </div>
  </footer>
</template>

<style>
/* AppShell.vue —— 外壳与**跨视图共用样式**（2026-10-08 精修）。
 *
 * 为什么是**非 scoped**：外壳是五个视图（含问答页）共用的 DOM；表格通用样式也要求
 * 在检索页与校订页都生效。这里一律**加明确前缀收口**——外壳部分前缀 `header.top` /
 * `footer.foot` / `#theme`，表格部分前缀 `.view-table`——绝不写裸标签选择器，
 * 因此不会外溢污染任一视图的正文。
 *
 * 配色沿用 core/ui.js 的 CSS 变量（--panel/--line/--accent/--accent2/--ink2/…），不另起一套。
 * ⚠ 不要改 core/ui.js：本文件只做「叠加微调」，与基线样式互补而不冲突。 */

/* 1) 导航：当前项高亮更明确（底色由 core/ui.js 给，这里再补字重 + 焦点环 + 下沿），
 *    tab 高亮与 hover 过渡统一，键盘 Tab 到时有清晰焦点。 */
header.top nav.tabs a { transition: background .15s, border-color .15s, color .15s; }
header.top nav.tabs a.on { font-weight: 600;
  box-shadow: 0 1px 0 color-mix(in srgb, var(--accent) 55%, transparent); }
header.top nav.tabs a:focus-visible,
header.top #theme:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--accent) 55%, transparent); outline-offset: 2px; }

/* 2) 主题按钮：明确「当前是什么」，夜间态用强调色区分；窄屏不与 logo 抢行。 */
header.top #theme { white-space: nowrap; }
header.top #theme[data-mode="dark"] { border-color: var(--accent2); color: var(--accent2); }

/* 3) 页脚：主信息（生成时间 / 数据源）与排障提示分两行，主次分明。 */
footer.foot .foot-main { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline; }
footer.foot .foot-main .sep { color: var(--line); }
footer.foot .foot-note { margin-top: 6px; line-height: 1.7; }
footer.foot .foot-note code { font-size: 12px; }

/* 4) 共用表格（`.view-table` 收口）：长表格可读性 —— 表头粘性沿用 core/ui.js 的
 *    `thead th{position:sticky;top:0}`（容器 `.scroll` 内滚动），此处只补三件事：
 *    ① 窄屏不再把列挤成一团，改为横向滚动；② 数值右对齐 + 等宽数字，便于纵向比对；
 *    ③ 可排序列给出指针与悬停反馈。 */
.view-table { min-width: 640px; }
.view-table th,
.view-table td { padding: 6px 10px; }
.view-table td.num,
.view-table th.num { text-align: right; font-variant-numeric: tabular-nums;
  font-family: var(--mono); letter-spacing: .3px; }
.view-table thead th.sortable { cursor: pointer; user-select: none; white-space: nowrap; }
.view-table thead th.sortable:hover { color: var(--accent); }
.view-table th .sort-ind { color: var(--accent); font-size: 11px; margin-left: 3px; }

@media (max-width: 640px) {
  .view-table { min-width: 560px; }
}
</style>
