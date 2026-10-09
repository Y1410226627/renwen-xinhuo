/* main-cipu.js —— **词谱对照页**入口（竞品「词谱比较」的对应实现，2026-10-10）。
 *
 * 做三件事：① 选一篇作品（按词牌/词人/题名检索，或直接给篇号）；
 * ② 列出该词牌在**谱库**里的全部体式（正体/变体，含句数、字数、来源核验）；
 * ③ 逐句「三行对照」：作品原字 / 谱书规范（平仄，含「中」） / 谱书例词，
 *    逐字给出 对（match）/ 异（mismatch）/ 中（any）三分账与统计条。
 * 数据来源与核验状态由后端 `cipu.py` 一并给出（**照抄、不加工**）——来源声明常驻页脚。
 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import CipuView from './views/CipuView.vue';

UI.inject();
createApp(CipuView).mount('#app');
