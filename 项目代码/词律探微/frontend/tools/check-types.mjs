/* frontend/tools/check-types.mjs —— 类型检查入口（包装 tsc / vue-tsc）。
 *
 * 为什么要包装：`tsc` 与 `vue-tsc` 装在 `frontend/node_modules/.bin/`，
 *   而门禁可能在「没装 node_modules」的机器上跑（如答辩机）。这里：
 *     ① 优先用本机 `vue-tsc`（能检查 .vue 的 <script setup>）；
 *     ② 没有则退回 `tsc`（只查 .ts/.d.ts/.mjs）；
 *     ③ 都没有则**跳过并打印 SKIP**（不判失败，避免因缺依赖卡住整条链）。
 *
 * strict 模式（缺依赖时必须判失败，供 CI / 交付验收用）：
 *   二选一即可——命令行 `--strict`，或环境变量 `LVC_STRICT_TYPES=1`。
 *
 * 用法：
 *   node frontend/tools/check-types.mjs                    # 有就查，没有就 SKIP
 *   node frontend/tools/check-types.mjs --strict           # 缺依赖时判失败（CI 用）
 *   LVC_STRICT_TYPES=1 node frontend/tools/check-types.mjs  # 同上（环境变量开关）
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(HERE, '..');
// strict：命令行 --strict 或环境变量 LVC_STRICT_TYPES=1 均生效（后者便于 CI/脚本统一开关）
const STRICT = process.argv.includes('--strict') || process.env.LVC_STRICT_TYPES === '1';

function bin(name) {
  const p = path.join(FRONTEND, 'node_modules', '.bin', name + (process.platform === 'win32' ? '.cmd' : ''));
  return fs.existsSync(p) ? p : null;
}

const vueTsc = bin('vue-tsc');
const tsc = bin('tsc');

let cmd = null, label = '';
if (vueTsc) { cmd = vueTsc; label = 'vue-tsc（含 .vue 组件）'; }
else if (tsc) { cmd = tsc; label = 'tsc（仅 .ts/.d.ts/.mjs）'; }

if (!cmd) {
  const msg = '未安装 typescript/vue-tsc（可 `npm install` 后重跑；不影响其它门禁）';
  if (STRICT) { console.error('✗ ' + msg); process.exit(1); }
  console.log('SKIP 类型检查：' + msg);
  process.exit(0);
}

console.log('▶ 类型检查：' + label);
const r = spawnSync(cmd, ['-p', 'tsconfig.app.json', '--noEmit'],
                    { cwd: FRONTEND, stdio: 'inherit', shell: process.platform === 'win32' });
if (r.status !== 0) {
  console.error('✗ 类型检查未通过（退出码 ' + r.status + '）');
  process.exit(r.status || 1);
}
console.log('✓ 类型检查通过：0 错误');
