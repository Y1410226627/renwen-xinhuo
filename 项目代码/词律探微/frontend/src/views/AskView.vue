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
import { ref, computed, onMounted, nextTick } from 'vue';
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
/* ─────────────── 对话式 UI 新增状态（2026-10-10，DeepSeek 式重构）───────────────
 * 旧「研究演示 / 应试作答」情景切换（mode/setMode/modeNote）已由 composer 里的
 * 三个 pill（深度理解 / 模型补写 / 论证草稿）承载——口径完全不变，只是入口更直接：
 * 论证草稿 ≙ 原 exam（useArg=1），只勾模型补写 ≙ 原 research（narrate=1）。 */
const taEl = ref(null);          // composer 输入框（自适应高度）
const speakingIdx = ref(-1);     // 正在朗读的轮次下标（-1 = 未在朗读）
/* 「发送中」：任一轮还在流式/请求中 → 发送按钮禁用（防连点重发）。 */
const busy = computed(() => turns.value.some((t) => t.streaming));

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
  q.value = '';                 // ⭐ 2026-10-09：切/建会话时清空输入框（主人实测驱动）
  persist();
  scrollBottom();
}

function switchSession(id) {
  if (id === activeId.value) { return; }
  activeId.value = id;
  loadActive();
  q.value = '';                 // ⭐ 2026-10-09：切会话清空输入框
  persist();
}

function delSession(id) {
  const i = sessions.value.findIndex((s) => s.id === id);
  if (i < 0) { return; }
  sessions.value.splice(i, 1);
  if (!sessions.value.length) { newSession(); return; }
  if (activeId.value === id) { activeId.value = sessions.value[0].id; loadActive(); }
  persist();
}

/* 左栏会话按「今天 / 昨天 / 更早」分组（DeepSeek 式）；空组不显示。
 * sessions 本身按最近更新在前维护（finishTurn 里上浮），组内保持该顺序。 */
const grouped = computed(() => {
  const d = new Date(); d.setHours(0, 0, 0, 0);
  const today = d.getTime();
  const yesterday = today - 86400000;
  const groups = [
    { label: '今天', items: [] },
    { label: '昨天', items: [] },
    { label: '更早', items: [] }
  ];
  for (const s of sessions.value) {
    if (s.ts >= today) { groups[0].items.push(s); }
    else if (s.ts >= yesterday) { groups[1].items.push(s); }
    else { groups[2].items.push(s); }
  }
  return groups.filter((g) => g.items.length);
});

/* ─────────────── 对话式交互工具（复制 / 朗读 / 重新生成 / 输入框自适应）─────────────── */

/* 输入框自适应高度：内容多时长高（上限 160px，超出内部滚动），清空后缩回一行。 */
function autoGrow() {
  const el = taEl.value;
  if (!el) { return; }
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

/* v-html → 纯文本（复制 / 朗读用）：不引依赖，用浏览器自带的解析。 */
function stripHtml(html) {
  if (typeof document === 'undefined') { return String(html || ''); }
  const d = document.createElement('div');
  d.innerHTML = String(html || '');
  return (d.textContent || '').replace(/\n{3,}/g, '\n\n').trim();
}

/* 剪贴板：优先 async API，降级 execCommand（file:// 等非安全上下文）。 */
function copyText(text) {
  if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  if (typeof document === 'undefined') { return Promise.reject(new Error('no document')); }
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } finally { ta.remove(); }
  return Promise.resolve();
}

/* 复制一轮回答：问句 + 结论 + 证据的纯文本（HTML 标签剥掉，粘贴即读）。 */
function copyAnswer(t) {
  const parts = [];
  if (t.question) { parts.push('问：' + t.question); }
  const concl = stripHtml(t.concl);
  const evid = stripHtml(t.evid);
  if (concl) { parts.push('答：' + concl); }
  if (evid) { parts.push('证据：' + evid); }
  if (!parts.length) { UI.toast('这一轮还没有可复制的内容'); return; }
  copyText(parts.join('\n\n')).then(
    () => UI.toast('已复制回答'),
    () => UI.toast('复制失败（浏览器未授权剪贴板）')
  );
}

/* 朗读：speechSynthesis（zh-CN）。再点一次 = 停止；读完自动复位按钮。
 * 内容 = 结论 + 证据的纯文本，截到 600 字（证据块太长时读主干）。 */
