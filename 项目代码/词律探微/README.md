# 词律探微 —— 清代词律声情智能研究助手

> 把清代（及宋元）词作的**声律**做成**可复算的数字**，用检索端**证据与原文**，大模型只负责**说得通顺**。
> **一句口令**：数字归引擎、文料归检索、说法归生成、出处归引用。

## 30 秒上手

```bash
# ① 只想看效果（不装任何东西）：双击离线自包含页面
data/vue/index.html

# ② 想用问答与在线检索（仅需 Python ≥ 3.10 标准库）
python web/serve.py            # 默认 127.0.0.1:8000，自动开浏览器
```

- 问答页 `http://127.0.0.1:8000/` ｜ 在线检索 `/browse.html` ｜ 研究库 `/research.html`
- 大模型**可选**：不设密钥也能用（数字全由本地引擎给）；设 `ZAI_API_KEY` / `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` 之一即可。

## 先读哪一份

| 你是… | 读这份 | 给你什么 |
| --- | --- | --- |
| **评委 / 首次体验** | [`使用说明.md`](使用说明.md) | 三种用法、页面导航、语言构成、研究库 |
| **接手改代码** | [`AGENTS.md`](AGENTS.md) | 最短理解路径、代码地图、改完跑什么 |
| **动手维护** | [`CONTRIBUTING.md`](CONTRIBUTING.md) | 五步流程、门禁清单、六条红线、三条链边界 |
| **要部署** | [`部署方案.md`](部署方案.md) | Windows / 信创 Linux 选型、nginx + systemd、适配清单 |
| **想核验数字** | [`项目现状说明书.md`](项目现状说明书.md) | 能力边界、门禁现值、缺陷与风险 |

## 改完先跑什么

```bash
python tools/check_all.py --fast   # 10–20 秒：交付答案哈希 + 自检
python tools/check_all.py          # 全档：另含双集零回归 / 服务端 / 逻辑层 / 逐题复核
```

> 三条链**物理隔离**：`solve/solver.py` 只导入 `corpus`/`pronounce`/`prosody`，
> **不导入** `ask`/`retrieve` —— 改问答层与前端**不可能**影响交付答案（`DECISIONS.md` D07）。
