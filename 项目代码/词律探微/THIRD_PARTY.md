# THIRD_PARTY.md —— 第三方数据、代码与许可

本文件登记项目内**随仓分发**的第三方数据与代码，以及它们的来源、许可与校验值。
（项目自定义代码一律在本仓演进，不在此表。）

---

## 1. 词谱对照数据（功能 9 使用）

| 项 | 内容 |
| --- | --- |
| 上游仓库 | <https://github.com/hulbji/couyun>（「凑韵·诗词格律检测工具」） |
| 固定版本 | commit `1744e87f850c2205bc231bfdd858256036c0e4db`（2026-10-04 取数） |
| 许可 | **MIT License**，`Copyright (c) 2026 hulbji`（全文见 `data/cipu/LICENSE-couyun.txt`） |
| 分发文件 | `data/cipu/normalized-rules.json`（144 体规范）、`data/cipu/tune-registry.json`（20 词牌注册表）、`data/cipu/manifest.json`（上游取数清单）、`data/cipu/LICENSE-couyun.txt` |
| SHA256 | `normalized-rules.json` = `0852477f1ec4c0b0cc24d79fa98489abd637d6517c0676efb779a8468c93aab0`<br>`tune-registry.json` = `bf8a49ee6e4b3dd8eebb8ac318676231ba083b819631933df1605300d3dcfbb8`<br>`manifest.json` = `8200dcfabbf934bb917c1a8c9310121f0a28d1e87bac6c3effea50330989aea0`<br>`LICENSE-couyun.txt` = `a22fdea1d0af3ad9385c4e642aa1898f64053349b39fa276b37fb2eb75e595d2` |
| 底本说明 | 上游数据系**搜韵（sou-yun.cn）公开转写**的整理，**未核对原书影像**。任何界面与文档一律注明「参照来源：搜韵公开转写（未核原书）」，**严禁**写成「钦定词谱原书核验」。 |

> 我方**原样分发**，未修改上述 JSON 文件；读取、拆句校验与对照逻辑在 `solve/cipu.py`，
> 数据完整性门禁在 `web/test_cipu.py`（144 体逐条校验 + 「直接拿 `ci_sep` 当句数组必错」的反向断言）。

---

## 2. 语料（只读引用，不随本仓分发）

| 项 | 内容 |
| --- | --- |
| `poetry-source`（清词） | 本项目仅**读取**，不入仓；来源清单与逐文件 SHA256 见 `data/corpus_manifest.json`（`tools/corpus_manifest.py --verify` 可复验） |
| `chinese-poetry`（宋词/元曲） | 同上 |

> 语料库 `data/corpus.db` 由 `build_corpus.py` 从上述数据源构建，**只读使用**，任何新功能不得写它。

---

## 3. 词谱数据的上游链（如实披露）

```
钦定词谱 / 龙榆生词谱（原书）
        ↓ （公开转写，未核原书影像）
搜韵 sou-yun.cn 公开页面
        ↓ （整理为 JSON，MIT 许可）
hulbji/couyun @1744e87…
        ↓ （原样取数，记录 SHA256）
本项目 data/cipu/
```

这一段链路会原样出现在 `solve/cipu.py` 的返回体 `source_note` 字段与前端界面上。
