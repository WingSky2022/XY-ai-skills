---
name: whyai-cli
description: |
  通过本地 whyai CLI 调用 YAI / 一堂服务：用户明确要求使用 YAI、委托 YAI 处理任务、查看账户/模型/配额/用量、排查 token 消耗异常，或管理 YAI 会话与文件时触发；检测不到 CLI 时按官方说明自动安装。
  默认保密模式（只拉取不出境，出境需当次确认）。用户说「解开/解放保密模式」时本会话内免逐次确认（凭据/不可逆公开/不可逆删除/账号与环境变更四类红线除外，不跨会话继承）。
  支持查询与挂载 YAI 侧 Partner（partners 只读、chat --partner 挂角色）；长文本默认落盘只读摘要（chat 重定向、conversations export --output、勿用 messages list）；多轮任务在发起第二轮前把会话 id 写入锚点文件（多任务共用一份 map）、逐轮用 -c 续用（绝不把历史回灌新会话），且必须留存 stderr。
  多伙伴协作按「是否需自动交叉引用」选架构；省 token 姿势与成本异常诊断（先定账本：服务端配额 vs 本地额度，平方由轮数而非命令造成）见「命令路由 §D–§E」；会话锚定、中途断联后的续用见「会话锚定、中断与恢复」。
argument-hint: "[check|install|status|login|models|account|billing|usage|conversations|partners|notes|memories|files|yitang|chat|upgrade]"
version: 1.14.0
author: WingSky
---

# WhyAI CLI（`whyai`）

本技能是 **YAI CLI 的本地 Agent 操作封装**，不是另一个 API 客户端，也不安装 wrapper。只在用户明确要求使用 YAI / WhyAI 时调用；不要把普通 AI 请求自动转发到 YAI。

---

## 默认保密模式（最高优先级）

本技能**默认以保密模式运行**：**只从 YAI 服务端拉取数据，不把本地的会话、文档、图片、音频或加工结果推送到 YAI。**

判定口诀：**「读=放行，写=要确认；拉=放行，推=要确认。」**

### 保密模式放行（单向 YAI → 本地）

| 类别 | 命令 |
|---|---|
| 身份 / 配额 | `status`、`account show\|usage`、`billing access\|plans\|subscriptions\|summary\|grants\|usage`、`models list` |
| 会话读取 | `conversations list\|get\|export`、`messages list\|versions\|minimap` |
| 笔记读取 | `notes list\|get\|export`、`note-folders list` |
| 记忆审计 | `memories list` |
| 文件元信息 | `files list\|quota\|get` |
| 一堂只读能力 | `whyai yitang` 下 `risk: read` 的能力（`homework list\|show`、`course info\|sections`、`me show` 等） |

> ⚠️ **`account model-usage` 已失效**（0.5.7 实测，2026-09-21）：无论 `--period` 取何值，服务端一律返回
> `410 USAGE_UNAVAILABLE`（`usage statistics endpoint is no longer available`）。
> **模型维度的用量/成本统计当前没有 CLI 入口**——`account usage` 只给配额百分比与 CLI 收据，**不含模型维度**。
> 需要判断「实际在用哪个模型」时，改用 `conversations list --json` 的 `model_id` 字段做分布统计（只读、无副作用）。

### 保密模式禁止（默认不发，除非走「出境确认」）

| 类别 | 命令 / 参数 | 出境的内容 |
|---|---|---|
| 发消息 | `chat`（**含 `--no-memory`**） | 提示词；不带 `-c` 时**自动新建服务端会话** |
| 本地内容当消息 | `@path`、`-`、heredoc、管道 | **本地文件整段内容** |
| 上传 | `files upload`、`chat --file`、`files reparse` | 本地文件（≤10MB，扩展名白名单） |
| 语音 | `asr <audio>` | 本地音频 base64 全量 |
| 写笔记 | `notes create\|update\|save-conversation\|generate\|download-log`、`note-folders create\|update\|delete\|reorder` | 本地文本 / JSON |
| 传本地 JSON | 任何 `--data @file`（notes / partners / plaza 等） | 本地 JSON 文件内容 |
| 转公开 | `plaza publish\|update\|visibility`、`share create` | 内容由私有变公开 |
| 伙伴写操作 | `partners create\|update\|publish\|optimize-prompt` | 提示词 / 配置 |
| 一堂写操作 | `whyai yitang call` 中 `risk: write` / `purchase` 的能力 | 参数内容（部分会改变账户状态） |

