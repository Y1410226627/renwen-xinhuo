# AGENTS.md —— 接手入口（先读什么、再读什么）

> 本文件给**下一位接手者**（人或 AI 协作者）一条**最短理解路径**。
> **一句话**：本项目把清代词作的声律做成**可复算的数字**，用检索端**证据与原文**，
> 大模型只负责**说得通顺**——每处数字都要能被引擎追认。
> **一句口令**：**数字归引擎、文料归检索、说法归生成、出处归引用。**

---

## 一、先读这几份（按顺序）

| 顺序 | 文件 | 给你什么 |
| --- | --- | --- |
| 0 | `CONTRIBUTING.md` | **维护手册（动手前必读）**：改一处的五步流程、门禁清单、**六条红线**、三条链边界、双库同步 |
| 1 | `solve/README.md` | **实现与自检总纲**：当前状态、每条命令怎么复现、口径演变、踩过的坑 |
| 2 | `DECISIONS.md` | **决策表**：已接受/已拒绝/已暂缓，以及**为什么没选另一种改法**（防重复试错） |
| 3 | `GLOSSARY.md` | **术语与措辞禁忌**：哪些话我们**不该说**（如「仄声越多越悲壮」） |
| 4 | `外部审查处置表.md` | 外部审查**逐项处置与状态**（已修／未做及理由）；第二轮架构重构见 `DECISIONS.md` D26 与 `solve/README.md` §49 |
| 5 | `CHANGELOG.md` | **每次对外可见的变化**（新增/修复/口径/工程机制）+ 零回归锚点声明 |

> **改完先跑什么（一句话）**：`python tools/check_all.py --fast`（10–20 秒，改完随手验）；
> 提交前跑全档 `python tools/check_all.py`。详见 §三。

---

## 二、代码地图（三条链，物理隔离）

