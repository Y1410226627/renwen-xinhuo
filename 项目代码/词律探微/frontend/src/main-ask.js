/* main-ask.js —— 问答页入口。 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import { installErrorHandler } from './error-boundary.js';
import AskView from './views/AskView.vue';

UI.inject();                       // 样式只有一份（core/ui.js），与离线视图同一套
installErrorHandler(createApp(AskView)).mount('#app');
