# <品牌>-<型号>-<android版本>.md（案例模板，复制本文件改名后填写）

| 项 | 值 |
|---|---|
| 品牌/型号 | （getprop ro.product.brand / ro.product.model） |
| Android | （ro.build.version.release + API level） |
| 固件 | （ro.build.version.incremental 或 display.id） |
| 验证日期 | YYYY-MM-DD |

## 关键命令行为

- `pm disable-user --user 0`：可用 / 被拒（被拒则记下报错）
- `pm uninstall -k --user 0`：可用 / 被拒
- `adb root`：预期拒绝，勿重试
- ADB 重启后是否重置为关：
- 待机 vs 真重启的电源键行为：

## 广告机制实测

- 开机广告由哪个组件播放（logcat 证据）：
- 断网重启判定：本地缓存 / 联网拉取：
- DNS 静态设置是否持久（DHCP 模式下是否被覆盖）：

## 候选包与处置

| 包名 | 作用 | 处置（停用/保留） | 用户取舍依据 |
|---|---|---|---|

## 生效配置与验证证据

（停了什么、DNS 指向、ping 验证、用户真重启观察结果）

## 未走通 / 未尝试

（路由器能力、日志探测结论、其他死路——防止后人重踩）

## 参考

（该品牌有用的 GitHub 项目/社区清单链接）
