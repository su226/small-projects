#!/usr/bin/python3
from pykeyboard import PyKeyboard, PyKeyboardEvent
from pymouse import PyMouse, PyMouseEvent
import ctypes
import gi
import json
import sys
import threading
import time
import traceback
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk

KEYBOARD = PyKeyboard()
MOUSE = PyMouse()
DISPLAY = Gdk.Display.get_default()
KEYMAP = Gdk.Keymap.get_for_display(DISPLAY)
CLIPBOARD = Gtk.Clipboard.get_default(DISPLAY)

def kill_thread(thread):
  if not thread or not thread.ident:
    return
  tid = ctypes.c_long(thread.ident)
  ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(SystemExit))
  if ret > 1:
    ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
    raise SystemError("Failed to kill thread.")
  
def get_key_name(key):
  if key < 0:
    return f"Mouse{-key}"
  return Gdk.keyval_name(key)

def get_raw_code(key):
  if key < 0:
    return key
  return KEYMAP.get_entries_for_keyval(key).keys[0].keycode

def get_screen_size():
  n = DISPLAY.get_n_monitors()
  width = height = 0
  for i in range(n):
    geometry = DISPLAY.get_monitor(i).get_geometry()
    width = max(width, geometry.x + geometry.width)
    height = max(height, geometry.y + geometry.height)
  return width, height

class KeyDialog(Gtk.MessageDialog):
  TEXTS = [
    "请按下鼠标或键盘",
    "请按下鼠标",
    "请按下键盘"
  ]

  def __init__(self, mode=0, **kw):
    super().__init__(text=self.TEXTS[mode], **kw)
    self.mode = mode
    self.code = None

    if mode != 1:
      self.connect("key-release-event", self.on_key_release)

    if mode != 2:
      button = Gtk.Button(label="点击此处")
      button.connect("button-release-event", self.on_button_release)
      self.get_message_area().pack_start(button, False, True, 0)
      button.show()    

  def on_button_release(self, entry, button):
    self.code = -button.button
    self.response(Gtk.ResponseType.OK)

  def on_key_release(self, entry, key):
    self.code = key.keyval
    self.response(Gtk.ResponseType.OK)

class LocateDialog(Gtk.Dialog):
  TEXT = "选择一个位置，ESC取消"

  def __init__(self):
    super().__init__()
    self.x = 0
    self.y = 0
    self.w, self.h = get_screen_size()
    self.fullscreen()
    self.set_app_paintable(True)
    self.set_size_request(self.w, self.h)
    self.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
    self.connect("draw", self.on_draw)
    self.connect("motion-notify-event", self.on_motion)
    self.connect("button-release-event", self.on_button_release)

  def on_draw(self, window, cr):
    cr.set_source_rgb(0.129411765, 0.588235294, 0.952941176) # 2196f3
    cr.move_to(0, self.y)
    cr.line_to(self.w, self.y)
    cr.move_to(self.x, 0)
    cr.line_to(self.x, self.h)
    cr.stroke()

    cr.set_font_size(14)
    extents = cr.text_extents(self.TEXT)
    cr.move_to(self.x, self.y - extents.y_bearing - extents.height)
    cr.show_text(self.TEXT)

    self.queue_draw()

  def on_motion(self, window, event):
    self.x = event.x
    self.y = event.y

  def on_button_release(self, window, event):
    self.response(Gtk.ResponseType.OK)

class Trigger:
  def __init__(self):
    self.thread = None

  def start(self, action_fn, stop_fn):
    self.action_fn = action_fn
    self.stop_fn = stop_fn

  def stop(self):
    kill_thread(self.thread)
    if self.stop_fn:
      self.stop_fn()

  def serialize(self):
    return {}

  def deserialize(self, data):
    pass

