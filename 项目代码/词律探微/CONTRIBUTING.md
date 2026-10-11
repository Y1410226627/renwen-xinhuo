# 维护手册（CONTRIBUTING）

> 给**下一位改这个项目的人**（人或 AI 协作者）。
> 目标：**改得对、改得稳、改了不闯祸**。
> 先读 `AGENTS.md`（最短理解路径），再读本文件（动手流程），最后再动代码。

---

## 0. 一句话总纲

> **数字归引擎、文料归检索、说法归生成、出处归引用。**
>
> 三条链**物理隔离**：交付链（`solver.py` / `official.py`）**不导入**问答链
> （`ask.py` / `retrieve.py`）→ **改问答层不可能动交付答案**（这是结构性保证，不是巧合）。

---

## 1. 五分钟上手

```bash
# 1) 解释器（项目自带一套隔离环境；用绝对路径最稳）
PY="C:/Users/湮貉/.workbuddy-ai/binaries/python/envs/default/Scripts/python.exe"

# 2) 改完随手验（10–20 秒；pre-commit 钩子跑的就是这一档）
"$PY" tools/check_all.py --fast

# 3) 提交前 / 答辩前 / CI（2–4 分钟，跑齐五道门禁）
"$PY" tools/check_all.py

# 4) 只看要跑哪些门禁
"$PY" tools/check_all.py --list
```

> 改前端（`frontend/` 或 `web/`）另跑：`node frontend/tools/check-core.cjs`。
> 改 `web/*.js` 转发文件**没用**——逻辑真源在 `frontend/src/core/`。

---

## 2. 改一处代码的标准流程（五步，一步都别省）

| 步骤 | 动作 | 为什么 |
| --- | --- | --- |
| ① 定位 | 判断改动落在**哪条链**：交付链 / 问答链 / 前端 | 决定「该不该影响交付答案」 |
| ② 预判 | 写下「我**预期**这次改动会不会动 `answers_700` SHA256」 | 事后核对，防「以为不会动」 |
| ③ 改 | 小步改，一次只动一个关注点 | 便于 bisect 定位回归 |
| ④ 验 | `check_all.py --fast`（改问答层）／全档（改交付链） | 门禁是唯一真相 |
| ⑤ 记 | 写 `CHANGELOG.md`；有口径/取舍 → 写 `DECISIONS.md`（新 `Dxx` 编号不复用） | 防后人重复试错 |

> **铁律**：**先证真值口径没错，再改引擎**。
> 第 12 轮有 3 处「缺陷」其实是**真值自身错**（∀ 漏并集、占比分子分母不同域）——
> 若当时有 `DECISIONS.md` 就不会返工。

---

## 3. 门禁清单（什么管什么）

### 3.1 一键入口 `tools/check_all.py`

| 档位 | 含哪些门禁 | 何时用 |
| --- | --- | --- |
| `--fast` | 交付答案 SHA256 + `selftest` | 改完随手验 / pre-commit（10–20 秒） |
| 全档 | fast + `test_api` + `check-core` + `verify_1000` | 提交前 / 答辩前 / CI（2–4 分钟） |

失败**即停**；缺环境**显式 SKIP**（不算通过）。退出码：`0` 通过 / `1` 有失败 / `2` 环境不满足。

### 3.2 五道关键门禁（各自管什么）

| 门禁 | 命令 | 管什么 | 当前值 |
| --- | --- | --- | --- |
| **A 零回归锚点** | （内建于 `check_all.py`） | `answers_700.jsonl` SHA256 恒等 | `bf863368…f7d1e` |
| **B 自检** | `python solve/selftest.py` | 结构 / 安全 / 说法层断言 | **270 项 0 失败** |
| **C 服务端** | `python web/test_api.py` | `/api/*` 接口（不起服务、不联网） | **171 项** |
| **D 前端逻辑层** | `node frontend/tools/check-core.cjs` | core 真源 vs 冻结基线（全库逐字节） | **213,972 项** |
| **E 逐题复核** | `python tools/verify_1000.py` | 1000 题答非所问 + 准确性 | **1000 题** |

### 3.3 更多门禁（按需）

| 命令 | 管什么 |
| --- | --- |
| `python reproduce.py --skip-build --quick` | 一键复现基线（**13/15**，2 项 FAIL 属 D14 暂缓族，**不是缺陷、不得为凑数而改**） |
| `python tools/regress.py --questions <题面> --gold <答案> --tag 公开` | 双集零回归（逐字节哈希） |
| `node frontend/tools/ssr-smoke.mjs` | 6 视图 SSR 组件冒烟（31 项） |
| `python web/test_e2e.py` | 端到端回归集（37 项；会话 / 快照 / 研究库全隔离） |
| `python tools/fixture_gate.py` | 小语料 fixture 门禁（CI 无语料也能跑） |

---

## 4. 红线（**碰了就是事故**）

1. **`data/corpus.db` 绝不改**。任何「派生索引」必须**只读派生**，写到别处
   （见 `tools/build_indexes.py`：H3 曾因往 corpus.db 写而被判违规）。
