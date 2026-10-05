<script setup>
/* ParseView.vue —— 「逐字解析 + 多条件检索」视图（同一组件服务两页）。
 *
 * 两种运行模式，**同一套逻辑**（数字口径走 core/parse.js，与 Python 引擎同一套）：
 *   · 离线模式（parse.html）：数据内嵌在页面里（window.__PACK__），全部在浏览器本地算；
 *   · 在线模式（browse.html / 服务）：条件发给 /api/search，由 SQLite 查；详情走 /api/parse。
 *
 * 与旧版的差异只在「结构写法」：21 个检索字段与 11 个排序项改为**配置数组驱动渲染**
 * （旧版是一百多行手写 <label>），这是本次「降低维护成本」的核心改进之一。
 * 判定表、分页语义、逐字解析渲染全部复用 core/parse.js 的纯函数（字符串契约不变）。
 */
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { ParseApp, UI } from '../core/index.mjs';
import AppShell from '../components/AppShell.vue';
import { api } from '../api.js';

const props = defineProps({
  mode: { type: String, default: 'offline' }      // 'offline' | 'online'
});
const online = props.mode === 'online';

/* ---------- 检索字段配置（唯一来源；表单、条件文本、清空、深链都用它） ---------- */
const FIELDS = [
  { id: 'dynasty', label: '朝代', type: 'select', opts: [['清', '清'], ['宋', '宋'], ['元', '元']], def: '清' },
  { id: 'q', label: '关键词', type: 'text', ph: '如：江南', wide: true },
  { id: 'author', label: '词人', type: 'text', ph: '如：纳兰性德' },
  { id: 'cipai', label: '词牌', type: 'text', ph: '如：临江仙' },
  { id: 'tail', label: '句脚字', type: 'text', ph: '愁 灯（多字取并集）' },
  { id: 'tailPz', label: '句脚平仄', type: 'select', opts: [['', '不限'], ['平', '平'], ['仄', '仄']] },
  { id: 'pz', label: '声律模式', type: 'text', ph: '仄仄平平仄（? = 任意）' },
  { id: 'minLen', label: '字数 ≥', type: 'number' },
  { id: 'maxLen', label: '字数 ≤', type: 'number' },
  { id: 'minSent', label: '句数 ≥', type: 'number' },
  { id: 'maxSent', label: '句数 ≤', type: 'number' },
  { id: 'minZe', label: '仄比 ≥%', type: 'number' },
  { id: 'maxZe', label: '仄比 ≤%', type: 'number' },
  { id: 'minLong', label: '最长句 ≥', type: 'number' },
  { id: 'changeMin', label: '变化值 ≥', type: 'number', step: '0.1' },
  { id: 'changeMax', label: '变化值 ≤', type: 'number', step: '0.1' },
  { id: 'thrMin', label: '长句阈值 ≥', type: 'number' },
  { id: 'thrMax', label: '长句阈值 ≤', type: 'number' },
  { id: 'scene', label: '声情', type: 'select',
    opts: [['', '不限'], ['后段上升', '后段上升'], ['后段下降', '后段下降'], ['前后持平', '前后持平']] },
  { id: 'sort', label: '排序', type: 'select', opts: [
    ['pid', '默认（按篇号）'], ['ze_desc', '仄声比例 从高到低'], ['ze_asc', '仄声比例 从低到高'],
    ['len_desc', '全篇字数 从多到少'], ['len_asc', '全篇字数 从少到多'],
    ['sent_desc', '句数 从多到少'], ['sent_asc', '句数 从少到多'],
    ['long_desc', '最长句 从长到短'], ['long_asc', '最长句 从短到长'],
    ['change_desc', '变化值 从高到低'], ['change_asc', '变化值 从低到高']] },
  { id: 'size', label: '每页', type: 'select', opts: [['20', '20'], ['50', '50'], ['100', '100'], ['200', '200']], def: '50' }
];

const cond = reactive({});
FIELDS.forEach((f) => { cond[f.id] = f.def !== undefined ? f.def : ''; });

