# 变更日志（CHANGELOG）

> 本文件记录**每次对外可见的变化**（新增能力 / 修复缺陷 / 口径变更 / 工程机制）。
> 遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 精神，版本号见根目录 `VERSION`。
>
> **本项目特殊纪律**：任何改动**先证零回归**再合入。标注 ✅ 的条目均已通过：
> - `answers_700.jsonl` SHA256 = `bf863368ffaf85d89ddd1aae28b334be5a0fdfd532a365fa9f8110a747ff7d1e`（交付答案逐字节不变）
> - `python tools/check_all.py`（统一门禁）全绿
>
> 条目日期为**实际开发日期**（非发布日）。

---

## [未发布]

### 安全边界、路由默认与交付说明修正（2026-10-16 · 待门禁验证）

- **研究库写接口加认证**：远程监听必须设置强随机 Bearer 令牌；远程写入仅接受同机 HTTPS 反向代理，拒绝非回环直连伪造转发头。
- **读音晋升门禁补强**：`--promote` 必须同时提供第二套题面与答案，避免仅通过公开集就替换交付覆写表。
- **规划路默认统一**：启动脚本与服务端默认均为 `rule`；`plan` 保持显式启用，符合 D67 的 No-Go 决策。
- **向量端点环境配置补齐**：`vector_index.py` 读取 `LVC_EMBED_URL`、`LVC_EMBED_KEY` 与 `LVC_EMBED_TIMEOUT`；同步校正 Markdown 部署和参赛说明。
- **部署示例**：反向代理转发原始 `Host`，避免浏览器写请求被同源校验误拒。
- **验证状态**：本次未运行测试套件或统一门禁；前端产物已在本轮改动过程中重建。开源版镜像尚未同步，见外部交接清单。

### 文档 · 评估与现状导出（2026-10-14）

- **新增 `项目现状说明书.md`**：面向技术评审的**完整现状导出**——设计思路、三条链架构、
  运行流程（安装/配置/启动）、逐目录文件作用、门禁体系、能力边界、优缺点、**缺陷与风险**、
  与参赛指南对照、**部署选型（Windows Server vs 信创 Linux）**、以及**请教企业导师的 6 个问题**。
- **新增 `优化评估报告_20261014.md`**：对「值得大刀阔斧改的地方」做 Go/No-Go 评估
  （唯一 Go：题名/词牌覆盖表接入；其余 No-Go 并附理由）。
- **`DECISIONS.md` D62**：更正 D61 对「审核表 pid 与语料库不一致」的**误判**——实测 100% 对齐。
- **`DECISIONS.md` D63**：**主动暂缓**题名规范化接入引擎。理由为三条实测：
  ① 1000 题**不按词牌筛选** → 门禁测不出好坏（无安全网）；
  ② 块内 `title`/`cipai` 进**护栏引文白名单**（`evidence.py`）→ 不是纯展示层；
  ③ 修正表为**大模型判定、未经人工核验**。列出 4 条前置条件（专用验收 / 专家抽检 /
  只改展示字段且可开关 / 全档门禁 + 双集回归）。
- **`DECISIONS.md` D64**：**对外表述口径统一**（纯文字，零行为变更）——全仓 55 处表述
  改为中性、自主的说法，使对外说明只呈现本项目自身的推导与依据。

### 声律双口径并存 · 部署方案 · 门禁补全（2026-10-13 · 零回归）

详见 `DECISIONS.md` **D57—D61**。

- **新增 · 声律双口径并存**（`solve/tone_policy.py`）：**评测口径**（普通话四声，本系统默认、
  题库口径）与**历史口径**（《广韵》中古平仄）**并列展示、互不覆盖**。
  逐字位给 `{mandarin, historical, status, guangyun}`，`status` 四态
  `match / differ / hist_missing / hist_ambiguous`；差异**如实并列，不判定谁对**。
  · `GET /api/tone_policy?pid=`（**新路径**，不动 `/api/parse`）；
  · CLI `python solve/tone_policy.py --pid <pid>`；
  · 研究库第 9 分区「**口径对照**」；
  · **默认口径一字不改**（`corpus.db` 的 `pz` 列与 `pronounce/prosody` 原样不动）→ 交付答案零回归；
  · 广韵未收录 / 多候选**如实标注，不用普通话顶替**。