class TriggerPressed(Trigger):
  class ConfigWidget(Gtk.Box):
    def __init__(self, trigger):
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.trigger = trigger

      hbox = Gtk.Box()
      self.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="类型")
      label.set_xalign(0)
      hbox.pack_start(label, False, True, 0)
      label.show()

      self.mode_combo = Gtk.ComboBoxText()
      self.mode_combo.append_text("按下触发一次")
      self.mode_combo.append_text("按下触发，松开停止")
      self.mode_combo.append_text("按下触发，再按停止")
      self.mode_combo.append_text("按触发键触发，按停止键停止")
      self.mode_combo.set_active(0)
      self.mode_combo.connect("changed", self.mode_changed)
      hbox.pack_start(self.mode_combo, True, True, 0)
      self.mode_combo.show()

      hbox = Gtk.Box()
      self.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="触发按键")
      hbox.pack_start(label, True, True, 0)
      label.show()

      button = Gtk.Button.new_from_icon_name("add", Gtk.IconSize.BUTTON)
      button.connect("clicked", self.add_activate_key)
      hbox.pack_start(button, False, False, 0)
      button.show()

      self.activate_box = Gtk.FlowBox(orientation=Gtk.Orientation.VERTICAL)
      self.pack_start(self.activate_box, False, True, 0)
      self.activate_box.show()

      self.deactivate_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
      self.pack_start(self.deactivate_wrap, False, True, 0)

      hbox = Gtk.Box()
      self.deactivate_wrap.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="停止按键")
      hbox.pack_start(label, True, True, 0)
      label.show()

      button = Gtk.Button.new_from_icon_name("add", Gtk.IconSize.BUTTON)
      button.connect("clicked", self.add_deactivate_key)
      hbox.pack_start(button, False, False, 0)
      button.show()

      self.deactivate_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
      self.deactivate_wrap.pack_start(self.deactivate_box, False, True, 0)
      self.deactivate_box.show()

    def mode_changed(self, combo):
      self.trigger.mode = combo.get_active()
      self.deactivate_wrap.set_visible(self.trigger.mode == 3)

    def add_activate_key(self, button):
      dialog = KeyDialog(buttons=Gtk.ButtonsType.CANCEL)
      if dialog.run() == Gtk.ResponseType.OK:
        self.add_key(self.activate_box, self.trigger.activate_keys, self.trigger.raw_activate_keys, dialog.code)
      dialog.destroy()
      
    def add_deactivate_key(self, button):
      dialog = KeyDialog(buttons=Gtk.ButtonsType.CANCEL)
      if dialog.run() == Gtk.ResponseType.OK:
        self.add_key(self.deactivate_box, self.trigger.deactivate_keys, self.trigger.raw_deactivate_keys, dialog.code)
      dialog.destroy()

    def add_key(self, wrap, keys, raw_keys, code, force=False):
      def delete(button):
        keys.remove(code)
        raw_keys.remove(raw_code)
        child.destroy()

      if code in keys and not force:
        return
      raw_code = get_raw_code(code)
      keys.add(code)
      raw_keys.add(raw_code)

      child = Gtk.FlowBoxChild()
      wrap.add(child)
      child.show()

      button = Gtk.Button.new_from_icon_name("delete", Gtk.IconSize.BUTTON)
      button.set_label(get_key_name(code))
      button.set_always_show_image(True)
      button.connect("clicked", delete)
      child.add(button)
      button.show()

    def update(self):
      self.mode_combo.set_active(self.trigger.mode)
      self.activate_box.foreach(Gtk.Widget.destroy)
      for i in self.trigger.activate_keys:
        self.add_key(self.activate_box, self.trigger.activate_keys, self.trigger.raw_activate_keys, i, True)
      self.deactivate_box.foreach(Gtk.Widget.destroy)
      for i in self.trigger.deactivate_keys:
        self.add_key(self.deactivate_box, self.trigger.deactivate_keys, self.trigger.raw_deactivate_keys, i, True)

  class KeyboardListener(PyKeyboardEvent):
    def __init__(self, trigger):
      super().__init__()
      self.trigger = trigger

    def tap(self, code, char, press):
      if press:
        self.trigger.press(code)
      else:
        self.trigger.release(code)
  
  class MouseListener(PyMouseEvent):
    def __init__(self, trigger):
      super().__init__()
      self.trigger = trigger

    def click(self, x, y, button, press):
      if press:
        self.trigger.press(-button)
      else:
        self.trigger.release(-button)

  ID = "pressed"
  NAME = "按键触发"

  def __init__(self):
    super().__init__()
    self.thread2 = None
    self.thread3 = None
    self.mode = 0
    self.activate_keys = set()
    self.raw_activate_keys = set()
    self.deactivate_keys = set()
    self.raw_deactivate_keys = set()
    self.pressed = set()
    self.active = False

  def start(self, action_fn, stop_fn):
    super().start(action_fn, stop_fn)
    if len(self.activate_keys) == 0:
      dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.OK,
        text="请设置触发键"
      )
      dialog.run()
      dialog.destroy()
      return self.stop()
    if self.mode == 3 and len(self.deactivate_keys) == 0:
      dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.OK,
        text="请设置停止键"
      )
      dialog.run()
      dialog.destroy()
      return self.stop()
    self.condition = threading.Condition()
    self.thread = threading.Thread(target=self.run)
    self.thread.start()
    self.thread2 = self.KeyboardListener(self)
    self.thread2.start()
    self.thread3 = self.MouseListener(self)
    self.thread3.start()
  
  def stop(self):
    kill_thread(self.thread2)
    kill_thread(self.thread3)
    super().stop()

  def serialize(self):
    return {
      "mode": self.mode,
      "activate_keys": tuple(self.activate_keys),
      "deactivate_keys": tuple(self.deactivate_keys)
    }

  def deserialize(self, data):
    self.mode = data["mode"]
    self.activate_keys = set(data["activate_keys"])
    self.deactivate_keys = set(data["deactivate_keys"])

  def press(self, code):
    if code in self.pressed:
      return
    self.pressed.add(code)
    if self.pressed == self.raw_activate_keys:
      # 按下触发一次，按下触发松开停止，触发键触发停止键停止
      if self.mode in (0, 1, 3):
        self.active = True
      # 按下触发再按停止
      else:
        self.active = not self.active
      if self.active:
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()
    elif self.mode == 3 and self.pressed == self.raw_deactivate_keys:
      self.active = False

  def release(self, code):
    if code not in self.pressed:
      return
    self.pressed.remove(code)
    # 按下触发松开停止
    if self.mode == 1 and self.pressed != self.activate_keys:
      self.active = False

  def run(self):
    while True:
      while self.active:
        self.action_fn()
        if self.mode == 0:
          self.active = False
      self.condition.acquire()
      self.condition.wait()
      self.condition.release()

