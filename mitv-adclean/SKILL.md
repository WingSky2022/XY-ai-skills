---
name: mitv-adclean
description: |
  小米/红米电视去广告改造技能：Agent 经 Wi-Fi ADB 停用广告/遥测组件 + 电视静态 DNS 指向过滤 DNS，
  去除开机广告与弹窗贴片。全程无 root、只做可逆操作、停用前预览清单必须经用户确认。
  适用：小米/红米电视（含老款 Android 6 固件）；其他安卓系 TV 走品牌扩展协议（见技能内「品牌扩展协议」节）。
  已验证机型见 references/cases/。
  触发词："电视去广告"、"小米电视广告"、"开机广告"、"改造电视"、"cleanyourtv"、"tv detox"、"电视 ADB"。
  红线：① 永不停用 com.mitv.tvhome / systemui / settings / providers（黑屏风险）；② 停用清单先给用户过目，
  确认后才执行；③ 只用可逆命令（pm uninstall -k --user 0 / pm install-existing / DNS 改回自动）。
version: 1.2.0
author: WingSky
---

# mitv-adclean · 小米电视去广告

让 Agent 通过 Wi-Fi ADB 完成小米电视去广告改造。Agent 负责探测、清单、执行、验证；用户只按遥控器配合。

## 适用边界（三档）

| 范围 | 适用度 | 说明 |
|---|---|---|
| 小米/红米全系（含最新款） | ✅ 直接适用 | 候选包清单现成；新固件上 `disable-user` 通常直接成功、开机广告多有官方开关、Android 8+ 可选换桌面路线，由探测+降级结构自动适配 |
| 其他安卓系 TV（索尼/TCL/海信/Google TV 盒子等） | ⚠️ 骨架适用，清单需品牌扩展 | Phase 0-6 流程原样可用；候选包名按品牌重建，走下方「品牌扩展协议」 |
| 非安卓 TV（三星 Tizen / LG webOS） | ❌ 不适用 | 无 ADB，工具体系完全不同 |

已验证机型档案见 `references/cases/`（每台电视一份，跑通即追加）：
- `xiaomi-mitv4-anms0-android6.md`（小米电视4，Android 6.0.1，2026-10-24）

## 品牌扩展协议（自进化机制）

碰到**非小米**的安卓系 TV 时，不要套用小米清单。按以下协议走，把本技能进化到该品牌：

1. **触发**：Phase 2 采集到 `ro.product.brand` 非 Xiaomi/Redmi（或小米清单明显不匹配）。
2. **打招呼（必须）**：向用户说明——当前电视是 <品牌>，技能尚无该品牌案例；建议进入品牌扩展流程：联网调研该品牌的社区去广告清单（CleanYourTV 的分品牌列表、GitHub 搜 `<品牌> TV debloat adb` 等），重建候选包骨架后再执行。**用户明确同意后才继续**；不同意则只做诊断汇报，不动系统。
3. **调研**：交叉验证 ≥2 个来源（GitHub 社区清单 + 包名特征 ad/analytics/statistic/push/telemetry），生成该品牌候选清单；同时确认该品牌的系统骨架包（launcher/systemui/settings/providers，列入红线）。
4. **执行**：走标准 Phase 3-6（断网诊断 → 清单预览确认 → 停用 → DNS → 验证），红线与可逆原则不变。
5. **沉淀**：跑通后复制 `references/cases/_TEMPLATE.md` 新建 `<品牌>-<型号>-<安卓版本>.md`，回填实测行为与生效配置，并在上方索引表登记一行。若该品牌差异大到需要独立章节（如设置路径完全不同），可在本文件「品牌差异」小节追加要点。
6. **私有数据**：该用户的设备信息记入 `config.json`（本地自建，见「私有配置」节），不入案例档案。

## 私有配置（config.json，本地自建）

你可以在技能目录下自建一个 `config.json` 存放**自家环境数据**（电视 IP/型号、网关路由器、已执行措施、遗留事项）。
Agent 执行前先读它：电视地址、网段、已停包清单直接复用，避免重复探测；执行后把新状态回写进去。
技能文档（本文件与 references/）只保留通用知识，**不要把私人 IP、路由器型号等实例数据写进文档与案例档案**。

## 前置条件（电脑侧）

1. `which adb` 检查。没有则装：macOS `brew install android-platform-tools`；Windows 装 Google platform-tools。
2. 电脑与电视连同一网段（电视 ADB 端口为 5555）。
3. 遥控器在用户手上——多个步骤需要电视端操作。

## 流程总览

