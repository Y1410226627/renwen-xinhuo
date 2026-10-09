# data/cipu —— 词谱对照数据（功能 9）

> **参照来源：搜韵公开转写（未核原书）**。本目录数据**不是**《钦定词谱》原书影像核验的产物，
> 请勿在任何界面、文档、汇报中写成"原书核验"。

## 文件

| 文件 | 内容 | SHA256 |
| --- | --- | --- |
| `normalized-rules.json` | **144 体**规范：每体含例词句数组（`normalized_sentences`）、逐句平仄规则（`normalized_rules`，`tones` 只含 `中/平/仄`，`ending` 为句尾标记）、来源定位 | `0852477f1ec4c0b0…` |
| `tune-registry.json` | 词牌注册表：20 个词牌的 canonical 名、别名、体数、来源链接 | `bf8a49ee6e4b3dd8…` |
| `manifest.json` | 上游取数清单（逐文件 URL / SHA256 / 许可 / 获取日期） | `8200dcfabbf934bb…` |
| `LICENSE-couyun.txt` | 上游 MIT 许可全文（`Copyright (c) 2026 hulbji`） | `a22fdea1d0af3ad9…` |

（完整哈希见 `THIRD_PARTY.md` 与 `manifest.json`。）

## 上游与许可

- 来源仓库：`https://github.com/hulbji/couyun`（「凑韵·诗词格律检测工具」，**MIT License**）
- 固定版本：commit `1744e87f850c2205bc231bfdd858256036c0e4db`
- 底本的底本：搜韵（`sou-yun.cn`）公开转写页面——**未核原书影像**（上游与本项目均如实声明）
- 我方仅**原样分发**上述数据文件，未做改动；读取与拆句逻辑在 `solve/cipu.py`

## 拆句口径（重要，勿踩）

原始 `ci_sep` 用**全角空格**把多个句子压进同一个数组元素（如 `"巫山高　巫山低"`），
**不能直接当句数组**。正确口径（上游核验文档 + 我方门禁 `web/test_cipu.py` 双重验证）：

- 例词：按**空白边界**拆；
- 规则：按**连续 `中/平/仄` + 句尾标记**拆（标记集：`韵 平韵 仄韵 换韵 换平韵 换仄韵 叠 叶 换叶 句 读`）。

本目录的 `normalized-rules.json` 是上游**已按此口径拆好**的成果（我方抽验 144/144 体句数齐全、
`tones` 长度与例词汉字数一致）。