class Action:
  def exec(self):
    pass

  def serialize(self):
    return {}

  def deserialize(self, data):
    pass

class ActionSleep(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, trigger):
      super().__init__()
      self.trigger = trigger

      label = Gtk.Label(label="延时")
      self.pack_start(label, False, False, 0)
      label.show()

      self.delay_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 3600, 1, 1, 0), 1, 3)
      self.delay_spin.connect("value-changed", self.changed)
      self.pack_start(self.delay_spin, True, True, 0)
      self.delay_spin.show()

    def changed(self, spin):
      self.trigger.delay = spin.get_value()

    def update(self):
      self.delay_spin.set_value(self.trigger.delay)

  ID = "sleep"
  NAME = "延时"

  def __init__(self):
    self.delay = 0

  def exec(self):
    time.sleep(self.delay)

  def serialize(self):
    return self.delay

  def deserialize(self, data):
    self.delay = data

class ActionKeyTap(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, trigger):
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.trigger = trigger

      hbox = Gtk.Box()
      self.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="模式")
      hbox.pack_start(label, False, True, 0)
      label.show()

      self.mode_combo = Gtk.ComboBoxText()
      self.mode_combo.append_text("点击")
      self.mode_combo.append_text("按下")
      self.mode_combo.append_text("松开")
      self.mode_combo.set_active(0)
      self.mode_combo.connect("changed", self.mode_changed)
      hbox.pack_start(self.mode_combo, True, True, 0)
      self.mode_combo.show()

      self.click_box = Gtk.Box()
      self.pack_start(self.click_box, False, True, 0)
      self.click_box.show()

      label = Gtk.Label(label="次数")
      self.click_box.pack_start(label, False, True, 0)
      label.show()

      self.times_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(1, 1, 1000, 1, 1, 1), 1, 0)
      self.times_spin.connect("value-changed", self.times_changed)
      self.click_box.pack_start(self.times_spin, True, True, 0)
      self.times_spin.show()

      label = Gtk.Label(label="时长")
      self.click_box.pack_start(label, False, True, 0)
      label.show()

      self.duration_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 1000, 1, 1, 0), 1, 3)
      self.duration_spin.connect("value-changed", self.duration_changed)
      self.click_box.pack_start(self.duration_spin, True, True, 0)
      self.duration_spin.show()

      label = Gtk.Label(label="间隔")
      self.click_box.pack_start(label, False, True, 0)
      label.show()

      self.delay_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 1000, 1, 1, 0), 1, 3)
      self.delay_spin.connect("value-changed", self.delay_changed)
      self.click_box.pack_start(self.delay_spin, True, True, 0)
      self.delay_spin.show()

      hbox = Gtk.Box()
      self.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="按键")
      hbox.pack_start(label, True, True, 0)
      label.show()

      button = Gtk.Button.new_from_icon_name("add", Gtk.IconSize.BUTTON)
      button.connect("clicked", self.add_clicked)
      hbox.pack_start(button, False, False, 0)
      button.show()

      self.keys_box = Gtk.FlowBox(orientation=Gtk.Orientation.VERTICAL)
      self.pack_start(self.keys_box, False, True, 0)
      self.keys_box.show()

    def add_key(self, code, force=False):
      def delete(button):
        self.trigger.keys.remove(code)
        self.trigger.raw_keys.remove(raw_code)
        child.destroy()

      if code in self.trigger.keys and not force:
        return
      raw_code = get_raw_code(code)
      self.trigger.keys.add(code)
      self.trigger.raw_keys.add(raw_code)

      child = Gtk.FlowBoxChild()
      self.keys_box.add(child)
      child.show()

      button = Gtk.Button.new_from_icon_name("delete", Gtk.IconSize.BUTTON)
      button.set_label(get_key_name(code))
      button.set_always_show_image(True)
      button.connect("clicked", delete)
      child.add(button)
      button.show()

    def mode_changed(self, combo):
      self.trigger.mode = combo.get_active()
      self.click_box.set_visible(self.trigger.mode == 0)

    def times_changed(self, spin):
      self.trigger.times = int(spin.get_value())

    def duration_changed(self, spin):
      self.trigger.duration = spin.get_value()

    def delay_changed(self, spin):
      self.trigger.delay = spin.get_value()

    def add_clicked(self, button):
      dialog = KeyDialog(mode=2, buttons=Gtk.ButtonsType.CANCEL)
      if dialog.run() == Gtk.ResponseType.OK:
        self.add_key(dialog.code)
      dialog.destroy()

    def update(self):
      self.mode_combo.set_active(self.trigger.mode)
      self.times_spin.set_value(self.trigger.times)
      self.duration_spin.set_value(self.trigger.duration)
      self.delay_spin.set_value(self.trigger.delay)
      self.keys_box.foreach(Gtk.Widget.destroy)
      for i in self.trigger.keys:
        self.add_key(i, True)

  ID = "key_tap"
  NAME = "点击键盘"

  def __init__(self):
    self.mode = 0
    self.times = 1
    self.duration = 0
    self.delay = 0
    self.keys = set()
    self.raw_keys = set()

  def exec(self):
    if self.mode == 0:
      for i in range(self.times):
        if i != 0:
          time.sleep(self.delay)
        self.press()
        time.sleep(self.duration)
        self.release()
    elif self.mode == 1:
      self.press()
    else:
      self.release()

  def press(self):
    for j in self.raw_keys:
      KEYBOARD.press_key(j)

  def release(self):
    for j in self.raw_keys:
      KEYBOARD.release_key(j)
  
  def serialize(self):
    return {
      "mode": self.mode,
      "times": self.times,
      "duration": self.duration,
      "delay": self.delay,
      "keys": tuple(self.keys)
    }

  def deserialize(self, data):
    self.mode = data["mode"]
    self.times = data["times"]
    self.duration = data["duration"]
    self.delay = data["delay"]
    self.keys = set(data["keys"])

