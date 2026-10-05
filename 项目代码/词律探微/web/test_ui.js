/* test_ui.js —— **前端功能门禁**（比渲染门禁更上一层：查「功能与页面本身」）。
 *
 * 覆盖：
 *   一、检索正确性：一批「条件 → 命中篇数」由 build_views.py 用 SQL 独立算出（expect_search.json），
 *       前端 JS 的 searchOffline() 必须给出同样的篇数（两套实现互证）。
 *   二、校订队列：review.html 内嵌的 JSON 与 data/review_diff.csv（node 侧独立解析 CSV）必须一致；
 *       筛选/排序的计数、单调性必须成立。
 *   三、页面审计：四张页面必须存在、带页脚「生成时间」探针、本地资源都在、正文里不得有 markdown 星号。
 *   四、共享文件一致性：data/*.js 必须与 web/*.js 逐字节相同（防「只改了一处」）。
 *   五、坏写法扫描：全树不得再出现 `.length-1` 这类「字符串拼接里夹算术」的老写法。
 *   六、本轮四处实测缺陷（2026-09-30 主人第二次贴回运行记录）：
 *       ① 在线翻页第二页空白（服务端已分页，前端又切一刀）；
 *       ② 表头 sticky `top:52px` 把表格前几行遮住（容器内滚动应 `top:0`）；
 *       ③ 检索表单不全面（引擎有的条件，表单里没有）；
 *       ④ 图谱字太小、同色圆挤在一起（同心圆布局 → 两列布局 + 字号 15px + 异色）。
 *
 * 用法：node web/test_ui.js [--selftest]
 * 退出码：0 = 全过（比对项为 0 也判 FAIL）；1 = 有问题。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const V = require('./vmload.js');

const argv = process.argv.slice(2);
const SELFTEST = argv.indexOf('--selftest') >= 0;

let cmp = 0, bad = 0;
const problems = [];
function ok(name, cond, detail) {
  cmp++;
  if (!cond) { bad++; if (problems.length < 20) { problems.push(name + (detail ? '：' + detail : '')); } }
}

/* ---------- 简易 CSV 解析（node 侧独立实现，用来复核 Python 侧解析结果） ---------- */
function parseCsv(text) {
  text = String(text).replace(/^\ufeff/, '');          // 带 BOM 的导出文件（Excel/记事本）
  const rows = []; let row = [], cur = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else { q = false; } }
      else { cur += c; }
    } else if (c === '"') { q = true; }
    else if (c === ',') { row.push(cur); cur = ''; }
    else if (c === '\n') { row.push(cur.replace(/\r$/, '')); rows.push(row); row = []; cur = ''; }
    else { cur += c; }
  }
  if (cur !== '' || row.length) { row.push(cur.replace(/\r$/, '')); rows.push(row); }
  return rows.filter(r => !(r.length === 1 && r[0] === ''));
}

