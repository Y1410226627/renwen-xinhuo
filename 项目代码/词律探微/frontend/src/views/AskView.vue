<script setup>
/* AskView.vue —— 「声情问答」视图（在线，走 /api/*）。
 *
 * 分工（贯穿全项目）：**数字归引擎、说法归大模型、出处归引用**。
 * 本组件只负责「交互与摆结构」：把问题发出去、把返回的 JSON 摆成人能读的样子、
 * 把「护栏校验 / 查询理解来源 / 命中总数 / 表述来源 / 大模型是否就绪 / 八态结论理由」如实显示。
 * 结果块的 HTML 由 core/ask.js 的 askHtml/blockHtml 生成 —— 与旧页面、node 门禁**同一份实现**。
 *
 * ⚠ 2026-10-08 两处增强（本轮交付）：
 *   ① 多轮「结果集」通路：每轮回答成功后记下**本轮命中的篇号（pid）**，下一轮把它与
 *      ctx（问句+解析摘要）一并交给后端；否则「那里面哪个最短？」只能靠模型**猜**「那里面」。
 *      上一轮 0 篇时**不带** ctx_pids（避免把范围锁死成空集）。
 *   ② 理解详情折叠区：如实展示解析来源 / 查询理解 / 丢弃字段 / 未理解片段 / 护栏校验
 *      （有则显示、无则隐藏）；若「有未理解片段且没形成任何条件」，明确告诉用户
 *      「以下按词面相关度排的结果不是该问题的答案」——**绝不**把相关度排序伪装成答案。
 */
import { ref, onMounted, nextTick } from 'vue';
import { api } from '../api.js';
import { AskApp, UI } from '../core/index.mjs';
import AppShell from '../components/AppShell.vue';

const q = ref('');
const useParse = ref(true);
const useLlm = ref(false);
const useArg = ref(false);
const llmTag = ref('');
const chips = ref([]);
const turns = ref([]);          // [{ question, ctx, ctxN, concl, evid, detail, gap, status, delta, ... }]
let lastTurn = null;            // { q, spec, pids } —— 供下一轮 ctx / ctx_pids 取用

/* 页面生成时间探针（由服务端在返回 HTML 时替换 @@STAMP@@ 注入）。 */
const stamp = ref('');
if (typeof window !== 'undefined' && window.__STAMP__) { stamp.value = String(window.__STAMP__); }

const logEl = ref(null);

function scrollBottom() {
  nextTick(() => { if (logEl.value) { logEl.value.scrollTop = logEl.value.scrollHeight; } });
}

/* 把返回体拆成「结论」「证据」两段 —— 都调用 core 自己的渲染器（askHtml / blockHtml），
   不重写契约，只把证据块摆到单独一栏，让「结论 / 证据 / 理解详情」三段一眼分开。 */
function conclHtml(j) { return AskApp.askHtml(Object.assign({}, j, { blocks: [] })); }
function evidHtml(j) { return ((j && j.blocks) || []).map(AskApp.blockHtml).join(''); }

/* 从返回体取「本轮命中的篇号」：优先显式 pid 列表，否则取每个证据块的 pid 字段
   （先读实际返回结构再写：/api/ask 的证据块里确有 pid）。去重、上限 200 个防超长。 */
function pidsOf(j) {
  if (!j || typeof j !== 'object') { return []; }
  const list = Array.isArray(j.pids) ? j.pids : ((j.blocks || []).map((b) => b && b.pid));
  const out = []; const seen = Object.create(null);
  for (const p of list) {
    if (typeof p === 'string' && p && !seen[p]) {
      seen[p] = 1;
      out.push(p);
      if (out.length >= 200) { break; }
    }
  }
  return out;
}

/* 结构化字段 → 可显示的字符串（对象则 JSON 化，避免页面出现 [object Object]）。 */
function one(x) {
  if (typeof x === 'string') { return x; }
  try { return JSON.stringify(x); } catch (e) { return String(x); }
}
function fmtList(arr, sep) { return (arr || []).map(one).join(sep); }

/* 理解详情：如实取后端返回的结构化字段（有则显示、无则隐藏）。 */
function detailOf(j) {
  if (!j || typeof j !== 'object') { return null; }
  const v = (j.verify && typeof j.verify === 'object') ? j.verify : {};
  let spec = '';
  if (typeof j.spec === 'string') { spec = j.spec; }
  else if (j.spec && typeof j.spec === 'object') { try { spec = JSON.stringify(j.spec); } catch (e) { spec = ''; } }
  const cp = (j.ctx_pids && typeof j.ctx_pids === 'object') ? j.ctx_pids : null;
  return {
    source: j.parse_source || j.source || '',
    spec: spec,
    dropped: Array.isArray(j.parse_dropped) ? j.parse_dropped : [],
    unparsed: Array.isArray(j.unparsed) ? j.unparsed : [],
    notes: Array.isArray(j.parse_notes) ? j.parse_notes : [],
    verifyOk: (typeof v.ok === 'boolean') ? v.ok : null,
    problems: Array.isArray(v.problems) ? v.problems : [],
    ctxPids: (cp && typeof cp.received === 'number') ? cp : null,
    total: (typeof j.total === 'number') ? j.total : null
  };
}

