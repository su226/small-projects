# 贴吧自动签到
## 简介
原脚本tiebaAllSign由congxz6688开发，我在它的基础上对界面和使用体验进行优化，顺便修复了几个bug，比如多个同时打开多个标签页会出错。

## 使用方法
首先确认你的浏览器有安装Tampermonkey或其他用户脚本管理器，然后安装本脚本。

安装完成之后，当你打开百度搜索或者百度贴吧时，如果当天还没有使用本脚本，就会自动开始签到（**包括首次安装**，可以在设置里关闭）。

如果需要手动签到，请点击“✔️️”图标，如果需要更改设置，请点击“⚙️️”图标。目前可以设置签到黑名单、签到间隔（默认是650ms，过小可能会签到失败）、签到浮窗位置（默认在正下方，也可以拖动调节）、是否自动签到。

本脚本在 Chrome 85 和 Firefox 81 上测试通过。如果你的浏览器过旧，可能无法使用，我**不保证**会兼容旧版浏览器，请[升级浏览器](https://support.dmeng.net/upgrade-your-browser.html)。

## 代码&安装
[一键安装](https://cdn.jsdelivr.net/gh/su226/small-projects/贴吧自动签到/贴吧自动签到.user.js) [查看代码](https://github.com/su226/small-projects/blob/master/贴吧自动签到/贴吧自动签到.user.js)<br>
需要安装有Tampermonkey或其他用户脚本管理器
