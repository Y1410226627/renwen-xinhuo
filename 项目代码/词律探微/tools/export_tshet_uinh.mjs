/* export_tshet_uinh.mjs —— 把《广韵》字头候选（vendor/tshet-uinh，MIT · Project NK2028）
 * 全量导出为 `data/rhyme/tshet_uinh.json`，供后端读音候选合并展示。
 *
 * 覆盖范围：**本项目语料里出现过的 7,711 个汉字**（data/rhyme/_chars.json）——
 * 不做全库导出（广韵字头远多于此，我们没有的字查了也用不上）。
 *
 * 每条候选：{ desc(音韻地位描述), mu(声母), yun(韵目), sheng(声调: 平/上/去/入),
 *             pz(平/仄——上去入计仄), fanqie(反切), zhiyin(直音), gloss(释义,截 160 字),
 *             source('廣韻') }
 *
 * ⚠ 口径红线（与竞品同款、且更明确）：广韵候选是**历史音韵参考**，只展示、不参与
 *   本系统的平仄计算——本系统平仄按**普通话四声**（题库口径），人工裁定也只收普通话读音。
 * 运行：node tools/export_tshet_uinh.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const T = require(join(HERE, '..', 'vendor', 'tshet-uinh-beta8.cjs'));

const chars = JSON.parse(readFileSync(join(HERE, '..', 'data', 'rhyme', '_chars.json'), 'utf-8'));
const out = {};
let nChar = 0, nEntry = 0;

for (const ch of chars) {
  let hits = [];
  try { hits = T.資料.query字頭(ch) || []; } catch { continue; }
  if (!hits.length) continue;
  const list = [];
  for (const h of hits) {
    const pos = h['音韻地位'] || {};
    const sheng = pos['聲'] || '';
    const fanqie = h['反切'] || null;
    const zhiyin = h['直音'] || null;
    let gloss = h['釋義'] || null;
    if (gloss && gloss.length > 160) gloss = gloss.slice(0, 160) + '…';
    list.push({
      desc: [pos['母'], pos['呼'], pos['等'] ? pos['等'] + '等' : null, pos['韻'], sheng + '聲']
        .filter(Boolean).join(''),
      mu: pos['母'] || null,
      yun: h['韻目'] || pos['韻'] || null,
      sheng: sheng || null,
      pz: sheng === '平' ? '平' : (['上', '去', '入'].includes(sheng) ? '仄' : null),
      fanqie, zhiyin, gloss,
      source: h['來源'] || '廣韻',
    });
    nEntry++;
  }
  if (list.length) { out[ch] = list; nChar++; }
}

mkdirSync(join(HERE, '..', 'data', 'rhyme'), { recursive: true });
writeFileSync(join(HERE, '..', 'data', 'rhyme', 'tshet_uinh.json'),
  JSON.stringify(out, null, 0), 'utf-8');
console.log(`导出完成：字 ${nChar} / 条目 ${nEntry} → data/rhyme/tshet_uinh.json`);
