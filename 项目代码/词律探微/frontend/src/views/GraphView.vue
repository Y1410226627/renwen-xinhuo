<script setup>
/* GraphView.vue —— 「知识图谱」视图：清代词人 ↔ 词牌 二部图。
 *
 * 数据来自 data/vue/graph.json（build_views.py 用 SQL 聚合：词人 TOP45 / 词牌 TOP45 / 边）。
 *
 * ⚠ 2026-10-11 更正（审查·低）：这里原写「布局算法与 build_views.py 的 Python 版**逐式对应**」，
 *   **与事实不符**——`build_views.py` 自 2026-10-05 重构（D15）起**只造数据、不拼页面**，
 *   里头根本没有布局代码（本页的布局是 Vue 侧 `layout` 一份）。注释说谎比没注释更糟：
 *   后来者会去 Python 里找「另一份布局」并对齐，白跑一趟。
 *   布局参数（行高 24px、字号 15px、两列 XA/XC）之所以这么定，理由仍是当初在
 *   build_views.py 里验过的那条：**两列布局解决「同心圆标签挤成一团」**（内圈标签间距
 *   只有 21px，看不清），且**无随机数**、任何机器上排版一致。
 * 交互：关键词筛选（高亮匹配节点与连线）、悬停节点高亮其连线并显示共有篇数。
 *
 * ⚠ 2026-10-08 精修（本轮交付）：
 *   ① 补齐三态——**加载态**（明确在载什么）/ **错误态**（fetch 失败给原因 + 三步处置）/
 *      **空态**（数据里没有节点时明说，而不是留一片空白）；
 *   ② 顶部「图谱说明」与筛选控件分区、图例更紧凑；
 *   ③ 配色沿用 core/ui.js 变量，节点异色与字号契约不变（门禁依赖）。
 *
 * ⚠ 2026-10-15 增强（缺陷 #6：图谱较浅 → 补「多跳推理」）：
 *   原页面只做「关系展示」（画点、画线、悬停看篇数），**不能沿边推理**。本轮在**纯前端**补三件事
 *   （不新增数据、不改 build_views.py、不碰 core/*.js → 六项门禁与交付答案哈希不受影响）：
 *     ① **多跳探索**：点节点设为「焦点」，面板列出**一跳邻居**（直接相连，按篇数排）与
 *        **二跳伙伴**（焦点是词人 → 经共同词牌相连的「同调词人」；焦点是词牌 → 经共同词人
 *        相连的「同作者词牌」），点伙伴即继续下一跳，顶部给出**路径面包屑**；
 *     ② **节点度数排序**：可切「按篇数」（原行为）/「按连接数」（度数 = 相异邻居数），
 *        后者让「连接面广」的节点浮到顶部；
 *     ③ **边权提示**：悬停**连线**直接显示「词人 X ↔ 词牌 Y：共 n 篇」（原来只有悬停节点）。
 *   邻接表/度数全部由 `edges` 在 computed 里现算，**无随机数**，SSR 下（graph 为空）安全短路。
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import AppShell from '../components/AppShell.vue';

const graph = ref(null);
const kw = ref('');
const hover = ref('');
const tip = ref({ on: false, text: '', x: 0, y: 0 });
/* 三态：load 有值 = 加载中；err 有值 = 出错；两者皆空且 graph 为空 = 空态。 */
const load = ref('');
const err = ref('');
/* ★ 2026-10-15 多跳探索状态：焦点节点 + 遍历路径（面包屑）+ 排序方式。 */
const focus = ref('');
const trail = ref([]);
const sortBy = ref('count');   /* 'count' = 按篇数（原行为）；'degree' = 按连接数 */

/* ---- 布局常量：两列（词人左 / 词牌右），行高与字号是验过的值 ---- */
const W = 1180, ROW = 24.0, TOP = 74.0, XA = 250.0, XC = W - 250.0;