> ⚠️ **`--no-memory` 的语义**：它只关闭**记忆抽取**，**不阻止内容上传**。`whyai chat --no-memory "…"` 依然会把提示词写入服务端会话。保密模式下 `chat` 一律需确认。

### 保密模式解锁（用户显式指令）

**触发口令**——只认用户**主动说出**，AI 永远不得自行解锁、不得诱导用户解锁：

> **「解开保密模式」** / **「解放保密模式」**

同义变体一并识别：**「解除保密模式」「解锁保密模式」「关闭保密模式」**。

#### 作用域与时效（硬约束）

- **仅在当前会话内有效**：不写入任何文件、不写进本技能、不跨会话继承。新会话自动回到保密模式。
- 用户说**「恢复保密模式」「锁上」「回到保密模式」** → **立即回锁**，不必再问。
- **不得把模糊表述当作解锁口令**（「你看着办」「随便」「不用问了」「怎么方便怎么来」都不算）。不确定时按保密模式处理，并反问一句确认。

#### 解锁后放行（不再逐次询问的「内容出境」类）

`chat`（含 `@file` / `-` / `--file` / `--web-search` / `--knowledge-base` / `chat --partner`）、`asr`、`files upload`、`notes` 写、所有 `--data @file`。

#### 解锁后仍须单独确认的四类红线

这四类与「内容出境」无关，属**凭据 / 不可逆 / 环境变更**，**不在保密模式的管辖范围内，解锁口令对它不生效**：

| 类别 | 命令 | 为什么不能随解锁放行 |
|---|---|---|
| 凭据外泄 | `whyai token` | 把有效访问令牌输出到 stdout，等于交出账户 |
| 不可逆公开 | `plaza publish\|update\|visibility`、`share create\|update` | 内容由私有变公开，撤回不保证有效 |
| 不可逆删除 | 所有 `delete`、`memories clear`、`files delete`、`conversations delete` | 服务端资产删除后不可恢复 |
| 账号与环境变更 | `login`、`logout`、`upgrade` | 改变登录态或运行版本，可能改变数据边界 |

#### 解锁 ≠ 免除版本核对


#### 解锁期间仍须履行的义务

1. **不主动建议解锁**，也不为省事而诱导用户说出解锁口令。
2. **每次出境动作完成后主动汇报**：新建的会话 id、上传的文件 id、是否触发记忆抽取（服务端默认开启）。
3. **保持最小出境面**：能用 `-c <id>` 续用已有会话就不新建；非必要不上传本地文件；本地能完成的加工不回推给 YAI。
4. **首次出境时提示一次**：记忆抽取默认开启，如不需要可加 `--no-memory`。提示一次即可，不重复打扰。
5. **回锁时汇总**：用户回锁或会话结束时，汇总本次解锁期间发生过的出境动作（动作、时间、目标会话/文件 id），便于事后审计；并写明用户说出解锁口令的时间与原文，便于回溯。

---

## 出境确认流程（触发条件：用户要求用 YAI 加工本地材料）

当用户要求上传文档/图片/音频、发送提示词、或把本地内容交给 YAI 加工时，**先停，不要直接执行**：

> ⚡ **若用户已解锁保密模式**（见「保密模式解锁」）：**跳过第 2 步的当次确认**，但第 1 步的说明、第 3 步的降风险、第 4 步的事后报告**照常执行** —— 解锁省掉的是「反复问」，不是「告知与汇报」。四类红线动作（凭据 / 不可逆公开 / 不可逆删除 / 账号与环境变更）不随解锁放行，仍须单独确认。

1. **说明将发送什么**：文件名或路径、大小、类型（例：`report.pdf`，240KB）；目标 Gateway（`https://ai.yitang.top`）；副作用（是否新建服务端会话、是否触发记忆抽取、是否转为公开）
2. **征询当次确认**：等用户明确回答（确认 / 发吧 / 同意）。未确认**一律不执行**，也不要改用等价命令绕过
3. **执行时降低风险**：加 `--no-memory` 关闭本次记忆抽取；延续会话用 `-c <id>` 而非新建；能本地完成的加工（分类、萃取、统计、格式转换）优先用本地工具，只有确实需要 YAI 能力时才出境
4. **事后报告**：告知实际发生了什么——新建的会话 id、上传的文件 id、是否产生记忆条目；不需要的资产提示用户可删除（`files delete <id>` / `conversations delete <id>`）