function hasDetail(d) {
  return !!d && !!(d.source || d.spec || d.dropped.length || d.unparsed.length
    || d.notes.length || d.problems.length || d.verifyOk !== null
    || (d.ctxPids && d.ctxPids.received > 0));
}

/* 语义缺口：有「没被理解的片段」且「没形成任何条件」（total 为空 → 按词面相关度兜底）时，
   用一句话说清楚——绝不把相关度排序伪装成答案。 */
function gapOf(d) {
  if (!d || !d.unparsed.length || d.total !== null) { return ''; }
  return '注意：这句话里的「' + d.unparsed.join('、')
    + '」没能转成可执行条件；以下按词面相关度排序展示的内容，不是对该问题的回答。';
}

/* 把一次返回体落到某一轮上（结论/证据/理解详情/缺口/篇号）。 */
function applyResult(turn, j) {
  turn.concl = conclHtml(j);
  turn.evid = evidHtml(j);
  turn.detail = detailOf(j);
  turn.gap = gapOf(turn.detail);
  turn.pids = pidsOf(j);
}

async function go() {
  const text = q.value.trim();
  if (!text) { UI.toast('先写一句问题'); return; }

  /* 多轮：把上一轮的「问句+解析摘要」与「命中结果集」一起带上。 */
  const carry = useParse.value && lastTurn;
  const ctxv = carry
    ? `上一问：${lastTurn.q}｜上一轮解析为：${lastTurn.spec}`.slice(0, 300) : '';
  const ctxPids = carry ? (lastTurn.pids || []).slice(0, 200) : [];   // 空数组 → api 不发送

  const turn = {
    question: text, ctx: !!ctxv, ctxN: ctxPids.length,
    concl: '', evid: '', detail: null, gap: '', pids: [],
    streaming: false, status: '', delta: '', done: false, error: ''
  };
  turns.value.push(turn);
  scrollBottom();

  const streaming = !!(useLlm.value || useArg.value) && typeof window.fetch === 'function';
  if (streaming) {
    turn.streaming = true;
    try {
      await api.askStream(text, {
        parse: useParse.value ? 1 : '',
        narrate: (useLlm.value || useArg.value) ? 1 : '',
        argument: useArg.value ? 1 : '',
        ctx: ctxv,
        ctx_pids: ctxPids
      }, (type, d) => {
        if (type === 'status') {
          turn.status = (d.text || '') + (d.model ? `（大模型：${d.model}）` : '');
        } else if (type === 'engine') {
          applyResult(turn, d);
          if (useLlm.value || useArg.value) {
            turn.status = `数字与证据已就绪（用时 ${d.ms || '…'} ms）；大模型正在补写${useArg.value ? '论证草稿' : '说明'}…`;
          }
          scrollBottom();
        } else if (type === 'delta') {
          turn.delta += (d.text || '');
          scrollBottom();
        } else if (type === 'final') {
          applyResult(turn, d);
          lastTurn = { q: text, spec: (typeof d.spec === 'string' ? d.spec : ''), pids: turn.pids };
          turn.delta = '';
          turn.streaming = false; turn.done = true;
          scrollBottom();
        } else if (type === 'error') {
          turn.error = d.error || '';
          turn.streaming = false; turn.done = true;
        }
      });
    } catch (e) {
      /* 流式不可用 → 退回普通端点（功能不降级，只少逐字效果） */
      try {
        const j = await api.ask(text, {
          parse: useParse.value ? 1 : '', narrate: 1, argument: useArg.value ? 1 : '',
          ctx: ctxv, ctx_pids: ctxPids
        });
        if (j && j.error) { turn.error = j.error; }
        else {
          applyResult(turn, j);
          lastTurn = { q: text, spec: (typeof j.spec === 'string' ? j.spec : ''), pids: turn.pids };
        }
      } catch (e2) {
        turn.error = String(e2);
      }
      turn.streaming = false; turn.done = true;
    }
    return;
  }

  /* 非流式 */
  turn.streaming = true;
  scrollBottom();
  try {
    const j = await api.ask(text, {
      parse: useParse.value ? 1 : '', narrate: (useLlm.value || useArg.value) ? 1 : '',
      argument: useArg.value ? 1 : '', ctx: ctxv, ctx_pids: ctxPids
    });
    if (j && j.error) { turn.error = j.error; }
    else {
      applyResult(turn, j);
      lastTurn = { q: text, spec: (typeof j.spec === 'string' ? j.spec : ''), pids: turn.pids };
    }
  } catch (e) {
    turn.error = String(e);
  }
  turn.streaming = false; turn.done = true;
  scrollBottom();
}

