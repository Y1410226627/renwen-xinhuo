<script setup>
/* ReviewView.vue —— 「校订队列」视图（标注闭环）。
 *
 * 数据来自 data/review_diff.csv（由构建时以 JSON 内嵌为 window.__REV__，或运行时 fetch）。
 * 把语料自带拼音标注当**独立第三方**，与引擎逐字比对，分歧进工单等词学裁定。
 * 筛选 / 排序 / 统计复用 core/review.js 的纯函数（与 node 门禁同一份实现），
 * 保证「筛选『长』的条数」等断言与旧版逐字段一致。
 */
import { ref, computed, onMounted } from 'vue';
import { ReviewApp, UI } from '../core/index.mjs';
import AppShell from '../components/AppShell.vue';

const rows = ref([]);
const kwInput = ref('');
const cur = ref([]);
const key = ref('pid');
const dir = ref('asc');
const page = ref(1);
const SIZE = 100;

const COLS = ReviewApp.COLS;
const st = computed(() => ReviewApp.stats(rows.value));
const pages = computed(() => Math.max(1, Math.ceil(cur.value.length / SIZE)));
const slice = computed(() => cur.value.slice((page.value - 1) * SIZE, page.value * SIZE));
const summaryText = computed(() => {
  const s = st.value;
  const top1 = s.top.length ? `${s.top[0][0]}（${s.top[0][1]} 条）` : '—';
  return `工单总数 = ${s.total}；涉及字数 = ${s.chars}；TOP1 = ${top1}`;
});

function doFilter() {
  cur.value = ReviewApp.filter(rows.value, kwInput.value);
  page.value = 1;
}
function sortBy(k) {
  dir.value = (k === key.value && dir.value === 'asc') ? 'desc' : 'asc';
  key.value = k;
  cur.value = ReviewApp.sortRows(cur.value, key.value, dir.value);
}
function goPage(p) { page.value = Math.min(Math.max(1, p), pages.value); }
function applyKw(k) { kwInput.value = k; doFilter(); }
function exportCsv() {
  const out = [COLS];
  cur.value.forEach((r) => out.push(COLS.map((c) => {
    const v = r[c];
    return (v && typeof v === 'object') ? JSON.stringify(v) : v;
  })));
  UI.download('词律探微_校订工单.csv', UI.csvText(out));
  UI.toast(`已导出 ${cur.value.length} 条`);
}

onMounted(async () => {
  if (typeof window !== 'undefined' && window.__REV__) {
    rows.value = window.__REV__;
  } else if (typeof window !== 'undefined' && window.__API_BASE__ === '') {
    /* 在线模式没有 review 接口，仍读同目录 JSON（由构建时随页面一起产出） */
    try { rows.value = await (await fetch('review_rows.json')).json(); } catch (e) { rows.value = []; }
  }
  const q = UI.query();
  if (q.kw) { kwInput.value = q.kw; }
  cur.value = ReviewApp.filter(rows.value, kwInput.value);
});
</script>

<template>
  <AppShell active="review" data-note="data/review_diff.csv">
    <div class="card">
      <h1>视图三 · 校订队列（标注闭环）</h1>
      <p class="dim">把语料自带拼音标注当作<b>独立第三方</b>，与引擎逐字比对，分歧进工单等词学裁定。
        汇总：{{ summaryText }}</p>
      <div class="row">
        <label class="f">筛选（任意字段）
          <input id="kw" type="text" placeholder="如：长 / 绝 / ci.清.0000"
                 v-model="kwInput" @keydown.enter="doFilter"></label>
        <button id="go" @click="doFilter">筛选</button>
        <button id="csv" class="ghost" @click="exportCsv">导出当前结果 CSV</button>
      </div>
      <p id="chips">
        <span v-for="kv in st.top.slice(0, 14)" :key="kv[0]" class="chip" :data-kw="kv[0]"
              @click="applyKw(kv[0])">{{ kv[0] }} <span class="dim">{{ kv[1] }}</span></span>
      </p>
    </div>

    <div class="card tight">
      <div id="meta">工单 <b>{{ cur.length }}</b> 条（总 {{ st.total }} 条）· 第 {{ page }} / {{ pages }} 页
        <span class="dim">点表头可排序；筛选支持任意字段，如填「长」只看该字</span></div>
    </div>

    <div class="card">
      <div class="scroll">
        <table>
          <thead><tr>
            <th v-for="c in COLS" :key="c" :data-key="c" style="cursor:pointer"
                @click="sortBy(c)">{{ c }}</th>
          </tr></thead>
          <tbody id="rows">
            <tr v-for="(r, i) in slice" :key="i">
              <td v-for="c in COLS" :key="c" :class="{ ping: c === '引擎平仄', ze: c === '语料平仄', dim: c === '证据' }">
                <b v-if="c === '字'">{{ r[c] }}</b><template v-else>{{ r[c] }}</template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div id="pager">
        <template v-if="pages > 1">
          <button class="ghost" @click="goPage(page - 1)">上一页</button>
          <span class="dim">第 {{ page }}/{{ pages }}</span>
          <button class="ghost" @click="goPage(page + 1)">下一页</button>
        </template>
      </div>
    </div>
  </AppShell>
</template>