---

## 固定环境

- 正式 Gateway：`https://ai.yitang.top`
- 官方安装说明：<https://ai.yitang.top/cli>
- 官方安装脚本：`https://ai.yitang.top/cli/install.mjs`
- 用户咨询参考页（需要时可发送给用户）：<https://yitanger.feishu.cn/wiki/XoFcwMmotigm7Ikv4RQc9TfQn0g>
- 安装要求：Node.js 20 或更新版本；macOS/Linux 默认命令目录为 `~/.local/bin`
- 每次需要调用前先确认：`command -v whyai`、`whyai --version`、`whyai status --json`
- `status` 必须显示 `gateway` 为 `https://ai.yitang.top` 且 `environment` 为 `prod`；Gateway 不匹配时停止，不要继续发送请求

## 调用前检测与自动安装路由

每次触发本技能时先运行：

```bash
command -v whyai
node --version
whyai --version
```


如果找不到 `whyai`，用户已授权本技能自行安装，因此可以直接执行官方安装流程，不必再次询问安装确认：

1. 检查 Node.js；不存在或主版本低于 20 时停止，报告依赖问题，不要自行安装 Node.js。
2. macOS/Linux 按下方官方安装命令下载并执行 `https://ai.yitang.top/cli/install.mjs`；Windows PowerShell 使用官方页面对应命令。
3. 将安装目录加入当前 Agent 进程的 PATH（POSIX 为 `~/.local/bin`；Windows 为 `%LOCALAPPDATA%\\WhyAI\\bin`）。
4. 运行 `whyai --version` 验证命令路径和版本，并报告安装结果。
5. 安装完成不等于已登录；只有用户要求调用业务功能或明确要求登录时，才进入登录路由。

若安装失败，只报告具体原因并停止；不要改用 npm 猜测包名、第三方脚本或未核验下载源。

## 安装与升级

升级仍需用户明确要求。优先按官方页面的下载、校验和安装流程，不要猜测 npm 包名或使用第三方脚本。检测缺失触发的是上面的自动安装路由，不是升级路由。

macOS / Linux：

```bash
cli_tmp="$(mktemp -d)"
curl -fsS https://ai.yitang.top/cli/install.mjs -o "$cli_tmp/install.mjs"
node "$cli_tmp/install.mjs"
export PATH="$HOME/.local/bin:$PATH"
whyai --version
```

Windows PowerShell 使用官方页面对应命令。安装完成后再次运行 `whyai --version`，并确认解析到预期的命令路径。

升级使用：

```bash
whyai upgrade
whyai --version
```

## 登录与 Gateway 校验

登录命令固定使用正式环境：

```bash
whyai login --gateway https://ai.yitang.top
```

登录会通过 YiTang 浏览器 SSO 授权。图形环境下可让 CLI 打开浏览器；无头环境使用 `--no-open`，把 CLI 输出的授权链接交给用户完成授权。登录完成后必须运行：

```bash
whyai status --json
```

只接受同时满足以下条件的状态：`logged_in: true`、`gateway: "https://ai.yitang.top"`、`environment: "prod"`。不要代替用户输入密码、验证码或批准授权。

## 命令路由

优先使用 `--json`，便于稳定解析；将结果中的令牌、个人标识和其他敏感字段脱敏后再汇报。

### A. 默认可用（只读拉取，不出境）

| 用户意图 | 命令 |
|---|---|
| 登录状态 / 当前用户 | `whyai status --json` / `whyai account show --json` |
| 可用模型 | `whyai models list --json` |
| CLI 资格与配额 | `whyai billing access\|summary\|grants\|usage` |
| 账户用量 | `whyai account usage`（⚠️ 只给配额百分比与 CLI 收据，无模型维度；`model-usage` 端点已下线，见「保密模式放行」表下注） |
| 对话列表 / 读取 | `whyai conversations list\|get ...` |
| **会话导出（读取侧首选）** | `whyai conversations export <id> --output <path>` —— **唯一带 `--output` 的读命令，实测 stdout 零字节** |
| 消息列表（⚠️ 全文走 stdout） | `whyai messages list <conversation-id>` —— 实测 65KB 全部进本地上下文；**除非确需在上下文里比对，否则改用 export** |
| 笔记读取 | `whyai notes list\|get\|export <id>` |
| 记忆审计 | `whyai memories list --json` |
| 伙伴只读 | `whyai partners list\|search\|resolve\|get\|history\|tags\|icons`、`partners conversations\|recommended <id>` |
| 文件元信息 | `whyai files list\|quota` |
| 一堂只读数据 | `whyai yitang homework list\|show`、`course info\|sections`、`me show` 等 `risk: read` 能力 |

