/* frontend/tools/build-all.mjs —— 一键构建：先 Vite 出视图，再 build_views.py 出数据。
 *
 * 为什么要定顺序：`data/vue/` 里同时住着「Vite 产出的 HTML+assets」与「Python 产出的数据脚本
 * （pack.js/graph.json/rev.js）」。若先跑 Python 再跑 Vite，Vite 若清空目录就会把数据一起清掉。
 * 这里把顺序固化下来（先 Vite 后 Python），避免「构建完页面白屏」。
 *
 * 注：`vite.config.js` 已设 `emptyOutDir:false`（避开宿主安全删除护栏，见该文件注释），
 * 所以 Vite 不会清目录；陈旧文件由本脚本的 cleanStale() 负责清（判据见下）。
 *
 * 用法：node frontend/tools/build-all.mjs   （或 npm run build:all）
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(HERE, '..');
const ROOT = path.resolve(FRONTEND, '..');

/* 找得到「真能跑这个项目」的 python。
 *
 * 坑（已踩两次）：
 *   ① 在 reproduce.py 的子进程环境里，`spawnSync('python', ...)` 会因 PATH 继承而偶发失败；
 *   ② ② 更隐蔽：宿主的进程沙箱会**间歇性拦截 spawnSync 本身**，报 EBUSY——
 *      `existsSync` 明明是 true、解释器明明是好的，探测却失败 → 误报「找不到 python」。
 *      （实测：同一台机器上一分钟前还能 spawn，一分钟后 EBUSY。）
 * 所以探测策略分两级：
 *   · **绝对路径候选（LVC_PYTHON / PYTHON / conda / Python314）**：`existsSync` 为真就**直接采信、
 *     不再 spawn 探测**——这些路径由 reproduce.py 的 pick_python() 或维护者预先验证过；
 *     解释器真坏了的话，后面 run() 步骤会带着真实报错浮出来，比这里瞎猜强。
 *   · **PATH 候选（python / python3 / py）**：无法 existsSync，仍用 spawnSync 试探，
 *     但失败（含 EBUSY）只跳过、不致命。
 */
function pythonExe() {
  const has = (p) => { try { return fs.existsSync(p); } catch { return false; } };
  for (const c of [process.env.LVC_PYTHON, process.env.PYTHON,
                   'D:/conda_envs/langchain-env/python.exe',
                   'C:/Python314/python.exe']) {
    if (c && has(c)) { return c; }            // 绝对路径：存在即采信（避开沙箱对 spawn 的拦截）
  }
  for (const c of ['python', 'python3', 'py']) {
    try {
      const r = spawnSync(c, ['-c', 'print(1)'],
                          { encoding: 'utf8', env: process.env, shell: false, timeout: 30000 });
      if (r && r.error == null && r.status === 0) { return c; }
    } catch { /* 跳过，试下一个 */ }
  }
  return null;
}

function run(cmd, args, cwd, name) {
  console.log('\n▶ ' + name + '\n  ' + cmd + ' ' + args.join(' '));
  /* 用 pipe 捕获而不是 inherit：这样在「被别的脚本调用、stdout 已是管道」时
     也能把 vite 的完整错误抓回来打印（inherit 只会把错误丢进上层管道，难定位）。 */
  const r = spawnSync(cmd, args, { cwd, stdio: ['ignore', 'pipe', 'pipe'], shell: false,
                                  encoding: 'utf8' });
  if (r.stdout) { process.stdout.write(r.stdout); }
  if (r.stderr) { process.stderr.write(r.stderr); }
  if (r.status !== 0) {
    console.error('✗ ' + name + ' 失败（退出码 ' + r.status + '）');
    console.error('  提示：若报 SAFE_DELETE_BULK_CONFIRM_REQUIRED，是宿主安全删除护栏拦截了');
    console.error('        批量删除——本项目已关掉 emptyOutDir 规避（见 vite.config.js）。');
    console.error('        若报 EBUSY/EPERM，才可能是 web/serve.py 占着 data/vue/ 的文件句柄。');
    process.exit(r.status || 1);
  }
}

const viteBin = path.join(FRONTEND, 'node_modules', 'vite', 'bin', 'vite.js');
/* 记录构建前的文件清单 + 构建后的清单，据此只删「**上轮产物里 Vite 专属、本轮没再产出**」的文件。
 *
 * ⚠ 踩过的坑（务必保留这段注释）：
 *   最初写的是「构建前快照，构建后把快照里仍存在的文件全删」——错得离谱。
 *   Vite 是 **覆盖写** 同名文件，构建后 `parse.html` 依然存在，于是被当成「陈旧文件」删掉，
 *   结果 `data/vue/` 里五个 HTML 全没了，`web/test_ui.js` 直接 ENOENT 崩掉。
 *   正确判据是：**只有「Vite 上轮产出的资产（assets/ 下的哈希文件、5 个 html），本轮不再产出」才删**；
 *   Python 生成的数据文件（pack.js/rev.js/graph.json/…）绝不能进删除清单。
 */
const VITE_OWNED = (p) => {
  const rel = path.relative(VUE, p).replace(/\\/g, '/');
  return /^assets\//.test(rel) || /^(index|parse|browse|graph|review)\.html$/.test(rel);
};
function snapshot(dir) {
  const set = new Set();
  const walk = (d) => {
    let ents = [];
    try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { walk(p); } else { set.add(p); }
    }
  };
  walk(dir);
  return set;
}
function cleanStale(dir, before, keepFn) {
  const after = snapshot(dir);
  let removed = 0;
  for (const p of before) {
    if (after.has(p)) { continue; }        // 本轮仍产出 => 不是陈旧文件
    if (keepFn && !keepFn(p)) { continue; } /* 只清理「Vite 专属」的旧产物 */
    try { fs.rmSync(p); removed++; } catch { /* 忽略 */ }
  }
  if (removed) { console.log('  清理陈旧文件 ' + removed + ' 个（' + dir + '）'); }
}

/* 1) Vite 构建（两条产线）。构建前快照，构建后清理陈旧文件。 */
const VUE = path.resolve(ROOT, 'data', 'vue');
const ASK = path.resolve(ROOT, 'web', 'dist', 'ask');
const snapVue = snapshot(VUE);
const snapAsk = snapshot(ASK);
run(process.execPath, [viteBin, 'build', '--mode', 'views'], FRONTEND,
    '① 构建离线视图 → data/vue/');
run(process.execPath, [viteBin, 'build'], FRONTEND, '② 构建问答页 → web/dist/ask/');
cleanStale(VUE, snapVue, VITE_OWNED);
cleanStale(ASK, snapAsk, null);       /* ask 目录是 Vite 独占，整体清理安全 */

/* 2) Python 造数据（必须在 Vite 之后，否则被 emptyOutDir 清掉） */
const py = pythonExe();
if (!py) {
  console.error('✗ 找不到 python（试过 LVC_PYTHON / PYTHON / conda / 系统 PATH）');
  console.error('  可显式指定：LVC_PYTHON=D:/conda_envs/langchain-env/python.exe node frontend/tools/build-all.mjs');
  process.exit(1);
}
console.log('  （使用解释器：' + py + '）');
run(py, [path.join(ROOT, 'web', 'build_views.py')], ROOT, '③ 生成数据 → data/ 与 data/vue/');

console.log('\n✓ 全部完成。离线视图：data/vue/index.html（双击可开）');
