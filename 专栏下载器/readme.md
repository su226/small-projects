# B站专栏下载器
展示视频: [av81542179|【Python】【效果展示】使用Python+Requests+BeautifulSoup的B站专栏下载器](https://www.bilibili.com/video/av81542179)

下载B站上的专栏，并将其转化为合适的格式，风格采用[Material Design](https://material.io)

B站专栏可以添加视频卡片、专栏卡片、番剧卡片等外部内容，本软件目前只支持视频卡片

dl.py - 主程序
sili - 原名biliparse，用于解析B站视频，获取封面
template.html, article.css, article.js - 输出专栏的模板

## 安装
本软件需要BeautifulSoup和Requests这两个第三方库

可以使用pip或者对应系统的软件包管理器进行安装
```shell
pip install beautifulsoup4 requests
```

## 用法
```shell
./dl.py cv1234567
./dl.py 1234567
```
这两种方式都会下载cv1234567