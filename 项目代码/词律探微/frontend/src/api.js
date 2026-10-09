/* src/api.js —— 后端接口的**唯一调用入口**（Vue 组件不再各写 fetch）。
 *
 * 设计原则（贯穿全项目）：**数字归引擎、文料归检索、说法归生成、出处归引用**。
 * 本文件只做「拼 URL + 取 JSON」，不做任何数值加工——数字一律来自 /api/*。
 *
 * base 约定：由入口 HTML 上的 `window.__API_BASE__` 指定（在线为空串＝同源；离线为 null）。
 */
const base = () => {
  if (typeof window === 'undefined') { return ''; }
  return (window.__API_BASE__ === undefined) ? '' : window.__API_BASE__;
};

/* ⚠ 2026-10-06 加（主人实测：页面永远停在「正在检索语料并核算…」）：
 *   原先所有请求都**没有超时**——当本地服务没在运行、或浏览器缓存了旧页面导致脚本 404、
 *   或后端卡住时，`fetch` 会一直挂着，界面只显示一个转圈占位，用户**完全看不出发生了什么**。
 *   这里给三类请求各一个**明确的失败期限**，超时后抛出带**处置建议**的中文错误。
 *   （数值选择依据：本地实测正常问答首帧 0.03 秒、总耗时 0.06 秒；
 *     留足余量后：普通接口 30 秒、流式首帧 20 秒、流式空闲 60 秒。） */
const ASK_TIMEOUT_MS = 30000;
const STREAM_FIRST_MS = 20000;
const STREAM_IDLE_MS = 60000;

function timeoutMsg(label, ms) {
  return label + ' 超过 ' + Math.round(ms / 1000) + ' 秒无响应——请确认本地服务在运行'
    + '（`python web/serve.py`）；若是刚更新过代码或页面，请按 Ctrl+F5 强制刷新后重试。';
}

/* 网络层失败（服务没起 / 端口不通 / 页面从旧缓存加载）也给出同一套可读指引 */
function netMsg(label, detail) {
  return label + ' 失败：' + detail + '——请确认本地服务在运行（`python web/serve.py`）；'
    + '若是刚更新过代码或页面，请按 Ctrl+F5 强制刷新后重试。';
}

async function withTimeout(ms, label, fn) {
  const ctrl = new AbortController();
  let hit = false;
  const t = setTimeout(() => { hit = true; try { ctrl.abort(); } catch (e) { /* 忽略 */ } }, ms);
  try {
    return await fn(ctrl.signal);
  } catch (e) {
    if (hit || (e && e.name === 'AbortError')) { throw new Error(timeoutMsg(label, ms)); }
    if (e instanceof TypeError) { throw new Error(netMsg(label, e.message || '连接失败')); }
    throw e;
  } finally {
    clearTimeout(t);
  }
}

/* 多轮「结果集」通路（2026-10-08）：`ctx_pids` = 上一轮命中的 pid 集合。
 *
 * 前端用数组更自然，HTTP 只认逗号串——这里统一成字符串；空数组/空串**不发送**
 * （getJson/askStream 会过滤空值），避免把检索范围锁死成空集。
 *
 * ⚠ 2026-10-08 新增（外部审查 A 项）：**服务端会话**。新增 `sid`（服务端会话 id）与
 *   `carry`（显式「承上一轮」开关）两个参数，**一并透传**给 `/api/ask` 与 `/api/ask_stream`。
 *   为什么要有 sid：把上一轮**完整**结果集存到服务端，下一轮由服务端判「集合指代/单篇指代/
 *   条件继承」——避免旧版「前端把 pid 截到 200 后当全部」（那是**语义截断**，不是性能截断）。
 *   `ctx_pids` 保留为**兜底**（服务端会话不可用时才用）。 */
function normCtxPids(opt) {
  const o = Object.assign({}, opt);
  if (Array.isArray(o.ctx_pids)) { o.ctx_pids = o.ctx_pids.join(','); }
  if (o.sid != null) { o.sid = String(o.sid); }          // sid 一律按字符串传（空串会被过滤不发送）
  if (o.carry != null) { o.carry = o.carry ? '1' : '0'; } // 归一成 0/1，服务端按布尔解析
  return o;
}

export async function getJson(path, params) {
  const b = base();
  if (b === null) { throw new Error('离线模式：没有本地服务，无法调用 ' + path); }
  let qs = '';
  if (params) {
    qs = Object.keys(params)
      .filter((k) => params[k] !== '' && params[k] !== null && params[k] !== undefined)
      .map((k) => encodeURIComponent(k) + '=' + encodeURIComponent(params[k]))
      .join('&');
  }
  const url = b + path + (qs ? ('?' + qs) : '');
  return withTimeout(ASK_TIMEOUT_MS, '接口 ' + path, async (signal) => {
    const r = await fetch(url, { signal });
    if (!r.ok) { throw new Error('接口 ' + path + ' 返回 HTTP ' + r.status); }
    return r.json();
  });
}