```
solve/                        交付链（**答案的唯一来源**，不 import ask/retrieve）
├── corpus.py    语料加载（清=poetry-source / 宋·元=chinese-poetry）
├── pronounce.py 逐字注音 + 平仄（标定表 pron_overrides.json）
├── prosody.py   句级/篇级指标 + 官方题型 C1–C5
├── solver.py    题面 → 定位 → 计算 → 答案（**入口**）
├── aggregate.py 分组统计（聚合题）
├── pairing.py   配对题
├── official.py  官方「甲乙两篇对比」题识别
├── ask.py       **问答链**（检索 + 证据 + 四道护栏）    ← 与上列**互不导入**
└── retrieve.py  多路检索（词面/元数据/全文/数值/声律模式/向量）
    guard.py     四道护栏（数字/引用/无据/边界）
    answer_reason.py 拒答理由八态（附加层，只读结果）
    ── 第二轮架构重构：**默认关闭、按需启用**（开启后对交付答案零影响）──
    queryplan.py   **Query Plan（执行真源）**：`LEAF_SCHEMA` 26 字段 + 布尔树编译 + to_plan/from_plan/to_spec
    planner.py     LLM 规划器：Prompt 由 `LEAF_SCHEMA` **现场生成**；无效实体→恒假哨兵（绝不剪枝成全库）
    plan_exec.py   计划执行器：**22 算子** + `ProvDAG` 溯源（`LVC_PLANNER=plan` 时接管主链）
    context.py     服务端会话语境：完整结果集 + 指代分类 + EXACT/SEMANTIC 区分
    fusion.py      RRF 名次融合 + 可选精排（`LVC_RERANK=1`）
    vector_index.py / llm_embed.py  真向量检索（SQLite 为真源、向量为派生索引）
    similar_ask.py 「与《某篇》**类似**」的**语义相似**作答（窄口径前置分支；不可用即返回 None 回落主链）
    ── 2026-10-11 二期能力增补（**原有功能与效果零回归**）──
      · `LVC_VECTOR` **默认开启**（`LVC_VECTOR=0` 显式关）：仅在 `semantic_signal(spec)` 为真
        （语义扩展词 / 2+ 字自由词面）时触发；纯形式条件问句 keywords 为空 → 不进向量块；
        索引不可用/断网/异常 → `_vector_channel` 返回 `{}`，与「关闭」逐字节一致。
        官方题型（C1–C5）走 `official.py`/`solver.py`，**不经过** `retrieve.search` 的向量块
        → 1000 题/700 答案完全不受影响（已验 SHA256 恒等）。
      · **纯主题词面向量主导排序**：当问句只剩自由词面（无任何形式硬条件）且该词面在正文
        **字面 0 命中**时，候选在硬条件（`restrict`）内按向量分降序展示——修「羁旅愁思」
        这类字面不重合的语义问句被元曲 bigram 噪声顶掉的老问题。1000 题全为有硬条件题 → 零影响。
      · **请求量词前缀剥离**（`_strip_ask_prefix`）：「找几首/给我几首/来两首…」等**请求前缀**
        不再与主题词粘连污染词面（否则「羁旅愁思」会被毁成「里写羁旅愁思」→ 全文路 0 召回）。
    ── 2026-10-11 深夜 二期能力增补 ② （语义可达面扩展，**零回归**）──
      · **词面净化·串首语法壳剥离**：在请求前缀之上，继续剥**串首**的「内容引导动词」
        （写/描写/咏/题/赋/记/吟/作/表达/寄托…）与「属性壳词」（意境/风格/题材/格调…）
        ——「写羁旅愁思」→「羁旅愁思」、「意境苍凉」→「苍凉」。
        ★ 关键陷阱：`咏梅/咏怀/咏史/题画` 等**凝固复合词**的词头与引导动词同形，
          用负向前瞻白名单（`_FUSED_AFTER_VERB`）保护，**不得误剥**；
          剥后**剩余汉字 < 2 字则回退**（绝不把词面剥成空/单字）。
      · **相似意图拓宽**（`similar_ask.is_similarity_ask`）：新增**显式仿照句式**触发
        （像《X》那样 / 仿《X》/ 比照《X》/ 效仿《X》），**不再**要求句中含「相似/类似」二字
        ——修「像《声声慢》那样写愁的词」进不来。回归防线：含《》但问**形式/事实**
        （「《临江仙》有多少首」「《蝶恋花》的平仄配置」）**不得**被误吞。
      · **向量索引扩展到全量语料**（数据层，不改代码）：由「仅清词 26,742 首」→
        **全量 58,852 首（清+宋+元）**。宋/元的语义问法从「够不着」变「够得着」；
        因 `_vector_channel` 走 `allow=restrict` 的受限检索，硬条件（如限清词）**照旧收窄**，
        只是候选宇宙变大，**不改变任何既有题的命中集合**。
        ✅ **2026-10-11 完成**：`build_vector_index.py --only poems` 增量建成 58,852 篇
        （manifest `n_poems=58852`，`available()=True`）；跨朝代实测通过——
        「意境苍凉的宋词」→ 宋·李震《贺新郎》、「写人生感慨的元词」→ 元·马致远，
        「咏梅的宋词」→ 姜夔《卜算子》；仿真句式（像/仿/比照《X》）均被 `similar_ask` 接管且过护栏；
        回归防线（《临江仙》有多少首 等）未误吞。重建期 `selftest` 曾一度 269/1
        （索引条数与 manifest 不符 → 语义降级 → 无 blocks），完成后恢复 **270/0**。
    answer_verify.py 集合身份校验（五态）+ 聚合复算（三态）
    entity_resolve.py 实体解析层（作者/词牌/题名收口，替代 `rescue_*` 补丁链）
    ── 研究库批次（2026-10-09；**默认零影响**，未使用即逐字节如旧）──
    research.py    研究库（`data/research.db`）：摘录/事实/读音裁定/个人录入/导入批次/版本链/决策事件/幂等键
    snapshot.py    冻结式问答快照（`data/snapshots/`；回查不重算 + 陈旧标注）
    cipu.py        词谱对照（`data/cipu/` 144 体；三行对照；来源红线「搜韵公开转写（未核原书）」）
    intake.py      录入体检（只读：题名当正文/句读/词牌体式匹配）

web/   演示页与后端服务
├── serve.py         本地服务：/api/*（含写接口 POST，见 接口文档 §3.4）+ 静态页；问答页取 web/dist/ask/，离线视图取 data/vue/
├── test_api.py      服务端门禁（143 项）
├── test_research.py 研究库门禁（89 项；功能 1/6/7/8/11/12/13/15/18）
├── test_cipu.py     词谱门禁（23 项；功能 9）
├── build_views.py   生成离线视图**数据**（pack.js/graph.json/rev.js）+ 门禁用的 JSON
├── vmload.js        门禁共用的 vm 装载器（受控 require，加载 core 真源）
├── test_ui.js / test_render.js / verify_views.js   前端门禁
└── metrics.js / ui.js / app_*.js   **薄转发**（一行 require → frontend/src/core/，勿在此改）

frontend/  Vue3 + Vite 前端（**视图与逻辑层的唯一真源**）
├── src/core/       纯逻辑唯一真源（UMD，可被 node 门禁与 Vue 共用）：
│   metrics.js 声律指标 / ui.js 样式与工具 / parse.js 判定表与渲染
│   review.js 校订队列 / ask.js 问答渲染
├── src/views/      6 视图组件：IndexView / AskView / ParseView(离线+在线) / GraphView / ReviewView
├── src/components/AppShell.vue   外壳（导航/主题/页脚）
├── src/api.js      /api/* 客户端（含 SSE 流式解析）  src/stores/theme.js 主题
├── tools/build-all.mjs  一键构建（**先 Vite 后 Python**，顺序不能反）
├── tools/check-core.cjs 逻辑层等价性（core vs 冻结基线，全库逐字节）
└── tools/ssr-smoke.mjs  组件冒烟（6 视图 SSR 渲染）

tools/ 门禁与工具（见下）
data/  corpus.db、golden_sha.json、corpus_manifest.json、存疑清单.md、web_poems.json…；vue/ = 前端构建产物
```

