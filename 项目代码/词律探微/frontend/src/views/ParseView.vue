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
 *
 * ⚠ 2026-10-08 精修（本轮交付）：① 加载/错误/空态各有明确文案（三态互斥，不再出现空白或永远转圈）；
 *   ② 结果表可点列头**对当前页**排序（纯前端，明确标注「仅当前页」，不动后端分页/排序语义）；
 *   ③ 每行加「复制 pid」、页头加「复制条件摘要」；④ 输入框 Enter 即检索、Esc 清错误；
 *   ⑤ CSV 顶部加一行「条件摘要 + 命中数 + 范围 + 生成时间」元信息；
 *   ⑥ 条件写入 URL（history.replaceState，保留既有 ?pid=，file:// 下自动跳过）——刷新不丢条件。
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
/* 字位候选（竞品「逐字研读」对应能力，2026-10-10）：
   点详情区任一汉字 → 取它的（句序, 字位）→ 拉候选 → 可人工选读 / 撤回。
   选读走**决策事件**（研究库），可回溯、可撤回，不改字级基线表。 */
const cand = ref(null);
const candErr = ref('');
const curDetailPid = ref('');
const whereSql = ref('');
const orderBy = ref('');
const cnt = ref(0);
const lastHits = ref([]);        // 供导出 CSV
let lastCond = {};

/* ⚠ 2026-10-08 精修（本轮交付）——把「状态」显式化，空态/加载态/错误态各有明确文案，
 *   不再让错误挤在成功元信息行里、也不出现「永远转圈」：
 *     · loadMsg 有值 → 加载态（带 spinner + 在做什么）；
 *     · errMsg  有值 → 错误态（原因 + 三步处置，Esc 可清）；
 *     · searched && 无加载无错误 && total=0 → 空态（给下一步提示，而不是一张空表）。
 *   三个 ref 互斥渲染，见模板。 */
const loadMsg = ref('');
const errMsg = ref('');
const searched = ref(false);     // 是否已跑过至少一次检索（避免首屏未跑就报「空态」）

/* 前端排序（仅排**当前页**已渲染的行，不改后端、不影响 /api/search 的分页与排序语义）：
 *   点列头在 升/降 间切换；列头右侧箭头如实标注方向；页面上另有一句「本页已排序」的提示，
 *   不把「本页排序」伪装成「全库排序」。 */
const sortKey = ref('');
const sortDir = ref('asc');
const COLS_KEYS = ['author', 'title', 'cipai', 'sent', 'len', 'ze', 'scene'];
function cellOf(it, k) {
  const r = it.row, m = it.info.metrics;
  if (k === 'author') { return r[2]; }
  if (k === 'title') { return r[4]; }
  if (k === 'cipai') { return r[3]; }
  if (k === 'scene') { return m.scene; }
  if (k === 'sent') { return m.sent_n; }
  if (k === 'len') { return m.han_len; }
  if (k === 'ze') { return m.ze_ratio; }
  return '';
}
const sortedRows = computed(() => {
  const base = rows.value.slice();
  const k = sortKey.value;
  if (!k) { return base; }
  const sign = sortDir.value === 'desc' ? -1 : 1;
  return base.sort((a, b) => {
    const x = cellOf(a, k), y = cellOf(b, k);
    if (typeof x === 'number' && typeof y === 'number') {
      return sign * (x - y) || (a.row[0] < b.row[0] ? -1 : a.row[0] > b.row[0] ? 1 : 0);
    }
    const sx = String(x), sy = String(y);
    return sign * (sx < sy ? -1 : sx > sy ? 1 : 0);
  });
});
const sortLabel = computed(() => {
  if (!sortKey.value) { return ''; }
  const names = { author: '词人', title: '题名', cipai: '词牌', sent: '句数', len: '字数', ze: '仄比', scene: '声情' };
  return `本页已按「${names[sortKey.value] || sortKey.value}」${sortDir.value === 'asc' ? '升序' : '降序'}排列`;
});
function clickSort(k) {
  if (COLS_KEYS.indexOf(k) < 0) { return; }
  if (sortKey.value === k) { sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'; }
  else { sortKey.value = k; sortDir.value = 'asc'; }
}
function sortInd(k) { return sortKey.value === k ? (sortDir.value === 'asc' ? '▲' : '▼') : ''; }

/* 空态：跑过检索、没在加载、没有错误、命中又为 0 —— 才提示「下一步怎么做」。 */
const noHit = computed(() => searched.value && !loadMsg.value && !errMsg.value && total.value === 0);

/* 复制到剪贴板：优先 navigator.clipboard（https/localhost），退回 textarea + execCommand
 *   （file:// 双击打开时 clipboard 常不可用）。两条路都失败才 toast 报错。 */
async function copyText(text, okMsg) {
  const t = String(text || '');
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(t);
      UI.toast(okMsg || '已复制');
      return;
    }
  } catch (e) { /* 退回下面的兜底 */ }
  try {
    const ta = document.createElement('textarea');
    ta.value = t; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    UI.toast(ok ? (okMsg || '已复制') : '复制失败：请手动选择文本');
  } catch (e2) { UI.toast('复制失败：请手动选择文本'); }
}
function copyPid(pid) { copyText(pid, `已复制 pid：${pid}`); }
function copyCond() {
  const lines = ['词律探微 · 检索条件摘要',
    '条件：' + ParseApp.condText(lastCond),
    `命中：${total.value} 篇`,
    '说明：数字由本地引擎（同一套确定性口径）逐字算出，可按此条件复算。'];
  copyText(lines.join('\n'), '已复制条件摘要');
}
function clearError() { if (errMsg.value) { errMsg.value = ''; } }