function pickExample(s) { q.value = s; go(); }

onMounted(async () => {
  try {
    const x = await api.llm();
    llmTag.value = x.available ? `大模型就绪：${x.model}` : '大模型未接入（按模板作答）';
  } catch (e) { llmTag.value = ''; }
  try { chips.value = await api.examples(); } catch (e) { chips.value = []; }
  /* 深链：?q= 自动提问 */
  const q0 = UI.query();
  if (q0.q) { q.value = q0.q; go(); }
});
</script>

<template>
  <AppShell active="ask" :online="true" data-note="本地引擎（data/corpus.db）" :stamp="stamp">
    <div class="card ask-intro">
      <h1>问我一句</h1>
      <p class="dim">可以这样问（点一下就填进输入框）：</p>
      <div id="chips">
        <span v-for="(s, i) in chips" :key="i" class="chip" :data-q="s" @click="pickExample(s)">{{ s }}</span>
      </div>
      <p class="dim">回答里的每一处数字都带证据块与出处（篇号 + 句序），可疑之处会明说，
        语料覆盖不到的问题会<b>拒答</b>而不是编。多轮提问会自动带上<b>上一轮的结果集</b>，
        这样「那里面……」这类指代才落得实。</p>
    </div>

    <div id="log" ref="logEl">
      <div v-if="!turns.length" class="empty">
        <p><b>还没有提问。</b></p>
        <p class="dim">点上面的例子，或直接在下方输入框写一句——例如「清 临江仙 仄声比例高于45%」。</p>
      </div>

      <article v-for="(t, idx) in turns" :key="idx" class="turn">
        <div class="q">
          问：{{ t.ctx ? '（承上一轮）' : '' }}{{ t.question }}
          <span v-if="t.ctxN" class="badge acc">已带上上一轮结果集 {{ t.ctxN }} 篇</span>
        </div>

        <div v-if="t.error" class="a err">
          <b class="bad">这一步没走通</b>
          <p>{{ t.error }}</p>
          <p class="dim">可试：① 确认本地服务在运行（python web/serve.py）；② 按 Ctrl+F5 强制刷新；
            ③ 换个说法再问一次。</p>
        </div>

        <div v-else class="a">
          <div v-if="t.gap" class="gap">{{ t.gap }}</div>

          <template v-if="t.concl">
            <div class="zone">
              <div class="zh">结论</div>
              <div class="ans" v-html="t.concl"></div>
            </div>
            <div v-if="t.evid" class="zone">
              <div class="zh">证据</div>
              <div class="ans" v-html="t.evid"></div>
            </div>
          </template>
          <p v-else class="loading"><span class="spin"></span> 正在检索语料并核算…（数字由本地引擎算出）</p>

          <div v-if="t.status" class="m">{{ t.status }}</div>

          <div v-if="t.delta" class="a delta">
            <b>说明</b>（大模型正在写；数字仍由引擎给，写完还要过四道护栏）<br>
            <span class="pre">{{ t.delta }}</span>
          </div>

          <details v-if="hasDetail(t.detail)" class="zone ud">
            <summary class="zh">理解详情</summary>
            <div class="u-body">
              <div v-if="t.detail.source" class="u-row">
                <b>解析来源</b><span>{{ t.detail.source }}</span></div>
              <div v-if="t.detail.spec" class="u-row">
                <b>查询理解</b><span>{{ t.detail.spec }}</span></div>
              <div v-if="t.detail.dropped.length" class="u-row">
                <b>丢弃字段</b><span>{{ fmtList(t.detail.dropped, '；') }}</span></div>
              <div v-if="t.detail.unparsed.length" class="u-row u-warn">
                <b>未理解片段</b><span>{{ fmtList(t.detail.unparsed, '、') }}</span></div>
              <div v-if="t.detail.verifyOk !== null" class="u-row">
                <b>护栏校验</b>
                <span :class="t.detail.verifyOk ? 'ok' : 'bad'">{{ t.detail.verifyOk ? '通过' : '未通过' }}</span>
              </div>
              <div v-if="t.detail.problems.length" class="u-row u-warn">
                <b>护栏问题</b><span>{{ fmtList(t.detail.problems, '；') }}</span>
              </div>
              <div v-if="t.detail.notes.length" class="u-row">
                <b>解析注记</b><span>{{ fmtList(t.detail.notes, '；') }}</span></div>
              <div v-if="t.detail.ctxPids && t.detail.ctxPids.received" class="u-row">
                <b>多轮结果集</b>
                <span>服务端收到 {{ t.detail.ctxPids.received }} 个篇号{{
                  t.detail.ctxPids.consumed ? '（理解层已消费）' : '（理解层暂未消费该参数）' }}</span>
              </div>
            </div>
          </details>
        </div>
      </article>
    </div>

    <div class="bar">
      <input id="q" v-model="q" style="width:min(560px,60%)"
             placeholder="例：清 临江仙 仄声比例高于45%" @keydown.enter="go">
      <button id="go" @click="go">提问</button>
      <label class="dim" style="margin-left:8px">
        <input type="checkbox" id="useParse" v-model="useParse"> 用大模型理解问句</label>
      <label class="dim" style="margin-left:8px">
        <input type="checkbox" id="useLlm" v-model="useLlm"> 让大模型写说明</label>
      <label class="dim" style="margin-left:6px">
        <input type="checkbox" id="useArg" v-model="useArg"> 论证辅助草稿</label>
      <span id="llmTag" class="dim" style="margin-left:8px">{{ llmTag }}</span>
    </div>
  </AppShell>
