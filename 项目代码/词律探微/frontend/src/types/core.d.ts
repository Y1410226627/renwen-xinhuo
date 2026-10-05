/* types/core.d.ts —— core 逻辑层（`frontend/src/core/*.js`）的类型声明。
 *
 * 为什么用 `.d.ts` 而不是把 `.js` 改成 `.ts`：
 *   core 是 **UMD 经典脚本**，node 门禁用 `vm.runInContext` 直接加载（见 web/vmload.js），
 *   改成 ESM/TS 会让门禁报 `Cannot use import statement outside a module`。
 *   所以实现保持 `.js` 不动，用**独立声明文件**给 Vue 侧提供强类型 —— 零实现改动、零门禁风险（D15）。
 *
 * 真源纪律：本文件的类型必须与 core/*.js 的 `return {...}` 导出**逐一对应**。
 *   `npm run check-types`（tools/check-types.mjs）会断言两者不漂移。
 */

/** 一个「字 → 平仄」的串（只含 '平' | '仄'）。 */
export type PZ = string;

/** 词篇的一行：原文 + 该行逐字平仄串。 */
export interface Line {
  text: string;
  pz: PZ;
}

/** 声律指标（`Metrics.compute` 的返回值；字段口径见 core/metrics.js 头部注释）。 */
export interface MetricsResult {
  /** 汉字总数（只数 CJK 基本区 + 扩展 A）。 */
  han_len: number;
  /** 句数（按 。？！ 切）。 */
  sent_n: number;
  /** 平声字数。 */
  ping: number;
  /** 仄声字数。 */
  ze: number;
  /** 仄声占比 = 100 × 仄 / 汉字数，银行家舍入一位。 */
  ze_ratio: number;
  /** 前段句数切点 = ⌊sent_n / 2⌋。 */
  cut: number;
  /** 前段仄声比例（舍入后）。 */
  f_ratio: number;
  /** 后段仄声比例（舍入后）。 */
  b_ratio: number;
  /** 变化 = 后段原始比例 − 前段原始比例（未舍入相减，舍入后一位）。 */
  change: number;
  /** 绝对变幅 = |change|。 */
  abs_change: number;
  /** 最长句的汉字数。 */
  longest_len: number;
  /** 最长句句序（1 起，含并列）。 */
  longest_seq: number[];
  /** 阈值 = ⌈汉字总数 ÷ 句数⌉。 */
  threshold: number;
  /** 声情转向。 */
  scene: '后段上升' | '后段下降' | '前后持平';
}

export interface MetricsApi {
  /** 计算声律指标。 */
  compute(lines: Line[]): MetricsResult;
  /** 银行家舍入到一位小数（15/48=31.25 → 31.2）。 */
  banker1(x: number): number;
  /** 只保留汉字（CJK 基本区 + 扩展 A）。 */
  hanOnly(s: string): string;
  /** 汉字个数。 */
  hanLen(s: string): number;
  /** 数 `ch` 在 `s` 里的出现次数。 */
  count(s: string, ch: string): number;
  /** 汉字判定正则。 */
  HAN: RegExp;
}

export interface UIApi {
  /** 全局样式（注入到 <style>）。 */
  CSS: string;
  /** 把样式注入文档。 */
  inject(): void;
  /** HTML 转义。 */
  esc(s: unknown): string;
  /** 属性值转义（含引号）。 */
  attr(s: unknown): string;
  /** 把「平/仄」串渲染成带样式的 span。 */
  hz(s: string): string;
  /** 渲染小徽标。 */
  badge(text: string, kind?: string): string;
  /** 千分位整数。 */
  fmtInt(n: number): string;
  /** 一位小数（非有限值显示「—」）。 */
  fmt1(v: number): string;
  /** 带正负号的一位小数。 */
  signed(v: number): string;
  /** 二维数组转 CSV 文本。 */
  csvText(rows: unknown[][]): string;
  /** 触发浏览器下载。 */
  download(text: string, filename: string, mime?: string): void;
  /** 轻提示。 */
  toast(msg: string, kind?: string): void;
  /** 加载指示器 HTML。 */
  spinner(text?: string): string;
  /** 读取当前 URL 查询参数。 */
  query(key: string, search?: string): string;
  /** 页脚 HTML。 */
  footer(stamp?: string, source?: string, n?: number): string;
  /** 挂载主题切换。 */
  mountTheme(root?: HTMLElement | null): void;
}

export interface ParseHit {
  /** 篇 id。 */
  pid: string;
  dynasty: string;
  author: string;
  cipai: string;
  title: string;
  source: string;
  sent_n: number;
  han_len: number;
  ping: number;
  ze: number;
  ze_ratio: number;
  scene: string;
  change: number;
  longest_len: number;
  threshold: number;
  /** 命中该条件的句数。 */
  n_match: number;
  lines: Line[];
  [k: string]: unknown;
}

