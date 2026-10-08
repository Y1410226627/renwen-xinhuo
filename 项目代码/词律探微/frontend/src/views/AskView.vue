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
 *
 * ⚠ 2026-10-08 第二轮增强（外部架构审查 A/B，本轮交付）：
 *   ③ **取消 200 截断的语义破坏**：旧版下一轮 `ctx_pids = lastTurn.pids.slice(0, 200)`，
 *      200 是**语义截断**——上一轮命中 3000 首、下一轮问「其中字数最少的有哪些」，
 *      实际只在前 200 篇里找。现改为：每个会话带一个**服务端会话 id（sid）**，
 *      由服务端保存**完整**结果集并按指代分类（集合/单篇/继承）使用；`ctx_pids` 保留为
 *      服务端不可用时的**兜底**（≤200，界面明标「已降级」）；「上一轮 N 篇」按**真值**显示。
 *   ④ **如实提示截断**：服务端标记 `session.truncated` 时，界面**必须**说
 *      「上一轮结果过多，仅保留前 M 篇参与追问」——不许静默。
 *   ⑤ **集合身份校验（set_check）展示**：理解详情里展示「独立复算命中集 vs 返回集」的
 *      多出/漏掉/完整性；有则显示、无则隐藏。
 *   ⑥ **未理解硬门**：返回体 `understanding_status == 'UNDERSTANDING_INCOMPLETE'` 时，
 *      在回答卡片顶部用醒目条明确「这句话里的 X 没能转成可执行条件，以下不是对该问题的回答」。
 *      （后端已在正文给出一版文案——前端只做顶部醒目条，不重复正文。）
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
/* ⚠ 2026-10-08 新增：**是否「承上一轮」由用户显式决定，默认关闭**。
 *   旧版无条件带上上一轮的问句摘要与结果集 → 用户问一个**新问题**时范围会被悄悄收窄
 *   （主人实测反馈：「每次问下一个问题总会默认承上一轮，导致检索范围有误」）。
 *   `lastTurn` 仍始终记录（供勾选时使用），但**不勾就不发**。 */
const carryOn = ref(false);

/* ─────────────── 多会话（本地保存，可删除）───────────────
 * 目标：像大模型对话那样「一个会话一条线」，互不污染；会话存 localStorage，可新建 / 切换 / 删除。
 * 存储纪律：只存**能恢复视图的字段**（问题、结论/证据 HTML、理解详情、状态、篇号），
 *   不存函数与响应式包装；会话数与每会话轮数都设上限，避免把 localStorage 撑爆。 */
const SKEY = 'lvc_ask_sessions_v2';   // v2：每会话新增 sid（服务端会话 id）
const S_MAX = 30;               // 最多保留 30 个会话
const T_MAX = 60;               // 每个会话最多保留 60 轮
/* 本地持久化的 pid 上限（**只为兜底**：服务端会话才是完整集合的权威）。
 * 注意：这是**本地存储**的容量取舍，不是「把 200 当全部」——展示一律用真值 total。 */
const PERSIST_PIDS = 200;
const sessions = ref([]);       // [{ id, sid, title, ts, turns: [...] }]
const activeId = ref('');
const sessPanel = ref(false);   // 会话面板开关

function uid() { return 's' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
/* 服务端会话 id：与本地会话一一对应（本地删除会话时服务端那份由 LRU 自然淘汰）。 */
function newSid() { return 'sv' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8); }
function nowTs() { return Date.now(); }

function titleOf(text) {
  const t = String(text || '').replace(/\s+/g, ' ').trim();
  return t ? (t.length > 18 ? t.slice(0, 18) + '…' : t) : '（空问题）';
}

/* 精简一轮：只留能恢复视图的字段（HTML 直接存，重新打开即原样呈现）。
 * ⚠ 2026-10-08：`pids` 只做**兜底**存储（≤PERSIST_PIDS），**完整集合在服务端会话里**；
 *   展示用的篇数一律取真值 `total`，绝不拿截断后的长度冒充「上一轮 N 篇」。 */