2. **`answers_700.jsonl` SHA256 必须恒等** `bf863368ffaf85d89ddd1aae28b334be5a0fdfd532a365fa9f8110a747ff7d1e`。
   要改这个锚点，**必须**同时说明「交付答案为何应当变化」并同步改
   `tools/check_all.py` 的 `GOLD_SHA256`。
3. **交付链不导入问答链**。`solver.py` / `official.py` 出现 `import ask/retrieve` 即破坏隔离。
4. **`「」` 只留给语料原文**。非原文引文用普通引号（`「」` 在本项目是**模板严格通道**，
   引文必须为语料原文整句，误用会触发引文护栏）。
5. **门禁 FAIL ≠ 门禁错**。剩余 FAIL 若属 `DECISIONS.md` **D14（⏸ 已暂缓）** 族，
   是「暂缓即结论」，**不擅动任一侧**。
6. **历史记录不得回改**：旧 changelog / 逐轮终值 / `DECISIONS` 旧条目，只追加不修改。

---

## 5. 三条链的边界（该改哪儿）

| 你想改… | 该动 | **不该**动 | 预期影响交付答案？ |
| --- | --- | --- | --- |
| 声律计算 / 官方题型 | `solve/prosody.py`、`solver.py`、`official.py` | — | **会**（要重跑全档 + 更新锚点说明） |
| 问答检索 / 语义 | `solve/ask.py`、`retrieve.py`、`similar_ask.py`、`guard.py` | `solver.py` | **不会**（结构性隔离） |
| 前端展示 | `frontend/src/core/` | `web/*.js`（薄转发） | **不会** |
| 后端接口 | `web/serve.py` | — | **不会** |
| 词谱 / 研究库 | `solve/cipu.py`、`research.py` | `corpus.db` | **不会** |

---

## 6. 提交约定

- **提交粒度**：一个关注点一次提交（便于 bisect）。
- **提交信息**：`<type>(<scope>): <摘要>` —— `type` ∈
  `feat` / `fix` / `docs` / `chore` / `refactor` / `test`；
  `scope` 用链名（`语义问答` / `交付链` / `前端` / `门禁`…）。
- **pre-commit 钩子**：已装 `.githooks/pre-commit`（跑 `check_all.py --fast`）。
  首次克隆后执行一次：
  ```bash
  git config core.hooksPath .githooks
  ```
  紧急跳过用 `git commit --no-verify`（**仅限确知无害时**）。
- **大文件**：`data/corpus.db`、`data/vector/*.index`、`*_meta.jsonl` 走 **Git LFS**（见 `.gitattributes`）。
  推送若被 LFS 卡住：`GIT_LFS_SKIP_PUSH=1 git push`。

---

## 7. 双仓库同步（主开发版 ↔ 开源版）

- **主开发版**：`D:\桌面\人文薪火\项目代码\词律探微`（本仓，含全部历史产物与工具）。
- **开源版**：`D:\桌面\人文薪火-开源版`（→ GitHub `Y1410226627/renwen-xinhuo`）。
- **纪律**：改完主版 → **逐字节同步**到开源版对应路径（`项目代码/词律探微/…`）→ 提交推送 →
  用 `git ls-remote origin refs/heads/main` 复核远端哈希。

---

## 8. 常见坑（前人踩过，别再踩）

| 坑 | 症状 | 正解 |
| --- | --- | --- |
| 构建顺序反了 | 数据被 Vite 的 `emptyOutDir` 清掉 | **先** `node frontend/tools/build-all.mjs`（Vite 出页面 → Python 出数据） |
| 改了 `web/*.js` | 没生效 | 逻辑真源在 `frontend/src/core/`，`web/*.js` 只是薄转发 |
| 向量索引重建中断 | `vector_index.available()=False` → 语义问答降级 | 重跑 `python build_vector_index.py --only poems`（**增量续跑**，进度已持久化） |
| 检查计数过期 | 文档里「N 项」长期不符 | `doc_check` 不校验「N 项」；改门禁后**手工**校正现状数字 |
| 为凑数改暂缓项 | 人为「修好」D14 族 FAIL | **不得**——「暂缓即结论」 |

---

## 9. 相关文档地图

| 文件 | 给你什么 |
| --- | --- |
| `AGENTS.md` | 接手入口：先读哪四份、代码地图、改完跑什么 |
| `DECISIONS.md` | 决策表（已接受 / 已拒绝 / 已暂缓 + 为什么没选另一种改法），编号 `Dxx` |
| `GLOSSARY.md` | 术语与**措辞禁忌**（哪些话我们不该说） |
| `外部审查处置表.md` | 外部审查逐项处置与状态 |
| `CHANGELOG.md` | 每次对外可见的变化 |
| `VERSION` | 当前版本号 |
| `solve/README.md` | 实现与自检总纲（每条命令怎么复现、口径演变、踩过的坑） |
| `reproduce.py` | 一键复现（15 步） |

---

## 10. 求助信号（什么时候该停下来问）

- 门禁 FAIL 且**说不出**为什么 → 先查 `DECISIONS.md` 有没有同族结论，再问。
- 要改 `corpus.db` 或 `answers_700.jsonl` 锚点 → **必须**先确认「为什么应当变」。
- 改动横跨**多条链** → 拆开，一次只动一条链，分别验。
