/* vmload.js —— 前端门禁共用的「把浏览器脚本装进 node」的小工具（唯一来源）。
 *
 * 为什么要真跑：页面里的 bug 常常只在**执行时**才现形（比如把字符串当数字减）。 
 * 只做静态检查抓不到；这里造一个最小 DOM 桩 + vm 上下文，把页面脚本原样跑起来。
 * 审计过的坑：script 里若用到 location / window / document 的某项而桩里没有，
 * 会以「脚本一运行就抛异常」的形式暴露——那正是我们想要看到的失败，不要静默吞掉。
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

function makeCtx(extra) {
  const stubs = {};
  function el() {
    return {
      innerHTML: '', textContent: '', value: '', style: {}, dataset: {},
      classList: { add() {}, remove() {}, contains() { return false; } },
      appendChild() {}, setAttribute() {}, getAttribute() { return null; },
      addEventListener() {}, removeEventListener() {}, click() {},
      querySelectorAll() { return []; }
    };
  }
  const document = {
    head: el(), body: el(),
    documentElement: { getAttribute() { return null; }, setAttribute() {} },
    getElementById(id) { if (!stubs[id]) { stubs[id] = el(); } return stubs[id]; },
    createElement() { return el(); },
    addEventListener() {}, querySelectorAll() { return []; }
  };
  const sandbox = { document: document, console: { log() {}, warn() {} },
                    location: { search: '', href: '' }, setTimeout() {}, clearTimeout() {},
                    module: undefined, exports: undefined };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  sandbox.globalThis = sandbox;
  if (extra) { Object.keys(extra).forEach(k => { sandbox[k] = extra[k]; }); }
  vm.createContext(sandbox);
  return { sandbox: sandbox, stubs: stubs };
}

function load(ctx, file) {
  vm.runInContext(fs.readFileSync(file, 'utf8'), ctx.sandbox, { filename: file, timeout: 300000 });
  return ctx.sandbox;
}

const WEB = __dirname;
module.exports = {
  makeCtx: makeCtx,
  load: load,
  web: WEB,
  data: require('path').join(WEB, '..', 'data'),
  /* 把 metrics.js + ui.js + app_*.js 装进同一个上下文（页面里的加载顺序） */
  boot() {
    const ctx = makeCtx();
    ['metrics.js', 'ui.js', 'app_parse.js', 'app_review.js'].forEach(f => load(ctx, require('path').join(WEB, f)));
    return ctx;
  }
};
