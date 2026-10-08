<template>
  <AppShell active="index" :stamp="stamp" :data-note="dataNote" :data-n="qingN" :online="isOnline">
  <div class="ov">
    <!-- 首屏：一句话讲清「这是什么 + 去哪儿」——指标做成磁贴，避免一行 chip 里数字被埋没 -->
    <div class="card hero">
      <h1>词律探微 · 清代词律声情研究助手</h1>
      <p class="lead">本项目把「清代词律声情」这一传统词学问题，转译成<b>可复算、可溯源、可复核</b>的工程问题：
        以 58,852 首诗词曲语料为底（清词 26,742 首为主），用一套<b>确定性口径</b>逐字标注平仄与句读，
        所有数字都由引擎现算，任何人可一键复现。</p>
      <p class="dim">一句话分工：<b>数字归引擎、文料归检索、说法归大模型、出处归引用</b>。</p>

      <div class="kpis" role="list">
        <div class="kpi" role="listitem"><b>{{ fmt(corpusN) }}</b><span>语料总篇</span></div>
        <div class="kpi" role="listitem"><b>{{ fmt(qingN) }}</b><span>清词主篇</span></div>
        <div class="kpi" role="listitem"><b>v{{ rulesV }}</b><span>口径版本</span></div>
        <div class="kpi" role="listitem"><b>{{ gateCount }}</b><span>门禁项</span></div>
        <div class="kpi ok" role="listitem"><b>已锁定</b><span>双集答案哈希</span></div>
      </div>

      <!-- 起始引导：把「第一眼之后点哪」写实，别让用户对着六个入口卡发呆 -->
      <p class="start-hint">
        第一次来？建议顺序：
        <template v-if="isOnline"><a href="ask.html">① 声情问答</a></template>
        <template v-else><span class="dim">① 声情问答（需先跑本地服务）</span></template>
        <span class="arrow">→</span><a href="parse.html">② 逐字解析</a>
        <span class="arrow">→</span><a href="browse.html">③ 多条件检索</a>。
        <span class="dim">要一句话结论走 ①，要逐字平仄走 ②，要批量筛篇走 ③。</span>
      </p>
      <p v-if="!qingN" class="dim warn-line">离线数据未注入：请先运行
        <code>python web/build_views.py</code>（或直接打开由构建产出的 <code>data/vue/index.html</code>）。</p>
    </div>

    <div class="grid">
      <div class="card entry">
        <h3><span class="no">①</span> 在线问答</h3>
        <p class="dim">问一句、答一句，每一处数字都带出处。大模型只负责组织「说法」，数字仍由引擎给；
          支持流式输出与多轮追问。</p>
        <p v-if="isOnline" class="cta"><a class="btn" href="ask.html">进入问答</a></p>
        <p v-else class="dim">问答页由本地服务提供（离线目录不含 ask.html）：先运行
          <code>python web/serve.py</code>，再打开首页的「进入问答」。</p>
      </div>
      <div class="card entry">
        <h3><span class="no">②</span> 逐字解析与检索</h3>
        <p class="dim">26,742 首清词，逐字平仄 + 句脚字 + 声律模式；支持多条件相与、分页、CSV 导出。
          离线模式下由页面内 JavaScript 用同一套口径自算。</p>
        <p class="cta"><a class="btn" href="parse.html">进入解析</a></p>
      </div>
      <div class="card entry">
        <h3><span class="no">③</span> 在线检索</h3>
        <p class="dim">同一套条件改由本地 SQLite 引擎执行（含句级条件与分面统计），
          还可让大模型把一句人话听成检索条件。</p>
        <p class="cta"><a class="btn" href="browse.html">进入检索</a></p>
      </div>
      <div class="card entry">
        <h3><span class="no">④</span> 知识图谱</h3>
        <p class="dim">词人 ↔ 词牌二部图（取作数前 45），可筛选、悬停高亮、可直接截图进 PPT。</p>
        <p class="cta"><a class="btn" href="graph.html">进入图谱</a></p>
      </div>
      <div class="card entry">
        <h3><span class="no">⑤</span> 校订队列</h3>
        <p class="dim">把语料自带拼音标注当作独立第三方，与引擎逐字比对，
          分歧自动进工单，等待词学裁定。</p>
        <p class="cta"><a class="btn" href="review.html">进入校订</a></p>
      </div>
      <div class="card entry">
        <h3><span class="no">⑥</span> 复现与验证</h3>
        <p class="dim">双集答案哈希、前端渲染门禁、口径等价性检查，全部一键可跑。</p>
        <p class="dim">复现说明见 <code>使用说明.md</code>（或下方「复现命令」）。</p>
      </div>
    </div>

    <div class="card">
      <h3>为什么可信：三道锁</h3>
      <ul class="locks">
        <li><b>确定性</b><span>固定种子、无网络/时间依赖，两次运行逐字节一致。</span></li>
        <li><b>双集互证</b><span>公开 700 与第二套 300 的答案哈希独立锁定，改动一处即报警。</span></li>
        <li><b>可复算</b><span>页面上的每个数字都能被 Python 引擎与浏览器 JS 两边独立重算并逐字段对照。</span></li>
      </ul>
    </div>

    <div class="card">
      <h3>复现命令</h3>
      <pre>{{ repro }}</pre>
    </div>
  </div>
  </AppShell>