function slim(t) {
  return {
    question: t.question || '', ctx: !!t.ctx, ctxN: t.ctxN || 0,
    concl: t.concl || '', evid: t.evid || '', detail: t.detail || null,
    gap: t.gap || '', pids: (t.pids || []).slice(0, PERSIST_PIDS),
    total: (typeof t.total === 'number') ? t.total : null,
    setCheck: t.setCheck || null, understanding: t.understanding || '',
    sess: t.sess || null,
    status: t.status || '', error: t.error || '',
    streaming: false, delta: '', done: true
  };
}

function persist() {
  try {
    localStorage.setItem(SKEY, JSON.stringify({
      active: activeId.value,
      sessions: sessions.value.slice(0, S_MAX).map((s) => ({
        id: s.id, sid: s.sid, title: s.title, ts: s.ts,
        turns: (s.turns || []).slice(-T_MAX).map(slim)
      }))
    }));
  } catch (e) { /* 配额满 / 隐私模式：静默降级（功能仍可用，只是不持久化） */ }
}

function restore() {
  try {
    const raw = localStorage.getItem(SKEY);
    if (!raw) { return false; }
    const o = JSON.parse(raw);
    if (!o || !Array.isArray(o.sessions) || !o.sessions.length) { return false; }
    sessions.value = o.sessions.map((s) => ({
      id: s.id || uid(), sid: s.sid || newSid(),
      title: s.title || '（未命名）', ts: s.ts || nowTs(),
      turns: (s.turns || []).map((t) => Object.assign({}, slim(t), { done: true, streaming: false }))
    }));
    activeId.value = sessions.value.some((s) => s.id === o.active) ? o.active : sessions.value[0].id;
    loadActive();
    return true;
  } catch (e) { return false; /* 存储损坏：当作全新开始 */ }
}

function activeSession() { return sessions.value.find((s) => s.id === activeId.value) || null; }

function loadActive() {
  const s = activeSession();
  turns.value = s ? s.turns : [];
  // 恢复「承上一轮」所需上下文：取最后一轮的问句与篇号（解析摘要不持久化，留空即可）
  const last = turns.value.length ? turns.value[turns.value.length - 1] : null;
  lastTurn = last ? { q: last.question, spec: '', pids: (last.pids || []) } : null;
  scrollBottom();
}

function newSession() {
  const s = { id: uid(), sid: newSid(), title: '新会话', ts: nowTs(), turns: [] };
  sessions.value.unshift(s);
  if (sessions.value.length > S_MAX) { sessions.value.length = S_MAX; }
  activeId.value = s.id;
  turns.value = [];
  lastTurn = null;
  persist();
  sessPanel.value = false;
  scrollBottom();
}

function switchSession(id) {
  if (id === activeId.value) { sessPanel.value = false; return; }
  activeId.value = id;
  loadActive();
  persist();
  sessPanel.value = false;
}

function delSession(id) {
  const i = sessions.value.findIndex((s) => s.id === id);
  if (i < 0) { return; }
  sessions.value.splice(i, 1);
  if (!sessions.value.length) { newSession(); return; }
  if (activeId.value === id) { activeId.value = sessions.value[0].id; loadActive(); }
  persist();
}

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
   （先读实际返回结构再写：/api/ask 的证据块里确有 pid）。
 * ⚠ 2026-10-08：**不再截到 200**。旧版 `slice(0,200)` 是**语义截断**——上一轮命中 3000 首时，
 *   下一轮「其中最短的」只在**前 200 篇**里找。现保留全量（服务端会话另有完整权威集合）。 */
function pidsOf(j) {
  if (!j || typeof j !== 'object') { return []; }
  const list = Array.isArray(j.pids) ? j.pids : ((j.blocks || []).map((b) => b && b.pid));
  const out = []; const seen = Object.create(null);
  for (const p of list) {
    if (typeof p === 'string' && p && !seen[p]) { seen[p] = 1; out.push(p); }
  }
  return out;
}

