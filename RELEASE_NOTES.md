# VRC Chatbox 1.4.1

修复 Windows 独立版手机连接时需要手动放行防火墙的问题。

- 启动时自动检查当前程序和 Web 端口的防火墙规则，默认 TCP 5000。
- 首次运行、移动目录或修改端口后，按需请求 Windows 管理员授权。规则保存后不重复授权。
- 仅允许本地子网访问当前程序；防火墙助手单独提升权限，网页服务保持普通权限。
- 取消授权或配置失败时保留本机使用，并在控制台提示；回环绑定不配置规则。

Windows users: startup now checks and configures a persistent LAN-only firewall rule for the current executable and web port. Approve the Windows UAC prompt once when setup is needed. The web server itself is not elevated.

## 下载与升级

下载 `VRCChatbox-1.4.1-Windows.zip`，退出旧版，解压完整文件夹，将旧版 `config` 文件夹复制到新版目录后运行 `VRCChatbox.exe`。必须保留 `_internal` 文件夹，无需安装 Python。

`VRCChatbox-1.4.1-source.zip` 提供对应源码；Windows 包也内附源码。`SHA256SUMS.txt` 提供校验值。

## 验证

19 项测试通过。已实测 Windows UAC 配置与后续免重复授权，并验证打包 EXE 启动及网页 HTTP 200。尚未从实体手机验证连接。程序未代码签名，仅用于可信局域网。
