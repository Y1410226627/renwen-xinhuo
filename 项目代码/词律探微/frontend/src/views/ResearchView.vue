<template>
  <AppShell active="research" :stamp="stamp" :data-note="dataNote" :online="isOnline">
  <div class="rs">
    <div class="card">
      <h1>研究库</h1>
      <p class="lead">问答之外的研究资产集中在这里：<b>文献摘录</b>（只增不改）、<b>研究事实</b>（必带出处）、
        <b>读音裁定</b>（每个字都能说清「为什么这么读」）、<b>词谱对照</b>（作品原字 / 规范 / 谱书例词三行）、
        <b>个人录入</b>（来源核验三态）、<b>批量导入</b>（幂等 + 批次对账）、<b>历史快照</b>（每轮问答冻结留档）。</p>
      <p class="dim">三条纪律：① 人工动作一律留<b>决策事件</b>（谁/何时/选了什么/依据/为什么）；
        ② 修订=追加新版本、删除=撤回标记，<b>绝不覆盖历史</b>；③ 写操作带幂等键，重复提交不会记两遍。</p>
      <p v-if="!isOnline" class="off-note">研究库的操作需要本地服务：请运行
        <code>python web/serve.py</code> 后从 <code>http://127.0.0.1:8000/research.html</code> 打开本页。
      </p>
    </div>

    <div class="card">
      <div class="rs-seg" role="tablist">
        <button v-for="t in TABS" :key="t.key" type="button"
                :class="{ on: tab === t.key }" @click="switchTab(t.key)">{{ t.label }}</button>
      </div>
      <p v-if="msg" class="rs-msg">✓ {{ msg }}</p>
      <p v-if="err" class="rs-err">✗ {{ err }}</p>

      <!-- ① 文献摘录 -->
      <section v-if="tab === 'materials'" class="rs-pane">
        <h3>新建摘录</h3>
        <div class="rs-row">
          <input v-model="mForm.title" placeholder="文献名（必填）">
          <select v-model="mForm.kind" title="文献类型">
            <option value="book">书籍 / 论著</option>
            <option value="paper">论文</option>
            <option value="web">网页 / 网络</option>
            <option value="archive">档案 / 手稿</option>
          </select>
          <input v-model="mForm.author" placeholder="作者（可选）">
          <input v-model="mForm.year" placeholder="年份：如 康熙二十三年 / 1684（可选）">
        </div>
        <div class="rs-row">
          <input v-model="mForm.source_url" placeholder="来源地址：如 https://…（可选）">
          <input v-model="mForm.locator" placeholder="定位：如 卷三·页12（可选）">
          <input v-model="mForm.note" placeholder="备注（可选）">
        </div>
        <textarea v-model="mForm.content" rows="3" placeholder="摘录正文（必填）"></textarea>
        <p><button type="button" :disabled="!isOnline" @click="createMaterial">新建摘录</button></p>
        <h3>摘录列表 <small class="dim">（编辑=追加新版本，删除=撤回标记，旧行永不删除）</small></h3>
        <table class="rs-table">
          <thead><tr><th>#</th><th>文献</th><th>类型</th><th>作者</th><th>年份</th><th>版本数</th><th>最新版本时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="m in mList" :key="m.id">
              <td>{{ m.id }}</td>
              <td>{{ m.title }}
                <a v-if="m.source_url" :href="m.source_url" target="_blank" rel="noopener" class="dim">[来源]</a>
                <div v-if="m.note" class="dim">{{ m.note }}</div></td>
              <td class="dim">{{ KIND_LABEL[m.kind] || m.kind }}</td>
              <td>{{ m.author || '—' }}</td>
              <td class="dim">{{ m.year || '—' }}</td>
              <td class="num">{{ m.n_rev }}</td><td class="dim">{{ m.latest_at || '—' }}</td>
              <td>
                <button type="button" class="mini" @click="viewChain(m.id)">版本链</button>
                <button type="button" class="mini danger" :disabled="!isOnline"
                        @click="withdrawMat(m.id)">撤回</button>
              </td>
            </tr>
            <tr v-if="!mList.length"><td colspan="8" class="dim">（还没有摘录）</td></tr>
          </tbody>
        </table>
        <div v-if="mChain" class="rs-detail">
          <h4>版本链 · 材料 #{{ mChain.id }}（{{ mChain.material.title }}）</h4>
          <p class="dim">类型：{{ KIND_LABEL[mChain.material.kind] || mChain.material.kind }}
            · 作者：{{ mChain.material.author || '—' }}
            · 年份：{{ mChain.material.year || '—' }}
            <template v-if="mChain.material.source_url">· 来源：
              <a :href="mChain.material.source_url" target="_blank" rel="noopener">{{ mChain.material.source_url }}</a></template>
            <template v-if="mChain.material.note"><br>备注：{{ mChain.material.note }}</template></p>
          <div v-for="r in mChain.revisions" :key="r.id" class="rs-rev">
            <span class="tag">v{{ r.id }}</span>
            <span class="dim">{{ r.created_at }}</span>
            <span v-if="r.parent_id" class="dim">← v{{ r.parent_id }}</span>
            <p class="rs-content">{{ r.content }}</p>
          </div>
          <textarea v-model="mRev" rows="2" placeholder="追加新版本（旧版本保留）"></textarea>
          <p><button type="button" :disabled="!isOnline" @click="addRevision">追加版本</button>
             <button type="button" class="mini" @click="mChain = null">收起</button></p>
        </div>
      </section>

      <!-- ② 研究事实 -->
      <section v-if="tab === 'facts'" class="rs-pane">
        <h3>登记研究事实 <small class="dim">（必须能回到原文：出处二选一——作品句+引文，或材料+定位）</small></h3>
        <textarea v-model="fForm.statement" rows="2" placeholder="陈述（必填）"></textarea>
        <div class="rs-row">
          <input v-model="fForm.poem_pid" placeholder="作品 pid（可选）">
          <input v-model="fForm.line_idx" placeholder="第几句（0 起）">
          <input v-model="fForm.evidence" placeholder="引文（与原文逐字一致，服务端会核验）">
        </div>
        <div class="rs-row">
          <input v-model="fForm.material_id" placeholder="材料 id（可选）">
          <input v-model="fForm.locator" placeholder="材料内定位">
        </div>
        <p><button type="button" :disabled="!isOnline" @click="createFact">登记事实</button></p>
        <h3>事实列表</h3>
        <table class="rs-table">
          <thead><tr><th>#</th><th>陈述</th><th>出处</th><th>引文核验</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="f in fList" :key="f.id">
              <td>{{ f.id }}</td><td>{{ f.statement }}</td>
              <td class="dim">{{ f.poem_pid ? (f.poem_pid + (f.line_idx !== null ? ' 第' + (f.line_idx + 1) + '句' : '')) : ('材料 #' + f.material_id) }}{{ f.evidence ? ('「' + f.evidence + '」') : '' }}</td>
              <td><span :class="f.verified ? 'badge ok' : 'badge'">{{ f.verified ? '已逐字核验' : '未核验' }}</span></td>
              <td><button type="button" class="mini danger" :disabled="!isOnline"
                          @click="withdrawFact(f.id)">撤回</button></td>
            </tr>
            <tr v-if="!fList.length"><td colspan="5" class="dim">（还没有事实）</td></tr>
          </tbody>
        </table>
      </section>

      <!-- ③ 读音裁定 -->
      <section v-if="tab === 'pron'" class="rs-pane">
        <h3>读音裁定 <small class="dim">（选定/撤回都写决策事件；解析页与证据块按裁定修正展示）</small></h3>
        <div class="rs-row">
          <input v-model="pForm.pid" placeholder="作品 pid">
          <input v-model="pForm.line" placeholder="第几句（0 起）" type="number" min="0">
          <input v-model="pForm.pos" placeholder="第几个汉字（0 起）" type="number" min="0">
          <button type="button" :disabled="!isOnline" @click="loadCand">查候选</button>
        </div>
        <div v-if="pCand" class="rs-detail">
          <p>句：<b>{{ pCand.char }}</b> ｜ 语料基线：<span class="tag">{{ pCand.base_pz || '?' }}</span>
             ｜ 当前裁定：<span v-if="pCand.current_decision" class="tag ok">{{ pCand.current_decision.reading }}
             （{{ pCand.current_decision.tone }} 声）</span><span v-else class="dim">无（走字级标定/普通话）</span></p>
          <p>候选（多来源，点选即裁定）：</p>
          <p>
            <button v-for="c in pCand.candidates" :key="c.reading" type="button" class="mini"
                    :disabled="!isOnline" @click="decide(c)">{{ c.reading }}<small>({{ c.source }})</small></button>
          </p>
          <div class="rs-row">
            <input v-model="pBasis" placeholder="依据（如《广韵》/词谱）">
            <input v-model="pWhy" placeholder="为什么（人话理由）">
          </div>
          <h4>该字位决策史（含撤回）</h4>
          <ul class="rs-hist">
            <li v-for="h in pCand.history" :key="h.id">
              <span class="tag" :class="{ danger: h.action === 'withdraw' }">{{ h.action }}</span>
              {{ h.ts }} · {{ h.payload }} · {{ h.why || '' }}
              <button v-if="h.action === 'select'" type="button" class="mini danger"
                      :disabled="!isOnline" @click="withdrawPron(h.id)">撤回</button>
            </li>
            <li v-if="!pCand.history.length" class="dim">（无）</li>
          </ul>
        </div>
      </section>

      <!-- ④ 词谱对照 -->
      <section v-if="tab === 'cipu'" class="rs-pane">
        <h3>词谱三行对照 <small class="dim">（作品原字 / 规范 / 谱书例词）</small></h3>
        <p class="rs-warn">参照来源：搜韵公开转写（<b>未核原书</b>）· 上游 hulbji/couyun（MIT License）。
          本对照用于研究参考，不等同于原书核验。</p>
        <div class="rs-row">
          <input v-model="cForm.pid" placeholder="作品 pid">
          <input v-model="cForm.tune" placeholder="词牌（可留空自动匹配）">
          <input v-model="cForm.form" placeholder="体号（可留空自动选体）" type="number" min="1">
          <button type="button" :disabled="!isOnline" @click="runCompare">对照</button>
          <button type="button" class="mini" @click="loadTunes">谱库列表（{{ nTunes }} 词牌）</button>
        </div>
        <div v-if="tuneList" class="rs-detail">
          <p class="dim">谱库覆盖：<span v-for="t in tuneList" :key="t.tune" class="tag">{{ t.tune }}×{{ t.n_forms }}</span></p>
        </div>
        <div v-if="cRes">
          <p v-if="cRes.status === 'no_tune'" class="rs-warn">{{ cRes.note }}</p>
          <template v-else>
            <p>词牌 <b>{{ cRes.tune }}</b> ｜ {{ cRes.form.authority }}·格{{ cRes.form.form }}（{{ cRes.form.n_lines }} 句 {{ cRes.form.n_chars }} 字）
               ｜ 选体依据：{{ cRes.form_why }} ｜ 对照：<b class="ok">{{ cRes.summary.n_match }}</b> 合、
               <b class="bad">{{ cRes.summary.n_mismatch }}</b> 不合、{{ cRes.summary.n_any }} 字平仄皆可</p>
            <table class="rs-table cipu">
              <thead><tr><th>句</th><th>作品原字</th><th>规范</th><th>韵/句</th><th>谱书例词</th></tr></thead>
              <tbody>
                <tr v-for="r in cRes.rows" :key="r.line">
                  <td class="num">{{ r.line + 1 }}</td>
                  <td><span v-for="c in r.cells" :key="c.pos" :class="['cell', c.verdict]"
                            :title="c.char + '：' + c.pz + ' / 规范 ' + c.rule">{{ c.char }}</span></td>
                  <td class="mono">{{ r.rule_tones || '—' }}</td>
                  <td>{{ r.ending || '—' }}</td>
                  <td class="dim">{{ r.example || '—' }}</td>
                </tr>
              </tbody>
            </table>
            <p class="dim">{{ cRes.source_note }}</p>
          </template>
        </div>
      </section>

      <!-- ⑤ 我的录入（来源核验三态） -->
      <section v-if="tab === 'works'" class="rs-pane">
        <h3>我的录入 <small class="dim">（与语料库分区：既有 58,852 篇语料恒为「已对上来源」，本区只收新录入）</small></h3>
        <p class="dim">语料来源分布（对照）：
          <span v-for="s in corpusSources" :key="s.name" class="tag">{{ s.name }} ×{{ s.poems }}</span>
          <span v-if="!corpusSources.length">（连上服务后显示）</span>
        </p>
        <div class="rs-row">
          <input v-model="wForm.title" placeholder="题名（必填）">
          <input v-model="wForm.author" placeholder="作者">
          <input v-model="wForm.cipai" placeholder="词牌">
        </div>
        <textarea v-model="wForm.content" rows="2" placeholder="正文（必填）"></textarea>
        <p><button type="button" :disabled="!isOnline" @click="createWork">录入作品（默认草稿）</button></p>
        <p>筛选：<button type="button" class="mini" @click="setFilter('')">全部</button>
          <button type="button" class="mini" @click="setFilter('draft')">草稿</button>
          <button type="button" class="mini" @click="setFilter('material_sample')">材料样例</button>
          <button type="button" class="mini" @click="setFilter('source_matched')">已对上来源</button></p>
        <table class="rs-table">
          <thead><tr><th>#</th><th>题名</th><th>作者</th><th>状态</th><th>来源</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="w in wList" :key="w.id">
              <td>{{ w.id }}</td><td>{{ w.title }}</td><td>{{ w.author || '—' }}</td>
              <td><span class="badge" :class="{ ok: w.verification_state === 'source_matched' }">{{ stateLabel(w.verification_state) }}</span></td>
              <td class="dim">{{ w.source || '—' }}</td>
              <td>
                <a v-if="isOnline" class="mini" :href="'parse.html?pid=personal:' + w.id" title="进入逐字解析（pid=personal:<id>，走研究库，不改语料库）">研读</a>
                <button type="button" class="mini" @click="editWork(w.id)">流转</button>
              </td>
            </tr>
            <tr v-if="!wList.length"><td colspan="6" class="dim">（还没有录入）</td></tr>
          </tbody>
        </table>
        <div v-if="wEdit" class="rs-detail">
          <h4>作品 #{{ wEdit.id }} 状态流转</h4>
          <div class="rs-row">
            <select v-model="wState">
              <option value="draft">草稿</option>
              <option value="material_sample">材料样例</option>
              <option value="source_matched">已对上来源</option>
            </select>
            <input v-model="wSource" placeholder="来源说明（选「已对上来源」时必填，不许空口自证）">
          </div>
          <p><button type="button" :disabled="!isOnline" @click="doVerify">确认流转（留决策事件）</button>
             <button type="button" class="mini" @click="wEdit = null">收起</button></p>
        </div>
      </section>

      <!-- ⑥ 批量导入 -->
      <section v-if="tab === 'imports'" class="rs-pane">
        <h3>批量导入 <small class="dim">（JSONL 文件；manifest + SHA256 + 批次对账；重复导入不产生重复行）</small></h3>
        <div class="rs-row">
          <input type="file" accept=".jsonl,.txt,.json" @change="pickImportFile">
          <input v-model="impTag" placeholder="批次名（默认取文件名）">
          <button type="button" :disabled="!isOnline || !impFile" @click="runImport">导入</button>
        </div>
        <p v-if="impFile" class="dim">已选择：{{ impFile.name }}（{{ impRows.length }} 行）
          <span v-if="impErr" class="rs-err">✗ {{ impErr }}</span></p>
        <p v-if="impRes" class="rs-msg" v-html="impResultText"></p>
        <h3>批次对账</h3>
        <button type="button" class="mini" @click="loadBatches">刷新</button>
        <table class="rs-table">
          <thead><tr><th>批次</th><th>名称</th><th>状态</th><th>承诺</th><th>现存行</th><th>作品</th><th>时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="b in batches" :key="b.id">
              <td>#{{ b.id }}</td><td>{{ b.tag }}</td>
              <td><span class="badge" :class="{ ok: b.status === 'committed' }">{{ b.status === 'committed' ? '已导入' : '已回滚' }}</span></td>
              <td class="num">{{ b.n_rows }}</td><td class="num">{{ b.rows_now }}</td><td class="num">{{ b.works_now }}</td>
              <td class="dim">{{ b.created_at }}</td>
              <td><button v-if="b.status === 'committed'" type="button" class="mini danger"
                          :disabled="!isOnline" @click="rollbackBatch(b.id)">回滚</button></td>
            </tr>
            <tr v-if="!batches.length"><td colspan="8" class="dim">（还没有批次）</td></tr>
          </tbody>
        </table>
      </section>

      <!-- ⑦ 历史快照 -->
      <section v-if="tab === 'snapshots'" class="rs-pane">
        <h3>历史快照 <small class="dim">（每轮问答自动冻结；回查原文返回、不用现在的引擎重算）</small></h3>
        <button type="button" class="mini" @click="loadSnaps">刷新</button>
        <table class="rs-table">
          <thead><tr><th>快照</th><th>时间</th><th>问题</th><th>命中</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="s in sList" :key="s.snapshot_id">
              <td class="mono">{{ s.snapshot_id }}</td><td class="dim">{{ s.ts }}</td>
              <td>{{ s.question }}</td><td class="num">{{ s.total }}</td>
              <td><button type="button" class="mini" @click="viewSnap(s.snapshot_id)">回查</button></td>
            </tr>
            <tr v-if="!sList.length"><td colspan="5" class="dim">（还没有快照——去「声情问答」问一句，这里就会有一条）</td></tr>
          </tbody>
        </table>
        <div v-if="sView" class="rs-detail">
          <h4>快照 {{ sView.snapshot_id }}（{{ sView.ts }}）</h4>
          <p v-if="sView.stale" class="rs-warn">⚠ {{ sView.stale_note }}</p>
          <p v-else class="dim">依赖未陈旧（口径指纹与当时一致）。</p>
          <p>问句：{{ sView.question }} ｜ 理解：{{ sView.spec }} ｜ 命中：{{ sView.total }} 篇
             ｜ 集合指纹：<span class="mono">{{ sView.result && sView.result.pids_sha }}</span></p>
          <p>护栏：{{ sView.verify && sView.verify.ok ? '通过' : '未通过' }}
             ｜ 集合身份：{{ sView.set_check && sView.set_check.status }}</p>
          <p class="rs-content">{{ sView.answer }}</p>
          <p><button type="button" class="mini" @click="sView = null">收起</button></p>
        </div>
      </section>
    </div>
  </div>
  </AppShell>