/* 本轮「命中篇数」的**真值**：优先后端 total（真值，不是 top-k），否则退回篇号个数。 */
function totalOf(j) {
  if (j && typeof j.total === 'number') { return j.total; }
  return null;
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
  const sc = (j.set_check && typeof j.set_check === 'object') ? j.set_check : null;
  const se = (j.session && typeof j.session === 'object') ? j.session : null;
  return {
    source: j.parse_source || j.source || '',
    spec: spec,
    dropped: Array.isArray(j.parse_dropped) ? j.parse_dropped : [],
    unparsed: Array.isArray(j.unparsed) ? j.unparsed : [],
    notes: Array.isArray(j.parse_notes) ? j.parse_notes : [],
    verifyOk: (typeof v.ok === 'boolean') ? v.ok : null,
    problems: Array.isArray(v.problems) ? v.problems : [],
    ctxPids: (cp && typeof cp.received === 'number') ? cp : null,
    total: (typeof j.total === 'number') ? j.total : null,
    setCheck: sc,                                   // 集合身份校验（外部审查 B）
    understanding: String(j.understanding_status || ''),
    sess: se
  };
}

function hasDetail(d) {
  return !!d && !!(d.source || d.spec || d.dropped.length || d.unparsed.length
    || d.notes.length || d.problems.length || d.verifyOk !== null
    || d.setCheck || (d.ctxPids && d.ctxPids.received > 0));
}

/* 语义缺口：有「没被理解的片段」且「没形成任何条件」（total 为空 → 按词面相关度兜底）时，
   用一句话说清楚——绝不把相关度排序伪装成答案。 */
function gapOf(d) {
  if (!d || !d.unparsed.length || d.total !== null) { return ''; }
  return '注意：这句话里的「' + d.unparsed.join('、')
    + '」没能转成可执行条件；以下按词面相关度排序展示的内容，不是对该问题的回答。';
}

/* 把一次返回体落到某一轮上（结论/证据/理解详情/缺口/篇号/校验/会话）。 */
function applyResult(turn, j) {
  turn.concl = conclHtml(j);
  turn.evid = evidHtml(j);
  turn.detail = detailOf(j);
  turn.gap = gapOf(turn.detail);
  turn.pids = pidsOf(j);
  turn.total = totalOf(j);
  turn.setCheck = (turn.detail && turn.detail.setCheck) || null;
  turn.understanding = (turn.detail && turn.detail.understanding) || '';
  turn.sess = (turn.detail && turn.detail.sess) || null;
}

/* 一次返回体 → 落盘到某一轮，并把**服务端会话**用了多少篇（指代承接情况）同步回界面。 */
function afterResult(turn, j, text) {
  applyResult(turn, j);
  const se = turn.sess;
  if (se) {
    if (typeof se.pids_used === 'number') { turn.ctxN = se.pids_used; }
    turn.ctx = !!se.used_context;
  }
  lastTurn = { q: text, spec: (j && typeof j.spec === 'string' ? j.spec : ''), pids: turn.pids };
}

/* ⑥ **未理解硬门**（外部审查 C）：返回体 `understanding_status == 'UNDERSTANDING_INCOMPLETE'`
 *   时，顶部出醒目条。后端正文已有一版文案，这里**只做顶部拦截条**，不重复正文。 */
function incompleteOf(turn) {
  return !!(turn && turn.understanding === 'UNDERSTANDING_INCOMPLETE');
}

/* 未理解片段的可读文本（供顶部硬门条点名「是哪一段没被理解」）。 */
function unparsedTextOf(turn) {
  const u = (turn && turn.detail && turn.detail.unparsed) || [];
  return u.length ? u.join('、') : '其中一部分';
}

/* ④ **如实提示截断**：服务端标记 `session.truncated` 时明说「仅保留前 M 篇参与追问」。 */
function truncNoteOf(turn) {
  const s = turn && turn.sess;
  if (!s || !s.truncated) { return ''; }
  const m = (typeof s.stored_pids === 'number') ? s.stored_pids : '若干';
  const n = (typeof s.result_total === 'number') ? s.result_total : '更多';
  return '上一轮结果过多（共 ' + n + ' 篇），仅保留前 ' + m + ' 篇参与追问——后续「其中…」只会在这 '
    + m + ' 篇内检索。';
}

