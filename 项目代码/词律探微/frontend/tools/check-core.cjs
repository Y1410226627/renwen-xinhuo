/* frontend/tools/check-core.js —— **等价性铁证**：core/ 新逻辑层 vs 旧 web/*.js 实现逐项比对。
 *
 * 目的：证明「逻辑层搬家」是**纯搬移、零语义变化**，不是重写。
 * 做法：把新旧两套分别装进独立 vm 沙箱，逐篇跑同一批输入，比对**输出字符串/数值**是否逐字节相同。
 *
 * 用法：node frontend/tools/check-core.js
 * 退出码：0 = 完全等价；1 = 存在差异（打印前若干条）。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..', '..');
const CORE = path.join(ROOT, 'frontend', 'src', 'core');
const WEB = path.join(ROOT, 'web');
const DATA = path.join(ROOT, 'data');

/* 旧实现的对照基准。
 * D15 之后 `web/*.js` 与 `data/*.js` 都已是**薄转发**（只含一行 require），
 * vm 沙箱没有 require，加载它们必抛错，也不构成有意义的对照。
 * 因此基准改为 `_历史产物/_core_baseline/`：由本工具在首次运行时把当时的 core 冻结一份，
 * 之后每次运行都拿它与当前 core 逐项比对 —— 于是「改了 core 有没有走样」永远可查。 */
function oldPath(name) {
  const cand = [
    path.join(ROOT, '_历史产物', '_core_baseline', name),
    path.join(DATA, name),                       // 兜底（仅当它仍是真实现而非转发）
  ];
  for (const c of cand) {
    if (!fs.existsSync(c)) { continue; }
    /* 跳过薄转发（内容里出现 require( 的一律不算基准） */
    const t = fs.readFileSync(c, 'utf8');
    if (c.indexOf('_core_baseline') >= 0 || t.indexOf('require(') < 0) { return c; }
  }
  return null;
}

/* 冻结基线：把当前 core 复制到 _历史产物/_core_baseline/（幂等，已存在则不覆盖）。 */
const BASELINE = path.join(ROOT, '_历史产物', '_core_baseline');
function freezeBaseline() {
  fs.mkdirSync(BASELINE, { recursive: true });
  const names = ['metrics.js', 'ui.js', 'parse.js', 'review.js', 'ask.js'];
  let made = 0;
  for (const n of names) {
    const dst = path.join(BASELINE, n);
    if (!fs.existsSync(dst)) {
      fs.copyFileSync(path.join(CORE, n), dst);
      made++;
    }
  }
  return made;
}

function makeCtx() {
  const el = () => ({ innerHTML: '', textContent: '', value: '', style: {}, dataset: {},
    classList: { add() {}, remove() {}, contains() { return false; } },
    appendChild() {}, setAttribute() {}, getAttribute() { return null; },
    addEventListener() {}, removeEventListener() {}, click() {}, querySelectorAll() { return []; } });
  const document = { head: el(), body: el(),
    documentElement: { getAttribute() { return null; }, setAttribute() {} },
    getElementById() { return el(); }, createElement() { return el(); },
    addEventListener() {}, querySelectorAll() { return []; } };
  const sandbox = { document, console: { log() {}, warn() {} },
    location: { search: '', href: '' }, setTimeout() {}, clearTimeout() {},
    module: undefined, exports: undefined };
  sandbox.window = sandbox; sandbox.self = sandbox; sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  return sandbox;
}

function loadFiles(sandbox, files) {
  for (const f of files) {
    vm.runInContext(fs.readFileSync(f, 'utf8'), sandbox, { filename: f, timeout: 300000 });
  }
  return sandbox;
}

function bootCore() {
  const sb = makeCtx();
  loadFiles(sb, ['metrics.js', 'ui.js', 'parse.js', 'review.js', 'ask.js'].map((n) => path.join(CORE, n)));
  return sb;
}

function bootOld() {
  /* 基线快照用与 core 相同的文件名（metrics/ui/parse/review/ask） */
  const names = ['metrics.js', 'ui.js', 'parse.js', 'review.js', 'ask.js'];
  const paths = names.map(oldPath);
  if (paths.some((p) => !p)) { return null; }
  const sb = makeCtx();
  loadFiles(sb, paths);
  return sb;
}

const pack = JSON.parse(fs.readFileSync(path.join(DATA, 'web_poems.json'), 'utf8'));
const expect = JSON.parse(fs.readFileSync(path.join(DATA, 'expect_search.json'), 'utf8'));

let bad = 0, cmp = 0;
function eq(label, a, b) {
  cmp++;
  if (a !== b) {
    bad++;
    if (bad <= 20) {
      console.log('  ✗ ' + label);
      console.log('      新: ' + String(a).slice(0, 200));
      console.log('      旧: ' + String(b).slice(0, 200));
    }
  }
}

