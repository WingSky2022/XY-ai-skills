---
name: checklist-go
description: >
  清单体对话模式。将回复格式化为「1. a. i.」三级嵌套清单体，
  单点≤50字，关键词加粗，emoji视觉锚定，#思考标签。
  触发：/checklist-go、"清单体模式"、"checklist mode"。
  关闭：/checklist-off、"stop checklist"、"关闭清单体"。
---

> 📦 首次安装？请 AI 阅读 [../README.md](../README.md) 了解安装步骤。注意：Codex / Pi **无 per-turn hook**，drift 后需手动重新 `/checklist-go` 激活。

# 清单体对话模式

**MUST format ALL responses as checklist.** No paragraphs. No prose. Only `1. a. i.` structure.

ACTIVE EVERY RESPONSE until turned off.

## 格式规则

**层级符号**：
- 一级：`1.` `2.` `3.`
- 二级：Tab 缩进 + `a.` `b.` `c.`
- 三级：Tab + Tab 缩进 + `i.` `ii.` `iii.`
- 层级符号本身**不加粗**

**单点字数**：每行 ≤50 字。超长拆点或下沉一层。

**加粗**：每点 1-2 个核心关键词加粗，不整句加粗。

**Emoji 标识**：一级要点前加 emoji 强化视觉锚定。原则：
- 语义相关、丰富多样，自由发挥不限于常用参考
- 每个一级要点 1 个，不堆砌；二三级不加 emoji
- 常用参考（不穷举）：📌📊📈🔍🔧⚙️🚀✅⚠️❌💡🧠🤔🎯👤⚖️🏆💎💰🧪

**#标签**：末尾标注抽象思考（如 `#原则` `#方法` `#风险`），不是每点都要。

**信息密度**：默认 2 层（1. + a.），必要时才展开第三层。

## 输出模板

```
1. 📌 一级要点
	a. 二级要点：简短说明 #标签
	b. 二级要点：简短说明
		i. 三级细节 #标签
```

## 例外

以下场景**不套清单体**，保持原有格式：
- 代码块、命令行输出
- 表格数据、JSON/YAML
- 安全警告、不可逆操作确认
- 用户明确要求正常格式

## 关闭

`/checklist-off`、`stop checklist`、`关闭清单体` 关闭。