/* ⚠ 2026-10-06 新增（外部审查 P1，本轮第 1/2 项）：把 `/api/nl2query` 的「理解结果」
   真正接到检索表单上（补上这一环，第 1/2 项才是端到端可用的）：
     · 改前 → 前端**根本没有**调用 nl2query 的地方（api.js 里导出了却无人用），
       理解出的 authorMode/cipaiMode（exact 语义）与 agg/pair/order_by（跨篇意图）
       没有任何路径进入 /api/search，被静默丢掉。
     · 改后 → 在线模式给一个「用自然语言理解」输入框：调用 nl2query → 回填表单 →
       把模式与意图随检索一起传给 /api/search → 服务端回 intent 后在本页如实提示。 */
const nlq = ref('');             // 自然语言理解输入框（在线）
const nlSource = ref('');        // 理解来源（规则／大模型）
const nlNote = ref('');          // 理解注记（如实披露 dropped/unparsed/unsupported）
const intentHint = ref('');      // /api/search 回传的「本页不执行这类意图」提示
/* 实体身份判定（2026-10-09 新增）：命中为 0 时对词牌/词人做一次 exact→ambiguous→unavailable
   判定，把「是不是想写…」如实提示出来（见 solve/entity_resolve.identify 与 /api/identify）。 */
const entityHint = ref('');
const entitySug = ref([]);
/* nl2query 回填的**匹配语义**与**跨篇意图**：表单里没有对应输入控件，单独保存并随检索传递
   （authorMode/cipaiMode → build_where 的 exact 语义；agg/pair/order_by → 服务端 intent 告知）。 */
const modes = reactive({ author: '', cipai: '' });
const nlIntent = reactive({ agg: null, pair: null, order_by: '' });

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
  /* ⚠ 本轮第 1/2 项：把 nl2query 回填的匹配语义与跨篇意图一并带上。
     改前 → 这两类信息从不进入检索参数：authorMode/cipaiMode 丢失致服务端退回 contains，
     agg/pair/order_by 丢失致跨篇意图被静默忽略。改后 → 随 /api/search 传递。 */
  if (modes.author) { o.authorMode = modes.author; }
  if (modes.cipai) { o.cipaiMode = modes.cipai; }
  /* agg/pair 是对象，走 GET 查询串须先 JSON 化（服务端 _intent_val 会再解析回来）。 */
  if (nlIntent.agg) { o.agg = JSON.stringify(nlIntent.agg); }
  if (nlIntent.pair) { o.pair = JSON.stringify(nlIntent.pair); }
  if (nlIntent.order_by) { o.order_by = nlIntent.order_by; }
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
  loadMsg.value = ''; errMsg.value = '';
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
  searched.value = true;
  syncUrl();
}

/* 深链：把当前条件写进 URL（`history.replaceState`，不新增历史、不刷新页面），
 *   这样刷新后 FIELDS 里的条件不丢、链接可直接分享。
 *   低风险保证：
 *     · 只写**表单里看得见的 FIELDS**，不写 nl2query 的内部意图（agg/pair 等）；
 *     · **保留既有 `?pid=`**，不破坏「深链直接定位某篇」的老行为；
 *     · file:// 下 replaceState 常被浏览器禁用 → 直接跳过；任何异常一律吞掉，绝不影响检索。 */
function syncUrl() {
  if (typeof window === 'undefined' || !window.history || !window.location) { return; }
  if (window.location.protocol === 'file:') { return; }
  try {
    const p = new URLSearchParams();
    FIELDS.forEach((f) => {
      if (f.id === 'size') { return; }         // size 单独处理（下面一并写入）
      const v = cond[f.id];
      const s = (v === null || v === undefined) ? '' : String(v).trim();
      if (s !== '') { p.set(f.id, s); }
    });
    if (String(cond.size || '').trim() !== '') { p.set('size', String(cond.size).trim()); }
    const q0 = UI.query();
    if (q0.pid) { p.set('pid', q0.pid); }
    const qs = p.toString();
    window.history.replaceState(null, '', window.location.pathname + (qs ? ('?' + qs) : ''));
  } catch (e) { /* 受限环境（file://、旧浏览器、隐私模式）：忽略，检索照常 */ }
}