</template>

<script setup>
/* ResearchView.vue —— 「研究库」视图（2026-10-09 新增；功能 1/6/7/8/9/11/12/13/15/18 的统一入口）。
 *
 * 设计纪律：
 *   · **在线专用**——全部数据与写操作走 /api/*（离线打开时顶部如实说明，不发假数据）；
 *   · 写操作先点「发生一次用户动作」→ 生成 `client_token`（幂等键），网络重试不会记两遍；
 *   · 后端返回什么就展示什么（徽标/白账/候选全部来自接口，不在前端造数字）。
 */
import { computed, onMounted, ref } from 'vue'
import AppShell from '../components/AppShell.vue'
import { api, post, newToken } from '../api.js'

defineProps({
  stamp: { type: String, default: '' },
  dataNote: { type: String, default: 'data/research.db（研究库）' },
})

const TABS = [
  { key: 'materials', label: '文献摘录' },
  { key: 'facts', label: '研究事实' },
  { key: 'pron', label: '读音裁定' },
  { key: 'cipu', label: '词谱对照' },
  { key: 'works', label: '我的录入' },
  { key: 'imports', label: '批量导入' },
  { key: 'snapshots', label: '历史快照' },
]
const tab = ref('materials')
const msg = ref('')
const err = ref('')
const isOnline = computed(() =>
  typeof window !== 'undefined' && window.location && window.location.protocol !== 'file:')

