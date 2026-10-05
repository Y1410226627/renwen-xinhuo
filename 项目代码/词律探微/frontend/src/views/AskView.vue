<script setup>
/* AskView.vue —— 「声情问答」视图（在线，走 /api/*）。
 *
 * 分工（贯穿全项目）：**数字归引擎、说法归大模型、出处归引用**。
 * 本组件只负责「交互与摆结构」：把问题发出去、把返回的 JSON 摆成人能读的样子、
 * 把「护栏校验 / 查询理解来源 / 命中总数 / 表述来源 / 大模型是否就绪 / 八态结论理由」如实显示。
 * 结果块的 HTML 由 core/ask.js 的 askHtml/blockHtml 生成 —— 与旧页面、node 门禁**同一份实现**。
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
const turns = ref([]);          // [{ question, html, streaming, status, delta }]
let lastTurn = null;

/* 页面生成时间探针（由服务端在返回 HTML 时替换 @@STAMP@@ 注入）。 */
const stamp = ref('');
if (typeof window !== 'undefined' && window.__STAMP__) { stamp.value = String(window.__STAMP__); }

const logEl = ref(null);

function scrollBottom() {
  nextTick(() => { if (logEl.value) { logEl.value.scrollTop = logEl.value.scrollHeight; } });
}

/* 用 core/ask.js 生成结果块 HTML（字符串契约与旧版一致） */
function askHtmlOf(j) { return AskApp.askHtml(j); }

async function go() {
  const text = q.value.trim();
  if (!text) { UI.toast('先写一句问题'); return; }
  const ctxv = (useParse.value && lastTurn)
    ? `上一问：${lastTurn.q}｜上一轮解析为：${lastTurn.spec}`.slice(0, 300) : '';

  const turn = {
    question: text, ctx: !!ctxv, html: '', streaming: false,
    status: '', delta: '', done: false, error: ''
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
        ctx: ctxv
      }, (type, d) => {
        if (type === 'status') {
          turn.status = (d.text || '') + (d.model ? `（大模型：${d.model}）` : '');
        } else if (type === 'engine') {
          turn.html = askHtmlOf(d);
          if (useLlm.value || useArg.value) {
            turn.status = `数字与证据已就绪（用时 ${d.ms || '…'} ms）；大模型正在补写${useArg.value ? '论证草稿' : '说明'}…`;
          }
          scrollBottom();
        } else if (type === 'delta') {
          turn.delta += (d.text || '');
          scrollBottom();
        } else if (type === 'final') {
          if (d.spec) { lastTurn = { q: text, spec: (typeof d.spec === 'string' ? d.spec : '') }; }
          turn.html = askHtmlOf(d);
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
          parse: useParse.value ? 1 : '', narrate: 1, argument: useArg.value ? 1 : '', ctx: ctxv
        });
        if (j && j.spec) { lastTurn = { q: text, spec: (typeof j.spec === 'string' ? j.spec : '') }; }
        turn.html = j && j.error ? AskApp.renderErrorHtml(j.error) : askHtmlOf(j);
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
      argument: useArg.value ? 1 : '', ctx: ctxv
    });
    if (j && j.spec) { lastTurn = { q: text, spec: (typeof j.spec === 'string' ? j.spec : '') }; }
    turn.html = j && j.error ? AskApp.renderErrorHtml(j.error) : askHtmlOf(j);
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
    <div class="card">
      <h1>问我一句</h1>
      <p class="dim">可以这样问（点一下就填进输入框）：</p>
      <div id="chips">
        <span v-for="(s, i) in chips" :key="i" class="chip" :data-q="s" @click="pickExample(s)">{{ s }}</span>
      </div>
      <p class="dim">回答里的每一处数字都带证据块与出处（篇号 + 句序），可疑之处会明说，
        语料覆盖不到的问题会<b>拒答</b>而不是编。</p>
    </div>

    <div id="log" ref="logEl">
      <template v-for="(t, idx) in turns" :key="idx">
        <div class="q">问：{{ t.ctx ? '（承上一轮）' : '' }}{{ t.question }}</div>
        <div v-if="t.error" class="a"><span class="bad">出错了：{{ t.error }}</span></div>
        <div v-else class="a">
          <div v-if="t.html" v-html="t.html"></div>
          <template v-else>
            <span class="spin"></span> 正在检索语料并核算…
          </template>
          <div v-if="t.status" class="m">{{ t.status }}</div>
          <div v-if="t.delta" class="a" style="background:var(--panel2)">
            <b>说明</b>（大模型正在写；数字仍由引擎给，写完还要过四道护栏）<br>
            <span style="white-space:pre-wrap">{{ t.delta }}</span>
          </div>
        </div>
      </template>
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