class ActionMouseTap(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, trigger):
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.trigger = trigger

      hbox = Gtk.Box()
      self.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="模式")
      hbox.pack_start(label, False, True, 0)
      label.show()

      self.mode_combo = Gtk.ComboBoxText()
      self.mode_combo.append_text("点击")
      self.mode_combo.append_text("按下")
      self.mode_combo.append_text("松开")
      self.mode_combo.set_active(0)
      self.mode_combo.connect("changed", self.mode_changed)
      hbox.pack_start(self.mode_combo, True, True, 0)
      self.mode_combo.show()

      self.pos_check = Gtk.CheckButton(label="坐标")
      self.pos_check.connect("toggled", self.pos_toggled)
      hbox.pack_start(self.pos_check, False, True, 0)
      self.pos_check.show()

      self.click_box = Gtk.Box()
      self.pack_start(self.click_box, False, True, 0)
      self.click_box.show()

      label = Gtk.Label(label="次数")
      self.click_box.pack_start(label, False, True, 0)
      label.show()

      self.times_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(1, 1, 1000, 1, 1, 1), 1, 0)
      self.times_spin.connect("value-changed", self.times_changed)
      self.click_box.pack_start(self.times_spin, True, True, 0)
      self.times_spin.show()

      label = Gtk.Label(label="时长")
      self.click_box.pack_start(label, False, True, 0)
      label.show()

      self.duration_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 1000, 1, 1, 0), 1, 3)
      self.duration_spin.connect("value-changed", self.duration_changed)
      self.click_box.pack_start(self.duration_spin, True, True, 0)
      self.duration_spin.show()

      label = Gtk.Label(label="间隔")
      self.click_box.pack_start(label, False, True, 0)
      label.show()

      self.delay_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 1000, 1, 1, 0), 1, 3)
      self.delay_spin.connect("value-changed", self.delay_changed)
      self.click_box.pack_start(self.delay_spin, True, True, 0)
      self.delay_spin.show()

      hbox = Gtk.Box()
      self.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="按键")
      hbox.pack_start(label, False, True, 0)
      label.show()

      self.change_button = Gtk.Button(label="Mouse1")
      self.change_button.connect("clicked", self.change_clicked)
      hbox.pack_start(self.change_button, True, True, 0)
      self.change_button.show()

      self.position_box = Gtk.Box()
      hbox.pack_start(self.position_box, False, True, 0)

      w, h = get_screen_size()

      self.x_spin = Gtk.SpinButton.new_with_range(0, w, 1)
      self.x_spin.connect("value-changed", self.x_changed)
      self.position_box.pack_start(self.x_spin, True, True, 0)
      self.x_spin.show()

      self.y_spin = Gtk.SpinButton.new_with_range(0, h, 1)
      self.y_spin.connect("value-changed", self.y_changed)
      self.position_box.pack_start(self.y_spin, True, True, 0)
      self.y_spin.show()

      button = Gtk.Button.new_from_icon_name("find-location", Gtk.IconSize.BUTTON)
      button.connect("clicked", self.locate_clicked)
      self.position_box.pack_start(button, False, False, 0)
      button.show()

    def mode_changed(self, combo):
      self.trigger.mode = combo.get_active()
      self.click_box.set_visible(self.trigger.mode == 0)

    def times_changed(self, spin):
      self.trigger.times = spin.get_value_as_int()

    def duration_changed(self, spin):
      self.trigger.duration = spin.get_value()

    def delay_changed(self, spin):
      self.trigger.delay = spin.get_value()

    def pos_toggled(self, check):
      self.trigger.position_lock = check.get_active()
      self.position_box.set_visible(self.trigger.position_lock)
    
    def x_changed(self, spin):
      self.trigger.position_x = spin.get_value_as_int()
    
    def y_changed(self, spin):
      self.trigger.position_y = spin.get_value_as_int()

    def locate_clicked(self, button):
      dialog = LocateDialog()
      if dialog.run() == Gtk.ResponseType.OK:
        self.x_spin.set_value(dialog.x)
        self.y_spin.set_value(dialog.y)
      dialog.destroy()

    def change_clicked(self, button):
      dialog = KeyDialog(1, buttons=Gtk.ButtonsType.CANCEL)
      if dialog.run() == Gtk.ResponseType.OK:
        self.trigger.button = -dialog.code
        button.set_label(get_key_name(dialog.code))
      dialog.destroy()

    def update(self):
      self.mode_combo.set_active(self.trigger.mode)
      self.times_spin.set_value(self.trigger.times)
      self.duration_spin.set_value(self.trigger.duration)
      self.delay_spin.set_value(self.trigger.delay)
      self.change_button.set_label(get_key_name(-self.trigger.button))
      self.pos_check.set_active(self.trigger.position_lock)
      self.x_spin.set_value(self.trigger.position_x)
      self.y_spin.set_value(self.trigger.position_y)

  def __init__(self):
    self.mode = 0
    self.times = 1
    self.duration = 0
    self.delay = 0
    self.button = 1
    self.position_lock = False
    self.position_x = 0
    self.position_y = 0
  
  def exec(self):
    if self.mode == 0:
      for i in range(self.times):
        if i != 0:
          time.sleep(self.delay)
        self.press()
        time.sleep(self.duration)
        self.release()
    elif self.mode == 1:
      self.press()
    else:
      self.release()

  def press(self):
    if self.position_lock:
      x, y = self.position_x, self.position_y
    else:
      x, y = MOUSE.position()
    MOUSE.press(x, y, self.button)

  def release(self):
    if self.position_lock:
      x, y = self.position_x, self.position_y
    else:
      x, y = MOUSE.position()
    MOUSE.release(x, y, self.button)

  def serialize(self):
    return {
      "mode": self.mode,
      "times": self.times,
      "duration": self.duration,
      "delay": self.delay,
      "button": self.button,
      "position": [self.position_lock, self.position_x, self.position_y]
    }

  def deserialize(self, data):
    self.mode = data["mode"]
    self.times = data["times"]
    self.duration = data["duration"]
    self.delay = data["delay"]
    self.button = data["button"]
    self.position_lock, self.position_x, self.position_y = data["position"]

  ID = "mouse_tap"
  NAME = "点击鼠标"