/* ---- 邻接表 + 度数：图谱推理的基础结构，纯前端从 edges 现算（无随机数） ---- */
const adj = computed(() => {
  const g = graph.value;
  const au = {}, cp = {}, deg = {};
  if (!g) { return { au, cp, deg }; }
  for (const e of (g.edges || [])) {
    const a = e[0], c = e[1], n = e[2];
    (au[a] || (au[a] = {}))[c] = n;
    (cp[c] || (cp[c] = {}))[a] = n;
    deg['a|' + a] = (deg['a|' + a] || 0) + 1;
    deg['c|' + c] = (deg['c|' + c] || 0) + 1;
  }
  return { au, cp, deg };
});
const authorSet = computed(() => {
  const s = new Set();
  const g = graph.value;
  if (g) { for (const r of (g.authors || [])) { s.add(r[0]); } }
  return s;
});
/* 焦点在哪一侧：'author' / 'cipai' / ''（未选）。 */
const focusKind = computed(() => {
  if (!focus.value) { return ''; }
  return authorSet.value.has(focus.value) ? 'author' : 'cipai';
});

const layout = computed(() => {
  const g = graph.value;
  if (!g) { return null; }
  const deg = adj.value.deg;
  const byDeg = (rows, pre) => rows.slice().sort((x, y) => {
    const dx = deg[pre + x[0]] || 0, dy = deg[pre + y[0]] || 0;
    return (dy - dx) || (y[1] - x[1]);
  });
  const au = sortBy.value === 'degree' ? byDeg(g.authors || [], 'a|') : (g.authors || []);
  const cp = sortBy.value === 'degree' ? byDeg(g.cipai || [], 'c|') : (g.cipai || []);
  const edges = g.edges || [];
  const nRow = Math.max(au.length, cp.length);
  const H = Math.round(TOP + ROW * nRow + 34);
  const mx = Math.max(...edges.map((e) => e[2]), 1);
  /* 圆半径的尺度基准取「全库最大篇数」，**与排序方式无关**（否则换排序会让所有圆跳一下）。 */
  const maxCnt = Math.max(1, ...(g.authors || []).map((r) => r[1]), ...(g.cipai || []).map((r) => r[1]));
  const rOf = (cnt) => 4.0 + 22.0 * Math.sqrt(cnt / maxCnt);
  const pos = {};
  au.forEach(([a], i) => { pos['a|' + a] = [XA, TOP + ROW * (i + 0.5)]; });
  cp.forEach(([c], i) => { pos['c|' + c] = [XC, TOP + ROW * (i + 0.5)]; });
  const paths = edges.map(([a, c, n]) => {
    const [x1, y1] = pos['a|' + a], [x2, y2] = pos['c|' + c];
    const mx1 = (x1 + x2) / 2;
    return { a, c, n, d: `M${x1.toFixed(1)} ${y1.toFixed(1)} C${mx1.toFixed(1)} ${y1.toFixed(1)} ${mx1.toFixed(1)} ${y2.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`,
             w: 0.5 + 3.2 * n / mx };
  });
  const nodes = [];
  /* ★ 自查第 7 遍修（暗色可读性）：圆点**填充色**是门禁契约（`web/test_ui.js` 断言
     `#1f6fb2` / `#c2691a` 存在），保留原样；但**标签文字色**（原 `tfill:#1b4f80` 深蓝 /
     `#8a4a10` 深棕）在 `prefers-color-scheme:dark`（或 `data-theme=dark`）下是**深字描深边**
     （核心样式的 `.nd text` 有 `stroke:var(--panel)` 光晕，暗色 panel 也是深色）→ 对比度约 1.9:1，
     近乎不可读。改为**只输出 kind 类名**，颜色走下方 `.t-author` / `.t-cipai` 的 CSS 变量，
     亮/暗两套各得其色（亮色值与原 `#1b4f80`/`#8a4a10` 等价观感）。 */
  au.forEach(([a, cnt]) => {
    const [x, y] = pos['a|' + a];
    nodes.push({ k: a, kind: '词人', cnt, x, y, r: rOf(cnt), tx: x - 10, anchor: 'end', fill: '#1f6fb2', tclass: 't-author' });
  });
  cp.forEach(([c, cnt]) => {
    const [x, y] = pos['c|' + c];
    nodes.push({ k: c, kind: '词牌', cnt, x, y, r: rOf(cnt), tx: x + 10, anchor: 'start', fill: '#c2691a', tclass: 't-cipai' });
  });
  return { W, H, nodes, paths, nAu: au.length, nCp: cp.length, nEdge: edges.length };
});