/* 集合指代歧义 / 集合落空等，服务端如实给出的会话注记。 */
function sessNoteOf(turn) {
  const s = turn && turn.sess;
  return (s && s.note) ? String(s.note) : '';
}

/* set_check → 人可读行（有则显示、无则隐藏）。 */
function setCheckLines(sc) {
  if (!sc || typeof sc !== 'object') { return []; }
  const out = [];
  if (sc.checked === false) {
    out.push('集合身份校验：未执行（' + (sc.reason || '无硬条件') + '）');
    return out;
  }
  const tot = (typeof sc.hit_total === 'number') ? sc.hit_total : '—';
  out.push('集合身份校验：' + (sc.ok ? '通过' : '未通过')
    + '（独立复算命中 ' + tot + ' 篇；结果给出 ' + (sc.shown != null ? sc.shown : '—') + ' 篇）');
  if (sc.extra_n) { out.push('多出的（不在条件命中集内）' + sc.extra_n + ' 篇：' + fmtList(sc.extra, '、')); }
  if (sc.missing_n) { out.push('漏掉的（满足条件却未在结果中）' + sc.missing_n + ' 篇：' + fmtList(sc.missing, '、')); }
  if (sc.problems && sc.problems.length) { out.push('校验问题：' + fmtList(sc.problems, '；')); }
  if (sc.notes && sc.notes.length) { out.push('校验说明：' + fmtList(sc.notes, '；')); }
  return out;
}

/* 一轮结束后的收尾：更新会话标题（首轮取问句前 18 字）并落盘。 */
function finishTurn(text) {
  const s = activeSession();
  if (s) {
    s.ts = nowTs();
    if (/^(新会话|（未命名）)$/.test(s.title)) { s.title = titleOf(text); }
  }
  persist();
}

