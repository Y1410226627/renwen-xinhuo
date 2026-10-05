/* app_review.js —— ⚠ 薄转发（D15 前端架构决策）。
 *
 * 实现的**唯一真源**已迁到 `frontend/src/core/review.js`（Vue 组件与 node 门禁共用同一份）。
 * 本文件只为兼容既有门禁（web/test_ui.js）与 build_views.py 的拷贝逻辑而保留原路径与原导出名。
 *
 * 若你想改校订队列的筛选 / 排序口径，请改 `frontend/src/core/review.js`。
 */
'use strict';
module.exports = require('../frontend/src/core/review.js');