function flash(m, e) {
  msg.value = e ? '' : (m || '')
  err.value = e ? (typeof e === 'string' ? e : (e.message || String(e))) : ''
}
function switchTab(k) {
  tab.value = k
  msg.value = ''
  err.value = ''
  if (k === 'materials' && isOnline.value) { loadMaterials() }
  if (k === 'facts' && isOnline.value) { loadFacts() }
  if (k === 'works' && isOnline.value) { loadWorks(); loadCatalog() }
  if (k === 'imports' && isOnline.value) { loadBatches() }
  if (k === 'snapshots' && isOnline.value) { loadSnaps() }
  if (k === 'cipu' && isOnline.value && !tuneList.value) { loadTunes() }
}
async function guard(fn) {
  try { await fn() } catch (e) { flash('', e) }
}

/* ① 文献摘录 */
/* 2026-10-11（P2-3）：文献档案字段进 UI——类型 / 年份 / 来源地址 / 备注。
 * kind 取值与后端 materials 表注释一致：book / paper / web / archive。 */
const KIND_LABEL = { book: '书籍 / 论著', paper: '论文', web: '网页 / 网络', archive: '档案 / 手稿' }
const mForm = ref({ title: '', kind: 'book', author: '', year: '', source_url: '',
                    locator: '', note: '', content: '' })