function speak(t, idx) {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    UI.toast('当前环境不支持朗读'); return;
  }
  if (speakingIdx.value === idx) {
    window.speechSynthesis.cancel();
    speakingIdx.value = -1;
    return;
  }
  const text = [stripHtml(t.concl), stripHtml(t.evid)].filter(Boolean).join('。').slice(0, 600);
  if (!text) { UI.toast('这一轮还没有可朗读的内容'); return; }
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'zh-CN';
  u.onend = () => { if (speakingIdx.value === idx) { speakingIdx.value = -1; } };
  u.onerror = () => { if (speakingIdx.value === idx) { speakingIdx.value = -1; } };
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
  speakingIdx.value = idx;
}

/* 重新生成：把那一轮的问题放回输入框并立即再问一遍（新开一轮，不覆盖旧答案）。 */
function regen(t) {
  if (!t || !t.question) { return; }
  q.value = t.question;
  autoGrow();
  go();
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
/* 2026-10-10（P2-1 引用环）：个人作品证据块走独立键 personal_evidence（不进 blocks/set_check），
   这里与语料 blocks 一起渲染到「证据」栏。 */
function evidHtml(j) {
  const b = ((j && j.blocks) || []).map(AskApp.blockHtml).join('');
  const pe = ((j && j.personal_evidence) || []).map(AskApp.blockHtml).join('');
  return b + pe;
}

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
  turn.raw = j;                    // 原样留一份，供「导出本轮 JSON」（不落 localStorage，见 slim）
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
  // ⚠ 2026-10-08 第二轮审查 §23：旧的 `sc.ok` 是**布尔**，「没做校验」与「做完且通过」
  //   都会让界面显示「通过」→ 用户以为系统已证明答案正确。现按后端**五态 status** 显示：
  //     VERIFIED_EXACT / VERIFIED_DERIVED → 证明到什么程度就说清楚；
  //     SEMANTIC_NOT_EXHAUSTIVE           → 明确「这类问题本就没有可判定的全集」；
  //     NOT_CHECKED                       → 明确「未验证」，禁止画 ✓；
  //     FAILED                            → 校验不通过。
  const st = String(sc.status || '');
  const txt = String(sc.status_text || sc.reason || '');
  if (!sc.checked) {
    out.push('集合身份校验：' + statusLabel(st) + (txt ? '（' + txt + '）' : ''));
    if (sc.reason && sc.reason !== txt) { out.push(sc.reason); }
    return out;
  }
  const tot = (typeof sc.hit_total === 'number') ? sc.hit_total : '—';
  out.push('集合身份校验：' + statusLabel(st)
    + '（独立复算命中 ' + tot + ' 篇；结果给出 ' + (sc.shown != null ? sc.shown : '—') + ' 篇）');
  if (sc.extra_n) { out.push('多出的（不在条件命中集内）' + sc.extra_n + ' 篇：' + fmtList(sc.extra, '、')); }
  if (sc.missing_n) { out.push('漏掉的（满足条件却未在结果中）' + sc.missing_n + ' 篇：' + fmtList(sc.missing, '、')); }
  if (sc.problems && sc.problems.length) { out.push('校验问题：' + fmtList(sc.problems, '；')); }
  if (sc.notes && sc.notes.length) { out.push('校验说明：' + fmtList(sc.notes, '；')); }
  return out;
}

/* 校验状态 → 徽标文案。**未验证的三种一律不给 ✓**。 */
function statusLabel(st) {
  switch (st) {
    case 'VERIFIED_EXACT': return '已验证（完整集合逐篇比对通过）';
    case 'VERIFIED_DERIVED': return '已验证（结果每篇都满足条件，为 top-k 子集）';
    case 'SEMANTIC_NOT_EXHAUSTIVE': return '未做集合校验（语义排序，本无可判定全集）';
    case 'NOT_CHECKED': return '未验证（本次未能执行校验）';
    case 'FAILED': return '未通过';
    default: return st || '未知';
  }
}

/* 分析级 JSON 导出（2026-10-09 新增）：把**本轮完整返回体**（数字/证据/护栏/理解详情全在内）
   原样导出，便于存档与复算。`raw` 只在内存里保留——单轮可达数百 KB，不进 localStorage
   （`slim()` 是白名单，天然不落盘）。 */
