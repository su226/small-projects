#!/usr/bin/python3
import cairo
import gi
import json
import math
import os
import random
import time
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

def parse_color(color):
  return int(color[:2], 16) / 255.0, int(color[2:4], 16) / 255.0, int(color[4:], 16) / 255.0

JSON_NAME = os.path.splitext(os.path.abspath(__file__))[0] + ".json"

with open(JSON_NAME) as f:
  JSON_DATA = json.load(f)
  X = JSON_DATA["x"]
  Y = JSON_DATA["y"]
  WIDTH = JSON_DATA["width"]
  HEIGHT = JSON_DATA["height"]
  SHADOW = JSON_DATA["shadow"]
  ANGLE = JSON_DATA["angle"]
  HALIGN = JSON_DATA["halign"]
  VALIGN = JSON_DATA["valign"]
  TEXT = random.choice(JSON_DATA["texts"])
  COLOR = parse_color(JSON_DATA["color"])
  SHADOW_COLOR = parse_color(JSON_DATA["shadow_color"])
  MAX_SIZE = JSON_DATA["max_size"]
  DURATION = JSON_DATA["duration"]
  MIN_SCALE = JSON_DATA["min_scale"]

OMEGA = math.pi * 2 / DURATION
RADIAN = ANGLE * math.pi / 180
cr = cairo.Context(cairo.ImageSurface(0, 0, 0))
cr.set_font_size(MAX_SIZE)
extents = cr.text_extents(TEXT)
FONT_SIZE = MAX_SIZE * min(WIDTH / extents.width, 1)
EXTENTS_RATIO = FONT_SIZE / MAX_SIZE
SURFACE_Y = -extents.y_bearing * EXTENTS_RATIO
SURFACE_WIDTH = int(extents.width * EXTENTS_RATIO + SHADOW)
SURFACE_HEIGHT = int(extents.height * EXTENTS_RATIO + SHADOW)
CENTER_X = (WIDTH - SURFACE_WIDTH) * HALIGN + SURFACE_WIDTH / 2
CENTER_Y = (HEIGHT - SURFACE_HEIGHT) * VALIGN + SURFACE_HEIGHT / 2

surface = cairo.ImageSurface(cairo.Format.ARGB32, SURFACE_WIDTH, SURFACE_HEIGHT)
cr = cairo.Context(surface)
cr.set_font_size(FONT_SIZE)
if SHADOW != 0:
  cr.set_source_rgb(*SHADOW_COLOR)
  cr.move_to(SHADOW, SURFACE_Y + SHADOW)
  cr.show_text(TEXT)
cr.set_source_rgb(*COLOR)
cr.move_to(0, SURFACE_Y)
cr.show_text(TEXT)

def draw(widget, cr):
  offset = .5 * math.sin(time.time() * OMEGA) + .5
  scale = MIN_SCALE + offset * (1 - MIN_SCALE)
  cr.translate(CENTER_X, CENTER_Y)
  cr.scale(scale, scale)
  cr.rotate(RADIAN)
  cr.translate(-SURFACE_WIDTH / 2, -SURFACE_HEIGHT / 2)
  cr.set_source_surface(surface)
  cr.move_to(0, 0)
  cr.line_to(SURFACE_WIDTH, 0)
  cr.line_to(SURFACE_WIDTH, SURFACE_HEIGHT)
  cr.line_to(0, SURFACE_HEIGHT)
  cr.fill()
  widget.queue_draw()

window = Gtk.Window()
screen = window.get_screen()
window.set_visual(screen.get_rgba_visual())
window.set_app_paintable(True)
window.connect("draw", draw)
window.move(X, Y)
window.set_default_size(WIDTH, HEIGHT)
window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)

window.connect("destroy", Gtk.main_quit)
window.show()
Gtk.main()