async function run(p) {
  page.value = p || 1;
  const c = readCond();
  errMsg.value = '';
  entityHint.value = ''; entitySug.value = [];     // 每次检索先清掉上一次的实体提示
  /* 声律模式含非法字符：明确报错并中止（不静默替换成通配符），与 web/serve.py 的
     400 INVALID_QUERY 同口径。 */
  if (c.pz && !PZ_OK.test(String(c.pz).trim())) {
    errMsg.value = '声律模式含非法字符：只允许「平」「仄」「?」「？」。请清掉该字段里的其它字符后重试。';
    loadMsg.value = '';
    rows.value = []; total.value = 0; pages.value = 1; facets.value = null;
    pagerHtml.value = ''; lastHits.value = []; intentHint.value = ''; searched.value = true;
    return;
  }
  if (online) {
    loadMsg.value = '正在向本地引擎检索…（条件已发出，等库里的行级数据返回）';
    try {
      const j = await api.search(c, page.value, size.value);
      if (j.error) {
        loadMsg.value = '';
        errMsg.value = `本地引擎返回错误：${j.error}`;
        intentHint.value = '';
        rows.value = []; total.value = 0; pages.value = 1; facets.value = null;
        pagerHtml.value = ''; lastHits.value = []; searched.value = true;
        return;
      }
      /* 行对象与离线统一成 [pid,dynasty,author,cipai,title,raw]；指标直接用库里的 */
      const hits = (j.rows || []).map((r) => ({
        row: [r.pid, r.dynasty, r.author, r.cipai, r.title, r.raw || ''],
        info: { metrics: r }
      }));
      paint({ total: j.total, hits, facets: j.facets, ms: j.ms }, c, true);
      whereSql.value = j.where || ''; orderBy.value = j.order_by || '';
      /* ⚠ 本轮第 2 项：/api/search 识别到「本页不执行」的跨篇意图时，如实告知用户，
         而不是把普通列表当成答案。改前无此提示 → 用户以为分组统计题被回答了。 */
      intentHint.value = (j.intent && j.intent.unsupported_by_search) ? (j.intent.hint || '') : '';
      /* 命中为 0 且填了词牌/词人 → 问一次身份判定，如实提示「是不是想写…」 */
      if (!j.total) { entitySuggest(c); }
    } catch (e) {
      loadMsg.value = '';
      errMsg.value = String(e);
      intentHint.value = '';
      rows.value = []; total.value = 0; pages.value = 1; facets.value = null;
      pagerHtml.value = ''; lastHits.value = []; searched.value = true;
    }
    return;
  }
  const pack = (typeof window !== 'undefined' && window.__PACK__) ? window.__PACK__ : null;
  if (!pack) {
    loadMsg.value = '';
    errMsg.value = '离线数据未注入（页面里找不到 window.__PACK__）。本页需要数据包才能本地自算。';
    searched.value = true;
    return;
  }
  loadMsg.value = '正在浏览器本地按同一套口径自算…';
  paint(ParseApp.searchOffline(pack.rows, c), c, false);
  whereSql.value = ''; orderBy.value = ''; intentHint.value = '';
}

/* ⚠ 本轮第 1/2 项：把一句自然语言交给 /api/nl2query 理解，回填到表单（含精确匹配语义），
   再把跨篇意图（agg/pair/order_by）交给 /api/search 识别并如实提示。
   「可人工修改」：回填后用户仍可改任何表单项再点「检索」。 */
async function understand() {
  const text = nlq.value.trim();
  if (!text) { UI.toast('先写一句问题'); return; }
  errMsg.value = '';
  loadMsg.value = '正在理解问句…（把一句话转成可执行的检索条件）';
  try {
    const j = await api.nl2query(text, 1);
    const c = j.cond || {};
    FIELDS.forEach((f) => {
      if (f.id === 'size') { return; }
      const v = c[f.id];
      if (v !== undefined && v !== null && v !== '') { cond[f.id] = v; }
    });
    /* 匹配语义（exact/contains/prefix）与跨篇意图：表单无对应控件，单独保存并随检索传递。 */
    modes.author = c.authorMode || '';
    modes.cipai = c.cipaiMode || '';
    nlIntent.agg = j.agg || null;
    nlIntent.pair = j.pair || null;
    nlIntent.order_by = j.order_by || '';
    nlSource.value = j.source ? ('理解来源：' + j.source) : '';
    const flags = [];
    if (j.dropped && j.dropped.length) { flags.push('落不到库：' + j.dropped.join('、')); }
    if (j.unparsed && j.unparsed.length) { flags.push('未听懂：' + j.unparsed.join('、')); }
    if (j.unsupported) { flags.push('语料外：' + String(j.unsupported)); }
    nlNote.value = flags.join('　');
    loadMsg.value = '';
    run(1);
  } catch (e) {
    loadMsg.value = '';
    errMsg.value = `理解失败：${e}`;
  }
}

