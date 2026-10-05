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
  const r = await fetch(url);
  return r.json();
}

export const api = {
  llm: () => getJson('/api/llm'),
  examples: () => getJson('/api/examples'),
  ask: (q, opt = {}) => getJson('/api/ask', Object.assign({ q }, opt)),
  search: (cond, page, size) => getJson('/api/search', Object.assign({}, cond, { page, size })),
  parse: (pid) => getJson('/api/parse', { pid }),
  rand: (dyn) => getJson('/api/rand', { dyn }),
  nl2query: (q, llm) => getJson('/api/nl2query', { q, llm }),
  summarize: (cond, llm) => getJson('/api/summarize', Object.assign({}, cond, { llm })),
  compare: (group_by, values, metric) => getJson('/api/compare', { group_by, values, metric }),
  /* SSE 流式问答：由调用方传入 onFrame(type, payload)；返回 Promise，deliver 完即 resolve。 */
  askStream(q, opt = {}, onFrame) {
    const b = base();
    if (b === null) { return Promise.reject(new Error('离线模式：无法调用流式接口')); }
    const params = Object.assign({ q, topk: 3 }, opt);
    const qs = Object.keys(params)
      .filter((k) => params[k] !== '' && params[k] !== null && params[k] !== undefined)
      .map((k) => encodeURIComponent(k) + '=' + encodeURIComponent(params[k]))
      .join('&');
    return fetch(b + '/api/ask_stream?' + qs).then((r) => {
      if (!r.ok || !r.body || !r.body.getReader) { throw new Error('该浏览器不支持流式'); }
      const rd = r.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      const pump = () => rd.read().then((x) => {
        if (x.done) { return; }
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
    });
  }
};
