# 仿Minecraft的闪烁标语

在桌面背景上显示一个类似与Minecraft主界面的闪烁标语。

## 使用方法

1. 确保已安装Python 3、GTK 3和PyGObject
2. 创建配置文件
3. 启动！（注意本程序不会改变窗口层次，所以如果要显示在conky之上，就要比conky后启动）

## 配置文件

配置文件是同名的json文件，比如`splash.py`→`splash.json`，注意配置项缺一不可。

```json
{
  "x": 0,
  "y": 0,
  "width": 0,
  "height": 0,
  "shadow": 0,
  "angle": -20,
  "halign": 0.5,
  "valign": 0.5,
  "color": "FFFF00",
  "shadow_color": "888800",
  "max_size": 20,
  "duration": 0.5,
  "min_scale": 0.9,
  "texts": []
}
```

|项目        |类型       |作用                                         |
|------------|-----------|---------------------------------------------|
|x           |int        |窗口横坐标                                   |
|y           |int        |窗口纵坐标                                   |
|width       |int        |窗口宽度                                     |
|height      |int        |窗口高度                                     |
|shadow      |float      |阴影长度                                     |
|angle       |float      |旋转角度，顺时针为正（不是弧度）             |
|halign      |float      |横向对齐，是\[0,1\]中的任意小数，0为左，1为右|
|valign      |float      |纵向对齐，是\[0,1\]中的任意小数，0为上，1为下|
|color       |str        |文字颜色，16进制RGB格式                      |
|shadow_color|str        |阴影颜色，16进制RGB格式                      |
|max_size    |float      |最大字号，实际字号会适应窗口宽度             |
|duration    |float      |动画周期，单位为秒                           |
|min_scale   |float      |动画中文字的最小缩放（最大不会超过1）        |
|texts       |list\[str\]|要显示的文本，每次启动时随机选择             |