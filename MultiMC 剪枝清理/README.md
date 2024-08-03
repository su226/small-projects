# MultiMC 剪枝清理

清理 MultiMC 系启动器中未使用的资源和库文件（类似于 `npm prune`），以及 Minecraft 实例产生的日志文件。

参数 `--dry-run` 可用于预览清理的文件。

已在 Linux + Prism Launcher 下测试。

注：内部使用 ctypes 调用 libc 的 wcswidth，使用 Gio 将文件移动到回收站，在其他平台使用时可能需要修改这两部分。
