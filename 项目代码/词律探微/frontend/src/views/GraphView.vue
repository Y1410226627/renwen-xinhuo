<script setup>
/* GraphView.vue —— 「知识图谱」视图：清代词人 ↔ 词牌 二部图。
 *
 * 数据来自 data/graph.json（build_views.py 用 SQL 聚合：词人 TOP45 / 词牌 TOP45 / 边）。
 * 布局算法与 build_views.py 的 Python 版**逐式对应**（行高 24px、字号 15px、两列 XA/XC），
 * 因为它已解决「同心圆标签挤成一团」的老毛病，且**无随机数**、任何机器上排版一致。
 * 交互：关键词筛选（高亮匹配节点与连线）、悬停节点高亮其连线并显示共有篇数。
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import AppShell from '../components/AppShell.vue';

const graph = ref(null);
const kw = ref('');
const hover = ref('');
const tip = ref({ on: false, text: '', x: 0, y: 0 });

/* ---- 布局常量：与 build_views.py 一致 ---- */
const W = 1180, ROW = 24.0, TOP = 74.0, XA = 250.0, XC = W - 250.0;

const layout = computed(() => {
  const g = graph.value;
  if (!g) { return null; }
  const au = g.authors || [], cp = g.cipai || [], edges = g.edges || [];
  const nRow = Math.max(au.length, cp.length);
  const H = Math.round(TOP + ROW * nRow + 34);
  const mx = Math.max(...edges.map((e) => e[2]), 1);
  const maxCnt = Math.max(au.length ? au[0][1] : 1, cp.length ? cp[0][1] : 1, 1);
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
  au.forEach(([a, cnt]) => {
    const [x, y] = pos['a|' + a];
    nodes.push({ k: a, kind: '词人', cnt, x, y, r: rOf(cnt), tx: x - 10, anchor: 'end', fill: '#1f6fb2', tfill: '#1b4f80' });
  });
  cp.forEach(([c, cnt]) => {
    const [x, y] = pos['c|' + c];
    nodes.push({ k: c, kind: '词牌', cnt, x, y, r: rOf(cnt), tx: x + 10, anchor: 'start', fill: '#c2691a', tfill: '#8a4a10' });
  });
  return { W, H, nodes, paths, nAu: au.length, nCp: cp.length, nEdge: edges.length };
});

function nodeOpacity(n) {
  const k = kw.value.trim();
  if (k && n.k.indexOf(k) < 0) { return 0.10; }
  return 1;
}
function nodeWeight(n) {
  return (hover.value && n.k === hover.value) ? '700' : '400';
}
function edgeOpacity(e) {
  const k = kw.value.trim();
  let on = true;
  if (k) { on = e.a.indexOf(k) >= 0 || e.c.indexOf(k) >= 0; }
  if (hover.value) { on = on && (e.a === hover.value || e.c === hover.value); }
  return on ? 0.85 : 0.04;
}
function onEnter(n, ev) {
  hover.value = n.k;
  tip.value = { on: true, text: `${n.kind} ${n.k}：共 ${n.cnt} 篇`, x: ev.clientX + 12, y: ev.clientY - 28 };
}
function onMove(ev) { tip.value = Object.assign({}, tip.value, { x: ev.clientX + 12, y: ev.clientY - 28 }); }
function onLeave() { hover.value = ''; tip.value.on = false; }
function clearKw() { kw.value = ''; }

onMounted(async () => {
  try {
    const base = (typeof window !== 'undefined' && window.__API_BASE__ === '') ? '' : '../';
    const r = await fetch(base + 'graph.json');
    graph.value = await r.json();
  } catch (e) {
    /* 离线双击时 graph.json 与页面同目录 → 直接试同级 */
    try {
      const r2 = await fetch('graph.json');
      graph.value = await r2.json();
    } catch (e2) { graph.value = null; }
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
      <div class="legend">
        <span><i style="background:#1f6fb2"></i>词人</span>
        <span><i style="background:#c2691a"></i>词牌</span>
        <span><u></u>线宽＝共有篇数</span>
        <span>圆大小＝篇数多少（右侧数字）</span>
      </div>
      <div class="row">
        <label class="f">只看包含
          <input id="gq" type="text" placeholder="如：纳兰 / 浣溪沙" v-model="kw"></label>
        <button id="gclr" class="ghost" @click="clearKw">清空</button>
        <span class="dim" id="gmeta">悬停节点可高亮其连线、看篇数</span>
      </div>
    </div>

    <div class="card">
      <svg v-if="layout" id="g" class="chart" xmlns="http://www.w3.org/2000/svg"
           :viewBox="`0 0 ${layout.W} ${layout.H}`" :width="layout.W" :height="layout.H"
           font-family="Microsoft YaHei,serif">
        <path v-for="(e, i) in layout.paths" :key="'e' + i" class="ed"
              :data-a="e.a" :data-c="e.c" :data-n="e.n" :d="e.d" fill="none"
              stroke="#5b86b8" stroke-opacity="0.35" :stroke-width="e.w"
              :style="{ opacity: edgeOpacity(e) }" />
        <g v-for="(n, i) in layout.nodes" :key="'n' + i" class="nd"
           :data-k="n.k" :data-kind="n.kind" :data-n="n.cnt"
           :style="{ opacity: nodeOpacity(n), fontWeight: nodeWeight(n), cursor: 'pointer' }"
           @mouseover="onEnter(n, $event)" @mousemove="onMove($event)" @mouseout="onLeave">
          <circle :cx="n.x" :cy="n.y" :r="n.r" :fill="n.fill" />
          <text :x="n.tx" :y="n.y + 5" :text-anchor="n.anchor" :fill="n.tfill">{{ n.k }}
            <tspan fill="#7a8b9a">{{ n.cnt }}</tspan></text>
        </g>
        <text :x="XA" y="30" text-anchor="middle" font-size="16">词律探微 · 清代词人 ↔ 词牌 二部图（作数前 {{ layout.nAu }}）</text>
        <text :x="XA" y="52" text-anchor="middle" font-size="13" fill="#6b7a88">左：词人　右：词牌　线：二者共有的篇数（越粗越多）</text>
      </svg>
      <p v-else class="dim"><span class="spin"></span> 正在载入 graph.json…</p>
    </div>

    <div class="tip" :class="{ on: tip.on }" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">{{ tip.text }}</div>
  </AppShell>
</template>