const mList = ref([])
const mChain = ref(null)
const mRev = ref('')
function loadMaterials() {
  return guard(async () => {
    const j = await api.materials(true)
    mList.value = (j && j.result) || []
  })
}
function createMaterial() {
  return guard(async () => {
    if (!mForm.value.title.trim() || !mForm.value.content.trim()) { return flash('', '文献名与摘录正文为必填') }
    const j = await post.material(Object.assign({}, mForm.value, { client_token: newToken() }))
    flash('已新建摘录 #' + j.result.material_id)
    mForm.value = { title: '', kind: 'book', author: '', year: '', source_url: '',
                    locator: '', note: '', content: '' }
    loadMaterials()
  })
}
function viewChain(id) {
  return guard(async () => {
    const j = await api.material(id)
    mChain.value = Object.assign({ id }, j.result)
  })
}
function addRevision() {
  return guard(async () => {
    if (!mRev.value.trim()) { return flash('', '请填写新版本内容') }
    const j = await post.materialRevision({ material_id: mChain.value.id, content: mRev.value, client_token: newToken() })
    flash('已追加版本 v' + j.result.version + '（旧版本保留）')
    mRev.value = ''
    viewChain(mChain.value.id)
    loadMaterials()
  })
}
function withdrawMat(id) {
  return guard(async () => {
    const j = await post.materialWithdraw({ material_id: id, why: '界面撤回', client_token: newToken() })
    flash('已撤回材料 #' + id + '（行保留，决策事件 #' + (j.result.decision_id || '') + '）')
    if (mChain.value && mChain.value.id === id) { mChain.value = null }
    loadMaterials()
  })
}

