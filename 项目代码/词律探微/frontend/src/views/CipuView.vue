<template>
  <AppShell active="cipu" :stamp="stamp" :data-note="dataNote" :online="isOnline">
  <div class="cp">
    <div class="card">
      <h1>词谱对照</h1>
      <p class="lead">选一篇作品，系统自动匹配词牌的<b>谱书体式</b>，给出逐句
        <b>三行对照</b>：作品原字 / 谱书规范（平、仄、中）/ 谱书例词。
        每字给出「对 / 异 / 中」三分账——<b>「中」表示谱书未限定</b>，不判对错。</p>
      <p v-if="!isOnline" class="off-note">本页需要本地服务：请运行
        <code>python web/serve.py</code> 后从 <code>http://127.0.0.1:8000/cipu.html</code> 打开。</p>
    </div>

    <!-- ① 选作品 -->
    <div class="card">
      <h3>① 选作品</h3>
      <div class="cp-row">
        <input v-model="q.cipai" placeholder="词牌（如 浣溪沙）">
        <input v-model="q.author" placeholder="词人（可选）">
        <input v-model="q.title" placeholder="题名关键字（可选）">
        <button type="button" :disabled="!isOnline" @click="search">检索</button>
      </div>
      <p class="dim">或直接给篇号：
        <input v-model="pid" class="cp-pid" placeholder="pid（如 ci.清.0000.base.json#000103）">
        <button type="button" :disabled="!isOnline" @click="compareByPid">对照</button>
      </p>
      <table v-if="hits.length" class="cp-table">
        <thead><tr><th>词牌</th><th>题名</th><th>词人</th><th>句数</th><th>字数</th><th>仄声%</th><th></th></tr></thead>
        <tbody>
          <tr v-for="h in hits" :key="h.pid">
            <td>{{ h.cipai }}</td><td>{{ h.title || '—' }}</td><td>{{ h.author || '—' }}</td>
            <td class="num">{{ h.sent_n }}</td><td class="num">{{ h.han_len }}</td>
            <td class="num">{{ h.ze_ratio }}</td>
            <td><button type="button" class="mini" @click="pick(h)">对照</button></td>
          </tr>
        </tbody>
      </table>
      <p v-if="err" class="cp-err">✗ {{ err }}</p>
    </div>

    <!-- ② 体式 -->
    <div v-if="res" class="card">
      <h3>② 谱书体式 <small class="dim">（谱库共 {{ tuneCount }} 个词牌；当前作品词牌：{{ res.cipai }}）</small></h3>
      <p v-if="res.status !== 'ok'" class="cp-err">该词牌未在谱库中（可换一篇，或看下方候选）。</p>
      <template v-else>
        <!-- ★ 2026-10-10（竞品图2 对齐）：体式分「句数相合 / 其它」两组，各带来源头 -->
        <h4 v-if="formsMatched.length" class="dim">匹配的词谱（句数相合）</h4>
        <div class="cp-forms">
          <button v-for="f in formsMatched" :key="f.form" type="button"
                  :class="{ on: curForm === f.form }" @click="pickForm(f.form)">
            {{ f.authority || '体' }} {{ f.form }} · {{ f.n_lines }}句/{{ f.n_chars }}字
            <small v-if="f.header" class="dim">· {{ String(f.header).slice(0, 14) }}</small>
          </button>
        </div>
        <h4 v-if="formsOther.length" class="dim">其它词谱</h4>
        <div class="cp-forms">
          <button v-for="f in formsOther" :key="f.form" type="button"
                  :class="{ on: curForm === f.form }" @click="pickForm(f.form)">
            {{ f.authority || '体' }} {{ f.form }} · {{ f.n_lines }}句/{{ f.n_chars }}字
            <small v-if="f.header" class="dim">· {{ String(f.header).slice(0, 14) }}</small>
          </button>
        </div>
        <p v-if="formWhy" class="dim">自动选中理由：{{ formWhy }}</p>
        <p class="dim">本体来源：{{ curFormHeader || '—' }}</p>
      </template>
    </div>

    <!-- ③ 三行对照 -->
    <div v-if="res && res.status === 'ok'" class="card">
      <h3>③ 逐句三行对照</h3>
      <div class="cp-legend">
        <span><i class="sw match"></i>对（与规范一致）</span>
        <span><i class="sw mismatch"></i>异（与规范不符）</span>
        <span><i class="sw any"></i>中（谱书未限定，不判对错）</span>
        <span class="dim">　句末标记「韵」= 该句押韵位（据谱书例词标注）</span>
      </div>
      <div class="cp-stat">
        <span>字数 {{ s.n_cells }}</span><span class="ok">对 {{ s.n_match }}</span>
        <span class="bad">异 {{ s.n_mismatch }}</span><span class="dim">中 {{ s.n_any }}</span>
        <span class="dim">作品 {{ s.n_lines_poem }} 句 / 谱书 {{ s.n_lines_rule }} 句</span>
        <span v-if="(s.missing_lines || []).length" class="bad">缺句 {{ s.missing_lines.join('、') }}</span>
        <span v-if="(s.extra_lines || []).length" class="bad">多句 {{ s.extra_lines.join('、') }}</span>
      </div>
      <div v-for="row in rows" :key="row.line" class="cp-line">
        <div class="cp-no">第 {{ row.line + 1 }} 句<span v-if="row.ending" class="tag">韵</span>
          <small class="dim">例：{{ row.example || '—' }}</small></div>
        <!-- ★ 2026-10-10（竞品图2 对齐）：**逐字竖排三行**——原字 / 谱书规范 / 作品实际，
             每列一字上下对齐；实际行与规范不符的字标红。 -->
        <div class="cp-grid">
          <div v-for="c in row.cells" :key="c.pos" class="cp-col">
            <div class="cp-char">{{ c.char }}</div>
            <div class="cp-rulech" :class="{ any: c.rule === '中' }">{{ c.rule }}</div>
            <div class="cp-actual" :class="c.verdict">{{ c.pz || '·' }}</div>
          </div>
          <div v-if="row.n_chars_poem > row.n_chars_rule" class="cp-col extra">
            <div v-for="k in (row.n_chars_poem - row.n_chars_rule)" :key="'e' + k" class="cp-char dim">＋</div>
          </div>
          <div v-if="row.n_chars_rule > row.n_chars_poem" class="cp-col extra">
            <div v-for="k in (row.n_chars_rule - row.n_chars_poem)" :key="'m' + k" class="cp-rulech dim">缺</div>
          </div>
        </div>
        <div class="cp-meta dim">
          作品平仄 {{ row.poem_pz || '—' }}　｜　规范 {{ row.rule_tones || '—' }}
          <span v-if="row.n_chars_poem !== row.n_chars_rule" class="bad">（字数 {{ row.n_chars_poem }} vs 谱 {{ row.n_chars_rule }}）</span>
        </div>
      </div>
      <p class="cp-src">来源声明：{{ res.source_note }}</p>
    </div>
  </div>
  </AppShell>