- **新增 · 部署方案**（`部署方案.md` + `deploy/`）：三种形态（单机 / 局域网 / **主从式**）；
  端口与路径规划；nginx / systemd / Windows 任务计划配置；**信创（openEuler / 麒麟）适配清单 6 项**
  （Python 版本 / SQLite FTS5 / 中文字体 / faiss 降级 / 防火墙 / 编码）；
  可访问性验收清单 8 条；**与另一个应用共存的接口边界**（只走 HTTP，各用各的端口与数据）。
- **门禁补全（真缺口）**：`tools/check_all.py` 新增 `gate_regress`，**全档内置**（`--only regress`
  可单跑，约 14 秒）——跑**公开 700 题 + 保密 300 题两套**回归。此前只校 `answers_700` 的 SHA256，
  **第二套没进门禁，零回归只防了一半**；现在**两套都逐字节一致才算过**（防卫面 1/2 → 2/2）。
  期望哈希只从 `solve/data/golden_sha.json` 读一处；题库定位不到**显式 SKIP**。
- **修复 · 4 个真缺陷**（D60）：① `ResearchView` 新分区切页不加载；② `dependency_state`
  双空误报「可能已陈旧」；③ `FAILURE_CODES` 里 `too_many_claims` 有码无出处；
  ④ `_arg_norm` 校验弱于生成侧（API 直写可绕过 `bridge`/`gaps` 纪律）。
- **文档校正**：`selftest` 270 → **294**、`test_api` 171 → **176**（AGENTS / CONTRIBUTING /
  solve/README / 作品报告 / 使用说明 / 外部审查处置表 / 接口文档，共 13 处）。
- **自检**：`selftest` **270 → 294**（新增双口径 4 项）；`test_api` **171 → 176**。
- **零回归铁证**：`answers_700.jsonl` SHA256 `bf863368…` 逐字节不变；
  **regress 双集全通过**；`doc_check` 9/9；`check-core` 213,972/0；`ssr-smoke` 31/0；
  `check-types` 0 错误；`test_render` 522,242/0；`verify_views` 43,459/0；`test_ui` 147/0。
- **已知问题（暂缓）**：`data/title_review.jsonl`（题名审核成果）的 pid 命名空间与
  `corpus.db` 不一致，**暂不能接入检索侧**；后续按（author,title,首句）重新对齐（见 D61）。

### 能力补全 · 第二批：六项（2026-10-13 · 零回归）

> 为把「论证辅助 / 说法层 / 研究库」三处做扎实，本轮补齐六项能力。详见 `DECISIONS.md` **D56**。

- **新增 · 可编辑论证稿 + 修订链**（`solve/research.py` 新表 `argument_drafts` / `argument_revisions`）：
  新建（一篇稿）→ 编辑（**追加**修订，乐观锁）→ 撤回（标记，行保留）→ **版本链**（旧版永不覆盖）；
  **Markdown / Word 导出**（Word 为**手写最小 OOXML**，纯标准库 zipfile，5 个 part，中文与码点不丢）；
  每次动作写**决策事件**（`kind='argument'`）。配套 **4 个写接口 + 3 个读接口**（`web/serve.py`）
  与**研究库第 8 分区「论证稿」**（`ResearchView.vue`：列表 / 查看 / 编辑 / 导出 / 撤回）。
- **新增 · 锚点机制**（`solve/gen.py` `expand_anchors`）：正文写 `@facts` / `@evidence`，
  由**程序**把冻结的事实/证据填回——模型不逐字复述固定内容，**转述出错**从根上消失。
  **无锚点时逐字节不变**。
- **新增 · 输出失败码**（`solve/gen.py` `FAILURE_CODES` **20 个** + `classify_failures`）：
  `problems` 仍是人话（界面用），`codes` 是**机器可判的枚举**（审计/统计用）；说法层各返回体均带 `codes`。
- **新增 · 逐依赖项实时状态**（`solve/snapshot.py` `dependency_state`）：除快照级 `stale` 外，
  再给 **corpus / overrides / golden / research / vector** 五项的「快照值 / 当前值 / 变没变 / 说明」；
  `capture()` 起同时记录 research+vector 指纹。取不到当前值 → `unknown`（**按可能已陈旧处理**）。
- **核实 · CSV 公式注入防护**：`frontend/src/core/ui.js` 的 `csvCell()` **早已**对
  `^[=+@]` / `^\t\r` / `^-[^0-9.]` 前缀加 `'`（与通行做法 `safe_cell` 同法）。本轮**只核实、未改动**。
- **文档 · 核验深度分层**：`GLOSSARY.md` 新增「六、核验深度分层」（转录一致 / 来源准入 / 底本校勘 /
  语境裁定 / 单篇年代 / 四层分离，逐条 `_Avoid_`）。
