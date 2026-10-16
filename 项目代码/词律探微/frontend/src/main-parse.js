/* main-parse.js —— 离线逐字解析页入口（数据由 pack.js 注入 window.__PACK__）。 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import { installErrorHandler } from './error-boundary.js';
import ParseView from './views/ParseView.vue';

UI.inject();
installErrorHandler(createApp(ParseView, { mode: 'offline' })).mount('#app');
