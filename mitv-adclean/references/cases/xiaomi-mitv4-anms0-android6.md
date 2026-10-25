# verified-cases · 已验证机型档案

每在一台新电视上跑完流程，追加一节。字段：型号 / 固件 / Android / 包清单差异 / 命令权限行为 / 生效路径 / 日期。

---

## MiTV4-ANSM0（小米电视4，55 寸，2016 款）· 2026-10-24 验证

| 项 | 值 |
|---|---|
| 型号 | MiTV4-ANSM0（Xiaomi） |
| Android | 6.0.1（API 23） |
| 固件 | 3234 |

> 私人实例数据（IP、控制端设备、网关路由器型号、当前已执行措施）不入本档案——档案只记通用行为，实例数据由使用者记录在自建的 `config.json` 里。

### 关键行为

- `pm disable-user --user 0` → SecurityException 拒绝（shell uid 2000 无权改组件状态）。
- `pm uninstall -k --user 0` → 可用。APK 留在只读分区，`pm install-existing --user 0` 可恢复。
- `adb root` → "adbd cannot run as root in production builds"（预期，勿重试）。
- 电视每次重启后 ADB 调试自动重置为关，需用户手动重开（关-再开一次最可靠）。
- 短按电源 = 待机（不走开机流程）；长按电源 → 「重新启动」= 真重启。

### 广告机制实测

- 开机广告由 `com.mitv.tvhome/.BootActivity` 播放（logcat 证据：`BootActivity.sendAdShowBroadcast`，开机约 9 秒后销毁）；广告 SDK `com.xiaomi.ad.*` 嵌在 tvhome 与 mivideoplayer 进程内。
- 断网重启 → 无广告 ⇒ 广告为开机时联网拉取，非本地缓存。
- DHCP 模式下填 DNS1 保存无效（重启被 DHCP 覆盖回路由器 IP）；切「静态 IP」模式后 DNS 持久生效。

### 最终生效配置

1. `pm uninstall -k --user 0`：com.miui.systemAdSolution（APK 位于 /system/vendor/app/AdServer）、com.miui.tv.analytics（/system/app/MiTVBiAnalytics）、com.xiaomi.statistic（/system/vendor/app/MiTVStat）。
2. 保留 com.xiaomi.mitv.tvpush.tvpushservice（用户要收降价/促销推送）。
3. 电视静态 IP + DNS1=94.140.14.14（AdGuard 公共过滤 DNS）。

### 验证证据

- `getprop net.dns1` = 94.140.14.14。
- `ping ad.xiaomi.com` → 127.0.0.1；`ping ad.doubleclick.net` → 127.0.0.1；`ping www.mi.com` → 正常解析。
- 用户真重启（长按→重新启动）后开机广告消失；日常使用正常。

### 未走通 / 未尝试

- 该用户家中路由器无自定义 Hosts / 网站黑名单能力，路由器层过滤路线不可用；DMZ 与此无关，勿开。（常见于运营商定制 / 老款路由器，遇到同类情况可直接跳过路由器层方案。）
- 视频流内嵌广告未根治（需自建 AdGuard Home 定制清单，NAS 常驻方向）。
- 电脑侧 AdGuard Home 因 53 端口需 root 未部署（无免密 sudo）。
- logcat 全缓冲区 URL 挖掘仅得 1 条统计地址，广告 URL 未在日志中出现（缓冲小+轮转）。

### 参考

- CleanYourTV：https://github.com/Gathin23/cleanyourtv（方法论同源：备份→停用→换桌面）
- TV Detox：https://github.com/Ansub/tv-detox
- guizang-tv：https://github.com/op7418/guizang-tv（Android 8+，新机型可考虑）
- miTVhosts 域名清单：https://github.com/liamliu108/miTVhosts
