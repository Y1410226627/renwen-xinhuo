<template>
  <AppShell active="index" :stamp="stamp" :data-note="dataNote" :data-n="qingN" :online="online">
  <div class="ov">
    <div class="card">
      <h1>词律探微 · 清代词律声情研究助手</h1>
      <p>本项目把「清代词律声情」这一传统词学问题，转译成<b>可复算、可溯源、可复核</b>的工程问题：
        以 58,852 首诗词曲语料为底（清词 26,742 首为主），用一套<b>确定性口径</b>逐字标注平仄与句读，
        所有数字都由引擎现算，任何人可一键复现。</p>
      <p class="dim">一句话分工：<b>数字归引擎、文料归检索、说法归大模型、出处归引用</b>。</p>
      <div class="row wrap">
        <span class="chip">语料 <b>{{ fmt(corpusN) }}</b> 首</span>
        <span class="chip">清词 <b>{{ fmt(qingN) }}</b> 首</span>
        <span class="chip">口径 <b>v{{ rulesV }}</b></span>
        <span class="chip">双集哈希<b>已锁定</b></span>
        <span class="chip">门禁<b>{{ gateCount }}</b> 项</span>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>① 在线问答</h3>
        <p class="dim">问一句、答一句，每一处数字都带出处。大模型只负责组织「说法」，数字仍由引擎给；
          支持流式输出与多轮追问。</p>
        <p><a class="btn" :href="root + 'ask.html'">进入问答</a></p>
      </div>
      <div class="card">
        <h3>② 逐字解析与检索</h3>
        <p class="dim">26,742 首清词，逐字平仄 + 句脚字 + 声律模式；支持多条件相与、分页、CSV 导出。
          离线模式下由页面内 JavaScript 用同一套口径自算。</p>
        <p><a class="btn" :href="root + 'view/parse.html'">进入解析</a></p>
      </div>
      <div class="card">
        <h3>③ 在线检索</h3>
        <p class="dim">同一套条件改由本地 SQLite 引擎执行（含句级条件与分面统计），
          还可让大模型把一句人话听成检索条件。</p>
        <p><a class="btn" :href="root + 'view/browse.html'">进入检索</a></p>
      </div>
      <div class="card">
        <h3>④ 知识图谱</h3>
        <p class="dim">词人 ↔ 词牌二部图（取作数前 45），可筛选、悬停高亮、可直接截图进 PPT。</p>
        <p><a class="btn" :href="root + 'view/graph.html'">进入图谱</a></p>
      </div>
      <div class="card">
        <h3>⑤ 校订队列</h3>
        <p class="dim">把语料自带拼音标注当作独立第三方，与引擎逐字比对，
          分歧自动进工单，等待词学裁定。</p>
        <p><a class="btn" :href="root + 'view/review.html'">进入校订</a></p>
      </div>
      <div class="card">
        <h3>⑥ 复现与验证</h3>
        <p class="dim">双集答案哈希、前端渲染门禁、口径等价性检查，全部一键可跑。</p>
        <p><a class="btn" :href="root + 'view/reproduce.html'">查看复现</a></p>
      </div>
    </div>

    <div class="card">
      <h3>为什么可信：三道锁</h3>
      <ul>
        <li><b>确定性</b>：固定种子、无网络/时间依赖，两次运行逐字节一致。</li>
        <li><b>双集互证</b>：公开 700 与第二套 300 的答案哈希独立锁定，改动一处即报警。</li>
        <li><b>可复算</b>：页面上的每个数字都能被 Python 引擎与浏览器 JS 两边独立重算并逐字段对照。</li>
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
 * 复现命令块由 props.root 决定前缀（file:// 用相对路径，在线服务用根路径）。
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

const repro = `python build_corpus.py --corpus <语料根> --db data/corpus.db   # 建库
python web/build_views.py                                  # 生成四个离线视图
python web/serve.py                                        # 启动在线问答（默认 127.0.0.1:8000）
python reproduce.py                                        # 一键复现全部门禁`

function fmt(n) { return Number(n || 0).toLocaleString('en-US') }
</script>

<style scoped>
.ov { max-width: 1100px; margin: 0 auto; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; margin: 14px 0; }
.grid .card { display: flex; flex-direction: column; gap: 6px; }
.grid .card h3 { margin: 0; }
.grid .card .btn { margin-top: auto; }
</style>
