# 精灵与森林终极版存档备份器

在《精灵与森林终极版》（*Ori and the Blind Forest: Definitive Edition*）存档时自动备份，按Ctrl+Shift+R可还原存档。对于一命通关和速通成就非常有用！

⚠️游戏在死亡时也会存档，因此还原时通常需要选择的不是第一项。

🚫由于本程序使用了inotify和Xlib，只兼容Linux。

💤~~奥里累了，奥里想休息，你有想过吗？没有，你只关心你自己（的全成就）！~~

## 使用方法

首先安装需要的库，以ArchLinux为例：

```shell
sudo pacman -S python python-pip python-xlib python-gobject gtk3
pip3 install inotify
```

然后将SaveHelper.py放到游戏目录中（默认是`.steam/root/steamapps/common/Ori DE`），在Steam中把启动参数设置为`./SaveHelper.py %COMMAND%`。

默认会打开GNOME终端，当备份或还原存档时会以青色高亮输出日志。如果没安装GNOME终端，或者是不想显示，需要将启动参数设置为`./SaveHelper.py --no-terminal %COMMAND%`。