**关键**：`solver.py` **不导入** `ask/retrieve` → 改问答层**不可能**动交付答案（见 `DECISIONS.md` D07）。

---

## 三、改完先跑什么（门禁四件套 + 快照）

> **★ 一键入口（最常用）**：`python tools/check_all.py --fast`（10–20 秒）／全档 `python tools/check_all.py`（3–6 分钟）。
> 全档跑齐：交付答案 SHA256 + **双集零回归（regress）** + `selftest` + `test_api` + `check-core` + `verify_1000`。
> 失败**即停**，缺环境**显式 SKIP**（不算通过）。`--list` 只看要跑哪些，`--only` 只跑指定门禁。
> ★ **2026-10-13 补**：双集回归（`--only regress`，约 14 秒）进全档——此前只校 `answers_700` 的
> SHA256，**300 题保密集没有进统一门禁**，零回归只防了一半；现在公开 + 第二套**都逐字节一致才算过**。

| 命令 | 管什么 |
| --- | --- |
| `python tools/check_all.py [--fast]` | **★ 统一门禁入口**（推荐；见上） |
| `python solve/selftest.py` | 结构/安全/说法层自检（当前 **294 项 0 失败**） |
| `python tools/regress.py --questions <题面> --gold <答案> --tag 公开` | **双集零回归**（逐字节哈希；公开 `BF863368…`、第二套 `ACEF8B15…`）——全档已内置，也可单独 `--only regress` |
| `python solve/tone_policy.py --pid <pid>` | **声律双口径对照**（评测口径 vs 《广韵》历史口径；逐字位四态，见 `GLOSSARY` 第六节） |
| `python tools/verify_1000.py` | **逐题复核：答非所问 + 准确性**（条件理解一致性 + 形态 + 真值） |
| `python tools/loop_check.py` | N 遍自检 + 代码树冻结 |
| `python tools/snapshot_answers.py --snapshot <answers.jsonl> --tag <标签>` | 答案产物**版本留痕**（可 bisect 定位回归） |

**前端门禁（改了 `frontend/` 或 `web/` 就跑这一组）**：

