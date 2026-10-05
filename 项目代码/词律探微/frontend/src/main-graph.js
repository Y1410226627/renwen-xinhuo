/* main-graph.js —— 知识图谱页入口（数据 fetch graph.json）。 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import GraphView from './views/GraphView.vue';

UI.inject();
createApp(GraphView).mount('#app');
