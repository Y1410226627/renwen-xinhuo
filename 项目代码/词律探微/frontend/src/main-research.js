/* main-research.js —— 研究库页入口（功能 1/6/7/8/9/11/12/13/15/18 的统一操作台）。
 *
 * 本页**在线专用**：文献摘录、研究事实、读音裁定、个人录入、批量导入、冻结快照
 * 全部走本地服务的 /api/*（写操作是 POST）。离线双击打开时会如实说明「需要本地服务」。
 */
import { createApp } from 'vue';
import { UI } from './core/index.mjs';
import ResearchView from './views/ResearchView.vue';

UI.inject();
createApp(ResearchView).mount('#app');
