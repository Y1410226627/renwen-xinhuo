/* types/api.d.ts —— 声明 `src/api.js` 的导出类型（接口是后端 /api/* 的唯一定义处）。 */

import type { SearchResult } from './core';

/** SSE 帧的类型。
 *
 * ⚠ 2026-10-06 修（外部审查 P1，本轮第 8 项）：运行时真实出现的帧类型是
 *   `status` / `engine` / `delta` / `final` / `error` / `done`（见 web/serve.py 的
 *   `q_ask_stream` 与 `_sse`）；旧声明只写了 `status | final | done`，漏了
 *   `delta`（大模型逐字增量）、`engine`（引擎答案先到）、`error`（worker 异常），
 *   组件按旧类型穷举会漏处理真实存在的帧。 */
export type StreamFrameType = 'status' | 'engine' | 'delta' | 'final' | 'error' | 'done';

export interface StreamFrame {
  type: StreamFrameType;
  /** status/final 帧的文本。 */
  text?: string;
  [k: string]: unknown;
}

export interface AskOptions {
  topk?: number;
  narrate?: boolean | string;
  argument?: boolean | string;
  parse?: boolean | string;
  policy?: 'auto' | string;
  ctx?: string;
  /** 多轮「结果集」通路：上一轮命中的 pid 集合（组件传数组更自然，api.js 会拼成逗号串）。 */
  ctx_pids?: string | string[];
  llm?: boolean | string;
}

/** 检索条件（键与 SEARCH_PARAMS 一致）。
 *
 * ⚠ 2026-10-06 修（外部审查 P1，本轮第 1/2 项）：补 `authorMode`/`cipaiMode`
 *   （contains|exact|prefix，由 nl2query 回填）与 `agg`/`pair`/`order_by`
 *   （nl2query 的跨篇意图，/api/search 不执行，仅用于回包 intent 如实告知）。
 */
export interface SearchCond {
  dynasty?: string;
  author?: string;
  /** author 的匹配语义：contains（默认）/ exact / prefix。 */
  authorMode?: 'contains' | 'exact' | 'prefix' | string;
  cipai?: string;
  /** cipai 的匹配语义：contains（默认）/ exact / prefix。 */
  cipaiMode?: 'contains' | 'exact' | 'prefix' | string;
  tail?: string;
  pz?: string;
  scene?: string;
  q?: string;
  /** 分组统计/对比意图（nl2query 产出；/api/search 不执行，仅如实告知）。 */
  agg?: unknown;
  /** 配对意图（同上）。 */
  pair?: unknown;
  /** 排序取值意图（同上）。 */
  order_by?: string;
  [k: string]: unknown;
}

export interface Api {
  /** 大模型可用性探测。
   *
   * ⚠ 2026-10-06 修（外部审查 P1，本轮第 8 项）：/api/llm 实际返回
   *   `{available, model, provider, hint}`（见 web/serve.py 的 `/api/llm` 分支）；
   *   旧类型写成 `{ok, model}`，字段名与含义都不符（ok 应为 available，且缺 provider/hint）。 */
  llm(): Promise<{ available: boolean; model: string | null; provider?: string; hint?: string }>;
  /** 示例问题。 */
  examples(): Promise<string[]>;
  /** 一次性问答。 */
  ask(q: string, opt?: AskOptions): Promise<Record<string, unknown>>;
  /** 条件检索（服务端）。 */
  search(cond: SearchCond, page?: number, size?: number): Promise<SearchResult>;
  /** 按 id 取一篇。 */
  parse(pid: string): Promise<Record<string, unknown>>;
  /** 随机一篇。 */
  rand(dyn?: string): Promise<Record<string, unknown>>;
  /** 自然语言转查询。 */
  nl2query(q: string, llm?: boolean | string): Promise<Record<string, unknown>>;
  /** 条件摘要成文。 */
  summarize(cond: SearchCond, llm?: boolean | string): Promise<Record<string, unknown>>;
  /** 分组对比。
   *
   * ⚠ 2026-10-06 修（外部审查 P1，本轮第 8 项）：HTTP 实际传的是 `values="宋,清"` **字符串**
   *   （api.js 把它整体 encodeURIComponent 进查询串；数组会被 Array.toString 拼成逗号串）。
   *   故 canonical 类型是 `string`，数组只是便利重载、仍会被拼成逗号串。 */
  compare(group_by: string, values: string | string[], metric: string): Promise<Record<string, unknown>>;
  /** 流式问答；onFrame 逐帧回调，Promise 在流结束时 resolve。 */
  askStream(
    q: string,
    opt: AskOptions,
    onFrame: (type: StreamFrameType, payload: StreamFrame) => void
  ): Promise<void>;
}

/** 通用 GET-JSON（保留导出，供组件偶尔直接调用）。 */
export function getJson<T = unknown>(path: string, params?: Record<string, unknown>): Promise<T>;

export const api: Api;