/* 实体身份判定（2026-10-09 新增，对齐竞品 `cilyutanwei` 的 exact→ambiguous→unavailable 三态）：
   命中为 0 且填了词牌/词人时，问一次 /api/identify —— 若库里**没有完全同名**，把候选如实提示出来。
   三态里只有 exact 不提示（名字本身是对的，命中 0 是别的条件太严，不该误导用户改名）。
   判定失败**静默**：它只是提示，绝不能因为提示失败而影响检索本身。 */
async function entitySuggest(c) {
  entityHint.value = ''; entitySug.value = [];
  const kind = c.cipai ? 'cipai' : (c.author ? 'author' : '');
  if (!kind) { return; }
  const text = String(kind === 'cipai' ? c.cipai : c.author).trim();
  if (!text) { return; }
  try {
    const j = await api.identify(kind, text);
    if (!j || j.status === 'exact') { return; }
    const label = (kind === 'cipai') ? '词牌' : '词人';
    entityHint.value = label + '「' + text + '」：' + (j.note || '库里查无此名。')
      + (j.status === 'ambiguous' ? '（点下面候选即按该名重检）' : '');
    entitySug.value = (j.matches || []).map((m) => ({ value: m.value, n: m.n, kind }));
  } catch (e) { /* 提示失败不影响检索结果 */ }
}

/* 采纳某条候选：写回对应输入框并重检（同时清掉 nl2query 的 exact 语义，回到默认 contains）。 */
function useSug(s) {
  if (s.kind === 'cipai') { cond.cipai = s.value; modes.cipai = ''; }
  else { cond.author = s.value; modes.author = ''; }
  run(1);
}

function resetAll() {
  FIELDS.forEach((f) => { if (f.id !== 'size') { cond[f.id] = f.def !== undefined ? f.def : ''; } });
  /* 清空时把理解得到的模式与意图也一并清掉，避免「残留的 exact/agg」影响下一次检索。 */
  modes.author = ''; modes.cipai = '';
  nlIntent.agg = null; nlIntent.pair = null; nlIntent.order_by = '';
  nlq.value = ''; nlSource.value = ''; nlNote.value = ''; intentHint.value = '';
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
      curDetailPid.value = j.pid || pid;      // 字位候选以「当前这篇」为主体
      cand.value = null;                       // 换篇即收起上一字位的候选面板
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

/* ── 字位候选 + 人工选读（2026-10-10 竞品对照）──
   坐标口径：`data-li` = 第几句（0 起）、`data-pos` = 该句第几个**汉字**（跳过标点），
   与后端 `/api/pronounce/candidates` 的 line/pos **同口径**（引擎与裁定共用一份坐标）。 */
async function onCharClick(ev) {
  const t = ev && ev.target;
  if (!t || t.tagName !== 'SPAN') { return; }
  const li = t.getAttribute && t.getAttribute('data-li');
  const pos = t.getAttribute && t.getAttribute('data-pos');
  if (li === null || pos === null || !curDetailPid.value) { return; }
  candErr.value = '';
  try {
    const p = new URLSearchParams({
      pid: curDetailPid.value, line: String(li), pos: String(pos)
    });
    const r = await fetch('/api/pronounce/candidates?' + p.toString());
    const j = await r.json();
    if (!r.ok || j.error) { throw new Error((j.error && j.error.message) || '取候选失败'); }
    const c0 = j.result || {};
    c0.line = Number(li); c0.pos = Number(pos);
    cand.value = c0;
  } catch (e) { candErr.value = String(e.message || e); cand.value = { line: Number(li), pos: Number(pos), char: t.textContent, candidates: [], history: [] }; }
}

function pickCand(c0) {
  if (!cand.value) { return; }
  // 进入「登记选读」状态：理由在**面板内**填写（不再用弹窗），保存时走决策事件
  cand.value = Object.assign({}, cand.value, {
    picking: c0, whyDraft: (cand.value.whyDraft || '')
  });
}

async function decide(c0) {
  if (!cand.value || !curDetailPid.value) { return; }
  const why = (cand.value.whyDraft || '').trim();
  try {
    const r = await fetch('/api/research/write', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: '/api/pronounce/decide',
        pid: curDetailPid.value, line: cand.value.line, pos: cand.value.pos,
        reading: c0.reading, tone: c0.tone, basis: (c0.source || ''), why,
        client_token: `pron:${curDetailPid.value}:${cand.value.line}:${cand.value.pos}:${c0.reading}`
      })
    });
    const j = await r.json();
    if (!r.ok || j.error) { throw new Error((j.error && j.error.message) || '选读失败'); }
    UI.toast('已登记选读（决策事件）');
    cand.value = Object.assign({}, cand.value, { picking: null });
    await refreshCand();
  } catch (e) { candErr.value = String(e.message || e); }
}