- **自检**：`solve/selftest.py` **278 → 290 项**；`web/test_api.py` **171 → 175 项**。
- **零回归铁证**：`answers_700.jsonl` SHA256 `bf863368…` 逐字节不变；
  `check-core` 213,972/0 · `ssr-smoke` 31/0 · `check-types` 0 错误 · `test_render` 522,242/0 ·
  `verify_views` 43,459/0 · `test_ui` 147/0。

### 说法层与论证能力加固（2026-10-13 · 零回归）

> 背景：自查发现两处真问题——① 论证辅助只切换任务提示、无独立论证稿实体；
> ② 护栏的「数字白名单」偏宽，**数字出现不等于它支持当前论断**。本轮逐条加固。
> **只改问答层，交付链零改动。** 详见 `DECISIONS.md` **D55**。

- **新增 · 结构化论证稿**（`solve/gen.py`）：`argument=True` 时先试**结构化 JSON 论证稿**
  （`thesis / claims[{claim, bridge, assessment, alternatives, gaps, evidence}] / limitations`），
  逐项校验：`bridge` **必填**（形式→解释的桥梁）、`assessment` ∈
  `supported|mixed|insufficient|unresolved`、`insufficient/unresolved` 必须给 `gaps`、
  `[E#]` 必须真实存在。**任一不过即整稿丢弃**，回落既有散文四层草稿（逐字未改）→ 再不过回落模板。
  新增 `parse_argument` / `render_argument` / `produce_argument`；CLI `gen.py --argument --show-struct`。
  ★ **`narrate` 路径完全不受影响**。
- **新增 · 数字可追溯性审计**（`solve/guard.py` `audit_number_traceability`）：
  逐行把每个数字分级为 `cited`（可追到本行 `[E#]`，强）/ `global`（仅凭全库合法值，**弱**）/
  `allowed` / `none`，并列出只拿到 `global` 级的行。**`check_numbers` 判定完全不变**（纯附加）。
  —— 直接回应「数字出现 ≠ 支持当前论断」这一真问题。
- **修复 · 相似问答静默降级成错误答案**（`solve/similar_ask.py`）：向量无返回时旧行为回落主链 →
  把「与《X》类似的词」**当成「定位 X」**答（实测嵌入端点瞬时不可达时复现）。
  现改为**接管并如实说明「语义检索当前未返回结果」**（列可能原因 + 建议改结构化条件），**不答非所问**。
- **自检**：`solve/selftest.py` **270 → 278 项**（新增结构化论证 6 项 + 审计分级 1 项 + 相似问答诚实分支 1 项）；
  相似问答两项改为**环境感知**（不再因嵌入端点瞬时不可达而误报 FAIL）。
- **文档**：`GLOSSARY.md` 新增「五、论证与判断的分层」（主张/桥梁/评估态/替代解释/缺证/数字可追溯性，
  含 `_Avoid_` 禁忌）；`DECISIONS.md` 新增 **D55**。
- **零回归铁证**：`answers_700.jsonl` SHA256 `bf863368…` 逐字节不变；`selftest` **278/0**。
- **未做（如实记录）**：可编辑论证稿的**持久化与修订链**（外部同类实现的 `argument_revisions`）未做，属研究库层表结构变更。

### 工程机制（2026-10-11）

为「以后方便修改 / 优化 / 维护」补五个缺口（不重建已有体系）：

- **新增** `tools/check_all.py` —— **统一门禁入口**。一条命令跑齐五道门禁
  （`answers_700` SHA256 · `solve/selftest.py` · `web/test_api.py` ·
  `frontend/tools/check-core.cjs` · `tools/verify_1000.py`）；
  支持 `--fast`（SHA256 + selftest，约 10–20 秒）/ 全档 / `--list` / `--only <门禁>`。
  失败即停；缺环境**显式 SKIP**（而非静默通过）。
- **新增** 主开发版本地 git 仓库 + `.gitignore` / `.gitattributes`（**基线提交 `80cfd5f`**）。
  口径：**可再生的一律不入仓，不可再生的必须入仓**。
  大资产走 Git LFS：`data/corpus.db`、`data/vector/*.index`、`data/vector/*_meta.jsonl`。
  排除：`node_modules/`、`__pycache__/`、运行会话、本机密钥（`llm_local.json`）、历史快照。
- **新增** `VERSION` + 本 `CHANGELOG.md`（版本与变化留痕）。
- **新增** `CONTRIBUTING.md`（维护手册：改动流程 / 门禁口径 / 红线）。
- **新增** `.githooks/pre-commit`（提交前自动跑 `check_all.py --fast`，防「带病提交」）。

