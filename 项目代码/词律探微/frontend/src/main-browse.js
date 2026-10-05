/* main-browse.js —— 在线检索页入口（条件交给本地引擎执行）。 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import ParseView from './views/ParseView.vue';

UI.inject();
createApp(ParseView, { mode: 'online' }).mount('#app');