</template>

<style>
/* AskView.vue —— 问答页精修（2026-10-08）。**只作用于本页**（ask 页只挂本组件），
 * 配色沿用 core/ui.js 的 CSS 变量，不另起一套；不引入任何依赖。
 * 注意：回答正文/证据块由 core/ask.js 生成（v-html），scoped 样式覆盖不到，故此处用非 scoped。 */

/* 1) 输入区：控件用 flex 对齐，间距一致（改前各控件靠 inline margin 拼，窄屏易散） */
.bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.bar label { margin-left: 0 !important; }
.bar #go { padding: 6px 20px; font-weight: 600; letter-spacing: 1px; }

/* 2) 一轮问答：问句与答案拉开距离，便于竖向扫读 */
#log .turn { margin: 18px 0 0; }
#log .q { font-size: 15px; padding: 9px 12px; }
#log .q .badge { margin-left: 6px; vertical-align: 1px; }

/* 3) 空态：不再是一片空白 */
#log .empty { border: 1px dashed var(--line); border-radius: var(--r); padding: 18px;
  background: var(--panel2); text-align: center; margin: 12px 0; }
#log .empty p { margin: 4px 0; }

/* 4) 回答卡片：结论 / 证据 / 理解详情 三段各成一区（靠分区标题 + 左侧色条区分） */
#log .a { padding: 12px 14px; }
#log .zone { margin: 2px 0 10px; }
#log .zh { font-size: 12px; font-weight: 700; letter-spacing: 1.5px; color: var(--accent);
  border-bottom: 1px solid var(--line); padding-bottom: 4px; margin-bottom: 8px; }
/* 结论正文：去掉 core 的整块边框/底色，交给「区」来提供结构 */
#log .ans > .a { border: none; background: transparent; padding: 0; margin: 0; }
/* 证据块：左侧换成本项目强调色，和结论文本一眼区分 */
#log .ans > .e { border-left: 3px solid color-mix(in srgb, var(--accent2) 65%, transparent); }

/* 5) 加载 / 缺口 / 增量 / 出错：都要有明确文案与不刺眼的颜色 */
#log .loading { margin: 4px 0; color: var(--ink2); }
#log .gap { border-left: 4px solid var(--warn);
  background: color-mix(in srgb, var(--warn) 10%, transparent);
  padding: 8px 12px; border-radius: 6px; margin: 0 0 10px; font-size: 13.5px; }
#log .delta { background: var(--panel2); border-style: dashed; }
#log .delta .pre { white-space: pre-wrap; }
#log .err { border-left: 4px solid var(--warn); }
#log .err p { margin: 6px 0 0; }

/* 6) 理解详情：折叠区 + 「标签 / 值」两列，元信息不再挤成一行 */
#log details.ud { border: 1px dashed var(--line); border-radius: 8px; padding: 6px 10px;
  background: var(--panel2); }
#log details.ud > summary { cursor: pointer; list-style: none; }
#log details.ud > summary::-webkit-details-marker { display: none; }
#log details.ud > summary::before { content: '▸ '; color: var(--accent); }
#log details.ud[open] > summary::before { content: '▾ '; }
#log .u-body { margin-top: 8px; }
#log .u-row { display: grid; grid-template-columns: 88px 1fr; gap: 4px 10px;
  font-size: 13px; padding: 3px 0; border-top: 1px dashed var(--line); }
#log .u-row:first-child { border-top: none; }
#log .u-row > b { color: var(--ink2); font-weight: 600; }
#log .u-warn { color: var(--warn); }

/* 7) 窄屏不塌：底栏不再 sticky（避免遮住内容）、理解详情改单列 */
@media (max-width: 640px) {
  .bar { position: static; }
  #log .u-row { grid-template-columns: 1fr; }
}
</style>
