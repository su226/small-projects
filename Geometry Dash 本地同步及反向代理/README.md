# Geometry Dash 本地同步 & 反向代理
我编写这个工具出于两个原因：RobTop 的备份服务器经常抽风，以及 [GDProxy](https://dl.geometrydashchinese.com) 有时会返回 500，导致游戏里时常出现“Something went wrong”，影响游戏体验。

## 主要功能
* 在本地保存备份并在后台自动上传
* 反向代理游戏的 API、音乐下载和音效下载，并为它们设置不同的代理
* 在下载关卡时后台下载所有音乐和音效，实现并行下载音乐和音效
* 在遇到 5xx 错误码时自动重试
* 支持鉴权，可选配置白名单 / 黑名单
* 在使用 GDProxy 时，可选绕过 [NGProxy](https://ng.geometrydashchinese.com) 而直接从 Newgrounds 下载音乐
* 完全可配置

## 使用方法
安装以下依赖

* aiohttp
* loguru
* pydantic

在工作目录下创建配置文件 config.json 并启动，配置项参见下文。

如果你要将服务器暴露在公网上，请考虑设置备份白名单。

（不保证在 Linux 以外的系统上能用）

### 创建客户端
在你想要打开游戏的电脑上打开服务器的链接，比如假设服务器的 IP（或域名）和端口号是 100.100.100.100:12345，在浏览器中打开 http<nolink>://100.100.100.100:12345，你应该看到这样的一条说明。

> 将服务器地址设置为 http<nolink>://100.100.100.100:12345//////

参见 [Cvolton/GMDprivateServer](https://github.com/Cvolton/GMDprivateServer/wiki/Creating-Windows,-Android-and-IOS-Apps) 的说明创建客户端。

如果你使用 HTTP 访问服务器，你**不能**使用 [GDPS Hub](https://gdpshub.com/) 的 GDPS Switcher，因为它会强制将 HTTP 链接转换为 HTTPS，不过你可以使用 [GDHM](https://www.youtube.com/watch?v=WLHXQtv3iYU) 附带的 GDPS Switcher 功能。

你也可以使用附带的 make-windows-client.py 和 make-android-client.py 脚本。（只适用于 2.2）使用这两个脚本时不需要（但允许）使用尾部填充 `/` 补齐长度的链接。

注意 make-android-client.py 只能修改 libcocos2dcpp.so，你需要 [APK Editor Studio](https://github.com/kefir500/apk-editor-studio) 或其他类似工具来修改 APK，详情请参考 Cvolton/GMDprivateServer 的说明。在 make-android-client.py 和 APK Editor Studio 中填入的包名应保持一致，如果需要使用反代的同时使用 Geode，你应该保持包名不变。

### 多设备使用场景
这是我个人的使用场景，我将其中一台电脑作为本地备份的服务器使用，手机和另一台电脑使用 Tailscale 连接到那台电脑，假设作服务器的电脑的 IP 和端口号是 100.100.100.100:12345。

尽管可以让其他设备直接连接到备份服务器作为反代，但有条件应尽量在本地运行反代以提升速度，只在备份时连接到备份服务器，电脑可使用以下方法在游戏启动时自动启动反代服务器。（可惜我并没有找到在手机上这么做的方法，也许可以通过编写 Geode Mod 来达成此目的）

在*另一台*电脑的游戏目录下创建目录 local-backup，在目录中创建 wrapper.sh 并写入以下内容，然后在 Steam 中设置启动参数为 `local-backup/wrapper.sh %command%`。

```bash
#!/bin/bash
DIR="$(dirname $0)"
# 将原始客户端链接到按上文方法制作的客户端（防止在 Steam 更新或检查完整性时恢复）
[ -L GeometryDash.exe ] || ln -sf "$(realpath --relative-to . $DIR)/client.exe" GeometryDash.exe
# 后台启动服务器
(cd $DIR && exec ./gd-local-backup-server.py) &
PID=$!
# 启动游戏并等待结束
"$@"
# 结束服务器
kill $PID
waitpid -e $PID 2> /dev/null
```

目录中还应放入制作好的客户端 client.exe，以及如下配置文件 config.json。

```jsonc
{
    // 注意这两项，其他配置按需求调整即可
    "backup_enabled": false,
    "backup_server": "http://100.100.100.100:12345"
}
```

## 配置文件说明及默认值
注：缺失的项目将使用默认值；复制时请去除注释
```jsonc
{
    "host": "0.0.0.0", // 监听的 IP 地址
    "port": 80, // 监听的端口
    "game_server": "https://www.boomlings.com/database", // 反代的上游服务器
    "game_retry_count": 4, // API 重试次数，null 为无限重试
    "game_retry_4xx": false, // 在 API 返回 4xx 错误码时重试，为 false 时只重试 5xx 错误码
    "game_proxy": null, // API 代理服务器（由于 AIOHTTP 限制，只支持 HTTP 代理）
    "backup_enabled": true, // 是否启用本地备份，设置为 "local" 时将禁用后台上传
    "backup_server": null, // 备份的上游服务器，null 为从游戏服务器获取，对于不可本地备份的用户（黑名单内 / 白名单外）将直接返回此地址，对于可本地备份的用户将在后台上传到此服务器
    "backup_retry_count": null, // 后台上传的重试次数，null 为无限重试
    "backup_retry_interval": 60, // 每次后台上传的间隔
    "backup_retry_4xx": false, // 参见 game_retry_4xx
    "backup_proxy": null, // 参见 game_proxy
    "backup_auth": {
        "type": "blacklist", // blacklist 或 whitelist
        "blacklist": [], // 帐号黑名单，仅当 type 为 blacklist 时可用
        "whitelist": [], // 帐号白名单，仅当 type 为 whitelist 时可用
        "fetch_gjp2": true, // 从游戏服务器自动获取 gjp2（密码的哈希），禁用将忽略 gjp2（不安全）
        "gjp2_override": {} // 手动覆盖指定帐号的 gjp2，可以为一个 SHA1 字符串、"auto"（自动获取）或 "ignore"（忽略 gjp2）
    },
    "song_enabled": true, // 是否反代音乐
    "song_ngproxy": true, // 是否优先使用 NGProxy，当 NGProxy 不可用时回退到原链接下载
    "song_bypass_ngproxy": true, // 在获取原链接时绕过 NGProxy，只保证在使用 GDProxy 时可用
    "song_retry_count": 4, // 下歌的重试次数，null 为无限重试
    "song_retry_4xx": false, // 参见 game_retry_4xx
    "song_proxy": null, // 参见 game_proxy
    "song_info_ttl": 600, // 音乐元数据的缓存时间，单位为秒，过期的缓存会自动删除，null 为永久缓存（不建议设置为 0，会导致下载音乐时获取两次元数据）
    "assets_enabled": true, // 是否反代音效
    "assets_server": null, // 自定义音效服务器，null 为从游戏服务器获取
    "assets_retry_count": 4, // 音效的重试次数，null 为无限重试
    "assets_retry_4xx": false,  // 参见 game_retry_4xx
    "assets_proxy": null, // 参见 game_proxy
    "assets_server_ttl": 600, // 从游戏服务器获取的音效服务器地址的缓存时间，单位为秒，null 为永久缓存（不建议设置为 0，会导致下载音效时获取多次服务器地址）
    "prefetch": true, // 在下载关卡时预载音乐和音效，所有的音乐和音效将会并行下载
    "prefetch_ttl": 600, // 预载文件的保留时长，单位为秒，过期的缓存会自动删除，null 为永久缓存（不建议设置为 0，很显然）
    "prefetch_target_dir": null // 存档目录，在本地运行时建议指定此选项，预载时将会跳过存档目录中已有的音乐和音效
}
```