```text
Phase 0 扫描定位电视 → Phase 1 引导开 ADB → Phase 2 连接采集信息
→ Phase 3 断网重启诊断（缓存 vs 联网）→ Phase 4 停用清单预览+确认+执行
→ Phase 5 DNS 过滤设置 → Phase 6 验证固化 → 闲置期回滚口令备查
```

## Phase 0 · 扫描定位

先拿网关与网段：macOS `ipconfig getoption en0 router` 或 `route -n get default`。然后扫 5555：

```sh
python3 - <<'EOF'
import socket, concurrent.futures
def probe(ip):
    s=socket.socket(); s.settimeout(0.4)
    try: s.connect((ip,5555)); return ip
    except Exception: return None
    finally: s.close()
with concurrent.futures.ThreadPoolExecutor(100) as ex:
    print([r for r in ex.map(probe,[f"<网段前缀>.{i}" for i in range(2,255)]) if r])
EOF
```

扫不到 = 电视 ADB 没开（多数小米电视重启后 ADB 自动重置为关）。直接进 Phase 1。

## Phase 1 · 引导用户开 ADB（话术照念）

对用户说（按需调整措辞）：

> 请拿遥控器做两步：
> 1. 「设置 → 关于」，连续点「产品型号」或「版本号」5 次，直到提示进入开发者模式。
> 2. 回到「设置」，找「开发者选项」（部分老机型在「设置 → 账号与安全 → ADB 调试」），打开「网络 ADB 调试」。
> 完成后不用重启，直接告诉我。

授权弹窗提示（首次 connect 后电视会弹窗）：

> 现在电视屏幕上应该弹出了「允许 USB 调试」的确认框，请用遥控器选「允许」（可勾选始终允许）。

⚠️ **每次电视重启后 ADB 会重置为关闭**。重扫连不上时，先请用户重新打开调试开关（关一下再开更可靠），不要反复盲连。话术：

> 电视重启后 ADB 调试一般会被系统自动关掉。麻烦到「开发者选项」里把它关一下再开一次，开完告诉我。

## Phase 2 · 连接与信息采集（只读）

```sh
adb connect <TV_IP>:5555
adb -s <TV_IP>:5555 shell getprop ro.product.model      # 型号
adb -s <TV_IP>:5555 shell getprop ro.build.version.release  # Android 版本
adb -s <TV_IP>:5555 shell pm list packages -s > packages_before.txt  # 存档（回滚对照用）
```

`unauthorized` 状态 = 电视端授权弹窗没确认，回 Phase 1 话术。

## Phase 3 · 断网重启诊断（关键分叉，5 分钟）

对用户说：

> 现在做个 5 分钟实验，判断广告是联网下载的还是存在电视里的：
> 请在电视设置里关掉 Wi-Fi（或拔网线），然后关机再开机，看开机时还出不出广告。
> 注意：短按电源是待机，待机唤醒不算开机；要长按电源键选「重新启动」，或关机后再开。
> 看完把 Wi-Fi 重新连上，告诉我结果：还出广告 / 不出广告。

- 仍出广告 → 本地缓存路径：`pm clear com.mitv.tvhome`（清桌面数据，布局会重置）再试；无效则走「换第三方桌面 + 下线 tvhome」（进阶，见下）。
- 不出广告 → 联网拉取路径（主流）：继续 Phase 4 + Phase 5。

## Phase 4 · 停用清单：预览 → 用户确认 → 执行

候选包（按电视实际清单里存在的提）：

| 类别 | 常见包名 | 说明 |
|---|---|---|
| 系统广告 | com.miui.systemAdSolution | 弹窗/贴片来源 |
| 遥测 | com.miui.tv.analytics | 行为埋点 |
| 统计 | com.xiaomi.statistic | 统计 SDK |
| 推送 | com.xiaomi.mitv.tvpush.tvpushservice | ⚠️ 降价/促销推送通道，用户要收促销就**保留** |

**必须先给用户预览清单**（表格形式：包名 / 作用 / 建议），等用户明确说「开始」才执行。推送这类有取舍的，单独问一句。

执行（先试温和命令，被拒再降级）：

```sh
# 首选（新版系统通常可行）：
adb -s <TV_IP>:5555 shell pm disable-user --user 0 <包名>
# 被拒（SecurityException，老固件常见）→ 降级用户级卸载（APK 保留，可恢复）：
adb -s <TV_IP>:5555 shell pm uninstall -k --user 0 <包名>
```

验证：`pm list packages | grep <包名>` 无输出即成功。

**红线**：永不执行上述命令于 `com.mitv.tvhome`、`systemui`、`settings`、`providers` 系——电视会黑屏。