**模型选择（默认策略，2026-09-21 起）**

新建会话的 `chat` **显式指定模型**，不再依赖服务端默认；策略以 [`references/model-catalog.json`](references/model-catalog.json) 的 `default_policy` 为准：

| 场景 | 传参 |
|---|---|
| 默认（纯文本 / 非图片附件） | `--model deepseek-v4-flash` |
| **本次消息带图片**（`--file` 指向 `.png` / `.jpg` / `.jpeg` / `.webp` / `.gif`） | `--model deepseek-v4-flash-vision-exp` |

- 混有图片与文档 → **按图片处理**（取 vision 模型）；纯文档（pdf / docx / xlsx）用默认模型
- **用户显式指定 `--model` 时一律以用户为准**，不套用本策略
- **续用已有会话（`-c <id>`）不传 `--model`**：payload 会带上该字段且服务端行为未验证，保守做法是保持会话原模型不变

### B. 需先走「出境确认流程」

| 用户意图 | 命令 | 备注 |
|---|---|---|
| 发送一次请求 | `whyai chat "<内容>"` | 会新建会话；默认触发记忆抽取 |
| 继续会话 | `whyai chat -c <id> "<内容>"` | 同上，不新建 |
| 开启联网搜索 / 知识库 | `whyai chat --web-search \| --knowledge-base` | 检索词同样出境 |
| 上传文件 | `whyai files upload <路径>` / `chat --file <路径>` | 本地文件上传并被服务端解析 |
| 语音转写 | `whyai asr <audio>` | 音频全量上传 |
| 写入笔记 / 记忆清理 | `whyai notes create\|update\|save-conversation`、`memories delete\|clear` | 写入或删除服务端资产 |
| 转公开 | `whyai plaza publish`、`whyai share create <conv>` | 内容转为公开可见 |
| **挂载伙伴对话** | `whyai chat --partner <id或精确名> "<内容>"` | 新建会话并挂角色；**附带一次服务端写操作**（见 §C） |
| 伙伴写操作 | `whyai partners use\|create\|update\|publish\|optimize-prompt` | `use` 会写使用记录与排序 |
| 一堂写操作 | `whyai yitang call <id> --confirm` | 先 `whyai yitang describe <id>` 确认 `risk` |

### C. Partner（伙伴 / 角色）调用

Partner 是 YAI 侧的角色（人格 + 提示词 + 知识库配置），**不是一堂基础产品侧的东西**——`yitang` 能力表里没有任何 partner 项，查询与挂载全部走 YAI 的 `/partners`。

**唯一调用路径是 `chat --partner`。不存在 `partners run` / `invoke` 这类独立执行命令。**

```bash
# 1) 找伙伴（只读）——search 对 name + description 做子串匹配
whyai partners list --json                              # 全量
whyai partners search "调研" --json                      # 子串搜
whyai partners list --type R --json                     # 按 TCPR 过滤：T 教学 / C 咨询 / P 实践 / R 研究
whyai partners search "调研" --scope official --json     # 只看官方

# 2) 解析成 id（只读）——确认唯一性，避免歧义报错
whyai partners resolve "高阶调研·爆炸式研究专家" --json

# 3) 挂角色开新会话（出境，需先确认；会附带一次使用记录写入）
whyai chat --partner <partner-id> "研究课题"
whyai chat --partner "高阶调研·爆炸式研究专家" "研究课题"     # 中文精确名同样可用

# 4) 续用已有会话（-c 优先，此时 --partner 被忽略）
whyai chat -c <conversation-id> "继续"
```

**四个必须记住的机制（已实读并复核）**