/* ② 研究事实 */
const fForm = ref({ statement: '', poem_pid: '', line_idx: '', evidence: '', material_id: '', locator: '' })
const fList = ref([])
function loadFacts() {
  return guard(async () => {
    const j = await api.facts({})
    fList.value = (j && j.result) || []
  })
}
function createFact() {
  return guard(async () => {
    const f = fForm.value
    if (!f.statement.trim()) { return flash('', '陈述为必填') }
    const d = { statement: f.statement, client_token: newToken() }
    if (f.poem_pid.trim()) { d.poem_pid = f.poem_pid.trim() }
    if (f.line_idx !== '' && f.line_idx !== null) { d.line_idx = Number(f.line_idx) }
    if (f.evidence.trim()) { d.evidence = f.evidence.trim() }
    if (f.material_id !== '' && f.material_id !== null) { d.material_id = Number(f.material_id) }
    if (f.locator.trim()) { d.locator = f.locator.trim() }
    const j = await post.fact(d)
    flash('已登记事实 #' + j.result.fact_id + '（引文核验：'
      + (j.result.verified ? '逐字通过' : (j.result.verify_detail || '未核验')) + '）')
    fForm.value = { statement: '', poem_pid: '', line_idx: '', evidence: '', material_id: '', locator: '' }
    loadFacts()
  })
}
function withdrawFact(id) {
  return guard(async () => {
    await post.factWithdraw({ fact_id: id, why: '界面撤回', client_token: newToken() })
    flash('已撤回事实 #' + id)
    loadFacts()
  })
}

