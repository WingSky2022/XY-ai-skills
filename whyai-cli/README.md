# whyai-cli — 让 AI 帮你操作 YAI

> 📦 **首次安装**？让 AI 阅读本文件，按「安装」一节完成配置即可。

把 [YAI CLI](https://ai.yitang.top/cli)（命令 `whyai`）封装成一个技能：**在你授权后，由 AI 助手替你操作 YAI** —— 查账户与用量、读会话与笔记、发起对话、管理文件。

## 能做什么

- **查**：登录状态、账户、模型清单、配额与用量、会话 / 笔记 / 记忆
- **聊**：发起 YAI 对话、继续已有会话、联网搜索、挂载 Partner（角色）
- **管**：上传与下载文件、整理笔记、清理服务端记忆
- **省**：长回复默认落盘、只读摘要，不把全文灌进对话上下文

## 安装

**前置**：Node.js 20 或更新版本。

**1. 安装 CLI**（macOS / Linux）

```bash
cli_tmp="$(mktemp -d)"
curl -fsS https://ai.yitang.top/cli/install.mjs -o "$cli_tmp/install.mjs"
node "$cli_tmp/install.mjs"
export PATH="$HOME/.local/bin:$PATH"
whyai --version
```

Windows 见官方页面对应的 PowerShell 命令。

**2. 登录**（浏览器一键 SSO）

```bash
whyai login --gateway https://ai.yitang.top
whyai status --json     # 确认 logged_in: true 且 environment: prod
```

**3. 装技能**：把本目录放到你的 Agent 技能目录下即可（例如 `~/.workbuddy/skills/whyai-cli/`）。

业务功能需要有效的 YAI 套餐；仅安装与登录不需要。

## 激活提示词

装好后，直接对 AI 说下面这些话就会触发本技能：

| 你想做什么 | 这样说 |
|:--|:--|
| 查账户与配额 | 「用 whyai 看看我的账户和配额」 |
| 看有哪些模型 | 「whyai 现在有哪些模型可以调」 |
| 列历史会话 | 「用 whyai 列一下我最近的会话」 |
| 继续某个会话 | 「用 whyai 接着刚才那个会话，问它……」 |
| 挂角色对话 | 「用 whyai 挂一个角色，帮我研究……」 |
| 导出会话全文 | 「把那个 whyai 会话导出到文件」 |
| 排查用量异常 | 「我这个月 whyai 的额度怎么用得这么快」 |

也可以直接说「**用 YAI 帮我……**」—— 技能会在授权范围内挑选合适的命令。

## 使用前的两条约定

1. **保密模式（默认开启）**：技能默认**只从 YAI 拉取数据，不把你的本地内容推出去**。当需要发消息或上传文件时，AI 应当先说明「将发送什么」并征得你同意。
2. **想免去逐次确认**：如果你信任当前这轮对话，可以对 AI 说「**解开保密模式**」—— 本会话内不再逐次询问；但涉及令牌输出、不可逆删除、内容转为公开、账号与环境变更这四类操作，**仍需单独确认**。该授权**不跨会话继承**。

## 目录结构

| 文件 | 作用 |
|:--|:--|
| `SKILL.md` | 技能主体：保密模式、出境确认、命令路由、安全边界 |
| `references/model-catalog.json` | 可用模型清单与默认模型策略 |
| `README.md` | 本文件 |

## 出问题怎么办

- 命令报未登录 / Gateway 不对 → 重新执行 `whyai login --gateway https://ai.yitang.top`，再用 `whyai status --json` 复核
- 提示套餐无资格 → 业务命令需要有效订阅，先确认套餐状态
- 其他异常 → 先跑 `whyai --help` 或对应子命令的 `--help` 看用法，不要凭猜测改动配置
