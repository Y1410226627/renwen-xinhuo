/* src/stores/theme.js —— 主题（夜间/日间）唯一状态源。
 * 与 core/ui.js 的 localStorage 约定完全一致（key='theme'，值 'dark'/'light'，
 * 挂在 <html data-theme>），这样新旧页面切换主题的「记忆」是同一份。
 */
import { reactive, watchEffect } from 'vue';

const KEY = 'theme';

function initial() {
  try {
    const s = localStorage.getItem(KEY);
    if (s === 'dark' || s === 'light') { return s; }
  } catch (e) { /* 隐私模式 */ }
  try {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches) { return 'dark'; }
  } catch (e) { /* 忽略 */ }
  return 'light';
}

export const theme = reactive({ mode: initial() });

export function toggleTheme() { theme.mode = theme.mode === 'dark' ? 'light' : 'dark'; }

watchEffect(() => {
  const mode = theme.mode;
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', mode);
  }
  try { localStorage.setItem(KEY, mode); } catch (e) { /* 忽略 */ }
});

export function themeLabel() { return theme.mode === 'dark' ? '☾ 夜间' : '☀ 日间'; }