export const api = {
  llm: () => getJson('/api/llm'),
  examples: () => getJson('/api/examples'),
  ask: (q, opt = {}) => getJson('/api/ask', Object.assign({ q }, normCtxPids(opt))),
  search: (cond, page, size) => getJson('/api/search', Object.assign({}, cond, { page, size })),
  parse: (pid) => getJson('/api/parse', { pid }),
  rand: (dyn) => getJson('/api/rand', { dyn }),
  nl2query: (q, llm) => getJson('/api/nl2query', { q, llm }),
  summarize: (cond, llm) => getJson('/api/summarize', Object.assign({}, cond, { llm })),
  compare: (group_by, values, metric) => getJson('/api/compare', { group_by, values, metric }),
  /* 语料总览统计（2026-10-09 新增）：全部数字由服务端 SQL 现算，见 web/serve.py 的 q_catalog。 */
  catalog: (top) => getJson('/api/catalog', { top }),
  /* 实体身份判定（2026-10-09 新增）：exact／ambiguous／unavailable + 近似提示。 */
  identify: (kind, text) => getJson('/api/identify', { kind, text }),
  /* SSE 流式问答：由调用方传入 onFrame(type, payload)；返回 Promise，deliver 完即 resolve。 */
  askStream(q, opt = {}, onFrame) {
    const b = base();
    if (b === null) { return Promise.reject(new Error('离线模式：无法调用流式接口')); }
    const params = Object.assign({ q, topk: 3 }, normCtxPids(opt));
    const qs = Object.keys(params)
      .filter((k) => params[k] !== '' && params[k] !== null && params[k] !== undefined)
      .map((k) => encodeURIComponent(k) + '=' + encodeURIComponent(params[k]))
      .join('&');
    /* 超时策略（2026-10-06 加）：**首帧** 20 秒 —— 服务没起 / 旧页面脚本 404 时立刻给出可读错误；
       收到首帧后改为**空闲** 60 秒 —— 大模型流式长回答不会被误杀。 */
    const ctrl = new AbortController();
    let hit = false;
    /* ⚠ 2026-10-06 修（外部审查 P1，本轮第 6 项）：记录「是否已收到首帧」。
       改前 → 无论何时超时都报「流式问答（首帧）20 秒无响应」——但那可能发生在**已收到
         status/engine 帧之后**（是后段空闲 60 秒超时），提示误导排查方向。
       改后 → 用 gotFrame 区分两种文案（见 catch 分支）。 */
    let gotFrame = false;
    let timer = null;
    const arm = (ms) => {
      if (timer) { clearTimeout(timer); }
      timer = setTimeout(() => { hit = true; try { ctrl.abort(); } catch (e) { /* 忽略 */ } }, ms);
    };
    arm(STREAM_FIRST_MS);
    return fetch(b + '/api/ask_stream?' + qs, { signal: ctrl.signal }).then((r) => {
      /* ⚠ 2026-10-06 修（外部审查 P1，本轮第 7 项）：把三件事**拆开**，不再混成一句
         「该浏览器不支持流式」——
         改前 → `if (!r.ok || !r.body || !r.body.getReader) throw new Error('该浏览器不支持流式')`：
           HTTP 错误（后端 bug）、服务端无响应体、浏览器能力不足三种情况都被错怪到浏览器。
         改后 → 三种各自明确（HTTP 带状态码 / body 为空 / 无 getReader 才是浏览器不支持）。 */
      if (!r.ok) {
        throw new Error('流式问答失败：服务端返回 HTTP ' + r.status
          + '——这是服务端错误（请查看服务端日志；若刚更新过代码，请重跑 python web/serve.py）。');
      }
      if (!r.body) {
        throw new Error('流式问答失败：服务端没有返回响应体（body 为空）——'
          + '请确认访问的是本地服务（python web/serve.py），而不是静态文件或旧缓存页面。');
      }
      if (typeof r.body.getReader !== 'function') {
        throw new Error('该浏览器不支持流式读取（ReadableStream.getReader 不可用）；'
          + '可改用「非流式」提问，数字与证据不降级。');
      }
      const rd = r.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      const pump = () => rd.read().then((x) => {
        if (x.done) { return; }
        gotFrame = true;          // 收到首帧（任意一帧字节）→ 之后超时按「空闲」语义报错
        arm(STREAM_IDLE_MS);
        buf += dec.decode(x.value, { stream: true });
        const parts = buf.split('\n\n');
        buf = parts.pop();
        for (const part of parts) {
          const ln = part.trim();
          if (ln.indexOf('data:') !== 0) { continue; }
          const p = ln.slice(5).trim();
          if (!p || p.indexOf('"done"') >= 0) { continue; }
          let d; try { d = JSON.parse(p); } catch (e) { continue; }
          onFrame(d.type, d);
        }
        return pump();
      });
      return pump();
    }).catch((e) => {
      if (hit || (e && e.name === 'AbortError')) {
        /* ⚠ 本轮第 6 项：区分「首帧超时」与「收到首帧后的空闲超时」，不再一律报首帧。 */
        if (gotFrame) { throw new Error(timeoutMsg('流式问答（空闲）', STREAM_IDLE_MS)); }
        throw new Error(timeoutMsg('流式问答（首帧）', STREAM_FIRST_MS));
      }
      if (e instanceof TypeError) { throw new Error(netMsg('流式问答', e.message || '连接失败')); }
      throw e;
    }).finally(() => { if (timer) { clearTimeout(timer); } });
  }
};
