# yitang-homework-snapshot · 作业评分快照

一条命令把你在「一堂」的**全部作业评分**（1–6 分）拉到本地，生成一对文件：JSON 数据真相源 + 自包含 HTML 工作台（评分分布、搜索、档位筛选、手机端卡片视图）。可选把作业正文全文一并归档。

- **只读、零出境**：只调用本地 `whyai` CLI 的只读接口，没有任何本地内容发往服务端。
- **自包含**：不依赖其他技能；环境核对（版本基线 + 登录态）内嵌在脚本里。
- **数据你做主**：JSON 是真相源，可手填；HTML 是展示模板，改数据后一键刷新。

## 安装

1. 前置：已安装 [whyai CLI](https://ai.yitang.top/cli) 并完成登录（`whyai login --gateway https://ai.yitang.top`）。
2. 把整个 `yitang-homework-snapshot/` 目录复制到你的 Agent 技能目录（各工具的 skills 目录），或任意你方便的位置——脚本按自身位置定位自带模板，放哪都能跑。

## 激活（两种方式）

**对 Agent 说**（已装入技能目录时）：「更新我的作业评分」「拉取作业学分」「查我作业得了几分」。

**直接命令行**：

```bash
cd 你想存放数据的目录
python3 <技能目录>/scripts/refresh_homework.py --dry-run   # 先看环境核对 + 对比报告，不写文件
python3 <技能目录>/scripts/refresh_homework.py             # 真实写入（自动 .bak）
python3 <技能目录>/scripts/refresh_homework.py --with-raw  # 顺带归档作业正文全文
```

## 约定（使用前请读）

- 产物：`一堂作业评分清单.json`（真相源）+ `一堂作业评分清单.html`（工作台，双击即看内嵌快照）+ 可选 `raw/` 正文归档；覆盖前自动生成 `.bak`。
- **改数据后如何生效**：双击打开时浏览器会拦读取旁边 JSON（`file://` 限制）——用 HTML 里的「导入 JSON」按钮手动加载；或 `python3 -m http.server` 起本地服务后打开，会自动读取。
- **手填规则**：只填 `rows`（每条 id/title/score/excellent/commented/wordCount/date）与 `account` 四项；所有统计（合计/平均/分布）由页面实时计算，不要写进 JSON。
- **口径**：单次作业评分 3/4/5/6（6 = 满分）；**逐条合计 ≠ 账户总学分**（学分含额外学分与非作业来源）；官方「优秀作业数」与列表标记数可能不一致，以官方页面为准。
- **安全边界**：只调只读接口，禁止 chat / 上传 / 任何服务端写入；版本与登录态核对不过时脚本拒绝执行（确认无碍后可 `--skip-env-check`）。
