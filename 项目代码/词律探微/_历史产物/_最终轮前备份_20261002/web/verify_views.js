/* verify_views.js —— 用 node 独立复算「网页那一侧」的数字，与 Python 引擎逐字段对照。
 *
 * 为什么要这么做：网页上的数字若只是 Python 的截图，那它不构成证据；
 * 让**两套独立实现**（Python 引擎 / JavaScript 前端）在同一语料上逐字段比对，
 * 才能说明「这些数字是口径的产物，不是某个程序的自说自话」。
 *
 * 2026-09-30 两处改进：
 *   ① 切句/pzOf 不再在这里重写一遍，而是**直接用页面的 app_parse.js**（同一份实现），
 *      避免「页面改了、对照脚本没改」的假通过（此前正是各写一份）。
 *   ② 新增 `--all`：对照 data/_db_metrics_all.json（全库 26,742 篇）。
 *      抽样会漏掉个别的口径不一致——实测漏了 scene/sent_n 各若干篇（见 README §29）。
 *
 * 用法：node web/verify_views.js [--n 3000] [--all] [--data data/]
 * 退出码：0 = 全一致；1 = 有差异（比对项数为 0 也判 FAIL）。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const V = require('./vmload.js');

const args = process.argv.slice(2);
function argOf(name, dflt) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : dflt;
}
const N = parseInt(argOf('--n', '3000'), 10);
const DIR = argOf('--data', path.join(__dirname, '..', 'data'));
const ALL = args.indexOf('--all') >= 0;

const pack = JSON.parse(fs.readFileSync(path.join(DIR, 'web_poems.json'), 'utf8'));
const dbFile = ALL ? '_db_metrics_all.json' : 'db_metrics.json';
if (!fs.existsSync(path.join(DIR, dbFile))) {
  console.log('✗ FAIL：找不到 ' + dbFile
    + (ALL ? '（先跑 python tools/dump_metrics_all.py）' : '（先跑 python web/build_views.py）'));
  process.exit(1);
}
const db = JSON.parse(fs.readFileSync(path.join(DIR, dbFile), 'utf8'));

/* 页面自己的实现（唯一来源） */
const sb = V.boot().sandbox;
const P = sb.ParseApp;
P.setData(pack);
const idx = new Map();
pack.rows.forEach((r, i) => idx.set(r[0], i));

const FIELDS = ['han_len', 'sent_n', 'ping', 'ze', 'ze_ratio', 'cut', 'f_ratio', 'b_ratio',
  'change', 'abs_change', 'longest_len', 'threshold', 'scene'];

let n = 0, mism = 0;
const bad = [];
const step = ALL ? 1 : Math.max(1, Math.floor(db.length / N));
for (let i = 0; i < db.length; i += step) {
  const d = db[i];
  const j = idx.get(d.pid);
  if (j === undefined) { console.log('  ✗ 前端数据缺篇：' + d.pid); mism++; continue; }
  const got = P.analyze(pack.rows[j][5]).metrics;
  for (const f of FIELDS) {
    n++;
    const a = got[f], b = d[f];
    const same = (typeof b === 'number') ? Math.abs(a - b) < 1e-9 : a === b;
    if (!same) {
      mism++;
      if (bad.length < 10) { bad.push(`${d.pid} ${f}: JS=${JSON.stringify(a)} PY=${JSON.stringify(b)}`); }
    }
  }
}
console.log(`比对 ${n} 项（${Math.ceil(db.length / step)} 首 × ${FIELDS.length} 字段，`
  + (ALL ? '全库' : '抽样') + `），不符 ${mism} 处`);
for (const b of bad) { console.log('  ✗ ' + b); }
if (n === 0) { console.log('✗ FAIL：比对项数为 0（防「空跑报通过」）'); process.exit(1); }
console.log(mism === 0 ? '✓ 两套独立实现逐字段一致' : '✗ 存在差异');
process.exit(mism === 0 ? 0 : 1);
