/* types/api.d.ts —— 声明 `src/api.js` 的导出类型（接口是后端 /api/* 的唯一定义处）。 */

import type { SearchResult } from './core';

/** SSE 帧的三种类型。 */
export type StreamFrameType = 'status' | 'final' | 'done';

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
  llm?: boolean | string;
}

/** 检索条件（键与 SEARCH_PARAMS 一致）。 */
export interface SearchCond {
  dynasty?: string;
  author?: string;
  cipai?: string;
  tail?: string;
  pz?: string;
  scene?: string;
  q?: string;
  [k: string]: unknown;
}

export interface Api {
  /** 大模型可用性探测。 */
  llm(): Promise<{ ok: boolean; model?: string | null }>;
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
  /** 分组对比。 */
  compare(group_by: string, values: string[], metric: string): Promise<Record<string, unknown>>;
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