### 语义能力增补（2026-10-11 · 二期 ①②，零回归）

目标：让问答更接近「**只要数据里有、大模型能理解，就能答**」。

- **词面净化 · 串首语法壳剥离**（`solve/retrieve.py` `_strip_ask_prefix`）：
  在请求前缀之上继续剥**串首**「内容引导动词」（写 / 描写 / 咏 / 题 / 赋 / 记 / 吟 / 作 /
  表达 / 寄托…）与「属性壳词」（意境 / 风格 / 题材 / 格调…）。
  `写羁旅愁思` → `羁旅愁思`；`意境苍凉` → `苍凉`。
  ★ 陷阱：`咏梅 / 咏怀 / 咏史 / 题画` 等**凝固复合词**词头与动词同形，用负向前瞻白名单
  （`_FUSED_AFTER_VERB`）保护**不误剥**；剥后**剩余汉字 < 2 则回退**。
- **相似意图拓宽**（`solve/similar_ask.py` `is_similarity_ask`）：新增**显式仿照句式**触发
  （`像《X》那样` / `仿《X》` / `比照《X》` / `效仿《X》`），不再要求句中含「相似 / 类似」二字。
  修「像《声声慢》那样写愁的词」进不来。回归防线：含《》但问**形式 / 事实**
  （「《临江仙》有多少首」）**不被误吞**。
- **向量索引扩展到全量语料**（数据层，不改代码）：由「仅清词 26,742 首」→
  「全量 58,852 首（清 + 宋 + 元）」。宋 / 元的语义问法从「够不着」变「够得着」；
  因 `_vector_channel` 走 `allow=restrict` 受限检索，硬条件（如限清词）照旧收窄，
  候选宇宙变大但**不改变任何既有题的命中集合**。

### 修复

- **`tools/doc_check.py` 两处真实缺陷**（本轮工程机制自查时暴露）：
  - `ck()` 的 `detail` 传 **list**（把子进程输出尾行贴进来）时，`'：' + detail` 抛
    `TypeError` → **把「本该报 FAIL」变成「脚本崩溃」**。已统一转字符串。
  - ① 命令活性**对每条 README 命令都跑 `--help`**：但门禁脚本（`selftest.py` / `test_api.py`）
    **不支持 `--help`**，跑它等于**真跑一遍完整测试**（慢 + 有副作用），其退出码 1
    （测试部分失败，如索引重建期的暂时态）被**误判为「命令不可跑」**。
    已改为**先 `py_compile` 证「不是坏文件」**，`--help` 结果仅作参考、不影响判定
    （回归 docstring 早写明的口径「或语法编译」）。修复后 `doc_check` **9/9 通过**。
- **三重缺陷（2026-10-13 · 提交前评估实测驱动，零回归）**：三处都属「**门禁覆盖盲区里的潜伏
  bug**」——均不在交付链（`answers_700` SHA256 恒定），但都真实损害「可复现 / 可演示 / 诚实」：
  - **`tools/nl_benchmark.py` plan 模式必崩**（`NameError: mode`）：10-09「P1-17 按模式隔离字段集合」
    改造**漏改函数签名与调用点**；该模式当时只验 rule 档 20/40，plan 档**从未被门禁覆盖**。
    修：签名补 `mode='rule'` + 调用点传参。
  - **`solve/planner.py` 规划提示词永久退化**（本批最重）：`SYSTEM = system_prompt()` 在模块中部
    执行，而函数体内引用的 `_load_queryplan` **定义在其后** → 导入期 `NameError` 被 `except`
    **静默吞掉** → 提示词**在正常导入路径下永远**缺失字段说明书（3389 字符；完整版 8328）。
    LLM 只能按示例猜字段名（实测 `han_len` → `char_count`）→ plan 档 9/40 高难句规划失败。
    修：模块中部只放占位兜底，完整版**移到 `_load_queryplan` 定义之后**生成。
    **效果：plan 档 25/31 → 35/40（跳过 9 → 0；覆盖 26/31 → 39/40）。**
  - **`solve/guard.py` 护栏①跨块误伤**：`_legal_anywhere`（未引用行「全库合法值」）只收
    「除 change 外」字段 → 一篇 `change=-2.4` 使 `'2.4'` 进 `abs_only`，**连累**另一篇
    `change=+2.4` 的正当无符号写法（「篇级：…变化 2.4」）被判「数字无出处」（`test_e2e` A 组）。
    修：**非负 change 的形态计入 `_legal_anywhere`**；负 change 不补、引用行剥除逻辑不变
    （不放松口径）。**效果：`test_e2e` 36/37 → 37/37。**
  - **反例三查**（防放松）：引用行丢符号仍拦 ／ 负值正写放行 ／ 正块引用行放行——全过。
  - 详见 `DECISIONS.md` **D54**。

