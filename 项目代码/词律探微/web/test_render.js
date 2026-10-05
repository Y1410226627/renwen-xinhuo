/* test_render.js —— **前端渲染门禁**：把「逐字解析」的渲染函数真的跑一遍，
 * 逐篇检查「评委在浏览器里看到的数字与表格」是否正确。
 *
 * 真实事故（2026-09-30）：视图一最后那一列「平/仄」曾写成
 *     '<td>'+L.pz.split('仄').length-1 +'/'+ L.pz.split('平').length-1
 * JS 里 `+`/`-` 同优先级、从左到右 → 先拼成字符串、再减 1 → **NaN**，
 * 于是**每一行的「平/仄」都显示 NaN**，而只比「引擎数字」的门禁一个都发现不了：
 * 它压根没跑到「页面自己拼出来的 HTML」。
 *   ⇒ 教训：门禁要覆盖**渲染结果**，不能只覆盖**数据**（引擎／数据库／渲染／交互四层各有各的错法）。
 *
 * 检查项（逐篇，用 ParseApp.detailHtml 这个纯函数）：
 *   1. 渲染结果不得出现 NaN / undefined / Infinity；
 *   2. 表格行数 = 句数 + 1（含表头）；
 *   3. 每句「逐字平仄串」= 页面自己的 pzOf() 重算值；
 *   4. 每句「平/仄」计数 = Metrics.count() 重算值（且顺序是 平/仄）；
 *   5. 篇级摘要 = Metrics.compute() 独立复算值；
 *   6. 句脚与声律模式的条件命中标记（✳ / 〜）条数与独立复算一致。
 *
 * 用法：
 *   node web/test_render.js                  # 全库逐篇
 *   node web/test_render.js --n 2000         # 抽样
 *   node web/test_render.js --selftest       # 自我验证：把旧的 NaN 写法注回去，必须报错
 * 退出码：0 = 全过（比对项为 0 也判 FAIL）；1 = 有问题。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const V = require('./vmload.js');
const Metrics = require('./metrics.js');

const argv = process.argv.slice(2);
function argOf(name, dflt) {
  const i = argv.indexOf(name);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : dflt;
}
const LIMIT = parseInt(argOf('--n', '0'), 10);       // 0 = 全部
const SELFTEST = argv.indexOf('--selftest') >= 0;

/* 现在的（正确）写法 与 老的（错误）写法——自我验证用 */
const FIXED = "M.count(L1.pz, '平') + '/' + M.count(L1.pz, '仄')";
const BUGGY = "L1.pz.split('仄').length-1 + '/' + L1.pz.split('平').length-1";

function bootWith(source) {
  const ctx = V.makeCtx();
  V.load(ctx, path.join(V.web, 'metrics.js'));
  V.load(ctx, path.join(V.web, 'ui.js'));
  if (source) {
    require('vm').runInContext(source, ctx.sandbox, { filename: 'app_parse(injected).js' });
  } else {
    V.load(ctx, path.join(V.web, 'app_parse.js'));
  }
  const pack = JSON.parse(fs.readFileSync(path.join(V.data, 'web_poems.json'), 'utf8'));
  ctx.sandbox.ParseApp.setData(pack);
  return ctx.sandbox;
}