1. **名称解析只认 id 或「精确全等的中文名」**，大小写不敏感；**slug 不可用**。`resolvePartner()` 只做 `id` 全等 + `name` 全等两步（`dist/src/domain/partner.js`），所以 `resolve explosive-research` 会直接报 `Partner not found`；同名多个会报 `ambiguous; use an ID`。
2. **`--partner` 只对「新建会话」生效**。带了 `-c <id>` 时该参数被完全忽略（`dist/src/commands/chat.js:269-282`）。想换角色只能开新会话。
3. **挂角色会附带一次服务端写操作**（即使不发消息）。建会话前先调 `recordPartnerUseAndPromote()` 写使用记录并调整历史排序（`chat.js:276`）；独立命令 `partners use <id>` 做的是同一件事——**它不等于「设成当前 Partner」**。
4. **客户端不校验 `can_use` / `conversation_window_end`**：全量源码里搜不到这两个字段的引用，拦截（若有）只在服务端，CLI 侧不会替你拦下不可用的伙伴。

**试用窗口（`conversation_access: trial` + `conversation_window_end`）不等于不可用**

`partners list` 会返回 `conversation_access`（`trial` / `unrestricted`）和 `conversation_window_end`。实测：`trial` 与 `unrestricted` 两种伙伴都可能存在；`trial` 伙伴的 `conversation_window_end` 即使已过期，**订阅有效时仍能正常新建并持续使用**。会话还会把创建时的窗口快照进 `conversation_window_end_snapshot`。

> 判据：**窗口过期本身不构成「不可用」的证据**，要结合 `billing access` 的订阅状态判断；真实拦截若发生，会以服务端报错形式返回，届时按报错处理而非预判。

### D. 省 Token 的调用姿势（结果落盘，Agent 只读摘要）

`chat` 的**两种输出模式都把全文写到 stdout**，而 stdout 就是 Agent 读到的工具结果——**直接跑 = 全文进本地上下文**，YAI 配额与本地上下文各付一遍：

- 默认流式模式：`process.stdout.write(content)` 逐块写正文（`chat.js:176`）
- `--json` 模式：`printResult(result, {json: true})` → `console.log(JSON.stringify(value, null, 2))`，`content` 字段就是全文（`chat.js:323-324`、`core/io.js:64-67`）

而 `chat` **没有 `--output` / `-o` 这类落盘参数**（`whyai chat --help` 核实），所以只能靠 shell 重定向。

**落盘有两条路径，别只记一条** —— 「生成」与「读取」是两个独立环节，最优解不同：

| 环节 | 最优命令 | 说明 |
|---|---|---|
| **生成**（内容由本地发起） | `whyai chat … > out.md` | `chat` 无 `--output`，只能 shell 重定向 |
| **读取**（会话已在服务端） | **`whyai conversations export <id> --output out.md`** | **自带 `--output`**，实测 stdout 零字节、stderr 仅一行 `Wrote <path>` |

同一会话（14 轮 / 7 组问答）两种读法的实测对比：

| 读法 | 输出形态 | 实测 |
|---|---|---|
| `conversations export <id> --output f.md` | **落盘** | **35,704 字节 / stdout 0 字节** ✅ |
| `messages list <id> --all --json` | 走 stdout | **65,298 字节全部进上下文** ⚠️ |

> 用错命令等于白省。另：导出的 markdown **不含推理链**，是纯净正文；`--format json` 反而大 1.8 倍（65KB vs 35KB）→ **优先默认的 `md`**。

> ⚠️ **`--output` 必须显式写文件名**：该参数默认值是 `-`（即 stdout），**省略就退回「全文进本地上下文」**，等于白省（`conversations.js:126`、`core/io.js:85-86`）。这是「落盘」与「没落盘」之间唯一的开关。

**好消息是 stdout 很干净**：建会话提示、上传进度、工具调用日志、推理增量、重连提示**全部走 stderr**（`chat.js:183 / 188 / 193 / 229 / 287 / 292`），stdout 只有助手正文与结尾换行。因此重定向能精确切分「正文」与「过程」。

```bash
# 正文落盘；过程与推理单独走 stderr（需要时才加 --show-thinking）
whyai chat --partner "高阶调研·爆炸式研究专家" "课题" --no-memory \
  > /tmp/whyai-out.json 2> /tmp/whyai-run.log

# 只读元数据：会话 id / 正文长度 / 工具调用次数 —— 正文留在文件里
python3 -c "import json;d=json.load(open('/tmp/whyai-out.json'));\
print(d['conversation_id'], len(d['content']), len(d['tool_executions']))"
```