class ActionCopy(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, trigger):
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.trigger = trigger

      label = Gtk.Label(label="内容")
      self.pack_start(label, False, True, 0)
      label.show()

      textview = Gtk.TextView()
      self.pack_start(textview, False, True, 0)
      textview.show()

      self.buffer = textview.get_buffer()
      self.buffer.connect("changed", self.buffer_changed)

    def update(self):
      self.buffer.set_text(self.trigger.text)
    
    def buffer_changed(self, entry):
      self.trigger.text = self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), False)

  ID = "copy"
  NAME = "复制"

  def __init__(self):
    self.text = ""

  def exec(self):
    GLib.idle_add(self.do_exec)

  def do_exec(self):
    CLIPBOARD.set_text(self.text, -1)
    CLIPBOARD.store()

  def serialize(self):
    return self.text

  def deserialize(self, data):
    self.text = data

class ActionType(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, trigger):
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.trigger = trigger

      hbox = Gtk.Box()
      self.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="间隔")
      hbox.pack_start(label, False, True, 0)
      label.show()

      self.interval_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 1000, 1, 1, 0.001), 1, 3)
      self.interval_spin.connect("value-changed", self.interval_changed)
      hbox.pack_start(self.interval_spin, True, True, 0)
      self.interval_spin.show()

      hbox = Gtk.Box()
      self.pack_start(hbox, False, True, 0)
      hbox.show()

      label = Gtk.Label(label="内容")
      hbox.pack_start(label, False, True, 0)
      label.show()

      self.entry = Gtk.Entry()
      self.entry.connect("changed", self.entry_changed)
      hbox.pack_start(self.entry, True, True, 0)
      self.entry.show()

    def update(self):
      self.interval_spin.set_value(self.trigger.interval)
      self.entry.set_text(self.trigger.text)

    def interval_changed(self, spin):
      self.trigger.interval = spin.get_value()
    
    def entry_changed(self, entry):
      self.trigger.text = entry.get_text()

  ID = "type"
  NAME = "输入文本（仅限英文）"

  def __init__(self):
    self.text = ""
    self.interval = 0

  def exec(self):
    KEYBOARD.type_string(self.text, self.interval)

  def serialize(self):
    return {
      "text": self.text,
      "interval": self.interval
    }

  def deserialize(self, data):
    self.text = data["text"]
    self.interval = data["interval"]