const size = ref(50);
const page = ref(1);
const total = ref(0);
const pages = ref(1);
const rows = ref([]);            // 已渲染的行（离线为 hit 对象；在线为行数组）
const facets = ref(null);
const metaHtml = ref('');
const pagerHtml = ref('');
const detailHtml = ref('');
const whereSql = ref('');
const orderBy = ref('');
const cnt = ref(0);
const lastHits = ref([]);        // 供导出 CSV
let lastCond = {};

/* ---------- 判据：离线数据（由构建时注入 window.__PACK__） ---------- */
function readPack() {
  if (typeof window !== 'undefined' && window.__PACK__) {
    ParseApp.setData(window.__PACK__);
    cnt.value = window.__PACK__.rows.length;
    if (window.__DATA_N__ === undefined) { window.__DATA_N__ = cnt.value; }
  }
}

function readCond() {
  const o = {};
  FIELDS.forEach((f) => {
    const v = cond[f.id];
    const s = (v === null || v === undefined) ? '' : String(v).trim();
    if (f.type === 'number') { o[f.id] = s === '' ? '' : Number(s); }
    /* ⚠ 2026-10-06 修（修复过程中发现的**新缺陷**）：`sort` 与 `size` 原先被一起排除，
       但两者性质不同——size 是「页长」（由上面的 `size` ref 驱动分页，不进检索条件），
       sort 是**检索参数**（服务端 `SORTS` 白名单要用它生成 ORDER BY）。
       排除 sort 后 `c.sort` 恒为 undefined → 服务端永远走默认 `ORDER BY p.pid`
       → **排序下拉框在在线/离线都不生效**；也让本轮的「离线/在线 tie-break 一致」
       修复在真实 UI 里根本走不到。现只排除 size，sort 正常进入条件。 */
    else if (f.id === 'size') { /* 页长不进条件 */ }
    else { o[f.id] = s; }
  });
  o.dynasty = o.dynasty || '清';
  return o;
}

/* 「每页」下拉框（cond.size）**不进检索条件**，只驱动分页。
   旧版把 size 从条件里排除后忘了接到分页上 → 用户改下拉框完全无效（永远 50/页）。
   这里监听它，改了就更新页长并回到第 1 页**重新检索/重切页**（否则只改数字、列表不重排）。 */
watch(() => cond.size, (v) => {
  const n = parseInt(v, 10);
  if (n > 0 && n !== size.value) { size.value = n; page.value = 1; run(1); }
});

/* 声律模式白名单（与 core/parse.js 的 PZ_OK / web/serve.py _pz_glob 同一口径） */
const PZ_OK = ParseApp.PZ_OK;

/* ---------- 渲染（在线/离线统一入口） ---------- */
function paint(res, c, alreadyPaged) {
  lastCond = c;
  const pg = ParseApp.pageSlice(res, page.value, size.value, !!alreadyPaged);
  page.value = pg.page; pages.value = pg.pages; total.value = pg.total;
  lastHits.value = res.hits || [];
  rows.value = pg.hits;
  facets.value = res.facets || null;
  metaHtml.value = `命中 <b>${pg.total}</b> 篇 · 本页显示 ${pg.hits.length} 篇 · 第 `
    + `${pg.page} / ${pg.pages} 页 · 用时 ${res.ms} ms`
    + `<br><span class="dim">条件：${UI.esc(ParseApp.condText(c))}</span>`;
  pagerHtml.value = pg.pages > 1
    ? `<button class="ghost" data-go="1">首页</button> <button class="ghost" data-go="${pg.page - 1}">上一页</button> `
      + `<span class="dim">第 ${pg.page} / ${pg.pages} 页</span> <button class="ghost" data-go="${pg.page + 1}">下一页</button> `
      + `<button class="ghost" data-go="${pg.pages}">末页</button>`
    : '';
}