</template>

<script setup>
/* CipuView.vue —— **词谱对照**（2026-10-10 竞品对照实现）。
 *
 * 与竞品「词谱比较」对齐的三件事，我们做得更实的三处：
 *   ① 逐字三分账（对/异/中）由后端 `cipu.compare` **一次算清**（引擎与谱书同一份预计算 pz），
 *      前端只做着色、不重算——不存在"显示与计算两套"；
 *   ② 体式可切换（`form` 参数），并给出**自动选中理由**（`form_why`）与**来源头**（header）；
 *   ③ 来源红线常驻（`source_note`：搜韵公开转写，未核原书）——不把谱书当定本。
 */
import { computed, ref } from 'vue';
import AppShell from '../components/AppShell.vue';
import { UI } from '../core/index.mjs';

const stamp = (typeof window !== 'undefined' && window.__STAMP__) || '';
const dataNote = '数字归引擎 · 文料归检索 · 说法归生成 · 出处归引用';
const isOnline = typeof window !== 'undefined' && !!window.fetch
  && !/^file:/i.test(window.location.href || '');

const q = ref({ cipai: '浣溪沙', author: '', title: '' });
const pid = ref('');
const hits = ref([]);
const res = ref(null);
const forms = ref([]);
const curForm = ref(null);
const err = ref('');
const tuneCount = ref(0);

const rows = computed(() => (res.value && res.value.rows) || []);
const s = computed(() => (res.value && res.value.summary) || {});
const formWhy = computed(() => (res.value && res.value.form_why) || '');
/* 体式分组：句数与作品相合的排前（竞品「匹配的词谱 / 其它词谱」） */
const formsMatched = computed(() => {
  const n = res.value && res.value.summary ? res.value.summary.n_lines_poem : null;
  return (n == null) ? [] : forms.value.filter(f => f.n_lines === n);
});
const formsOther = computed(() => {
  const n = res.value && res.value.summary ? res.value.summary.n_lines_poem : null;
  return (n == null) ? [] : forms.value.filter(f => f.n_lines !== n);
});
const curFormHeader = computed(() => {
  const f = (forms.value || []).find(x => x.form === curForm.value);
  return f ? (f.header || f.source_url || '') : '';
});