TRIGGERS = { i.ID: i for i in [
  TriggerPressed
] }

TRIGGERS_INDEX = { k: i for i, k in enumerate(TRIGGERS) }

ACTIONS = { i.ID: i for i in [
  ActionSleep,
  ActionKeyTap,
  ActionMouseTap,
  ActionCopy,
  ActionType
] }

ACTIONS_INDEX = { k: i for i, k in enumerate(ACTIONS) }

class MainWindow(Gtk.Window):
  def __init__(self):
    super().__init__(title="连点器")
    self.set_default_size(800, 600)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    self.add(vbox)
    vbox.show()

    scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
    vbox.pack_start(scrolled, True, True, 0)
    scrolled.show()

    vbox2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    scrolled.add(vbox2)
    vbox2.show()

    ########################################
    
    hbox = Gtk.Box()
    vbox2.pack_start(hbox, False, True, 0)
    hbox.show()
    
    label = Gtk.Label(label="触发器")
    label.set_xalign(0)
    hbox.pack_start(label, False, True, 0)
    label.show()

    self.trigger_store = Gtk.ListStore(str, str)
    for i, v in TRIGGERS.items():
      self.trigger_store.append([i, v.NAME])

    self.trigger_combo = Gtk.ComboBox.new_with_model(self.trigger_store)
    cell = Gtk.CellRendererText()
    self.trigger_combo.pack_start(cell, True)
    self.trigger_combo.add_attribute(cell, "text", 1)
    self.trigger_combo.connect("changed", self.trigger_changed)
    hbox.pack_start(self.trigger_combo, False, True, 0)
    self.trigger_combo.show()

    self.trigger_wrap = Gtk.Frame()
    vbox2.pack_start(self.trigger_wrap, False, True, 0)
    self.trigger_wrap.show()

    self.trigger_combo.set_active(0)

    ########################################

    label = Gtk.Label(label="操作")
    label.set_xalign(0)
    vbox2.pack_start(label, False, True, 0)
    label.show()

    self.action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    vbox2.pack_start(self.action_box, True, True, 0)
    self.action_box.show()

    button = Gtk.Button.new_from_icon_name("add", Gtk.IconSize.BUTTON)
    button.connect("clicked", self.add_clicked)
    vbox2.pack_start(button, False, False, 0)
    button.show()

    ########################################

    hbox = Gtk.ButtonBox()
    hbox.set_layout(Gtk.ButtonBoxStyle.EXPAND)
    vbox.pack_start(hbox, False, True, 0)
    hbox.show()

    button = Gtk.Button(label="导入")
    button.connect("clicked", self.import_clicked)
    hbox.pack_start(button, True, True, 0)
    button.show()

    button = Gtk.Button(label="导出")
    button.connect("clicked", self.export_clicked)
    hbox.pack_start(button, True, True, 0)
    button.show()
    
    self.toggle_button = Gtk.Button(label="开始")
    self.toggle_button.connect("clicked", self.toggle_clicked)
    hbox.pack_start(self.toggle_button, True, True, 0)
    self.toggle_button.show()

    self.actions = []
    self.running = False

  def add_action(self, index):
    def up(button):
      pos = self.actions.index(action)
      if pos > 0:
        self.actions[pos], self.actions[pos - 1] = self.actions[pos - 1], self.actions[pos]
        pos -= 1
        self.action_box.reorder_child(box, pos)

    def down(button):
      pos = self.actions.index(action)
      if pos < len(self.actions) - 1:
        self.actions[pos], self.actions[pos + 1] = self.actions[pos + 1], self.actions[pos]
        pos += 1
        self.action_box.reorder_child(box, pos)

    def delete(button):
      self.actions.remove(action)
      box.destroy()

    def change(combo):
      nonlocal action
      new_action = ACTIONS[store[combo.get_active()][0]]()
      if action is not None:
        config_wrap.get_child().destroy()
        self.actions[self.actions.index(action)] = new_action
      else:
        self.actions.append(new_action)
      action = new_action
      widget = action.ConfigWidget(action)
      config_wrap.add(widget)
      widget.show()

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    self.action_box.add(box)
    box.show()

    hbox = Gtk.Box()
    box.pack_start(hbox, False, True, 0)
    hbox.show()

    store = Gtk.ListStore(str, str)
    for k, v in ACTIONS.items():
      store.append([k, v.NAME])

    combo = Gtk.ComboBox.new_with_model(store)
    cell = Gtk.CellRendererText()
    combo.pack_start(cell, True)
    combo.add_attribute(cell, "text", 1)
    combo.connect("changed", change)
    hbox.pack_start(combo, True, True, 0)
    combo.show()

    bbox = Gtk.ButtonBox()
    bbox.set_layout(Gtk.ButtonBoxStyle.EXPAND)
    hbox.pack_start(bbox, False, True, 0)
    bbox.show()

    button = Gtk.Button.new_from_icon_name("up", Gtk.IconSize.BUTTON)
    button.connect("clicked", up)
    bbox.pack_start(button, False, False, 0)
    button.show()

    button = Gtk.Button.new_from_icon_name("delete", Gtk.IconSize.BUTTON)
    button.connect("clicked", delete)
    bbox.pack_start(button, False, False, 0)
    button.show()

    button = Gtk.Button.new_from_icon_name("down", Gtk.IconSize.BUTTON)
    button.connect("clicked", down)
    bbox.pack_start(button, False, False, 0)
    button.show()

    config_wrap = Gtk.Frame()
    box.pack_start(config_wrap, False, False, 0)
    config_wrap.show()

    if isinstance(index, str):
      index = ACTIONS_INDEX[index]
    action = None
    combo.set_active(index)

    return (action, config_wrap.get_child())

  def trigger_changed(self, combo):
    self.trigger = TRIGGERS[self.trigger_store[combo.get_active()][0]]()
    if child := self.trigger_wrap.get_child():
      child.destroy()
    child = self.trigger.ConfigWidget(self.trigger)
    self.trigger_wrap.add(child)
    child.show()

  def add_clicked(self, button):
    self.add_action(0)

  def import_clicked(self, button):
    dialog = Gtk.FileChooserDialog(parent=self, title="导入", action=Gtk.FileChooserAction.OPEN)
    dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
    filter_json = Gtk.FileFilter()
    filter_json.set_name("JSON")
    filter_json.add_mime_type("application/json")
    dialog.add_filter(filter_json)
    filter_all = Gtk.FileFilter()
    filter_all.add_pattern("*")
    filter_all.set_name("所有文件")
    dialog.add_filter(filter_all)
    response = dialog.run()
    filename = dialog.get_filename()
    dialog.destroy()
    if response != Gtk.ResponseType.OK:
      return
    with open(filename, "r") as f:
      data = json.load(f)
    self.trigger_combo.set_active(TRIGGERS_INDEX[data["trigger"][0]])
    self.trigger.deserialize(data["trigger"][1])
    self.trigger_wrap.get_child().update()
    self.actions.clear()
    self.action_box.foreach(Gtk.Widget.destroy)
    for (name, config) in data["actions"]:
      action, widget = self.add_action(name)
      action.deserialize(config)
      widget.update()

  def export_clicked(self, button):
    dialog = Gtk.FileChooserDialog(parent=self, title="导出", action=Gtk.FileChooserAction.SAVE)
    dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
    filter_json = Gtk.FileFilter()
    filter_json.set_name("JSON")
    filter_json.add_mime_type("application/json")
    dialog.add_filter(filter_json)
    filter_all = Gtk.FileFilter()
    filter_all.add_pattern("*")
    filter_all.set_name("所有文件")
    dialog.add_filter(filter_all)
    if dialog.run() == Gtk.ResponseType.OK:
      with open(dialog.get_filename(), "w") as f:
        json.dump({
          "trigger": [self.trigger.ID, self.trigger.serialize()],
          "actions": [[i.ID, i.serialize()] for i in self.actions]
        }, f)
    dialog.destroy()

  def toggle_clicked(self, button):
    if self.running:
      self.trigger.stop()
    else:
      self.running = True
      self.toggle_button.set_label("停止")
      self.trigger.start(self.on_action, self.on_stop)

  def on_action(self):
    for i in self.actions:
      try:
        i.exec
      except:
        traceback.print_exc()

  def on_stop(self):
    self.running = False
    self.toggle_button.set_label("开始")

if __name__ == "__main__":
  window = MainWindow()
  window.connect("destroy", Gtk.main_quit)
  window.show()
  Gtk.main()
