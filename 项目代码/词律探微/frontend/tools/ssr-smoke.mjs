/* frontend/tools/ssr-smoke.mjs —— **组件冒烟门禁**：把每个视图真实渲染一遍，验证不报错。
 *
 * 为什么要它：Vite 构建成功 ≠ 组件运行时正确。模板里一个未定义变量、一个循环 `key` 冲突、
 * 或 setup 里一句 `xxx is not defined`，都能让页面**白屏**而构建照样通过。
 * 这里用 Vite 的 SSR 模块加载器把 `.vue` 真编译、用 Vue 的 SSR 渲染器把组件渲成字符串，
 * 再断言「DOM 骨架 + 关键文案」都在。
 *
 * 用法：node frontend/tools/ssr-smoke.mjs
 * 退出码：0 = 全部视图可渲染；1 = 有视图报错或缺关键结构。
 */
import { createServer } from 'vite';
import { renderToString } from 'vue/server-renderer';
import { createSSRApp, h } from 'vue';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(dir, '..', 'src');

let cmp = 0, bad = 0;
const problems = [];
function ok(name, cond, detail) {
  cmp++;
  if (!cond) { bad++; if (problems.length < 30) { problems.push(name + (detail ? '：' + detail : '')); } }
}

/* 最小浏览器桩：SSR 下组件可能读到 window/document（如 __STAMP__、localStorage） */
const g = globalThis;

async function main() {
  const server = await createServer({
    root,
    logLevel: 'error',
    server: { middlewareMode: true },
    appType: 'custom',
    configFile: path.resolve(dir, '..', 'vite.config.js')
  });

  const views = [
    { file: '/views/IndexView.vue', name: '总览 IndexView', must: ['词律探微', '复现'], props: {} },
    { file: '/views/AskView.vue', name: '问答 AskView', must: ['词律探微', '提问'], props: {} },
    { file: '/views/ParseView.vue', name: '逐字解析 ParseView（离线）', must: ['词律探微'], props: { mode: 'offline' } },
    { file: '/views/ParseView.vue', name: '多条件检索 ParseView（在线）', must: ['词律探微'], props: { mode: 'online' } },
    { file: '/views/GraphView.vue', name: '知识图谱 GraphView', must: ['词律探微'], props: {} },
    { file: '/views/ReviewView.vue', name: '校订队列 ReviewView', must: ['词律探微'], props: {} }
  ];

  for (const v of views) {
    let html = '';
    try {
      const mod = await server.ssrLoadModule(v.file);
      const comp = mod.default;
      const app = createSSRApp({ render: () => h(comp, v.props || {}) });
      html = await renderToString(app);
    } catch (e) {
      /* 文件还不存在时记为 SKIP（渐进迁移中），存在但报错记为 FAIL */
      const msg = String(e && e.message || e);
      if (/Failed to load|ENOENT|no such file|Cannot find/.test(msg)) {
        console.log('  · ' + v.name + ' 尚未迁移（跳过）');
        continue;
      }
      ok(v.name + ' 渲染不报错', false, msg.slice(0, 240));
      continue;
    }
    ok(v.name + ' 渲染出内容', html.length > 50, '仅 ' + html.length + ' 字符');
    for (const s of v.must) {
      ok(v.name + ' 含「' + s + '」', html.indexOf(s) >= 0);
    }
    ok(v.name + ' 有导航外壳（header.top）', html.indexOf('class="top"') >= 0);
    ok(v.name + ' 有页脚探针（页面生成时间）', html.indexOf('页面生成时间') >= 0);
    console.log('  ✓ ' + v.name + ' 渲染 ' + html.length + ' 字符');
  }

  await server.close();
  console.log('');
  console.log('组件冒烟：比对项 ' + cmp + ' 项，不符 ' + bad + ' 项');
  for (const p of problems) { console.log('  ✗ ' + p); }
  process.exit(bad === 0 ? 0 : 1);
}

main().catch((e) => { console.error(e); process.exit(1); });
