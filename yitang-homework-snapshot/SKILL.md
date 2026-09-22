---
name: yitang-homework-snapshot
description: 一条命令把你在「一堂」的全部作业评分拉到本地：只读调用 whyai CLI，生成 JSON 数据真相源 + 自包含 HTML 工作台（评分分布 / 搜索 / 档位筛选 / 小屏卡片），可选归档作业正文全文。带内嵌环境核对（版本基线 + 登录态）与保密模式边界（零出境，不调 chat、不上传、不写服务端）。当用户要求「更新作业评分」「拉取作业学分」「刷新作业清单」「查我作业得了几分」或要生成作业评分报告时触发。
triggers:
  - 更新作业评分
  - 拉取作业学分
  - 刷新作业清单
  - 作业评分报告
  - homework snapshot
version: 1.0.0
author: WingSky
---

# 作业评分快照（yitang-homework-snapshot）

一条命令把你在「一堂」的**全部作业评分**拉到本地，产出两个文件（默认在当前目录）：

| 文件 | 角色 |
|---|---|
| `一堂作业评分清单.json` | **数据真相源**：`meta`（快照日期）+ `account`（账户口径）+ `rows[]`（逐条作业） |
| `一堂作业评分清单.html` | **自包含工作台**：评分分布、关键词搜索、3/4/5/6 分与未评分筛选、小屏自动卡片化；内嵌快照可双击直开 |

本技能**自包含、不依赖其他技能**：只调用本地已安装的 `whyai` CLI（whyai-cli 公开技能是可选补充，非必需）。

## 前置条件（内嵌环境核对规则）

1. **已安装并登录 whyai CLI**（安装与登录见官方 <https://ai.yitang.top/cli>；登录命令 `whyai login --gateway https://ai.yitang.top`，正式环境）。
2. **版本基线 `0.5.7`**：脚本运行前核对 `whyai --version`，与基线不一致会**拒绝执行**——版本变化可能改变命令行为与数据边界，先人工确认变化内容，确认无碍后加 `--skip-env-check`。
3. **登录态/Gateway**：脚本核对 `whyai status --json` 必须为 `logged_in: true`、`gateway: https://ai.yitang.top`、`environment: prod`。

### 安全边界（保密模式，内嵌）

- 本技能**只调用只读接口**：`yitang homework list`、`me info`、学习报告等 `risk: read` 能力。
- **禁止** `chat`（含 `--no-memory`，它不阻止内容上传）、文件上传、笔记/广场/伙伴等一切写能力、一切 `write` / `purchase` 能力——**全程零出境**：只有数据从服务端拉到本地，没有任何本地内容发出去。
- 已知且可接受的元数据行为：每条 `yitang` 命令会向 Gateway 上报一次收据（接口名、字节数、成败），**不含参数值与返回正文**；每个命令执行前 CLI 会做一次版本策略检查。
- 所有成绩数据只落本地，不回传。

## 使用

```bash
cd 你想存放数据的目录

# 第一步永远先 dry-run：环境核对 + 只拉取出对比报告，不写任何文件
python3 <技能目录>/scripts/refresh_homework.py --dry-run

# 确认报告（条数/合计/满分变化、新增/消失/评分变化明细）后，真实写入（默认自动生成 .bak）
python3 <技能目录>/scripts/refresh_homework.py

# 额外归档原始 API 返回（含作业正文全文）到 raw/一堂作业正文-<日期>.json
python3 <技能目录>/scripts/refresh_homework.py --with-raw
```

参数：`--target DIR`（输出目录，默认当前目录）、`--pages N`（限定页数）、`--no-backup`、`--skip-env-check`、`--with-raw`。

**脚本自动完成**：whyai 发现（`WHYAI_BIN` → `PATH` → macOS `~/.local/bin` → Windows `%LOCALAPPDATA%\WhyAI\bin`）→ 环境核对 → 分页拉取去重 → 与旧数据对比 → 原子写 JSON（旧文件存 `.bak`）→ 工作台生成：目标目录**没有** HTML 时从自带模板实例化；**已有**则仅替换其 `<script id="seed">` 块（其余人工修改保留，找不到唯一 seed 块则不动 HTML 并告警）。

## 工作台怎么用（数据更新后看新数据）

| 打开方式 | 效果 |
|---|---|
| 双击 HTML（`file://`） | 立即可看**内嵌快照**；但浏览器会拦截读取旁边 JSON 的请求（CORS），改了 JSON 不会自动生效 |
| 本地 HTTP 服务 | 自动读取旁边 JSON。例：`python3 -m http.server`，浏览器打开后状态条显示「已加载外部 JSON」 |
| HTML 里「导入 JSON」按钮 | 任何环境可用：手动选择 JSON 文件，读完刷新整页 |

## 数据契约（手工填写也支持）

```json
{
  "version": 1,
  "meta":    { "snapshotDate": "YYYY-MM-DD" },
  "account": { "score": 0, "scoreExtra": 0, "officialExcellent": 0, "officialPerfect": 0 },
  "rows": [ { "id": 1, "title": "课程/作业标题", "score": 5, "excellent": false,
              "commented": true, "wordCount": 1234, "date": "2026.09.21" } ]
}
```

两条铁律：

1. `count / sum / avg / 评分分布` 全部由 HTML 从 `rows` **实时计算**——不要写进 JSON，手填时不算数。
2. `account` 是**官方账户口径**（含额外学分与非作业来源），**永远不从作业列表推算**；缺失时脚本告警并留空。

## 口径方法论（读数据前必读）

- 「评分」= 单次作业的学分评定，取值 **3 / 4 / 5 / 6**，6 分为满分；`0`（页面显示 `—`）表示尚无评分。
- **逐条评分合计 ≠ 账户总学分**。账户侧另有额外学分与非作业来源，正式口径以账户学分为准；本清单只反映作业评分本身。
- **官方「优秀作业数」与列表 `excellent` 标记数可能不一致**：优秀标记可能只出现在高分作业上，差异原因无法从返回字段判定，以官方页面为准。
- 两项**应始终一致**，不一致说明抓取不完整（脚本会 WARN）：官方满分数 = 清单 6 分条数；官方作业总数 = `rows` 条数。

## 边界

- 只写目标目录下 `一堂作业评分清单.json` / `.html`（及 `.bak`）与 `raw/` 归档；不碰其他文件；删除/重命名产物由用户决定。
- 如需 whyai CLI 更完整的命令路由、Partner 体系与操作细节说明，可配合同仓的 `whyai-cli` 公开技能（可选，非依赖）。