async function run(p) {
  page.value = p || 1;
  const c = readCond();
  /* 声律模式含非法字符：明确报错并中止（不静默替换成通配符），与 web/serve.py 的
     400 INVALID_QUERY 同口径。 */
  if (c.pz && !PZ_OK.test(String(c.pz).trim())) {
    metaHtml.value = '<span class="bad">声律模式含非法字符：只允许「平」「仄」「?」「？」</span>';
    rows.value = []; total.value = 0; pages.value = 1; facets.value = null;
    pagerHtml.value = ''; lastHits.value = [];
    return;
  }
  if (online) {
    metaHtml.value = '<span class="spin"></span> 正在向本地引擎检索…';
    try {
      const j = await api.search(c, page.value, size.value);
      if (j.error) { metaHtml.value = `<span class="bad">出错：${UI.esc(j.error)}</span>`; return; }
      /* 行对象与离线统一成 [pid,dynasty,author,cipai,title,raw]；指标直接用库里的 */
      const hits = (j.rows || []).map((r) => ({
        row: [r.pid, r.dynasty, r.author, r.cipai, r.title, r.raw || ''],
        info: { metrics: r }
      }));
      paint({ total: j.total, hits, facets: j.facets, ms: j.ms }, c, true);
      whereSql.value = j.where || ''; orderBy.value = j.order_by || '';
    } catch (e) {
      metaHtml.value = `<span class="bad">出错：${UI.esc(e)}</span>`;
    }
    return;
  }
  const pack = (typeof window !== 'undefined' && window.__PACK__) ? window.__PACK__ : null;
  if (!pack) { metaHtml.value = '<span class="bad">离线数据未注入</span>'; return; }
  paint(ParseApp.searchOffline(pack.rows, c), c, false);
  whereSql.value = ''; orderBy.value = '';
}

function resetAll() {
  FIELDS.forEach((f) => { if (f.id !== 'size') { cond[f.id] = f.def !== undefined ? f.def : ''; } });
  run(1);
}

/* 最长句序的规范化（2026-10-06 修「第 NaN 句」）：
   数据可能以三种形态到达——① 真数组（离线自算 / 新服务端）；② JSON 数组字面量字符串
   （库里原样存 '[4]'，旧服务端会这么返回）；③ 纯文本「1、3」/「1,3」（更早的格式）。
   旧版只认第 ③ 种，于是第 ② 种被整串当作一个元素 → Number('[4]') = NaN → 渲染「第 NaN 句」。
   这里三种都认，并过滤非有限数，保证产出恒为「数字数组」。 */
function parseSeq(v) {
  if (Array.isArray(v)) return v.map(Number).filter(Number.isFinite);
  if (v === undefined || v === null) return [];
  const s = String(v).trim();
  if (s.charAt(0) === '[') {
    try {
      const a = JSON.parse(s);
      if (Array.isArray(a)) return a.map(Number).filter(Number.isFinite);
    } catch (e) { /* 退回纯文本分支 */ }
  }
  return s.split(/[、,，\s]+/).filter((x) => x !== '').map(Number).filter(Number.isFinite);
}

async function showDetail(pid) {
  detailHtml.value = '<span class="spin"></span> 取逐字解析…';
  if (online) {
    try {
      const j = await api.parse(pid);
      if (j.error) { detailHtml.value = `<span class="bad">${UI.esc(j.error)}</span>`; return; }
      const lines = (j.lines || []).map((L) => ({ text: L.text, pz: L.pz, tail: L.tail }));
      const row = [j.pid, j.dynasty, j.author, j.cipai, j.title, j.raw || ''];
      const jm = Object.assign({}, j);
      jm.longest_seq = parseSeq(j.longest_seq);
      detailHtml.value = ParseApp.detailHtml(row, {
        lines, metrics: jm, tails: lines.map((L) => L.tail)
      }, lastCond);
    } catch (e) {
      detailHtml.value = `<span class="bad">${UI.esc(e)}</span>`;
    }
    return;
  }
  const pack = window.__PACK__;
  const i = pack.rows.findIndex((r) => r[0] === pid);
  if (i >= 0) { detailHtml.value = ParseApp.detailHtml(pack.rows[i], ParseApp.info(pack.rows[i], i), lastCond); return; }
  detailHtml.value = `<span class="bad">没有这一篇：${UI.esc(pid)}</span>`;
}