function check(sb, limit) {
  const P = sb.ParseApp, ROWS = sb.ROWS || P.ROWS;
  const rows = JSON.parse(fs.readFileSync(path.join(V.data, 'web_poems.json'), 'utf8')).rows;
  const step = limit > 0 ? Math.max(1, Math.floor(rows.length / limit)) : 1;
  let n = 0, cmp = 0, bad = 0;
  const errs = [];
  for (let i = 0; i < rows.length; i += step) {
    const row = rows[i];
    const inf = P.info(row, i);
    const html = P.detailHtml(row, inf, {});
    n++;
    const problems = [];
    if (/NaN|undefined|Infinity/.test(html)) { problems.push('渲染结果出现 NaN/undefined/Infinity'); }
    const sents = P.splitSents(row[5]);
    cmp++;
    if ((html.match(/<tr/g) || []).length !== sents.length + 1) {
      problems.push('表格行数 ≠ 句数+表头');
    }
    const body = html.split('<tr').slice(2);
    sents.forEach(function (s, j) {
      const pz = P.pzOf(s);
      const want = Metrics.count(pz, '平') + '/' + Metrics.count(pz, '仄');
      const r = body[j] || '';
      cmp += 2;
      if (r.indexOf('<td>' + pz + '</td>') < 0) { problems.push('第 ' + (j + 1) + ' 句逐字平仄串不符'); }
      if (r.indexOf('<td>' + want + '</td>') < 0) { problems.push('第 ' + (j + 1) + ' 句「平/仄」应为 ' + want); }
    });
    const lines = sents.map(function (s) { return { text: s, pz: P.pzOf(s) }; });
    const mm = Metrics.compute(lines);
    const wantP = '全篇 ' + mm.sent_n + ' 句 / ' + mm.han_len + ' 字：平 ' + mm.ping + '、仄 ' + mm.ze
      + '，仄声比例 ' + mm.ze_ratio + '%';
    cmp++;
    if (html.indexOf(wantP) < 0) { problems.push('篇级摘要与独立复算不一致'); }

    /* 条件命中标记：句脚字与声律模式 */
    const tail = inf.tails.filter(Boolean)[0];
    if (tail) {
      const h2 = P.detailHtml(row, inf, { tail: tail });
      const want2 = inf.tails.filter(function (t) { return t === tail; }).length;
      const got2 = (h2.match(/<tr class="hit">/g) || []).length;
      cmp++;
      if (got2 !== want2) { problems.push('句脚高亮行 ' + got2 + ' ≠ 应有 ' + want2 + '（句脚 ' + tail + '）'); }
    }
    const pzs = inf.lines.map(function (L) { return L.pz; }).filter(function (x) { return x.length >= 3; });
    if (pzs.length) {
      const pat = pzs[0].slice(0, 3);
      const re = P.pzTest(pat);
      const h3 = P.detailHtml(row, inf, { pz: pat });
      const want3 = inf.lines.filter(function (L) { return re.test(L.pz); }).length;
      const got3 = (h3.match(/〜/g) || []).length;
      cmp++;
      if (got3 !== want3) { problems.push('声律模式命中标记 ' + got3 + ' ≠ 应有 ' + want3 + '（模式 ' + pat + '）'); }
    }
    if (problems.length) {
      bad++;
      if (errs.length < 8) { errs.push(row[0] + '：' + problems.slice(0, 2).join('；')); }
    }
  }
  return { n: n, cmp: cmp, bad: bad, errs: errs };
}

function main() {
  const packFile = path.join(V.data, 'web_poems.json');
  if (!fs.existsSync(packFile)) {
    console.log('✗ FAIL：找不到 ' + packFile + '（先跑 python web/build_views.py）');
    process.exit(1);
  }
  if (SELFTEST) {
    const src0 = fs.readFileSync(path.join(V.web, 'app_parse.js'), 'utf8');
    if (src0.indexOf(FIXED) < 0) {
      console.log('✗ FAIL（自我验证）：源码里找不到现在的写法，无法注入旧 bug —— 注入失败也算 FAIL，');
      console.log('   否则「这道门禁能报错」本身没被验证过。');
      process.exit(1);
    }
    const sb = bootWith(src0.split(FIXED).join(BUGGY));
    const r = check(sb, 40);
    console.log('自我验证：把旧的 NaN 写法注回去 → 检查 ' + r.n + ' 篇，报错 ' + r.bad + ' 篇');
    if (r.bad > 0) {
      console.log('✓ 自我验证通过：这道门禁确实能抓到「平/仄 = NaN」这类渲染错误');
      process.exit(0);
    }
    console.log('✗ FAIL（自我验证）：注入旧 bug 后竟然没报错 —— 门禁是无效的');
    process.exit(1);
  }
  const r = check(bootWith(null), LIMIT);
  console.log('逐篇渲染检查：' + r.n + ' 篇 / 比对项 ' + r.cmp + ' 项，不符 ' + r.bad + ' 篇');
  for (const e of r.errs) { console.log('  ✗ ' + e); }
  if (r.cmp === 0 || r.n === 0) {
    console.log('✗ FAIL：比对项数为 0（防「空跑报通过」）');
    process.exit(1);
  }

  /* 深链自检：?pid= 必须能定位到那一篇 */
  let dlOk = false;
  try {
    const rows = JSON.parse(fs.readFileSync(packFile, 'utf8')).rows;
    const page = fs.readFileSync(path.join(V.data, 'parse.html'), 'utf8');
    dlOk = page.indexOf('?pid=') >= 0 || page.indexOf('q0.pid') >= 0;
    console.log('深链自检：页面支持 ?pid= 直接定位 → ' + (dlOk ? '是' : '否（FAIL）'));
  } catch (e) { console.log('深链自检异常：' + e.message); }
  console.log((r.bad === 0 && dlOk)
    ? '✓ 浏览器侧渲染逐篇正确（无 NaN、无空表、计数与独立复算一致、条件标记正确）'
    : '✗ 存在渲染错误或深链失效');
  process.exit((r.bad === 0 && dlOk) ? 0 : 1);
}

main();