function exportTurn(t, idx) {
  if (!t || !t.raw) { UI.toast('这一轮还没有可导出的结果'); return; }
  UI.downloadJson('词律探微_问答第' + (idx + 1) + '轮.json', {
    generator: '词律探微 · 清代词律声情研究助手',
    note: '本文件是 /api/ask 的完整返回体（原样导出，未加工）；数字全部由本地引擎算出。',
    question: t.question,
    generated_at: new Date().toLocaleString(),
    result: t.raw
  });
  UI.toast('已导出本轮 JSON');
}

/* 会话追问范围：语义排序集要**明说**只在展示过的那几篇里找（第二轮审查 §22）。 */
function finishTurn(text) {
  const s = activeSession();
  if (s) {
    s.ts = nowTs();
    if (/^(新会话|（未命名）)$/.test(s.title)) { s.title = titleOf(text); }
  }
  /* 最近活跃的会话浮到列表最前（DeepSeek 式；sort 在主流引擎稳定，同 ts 不乱序）。 */
  sessions.value.sort((a, b) => b.ts - a.ts);
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
  /* ⭐ 2026-10-09 修（主人实测）：「每次输完问题之后，上一个问题还留在对话框里」——
     提交后**清空输入框**（对话式交互的标准行为）。此前 `q` 只读不清，
     且它是独立 ref（不属于会话存储）→ 换会话后旧文本仍在。 */
  q.value = '';
  autoGrow();                   // 清空后输入框缩回一行（自适应高度）
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

function pickExample(s) { q.value = s; autoGrow(); go(); }

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
    <div class="ask-shell">
      <!-- ★ 2026-10-10：**对话式布局**（对标 DeepSeek 截图逐细节）——
           左栏固定会话列表（开始新对话 / 今天·昨天·更早分组 / 选中高亮 / hover 删除 / 底部状态）；
           右主区对话流 + 底部粘性输入区（大输入框 + pill 开关 + 圆形发送）。 -->
      <aside class="side">
        <button class="newchat" @click="newSession">＋ 开始新对话</button>
        <div v-for="g in grouped" :key="g.label" class="sgroup">
          <div class="slabel dim">{{ g.label }}</div>
          <div v-for="s in g.items" :key="s.id" class="sitem" :class="{ on: s.id === activeId }"
               :title="s.title" @click="switchSession(s.id)">
            <span class="stitle">{{ s.title }}</span>
            <span class="sn dim">{{ (s.turns || []).length }}</span>
            <button class="sdel" title="删除该会话" @click.stop="delSession(s.id)">✕</button>
          </div>
        </div>
        <div class="sfoot dim">
          <div>本地 · 词律探微</div>
          <div class="sllm">{{ llmTag }}</div>
          <label class="carry"><input type="checkbox" v-model="carryOn"> 承上一轮结果集</label>
          <div class="dim" style="font-size:11.5px">不勾 = 每问独立（默认）；勾上才把上一轮的篇目范围带进来</div>
        </div>
      </aside>

      <section class="main">
        <div id="log" ref="logEl">
          <div v-if="!turns.length" class="empty">
            <h1>问我一句</h1>
            <p class="dim">可以这样问（点一下就填进输入框）——回答里的每一处数字都带证据块与出处
              （篇号 + 句序），可疑之处会明说，语料覆盖不到的问题会<b>拒答</b>而不是编。</p>
            <div id="chips">
              <span v-for="(s, i) in chips" :key="i" class="chip" :data-q="s" @click="pickExample(s)">{{ s }}</span>
            </div>
          </div>

          <article v-for="(t, idx) in turns" :key="idx" class="turn">
            <!-- 用户消息：右对齐气泡 -->
            <div class="u-msg">
              <span v-if="t.ctxN" class="badge acc">已带上一轮 {{ t.ctxN }} 篇</span>
              <span class="bubble">{{ t.ctx ? '（承上一轮）' : '' }}{{ t.question }}</span>
            </div>

            <!-- AI 回答：平铺无气泡 -->
            <div class="a-wrap">
              <div v-if="t.error" class="a err">
                <b class="bad">这一步没走通</b>
                <p>{{ t.error }}</p>
                <p class="dim">可试：① 确认本地服务在运行（python web/serve.py）；② 按 Ctrl+F5 强制刷新；
                  ③ 换个说法再问一次。</p>
              </div>

              <div v-else class="a">
                <div v-if="incompleteOf(t)" class="hardgate">
                  <b>这句话里的「{{ unparsedTextOf(t) }}」没能转成可执行条件</b>
                  <p>以下内容<b>不是</b>对该问题的回答（详见「执行详情」）。请换一种说法，或把它拆成
                    「词牌／词人／朝代／句脚字／声律模式／字数句数」这类可执行条件。</p>
                </div>
                <div v-if="truncNoteOf(t)" class="gap">{{ truncNoteOf(t) }}</div>
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

                <!-- ★ 「已思考（用时 N）」的对应物：**执行详情**可折叠——
                     本系统的"思考过程"是确定性执行链（路线/召回/校验），如实折叠展示 -->
                <details v-if="hasDetail(t.detail)" class="zone ud">
                  <summary class="zh">已执行（{{ t.detail.ms ? '用时 ' + t.detail.ms + ' ms' : '引擎链路' }}）</summary>
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
                      <b>执行注记</b><span>{{ fmtList(t.detail.notes, '；') }}</span></div>
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

                <!-- 操作图标行（DeepSeek 式）：复制 / 重新生成 / 朗读 / 导出 -->
                <div v-if="t.done && t.concl" class="acts">
                  <button class="mini ghost" type="button" @click="copyAnswer(t)">⧉ 复制回答</button>
                  <button class="mini ghost" type="button" @click="regen(t)">↻ 重新生成</button>
                  <button class="mini ghost" type="button" @click="speak(t, idx)">
                    {{ speakingIdx === idx ? '■ 停止朗读' : '▷ 朗读' }}</button>
                  <button v-if="t.raw" class="mini ghost" type="button" @click="exportTurn(t, idx)">⬇ 导出 JSON</button>
                </div>
              </div>
            </div>
          </article>
        </div>

        <!-- 底部输入区（粘性）：大输入框 + pill 开关 + 圆形发送 -->
        <div class="composer-wrap">
          <div class="composer">
            <textarea id="q" ref="taEl" v-model="q" rows="1"
                      placeholder="给词律探微发消息：例「清 临江仙 仄声比例高于45%」"
                      @keydown.enter.exact.prevent="go" @input="autoGrow"></textarea>
            <div class="crow">
              <div class="pills">
                <button type="button" class="pill" :class="{ on: useParse }"
                        @click="useParse = !useParse" title="先让大模型理解问句（条件经引擎校验）">◐ 深度理解</button>
                <button type="button" class="pill" :class="{ on: useLlm }"
                        @click="useLlm = !useLlm" title="在确定性结论之上让大模型补写说法">✎ 模型补写</button>
                <button type="button" class="pill" :class="{ on: useArg }"
                        @click="useArg = !useArg" title="论证口径：更严、依据分列">≡ 论证草稿</button>
              </div>
              <button id="go" class="send" :disabled="busy || !(q && q.trim())" @click="go"
                      title="发送（Enter）">↑</button>
            </div>
          </div>
          <div class="cfoot dim">数字归引擎 · 文料归检索 · 说法归生成 · 出处归引用——内容由本地引擎与大模型共同生成，请对照证据甄别</div>
        </div>
      </section>
    </div>
  </AppShell>
</template>

<style>
/* AskView.vue —— 问答页「对话式布局」精修（2026-10-10，对标 DeepSeek 逐细节）。
 * 只作用于本页（ask 页只挂本组件）；配色沿用 core/ui.js 的 CSS 变量，不另起一套；
 * 不引入任何依赖。回答正文/证据块由 core/ask.js 生成（v-html），scoped 样式覆盖不到，
 * 故此处用非 scoped——所有选择器都带 #log / .ask-shell / .composer 前缀收口，不外溢。 */

/* 0) 两栏骨架：左栏会话（sticky 跟随）+ 右主区（对话流 + 粘性 composer） */
.ask-shell { display: flex; align-items: flex-start; min-height: 62vh; }

/* 1) 左栏：会话列表（开始新对话 / 今天·昨天·更早分组 / 选中高亮 / hover 删除） */
.side { width: 250px; flex: none; position: sticky; top: 12px;
  max-height: calc(100vh - 28px); overflow: auto;
  display: flex; flex-direction: column;
  background: var(--panel2); border: 1px solid var(--line); border-radius: 12px; padding: 10px; }
.newchat { width: 100%; text-align: left; background: transparent; color: var(--ink);
  border: 1px solid var(--line); padding: 9px 12px; font-size: 14px; }
.newchat:hover { background: transparent; border-color: var(--accent); color: var(--accent); }
.sgroup { margin-top: 10px; }
.slabel { font-size: 11px; letter-spacing: 1.5px; padding: 2px 8px 5px; }
.sitem { display: flex; align-items: center; gap: 6px; padding: 7px 9px; border-radius: 8px;
  cursor: pointer; color: var(--ink); }
.sitem:hover { background: var(--panel3); }
.sitem.on { background: color-mix(in srgb, var(--accent) 13%, transparent); }
.sitem.on .stitle { color: var(--accent); font-weight: 600; }
.sitem .stitle { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; font-size: 13.5px; }
.sitem .sn { font-size: 11px; flex: none; }
.sdel { visibility: hidden; flex: none; background: none; border: none; padding: 0 3px;
  color: var(--ink2); font-size: 12px; cursor: pointer; }
.sitem:hover .sdel { visibility: visible; }
.sdel:hover { color: var(--warn); }
.sfoot { margin-top: auto; padding: 10px 8px 2px; border-top: 1px solid var(--line); line-height: 1.8; }
.sfoot .carry { display: inline-flex; align-items: center; gap: 4px; cursor: pointer; font-weight: 600; }

/* 2) 主区：对话流 + 粘性输入区 */
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; padding-left: 18px; }
#log { flex: 1; }
#log .turn { margin: 20px 0 0; }

