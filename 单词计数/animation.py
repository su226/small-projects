#!python3
from collections import defaultdict
from html.parser import HTMLParser
import heapq
import curses
import os
import sys
import time

class WordCounter(HTMLParser):
  CLASS_BLACKLIST = ("sgc-3",)
  TAG_BLACKLIST = ("h2", "a")
  TAG_TRIGGER = "body"
  SYMBOL_BLACKLIST = ",.;“”\"!?—()[]:"

  def __init__(self):
    super().__init__()
    self.triggered = False
    self.blacklisted = False

  def handle_starttag(self, tag, attrs):
    if tag == self.TAG_TRIGGER:
      self.triggered = True
    elif tag in self.TAG_BLACKLIST:
      self.blacklisted = True
    for i in attrs:
      if i[0] == "class" and i[1] in self.CLASS_BLACKLIST:
        self.blacklisted = True
  
  def handle_data(self, data:str):
    if not self.triggered or self.blacklisted:
      return
    for i in self.SYMBOL_BLACKLIST:
      data = data.replace(i, " ")
    for i in data.lower().split():
      if i.islower():
        self.handle_word(i)

  def handle_word(self, word):
    pass

  def handle_endtag(self, tag):
    if tag == self.TAG_TRIGGER:
      self.triggered = False
    self.blacklisted = False

class WordAnimation(WordCounter):
  BAR_CHAR = "▏▎▍▌▋▊▉"

  def __init__(self, stdscr, interval=1):
    super().__init__()
    self.name = ""
    self.stdscr = stdscr
    self.stream = ""
    self.interval = interval
    self.count = defaultdict(int)

  def show_graph(self, w, h, w_s10, h_s1):
    counts = heapq.nlargest(h_s1, self.count.items(), lambda x: x[1])
    maxv = counts[0][1]
    for i, (k, v) in enumerate(counts):
      out = k.ljust(w_s10) + str(v).rjust(10)
      self.stdscr.addstr(i, 0, out)
      self.stdscr.chgat(i, 0, v * w // maxv, curses.A_REVERSE)

  def handle_word(self, word):
    self.count[word] += 1

    h, w = self.stdscr.getmaxyx()
    w_s1 = w - 1 # 这里是玄学优化
    h_s1 = h - 1
    w_s10 = w - 10
    self.show_graph(w, h, w_s10, h_s1)
    self.stream = f"{self.stream} {word}".rjust(w_s1)[-w_s1:]
    self.stdscr.addstr(h_s1, 0, self.stream)
    self.stdscr.addstr(h_s1, 0, self.name + "|")
    self.stdscr.move(h_s1, w_s1)
    self.stdscr.refresh()

    time.sleep(self.interval)

  def animate(self, filename):
    self.name = os.path.splitext(os.path.basename(filename))[0]
    with open(filename) as f:
      self.feed(f.read())

def main(stdscr):
  animation = WordAnimation(stdscr, int(sys.argv[1]) if len(sys.argv) > 1 else 1)
  for i in sorted(os.listdir("Text")):
    animation.animate(f"Text/{i}")
  stdscr.getch()

try:
  curses.wrapper(main)
except KeyboardInterrupt:
  pass