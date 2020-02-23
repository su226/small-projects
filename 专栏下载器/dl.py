#!/usr/bin/python3
from urllib.parse import quote
import sili
import bs4
import requests
import os
import shutil
import sys
import time

# 建立下载目录
if len(sys.argv) != 2:
  print("需要一个参数")
  exit(1)
cid = sys.argv[1]
if not cid.startswith("cv"):
  cid = "cv" + str(cid)
dst = cid + os.path.sep
if not os.path.exists(cid):
  os.mkdir(cid)

def path(name):
  return dst + name.replace("/", os.path.sep)

def download(url, name):
  name = path(name)
  dirname = os.path.dirname(name)
  if dirname != "" and not os.path.exists(dirname):
    os.mkdir(dirname)
  data = requests.get(url)
  with open(name, "wb") as f:
    f.write(data.content)

def copy(src):
  shutil.copy(src, dst + src)

# 获取专栏
html = requests.get("https://www.bilibili.com/read/" + cid).text
soup = bs4.BeautifulSoup(html, "html.parser")

title = soup.find("h1", class_="title").text
banner = soup.find(itemprop="image")["content"]
tags = tuple(map(lambda x: x.text, soup.find_all(class_="tag-content")))
author_tag = soup.find(class_="author-name")
author_name = author_tag.text
author_id = author_tag["href"].split("/")[-1]
avatar = "https:" + soup.find(class_="up-face-image")["data-face-src"]

print("标题", title)
print("头图", banner)
print("标签", ", ".join(tags))
print("作者", author_name, "(UID {})".format(author_id))
print("头像", avatar)

print("下载头图")
download(banner, "banner.jpg")
print("下载头像")
download(avatar, "avatar.png")
article = soup.select_one(".article-holder")
article.name = "article"
del article["class"]

# figure
def proc_img(figure, img):
  # 图片标题
  figcaption = figure.figcaption
  if figcaption.text == "": figcaption.decompose()
  else: del figcaption["contenteditable"]
  # 下载图片
  url = "https:" + img["data-src"]
  name = "images/" + url.split("/")[-1]
  print("下载图片", url)
  download(url, name)
  # 设置图片链接
  img["src"] = name
  del img["width"]
  del img["height"]
  del img["data-size"]
  del img["data-src"]

def make_video_card(avid):
  print("获取视频信息", "av" + str(avid))
  info = sili.get_video_info(avid)
  cover_name = "videos/" + info.cover.split("/")[-1]
  print("下载视频封面", info.cover)
  download(info.cover, cover_name)
  markup = '''<a no-link href="https://www.bilibili.com/video/av{avid}"><figure video-card>
  <img video-cover src="{cover}">
  <div card-container>
    <div video-owner>{owner} - {time}</div>
    <div video-title>{title}</div>
    <div video-data>{view}观看 {like}赞 {coin}硬币 {share}转发 {danmaku}弹幕 {comment}评论</div>
  </div>
</figure></a>'''.format(avid=avid, cover=cover_name, owner=info.owner.name, title=info.title,
    time=time.strftime("%Y-%m-%d", time.localtime(info.time)), view=info.stat.view, like=info.stat.like,
    coin=info.stat.coin, share=info.stat.share, danmaku=info.stat.danmaku, comment=info.stat.comment)
  return bs4.BeautifulSoup(markup, "html.parser")

def proc_vid(fig, img):
  avids = img["aid"].split(",")
  for avid in avids:
    card = make_video_card(avid)
    fig.insert_after(card)
  fig.decompose()

MATERIAL_HR = False
def proc_hr(fig, img):
  if MATERIAL_HR:
    hr = bs4.Tag(name="hr")
    fig.replace_with(hr)
  else:
    url = "https:" + img["data-src"]
    name = "dividers/{}.png".format(url.split("/")[-1])
    if not os.path.exists(path(name)):
      print("下载分割线", url)
      download(url, name)
    hr = bs4.Tag(name="img", attrs={"src": url, "hr": None})
    fig.replace_with(hr)

figs = article("figure", class_="img-box")
for i, fig in enumerate(figs, 1):
  print("处理卡片 {}/{}".format(i, len(figs)))
  img = fig.img
  clz = img.attrs.get("class", [])
  clzlen = len(clz)
  del fig["contenteditable"]
  del fig["class"]
  if clzlen == 0:
    proc_img(fig, img)
  elif clz[0].startswith("cut-off-"):
    proc_hr(fig, img)
  elif "video-card" in clz:
    proc_vid(fig, img)
  else:
    print("未知卡片")

# 对齐
for i in ("left", "right", "center"):
  for j in article("p", style="text-align: {};".format(i)):
    del j["style"]
    j["talign"] = i[0]

# 文本尺寸
for i, j in ((12, 1), (16, 2), (20, 3), (23, 4)):
  for k in article("span", class_="font-size-" + str(i)):
    del k["class"]
    k["tsize"] = str(j)

# 文本颜色
for i, j in (
  ("blue", (300, 500, 800, 900)),
  ("lblue", (200, 300, 700, 800)),
  ("green", (300, 400, 500, 800)),
  ("yellow", (300, 500, 700, 900)),
  ("pink", (200, 300, 600, 800)),
  ("purple", (200, 300, 400, 500)),
  ("gray", (300, 500, 700))
):
  for k, l in enumerate(j, 1):
    for m in article.find_all("span", class_="color-{}-{:02}".format(i, k)):
      del m["class"]
      m["fg"] = i + str(l)
for m in article.find_all("span", class_="color-default"):
  del m["class"]
  m["fg"] = "gray900"

tags_html = ""
for i in tags:
  tags_html += '<a tag href="https://search.bilibili.com/article?keyword={}">{}</a>'.format(quote(i), i)
copy("article.css")
copy("article.js")
with open("{}{}.html".format(dst, cid), "w") as f, open("template.html") as t:
  f.write(t.read().format(
    title=title, content=article, uid=author_id,
    author=author_name, tag=tags_html))
