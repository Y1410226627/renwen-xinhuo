<script setup>
/* AppShell.vue —— 应用外壳（五个视图共用）：顶部导航、主题按钮、页脚。
 * DOM 结构、class 名、锚点 id 与旧模板保持一致
 * （header.top / .in / .brand / nav.tabs / button#theme / main / footer.foot），
 * 这样 core/ui.js 的样式与门禁的页面审计都能对准。
 */
import { computed } from 'vue';
import { toggleTheme, themeLabel } from '../stores/theme.js';

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
      <nav class="tabs">
        <a v-for="t in tabs" :key="t.key" :href="t.href"
           :class="{ on: t.key === active }">{{ t.label }}</a>
      </nav>
      <button id="theme" class="ghost" title="切换日间/夜间" @click="toggleTheme">{{ themeLabel() }}</button>
    </div>
  </header>

  <main><slot /></main>

  <footer class="foot">
    页面生成时间：{{ stampText }}　·　数据：{{ noteText }}　·　
    数字全部由本地引擎算出（逐字注音 → 平仄 → 比例 → 声情）；
    若你看到 NaN 或空表格，说明打开的是旧副本：按 Ctrl+F5 强制刷新，
    或重新跑 python web/build_views.py。
  </footer>
</template>