async function go() {
  const text = q.value.trim();
  if (!text) { UI.toast('先写一句问题'); return; }

  /* ── 多轮（2026-10-08 重构，外部审查 A）──
   * 主通路：把本会话的**服务端会话 id（sid）**随请求发出。服务端据此持有**完整**结果集，
   *   并按「集合指代 / 单篇指代 / 条件继承」自动决定承接方式 —— 不再由前端把 pid 截到 200。
   * 兜底通路（保留、不删）：仅当**用户显式勾选「承上一轮结果集」**时，附上上一轮的
   *   「问句摘要 + ≤200 篇号」；服务端会话不可用（sid 无历史）时才用得上，界面会明标降级。 */
  const cur = activeSession();
  const sid = cur ? cur.sid : '';
  const carryOnNow = !!(useParse.value && carryOn.value && lastTurn);
  const ctxv = carryOnNow
    ? `上一问：${lastTurn.q}｜上一轮解析为：${lastTurn.spec}`.slice(0, 300) : '';
  const ctxPids = carryOnNow ? (lastTurn.pids || []).slice(0, PERSIST_PIDS) : [];

  turns.value.push({
    question: text, ctx: carryOnNow, ctxN: ctxPids.length,
    concl: '', evid: '', detail: null, gap: '', pids: [],
    total: null, setCheck: null, understanding: '', sess: null,
    streaming: false, status: '', delta: '', done: false, error: ''
  });
  /* ⚠⚠ 关键修复（2026-10-08，主人实测「问完必须按一下退格键才显示答案」）：
   *   Vue3 的响应式是**惰性代理** —— `turns.value.push(obj)` 之后，`turns.value[n]` 才是**代理**，
   *   而刚才那个对象仍是**原始对象**。对原始对象赋值**不经过代理 setter** → **不触发重渲染** →
   *   界面一直停在「正在检索语料并核算…」，直到用户敲一下退格键改了 `q.value` 才引发重渲染，
   *   把早已算好的结果「突然」显示出来。
   *   修法：**push 之后从数组取回代理**，后续所有赋值都走它（依赖追踪才能正常工作）。
   *   （已用 @vue/reactivity 做确定性验证：改原始对象渲染增量 0；改代理增量 1。） */
  const turn = turns.value[turns.value.length - 1];
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
        ctx_pids: ctxPids,
        sid: sid,
        carry: carryOn.value ? 1 : ''
      }, (type, d) => {
        if (type === 'status') {
          turn.status = (d.text || '') + (d.model ? `（大模型：${d.model}）` : '');
        } else if (type === 'engine') {
          afterResult(turn, d, text);
          if (useLlm.value || useArg.value) {
            turn.status = `数字与证据已就绪（用时 ${d.ms || '…'} ms）；大模型正在补写${useArg.value ? '论证草稿' : '说明'}…`;
          }
          scrollBottom();
        } else if (type === 'delta') {
          turn.delta += (d.text || '');
          scrollBottom();
        } else if (type === 'final') {
          afterResult(turn, d, text);
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
          ctx: ctxv, ctx_pids: ctxPids, sid: sid, carry: carryOn.value ? 1 : ''
        });
        if (j && j.error) { turn.error = j.error; }
        else { afterResult(turn, j, text); }
      } catch (e2) {
        turn.error = String(e2);
      }
      turn.streaming = false; turn.done = true;
    }
    finishTurn(text);
    return;
  }

  /* 非流式 */
  turn.streaming = true;
  scrollBottom();
  try {
    const j = await api.ask(text, {
      parse: useParse.value ? 1 : '', narrate: (useLlm.value || useArg.value) ? 1 : '',
      argument: useArg.value ? 1 : '', ctx: ctxv, ctx_pids: ctxPids,
      sid: sid, carry: carryOn.value ? 1 : ''
    });
    if (j && j.error) { turn.error = j.error; }
    else { afterResult(turn, j, text); }
  } catch (e) {
    turn.error = String(e);
  }
  turn.streaming = false; turn.done = true;
  scrollBottom();
  finishTurn(text);
}

function pickExample(s) { q.value = s; go(); }

