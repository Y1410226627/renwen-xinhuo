/* ui.js —— ⚠ 薄转发（D15 前端架构决策）。
 *
 * 实现的**唯一真源**已迁到 `frontend/src/core/ui.js`（Vue 组件与 node 门禁共用同一份）。
 * 本文件只为兼容既有门禁与 build_views.py 的拷贝逻辑而保留原路径与原导出名。
 *
 * 若你想改样式 / 转义 / 格式化口径，请改 `frontend/src/core/ui.js`，**不要**在这里改。
 * 注意：门禁里对 CSS 的文本断言（sticky 表头、图谱字号）现已直接读真源文件。
 */
'use strict';
module.exports = require('../frontend/src/core/ui.js');