| 命令 | 管什么 |
| --- | --- |
| `node frontend/tools/check-core.cjs` | 逻辑层等价性（core vs 冻结基线，**213,972 项**） |
| `node frontend/tools/ssr-smoke.mjs` | 6 视图 SSR 组件冒烟（**31 项**） |
| `node web/test_render.js` | 逐篇渲染（**26,742 篇 / 522,242 项**） |
| `node web/verify_views.js --n 3000` | 前端 JS ↔ Python 引擎逐字段（**43,459 项**） |
| `node web/test_ui.js` | 前端功能（含检索标尺、页面审计、**147 项**） |
| `python web/test_api.py` | 服务端接口（**176 项**） |
| `python web/test_e2e.py` | **端到端回归集**（真实问句 + 失败场景 + 多轮上下文 + 流式，**37 项**；会话/快照/研究库全隔离，可重复跑） |

> 构建顺序：**先 `node frontend/tools/build-all.mjs`（Vite 出页面 → Python 出数据）**，
> 顺序反了数据会被 Vite 的 `emptyOutDir` 清掉。改了 `web/*.js` 转发文件没用 —— 逻辑真源在 `frontend/src/core/`。

> **铁律**：**先证真值口径没错，再改引擎**（第 12 轮有 3 处「缺陷」其实是真值自身错）。

---

## 四、新增工具（2026-10-05，朋友对照驱动）

| 工具 | 作用 | 零回归？ |
| --- | --- | --- |
| `tools/corpus_manifest.py` | **语料来源冻结**：相对路径 + SHA256 + 条数；`--verify` 报缺失/多出/哈希变 | ✅ 只读 |
| `tools/uncertainty_report.py` | **可存疑清单**：覆写字/空片/异读翻转平仄的篇数 | ✅ 只读 |
| `tools/snapshot_answers.py` | **答案版本化** + 逐版差异（`--diff`） | ✅ 旁路 |
| `solve/answer_reason.py` | **拒答理由八态**（附加字段 `reason`）+ `reason_from_status()` 与 `answer_verify` 五态对齐 | ✅ 只读结果 |
| `tools/fixture_gate.py` | **小语料 fixture 门禁**：CI 无语料也能跑「检索 ↔ 独立 SQL」端到端（`tests/fixture/corpus_mini.db`） | ✅ 只读 |
| `tools/cipai_clean.py` | **词牌白名单**派生数据（频次门槛，只读；不改 corpus.db） | ✅ 只读 |

## 五、本轮修掉的一个真缺陷：**「题名当词原文」**

- **症状**（朋友实测截图）：输入**题名**「蝶恋花·清明同诸子集原白斋中」，系统把它当**词正文**检索 → 答非所问。
- **铁证**：「清明同诸子集原白斋中」在**正文**里命中 **0**，在 **title** 里命中 **1**（清·陈维崧）。
- **修复**（两处，都在问答层，**不动交付链**）：
  1. `retrieve.py`：`QuerySpec` 新增 `title_any`；识别「**词牌·题名**」写法；
  2. `retrieve.py` `rescue_title()`：**裸题名**（不带词牌）若「词面在 title 命中、正文 0 命中」→ 提升为**题名条件**。
- **效果**：裸题名「清明同诸子集原白斋中」→ 题名=…，命中 1 篇（陈维崧）；「寄怀阿嫂」→ 命中 2 篇（费墨娟）。
- **不误伤**：常见词「相思/落花/东风/明月」因**正文里确有其句**，仍走词面（语义排序）。
- **零回归**：双集哈希逐字节不变（`BF863368…` / `ACEF8B15…`）。

---

## 六、口径要点（与任务书原文分歧处，**以实测为准**）

1. 汉字 = 基本区 + **CJK 扩展 A**；占位符 □○■ 不计。
2. 句末点 = **`。？！`**（任务书写「只按。切」，**错**）。
3. 舍入 = **Python round（银行家）**（15/48=31.25→31.2）。
4. 派生量：篇内用**未舍入**相减；顶层差值用**舍入后显示值**相减。
5. C4 并列：比例相同按 **丙＞乙＞甲** 倒序（任务书写「甲乙丙」，**错**）。
6. 覆写表：长→cháng、别→biè、绝→仄（**不可推广「入声归仄」**）。