const hasNodes = computed(() => !!(layout.value && layout.value.nodes.length));
/* 命中关键词的节点数（筛选时给一句「命中几个」的反馈，而不是只把其余调暗） */
const matchedN = computed(() => {
  const l = layout.value;
  if (!l) { return 0; }
  const k = kw.value.trim();
  if (!k) { return l.nodes.length; }
  return l.nodes.filter((n) => n.k.indexOf(k) >= 0).length;
});

/* ---- 多跳：一跳邻居 / 二跳伙伴 / 焦点信息 ---- */
const neigh = computed(() => {
  const f = focus.value;
  if (!f) { return []; }
  const a = adj.value;
  const map = focusKind.value === 'author' ? (a.au[f] || {}) : (a.cp[f] || {});
  const out = [];
  for (const k in map) { out.push({ k, n: map[k] }); }
  out.sort((x, y) => (y.n - x.n) || (x.k < y.k ? -1 : 1));
  return out.slice(0, 24);
});
/* 二跳：焦点为词人 → 经**共同词牌**相连的「同调词人」；焦点为词牌 → 经**共同词人**相连的「同作者词牌」。 */
const partners = computed(() => {
  const f = focus.value;
  const a = adj.value;
  if (!f) { return []; }
  const agg = {};
  if (focusKind.value === 'author') {
    const via = a.au[f] || {};
    for (const c in via) {
      const co = a.cp[c] || {};
      for (const b in co) {
        if (b === f) { continue; }
        const o = agg[b] || (agg[b] = { k: b, nVia: 0, n: 0 });
        o.nVia += 1; o.n += co[b];
      }
    }
  } else {
    const via = a.cp[f] || {};
    for (const au2 in via) {
      const co = a.au[au2] || {};
      for (const c2 in co) {
        if (c2 === f) { continue; }
        const o = agg[c2] || (agg[c2] = { k: c2, nVia: 0, n: 0 });
        o.nVia += 1; o.n += co[c2];
      }
    }
  }
  const out = [];
  for (const k in agg) { out.push(agg[k]); }
  out.sort((x, y) => (y.nVia - x.nVia) || (y.n - x.n) || (x.k < y.k ? -1 : 1));
  return out.slice(0, 16);
});
const focusInfo = computed(() => {
  const f = focus.value;
  const g = graph.value;
  if (!f || !g) { return null; }
  const isAu = focusKind.value === 'author';
  let cnt = 0;
  for (const r of (g.authors || [])) { if (r[0] === f) { cnt = r[1]; } }
  for (const r of (g.cipai || [])) { if (r[0] === f) { cnt = r[1]; } }
  return { k: f, kind: isAu ? '词人' : '词牌', cnt,
           deg: adj.value.deg[(isAu ? 'a|' : 'c|') + f] || 0,
           other: isAu ? '词牌' : '词人',
           partnerKind: isAu ? '同调词人' : '同作者词牌',
           viaLabel: isAu ? '共同词牌' : '共同词人' };
});

