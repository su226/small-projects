#!/usr/bin/python3
'''
sili - 解析B站视频
'''
from collections import namedtuple
from html.parser import HTMLParser
import html
import json
import requests

__all__ = ["INFO_API_URL", "VIDEO_API_URL", "BANGUMI_PLAY_URL", "HTML_PARSER",
  "get_avid_from_epid", "get_video_info", "get_video_links", "UserInfo",
  "VideoInfo", "VideoStat", "PartInfo", "DownloadInfo", "FileInfo", "Vec2"]

# 获取视频信息 (包括分P信息) 的接口, 返回JSON
INFO_API_URL:str = "https://api.bilibili.com/x/web-interface/view?aid={avid}"
# 获取视频地址的API, 返回JSON, 由Cookies中的SESSDATA决定用户
VIDEO_API_URL:str = "https://api.bilibili.com/x/player/playurl?avid={avid}&cid={cid}&qn={quality}"
# 播放番剧/电影/电视剧的页面，用于获取AVID
BANGUMI_PLAY_URL:str = "https://www.bilibili.com/bangumi/play/ep{epid}"

UserInfo = namedtuple("UserInfo", ["uid", "name", "avatar"])
VideoInfo = namedtuple("VideoInfo", [
  "avid", "title", "time", "description", "cover", "owner", "stat", "parts"])
VideoStat = namedtuple("VideoStat", [
  "view", "like", "coin", "favorite", "share", "danmaku", "comment"])
PartInfo = namedtuple("PartInfo", [
  "cid", "title", "duration", "size"])
DownloadInfo = namedtuple("DownloadInfo", ["quality", "duration", "files"])
FileInfo = namedtuple("FileInfo", ["duration", "size", "links"])
Vec2 = namedtuple("Vec2", ["x", "y"])
class Error(Exception): pass
class ApiError(Error):
  def __init__(self, code):
    super().__init__(code)
    self.code = code
class VideoNonExist(Error): pass

class AvidParser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.avid = None
    self.started = False

  def handle_starttag(self, tag, attrs):
    if ("class", "av-link") in attrs:
      self.started = True

  def handle_data(self, data):
    if self.started:
      self.avid = int(data[2:])
      self.started = False


def get_avid_from_epid(epid:int) -> int:
  '''从EPID获取AVID'''
  assert 0 < epid < 0x80000000
  response = requests.get(BANGUMI_PLAY_URL.format(epid=epid))
  if response.status_code == 404:
    raise VideoNonExist(f"ep{epid}")
  response.raise_for_status()
  # TODO: 我希望终有一天摆脱对解析HTML的依赖
  parser = AvidParser()
  parser.feed(response.text)
  return parser.avid

def get_video_info(avid:int) -> VideoInfo:
  '''获取视频信息'''
  assert 0 < avid < 0x80000000
  response = requests.get(INFO_API_URL.format(avid=avid))
  response.raise_for_status()
  data = response.json()
  if data["code"] == -404:
    raise VideoNonExist(f"av{avid}")
  elif data["code"] != 0:
    raise ApiError(data["code"])
  parts = []
  for part in data["data"]["pages"]:
    parts.append(PartInfo(
      title=part["part"],
      cid=part["cid"],
      duration=part["duration"],
      size=Vec2(
        part["dimension"]["width"],
        part["dimension"]["height"])))
  return VideoInfo(
    avid=avid,
    title=data["data"]["title"],
    time=data["data"]["pubdate"],
    description=data["data"]["desc"],
    cover=data["data"]["pic"],
    owner=UserInfo(
      uid=data["data"]["owner"]["mid"],
      name=data["data"]["owner"]["name"],
      avatar=data["data"]["owner"]["face"]),
    stat=VideoStat(
      view=data["data"]["stat"]["view"],
      like=data["data"]["stat"]["like"],
      coin=data["data"]["stat"]["coin"],
      favorite=data["data"]["stat"]["favorite"],
      share=data["data"]["stat"]["share"],
      danmaku=data["data"]["stat"]["danmaku"],
      comment=data["data"]["stat"]["reply"]),
    parts=tuple(parts))

def get_video_files(avid:int, cid:int, quality:int=120, session:str=""):
  response = requests.get(
    VIDEO_API_URL.format(avid=avid, cid=cid, quality=quality),
    cookies={"SESSDATA": session})
  response.raise_for_status()
  data = response.json()
  if data["code"] == -404:
    raise VideoNonExist(f"av{avid}")
  elif data["code"] != 0:
    raise ApiError(data["code"])
  files = []
  for i in data["data"]["durl"]:
    files.append(FileInfo(
      duration=i["length"],
      size=i["size"],
      links=tuple([i["url"]] + i["backup_url"])))
  return DownloadInfo(
    quality=data["data"]["quality"],
    duration=data["data"]["timelength"],
    files=tuple(files))
