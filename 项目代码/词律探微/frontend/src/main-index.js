/* main-index.js —— 总览页入口。 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import { installErrorHandler } from './error-boundary.js';
import IndexView from './views/IndexView.vue';

UI.inject();
installErrorHandler(createApp(IndexView)).mount('#app');