function nodeOpacity(n) {
  const k = kw.value.trim();
  if (k && n.k.indexOf(k) < 0) { return 0.10; }
  const f = focus.value;
  if (f && n.k !== f) {
    /* 焦点存在时：只有**一跳邻居**保持全亮，其余压暗（二跳伙伴走下方面板，不铺在图上）。 */
    const near = focusKind.value === 'author' ? adj.value.au[f] : adj.value.cp[f];
    if (!(near && near[n.k])) { return 0.12; }
  }
  return 1;
}
function nodeWeight(n) {
  if (focus.value && n.k === focus.value) { return '700'; }
  return (hover.value && n.k === hover.value) ? '700' : '400';
}
function onTrail(k) { return trail.value.indexOf(k) >= 0; }
function edgeOpacity(e) {
  const k = kw.value.trim();
  let on = true;
  if (k) { on = e.a.indexOf(k) >= 0 || e.c.indexOf(k) >= 0; }
  if (hover.value) { on = on && (e.a === hover.value || e.c === hover.value); }
  if (focus.value) { on = on && (e.a === focus.value || e.c === focus.value); }
  return on ? 0.85 : 0.04;
}
function onEnter(n, ev) {
  hover.value = n.k;
  tip.value = { on: true, text: `${n.kind} ${n.k}：共 ${n.cnt} 篇`, x: ev.clientX + 12, y: ev.clientY - 28 };
}
function onEdgeEnter(e, ev) {
  hover.value = '';
  tip.value = { on: true, text: `词人 ${e.a} ↔ 词牌 ${e.c}：共 ${e.n} 篇`, x: ev.clientX + 12, y: ev.clientY - 28 };
}
function onMove(ev) { tip.value = Object.assign({}, tip.value, { x: ev.clientX + 12, y: ev.clientY - 28 }); }
function onLeave() { hover.value = ''; tip.value.on = false; }
function clearKw() { kw.value = ''; }
/* 点节点 → 设焦点（再点同一节点 = 退出探索）。 */
function onNodeClick(n) {
  if (focus.value === n.k) { clearFocus(); return; }
  setFocus(n.k);
}
function setFocus(k) {
  focus.value = k;
  const i = trail.value.indexOf(k);
  if (i >= 0) { trail.value = trail.value.slice(0, i + 1); }      /* 回到走过的节点 → 截断路径 */
  else { trail.value = trail.value.concat([k]); }
}
function jumpTo(k) { setFocus(k); }
function clearFocus() { focus.value = ''; trail.value = []; }

onMounted(async () => {
  load.value = '正在载入 graph.json（词人／词牌／边，构建时已算好）…';
  try {
    const base = (typeof window !== 'undefined' && window.__API_BASE__ === '') ? '' : '../';
    const r = await fetch(base + 'graph.json');
    if (!r.ok) { throw new Error('HTTP ' + r.status); }
    graph.value = await r.json();
    load.value = '';
  } catch (e) {
    /* 离线双击时 graph.json 与页面同目录 → 直接试同级 */
    try {
      const r2 = await fetch('graph.json');
      if (!r2.ok) { throw new Error('HTTP ' + r2.status); }
      graph.value = await r2.json();
      load.value = '';
    } catch (e2) {
      graph.value = null;
      load.value = '';
      err.value = String(e2 && e2.message ? e2.message : e2);
    }
  }
});
onUnmounted(() => { tip.value.on = false; });
</script>

