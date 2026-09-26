# data-schema · 工作台数据 JSON 字段规范

> 工作台数据真相源。模板 `assets/workbench-template.html` 以 `__DATA_JSON__` 占位注入本 JSON。所有正文面向展示，字段命名与模板 JS 消费点一一对应。

## 顶层结构

```jsonc
{
  "$schema": "xy-capability-workbench/v1",
  "meta": { ... },            // 页面元信息
  "profile": { ... },         // 被评者画像与段位
  "dualTriangle": { ... },    // 双三角（左人类/右AI，各三尖）
  "featurePeriodic": { ... }, // Feature 周期律 L1–L5 × 四维度
  "library": { ... },         // Feature Library 与沉淀六阶段
  "iterationChains": [ ... ], // 迭代证据链
  "assets": [ ... ],          // 资产画布（六要素判级）
  "keyFindings": [ ... ]      // 关键发现（对外亮点）
}
```

## 字段明细

逐顶层键说明如下；示例取值见本仓发布说明或首次运行产物。

### meta
| 字段 | 类型 | 说明 |
|---|---|---|
| title | string | 工作台主标题（hero 大标题由此填充） |
| subtitle | string | 副标题 |
| generated | string | 生成日期 YYYY-MM-DD |
| framework | string | 框架出处（一堂双三角 + Feature 周期律 v0.8） |
| dataSources | string[] | 数据来源清单（扫描报告/门控决断/git 史） |
| audience | string | `self` 或 `external`（对外时差距细节不入台） |

### profile
| 字段 | 说明 |
|---|---|
| name / positioning | 被评者标识与一句话定位 |
| overallStage | 综合段位（如「进阶后期 → 高阶门槛」） |
| stageEvidence | 段位依据一句话 |
| featureTurningPoint | `{date, event, before, after}` 特征思维拐点（无则整组省略） |

### dualTriangle
- `left`（人类三角）与 `right`（AI三角），各含 `name / slogan / theme(orange|blue) / corners[3]`。
- corner：`key`（aesthetic/system/creativity/fundamentals/data/scene）、`name`、`position`、`original`（原图条目，保持课程原表述）、`level`（段位词）、`levelScale`（1–5 数值，渲染圆点）、`oneLiner`、`evidence[]`（证据条目）、`assets[]`（代表资产）。
- `flywheel`：`top`「人变强了，调教更强AI」/ `bottom`「有了强AI，辅助人变得更强」+ `note`。
- `soulQuestions`：`left` / `right` 两条灵魂拷问。

### featurePeriodic
- `axisNote`：轴注。
- `sceneBar`：`{title:"借假修真：场景是假，Feature 是真", items[]}`。
- `levels[]`：按 **L5→L1** 顺序（自上而下渲染）；每层 `id/name/tagline/cells/myEvidence`。
  - `cells`：L2–L4 为 `{A,B,C,D}` 四格文本；L1 为跨维度两格（如 `跨维度-模型组合 / 跨维度-参数控制`）。
  - `myEvidence[]`：`{dim, note}` —— 被评者在该层·维度的归位实证；`dim` 与格键对应（L1 用 `跨维度`）。

### library
`stages[]`（固定六阶段）、`currentNote`（当前阶段分布一句话）、`items[]`（`{name, from, date}` 已收入 Library 的 Feature）。

### iterationChains
`{name, span, commits, story}` —— 版本区间、commit 数、一段可归因的迭代叙事。

### assets
`{name, role, levels:{审美,体系,创造力,基本功,数据,场景}, highlight}` —— 判级取值：完备 / 确认 / 部分 / 线索 / 0 / 待确认。

### keyFindings
3–6 条一句话亮点（对外口径）。

## 生成纪律

1. 每条 evidence/note 必须能在扫描报告中找到出处；置信档低的标注「索引级」。
2. 受众 `external` 时：差距清单、Gate 待决断项、低分细节**不入**此 JSON。
3. 周期律 `cells` 文本保持课程原表述，不自创；`myEvidence` 才是被评者内容。
