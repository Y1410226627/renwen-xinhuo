/* frontend/tools/gen-docs.mjs —— 从 Vue 组件源码抽取 props/emits/slots，生成组件 API 文档。
 *
 * 为什么要它：老师指出的「接手难」不只指 HTML，也指「不知道组件怎么用」。
 *   手写文档必然与代码漂移；这里**从源码抽取**，并配 `--check` 校验（CI/门禁用）。
 *
 * 实现：正则抽取（不引额外依赖，保持仓库轻量）：
 *   · defineProps({...}) / defineProps<...>()  → props 表
 *   · defineEmits([...]) / defineEmits({...})  → emits 表
 *   · <slot name="x"> / <slot>                 → slots 表
 *
 * 用法：
 *   node frontend/tools/gen-docs.mjs           # 生成 docs/组件API.md
 *   node frontend/tools/gen-docs.mjs --check   # 只校验，不写（文档落后于源码则退出码 1）
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(HERE, '..');
const SRC = path.join(FRONTEND, 'src');
const OUT = path.join(FRONTEND, 'docs', '组件API.md');
const CHECK = process.argv.includes('--check');

/* 收集所有组件（views 与 components）。 */
function collectVue(dir) {
  const out = [];
  const walk = (d) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { walk(p); } else if (e.name.endsWith('.vue')) { out.push(p); }
    }
  };
  walk(dir);
  return out.sort();
}

/* 抽取 defineProps 的对象字面量条目：`name: { type: X, default: Y }` 或简写 `name: X`。 */
function parseProps(src) {
  const out = [];
  const m = src.match(/defineProps\s*\(\s*\{([\s\S]*?)\}\s*\)/);
  if (!m) { return out; }
  const body = m[1];
  /* 逐行匹配 `ident: { type: ..., default: ... }` / `ident: Type` */
  const re = /^\s*([A-Za-z_$][\w$]*)\s*:\s*(\{[^}]*\}|[^,{}\n]+)/gm;
  let mm;
  while ((mm = re.exec(body))) {
    const name = mm[1];
    const rest = mm[2].trim();
    let type = '—', def = '—', desc = '—';
    if (rest.startsWith('{')) {
      const t = rest.match(/type\s*:\s*([A-Za-z_$][\w$.]*)/);
      if (t) { type = t[1].replace(/^(String|Number|Boolean|Array|Object|Function)$/, '$1'); }
      const d = rest.match(/default\s*:\s*([^,}]+)/);
      if (d) { def = d[1].trim(); }
    } else {
      type = rest;
    }
    /* 行内注释作为说明 */
    const line = body.slice(mm.index, body.indexOf('\n', mm.index) === -1 ? undefined : body.indexOf('\n', mm.index));
    const c = line.match(/\/\/\s*(.+)$/);
    if (c) { desc = c[1].trim(); }
    out.push({ name, type, def, desc });
  }
  return out;
}

function parseEmits(src) {
  const out = [];
  const arr = src.match(/defineEmits\s*\(\s*\[([\s\S]*?)\]\s*\)/);
  if (arr) {
    for (const s of arr[1].split(',')) {
      const n = s.trim().replace(/['"]/g, '');
      if (n) { out.push(n); }
    }
  }
  return out;
}

function parseSlots(src) {
  const out = new Set();
  const re = /<slot\s*(?::name="([^"]+)"|name="([^"]+)")?\s*\/?>/g;
  let m;
  while ((m = re.exec(src))) {
    const n = m[1] || m[2] || 'default';
    out.add(n);
  }
  return [...out];
}

/* 抽取组件头部注释里的第一句作为「用途」。
 * 兼容两种风格：`/* X.vue —— 说明`（块注释）与文件内任意 `X.vue —— 说明`。 */
function purposeOf(src, name) {
  const esc = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = src.match(new RegExp('/\\*[\\s\\S]*?' + esc + '\\.vue\\s*——\\s*([^\\n*]+)'));
  if (m) { return m[1].trim().replace(/[。.]$/, ''); }
  const m2 = src.match(new RegExp(esc + '\\.vue\\s*——\\s*([^\\n*<]+)'));
  if (m2) { return m2[1].trim().replace(/[。.]$/, ''); }
  const m3 = src.match(/<!--\s*([^\n]+?)\s*-->/);
  return m3 ? m3[1].trim() : '—';
}

function build() {
  const files = collectVue(SRC);
  const lines = [];
  lines.push('# 组件 API 文档（自动生成）', '');
  lines.push('> 本文件由 `frontend/tools/gen-docs.mjs` **从组件源码自动抽取**，请勿手改。');
  lines.push('> 改动组件后运行 `npm run docs`（或 `npm run docs:check` 校验）重新生成。', '');
  lines.push(`共 ${files.length} 个组件。`, '');
  lines.push('---', '');

  for (const f of files) {
    const src = fs.readFileSync(f, 'utf8');
    const rel = path.relative(FRONTEND, f).replace(/\\/g, '/');
    const name = path.basename(f, '.vue');
    lines.push(`## ${name}`, '');
    lines.push(`**文件**：\`${rel}\`　·　**用途**：${purposeOf(src, name)}`, '');

    const props = parseProps(src);
    if (props.length) {
      lines.push('### props', '');
      lines.push('| 名称 | 类型 | 默认值 | 说明 |');
      lines.push('| --- | --- | --- | --- |');
      for (const p of props) {
        lines.push(`| \`${p.name}\` | \`${p.type}\` | \`${p.def}\` | ${p.desc} |`);
      }
      lines.push('');
    } else {
      lines.push('### props', '', '（无）', '');
    }

    const emits = parseEmits(src);
    lines.push('### emits', '');
    lines.push(emits.length ? emits.map((e) => `\`${e}\``).join('、') : '（无）');
    lines.push('');

    const slots = parseSlots(src);
    lines.push('### slots', '');
    lines.push(slots.length ? slots.map((s) => `\`${s}\``).join('、') : '（无）');
    lines.push('');
    lines.push('---', '');
  }
  return lines.join('\n') + '\n';
}

const content = build();
if (CHECK) {
  const cur = fs.existsSync(OUT) ? fs.readFileSync(OUT, 'utf8') : '';
  if (cur !== content) {
    console.error('✗ 组件文档已过期：请运行 node frontend/tools/gen-docs.mjs 重新生成');
    process.exit(1);
  }
  console.log('✓ 组件文档与源码一致（' + OUT + '）');
} else {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, content, 'utf8');
  console.log('✓ 已生成 ' + OUT + '（' + content.split('\n').length + ' 行）');
}