<template>
  <AppShell active="graph" data-note="data/graph.json">
    <div class="card">
      <h1>视图二 · 知识图谱</h1>
      <p class="dim">节点 {{ layout ? layout.nAu : '—' }}（词人）＋ {{ layout ? layout.nCp : '—' }}（词牌），
        边 {{ layout ? layout.nEdge : '—' }}。布局在构建时算好（无随机数），两列排版：
        字号 15px、行距 24px，不会重叠；可筛选、悬停高亮；也可截图进 PPT。</p>
      <p class="dim">多跳探索：<b>点任一节点</b>设为焦点 → 面板列出<b>一跳邻居</b>与<b>二跳伙伴</b>
        （词人→经共同词牌的同调词人；词牌→经共同词人的同作者词牌），点伙伴可继续往下走。</p>
      <div class="legend">
        <span><i style="background:#1f6fb2"></i>词人</span>
        <span><i style="background:#c2691a"></i>词牌</span>
        <span><u></u>线宽＝共有篇数</span>
        <span>圆大小＝篇数多少（右侧数字）</span>
      </div>
      <div class="row gv-ctrl">
        <label class="f">只看包含
          <input id="gq" type="text" placeholder="如：纳兰 / 浣溪沙" v-model="kw"></label>
        <button id="gclr" class="ghost" @click="clearKw">清空</button>
        <span class="dim">排序</span>
        <button id="gsort-count" class="ghost" :class="{ on: sortBy === 'count' }" @click="sortBy = 'count'">按篇数</button>
        <button id="gsort-degree" class="ghost" :class="{ on: sortBy === 'degree' }" @click="sortBy = 'degree'">按连接数</button>
        <span class="dim" id="gmeta">
          <template v-if="hasNodes && kw.trim()">命中 {{ matchedN }} / {{ layout.nodes.length }} 个节点</template>
          <template v-else>悬停节点/连线可看篇数，点节点进入多跳探索</template>
        </span>
      </div>
    </div>

    <div class="card">
      <div v-if="err" class="err">
        <b class="bad">图谱数据没载入</b>
        <p>{{ err }}</p>
        <p class="dim">可试：① 确认 <code>data/vue/graph.json</code> 存在（先跑
          <code>python web/build_views.py</code>）；② 从本地服务打开本页
          （<code>python web/serve.py</code>）；③ 按 <b>Ctrl+F5</b> 强制刷新，排除旧页面缓存。</p>
      </div>
      <p v-else-if="load" class="loading"><span class="spin"></span> {{ load }}</p>
      <svg v-else-if="hasNodes" id="g" class="chart" xmlns="http://www.w3.org/2000/svg"
           :viewBox="`0 0 ${layout.W} ${layout.H}`" :width="layout.W" :height="layout.H"
           font-family="Microsoft YaHei,serif">
        <path v-for="(e, i) in layout.paths" :key="'e' + i" class="ed"
              :data-a="e.a" :data-c="e.c" :data-n="e.n" :d="e.d" fill="none"
              :stroke-width="e.w"
              :style="{ opacity: edgeOpacity(e) }"
              @mouseover="onEdgeEnter(e, $event)" @mousemove="onMove($event)" @mouseout="onLeave" />
        <g v-for="(n, i) in layout.nodes" :key="'n' + i" class="nd"
           :class="{ focused: n.k === focus, ontrail: onTrail(n.k) }"
           :data-k="n.k" :data-kind="n.kind" :data-n="n.cnt"
           :style="{ opacity: nodeOpacity(n), fontWeight: nodeWeight(n), cursor: 'pointer' }"
           @mouseover="onEnter(n, $event)" @mousemove="onMove($event)" @mouseout="onLeave"
           @click="onNodeClick(n)">
          <circle :cx="n.x" :cy="n.y" :r="n.r" :fill="n.fill" />
          <text :x="n.tx" :y="n.y + 5" :text-anchor="n.anchor" :class="n.tclass">{{ n.k }}
            <tspan class="t-cnt">{{ n.cnt }}</tspan></text>
        </g>
        <text :x="XA" y="30" text-anchor="middle" font-size="16" class="gv-title">词律探微 · 清代词人 ↔ 词牌 二部图（作数前 {{ layout.nAu }}）</text>
        <text :x="XA" y="52" text-anchor="middle" font-size="13" class="gv-sub">左：词人　右：词牌　线：二者共有的篇数（越粗越多）</text>
      </svg>
      <div v-else class="empty">
        <p><b>图谱里没有可显示的节点。</b></p>
        <p class="dim">多半是 graph.json 里词人／词牌／边为空。下一步：先跑
          <code>python web/build_views.py</code> 重新聚合数据，再刷新本页。</p>
      </div>
    </div>

    <div v-if="focus && layout" class="card explore">
      <div class="ex-head">
        <b>多跳探索</b>
        <span class="dim">沿「词人 ↔ 词牌」边逐跳展开；点伙伴继续走，点同一节点退出</span>
        <button id="gexit" class="ghost" @click="clearFocus">退出探索</button>
      </div>
      <p class="ex-trail"><span class="dim">路径</span>
        <template v-for="(t, i) in trail" :key="'t' + i">
          <span v-if="i" class="ex-arrow">→</span><b class="ex-node">{{ t }}</b>
        </template>
      </p>
      <p v-if="focusInfo" class="ex-focus">
        焦点：<b>{{ focusInfo.kind }} {{ focusInfo.k }}</b>
        （共 {{ focusInfo.cnt }} 篇，直接连接 {{ focusInfo.deg }} 个{{ focusInfo.other }}）
      </p>
      <div class="ex-cols">
        <div class="ex-col">
          <h3>一跳 · 直接相连（{{ neigh.length }}）</h3>
          <p class="dim">点任一项即换焦点（下一跳）</p>
          <div class="chips">
            <button v-for="x in neigh" :key="'n' + x.k" class="chip" @click="jumpTo(x.k)">
              {{ x.k }}<span class="dim">·{{ x.n }}篇</span></button>
          </div>
        </div>
        <div class="ex-col">
          <h3>二跳 · {{ focusInfo ? focusInfo.partnerKind : '' }}（{{ partners.length }}）</h3>
          <p class="dim">经{{ focusInfo ? focusInfo.viaLabel : '' }}相连的伙伴，按共同连接数排序</p>
          <div class="chips">
            <button v-for="p in partners" :key="'p' + p.k" class="chip" @click="jumpTo(p.k)">
              {{ p.k }}<span class="dim">·{{ p.nVia }}{{ focusInfo ? focusInfo.viaLabel : '' }}/共{{ p.n }}篇</span></button>
          </div>
        </div>
      </div>
    </div>

    <div class="tip" :class="{ on: tip.on }" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">{{ tip.text }}</div>
  </AppShell>