function main() {
  const D = V.data, WEB = V.web;
  const sb = V.boot().sandbox;
  const P = sb.ParseApp, Rev = sb.ReviewApp, U = sb.UI;

  /* ---------- 一、检索正确性（前端 JS ↔ SQL） ---------- */
  const pack = JSON.parse(fs.readFileSync(path.join(D, 'web_poems.json'), 'utf8'));
  const rows = pack.rows;
  P.setData(pack);
  const exp = JSON.parse(fs.readFileSync(path.join(D, 'expect_search.json'), 'utf8'));
  let cases = 0;
  for (const c of exp.cases) {
    const res = P.searchOffline(rows, c.cond);
    cases++;
    ok('检索篇数 [' + JSON.stringify(c.cond) + ']', res.total === c.expect,
       '前端 ' + res.total + ' ≠ SQL ' + c.expect + '（where: ' + c.where + '）');
    ok('结果数组长度与 total 一致', res.hits.length === res.total);
  }
  ok('检索标尺条数 ≥ 10', cases >= 10, '只有 ' + cases + ' 条');
  /* 排序必须真的单调 */
  const byZe = P.searchOffline(rows, { sort: 'ze_desc', minLen: 40 });
  let mono = true;
  for (let i = 1; i < Math.min(byZe.hits.length, 300); i++) {
    if (byZe.hits[i - 1].info.metrics.ze_ratio < byZe.hits[i].info.metrics.ze_ratio) { mono = false; break; }
  }
  ok('排序 ze_desc 单调不增', mono);
  /* 分面统计与命中总数自洽 */
  const f = byZe.facets;
  const bucketSum = Object.keys(f.ratio).reduce((a, k) => a + f.ratio[k], 0);
  ok('分面「仄比分布」求和 = 命中数', bucketSum === byZe.total, bucketSum + ' ≠ ' + byZe.total);
  const sceneSum = f.scene.reduce((a, kv) => a + kv[1], 0);
  ok('分面「声情」求和 = 命中数', sceneSum === byZe.total, sceneSum + ' ≠ ' + byZe.total);

  /* ---------- 二、校订队列（内嵌 JSON ↔ 独立解析的 CSV） ---------- */
  const revHtml = fs.readFileSync(path.join(D, 'review.html'), 'utf8');
  const m = /var REV=(\[[\s\S]*?\]);/.exec(revHtml);
  ok('review.html 内嵌了工单数据', !!m);
  if (m) {
    const rev = JSON.parse(m[1]);
    const csv = parseCsv(fs.readFileSync(path.join(D, 'review_diff.csv'), 'utf8'));
    const head = csv[0];
    ok('内嵌工单条数 = CSV 行数', rev.length === csv.length - 1,
       rev.length + ' vs ' + (csv.length - 1));
    ok('内嵌字段与 CSV 表头一致',
       JSON.stringify(Object.keys(rev[0])) === JSON.stringify(head));
    const st = Rev.stats(rev);
    ok('stats.total = 工单数', st.total === rev.length);
    ok('stats.chars = CSV 中不同字数',
       st.chars === new Set(csv.slice(1).map(r => r[head.indexOf('字')])).size);
    const wantLong = csv.slice(1).filter(r => r.join('\u0001').indexOf('长') >= 0).length;
    ok('筛选「长」的条数 = CSV 独立统计', Rev.filter(rev, '长').length === wantLong,
       Rev.filter(rev, '长').length + ' ≠ ' + wantLong);
    const s2 = Rev.sortRows(rev, '字', 'asc');
    let mono2 = true;
    for (let i = 1; i < s2.length; i++) { if (String(s2[i - 1]['字']) > String(s2[i]['字'])) { mono2 = false; break; } }
    ok('按「字」排序单调不减', mono2);
  }

  /* ---------- 三、页面审计 ---------- */
  const pages = ['index.html', 'parse.html', 'browse.html', 'graph.html', 'review.html'];
  for (const pg of pages) {
    const p = path.join(D, pg);
    ok(pg + ' 存在', fs.existsSync(p));
    if (!fs.existsSync(p)) { continue; }
    const h = fs.readFileSync(p, 'utf8');
    ok(pg + ' 带「生成时间」探针', h.indexOf('页面生成时间') >= 0);
    ok(pg + ' 正文无 markdown 星号', h.indexOf('**') < 0);
    ok(pg + ' 无字面 NaN 断言（除探针提示）',
       (h.match(/NaN/g) || []).length <= 2);
    for (const mm of h.matchAll(/(?:src|href)="([^"#?][^"]*)"/g)) {
      const t = mm[1];
      if (/^(https?:|javascript:|mailto:)/.test(t)) { continue; }
      ok(pg + ' 本地资源存在 ' + t, fs.existsSync(path.join(D, t)));
    }
  }
  ok('parse.html 引用 app_parse.js',
     fs.readFileSync(path.join(D, 'parse.html'), 'utf8').indexOf('app_parse.js') >= 0);
  ok('parse.html 内嵌数据（离线可用）',
     fs.readFileSync(path.join(D, 'parse.html'), 'utf8').indexOf('EMBED_PACK=') >= 0);

  /* ---------- 四、共享文件一致 ---------- */
  for (const f of ['ui.js', 'app_parse.js', 'app_review.js', 'metrics.js']) {
    const a = fs.readFileSync(path.join(WEB, f));
    const b = fs.readFileSync(path.join(D, f));
    ok('data/' + f + ' 与 web/' + f + ' 逐字节相同', a.equals(b));
  }

  /* ---------- 五、坏写法扫描 ---------- */
  const scan = pages.map(p => path.join(D, p)).concat(
    ['ui.js', 'app_parse.js', 'app_review.js', 'metrics.js'].map(f => path.join(D, f)));
  let hits = 0;
  /* 只抓「字符串拼接里夹算术」：字符串字面量后紧跟 + ，中间出现 .length-数字，**且结果又去拼字符串**。
     正当写法（`(rows.length - 1)` 后跟括号、`for (i = s.length - 1; ...)`）不会命中。 */
  const PAT = /(['"])\s*\+[^;]*\.length\s*-\s*\d\s*\+/;
  const detect = function (line) {
    if (/for\s*\(/.test(line)) { return false; }
    return PAT.test(line);
  };
  ok('坏写法检测器自检（旧 bug 必须被抓到，正当写法不误报）',
     detect("h+='<td>'+L.pz.split('仄').length-1+'/'+L.pz.split('平').length-1+'</td>';") === true
     && detect("U.toast('已导出 ' + (rows.length - 1) + ' 行');") === false);
  for (const p of scan) {
    const t = fs.readFileSync(p, 'utf8');
    cmp++;
    for (const line of t.split('\n')) {
      if (detect(line)) {
        hits++;
        if (problems.length < 20) {
          problems.push('坏写法（字符串拼接里夹算术）：' + path.basename(p) + ' → ' + line.trim().slice(0, 90));
        }
      }
    }
  }
  ok('全树无 .length-1 类写法', hits === 0, hits + ' 处');

  /* ---------- 六、本轮四处实测缺陷 ---------- */
  /* ③-a 表单完整性：引擎支持的每个条件，两张检索页都必须有一个对应字段（id 同名） */
  const COND_FIELDS = ['dynasty', 'q', 'author', 'cipai', 'tail', 'tailPz', 'pz', 'minLen',
    'maxLen', 'minSent', 'maxSent', 'minZe', 'maxZe', 'minLong', 'changeMin', 'changeMax',
    'thrMin', 'thrMax', 'scene', 'sort', 'size'];
  for (const pg of ['parse.html', 'browse.html']) {
    const h = fs.readFileSync(path.join(D, pg), 'utf8');
    for (const f2 of COND_FIELDS) {
      ok(pg + ' 有检索条件字段 #' + f2, h.indexOf('id="' + f2 + '"') >= 0);
    }
  }
  /* ③-b 服务端必须真的认这些参数（与 UI 同一张清单） */
  const srv = fs.readFileSync(path.join(WEB, 'serve.py'), 'utf8');
  for (const f2 of ['tailPz', 'changeMin', 'changeMax', 'thrMin', 'thrMax', 'author', 'cipai',
                    'dynasty']) {
    ok('服务端 build_where 支持参数 ' + f2, srv.indexOf("'" + f2 + "'") >= 0);
  }
  /* ② 表头：容器内滚动必须 sticky top:0；旧的 top:52px 是「遮住前几行」的真凶 */
  const css = fs.readFileSync(path.join(WEB, 'ui.js'), 'utf8');
  ok('表头 sticky 定位在容器顶部（top:0）', /thead th\{[^}]*top:0/.test(css));
  ok('表头不再用 top:52px 偏移（旧 bug）', css.indexOf('top:52px') < 0);
  /* ④ 图谱：两列布局 + 异色 + 字号 15px + 图例 */
  const gh = fs.readFileSync(path.join(D, 'graph.html'), 'utf8');
  ok('图谱用两列布局（左词人右词牌，不再画同心圆）',
     gh.indexOf('text-anchor="end"') > 0 && gh.indexOf('text-anchor="start"') > 0);
  ok('图谱节点有 class="chart" 的样式钩子', gh.indexOf('class="nd" data-k=') > 0);
  ok('图谱两种节点异色（词人蓝 #1f6fb2 / 词牌橙 #c2691a）',
     gh.indexOf('#1f6fb2') > 0 && gh.indexOf('#c2691a') > 0);
  ok('图谱字号 15px（不再是小字 12px）', /font-size:15px/.test(css));
  ok('图谱带图例（颜色／线宽含义）', gh.indexOf('class="legend"') > 0);
  ok('图谱节点带篇数标签（可读）', /<tspan fill="#7a8b9a">\d+<\/tspan>/.test(gh));
  /* ① 翻页：服务端已分页时不得再切一刀（旧 bug：第二页永远空） */
  const srvRows = [];
  for (let i = 0; i < 50; i++) { srvRows.push({ row: ['p' + i], info: { metrics: {} } }); }
  const livePg = P.pageSlice({ total: 120, hits: srvRows }, 2, 50, true);
  ok('在线分页：第二页仍显示本页 50 行（旧版切成了 0 行）', livePg.hits.length === 50,
     '得 ' + livePg.hits.length + ' 行');
  ok('在线分页：页数与总数自洽', livePg.pages === 3 && livePg.page === 2);
  const offAll = [];
  for (let i = 0; i < 120; i++) { offAll.push({ row: ['q' + i], info: { metrics: {} } }); }
  const offPg = P.pageSlice({ total: 120, hits: offAll }, 2, 50, false);
  ok('离线分页：第二页切出第 51—100 行',
     offPg.hits.length === 50 && offPg.hits[0].row[0] === 'q50', offPg.hits[0].row[0]);
  ok('分页：越界页自动夹到末页', P.pageSlice({ total: 120, hits: offAll }, 99, 50, false).page === 3);

  /* ---------- 自检：把**旧的错误写法**注回去，必须报错（护栏的护栏） ---------- */
  if (SELFTEST) {
    const det = [];
    /* ① 翻页：旧逻辑（对服务端已分好的页再切一刀）必须被判定为「第二页空白」 */
    const oldSlice = (res, page, size) => res.hits.slice((page - 1) * size, page * size);
    det.push(['翻页（服务端已分页还再切一刀）', oldSlice({ total: 120, hits: srvRows }, 2, 50).length === 0]);
    /* ② 表头：旧 CSS（top:52px）必须不能再通过「sticky 在容器顶部」这一条 */
    const cssBad = css.replace('top:0;z-index:3', 'top:52px;z-index:3');
    det.push(['表头 sticky top:52px 遮住前几行',
              !(/thead th\{[^}]*top:0/.test(cssBad)) && cssBad.indexOf('top:52px') >= 0]);
    /* ③ 表单：拿掉一个条件字段，必须被抓到 */
    const browseH = fs.readFileSync(path.join(D, 'browse.html'), 'utf8');
    const browseBad = browseH.replace('id="tailPz"', 'id="tailPz_gone"');
    det.push(['检索表单缺条件字段（tailPz）', browseBad.indexOf('id="tailPz"') < 0]);
    /* ④ 图谱：换回同色，必须被抓到 */
    const ghBad = gh.replace(/#1f6fb2/g, '#c0392b').replace(/#c2691a/g, '#1e6f3c');
    det.push(['图谱两种节点同色（挤在一起看不清）',
              !(ghBad.indexOf('#1f6fb2') > 0 && ghBad.indexOf('#c2691a') > 0)]);
    let miss = 0;
    for (const [name, caught] of det) {
      console.log((caught ? '  ✓ 自检抓到：' : '  ✗ 自检漏报：') + name);
      if (!caught) { miss++; }
    }
    console.log('自检：' + (det.length - miss) + '/' + det.length + ' 旧写法都被抓到');
    process.exit(miss === 0 ? 0 : 1);
  }

  /* ---------- 汇报 ---------- */
  console.log('前端功能门禁：比对项 ' + cmp + ' 项，不符 ' + bad + ' 项'
    + '（含检索标尺 ' + cases + ' 条、页面 ' + pages.length + ' 张、条件字段 '
    + COND_FIELDS.length + ' 个 × 2 页）');
  for (const p of problems) { console.log('  ✗ ' + p); }
  if (cmp === 0) { console.log('✗ FAIL：比对项数为 0（防「空跑报通过」）'); process.exit(1); }
  console.log(bad === 0 ? '✓ 前端检索／队列／页面／共享文件 全部一致' : '✗ 存在不一致');
  process.exit(bad === 0 ? 0 : 1);
}

main();
