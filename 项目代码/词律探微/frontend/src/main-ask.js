/* main-ask.js —— 问答页入口。 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import AskView from './views/AskView.vue';

UI.inject();                       // 样式只有一份（core/ui.js），与离线视图同一套
createApp(AskView).mount('#app');
