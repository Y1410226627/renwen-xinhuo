<script setup>
/* GraphView.vue —— 「知识图谱」视图：清代词人 ↔ 词牌 二部图。
 *
 * 数据来自 data/graph.json（build_views.py 用 SQL 聚合：词人 TOP45 / 词牌 TOP45 / 边）。
 * 布局算法与 build_views.py 的 Python 版**逐式对应**（行高 24px、字号 15px、两列 XA/XC），
 * 因为它已解决「同心圆标签挤成一团」的老毛病，且**无随机数**、任何机器上排版一致。
 * 交互：关键词筛选（高亮匹配节点与连线）、悬停节点高亮其连线并显示共有篇数。
 *
 * ⚠ 2026-10-08 精修（本轮交付）：
 *   ① 补齐三态——**加载态**（明确在载什么）/ **错误态**（fetch 失败给原因 + 三步处置）/
 *      **空态**（数据里没有节点时明说，而不是留一片空白）；
 *   ② 顶部「图谱说明」与筛选控件分区、图例更紧凑；
 *   ③ 配色沿用 core/ui.js 变量，节点异色与字号契约不变（门禁依赖）。
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

const hasNodes = computed(() => !!(layout.value && layout.value.nodes.length));
/* 命中关键词的节点数（筛选时给一句「命中几个」的反馈，而不是只把其余调暗） */
const matchedN = computed(() => {
  const l = layout.value;
  if (!l) { return 0; }
  const k = kw.value.trim();
  if (!k) { return l.nodes.length; }
  return l.nodes.filter((n) => n.k.indexOf(k) >= 0).length;
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
        <span class="dim" id="gmeta">
          <template v-if="hasNodes && kw.trim()">命中 {{ matchedN }} / {{ layout.nodes.length }} 个节点</template>
          <template v-else>悬停节点可高亮其连线、看篇数</template>
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
      <div v-else class="empty">
        <p><b>图谱里没有可显示的节点。</b></p>
        <p class="dim">多半是 graph.json 里词人／词牌／边为空。下一步：先跑
          <code>python web/build_views.py</code> 重新聚合数据，再刷新本页。</p>
      </div>
    </div>

    <div class="tip" :class="{ on: tip.on }" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">{{ tip.text }}</div>
  </AppShell>
</template>

<style scoped>
/* GraphView.vue —— 图谱页精修（2026-10-08）。配色沿用 core/ui.js 变量，不另起一套。 */
.gv-ctrl { align-items: center; }
.gv-ctrl #gmeta { margin-left: 4px; }

.loading { margin: 4px 0; color: var(--ink2); }
.err { border-left: 4px solid var(--warn); border-radius: 6px; padding: 8px 12px;
  background: color-mix(in srgb, var(--warn) 8%, transparent); }
.err p { margin: 6px 0 0; }
.empty { border: 1px dashed var(--line); border-radius: var(--r); padding: 14px 16px;
  background: var(--panel2); margin: 8px 0 2px; }
.empty p { margin: 4px 0; }

.legend { margin: 6px 0; }
</style>
