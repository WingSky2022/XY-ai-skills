---
name: yitang-homework-snapshot
description: 一条命令把你在「一堂」的全部作业评分拉到本地：只读调用 whyai CLI，生成 JSON 数据真相源 + 自包含 HTML 工作台（评分分布 / 搜索 / 档位筛选 / 小屏卡片），可选归档作业正文全文。带内嵌环境核对（版本基线 + 登录态）与保密模式边界（零出境，不调 chat、不上传、不写服务端）。当用户要求「更新作业评分」「拉取作业学分」「刷新作业清单」「查我作业得了几分」或要生成作业评分报告时触发。
triggers:
  - 更新作业评分
  - 拉取作业学分
  - 刷新作业清单
  - 作业评分报告
  - homework snapshot
version: 1.2.1
author: WingSky
---

# 作业评分快照（yitang-homework-snapshot）

一条命令把你在「一堂」的**全部作业评分**拉到本地。**关注点分离**——程序与前端在技能内，个人数据只写数据目录：

| 位置 | 内容 |
|---|---|
| 数据目录（默认 `~/Documents/一堂作业工作台`） | **只有数据**：`一堂作业评分清单.json`（`meta` + `account` + `rows[]`），可选 `raw/` 正文归档 |
| 技能目录/`workbench/` | **工作台前端**（评分分布、关键词搜索、3/4/5/6 分与未评分筛选、小屏卡片化）+ 双击启动入口 |
| 技能目录/`scripts/`、`assets/` | 拉取脚本、本地服务启动器、工作台模板 |

数据目录默认 `~/Documents/一堂作业工作台`；可用 `--target DIR` 或环境变量 `YITANG_HOMEWORK_DATA_DIR` 指定，也可在技能目录自建 `config.json`（`{"data_dir": "路径"}`，相对路径按技能目录解析）。

本技能**自包含、不依赖其他技能**：只调用本地已安装的 `whyai` CLI（whyai-cli 公开技能是可选补充，非必需）。

## 前置条件（内嵌环境核对规则）

1. **已安装并登录 whyai CLI**（安装与登录见官方 <https://ai.yitang.top/cli>；登录命令 `whyai login --gateway https://ai.yitang.top`，正式环境）。
2. **版本基线 `0.5.8`**：脚本运行前核对 `whyai --version`，与基线不一致会**拒绝执行**——版本变化可能改变命令行为与数据边界，先人工确认变化内容，确认无碍后加 `--skip-env-check`。
3. **登录态/Gateway**：脚本核对 `whyai status --json` 必须为 `logged_in: true`、`gateway: https://ai.yitang.top`、`environment: prod`。

### 安全边界（保密模式，内嵌）

- 本技能**只调用只读接口**：`yitang homework list`、`me info`、学习报告等 `risk: read` 能力。
- **禁止** `chat`（含 `--no-memory`，它不阻止内容上传）、文件上传、笔记/广场/伙伴等一切写能力、一切 `write` / `purchase` 能力——**全程零出境**：只有数据从服务端拉到本地，没有任何本地内容发出去。
- 已知且可接受的元数据行为：每条 `yitang` 命令会向 Gateway 上报一次收据（接口名、字节数、成败），**不含参数值与返回正文**；每个命令执行前 CLI 会做一次版本策略检查。
- 所有成绩数据只落本地，不回传。

## 使用（两段式：先检查，确认后才写入）

```bash
# 第一段：环境核对 + 只读拉取 + 出报告，**不写任何文件**
python3 <技能目录>/scripts/refresh_homework.py

# —— 到此为止只读。把报告（条数 / 评分分布 / 新增消失 / 评分变化）给用户看，取得明确确认 ——

# 第二段：用户确认后才写入，并直接拉起后台服务 + 打开工作台
python3 <技能目录>/scripts/refresh_homework.py --confirm --serve

# 可选：顺带归档作业正文全文到 数据目录/raw/
python3 <技能目录>/scripts/refresh_homework.py --confirm --with-raw
```

