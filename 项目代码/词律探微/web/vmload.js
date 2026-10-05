/* vmload.js —— 前端门禁共用的「把浏览器脚本装进 node」的小工具（唯一来源）。
 *
 * 为什么要真跑：页面里的 bug 常常只在**执行时**才现形（比如把字符串当数字减）。 
 * 只做静态检查抓不到；这里造一个最小 DOM 桩 + vm 上下文，把页面脚本原样跑起来。
 * 审计过的坑：script 里若用到 location / window / document 的某项而桩里没有，
 * 会以「脚本一运行就抛异常」的形式暴露——那正是我们想要看到的失败，不要静默吞掉。
 *
 * ⚠ 2026-10-05（D15 前端架构）：逻辑层真源已迁到 `frontend/src/core/`，`web/*.js` 退化为
 *   薄转发（`module.exports = require('../frontend/src/core/xxx.js')`）。但 `vm` 沙箱里
 *   默认**没有 `require`**，加载薄转发会报 `ReferenceError: require is not defined`。
 *   故这里给沙箱注入一个**受控 require**（只允许加载 core 目录内的文件），
 *   于是「门禁加载 web/ 转发文件」与「门禁直接加载 core 真源」两条路都走得通，
 *   断言与期望值一字不改。
 */
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

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
  /* 受控 require：只允许加载 frontend/src/core/ 下的文件（薄转发指向的正是那里）。
     其余路径一律抛错——沙箱不该能任意读盘。 */
  const CORE = path.join(__dirname, '..', 'frontend', 'src', 'core');
  sandbox.require = function (spec) {
    let p = spec;
    if (p.charAt(0) === '.') { p = path.resolve(CORE, p); }
    const full = path.extname(p) ? p : p + '.js';
    if (path.dirname(full) !== CORE) {
      throw new Error('沙箱 require 只允许加载 core/ 目录：' + spec);
    }
    if (!fs.existsSync(full)) { throw new Error('沙箱 require 找不到：' + full); }
    const mod = { exports: {} };
    const sub = vm.createContext({ module: mod, exports: mod.exports, require: sandbox.require,
                                   window: sandbox, globalThis: sandbox, console: console });
    sub.self = sub;
    vm.runInContext(fs.readFileSync(full, 'utf8'), sub, { filename: full, timeout: 300000 });
    return mod.exports;
  };
  if (extra) { Object.keys(extra).forEach(k => { sandbox[k] = extra[k]; }); }
  vm.createContext(sandbox);
  return { sandbox: sandbox, stubs: stubs };
}

function load(ctx, file) {
  vm.runInContext(fs.readFileSync(file, 'utf8'), ctx.sandbox, { filename: file, timeout: 300000 });
  return ctx.sandbox;
}

const WEB = __dirname;
const CORE = path.join(WEB, '..', 'frontend', 'src', 'core');
const VUE = path.join(WEB, '..', 'data', 'vue');
module.exports = {
  makeCtx: makeCtx,
  load: load,
  web: WEB,
  core: CORE,
  vue: VUE,
  data: path.join(WEB, '..', 'data'),
  /* 把逻辑层真源装进同一个上下文（页面里的加载顺序）。
     优先用 core/ 真源（门禁本来就该测真源）；core 缺失时退回 web/ 下的转发文件。 */
  boot() {
    const ctx = makeCtx();
    const names = ['metrics.js', 'ui.js', 'parse.js', 'review.js', 'ask.js'];
    const coreOk = fs.existsSync(path.join(CORE, 'parse.js'));
    names.forEach(n => {
      const f = coreOk ? path.join(CORE, n)
                       : path.join(WEB, { 'parse.js': 'app_parse.js', 'review.js': 'app_review.js',
                                          'ask.js': 'app_ask.js' }[n] || n);
      load(ctx, f);
    });
    return ctx;
  }
};