async function withdraw(d) {
  try {
    const r = await fetch('/api/research/write', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: '/api/pronounce/withdraw', decision_id: d.decision_id || d.id,
        why: '人工撤回', client_token: `wd:${d.decision_id || d.id}`
      })
    });
    const j = await r.json();
    if (!r.ok || j.error) { throw new Error((j.error && j.error.message) || '撤回失败'); }
    UI.toast('已撤回（回到基线）');
    await refreshCand();
  } catch (e) { candErr.value = String(e.message || e); }
}

async function refreshCand() {
  if (!cand.value) { return; }
  const p = new URLSearchParams({
    pid: curDetailPid.value, line: String(cand.value.line), pos: String(cand.value.pos)
  });
  const r = await fetch('/api/pronounce/candidates?' + p.toString());
  const j = await r.json();
  if (r.ok && !j.error) {
    const c0 = j.result || {};
    c0.line = cand.value.line; c0.pos = cand.value.pos;
    cand.value = c0;
  }
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
  const nRows = lastHits.value.length;
  if (!nRows) { UI.toast('没有可导出的结果'); return; }
  const header = ['导出范围', 'pid', '朝代', '词人', '词牌', '题名', '句数', '字数', '平', '仄', '仄声比例%', '声情', '变化值', '阈值', '原文'];
  /* ⚠ 本轮交付（结果导出增强）：CSV 顶部加**一行元信息**——条件摘要 + 命中数 + 导出范围 +
     生成时间。这样把表单独存一份时，脱离页面也能看清「这批数据是怎么筛出来的、覆盖多少」。
     既有「导出范围」列保留（范围已在按钮文案与每行首列如实标注）。 */
  const meta = ['# 导出信息',
    '范围=' + csvScope.value, '命中=' + total.value, '本文件行数=' + nRows,
    '条件=' + ParseApp.condText(lastCond),
    '生成=' + new Date().toLocaleString()];
  const out = [meta, header];
  lastHits.value.forEach((it) => {
    const r = it.row, m = it.info.metrics;
    out.push([csvScope.value, r[0], r[1], r[2], r[3], r[4], m.sent_n, m.han_len, m.ping, m.ze, m.ze_ratio, m.scene, m.change, m.threshold, r[5]]);
  });
  UI.download('词律探微_检索结果.csv', UI.csvText(out));
  UI.toast(`已导出 ${csvScope.value} ${nRows} 篇（含条件摘要）`);
}

/* 分析级 JSON 导出（2026-10-09 新增，对齐竞品 `cilyutanwei` 的 analysis JSON 导出）。
   与 CSV 的分工：CSV 给人看（带 BOM、表格友好）；JSON 给**脚本/二次分析**用（键值明确、
   不带 BOM——带 BOM 会让 `json.load` / `JSON.parse` 直接报错，见 core/ui.js 的 downloadJson）。
   口径不变：数字仍全部来自引擎，本函数只负责「打包 + 标注口径」。 */
function exportJson() {
  const nRows = lastHits.value.length;
  if (!nRows) { UI.toast('没有可导出的结果'); return; }
  const rowsOut = lastHits.value.map((it) => {
    const r = it.row, m = it.info.metrics;
    return {
      pid: r[0], dynasty: r[1], author: r[2], cipai: r[3], title: r[4],
      sent_n: m.sent_n, han_len: m.han_len, ping: m.ping, ze: m.ze,
      ze_ratio: m.ze_ratio, scene: m.scene, change: m.change, threshold: m.threshold,
      raw: r[5]
    };
  });
  UI.downloadJson('词律探微_检索结果.json', {
    generator: '词律探微 · 清代词律声情研究助手',
    note: '数字全部由本地引擎算出；scope 标明本文件覆盖「当前页」还是「全部」。',
    scope: csvScope.value,
    total_hits: total.value,
    rows_in_file: nRows,
    condition: ParseApp.condText(lastCond),
    generated_at: new Date().toLocaleString(),
    fields: ['pid', 'dynasty', 'author', 'cipai', 'title', 'sent_n', 'han_len', 'ping', 'ze',
             'ze_ratio', 'scene', 'change', 'threshold', 'raw'],
    rows: rowsOut
  });
  UI.toast(`已导出 JSON（${csvScope.value} ${nRows} 篇）`);
}