**执行纪律**

1. **重定向之后不要 `cat` 全文**——否则前面白做。只看 `wc -c`、抽字段、`head` 或按需取片段。
2. **需要用户看正文时，给出文件路径让用户自己打开**，不要回显。用户随后明确要求「总结一下」时才读，且优先读关键片段。
3. `--json` 模式在**失败时也会先把部分结果打到 stdout**（`chat.js:329-330`）再以非零退出码结束——所以落盘文件可能含部分正文，判读时结合退出码。
4. 多轮任务**在发起第二轮之前把会话 id 落盘锚定**，随后逐轮用 `-c <id>` 续用同一会话：历史由服务端累积，本地不必重发——锚定时机（单次任务不锚）与「id 丢失」的危险入口见「会话锚定、中断与恢复」。

> ⚠️ **重定向只省「本地 token」，不改变出境性质**：内容照样上传服务端、照样可能触发记忆抽取，保密模式判定与出境确认流程完全不受影响。

### E. 多 Partner 协作：谁驱动多轮，决定成本量级

`export --output` 只优化**「读」**，**救不了「聊」**。多轮循环的平方级开销由「**谁驱动多轮**」决定，两个环节相加才是总账：

| 编排方式 | 多轮阶段本地成本 | 汇总阶段本地成本 | 协作能力 |
|---|---|---|---|
| 本地 Agent 循环调 CLI | **平方级**（每轮输出都留在上下文） | 已含在内 | ✅ 可自动把 A 的结论喂给 B |
| **网页端多线 + 本地 export 汇总** | **0**（本地 LLM 完全不参与） | 落盘为 0，按需抽片段 | ❌ 各 Partner 互相看不见，需人工串联 |

**选型判据不是「省不省 token」，而是「协作是否需要自动交叉引用」**：

- 各 Partner **独立调研**、由人串联结论 → **网页端多线 + `export` 落盘 + 本地脚本抽取**（本地成本最低）
- 需要 **A 的输出自动喂给 B**、多轮自动编排 → 只能用本地循环（代价是本地平方级）

> 一个容易绕进去的点：**若多轮本就是本地 CLI 驱动的，则不需要 `export`** —— `chat > file` 已经等价。
> `export` 的独有价值恰恰是**桥接「网页端产生的内容」与「本地加工」之间那道缝**：它让「读」这一步归零，前提是内容先在网页端聊出来。


## 会话锚定、中断与恢复


### 会话锚定：什么时候必须把 id 写下来


所以锚定**不是「每次对话的第一动作」**，而是按需触发——只在对话确实要延续时才把 id 写下来：

| 档 | 何时落盘 | 适用场景 | 额外代价 |
|---|---|---|---|
| **不锚**（默认） | —— | 单次一问一答、各轮互不依赖上下文的调用（`billing` / `models` / `conversations list` 等只读查询、一次性 `chat`） | 0 |
| **延迟锚**（自然多轮的默认） | **首轮不写锚点；决定发起第二轮时，先把 id 落盘，再发第二轮** | 边跑边看、跑到一半才发现要续问的任务 | 0（不新增任何调用） |
| **预锚**（例外，须申报） | 第一句话发出前就固定 id：`whyai conversations create --title "<任务名>" --json` | 需先定标题 / 先挂 Partner；或跨 Agent、跨设备交接前就要钉死 | 一次服务端写操作 |

**为什么「第二轮再锚」可行**：CLI 命令集**没有「这是第几轮」这类信号**，所以「检测到第二轮」做不成自动检测——但**也不需要检测**：Agent 本身就是发起方，它决定发第二轮的那一刻天然知道。把落盘动作推迟到**发起第二轮之前**即可；此时 id 仍在上下文里，语义与「首轮后立刻落盘」完全等价，而单次任务**零副作用**（不产生任何文件）。

> ⚠️ **延迟锚的已知窗口**：首轮结束 → 发起第二轮之前，id 只活在上下文里。该窗口内若上下文被压缩、会话中断或换了 Agent，**续聊能力即丢失**。单次任务不受影响；**已明确要多轮 / 长任务 / 重要任务**应跳过延迟档，首轮结束后**立即落盘**（用同一份 map 文件）。

