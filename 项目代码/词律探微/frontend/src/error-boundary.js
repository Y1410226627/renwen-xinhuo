/* src/error-boundary.js —— 全局错误兜底：任何组件渲染期抛错都不再「整页白屏」。
 *
 * 背景（2026-10-16 前端审查 P1）：8 个入口原本只有 `createApp(X).mount('#app')`，
 *   既没有 `app.config.errorHandler`，也没有 `onErrorCaptured`。Vue 3 里组件渲染抛错若无人
 *   接管，出错的那棵子树就渲染成空 —— 用户看到的是**整页白**，且没有任何提示，
 *   完全无法判断是「服务没起 / 数据没生成 / 代码 bug」。
 *
 * 做法：给每个 app 装一个 errorHandler。捕获后：
 *   ① 把错误照常打到 console（便于排查）；
 *   ② 在页面顶部插一张**错误卡**（含「刷新」按钮与出错环节），保证用户至少知道发生了什么。
 * 卡片用内联样式，不依赖 core/ui.js 是否已注入 —— 万一错就出在样式注入阶段也能显示。
 *
 * 为什么不用 onErrorCaptured：那需要额外包一层根组件（改动 8 个入口的挂载方式）。
 *   errorHandler 是 Vue 官方提供的**应用级**兜底，一行接入、零结构改动。
 *
 * 影响面：本文件在 D07 结构性隔离之外（改 frontend/ 不影响交付答案哈希）。
 */
const CARD_ID = 'lvc-fatal-card';

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/* 插入/更新错误卡（幂等：同一页面多次出错只保留一张，内容取最新）。 */
function showCard(err, info) {
  if (typeof document === 'undefined' || !document.body) { return; }
  let el = document.getElementById(CARD_ID);
  if (!el) {
    el = document.createElement('div');
    el.id = CARD_ID;
    el.setAttribute('role', 'alert');
    el.setAttribute('aria-live', 'assertive');
    el.style.cssText = 'position:fixed;left:50%;top:14px;transform:translateX(-50%);'
      + 'z-index:9999;max-width:min(720px,92vw);background:#fbf8f1;color:#292722;'
      + 'border:1px solid #8e3025;border-left:6px solid #8e3025;border-radius:8px;'
      + 'box-shadow:0 8px 24px rgba(74,58,38,.18);padding:12px 16px;'
      + 'font:14px/1.7 "FangSong","仿宋",serif;';
    document.body.appendChild(el);
  }
  const msg = (err && (err.message || String(err))) || '未知错误';
  el.innerHTML = '<b style="color:#8e3025">页面出现异常，部分内容没能渲染</b>'
    + '<div style="font-size:12.5px;color:#6b6558;margin-top:4px">出错环节：'
    + esc(info || '—') + '</div>'
    + '<div style="font-size:12.5px;color:#6b6558">' + esc(String(msg).slice(0, 300)) + '</div>'
    + '<div style="margin-top:6px">可试：按 <b>Ctrl+F5</b> 强制刷新；若仍复现，'
    + '请把上面「出错环节」一并记录。</div>'
    + '<button type="button" style="margin-top:8px;padding:5px 14px;border:1px solid #a64333;'
    + 'background:#f6f0e4;color:#a64333;border-radius:4px;cursor:pointer">刷新页面</button>';
  const btn = el.querySelector('button');
  if (btn) { btn.addEventListener('click', function () { location.reload(); }); }
}

/* 给一个 Vue app 装上应用级错误兜底。用法：
 *   const app = createApp(View); installErrorHandler(app); app.mount('#app'); */
export function installErrorHandler(app) {
  app.config.errorHandler = function (err, instance, info) {
    try { console.error('[词律探微] 组件异常（' + info + '）', err); } catch (e) { /* 忽略 */ }
    showCard(err, info);
  };
  return app;
}