/* 分面 → 点击即筛 */
function applyFacet(pairs) {
  pairs.forEach(([f, v]) => {
    if (cond[f] !== undefined) { cond[f] = v; }
    /* 手动点分面改词人/词牌 → 退回默认 contains 语义（不沿用 nl2query 的 exact）。 */
    if (f === 'author') { modes.author = ''; }
    if (f === 'cipai') { modes.cipai = ''; }
  });
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
   <div class="pv" @keydown.esc="clearError">
    <div class="card">
      <h1>{{ online ? '多条件检索（在线 · 由 SQLite 查）' : '逐字解析与检索（离线 · 浏览器本地算）' }}</h1>
      <p class="dim">条件之间是「且」。{{ online
        ? '本页把条件发给本地服务，由库里的行级数据（含 lines 表）检索；数字与引擎逐字段一致。'
        : '本页数据内嵌在网页里，无需服务；判定规则与服务端同一张表。' }}
        <span v-if="!online">共 <b id="cnt">{{ cnt }}</b> 篇。</span></p>
      <div class="row pv-form">
        <label v-for="f in FIELDS" :key="f.id" class="f" :style="f.wide ? 'flex:1 1 240px' : ''">
          {{ f.label }}
          <select v-if="f.type === 'select'" :id="f.id" v-model="cond[f.id]"
                  @keydown.enter="run(1)">
            <option v-for="o in f.opts" :key="o[0]" :value="o[0]">{{ o[1] }}</option>
          </select>
          <input v-else-if="f.type === 'number'" :id="f.id" type="number"
                 :step="f.step || '1'" v-model="cond[f.id]" @keydown.enter="run(1)">
          <input v-else :id="f.id" type="text" :placeholder="f.ph || ''" v-model="cond[f.id]"
                 @keydown.enter="run(1)">
        </label>
        <button id="go" @click="run(1)">检索</button>
        <button id="reset" class="ghost" @click="resetAll">清空</button>
        <button id="copycond" class="ghost" title="把当前条件与命中数复制成一段文本，便于写论文时引用"
                @click="copyCond">复制条件摘要</button>
        <button id="csv" class="ghost" @click="exportCsv">{{ csvLabel }}</button>
        <button id="jsonexport" class="ghost" title="把当前结果集导出为结构化 JSON（给脚本/二次分析用）"
                @click="exportJson">导出 JSON</button>
      </div>
      <p class="dim pv-hint">在任一输入框按 <b>Enter</b> 即检索；按 <b>Esc</b> 清错误提示。
        点表头可对<b>当前页</b>排序（不改后端查询）。</p>
      <!-- ⚠ 本轮第 1/2 项：自然语言理解入口（仅在线；离线无后端）。理解 → 回填 → 检索。 -->
      <div v-if="online" class="row" style="margin-top:8px">
        <label class="f" style="flex:1 1 320px">用自然语言理解
          <input id="nlq" type="text" v-model="nlq"
                 placeholder="如：哪个词人的词最多（先理解成条件回填，再检索；可人工改）"
                 @keydown.enter="understand">
        </label>
        <button id="nlgo" @click="understand">理解并填条件</button>
        <span v-if="nlSource" class="dim" style="flex:1 1 100%">
          {{ nlSource }}<template v-if="nlNote">　{{ nlNote }}</template>
        </span>
      </div>
    </div>

    <div class="card tight">
      <!-- 三态互斥：加载 / 错误 / 结果（含空态），任一时刻只出现一种，绝不「永远转圈」。 -->
      <div v-if="loadMsg" id="load" class="loading"><span class="spin"></span> {{ loadMsg }}</div>

      <div v-else-if="errMsg" id="err" class="err">
        <b class="bad">这一步没走通</b>
        <p>{{ errMsg }}</p>
        <p class="dim">可试：① 确认本地服务在运行（<code>python web/serve.py</code>）；
          ② 按 <b>Ctrl+F5</b> 强制刷新，排除旧页面缓存；
          ③ 放宽条件、或改用离线页 <code>parse.html</code> 复算。按 <b>Esc</b> 可清掉本条提示。</p>
      </div>

      <template v-else>
        <div id="meta" v-html="metaHtml"></div>
        <div v-if="noHit" id="empty" class="empty">
          <p><b>没有命中的篇目。</b></p>
          <p class="dim">下一步：① 放宽一个条件（如把「仄比 ≥」调低、清掉句脚字）；
            ② 点下面的分面 chip 换个词人／词牌；③ 或点「清空」回到全库，再逐步加条件
            —— 条件之间是「且」，越多越严。</p>
        </div>
      </template>

      <!-- 实体身份判定（2026-10-09 新增）：命中为 0 且词牌/词人「库里没有完全同名」时，
           如实提示 exact/ambiguous/unavailable 三态与近似候选；点候选即换名重检。 -->
      <div v-if="entityHint" id="entityHint" class="hint-box">
        <span>{{ entityHint }}</span>
        <span v-for="s in entitySug" :key="s.kind + s.value" class="chip"
              @click="useSug(s)">{{ s.value }} <span class="dim">{{ s.n }}</span></span>
      </div>

      <div v-if="online && whereSql" class="dim">SQL 条件：{{ whereSql }}；ORDER BY {{ orderBy }}</div>
      <!-- ⚠ 本轮第 2 项：这类意图本页不执行，如实告知并引导去问答页（不再静默当普通列表）。 -->
      <div v-if="intentHint" id="intentHint" class="bad" style="margin-top:6px">{{ intentHint }}</div>
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
      <div v-if="sortLabel" class="dim pv-sorthint">
        {{ sortLabel }}（仅当前页；如需全库排序请用上方「排序」下拉后再检索）</div>
      <div class="scroll">
        <table class="view-table">
          <thead><tr>
            <th>#</th>
            <th class="sortable" @click="clickSort('author')">词人<span class="sort-ind" v-if="sortInd('author')">{{ sortInd('author') }}</span></th>
            <th class="sortable" @click="clickSort('title')">题名<span class="sort-ind" v-if="sortInd('title')">{{ sortInd('title') }}</span></th>
            <th class="sortable" @click="clickSort('cipai')">词牌<span class="sort-ind" v-if="sortInd('cipai')">{{ sortInd('cipai') }}</span></th>
            <th class="sortable num" @click="clickSort('sent')">句数<span class="sort-ind" v-if="sortInd('sent')">{{ sortInd('sent') }}</span></th>
            <th class="sortable num" @click="clickSort('len')">字数<span class="sort-ind" v-if="sortInd('len')">{{ sortInd('len') }}</span></th>
            <th class="sortable num" @click="clickSort('ze')">仄比<span class="sort-ind" v-if="sortInd('ze')">{{ sortInd('ze') }}</span></th>
            <th class="sortable" @click="clickSort('scene')">声情<span class="sort-ind" v-if="sortInd('scene')">{{ sortInd('scene') }}</span></th>
            <th>操作</th>
          </tr></thead>
          <tbody id="rows">
            <tr v-for="(it, i) in sortedRows" :key="i">
              <td class="dim">{{ (page - 1) * size + i + 1 }}</td>
              <td v-html="ParseApp.highlight(it.row[2], lastCond.q)"></td>
              <td v-html="ParseApp.highlight(it.row[4], lastCond.q)"></td>
              <td class="dim" v-html="ParseApp.highlight(it.row[3], lastCond.q)"></td>
              <td class="num">{{ it.info.metrics.sent_n }}</td>
              <td class="num">{{ it.info.metrics.han_len }}</td>
              <td class="num">{{ it.info.metrics.ze_ratio }}%</td>
              <td class="dim">{{ it.info.metrics.scene }}</td>
              <td class="op">
                <button class="ghost" :data-pid="it.row[0]" @click="showDetail(it.row[0])">逐字解析</button>
                <button class="ghost" title="复制本篇 pid，便于在别处引用" @click="copyPid(it.row[0])">复制 pid</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div id="pager" v-html="pagerHtml" @click="(e) => { const g = e.target.getAttribute && e.target.getAttribute('data-go'); if (g) { goPage(parseInt(g, 10)); } }"></div>
    </div>

    <div class="card">
      <h2>逐字解析</h2>
      <div id="detail" v-html="detailHtml" @click="onCharClick"></div>
      <p class="dim">（点<b>任一汉字</b>可查看它的读音候选并人工选读——选读会写进研究库的
        决策事件，可撤回，绝不改动字级基线表）</p>

      <!-- 字位候选 + 人工选读（竞品「逐字研读」的对应能力，2026-10-10） -->
      <div v-if="cand" class="pv-cand">
        <h3>字位 {{ cand.line + 1 }} 句 · 第 {{ cand.pos + 1 }} 字「{{ cand.char }}」
          <small class="dim">基线平仄 {{ cand.base_pz || '—' }}（普通话口径）</small></h3>
        <p v-if="candErr" class="bad">✗ {{ candErr }}</p>

        <h4>普通话候选 <small class="dim">（可人工选定；平仄按普通话四声派生）</small></h4>
        <table class="cp-table">
          <thead><tr><th>读音</th><th>声调</th><th>平仄</th><th>来源</th><th></th></tr></thead>
          <tbody>
            <tr v-for="c0 in cand.candidates" :key="c0.reading"
                :class="{ cur: cand.current_decision && cand.current_decision.reading === c0.reading }">
              <td>{{ c0.reading }}</td>
              <td class="num">{{ c0.tone }}</td>
              <td>{{ c0.tone >= 3 ? '仄' : '平' }}</td>
              <td class="dim">{{ c0.source }}</td>
              <td><button type="button" class="mini" :disabled="!online"
                          @click="pickCand(c0)">选定</button></td>
            </tr>
            <tr v-if="!(cand.candidates || []).length">
              <td colspan="5" class="dim">（该字只有一种读音，无可选项）</td>
            </tr>
          </tbody>
        </table>
        <p v-if="cand.picking" class="dim">正在为「{{ cand.picking.reading }}」登记选读——
          <input v-model="cand.whyDraft" placeholder="选读依据（可留空；写进决策事件）" style="width:320px">
          <button type="button" class="mini" :disabled="!online" @click="decide(cand.picking)">保存选读</button>
          <button type="button" class="mini" @click="cand.picking = null">放弃更改</button>
        </p>

        <div v-if="cand.current_decision" class="pv-cur">
          当前生效裁定：<b>{{ cand.current_decision.reading }}</b>
          （{{ cand.current_decision.pz }}）
          <button type="button" class="mini danger" :disabled="!online"
                  @click="withdraw(cand.current_decision)">撤回</button>
        </div>

        <h4>《广韵》候选 <small class="dim">（历史音韵参考·只读——不改变普通话平仄口径）</small></h4>
        <p v-if="cand.guangyun_note" class="dim">{{ cand.guangyun_note }}</p>
        <table v-if="(cand.guangyun || []).length" class="cp-table">
          <thead><tr><th>音韵地位</th><th>反切</th><th>直音</th><th>释义（截 160 字）</th><th>平仄（中古）</th></tr></thead>
          <tbody>
            <tr v-for="(g, gi) in cand.guangyun" :key="gi">
              <td>{{ g.desc }}</td>
              <td>{{ g.fanqie || '—' }}</td>
              <td>{{ g.zhiyin || '—' }}</td>
              <td class="dim">{{ g.gloss || '—' }}</td>
              <td>{{ g.pz || '—' }}<small class="dim">（{{ g.sheng }}声·{{ g.yun }}韵）</small></td>
            </tr>
          </tbody>
        </table>
        <p v-else class="dim">（《广韵》未收录此字，或导出数据中无此字条目）</p>

        <div v-if="(cand.history || []).length" class="pv-hist">
          <h4>决策历史（select / withdraw 全留痕）</h4>
          <div v-for="h in cand.history" :key="h.id" class="dim">
            #{{ h.id }} {{ h.action }} {{ (h.payload || {}).reading || '' }}
            <span v-if="h.why">（{{ h.why }}）</span>
            <span class="dim">{{ h.created_at || '' }}</span>
          </div>
        </div>
        <p><button type="button" class="mini" @click="cand = null">收起</button></p>
      </div>
    </div>
   </div>
  </AppShell>
</template>

<style scoped>
/* ParseView.vue —— 检索页精修（2026-10-08）。配色沿用 core/ui.js 变量，不另起一套。
 * 这里只放**模板渲染**部分的样式；v-html 注入的 #detail 内部另有非 scoped 块（见下）。 */

.pv-form { margin-top: 6px; }
.pv-hint { margin: 10px 0 0; }
.pv-sorthint { margin: 0 0 6px; }
/* 字位候选面板（竞品「逐字研读」对应能力，2026-10-10） */
.pv-cand { border-top: 1px solid var(--bd, #ddd); margin-top: 10px; padding-top: 8px; }
.pv-cand h3 { margin: 4px 0; }
.pv-cand h4 { margin: 10px 0 4px; font-size: 14px; }
.pv-cand .cp-table { width: 100%; border-collapse: collapse; margin: 4px 0 8px; }
.pv-cand .cp-table th, .pv-cand .cp-table td {
  border-bottom: 1px solid var(--bd, #ddd); padding: 3px 6px; text-align: left; font-size: 13px; }
.pv-cand .cp-table .num { text-align: right; }
.pv-cand tr.cur td { background: var(--hl, #fff7e6); }
.pv-cur { margin: 6px 0; }
.pv-hist { font-size: 12px; }
.pv-hist h4 { margin: 6px 0 2px; }

/* 加载 / 错误 / 空态：三种状态各有明确文案与不刺眼的配色 */
.loading { margin: 4px 0; color: var(--ink2); }
.err { border-left: 4px solid var(--warn); border-radius: 6px; padding: 8px 12px;
  background: color-mix(in srgb, var(--warn) 8%, transparent); }
.err p { margin: 6px 0 0; }
.empty { border: 1px dashed var(--line); border-radius: var(--r); padding: 14px 16px;
  background: var(--panel2); margin: 8px 0 2px; }
.empty p { margin: 4px 0; }

/* 表格操作列不换行，两个按钮间距一致 */
.pv .op { white-space: nowrap; }
.pv .op button { margin-right: 4px; }

/* 实体身份判定提示（2026-10-09）：与「空态」区分——它不是「没结果」，而是「这名字库里没有」。
   用虚线棕边 + 候选 chip，让「换个名字再试」一眼可点。 */
.hint-box { border: 1px dashed color-mix(in srgb, var(--accent2) 70%, transparent);
  border-radius: var(--r); padding: 8px 12px; background: var(--panel3);
  margin: 8px 0 2px; font-size: 13.5px; }
.hint-box .chip { margin-left: 6px; }

@media (max-width: 640px) {
  .pv .op button { margin: 2px 4px 2px 0; }
}
</style>

<style>
/* 逐字解析面板（#detail）由 core/parse.js 的 detailHtml 经 v-html 注入，
   scoped 样式覆盖不到其子元素，故用**非 scoped**；前缀 `.pv` 收口，只在本页生效，
   不外溢到其它视图（其它视图没有 .pv 容器）。 */
.pv #detail h2 { font-size: 16px; margin: 2px 0 6px; }
.pv #detail p { margin: 4px 0 8px; color: var(--ink2); font-size: 13px; }
.pv #detail table { font-size: 13px; }
.pv #detail td, .pv #detail th { padding: 4px 8px; }
.pv #detail td:first-child, .pv #detail th:first-child { text-align: right; width: 3em; }
</style>