async function call(path) {
  const r = await fetch(path);
  const j = await r.json();
  if (!r.ok || j.error) throw new Error((j.error && j.error.message) || '请求未成功');
  return j;
}

async function loadTunes() {
  try {
    const j = await call('/api/cipu/list');
    tuneCount.value = (j.result || []).length;
  } catch (e) { /* 静默：谱库一览只是提示 */ }
}
loadTunes();

async function search() {
  err.value = ''; hits.value = [];
  const p = new URLSearchParams({ topk: '20' });
  if (q.value.cipai) p.set('cipai', q.value.cipai);
  if (q.value.author) p.set('author', q.value.author);
  if (q.value.title) p.set('title', q.value.title);
  try {
    const j = await call('/api/search?' + p.toString());
    // `/api/search` 的结果在 `rows`（带分页；这里只取前 20 条供挑选）
    hits.value = (j.rows || []).slice(0, 20);
    if (!hits.value.length) err.value = '没有命中，换个词牌或放宽条件';
  } catch (e) { err.value = String(e.message || e); }
}

function pick(h) { pid.value = h.pid; compareByPid(); }

async function compareByPid() {
  err.value = ''; res.value = null;
  if (!pid.value) { err.value = '先选一篇或填篇号'; return; }
  try {
    const p = new URLSearchParams({ pid: pid.value });
    if (curForm.value) p.set('form', String(curForm.value));
    const j = await call('/api/cipu/compare?' + p.toString());
    res.value = j.result || null;
    if (!res.value) { err.value = '没有这一篇'; return; }
    if (res.value.form) curForm.value = res.value.form.form;
    const tj = await call('/api/cipu?tune=' + encodeURIComponent(res.value.tune || ''));
    forms.value = ((tj.result || {}).forms) || [];
    if (!forms.value.length && res.value.form) forms.value = [res.value.form];
  } catch (e) { err.value = String(e.message || e); }
}

async function pickForm(f) { curForm.value = f; await compareByPid(); }

function tip(c) {
  return `第 ${c.pos + 1} 字「${c.char}」：作品 ${c.pz || '—'}／规范 ${c.rule}` +
    (c.verdict === 'any' ? '（谱书未限定）' : c.verdict === 'match' ? '（一致）' : '（不一致）');
}
</script>

<style>
.cp { max-width: 1080px; margin: 0 auto; padding: 12px; }
.cp-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.cp-row input { width: 160px; }
.cp-pid { width: 300px; }
.cp-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
.cp-table th, .cp-table td { border-bottom: 1px solid var(--bd, #ddd); padding: 4px 6px; text-align: left; }
.cp-table .num { text-align: right; }
.cp-err { color: #b00; }
.cp-forms { display: flex; gap: 6px; flex-wrap: wrap; margin: 6px 0; }
.cp-forms button.on { font-weight: 600; border-color: var(--ac, #666); }
.cp-legend { display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0; font-size: 13px; }
.cp-legend .sw { display: inline-block; width: 12px; height: 12px; margin-right: 4px; vertical-align: -2px; }
.sw.match, .cp-legend .sw.match { background: #dff0d8; border: 1px solid #9c9; }
.sw.mismatch, .cp-legend .sw.mismatch { background: #f8d7da; border: 1px solid #c99; }
.sw.any, .cp-legend .sw.any { background: #eee; border: 1px solid #bbb; }
.cp-stat { display: flex; gap: 10px; flex-wrap: wrap; margin: 6px 0; font-size: 13px; }
.cp-stat .ok { color: #2a7; } .cp-stat .bad { color: #b33; }
.cp-line { border-top: 1px solid var(--bd, #e5e5e5); padding: 8px 0; }
.cp-no { font-size: 13px; margin-bottom: 4px; }
.cp-no .tag { margin-left: 6px; padding: 0 4px; border: 1px solid #bbb; border-radius: 3px; font-size: 12px; }
.cp-grid { display: flex; flex-wrap: wrap; gap: 2px 0; margin: 4px 0; }
.cp-col { display: flex; flex-direction: column; align-items: center; min-width: 26px; }
.cp-col.extra { opacity: .55; }
.cp-char { font-size: 19px; line-height: 1.4; }
.cp-rulech { font-size: 13px; color: #555; }
.cp-rulech.any { color: #999; }
.cp-actual { font-size: 13px; }
.cp-actual.match { color: #2a7; }
.cp-actual.mismatch { color: #b33; font-weight: 600; }
.cp-actual.any { color: #888; }
.cp-meta { font-size: 12px; margin-top: 2px; }
.cp-src { margin-top: 8px; font-size: 12px; color: #a60; }
.off-note { color: #a60; }
.dim { color: #777; }
.mini { padding: 1px 6px; font-size: 12px; }
</style>