**确认门禁（硬规则）**：`--confirm` 表示「用户已确认全量写入」。**未经用户明确确认，不得自行加 `--confirm`**；无 `--confirm` 时脚本只做只读检查与报告。

参数：`--confirm`（授权写入）、`--serve`（写入后拉起工作台）、`--target DIR`（覆盖数据目录）、`--pages N`、`--with-raw`、`--no-backup`、`--skip-env-check`。

**脚本自动完成**：whyai 发现（`WHYAI_BIN` → `PATH` → macOS `~/.local/bin` → Windows `%LOCALAPPDATA%\WhyAI\bin`）→ 环境核对 → 分页拉取去重 → 与旧数据对比 → （确认后）原子写数据目录 JSON（旧文件存 `.bak`）→ 在技能内 `workbench/` 生成工作台前端（空 seed）+ 双击启动入口 → 可选拉起后台服务。

## 工作台怎么用

**推荐：让技能拉起后台服务**（`--serve`）：自动选空闲端口启动本地服务并打开浏览器，此时页面**真正读取数据目录的 JSON**，数据源与 JSON 始终一致。停止服务：`python3 <技能目录>/scripts/start_workbench.py --stop`。

**随时手动打开**：

```bash
python3 <技能目录>/scripts/start_workbench.py        # 前台服务 + 自动开浏览器，Ctrl+C 停止
```
也可双击 `workbench/start-workbench.command`（macOS）/ `workbench/start-workbench.bat`（Windows）。

服务是**双根**的：请求先在工作台根（技能内）找，找不到再回落到数据根——前端与数据无需同目录。只监听 `127.0.0.1`。

| 打开方式 | 效果 |
|---|---|
| 本地服务（推荐） | **自动读取数据目录 JSON**（状态条显示「已加载外部 JSON」）——数据源唯一 |
| 双击技能内 HTML（`file://`） | 技能内工作台是**空 seed**，会提示「请用工作台启动器打开」；不显示个人数据（个人数据不在技能里） |
| HTML 里「导入 JSON」按钮 | 任何环境可用：手动选数据目录的 JSON，读完刷新整页 |

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
2. `account` 是**官方账户口径**（含额外学分与非作业来源），**永远不从作业列表推算**。首次运行时脚本写入空值并告警，页面显示「—」与「账户口径待填写」提示，等你手工补这四项。

> 刷新策略：`rows` 以官方拉取为权威，**每次全量写入整体覆盖**；`account` 保留人工值。若要保留手工补录的作业条目，不要加进 `rows`（会被覆盖），改为放在单独文件里自行维护。

## 口径方法论（读数据前必读）

- 「评分」= 单次作业的学分评定，取值 **3 / 4 / 5 / 6**，6 分为满分；`0`（页面显示 `—`）表示尚无评分。
- **逐条评分合计 ≠ 账户总学分**。账户侧另有额外学分与非作业来源，正式口径以账户学分为准；本清单只反映作业评分本身。
- **官方「优秀作业数」与列表 `excellent` 标记数可能不一致**：优秀标记可能只出现在高分作业上，差异原因无法从返回字段判定，以官方页面为准。
- 两项**应始终一致**，不一致说明抓取不完整（脚本会 WARN）：官方满分数 = 清单 6 分条数；官方作业总数 = `rows` 条数。

## 边界

- 只写两处：**数据目录**的 `一堂作业评分清单.json`（及 `.bak`、可选 `raw/`）；**技能目录**的 `workbench/`（工作台前端、启动入口、服务点文件，且带 `.gitignore` 屏蔽点文件）。不碰其他文件；删除/重命名产物由用户决定。
- **个人数据只落在数据目录**：技能目录内的工作台是空 seed，避免个人数据进入版本库或随技能分发外流。
- 后台服务只监听 `127.0.0.1`，不对外网暴露；不需要时用 `--stop` 关闭。
- 如需 whyai CLI 更完整的命令路由、Partner 体系与操作细节说明，可配合同仓的 `whyai-cli` 公开技能（可选，非依赖）。
