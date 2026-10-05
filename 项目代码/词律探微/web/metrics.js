/* metrics.js —— ⚠ 薄转发（D15 前端架构决策）。
 *
 * 实现的**唯一真源**已迁到 `frontend/src/core/metrics.js`（Vue 组件与 node 门禁共用同一份）。
 * 本文件只为兼容既有门禁（web/test_render.js、web/test_ui.js、web/verify_views.js、
 * web/build_views.py 的拷贝逻辑）而保留原路径与原导出名。
 *
 * 若你想改声律指标口径，请改 `frontend/src/core/metrics.js`，**不要**在这里改。
 */
'use strict';
module.exports = require('../frontend/src/core/metrics.js');
