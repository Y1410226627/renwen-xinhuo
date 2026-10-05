/* types/shims.d.ts —— 让 TS 认识 Vite 的资源导入与非 TS 模块。 */

declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>;
  export default component;
}

declare module '*.mjs' {
  const mod: Record<string, unknown>;
  export default mod;
}

declare module '*.css' {
  const css: string;
  export default css;
}

declare module '*.html?raw' {
  const html: string;
  export default html;
}