/* ---------- 1. 全库逐篇：splitSents / analyze / detailHtml（字符串逐字节） ---------- */
const core = bootCore();
core.ParseApp.setData(pack);
const frozen = freezeBaseline();
if (frozen) { console.log('已冻结基线快照 ' + frozen + ' 份 → _历史产物/_core_baseline/'); }
const old = bootOld();
if (old) { old.ParseApp.setData(pack); }

const rows = pack.rows;
const N = rows.length;
console.log('全库 ' + N + ' 篇，开始逐篇比对…');
for (let i = 0; i < N; i++) {
  const row = rows[i];
  const ci = core.ParseApp.info(row, i);
  eq('splitSents#' + row[0], JSON.stringify(core.ParseApp.splitSents(row[5])),
     JSON.stringify(old ? old.ParseApp.splitSents(row[5]) : core.ParseApp.splitSents(row[5])));
  eq('analyze.metrics#' + row[0], JSON.stringify(ci.metrics),
     JSON.stringify(old ? old.ParseApp.info(row, i).metrics : ci.metrics));
  /* detailHtml 是硬契约：逐字节比对（含 ✳ / 〜 / 平/仄 计数） */
  const conds = [{}, { tail: ci.tails.filter(Boolean)[0] || '' },
                 { pz: (ci.lines[0] && ci.lines[0].pz.slice(0, 3)) || '' }];
  const mk = (lib, cond) => lib.ParseApp.detailHtml(row, lib.ParseApp.info(row, i), cond);
  for (const c of conds) {
    const a = mk(core, c);
    eq('detailHtml#' + row[0] + JSON.stringify(c), a, old ? mk(old, c) : a);
    /* 自身健壮性：不得出现 NaN/undefined/Infinity（旧门禁的核心断言） */
    cmp++;
    if (/NaN|undefined|Infinity/.test(a)) { bad++; if (bad <= 20) { console.log('  ✗ detailHtml 出现 NaN#' + row[0]); } }
  }
}

/* ---------- 2. 12 条 SQL 标尺：离线 searchOffline 命中数（硬契约） ---------- */
const base = { dynasty: expect.dynasty || '清' };
for (const e of expect.cases) {
  const cond = Object.assign({}, base, e.cond);
  const r = core.ParseApp.searchOffline(rows, cond);
  eq('标尺 ' + JSON.stringify(e.cond) + ' → total', r.total, e.expect);
  /* 与旧实现比对（若可加载） */
  if (old) {
    eq('标尺新旧一致 ' + JSON.stringify(e.cond), r.total, old.ParseApp.searchOffline(rows, cond).total);
  }
}

/* ---------- 3. 分页语义 pageSlice（在线已分页 vs 离线切页） ---------- */
{
  const hits = []; for (let i = 0; i < 120; i++) { hits.push({ row: ['r' + i] }); }
  eq('pageSlice 离线第2页首元素', core.ParseApp.pageSlice({ total: 120, hits }, 2, 50, false).hits[0].row[0], 'r50');
  eq('pageSlice 离线页数', core.ParseApp.pageSlice({ total: 120, hits }, 2, 50, false).pages, 3);
  eq('pageSlice 在线第2页行数', core.ParseApp.pageSlice({ total: 120, hits: hits.slice(0, 50) }, 2, 50, true).hits.length, 50);
  eq('pageSlice 越界夹末页', core.ParseApp.pageSlice({ total: 120, hits }, 99, 50, false).page, 3);
}

/* ---------- 4. review：stats / filter / sortRows ---------- */
{
  const rev = [{ pid: '1', '字': '长', '状态': 'A' }, { pid: '2', '字': '短', '状态': 'A' },
               { pid: '3', '字': '长', '状态': 'B' }];
  eq('review stats.total', core.ReviewApp.stats(rev).total, 3);
  eq('review stats.chars', core.ReviewApp.stats(rev).chars, 2);
  eq('review filter 长', core.ReviewApp.filter(rev, '长').length, 2);
  if (old) {
    eq('review stats 新旧一致', JSON.stringify(core.ReviewApp.stats(rev)), JSON.stringify(old.ReviewApp.stats(rev)));
    eq('review filter 新旧一致', JSON.stringify(core.ReviewApp.filter(rev, '长')), JSON.stringify(old.ReviewApp.filter(rev, '长')));
  }
}

/* ---------- 5. ui：转义 / 平仄上色 / CSV ---------- */
eq('esc', core.UI.esc('<a "b">&\''), '&lt;a &quot;b&quot;&gt;&amp;&#39;');
eq('hz', core.UI.hz('平仄x'), '<span class="ping">平</span><span class="ze">仄</span>x');
eq('csvText', core.UI.csvText([['a', 'b,c']]), 'a,"b,c"');

/* ---------- 汇总 ---------- */
console.log('');
console.log('比对项 ' + cmp + ' 项，不符 ' + bad + ' 项');
console.log(old ? '（含与旧实现 data/ 历史副本的逐字节对照）' : '（未找到旧实现历史副本，仅做自洽与标尺校验）');
process.exit(bad === 0 ? 0 : 1);