</template>

<style scoped>
/* GraphView.vue —— 图谱页精修（2026-10-08）+ 多跳探索（2026-10-15）。配色沿用 core/ui.js 变量。 */
.gv-ctrl { align-items: center; }
.gv-ctrl #gmeta { margin-left: 4px; }
.gv-ctrl button.on { border-color: var(--accent); color: var(--accent); font-weight: 700; }

.loading { margin: 4px 0; color: var(--ink2); }
.err { border-left: 4px solid var(--warn); border-radius: 6px; padding: 8px 12px;
  background: color-mix(in srgb, var(--warn) 8%, transparent); }
.err p { margin: 6px 0 0; }
.empty { border: 1px dashed var(--line); border-radius: var(--r); padding: 14px 16px;
  background: var(--panel2); margin: 8px 0 2px; }
.empty p { margin: 4px 0; }

.legend { margin: 6px 0; }

/* ---- 多跳探索面板 ---- */
.explore { margin-top: 12px; }
.ex-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.ex-head button { margin-left: auto; }
.ex-trail { margin: 8px 0 4px; }
.ex-node { margin: 0 2px; }
.ex-arrow { color: var(--ink2); margin: 0 4px; }
.ex-focus { margin: 2px 0 8px; }
.ex-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 760px) { .ex-cols { grid-template-columns: 1fr; } }
.ex-col h3 { font-size: 14px; margin: 4px 0; }
.ex-col > p { margin: 2px 0 6px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { border: 1px solid var(--line); background: var(--panel2); border-radius: 999px;
  padding: 3px 10px; font-size: 13px; cursor: pointer; color: var(--ink); }
.chip:hover { border-color: var(--accent); color: var(--accent); }
.chip .dim { margin-left: 2px; }

/* 焦点/路径节点：描一圈，让「现在走到哪」一眼可见（不改填充色，门禁契约不动）。 */
.nd.focused circle { stroke: var(--ink); stroke-width: 2; }
.nd.ontrail circle { stroke: var(--accent); stroke-width: 1.5; }

/* ★ 自查第 7 遍修（暗色可读性）：图谱标签/连线改用**主题变量**，随亮/暗两套自动切换。
   圆点填充仍由模板内联（门禁断言 `#1f6fb2`/`#c2691a`，不动）。
   `--ping`（亮 #2f5d7c / 暗 #8fb6d4）本就是「词人蓝」，`--accent2`（亮 #8a6a53 / 暗 #c9ab8c）
   是「词牌棕」，`--ink2` 作计数灰——与核心变量一一对应，无需再写两套媒体查询。 */
.nd text.t-author { fill: var(--ping); }
.nd text.t-cipai { fill: var(--accent2); }
.nd text .t-cnt { fill: var(--ink2); }
.chart .ed { stroke: color-mix(in srgb, var(--ping) 55%, transparent); stroke-opacity: 0.5; }
.gv-title { fill: var(--ink); }
.gv-sub { fill: var(--ink2); }
</style>