### 文档

- `AGENTS.md`：§一 增补第 0 项 `CONTRIBUTING.md`、第 5 项 `CHANGELOG.md`；
  §三 置顶 `tools/check_all.py` 为**一键入口**；自检计数校正 `235 → 270`。
- `solve/README.md` / `作品报告.md` / `外部审查处置表.md`：`selftest` 计数校正为 **270 项 0 失败**，
  并新增「统一门禁」行。（历史轮次报告 `自查报告/第07、08遍` 属**历史终值，不回改**。）
- **相似意图识别失效**：`is_similarity_ask` 第一道门 `if not any(w in q for w in _SIM_WORDS)`
  挡死了仿照句式 → 重构为**先判是否含《…》**，再判仿照句式或相似词。
- **词面误剥**：初版 `_LEAD_VERB_RE` 一律剥「咏」，`找几首咏梅的清词` 被剥成「梅」（单字被丢）
  → 加白名单保护 + 剩余字数下限回退。
- **STOPWORDS 与凝固复合词保护冲突**：从 STOPWORDS 移除 `咏怀 / 咏史 / 题画`（它们是凝固复合词，
  非句式残留）；只保留 `那样 / 这样 / 似的 / 一般 / 一样 / 之类 / 这种 / 那种`。

### 自检

- `solve/selftest.py`：**257 → 270 项**（新增 13 项）——
  词面净化 4 例（`写羁旅愁思`→`羁旅愁思`、`描写边塞风雪`→`边塞风雪`、`意境苍凉`→`苍凉`、
  `表达隐逸闲适`→`隐逸闲适`）、凝固复合词保护 3 例（`咏梅 / 咏怀 / 咏史` 不被误剥）、
  相似意图新增 3 例（仿照句式 → True）、回归防线 3 例（问形式 / 事实 → False）。

---

## [1.0.1] — 2026-10-11

### 修复（二期复核）

- 护栏①**变化值绕过**（数字须有出处）被绕过：变化值路径未纳入数字核验。
- **题名书名号识别失效**：`《题名》` 未正确识别为题名条件。
- **定位器并发竞态**：共享状态未隔离，并发请求下结果可能串扰。

### 自检

- `solve/selftest.py` 门禁扩至 **257 项 0 失败**。

---

## [1.0.0] — 2026-10-09

### 新增

- **向量语义检索能力**（`solve/vector_index.py` / `llm_embed.py` / `fusion.py` / `build_vector_index.py`）：
  faiss + 模型 `qwen3-vl-embedding-8b`（4096 维），RRF 名次融合。
  环境开关 `LVC_VECTOR`（默认 **开**，`=0` 关）。
- **请求量词前缀剥离**（`_strip_ask_prefix`）：「找几首 / 给我几首 / 来两首…」等请求前缀
  不再与主题词粘连污染词面。
- **主题问路由修正**：纯主题词面且字面 0 命中时 → 语义排序主导。

### 交付基线

- `answers_700.jsonl` SHA256 `bf863368…`（公开集）确立为**零回归锚点**。

---

## 早期里程碑（摘要）

- **2026-10-06** 第二轮架构重构：Query Plan 执行真源（`queryplan.py` LEAF_SCHEMA 26 字段）、
  LLM 规划器（`planner.py`）、计划执行器（`plan_exec.py` 22 算子 + `ProvDAG` 溯源）、
  会话语境（`context.py`）、RRF 融合（`fusion.py`）。
  **默认关闭、按需启用**（`LVC_PLANNER=plan`），开启后对交付答案零影响。
- **2026-10-05** 新增对照工具：语料来源冻结（`corpus_manifest.py`）、可存疑清单
  （`uncertainty_report.py`）、答案版本留痕（`snapshot_answers.py`）、拒答理由八态
  （`answer_reason.py`）、小语料 fixture 门禁（`fixture_gate.py`）。
- **2026-10-04** 修「**题名当词原文**」真缺陷：裸题名在 title 命中、正文 0 命中 → 提升为题名条件。
- **2026-10-03** 第 12 轮教训：三处「疑似缺陷」经查实为**真值自身错**（∀ 漏并集、占比分子分母不同域）。
  催生 **DECISIONS.md**（防重复试错）。