/* ③ 读音裁定 */
const pForm = ref({ pid: '', line: 0, pos: 0 })
const pCand = ref(null)
const pBasis = ref('')
const pWhy = ref('')
function loadCand() {
  return guard(async () => {
    pCand.value = null
    const j = await api.pronCandidates(pForm.value.pid.trim(), Number(pForm.value.line) || 0, Number(pForm.value.pos) || 0)
    pCand.value = j.result
  })
}
function decide(c) {
  return guard(async () => {
    const j = await post.pronDecide({
      pid: pForm.value.pid.trim(), line: Number(pForm.value.line) || 0, pos: Number(pForm.value.pos) || 0,
      reading: c.reading, tone: c.tone, basis: pBasis.value, why: pWhy.value, client_token: newToken(),
    })
    flash('已裁定：' + c.reading + '（决策 #' + j.result.decision_id + '）')
    loadCand()
  })
}
function withdrawPron(id) {
  return guard(async () => {
    await post.pronWithdraw({ decision_id: id, why: '界面撤回', client_token: newToken() })
    flash('已撤回裁定 #' + id + '（回到基线）')
    loadCand()
  })
}

/* ④ 词谱对照 */
const cForm = ref({ pid: '', tune: '', form: '' })
const cRes = ref(null)
const tuneList = ref(null)
const nTunes = computed(() => (tuneList.value ? tuneList.value.length : 20))
function loadTunes() {
  return guard(async () => {
    const j = await api.cipuList()
    tuneList.value = (j && j.result) || []
  })
}
function runCompare() {
  return guard(async () => {
    cRes.value = null
    const opt = {}
    if (cForm.value.tune.trim()) { opt.tune = cForm.value.tune.trim() }
    if (cForm.value.form !== '' && cForm.value.form !== null) { opt.form = Number(cForm.value.form) }
    const j = await api.cipuCompare(cForm.value.pid.trim(), opt)
    cRes.value = j.result
  })
}

