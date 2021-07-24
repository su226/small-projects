# 星露谷整合包管理器

轻松管理星露谷物语SMAPI的Mod：在不同存档中使用不同的Mod、随时切换美化包、搭建编写Mod时的调试环境……

## 使用方法

首先确保已安装Python 3、GTK 3和PyGObject。

将ModpackManager.py放到游戏目录（默认是`~/.steam/root/steamapps/common/Stardew Valley`），在Steam中设置启动参数为`./ModpackManager.py %COMMAND%`。

Windows上可以直接下载ModpackManager.exe，不需要额外的依赖（就是有点大），另外启动参数应该改成`ModpackManager %COMMAND`。

在管理界面中点击左上角的“+”按钮创建整合包，不同整合包之间的存档和Mods是独立的（不支持云同步），存放在游戏目录下的Modpacks文件夹。将需要的Mod放入Mods文件夹，然后点击“✏️”按钮启用你想要的Mod，最后点击“▶️”按钮启动游戏。

