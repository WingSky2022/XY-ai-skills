# reason-network

> **版本**：v1.0.1

指导 Agent 把当前会话接入 Reason Network，并完成跨 Agent 交接、收信、等待与排障。技能强调“机器入网”和“指定会话在线”的区别，避免把消息误发给同机的终端或其他 Agent。

## 文件

- `SKILL.md`：触发、路由、身份核对、消息纪律与权限边界。
- `references/connect.md`：本机 CLI、远程 MCP 和常见故障的接入分流。
- `CHANGELOG.md`：版本记录。

## 来源与安装

- **上游项目**：[reason-machines/reason-network](https://github.com/reason-machines/reason-network)（官方仓库；本技能为按协作需求原创编写，未复制上游技能包）
- **官方接入页**：https://reasonmachines.com/network
- **远程 MCP**：`https://mcp.reasonmachines.com/mcp`（托管助手用）

**首次安装**（Agent 检测到本机无 `reason` CLI 且无 MCP 工具时，先咨询用户，经同意后再执行）：

```sh
# macOS / Linux
curl -fsSL https://reasonmachines.com/install.sh | bash -s -- network

# Windows（PowerShell）
irm https://reasonmachines.com/network/install.ps1 | iex
```

安装器会打开浏览器登录（免费：Google / GitHub / Apple / 邮箱）。加入已有网络用邀请链接：`curl -fsSL https://reasonmachines.com/install.sh | bash -s -- network join '<邀请链接>'`。安装后重开 Agent 会话使 MCP 工具挂载生效。详细分流见 [`references/connect.md`](references/connect.md)。

安装和 Agent 分发由用户通过现有技能管理流程决定；本目录不保存邀请链接或凭证。
