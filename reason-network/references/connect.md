# 接入与排障

本页只收录可重复使用的分流。以当前 `reason network --help`、MCP 工具说明和[官方接入页](https://reasonmachines.com/network)为准。历史实测记录中的版本、在线会话和命令可能已过期。

## 用户电脑上的编码 Agent

```text
已有 MCP 工具？ ── 是 → list_team → 核对当前会话
       │
       否
       ↓
本机有 reason CLI？ ── 是 → reason network who → 检查机器与会话
       │                                      └→ 未加入：reason network join '<用户当次给的完整邀请链接>'
       否
       ↓
打开官方接入页，按当前平台安装并登录；重开目标 Agent 会话
```

macOS/Linux 官方安装示例：`curl -fsSL https://reasonmachines.com/install.sh | bash -s -- network`。Windows 官方接入页给出 PowerShell 命令；先从官网核对当前命令，再执行。安装器会打开浏览器登录。若目标宿主没有自动挂载工具，按该宿主当前 MCP 配置方式接入；不要假设安装完成后当前会话立即拥有新工具。

常用命令参考（以实时 `reason network --help` 为准）：

| 目的 | 命令 |
|---|---|
| 看在线会话 | `reason network who --all` |
| 加入用户提供的网络 | `reason network join '<完整邀请链接>'` |
| 单向发送 | `reason network send <person/session> "消息"` |
| 等待回复 | `reason network follow <消息ID> --timeout 60` |
| 收件 | `reason network inbox --wait 45` |
| 查看本机状态和邀请行 | `reason network` |
| 查看实时用法 | `reason network --help` |

若 CLI 因继承的代理环境变量拒绝运行，先读取报错说明；只对该次命令临时移除被点名的代理变量，或按 CLI 指引使用受支持的代理配置。不要全局改用户的网络设置，也不要把密钥打印出来。

## 托管助手

官方远程 MCP 地址为 `https://mcp.reasonmachines.com/mcp`。在宿主支持自定义 MCP/连接器时，使用宿主设置接入并走用户登录；不要在云端 shell 安装本机 daemon。连接后调用 `list_team`，确认用户电脑已有在线 Reason Network 节点及目标会话。宿主不支持自定义 MCP 时，报告能力缺口，让用户通过本机 Agent 转达，不假装能直接投递。

## 常见误判

| 现象 | 判断与处理 |
|---|---|
| `who` 看到了机器，看不到目标 WorkBuddy 等会话 | 机器加入不等于宿主会话挂载。检查目标宿主是否提供 Reason MCP；必要时重启宿主并让目标会话发一条身份探针。 |
| 只看到 `terminal` 或另一个 Agent 会话 | 不能把它当成用户指定的 Agent。停止交接并报告当前可见地址。 |
| 发送结果是 `queued` | 收件方可能是 pull 模式。让它调用 inbox；用 message_status 复核，不反复重发。 |
| 发送后发现交给了错误 Agent | 立即发引用原 ID 的取消消息，并告知用户；不声称旧消息已被服务器撤销。 |
| 没有 `mcp__reason_network__*` 工具 | 检查会话启动时是否挂载 MCP；重新打开会话或重载宿主配置，再列团队。 |
| `reason network who` 无对方 | 对方未上线、未登录或不在同一网络。请对方报当前地址，必要时用当次邀请链接加入。 |

`reason network serve` 会启动一个新的常驻 Agent。仅在用户明确要求建立独立常驻接收者时使用；它不能替代 WorkBuddy、DSH 等指定宿主里的原会话。
