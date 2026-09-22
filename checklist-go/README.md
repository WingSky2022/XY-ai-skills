# checklist-go

将 AI 回复格式化为「1. a. i.」三级嵌套清单体。支持 Claude Code、Codex CLI、Pi CLI。

## ⚠️ 平台差异（重要）

| 特性 | Claude Code | Codex CLI | Pi CLI |
|------|:-----------:|:---------:|:------:|
| 持久生效 | ✅ 自动维持 | ❌ 需手动重激活 | ❌ 需手动重激活 |
| Per-turn 防 drift | ✅ hook 注入 | ❌ | ❌ |
| 关闭方式 | `/checklist-off` | `/checklist-off` | `/checklist-off` |

> **CC 用户**：安装 hook 后一劳永逸，激活后整个会话自动维持清单体格式。
> **Codex / Pi 用户**：每次激活仅当前轮生效，AI 可能逐渐 drift 回普通格式，届时重新输入 `/checklist-go` 即可。

## 文件结构

```
checklist-go/
├── SKILL.md              # CC 技能规则
├── checklist-go.js       # CC UserPromptSubmit hook
├── README.md             # 本文件（安装指南）
└── pi/
    └── SKILL.md          # Codex / Pi 技能规则
```

## 安装

以下操作可交给 AI 执行——将本目录路径告诉 AI，让它按本 README 完成安装。

### Claude Code

1. **复制技能文件**到 CC 全局技能目录：
   ```
   将整个 checklist-go/ 目录复制到 ~/.claude/skills/checklist-go/
   ```
   即 `~/.claude/skills/checklist-go/SKILL.md` 和 `~/.claude/skills/checklist-go/checklist-go.js` 就位。

2. **注册 hook**（强烈推荐，否则无 per-turn 持久能力）：
   编辑 `~/.claude/settings.json`，在 `hooks` 中增加：
   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "node \"<HOME>\\.claude\\skills\\checklist-go\\checklist-go.js\"",
               "timeout": 5
             }
           ]
         }
       ]
     }
   }
   ```
   > 将 `<HOME>` 替换为用户主目录的绝对路径（Windows 如 `C:\\Users\\<用户名>`，macOS/Linux 如 `/home/<用户名>`）。AI 执行时会自动解析。

3. **激活**：在 CC 中输入 `/checklist-go`，即可开始清单体对话。

### Codex CLI

将 `pi/SKILL.md` 复制到 Codex 技能目录：
```
checklist-go/pi/SKILL.md  →  ~/.codex/skills/checklist-go/SKILL.md
```

激活：`/checklist-go`。⚠️ Codex 无 per-turn hook，drift 后需重新激活。

### Pi CLI

将 `pi/SKILL.md` 复制到 Pi 技能目录：
```
checklist-go/pi/SKILL.md  →  ~/.pi/agent/skills/checklist-go/SKILL.md
```

激活：`/checklist-go`。⚠️ Pi 当前为降级版（无 Extension hook），drift 后需重新激活。

## 架构

### Claude Code — Hook 注入（完整版）

通过 CC hooks 实现跨轮次持久生效 + 每 10 轮循环注入防 drift。

```
用户输入 "/checklist-go"
    │
    ├── CC 内置机制：加载 SKILL.md（首轮完整规则）
    │
    └── UserPromptSubmit hook（checklist-go.js）：
            │
            ├── 检测激活命令 → 写标记文件 + 输出完整规则
            ├── 检测关闭命令 → 删标记文件
            └── 标记存在时 → 按计划注入
                    │
                    ├── Turn 1, 10, 20... → 完整规则（~400 token）
                    └── Turn 2-9, 11-19... → 1 句提醒含示例（~50 token）
```

### Codex CLI — SKILL.md 静态注入（降级版）

Codex 无 per-turn hook 机制。通过 SKILL.md 实现手动触发加载，drift 后可重新激活。

### Pi CLI — SKILL.md 静态注入（降级版）

Pi 的 Extension 可实现 per-turn 注入，但开发复杂度高。当前用 SKILL.md 静态注入，后续可升级。

## 使用

| 操作 | CC | Codex | Pi |
|------|:--:|:-----:|:--:|
| 激活 | `/checklist-go` | `/checklist-go` | `/checklist-go` |
| 关闭 | `/checklist-off` | `/checklist-off` | `/checklist-off` |

## 状态文件（CC hook 专用）

| 文件 | 作用 |
|------|------|
| `~/.claude/.checklist-go-active` | 标记模式是否激活 |
| `~/.claude/.checklist-go-counter` | 轮次计数器 |

## 后续增强

### P1: Pi Extension 开发（优先级：高）

将 Pi 从降级版升级为完整版，实现与 CC 相同的 per-turn 注入机制。

**技术方案**：TypeScript Extension，利用 Pi 的生命周期 API
- 注册 `onUserMessage` 钩子，每次用户输入时检测激活/关闭命令
- 维护计数器文件 `~/.pi/.checklist-go-counter`
- 按轮次注入完整规则或简短提醒（同 CC 的 10 轮循环策略）

### P2: Codex plugin 探索（优先级：中）

调查 `codex plugin` 命令是否支持 hook 或生命周期拦截能力。如有，可将 Codex 从降级版升级。

### P3: caveman 状态感知（优先级：低）

checklist-go hook 读取 `.caveman-active` 标记文件，当 caveman 激活时调整提醒内容（避免重复注入冲突）。
