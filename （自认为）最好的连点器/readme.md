# （自认为）最好的连点器

有一天我在玩《精灵与森林》（_Ori and the Blind Forest_）时，想着精灵之火需要一直点左键（长按左键是充能烈焰），就想着能不能做一个连点器来连发左键，于是我就做出来了！

💢~~赛安骂骂咧咧地离开了直播间。~~

## 使用方法

首先安装需要的库，以ArchLinux为例：

```shell
sudo pacman -S python python-pip python-gobject gtk3
pip install PyUserInput
```

连点器的界面分为触发器和操作两个部分：触发器决定何时开始操作，而操作决定执行什么。

### 太长不看或没看懂？

`压榨赛安.json`是一个简单的配置文件，使用导入功能可以直接使用，这个配置文件可以在点击鼠标侧键时连发左键 ~~（适合做什么正如其名）~~。

### 触发器

目前触发器只有一个：按键触发。

#### 按键触发

它有四种模式：按下触发一次、按下触发，松开停止、按下触发，再按停止和按触发键触发，按停止键停止。

前三种模式需要设置触发按键，可以是鼠标或者键盘，第四种模式还需要设置停止键，也可以是鼠标或者键盘。具体的效果就如其名字所述。

如果设置多个按键就相当于设置了一个组合键，只有同时按下才会触发。

### 操作

目前有五种操作：延时、点击键盘、点击鼠标、复制和输入文本。

#### 延时

简单的延时功能，以秒为单位，最多精确到毫秒。

#### 点击键盘

可以点击、按下或松开键盘，支持发送组合键。在点击模式下还能设置点击的次数、每次点击的时长和延时（同样以秒为单位，最多精确到毫秒），但在按下和松开模式下不能设置。

#### 点击鼠标

同上，但不能发送组合键。如果勾选坐标，将会在点击时改变鼠标的位置，否则保持不动。坐标可以直接输入，也可以从屏幕中选择。

#### 复制

复制任意文本。

#### 输入文本

这个模式下可以模拟键盘输入文字，但只能是英文，且不能有换行。（这个功能直接调用PyUserInput实现）如果需要输入非英文，可以考虑先复制，再发送Ctrl+V。

### 底部工具栏

在底部工具栏可以导入和导出设置，格式为JSON。所有的设置需要点击开始按钮后才能生效，开始后可以停止。
