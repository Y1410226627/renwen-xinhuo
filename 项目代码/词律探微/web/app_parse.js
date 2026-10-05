/* app_parse.js —— ⚠ 薄转发（D15 前端架构决策）。
 *
 * 实现的**唯一真源**已迁到 `frontend/src/core/parse.js`（Vue 组件与 node 门禁共用同一份）。
 * 本文件只为兼容既有门禁（web/test_ui.js、web/test_render.js、web/verify_views.js）
 * 与 build_views.py 的拷贝逻辑而保留原路径与原导出名。
 *
 * 若你想改检索判定表 / 分页语义 / detailHtml 渲染，请改 `frontend/src/core/parse.js`。
 */
'use strict';
module.exports = require('../frontend/src/core/parse.js');