**兜底：不写锚点 ≠ 丢 id。** 首轮的会话 id 已随产物落在磁盘上，最坏情况也能取回（代价仅一次 `grep -o`，只回一行，不读全文）：

| 来源 | 取法 |
|---|---|
| `--json` 的落盘产物 | `grep -o '"conversation_id": "[^"]*"' out.json` |
| stderr 日志 | 不带 `--json` 时，建会话提示 `Created conversation <id>` 打在 stderr（`chat.js:287`）—— §D 的「留存 stderr」纪律同时服务于锚定 |
| 服务端 | `whyai conversations list --json`（最后手段，需人眼筛选） |

**三条不变的纪律**：id 一旦落盘，**每次调用前先读锚点**（本轮提问形如 `whyai chat -c "$(读出的 id)" …`）；**绝不把历史回灌新会话**；**不得用 `--data @file` 喂本地文件**。

**锚点文件：一份 map 装多个任务**

文件名 `.whyai-sessions.json`（复数），落在**当前任务的工作目录**（项目已有工作区约定时建在其中）。**同一目录并行跑多个 YAI 任务共用这一份 map**，每个任务只读写自己那个键——**不得整体覆盖文件**，否则会抹掉其它任务的锚。

```json
{
  "version": 1,
  "sessions": {
    "cost-diagnosis": {
      "conversation_id": "a7184ed2-…",
      "title": "成本异常排查",
      "partner_id": null,
      "updated_at": "2026-09-20T20:10:00+08:00"
    },
    "partner-survey": {
      "conversation_id": "…",
      "updated_at": "…"
    }
  }
}
```

- **任务键**：语义化 kebab-case，由用户指定或 Agent 自拟；**定下就不许改**（改名等于丢锚）。只有一个任务时用 `default`；不要用随机串或时间戳做键。
- **写纪律**：**读 → 只改本任务的键 → 写回**；写入用「临时文件 + rename」原子替换，避免两个任务并发写时互相截断。
- **每次续用后刷新 `updated_at`**，便于判断条目新旧。任务结束条目可保留；确认不再需要时**只删本任务的键**。
- 预锚 / 延迟锚 / 首轮后立即落盘——三种时机的**文件格式完全一致**，只有写入时刻不同。

```bash
# 读锚点 → 发起第二轮（省 token 姿势照 §D）
whyai chat -c "$(python3 -c \
  "import json;print(json.load(open('.whyai-sessions.json'))['sessions']['cost-diagnosis']['conversation_id'])")" \
  "下一问" > out2.md 2> run2.log
```

**预锚前须先申报**（属「写」操作，走「出境确认流程」）：

- `conversations create` 打的是 `POST /conversations`（`conversations.js:44-60`），payload 仅 `title` / `model_id` / `partner_id`，**不含本地内容** —— 确认时说明这一点即可。
- 带 `--partner <id>` 会**额外触发一次写操作**（`recordPartnerUseAndPromote`，`conversations.js:57-58`），与 `chat --partner` 一致。
- 锚点确立后，**把 id 与锚点文件路径一并报给用户**。

### 中断后要不要新开会话？

**不需要。** 会话在提问发出前就由客户端创建（`chat.js:277-288` 第一步即 `POST /conversations`）——中断的是「这一轮的回复流」，不是会话本身，服务端留存不受影响。恢复时直接续用原会话：

```bash
# 已知会话 id：直接续用（新一轮请求，历史在服务端）
whyai chat -c <conversation-id> "下一个问题"

# 接着上一段被截断的回复继续写
whyai chat -c <conversation-id> --continue

# 会话 id 丢失：先找回，再续用（绝不开新会话回灌历史）
whyai conversations list --json
```

### `-c` / `--continue` / `--regenerate` 三者语义

| 参数 | 语义 | 计费 | 历史来源 |
|---|---|---|---|
| `-c <id>` | 续用已有会话；payload **只含本轮 content**（`chat.js:307-320`） | 新一轮 | 服务端维护，本地不重发 |
| `--continue` | 发一句固定文本「请继续完成上面的回答」（`chat.js:299-300`），**必须配 `-c`** | 新一轮 | 复用原会话，接续被截断的回复 |
| `--regenerate <message-id>` | 精确重做某一条已有消息 | 新一轮 | 复用该会话上下文，不重发历史 |

