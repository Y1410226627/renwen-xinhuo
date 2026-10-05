/* vite.config.js —— 构建配置（词律探微前端）。
 *
 * 输出策略（两条产线，互不干扰）：
 *   ① `npm run build`（默认 mode=app）：产出 **问答页**（在线服务用），到 `../web/dist/ask/`。
 *      serve.py 以 /(根) 提供该页；资源用**相对路径**（base:'./'），file:// 也能开。
 *   ② `npm run build:views`（mode=views）：产出**四个离线视图**（parse/browse/graph/review/index），
 *      多页入口，到 `../data/vue/`；由 build_views.py 或页面直接从 data/ 打开。
 *
 * 为什么分两条：离线视图要「双击 HTML 就能看」（不需要起服务、不需要 node_modules），
 * 在线问答要「接 /api」。两者资源与数据来源不同，分开产出最省事、也最不容易互相污染。
 */
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const dir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const isViews = mode === 'views';
  const outDir = isViews
    ? path.resolve(dir, '..', 'data', 'vue')
    : path.resolve(dir, '..', 'web', 'dist', 'ask');

  return {
    root: path.resolve(dir, 'src'),
    base: './',                       // 相对路径：file:// 与 http:// 都能开
    publicDir: path.resolve(dir, 'public'),
    plugins: [vue()],
    resolve: {
      alias: { '@': path.resolve(dir, 'src') }
    },
    build: {
      outDir,
      /* ⚠ emptyOutDir 必须为 false：
       *   Vite 默认会在构建前 `fs.rmSync(outDir)` 清空旧产物。在本项目的构建环境里，
       *   删除 ≥50 个文件会被宿主的安全删除护栏拦截（报 SAFE_DELETE_BULK_CONFIRM_REQUIRED），
       *   导致构建 exit 1。而且 `data/vue/` 里还混着 Python 生成的 pack.js / rev.js / graph.json，
       *   清空目录本来就会误删它们。
       *   改为：**不做目录清空**，只让 Vite 覆盖同名文件；build-all.mjs 负责清理「陈旧」的文件。 */
      emptyOutDir: false,
      target: 'es2019',               // 兼容较老的评审机浏览器
      assetsDir: 'assets',
      rollupOptions: isViews
        ? {
            input: {
              index: path.resolve(dir, 'src', 'index.html'),
              parse: path.resolve(dir, 'src', 'parse.html'),
              browse: path.resolve(dir, 'src', 'browse.html'),
              graph: path.resolve(dir, 'src', 'graph.html'),
              review: path.resolve(dir, 'src', 'review.html')
            }
          }
        : {
            input: { ask: path.resolve(dir, 'src', 'ask.html') }
          }
    }
  };
});