/* 2a) 用户消息：右对齐气泡（问句用楷体，与 AI 回答一眼区分） */
.u-msg { display: flex; justify-content: flex-end; align-items: center; gap: 8px;
  margin: 4px 0 10px; }
.u-msg .bubble { background: var(--panel3); border: 1px solid var(--line);
  border-radius: 14px 14px 4px 14px; padding: 9px 14px; max-width: 76%;
  font-family: var(--kai); font-size: 15.5px; line-height: 1.75;
  white-space: pre-wrap; word-break: break-word; }
.a-wrap { margin: 0; }

/* 3) 空态 + 操作图标行（复制/重新生成/朗读/导出，DeepSeek 式轻量按钮） */
#log .empty { border: 1px dashed var(--line); border-radius: var(--r); padding: 18px;
  background: var(--panel2); text-align: center; margin: 12px 0; }
#log .empty p { margin: 4px 0; }
.acts { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.acts .mini { font-size: 12px; padding: 3px 10px; }

/* 4) 回答卡片：结论 / 证据 / 执行详情 三段各成一区（靠分区标题 + 左侧色条区分） */
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

/* 6) 执行详情：折叠区（「已思考」的对应物）+ 「标签 / 值」两列 */
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

/* 7) composer：粘性底部输入区（大输入框 + pill 开关 + 圆形发送，DeepSeek 式） */
.composer-wrap { position: sticky; bottom: 0; z-index: 6; padding: 16px 0 4px;
  background: linear-gradient(to top, var(--bg) 78%, transparent); }
.composer { background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
  padding: 10px 12px 8px; box-shadow: 0 8px 28px rgba(0, 0, 0, .08); }
.composer textarea { display: block; width: 100%; box-sizing: border-box;
  border: none; background: transparent; resize: none; outline: none;
  font-family: var(--song); font-size: 14.5px; line-height: 1.6; color: var(--ink);
  min-height: 26px; max-height: 160px; padding: 2px; }
.composer textarea:focus-visible { outline: none; }
.composer textarea::placeholder { color: var(--ink2); }
.crow { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
.pills { display: flex; flex-wrap: wrap; gap: 6px; flex: 1; min-width: 0; }
.pill { background: transparent; color: var(--ink2); border: 1px solid var(--line);
  border-radius: 999px; padding: 4px 12px; font-size: 12.5px; cursor: pointer;
  transition: color .12s, border-color .12s, background .12s; }
.pill:hover { border-color: var(--accent); color: var(--accent); background: transparent; }
.pill.on { background: color-mix(in srgb, var(--accent) 14%, transparent);
  border-color: var(--accent); color: var(--accent); }
.send { width: 36px; height: 36px; border-radius: 50%; padding: 0; flex: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 17px; line-height: 1; }
.send:disabled { opacity: .45; cursor: not-allowed; }
.cfoot { text-align: center; padding: 6px 0 2px; font-size: 11.5px; }

/* 8) 窄屏不塌：左栏隐藏（会话仍在 localStorage，宽屏可见），气泡放宽 */
@media (max-width: 900px) {
  .side { display: none; }
  .main { padding-left: 0; }
  .u-msg .bubble { max-width: 92%; }
  #log .u-row { grid-template-columns: 1fr; }
}
</style>