</template>

<script setup>
/* IndexView.vue —— 「总览」视图：项目一句话 + 六个入口卡 + 三道锁与复现命令。
 *
 * 它是评委/接手者的第一落点：把「这是什么、能点哪、数字怎么来的」一次讲清。
 * 入口卡的链接与 AppShell.vue 保持一致：**相对平铺**（parse.html/browse.html/graph.html/
 * review.html），因为离线产物就在 data/vue/ 根层，没有 view/ 子目录。
 *
 * ⚠ 2026-10-08 精修（本轮交付）：把原来「一句话 + 一行 chip + 六个等权卡」改成有主次的首屏——
 *   ① 指标 chip 改成**数字磁贴**（数字放大、标签在下），第一眼就能读到体量；
 *   ② 新增**起始引导**（点哪三个入口、各自适合什么问题）与「离线数据未注入」的明确空态提示；
 *   ③ 入口卡加编号与 CTA 对齐，三道锁改成「名称 + 一句话」的左侧色条列表。
 *   文案里保留了门禁依赖的「词律探微」「复现」等既有必需文本。
 */
import { computed } from 'vue'
import AppShell from '../components/AppShell.vue'

const props = defineProps({
  corpusN: { type: Number, default: 58852 },
  qingN: { type: Number, default: 26742 },
  rulesV: { type: String, default: '5.0' },
  gateCount: { type: Number, default: 171 },
  root: { type: String, default: '/' },
  stamp: { type: String, default: '' },
  dataNote: { type: String, default: 'data/corpus.db' },
  online: { type: Boolean, default: false },
})

/* 在线/离线判定：优先 props.online；总览入口（main-index.js）未传该 prop，
   故回退按协议判断——file:// = 离线双击（无问答页），http(s) = 由 web/serve.py 提供（可用）。 */
const isOnline = computed(() => props.online
  || (typeof window !== 'undefined' && window.location && window.location.protocol !== 'file:'));

const repro = `python build_corpus.py --corpus <语料根> --db data/corpus.db   # 建库
python web/build_views.py                                  # 生成离线视图的数据文件
python web/serve.py                                        # 启动在线问答（默认 127.0.0.1:8000）
python reproduce.py                                        # 一键复现全部门禁`

function fmt(n) { return Number(n || 0).toLocaleString('en-US') }
</script>

<style scoped>
.ov { max-width: 1100px; margin: 0 auto; }

/* 首屏：把介绍与指标收在一张卡里，线索更集中 */
.hero .lead { margin: 6px 0; }
.hero .start-hint { margin: 12px 0 2px; padding: 8px 12px; border-radius: 8px;
  background: var(--panel2); border-left: 3px solid var(--accent); font-size: 13.5px; }
.hero .start-hint .arrow { color: var(--ink2); margin: 0 6px; }
.hero .warn-line { margin-top: 8px; color: var(--warn); }

/* 指标磁贴：数字大、标签小，扫一眼就能读到体量 */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px; margin: 12px 0 4px; }
.kpi { display: flex; flex-direction: column; gap: 2px; padding: 10px 12px;
  border: 1px solid var(--line); border-radius: var(--r); background: var(--panel2); }
.kpi b { font-size: 20px; line-height: 1.2; font-weight: 700; letter-spacing: .5px; }
.kpi span { font-size: 12px; color: var(--ink2); }
.kpi.ok b { color: var(--ok); }

/* 入口卡：编号 + 标题 + 说明 + 底部对齐的 CTA */
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; margin: 14px 0; }
.entry { display: flex; flex-direction: column; gap: 6px; transition: box-shadow .15s, transform .15s; }
.entry:hover { transform: translateY(-1px); }
.entry h3 { margin: 0; display: flex; align-items: baseline; gap: 7px; }
.entry h3 .no { color: var(--accent); font-weight: 700; font-size: 15px; }
.entry .cta { margin-top: auto; padding-top: 4px; }
.entry .cta .btn { display: inline-block; }

/* 三道锁：名称 + 一句话，左侧色条区分每一条 */
.locks { list-style: none; margin: 8px 0 0; padding: 0; }
.locks li { display: grid; grid-template-columns: 84px 1fr; gap: 4px 12px;
  padding: 8px 0 8px 12px; border-left: 3px solid color-mix(in srgb, var(--accent2) 60%, transparent);
  border-bottom: 1px dashed var(--line); }
.locks li:last-child { border-bottom: none; }
.locks li b { color: var(--ink); }
.locks li span { color: var(--ink2); font-size: 13.5px; }

@media (max-width: 640px) {
  .locks li { grid-template-columns: 1fr; }
}
</style>
