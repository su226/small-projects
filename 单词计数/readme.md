# 单词计数
展示视频: [av88455400 【Python × 数据可视化】克苏鲁神话中什么单词最多？](https://www.bilibili.com/video/av88455400)

使用html.parser和curses做的一个简单的终端动画，用柱状图的形式展示出各个单词的数量

其原理非常简单，就是读取EPUB内的XHTML文件，然后以空格拆分得到单词

在我看了视频[av87161700 克苏鲁神话怪物神灵体型排行](https://www.bilibili.com/video/av87161700)后一时兴起写的一个小东西

# 用法
解压EPUB文件，将内部的XHTML放入Texts目录（如果没有就新建），然后运行
```shell
./animation.py [延时]
```
\[延时\]是指单词与单词之间的延时

洛夫克拉夫特全部作品(英文电子书): https://arkhamarchivist.com/free-complete-lovecraft-ebook-nook-kindle/