/* ⑤ 我的录入 */
const wForm = ref({ title: '', author: '', cipai: '', content: '' })
const wList = ref([])
const wFilter = ref('')
const wEdit = ref(null)
const wState = ref('draft')
const wSource = ref('')
const corpusSources = ref([])
const STATES = { draft: '草稿', material_sample: '材料样例', source_matched: '已对上来源' }
function stateLabel(s) { return STATES[s] || s }
function loadWorks() {
  return guard(async () => {
    const j = await api.works(wFilter.value)
    wList.value = (j && j.result) || []
  })
}
function loadCatalog() {
  return guard(async () => {
    const j = await api.catalog(5)
    corpusSources.value = (j && j.source) || []
  })
}
function setFilter(s) { wFilter.value = s; loadWorks() }
function createWork() {
  return guard(async () => {
    if (!wForm.value.title.trim() || !wForm.value.content.trim()) { return flash('', '题名与正文为必填') }
    const j = await post.work(Object.assign({}, wForm.value, { client_token: newToken() }))
    flash('已录入作品 #' + j.result.work_id + '（' + j.result.label + '）')
    wForm.value = { title: '', author: '', cipai: '', content: '' }
    loadWorks()
  })
}
function editWork(id) {
  const w = wList.value.find((x) => x.id === id)
  wEdit.value = w || { id }
  wState.value = (w && w.verification_state) || 'draft'
  wSource.value = (w && w.source) || ''
}
function doVerify() {
  return guard(async () => {
    const j = await post.workVerify({ work_id: wEdit.value.id, state: wState.value, source: wSource.value, why: '界面流转', client_token: newToken() })
    flash('作品 #' + j.result.work_id + '：' + stateLabel(j.result.from) + ' → ' + j.result.label)
    wEdit.value = null
    loadWorks()
  })
}

/* ⑥ 批量导入 */
const impFile = ref(null)
const impRows = ref([])
const impErr = ref('')
const impTag = ref('')
const impRes = ref(null)
const batches = ref([])
const impResultText = computed(() => {
  const r = impRes.value
  if (!r) { return '' }
  if (r.already) { return '同内容批次已导入过（清单哈希 ' + r.manifest_sha + '），本次零新增。' }
  return '批次 #' + r.batch_id + ' 导入完成：新增 ' + r.inserted + ' 行、跳过 ' + r.skipped + ' 行（清单哈希 ' + r.manifest_sha + '）'
})
function pickImportFile(ev) {
  impErr.value = ''
  impRes.value = null
  impRows.value = []
  impFile.value = null
  const f = ev && ev.target && ev.target.files && ev.target.files[0]
  if (!f) { return }
  impFile.value = f
  const rd = new FileReader()
  rd.onload = () => {
    try {
      const rows = String(rd.result || '').split('\n').map((s) => s.trim()).filter(Boolean)
        .map((s) => JSON.parse(s))
      impRows.value = rows
    } catch (e) { impErr.value = 'JSONL 解析失败：' + (e.message || e) }
  }
  rd.onerror = () => { impErr.value = '文件读取失败' }
  rd.readAsText(f, 'utf-8')
}
function runImport() {
  return guard(async () => {
    if (!impFile.value || impErr.value) { return flash('', impErr.value || '请先选择文件') }
    const j = await post.importBatch({
      tag: impTag.value.trim() || impFile.value.name,
      files: [{ name: impFile.value.name, rows: impRows.value }],
      client_token: newToken(),
    })
    impRes.value = j.result
    loadBatches()
  })
}
function loadBatches() {
  return guard(async () => {
    const j = await api.importBatches()
    batches.value = (j && j.result) || []
  })
}
function rollbackBatch(id) {
  return guard(async () => {
    const j = await post.importRollback({ batch_id: id, why: '界面回滚', client_token: newToken() })
    flash('已回滚批次 #' + id + '（撤下 ' + j.result.removed_rows + ' 行 / ' + j.result.removed_works + ' 篇）')
    loadBatches()
  })
}

