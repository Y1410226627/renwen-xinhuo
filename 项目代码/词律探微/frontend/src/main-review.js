/* main-review.js —— 校订队列页入口（数据由 rev.js 注入 window.__REV__）。 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import { installErrorHandler } from './error-boundary.js';
import ReviewView from './views/ReviewView.vue';

UI.inject();
installErrorHandler(createApp(ReviewView)).mount('#app');