export interface SearchResult {
  /** 命中篇数。 */
  total: number;
  /** 当前页命中。 */
  hits: ParseHit[];
  /** 分面统计。 */
  facets: Record<string, Array<{ v: string; n: number }>>;
  /** 耗时（毫秒）。 */
  ms: number;
}

export interface PageSlice {
  page: number;
  pages: number;
  hits: ParseHit[];
  total: number;
}

export interface ParseApi {
  /** 载入全库数据（离线视图用）。 */
  setData(rows: ParseHit[], tmap?: Record<string, unknown>): void;
  /** 载入服务端结果（在线模式用）。 */
  setLive(res: SearchResult): void;
  /** 当前是否为在线模式。 */
  isLive(): boolean;
  /** 解析一篇（分词 + 逐字平仄 + 指标）。 */
  analyze(pid: string): { sents: string[]; lines: Line[]; metrics: MetricsResult } | null;
  /** 取一篇的元信息行。 */
  info(pid: string): Array<[string, string]>;
  /** 断句。 */
  splitSents(text: string): string[];
  /** 逐字平仄串。 */
  pzOf(text: string): PZ;
  /** 句脚。 */
  tailOf(text: string): string;
  /** 判断一篇是否满足条件。 */
  matchCond(row: ParseHit, cond: Record<string, unknown>): boolean;
  /** 平仄判断。 */
  pzTest(ch: string, want: string): boolean;
  /** 离线检索（与 Python 引擎同口径）。 */
  searchOffline(cond: Record<string, unknown>): SearchResult;
  /** 渲染一篇详情 HTML。 */
  detailHtml(pid: string, cond?: Record<string, unknown>): string;
  /** 渲染列表行 HTML。 */
  listRow(row: ParseHit, no: number, cond?: Record<string, unknown>): string;
  /** 分面统计。 */
  facets(hits: ParseHit[]): Record<string, Array<{ v: string; n: number }>>;
  /** 条件描述文本。 */
  condText(cond: Record<string, unknown>): string;
  /** 关键词高亮。 */
  highlight(text: string, kw?: string): string;
  /** 分页切片。 */
  pageSlice(hits: ParseHit[], page: number, size: number): PageSlice;
  textHit(text: string, cond: Record<string, unknown>): boolean;
  resetCache(): void;
  allHits(): ParseHit[];
  _internals: Record<string, unknown>;
}

export interface ReviewRow {
  pid: string;
  author: string;
  cipai: string;
  title: string;
  char: string;
  before: string;
  after: string;
  count: number;
  note: string;
  [k: string]: unknown;
}

export interface ReviewCol {
  key: string;
  label: string;
  numeric?: boolean;
}

export interface ReviewApi {
  /** 表格列定义。 */
  COLS: ReviewCol[];
  /** 队列统计。 */
  stats(rows: ReviewRow[]): { total: number; chars: number; top: Array<{ char: string; n: number }> };
  /** 按条件筛选。 */
  filter(rows: ReviewRow[], cond: Record<string, unknown>): ReviewRow[];
  /** 排序。 */
  sortRows(rows: ReviewRow[], key: string, dir: 'asc' | 'desc'): ReviewRow[];
  /** 渲染一行 HTML。 */
  rowHtml(row: ReviewRow): string;
}

export interface AnswerBlock {
  eid: string;
  dynasty: string;
  author: string;
  cipai?: string;
  title?: string;
  [k: string]: unknown;
}

export interface AskApi {
  /** 渲染整份答案 HTML。 */
  askHtml(res: Record<string, unknown>): string;
  /** 渲染单个篇块。 */
  blockHtml(block: AnswerBlock): string;
  /** 渲染错误 HTML。 */
  renderErrorHtml(err: unknown): string;
}

declare global {
  interface Window {
    Metrics: MetricsApi;
    UI: UIApi;
    ParseApp: ParseApi;
    ReviewApp: ReviewApi;
    AskApp: AskApi;
    /** 离线数据包（由 build_views.py 生成的 pack.js 注入）。 */
    __PACK__?: { tonemap: Record<string, unknown>; rows: ParseHit[] };
    /** 校订队列数据（rev.js 注入）。 */
    __REV__?: ReviewRow[];
    /** 构建时间戳（stamp.js 注入）。 */
    __STAMP__?: string;
    /** API 基址：空串＝同源；null/undefined＝离线。 */
    __API_BASE__?: string | null;
  }
}
