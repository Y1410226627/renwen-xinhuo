/* core/index.mjs —— ESM 桥接层：把 UMD 经典脚本（唯一真源）转成 Vue 可 `import` 的模块。
 *
 * 为什么需要：core/*.js 用 UMD 外壳，原因是 **node 门禁用 `vm` 直接加载它们**
 * （见 web/vmload.js），而 `vm` 只吃经典脚本、不吃 `import`。Vue/Vite 侧则要 ESM。
 * 桥接层不实现任何业务逻辑，只做「加载 + 具名转出」，因此**实现仍然只有一份**（D15）。
 */
import './metrics.js';
import './ui.js';
import './parse.js';
import './review.js';
import './ask.js';

const g = (typeof window !== 'undefined' ? window : globalThis);

export const Metrics = g.Metrics;
export const UI = g.UI;
export const ParseApp = g.ParseApp;
export const ReviewApp = g.ReviewApp;
export const AskApp = g.AskApp;

/* 便于按需具名导入 */
export const {
  compute, banker1, hanOnly, hanLen, count, HAN
} = g.Metrics;

export const {
  esc, attr, hz, badge, fmtInt, fmt1, signed, csvText, download, toast, spinner,
  query, footer, mountTheme, CSS
} = g.UI;

export const {
  setData, setLive, isLive, analyze, info, splitSents, pzOf, tailOf, matchCond,
  pzTest, searchOffline, detailHtml, listRow, facets, condText, highlight, pageSlice
} = g.ParseApp;

export const { COLS, stats: reviewStats, filter: reviewFilter, sortRows, rowHtml } = g.ReviewApp;

export const { askHtml, blockHtml, renderErrorHtml } = g.AskApp;

export default { Metrics: g.Metrics, UI: g.UI, ParseApp: g.ParseApp, ReviewApp: g.ReviewApp, AskApp: g.AskApp };
