/* app_ask.js —— ⚠ 薄转发（D15 前端架构决策）。
 *
 * 实现的**唯一真源**已迁到 `frontend/src/core/ask.js`（Vue 问答组件与 node 门禁共用同一份）。
 * 本文件只为兼容既有引用（web/serve.py 的静态路由清单、web/test_api.py 的文本扫描）
 * 与 build_views.py 的拷贝逻辑而保留原路径与原导出名。
 *
 * 若你想改问答结果块的渲染，请改 `frontend/src/core/ask.js`。
 */
'use strict';
module.exports = require('../frontend/src/core/ask.js');