onMounted(async () => {
  /* 会话：先从 localStorage 恢复；没有（或存储损坏）就开一个新的。 */
  if (!restore()) { newSession(); }
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
    <!-- 会话栏：多会话（本地保存）、可新建 / 切换 / 删除；「承上一轮」默认关闭，由用户显式勾选 -->
    <div class="card sess">
      <div class="sess-head">
        <button class="ghost" @click="sessPanel = !sessPanel">
          {{ sessPanel ? '收起会话' : '会话' }}（{{ sessions.length }}）
        </button>
        <span class="sess-cur">{{ (activeSession() && activeSession().title) || '新会话' }}</span>
        <button class="ghost" @click="newSession">＋ 新会话</button>
        <label class="dim carry">
          <input type="checkbox" v-model="carryOn"> 承上一轮结果集
        </label>
        <span class="dim sess-hint">不勾 = 每问独立（默认）；勾上才把上一轮的篇目范围带进来</span>
      </div>
      <ul v-if="sessPanel" class="sess-list">
        <li v-for="s in sessions" :key="s.id" :class="{ on: s.id === activeId }">
          <a href="#" @click.prevent="switchSession(s.id)">{{ s.title }}</a>
          <span class="dim">{{ (s.turns || []).length }} 轮</span>
          <button class="ghost del" title="删除该会话" @click="delSession(s.id)">删除</button>
        </li>
      </ul>
    </div>

    <div class="card ask-intro">
      <h1>问我一句</h1>
      <p class="dim">可以这样问（点一下就填进输入框）：</p>
      <div id="chips">
        <span v-for="(s, i) in chips" :key="i" class="chip" :data-q="s" @click="pickExample(s)">{{ s }}</span>
      </div>
      <p class="dim">回答里的每一处数字都带证据块与出处（篇号 + 句序），可疑之处会明说，
        语料覆盖不到的问题会<b>拒答</b>而不是编。多轮提问由<b>服务端会话</b>保存上一轮的
        <b>完整</b>结果集，「其中…」「那首…」这类指代才会落到真实集合上（若结果过大被截，
        界面会如实说明保留了多少篇）。</p>
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
          <!-- ⑥ 未理解硬门：顶部醒目条（后端正文另有一版文案，这里不重复正文） -->
          <div v-if="incompleteOf(t)" class="hardgate">
            <b>这句话里的「{{ unparsedTextOf(t) }}」没能转成可执行条件</b>
            <p>以下内容<b>不是</b>对该问题的回答（详见「理解详情」）。请换一种说法，或把它拆成
              「词牌／词人／朝代／句脚字／声律模式／字数句数」这类可执行条件。</p>
          </div>
          <!-- ④ 如实提示截断：服务端标记 truncated 时必说 -->
          <div v-if="truncNoteOf(t)" class="gap">{{ truncNoteOf(t) }}</div>
          <!-- 指代歧义 / 集合落空等会话注记 -->
          <div v-if="sessNoteOf(t)" class="gap">{{ sessNoteOf(t) }}</div>
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
                <span>本轮把 {{ t.detail.ctxPids.received }} 个篇号作为范围交给检索{{
                  t.detail.ctxPids.from_session ? '（来自服务端会话）' : '（来自前端兜底）' }}，{{
                  t.detail.ctxPids.consumed ? '检索层已消费' : '检索层暂未消费该参数' }}</span>
              </div>
              <div v-if="t.detail.sess && t.detail.sess.used_context" class="u-row">
                <b>会话承接</b>
                <span>指代类型 {{ t.detail.sess.ref_kind }}；本轮锁定 {{ t.detail.sess.pids_used }} 篇{{
                  t.detail.sess.from_fallback ? '（降级：前端兜底）' : '（服务端完整集合）' }}</span>
              </div>
              <div v-if="t.setCheck" class="u-row">
                <b>集合校验</b>
                <span :class="t.setCheck.ok ? 'ok' : 'bad'">{{ t.setCheck.ok ? '通过' : '未通过' }}</span>
              </div>
              <div v-if="t.setCheck && setCheckLines(t.setCheck).length" class="u-row">
                <b>校验明细</b>
                <div>
                  <div v-for="(ln, i) in setCheckLines(t.setCheck)" :key="'scl' + i">{{ ln }}</div>
                </div>
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

/* 0) 会话栏（多会话，本地保存；可新建/切换/删除，「承上一轮」默认关闭） */
.sess { padding: 10px 14px; margin-bottom: 10px; }
.sess-head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.sess-cur { font-weight: 600; color: var(--accent); }
.sess-hint { font-size: 12.5px; }
.sess .carry { display: inline-flex; align-items: center; gap: 4px; font-weight: 600; }
.sess-list { list-style: none; margin: 10px 0 0; padding: 0; border-top: 1px dashed var(--line); }
.sess-list li { display: flex; align-items: center; gap: 10px; padding: 6px 2px;
  border-bottom: 1px dashed var(--line); }
.sess-list li.on a { font-weight: 700; color: var(--accent); }
.sess-list a { color: var(--ink); text-decoration: none; flex: 1; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; }
.sess-list .del { margin-left: auto; }

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
/* ⑥ 未理解硬门：顶部醒目条（比 .gap 更重：整块底色 + 左侧粗条 + 加粗标题） */
#log .hardgate { border: 1px solid color-mix(in srgb, var(--warn) 55%, transparent);
  border-left: 6px solid var(--warn);
  background: color-mix(in srgb, var(--warn) 16%, transparent);
  padding: 10px 12px; border-radius: 8px; margin: 0 0 10px; }
#log .hardgate b { color: var(--warn); }
#log .hardgate p { margin: 6px 0 0; font-size: 13.5px; }
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
  .sess-hint { display: none; }
}
</style>
