/* main-index.js —— 总览页入口。 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import IndexView from './views/IndexView.vue';

UI.inject();
createApp(IndexView).mount('#app');