/* 导出范围（F6）：离线 lastHits 是**全部命中**；在线是服务端分页后的**当前页**。
   旧版两种模式都只导出 lastHits，在线时悄悄把「当前页」当成「全部」。
   这里不偷偷换语义，而是把范围**显式标注**在按钮文案与 CSV 首列上：
     · 在线且总命中 > 当前页行数 → 「当前页 N 篇」；
     · 其余（离线 / 在线凑巧一页装下）→ 「全部 N 篇」。
   这样导出结果始终可预期（低风险：不动分页与检索，只改展示）。 */
const csvScope = computed(() => (online && lastHits.value.length < total.value) ? '当前页' : '全部');
const csvLabel = computed(() => `导出 CSV（${csvScope.value} ${lastHits.value.length} 篇）`);

function exportCsv() {
  const out = [['导出范围', 'pid', '朝代', '词人', '词牌', '题名', '句数', '字数', '平', '仄', '仄声比例%', '声情', '变化值', '阈值', '原文']];
  lastHits.value.forEach((it) => {
    const r = it.row, m = it.info.metrics;
    out.push([csvScope.value, r[0], r[1], r[2], r[3], r[4], m.sent_n, m.han_len, m.ping, m.ze, m.ze_ratio, m.scene, m.change, m.threshold, r[5]]);
  });
  if (out.length === 1) { UI.toast('没有可导出的结果'); return; }
  UI.download('词律探微_检索结果.csv', UI.csvText(out));
  UI.toast(`已导出 ${csvScope.value} ${out.length - 1} 篇`);
}

/* 分面 → 点击即筛 */
function applyFacet(pairs) {
  pairs.forEach(([f, v]) => { if (cond[f] !== undefined) { cond[f] = v; } });
  run(1);
}
function goPage(p) { run(p); window.scrollTo(0, 0); }

/* 比例分桶（键名/文案与 core/parse.js 的 facets 分桶、web/serve.py 的 RATIO_BUCKETS 完全一致）。
   ⚠ 边界重叠（F5）：分面**计数**用半开区间（core/parse.js 的 `z<40` / serve.py 的 `>=lo AND <hi`），
   而点击分面写入 minZe/maxZe 后，**命中判定**是闭区间 `minZe<=z<=maxZe`。
   若上界直接写 40，则 ze_ratio=40.0 会同时命中 '25–40%'（[25,40]）与 '40–50%'（[40,50]），
   与计数口径不一致。ze_ratio 恒为 1 位小数（core/metrics.js 银行家舍入），
   故非末桶上界减 0.01 以表达开区间：40.0 只落 '40–50%'；末桶无上界，用 100 收口。 */
const ratioBuckets = { '0–25%': [0, 24.99], '25–40%': [25, 39.99], '40–50%': [40, 49.99], '50–65%': [50, 64.99], '65–100%': [65, 100] };

onMounted(() => {
  readPack();
  const q0 = UI.query();
  FIELDS.forEach((f) => { if (q0[f.id] !== undefined) { cond[f.id] = q0[f.id]; } });
  if (q0.q !== undefined) { cond.q = q0.q; }
  if (q0.size) { cond.size = q0.size; size.value = parseInt(q0.size, 10) || size.value; }
  run(1);
  if (q0.pid) { showDetail(q0.pid); }
});
</script>