> ⚠️ `--continue` 不是「免费补完」：它本质是再发一轮新请求，**单独使用无意义——必须带 `-c <conversation-id>`**，否则回到新建会话逻辑。

### 会话 id 丢失是唯一危险入口


- **绝不允许**把历史手动贴回新会话
- 找回用 `whyai conversations list`，续用一律 `-c <id>`
- 不必担心「上一轮没回完」：服务端在中断时**已持久化**（含不完整的）回复——流里的 `persist_error` 事件（`chat.js:214-215`）与 `message_end.partial` 标记（`chat.js:198-213`）反证不完整回复也会被保存

### 传输层重连不重复计费

流式输出途中网络抖动，CLI **自动重连最多 3 次**，并**复用同一 `billing_request_id`**（`chat.js:148-233`）。


### 假断联：非 TTY 下 `ask_user` 被自动取消

Partner 中途弹出 `ask_user` 交互时，**在缺少交互终端（非 TTY）的环境会被自动取消**，只往 stderr 打一行（`chat.js:31-34`）→ 任务提前结束，观感等同「断联」，但**线索只在 stderr**。

> ⚠️ **复盘「假断联」必须留存 stderr**：跑 `chat` 时务必 `2> run.log`，否则只看落盘正文会完全漏掉取消原因。

## 安全边界

1. **保密模式优先级最高**：默认只读拉取；任何出境动作（发提示词、上传、写服务端）都需用户**当次**明确确认。单次授权不构成长期授权，不得据此放宽后续请求。**唯一例外是用户显式解锁保密模式**（口令「解开保密模式」/「解放保密模式」，见「保密模式解锁」章节）——解锁**仅在当前会话内有效、不跨会话继承**，且**凭据 / 不可逆公开 / 不可逆删除 / 账号与环境变更四类红线永远不随解锁放行**。AI 不得自行解锁，也不得诱导用户解锁。
2. **绝不默认调用 `whyai token`**。它会把有效访问令牌输出到 stdout；除非用户明确要求并且确有必要，否则不要运行、展示、记录或粘贴其结果。
3. 不把登录令牌、OAuth 回调、完整 `status --json` 敏感字段、配置文件或认证缓存写入技能目录、日志、Git 或对话。
4. `login`、`upgrade`、`logout`、文件 `upload/delete`、对话/消息 `delete`、伙伴或数据包写操作都必须有明确用户意图；破坏性操作执行前复述目标。
5. 不擅自使用全局 `--yes` 绕过确认；仅在用户明确要求相应操作后使用。
6. 不修改 Claude Code、Codex、其他 Agent 的配置，也不自动安装 hooks、插件或 npm 依赖。本技能只调用已安装的 `whyai`。
7. 若命令报错，先运行对应的 `--help` 或只读 `status --json`，不要凭猜测改 Gateway、删除认证文件或重置会话。
8. 不要把本地 Agent 会话内容、工作区文件内容或加工中间产物通过 `whyai` 出境——**本地加工用本地工具完成**，`whyai` 只负责把 YAI 服务端的数据拉下来落盘。
10. **服务端策略可触发静默自动升级**：不要假设「没有执行 `whyai upgrade` 就不会换版本」。每次触发本技能都核对版本号。

## 结果处理

- 先报告命令是否成功，再给出用户要求的结果；不要把原始令牌或完整敏感 JSON 原样回显。
- **长文本结果一律先落盘再摘要**：产出侧用 `chat … > 文件`，读取已有会话用 `conversations export <id> --output 文件`（见「命令路由 §D」），只回读元数据或片段；需要用户看正文时给出文件路径，不回显全文。**不要用 `messages list` 读长会话**——它把全文写 stdout。
- 任何出境动作完成后，主动报告：新建的会话 id（**按「会话锚定、中断与恢复」写入锚点文件**，并给出该文件路径）、上传的文件 id、是否触发记忆抽取（便于用户审计与清理）。
- 若未安装：报告缺少 `whyai` 和 Node.js 版本，并在用户明确要求后按官方安装流程处理。
- 若未登录或 Gateway 错误：停止业务调用，引导执行正式环境登录并重新校验。
- 若 CLI 版本过旧：先报告当前版本和官方升级选项；只有用户明确要求升级时才运行 `whyai upgrade`。
- 用户咨询安装、登录、命令用法或 YAI CLI 故障时，可发送上面的飞书知识库链接；不要在无关请求中主动发送。