/* ⑦ 历史快照 */
const sList = ref([])
const sView = ref(null)
function loadSnaps() {
  return guard(async () => {
    const j = await api.snapshots(30)
    sList.value = (j && j.result) || []
  })
}
function viewSnap(id) {
  return guard(async () => {
    const j = await api.snapshot(id)
    sView.value = j.result
  })
}

onMounted(() => {
  if (!isOnline.value) { return }
  loadMaterials()
})
</script>

<style scoped>
/* 研究库视图样式（scoped：只作用于本页，不碰 core/ui.js 与其它视图）。 */
.rs { display: grid; gap: 14px; }
.rs h1 { margin: 0 0 6px; }
.rs .lead { margin: 4px 0 8px; }
.off-note { border-left: 3px solid var(--accent, #a64333); padding: 6px 10px; margin: 8px 0 0; background: var(--panel, #fbf8f1); }
.rs-seg { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 12px; }
.rs-seg button { border: 1px solid var(--line, #d2caba); background: transparent; padding: 5px 12px; cursor: pointer; border-radius: 3px; }
.rs-seg button.on { background: #292722; color: #fbf8f1; border-color: #292722; }
.rs-msg { color: #3d6a3d; margin: 6px 0; }
.rs-err { color: #8e3025; margin: 6px 0; }
.rs-warn { color: #8e3025; border-left: 3px solid #a64333; padding: 4px 10px; background: var(--panel, #fbf8f1); }
.rs-pane h3 { margin: 14px 0 8px; }
.rs-pane h4 { margin: 10px 0 6px; }
.rs-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0; }
.rs-row input, .rs-row select { padding: 5px 8px; border: 1px solid var(--line, #d2caba); border-radius: 3px; background: var(--input, #fcf9f4); color: inherit; }
.rs-pane textarea { width: 100%; box-sizing: border-box; padding: 6px 8px; border: 1px solid var(--line, #d2caba); border-radius: 3px; background: var(--input, #fcf9f4); color: inherit; font: inherit; }
.rs-pane button { padding: 5px 14px; border: 1px solid var(--line, #d2caba); border-radius: 3px; background: transparent; color: inherit; cursor: pointer; }
.rs-pane button:hover:not(:disabled) { border-color: var(--accent, #a64333); color: var(--accent, #a64333); }
.rs-pane button:disabled { opacity: .45; cursor: not-allowed; }
.rs-pane .mini { padding: 2px 9px; font-size: 12px; margin-right: 4px; }
.rs-pane .mini.danger { color: #8e3025; }
.rs-table { width: 100%; border-collapse: collapse; margin: 6px 0 10px; }
.rs-table th, .rs-table td { border-bottom: 1px solid var(--line, #d2caba); padding: 5px 8px; text-align: left; font-size: 13px; vertical-align: top; }
.rs-table td.num, .rs-table th.num { text-align: right; font-variant-numeric: tabular-nums; }
.rs-detail { border: 1px solid var(--line, #d2caba); border-radius: 4px; padding: 10px 12px; margin: 8px 0; background: var(--panel, #fbf8f1); }
.rs-rev { border-bottom: 1px dashed var(--line, #d2caba); padding: 4px 0; }
.rs-content { white-space: pre-wrap; margin: 4px 0; }
.tag { display: inline-block; border: 1px solid var(--line, #d2caba); border-radius: 3px; padding: 0 6px; margin-right: 6px; font-size: 12px; }
.tag.ok { border-color: #3d6a3d; color: #3d6a3d; }
.tag.danger { border-color: #8e3025; color: #8e3025; }
.badge { border: 1px solid var(--line, #d2caba); border-radius: 3px; padding: 0 6px; font-size: 12px; }
.badge.ok { border-color: #3d6a3d; color: #3d6a3d; }
.mono { font-family: Consolas, Menlo, monospace; font-size: 12px; }
.dim { color: var(--ink2, #746e62); }
.ok { color: #3d6a3d; }
.bad { color: #8e3025; }
.rs-hist { margin: 4px 0; padding-left: 18px; }
.rs-hist li { margin: 3px 0; }
.cipu .cell { display: inline-block; min-width: 1em; text-align: center; border-bottom: 2px solid transparent; }
.cipu .cell.match { border-bottom-color: #3d6a3d; }
.cipu .cell.mismatch { border-bottom-color: #a64333; color: #a64333; font-weight: 600; }
.cipu .cell.any { border-bottom-style: dashed; border-bottom-color: var(--line, #d2caba); }
</style>
