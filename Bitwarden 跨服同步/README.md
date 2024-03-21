# Bitwarden 跨服同步
本项目可用于跨服务器同步 Bitwarden 密码库，典型使用场景包括将自建的 Vaultwarden 密码库上传到官方服务器作为备份。

本项目为 [martadams89/bitwarden-sync](https://github.com/martadams89/bitwarden-sync) 的重制版，与原版的主要区别有：

* 使用 Python 重写
* 使用 GnuPG 而非 OpenSSL 加密备份
* 快速清空密码库而非逐个删除
* 使用 BITWARDENCLI_APPDATA_DIR 环境变量分隔源帐号和目标帐号的登录凭据

## 依赖项
你需要安装以下 Python 库：

* argon2_cffi
* requests
* loguru

除此之外，PATH 中还应该有 Bitwarden CLI `bw` 和 GnuPG `gpg`。

## 使用方式
打开 sync.py，修改以下内容，其中 Client ID 和 Client Secret 可从网页版密码库中获取，在 `设置 > 安全 > 密钥 > 查看 API 密钥` 中；服务器为 https://vault.bitwarden.com 或者你的自建实例地址。

```python
BACKUP_PASSWORD = ""  # 备份文件的密码（使用 GnuPG 对称加密，AES256）
BACKUP_TTL = 30 * 24 * 60 * 60  # 备份文件的保存时间，单位为秒（过期备份将会删除）

# 源帐号配置
SERVER_SRC = ""
EMAIL_SRC = ""
PASSWORD_SRC = ""
CLIENT_ID_SRC = ""
CLIENT_SECRET_SRC = ""

# 目标帐号配置
SERVER_DST = ""
EMAIL_DST = ""
PASSWORD_DST = ""
CLIENT_ID_DST = ""
CLIENT_SECRET_DST = ""
```

然后运行 sync.py 即可，所有文件将会生成在工作目录下，注意目标帐号的密码库将被**清空**。（尽管清空之前会自动备份，但还请引起注意）

如需要定时备份，请自行设置 cron 或者 systemd.timer。