## Phase 5 · DNS 过滤（联网路径的根治步骤）

对用户说：

> 最后一步，把电视的 DNS 指到带广告过滤的公共 DNS（AdGuard）：
> 「设置 → 网络设置 → 当前 Wi-Fi → IP 设置」，把模式从 DHCP 改为「静态」，然后填：
> IP 地址填电视当前 IP（例如 192.168.x.x），网关填路由器地址，掩码 255.255.255.0，
> DNS1 填 94.140.14.14，保存。
> 注意：一定要切到「静态」模式再填 DNS——DHCP 模式下填的 DNS 重启后会被路由器覆盖回去。
> 如果只有一个 DNS 输入框，就只填这一个，不用填备用。

保存后请用户重启电视（长按电源 → 重新启动）验证。

## Phase 6 · 验证与固化

电视重启后 ADB 又关了，先请用户重开（Phase 1 话术）。然后：

```sh
adb -s <TV_IP>:5555 shell getprop net.dns1        # 应显示 94.140.14.14
adb -s <TV_IP>:5555 shell "ping -c1 -W2 ad.xiaomi.com"   # 应解析到 127.0.0.1（被拦截）
adb -s <TV_IP>:5555 shell "ping -c1 -W2 www.mi.com"      # 对照：正常解析
```

广告有无以**用户真重启后肉眼观察**为准（短按待机不算）。同时问一句日常 App 是否正常，防误伤。

若 `net.dns1` 显示路由器 IP = 静态配置没保存成功，回 Phase 5 话术重走；仍不行 → 路由器 DHCP 全局下发 DNS 或自建 AdGuard Home（进阶）。

## 回滚（完整可逆）

```sh
# 恢复被停用的包：
adb -s <TV_IP>:5555 shell pm install-existing --user 0 <包名>
# DNS：电视网络设置改回「自动/DHCP」即可。
```

应急：若电视「联网但内容全打不开」，优先怀疑过滤 DNS 不可达，DNS 改回自动即恢复。

## 常见坑速查

| 现象 | 原因 | 处置 |
|---|---|---|
| connect 后 unauthorized | 电视授权弹窗未确认 | 让用户遥控器点允许 |
| 扫描无 5555 | 重启后 ADB 自动关 | 让用户关-再开调试开关 |
| disable-user 报 SecurityException | 老固件 shell 权限收紧 | 降级 `pm uninstall -k --user 0` |
| `adb root` 报 production builds | 正常，生产固件不给 root | 不需要 root，别再试 |
| DNS 填了不生效 | 在 DHCP 模式下填，重启被覆盖 | 切「静态」IP 模式再填 |
| 用户说"重启了没广告"但用的是短按电源 | 短按=待机唤醒，不走开机流程 | 要求长按电源→重新启动 |
| logcat 挖不到广告 URL | 缓冲区小，开机日志易轮转 | 靠断网诊断 + DNS 查询日志，别死磕 logcat |
| GitHub 直连超时 | 网络环境 | 下载走 gh-proxy.com 等镜像 |

## 进阶（默认不做，用户提出再做）

1. **视频流内嵌广告 / 贴片根治**：公共过滤 DNS 只能拦通用广告域（小米自家族已覆盖），爱奇艺 cupid 贴片族等需自建 AdGuard Home 定制清单。完整方案见 `references/adguard-home-gatekeeper.md`（监控→门卫两阶段、Docker 部署命令、预定位清单、常驻必要性、DoH 边界）。前提：家中有一台局域网常开设备（NAS/树莓派/软路由）。
2. **换桌面路线**（广告是本地缓存时的根治法）：装兼容机型 Android 版本的第三方桌面（guizang-tv 需 Android 8+；Android 6 需选低版本 minSdk 的 launcher），设为默认 HOME 后可 `pm uninstall -k --user 0 com.mitv.tvhome`；黑屏恢复 = `pm install-existing --user 0 com.mitv.tvhome`。
3. **官方通道**：小米客服 400 可登记关闭开机广告（零风险，与上述方案不冲突，可并行）。

## 收尾必做

1. 汇报最终态：停了哪些包 / DNS 状态 / 验证证据 / 回滚口令。
2. 若是新机型首次跑通：复制 `references/cases/_TEMPLATE.md` 新建案例档案并回填，在「适用边界」索引表登记；该用户的私有设备信息写入自建的 `config.json`。若走了品牌扩展协议，同时更新本文件的索引与（如需）品牌差异小节——这是本技能跨品牌泛化的核心资产。