<template>
  <AppShell :active="online ? 'browse' : 'parse'" :online="online"
            :data-note="online ? '本地引擎（data/corpus.db）' : 'data/web_poems.json'" :data-n="cnt">
    <div class="card">
      <h1>{{ online ? '多条件检索（在线 · 由 SQLite 查）' : '逐字解析与检索（离线 · 浏览器本地算）' }}</h1>
      <p class="dim">条件之间是「且」。{{ online
        ? '本页把条件发给本地服务，由库里的行级数据（含 lines 表）检索；数字与引擎逐字段一致。'
        : '本页数据内嵌在网页里，无需服务；判定规则与服务端同一张表。' }}
        <span v-if="!online">共 <b id="cnt">{{ cnt }}</b> 篇。</span></p>
      <div class="row">
        <label v-for="f in FIELDS" :key="f.id" class="f" :style="f.wide ? 'flex:1 1 240px' : ''">
          {{ f.label }}
          <select v-if="f.type === 'select'" :id="f.id" v-model="cond[f.id]">
            <option v-for="o in f.opts" :key="o[0]" :value="o[0]">{{ o[1] }}</option>
          </select>
          <input v-else-if="f.type === 'number'" :id="f.id" type="number"
                 :step="f.step || '1'" v-model="cond[f.id]">
          <input v-else :id="f.id" type="text" :placeholder="f.ph || ''" v-model="cond[f.id]"
                 @keydown.enter="run(1)">
        </label>
        <button id="go" @click="run(1)">检索</button>
        <button id="reset" class="ghost" @click="resetAll">清空</button>
        <button id="csv" class="ghost" @click="exportCsv">{{ csvLabel }}</button>
      </div>
    </div>

    <div class="card tight">
      <div id="meta" v-html="metaHtml"></div>
      <div v-if="online && whereSql" class="dim">SQL 条件：{{ whereSql }}；ORDER BY {{ orderBy }}</div>
      <div id="facets" v-if="facets">
        <div class="grid">
          <div><h3>词人 TOP</h3>
            <span v-for="kv in facets.author" :key="'a' + kv[0]" class="chip"
                  @click="applyFacet([['author', kv[0]]])">{{ kv[0] }} <span class="dim">{{ kv[1] }}</span></span>
          </div>
          <div><h3>词牌 TOP</h3>
            <span v-for="kv in facets.cipai" :key="'c' + kv[0]" class="chip"
                  @click="applyFacet([['cipai', kv[0]]])">{{ kv[0] }} <span class="dim">{{ kv[1] }}</span></span>
          </div>
          <div><h3>句脚字 TOP</h3>
            <span v-for="kv in facets.tail" :key="'t' + kv[0]" class="chip"
                  @click="applyFacet([['tail', kv[0]]])">{{ kv[0] }} <span class="dim">{{ kv[1] }}</span></span>
          </div>
          <div><h3>仄声比例分布（点区间即筛）</h3>
            <span v-for="(n, k) in facets.ratio" :key="'r' + k" class="chip"
                  @click="applyFacet([['minZe', (ratioBuckets[k] || [0, 100])[0]], ['maxZe', (ratioBuckets[k] || [0, 100])[1]]])"
            >{{ k }} <span class="dim">{{ n }}</span></span>
            <h3 style="margin-top:8px">声情转向</h3>
            <span v-for="kv in facets.scene" :key="'s' + kv[0]" class="chip"
                  @click="applyFacet([['scene', kv[0]]])">{{ kv[0] }} <span class="dim">{{ kv[1] }}</span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="scroll">
        <table>
          <thead><tr><th>#</th><th>词人</th><th>题名</th><th>词牌</th><th>句数</th><th>字数</th><th>仄比</th><th>声情</th><th>操作</th></tr></thead>
          <tbody id="rows">
            <tr v-for="(it, i) in rows" :key="i">
              <td class="dim">{{ (page - 1) * size + i + 1 }}</td>
              <td v-html="ParseApp.highlight(it.row[2], lastCond.q)"></td>
              <td v-html="ParseApp.highlight(it.row[4], lastCond.q)"></td>
              <td class="dim" v-html="ParseApp.highlight(it.row[3], lastCond.q)"></td>
              <td>{{ it.info.metrics.sent_n }}</td>
              <td>{{ it.info.metrics.han_len }}</td>
              <td>{{ it.info.metrics.ze_ratio }}%</td>
              <td class="dim">{{ it.info.metrics.scene }}</td>
              <td><button class="ghost" :data-pid="it.row[0]" @click="showDetail(it.row[0])">逐字解析</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div id="pager" v-html="pagerHtml" @click="(e) => { const g = e.target.getAttribute && e.target.getAttribute('data-go'); if (g) { goPage(parseInt(g, 10)); } }"></div>
    </div>

    <div class="card">
      <h2>逐字解析</h2>
      <div id="detail" v-html="detailHtml"></div>
    </div>
  </AppShell>
</template>
