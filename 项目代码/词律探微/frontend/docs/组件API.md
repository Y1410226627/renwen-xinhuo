# 组件 API 文档（自动生成）

> 本文件由 `frontend/tools/gen-docs.mjs` **从组件源码自动抽取**，请勿手改。
> 改动组件后运行 `npm run docs`（或 `npm run docs:check` 校验）重新生成。

共 6 个组件。

---

## AppShell

**文件**：`src/components/AppShell.vue`　·　**用途**：应用外壳（五个视图共用）：顶部导航、主题按钮、页脚

### props

| 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `active` | `String` | `''` | — |
| `stamp` | `String` | `''` | 页面生成时间探针 |
| `dataNote` | `String` | `'data/corpus.db'` | — |
| `dataN` | `Number` | `null` | — |
| `online` | `Boolean` | `false` | true = 走本地服务（链接指向服务根） |

### emits

（无）

### slots

`default`

---

## AskView

**文件**：`src/views/AskView.vue`　·　**用途**：「声情问答」视图（在线，走 /api/

### props

（无）

### emits

（无）

### slots

（无）

---

## GraphView

**文件**：`src/views/GraphView.vue`　·　**用途**：「知识图谱」视图：清代词人 ↔ 词牌 二部图

### props

（无）

### emits

（无）

### slots

（无）

---

## IndexView

**文件**：`src/views/IndexView.vue`　·　**用途**：「总览」视图：项目一句话 + 六个入口卡 + 三道锁与复现命令

### props

| 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `corpusN` | `Number` | `58852` | — |
| `qingN` | `Number` | `26742` | — |
| `rulesV` | `String` | `'5.0'` | — |
| `gateCount` | `Number` | `171` | — |
| `root` | `String` | `'/'` | — |
| `stamp` | `String` | `''` | — |
| `dataNote` | `String` | `'data/corpus.db'` | — |
| `online` | `Boolean` | `false` | — |

### emits

（无）

### slots

（无）

---

## ParseView

**文件**：`src/views/ParseView.vue`　·　**用途**：「逐字解析 + 多条件检索」视图（同一组件服务两页）

### props

| 名称 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `mode` | `String` | `'offline'` | — |

### emits

（无）

### slots

（无）

---

## ReviewView

**文件**：`src/views/ReviewView.vue`　·　**用途**：「校订队列」视图（标注闭环）

### props

（无）

### emits

（无）

### slots

（无）

---

