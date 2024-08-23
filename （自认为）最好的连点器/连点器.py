#!/usr/bin/python3
import ctypes
import json
import threading
import time
import traceback
from typing import Any, Callable, ClassVar, Literal, Protocol, cast

import cairo
import gi
import pynput

gi.require_version("Gdk", "3.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402 # type: ignore

KeyDialogMode = Literal[0, 1, 2]
TriggerPressedMode = Literal[0, 1, 2, 3]

KEYBOARD = pynput.keyboard.Controller()
MOUSE = pynput.mouse.Controller()
_DISPLAY = Gdk.Display.get_default()
if not _DISPLAY:
  raise RuntimeError("No display.")
DISPLAY = _DISPLAY
del _DISPLAY
KEYMAP = Gdk.Keymap.get_for_display(DISPLAY)
CLIPBOARD = Gtk.Clipboard.get_default(DISPLAY)

def kill_thread(thread: threading.Thread) -> None:
  if not thread.ident:
    return
  tid = ctypes.c_long(thread.ident)
  ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(SystemExit))
  if ret > 1:
    ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, 0)
    raise SystemError("Failed to kill thread.")
  
def get_key_name(key: int) -> str:
  if key < 0:
    return f"Mouse{-key}"
  name = Gdk.keyval_name(key)
  if not name:
    raise RuntimeError(f"Failed to get name of key {key}.")
  return name

def get_screen_size() -> tuple[int, int]:
  n = DISPLAY.get_n_monitors()
  width = height = 0
  for i in range(n):
    monitor = DISPLAY.get_monitor(i)
    if not monitor:
      raise RuntimeError(f"Failed to get monitor {i}.")
    geometry = monitor.get_geometry()
    width = max(width, geometry.x + geometry.width)
    height = max(height, geometry.y + geometry.height)
  return width, height

class KeyDialog(Gtk.MessageDialog):
  TEXTS = [
    "请按下鼠标或键盘",
    "请按下鼠标",
    "请按下键盘"
  ]

  def __init__(self, mode: KeyDialogMode = 0, **kw: Any) -> None:
    super().__init__(text=self.TEXTS[mode], **kw)
    self.mode = mode
    self.code: int | None = None

    if mode != 1:
      self.connect("key-release-event", self.self_key_release)

    if mode != 2:
      button = Gtk.Button(label="点击此处")
      button.connect("button-release-event", self.self_button_release)
      cast(Gtk.Box, self.get_message_area()).pack_start(button, False, True, 0)
      button.show()    

  def self_button_release(self, widget: Gtk.Widget, button: Gdk.EventButton) -> None:
    self.code = -button.button
    self.response(Gtk.ResponseType.OK)

  def self_key_release(self, widget: Gtk.Widget, key: Gdk.EventKey) -> None:
    self.code = key.keyval
    self.response(Gtk.ResponseType.OK)

class LocateDialog(Gtk.Dialog):
  TEXT = "选择一个位置，ESC取消"

  def __init__(self) -> None:
    super().__init__()
    self.x = 0
    self.y = 0
    self.w, self.h = get_screen_size()
    self.fullscreen()
    self.set_app_paintable(True)
    self.set_size_request(self.w, self.h)
    self.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
    self.connect("draw", self.self_draw)
    self.connect("motion-notify-event", self.self_motion)
    self.connect("button-release-event", self.self_button_release)

  def self_draw(self, window: Gtk.Window, cr: "cairo.Context[cairo.ImageSurface]") -> None:
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

  def self_motion(self, window: Gtk.Window, event: Gdk.EventMotion) -> None:
    self.x = event.x
    self.y = event.y

  def self_button_release(self, window: Gtk.Window, event: Gdk.EventButton) -> None:
    self.response(Gtk.ResponseType.OK)

class Trigger:
  ID: ClassVar[str]
  NAME: ClassVar[str]

  def __init__(self) -> None:
    self.thread: threading.Thread | None = None

  def start(self, action_fn: Callable[[], None], stop_fn: Callable[[], None] | None) -> None:
    self.action_fn = action_fn
    self.stop_fn = stop_fn

  def stop(self) -> None:
    if self.thread:
      kill_thread(self.thread)
    if self.stop_fn:
      self.stop_fn()

  def serialize(self) -> Any:
    return {}

  def deserialize(self, data: Any) -> None:
    pass

class TriggerPressed(Trigger):
  class ConfigWidget(Gtk.Box):
    def __init__(self, trigger: "TriggerPressed") -> None:
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

    def mode_changed(self, combo: Gtk.ComboBoxText) -> None:
      self.trigger.mode = cast(TriggerPressedMode, combo.get_active())
      self.deactivate_wrap.set_visible(self.trigger.mode == 3)

    def add_activate_key(self, button: Gtk.Button) -> None:
      dialog = KeyDialog(buttons=Gtk.ButtonsType.CANCEL)
      if dialog.run() == Gtk.ResponseType.OK and dialog.code is not None:
        self.add_key(self.activate_box, self.trigger.activate_keys, dialog.code)
      dialog.destroy()
      
    def add_deactivate_key(self, button: Gtk.Button) -> None:
      dialog = KeyDialog(buttons=Gtk.ButtonsType.CANCEL)
      if dialog.run() == Gtk.ResponseType.OK and dialog.code is not None:
        self.add_key(self.deactivate_box, self.trigger.deactivate_keys, dialog.code)
      dialog.destroy()

    def add_key(self, wrap: Gtk.Container, keys: set[int], code: int, force: bool = False) -> None:
      def delete(button: Gtk.Button) -> None:
        keys.remove(code)
        child.destroy()

      if code in keys and not force:
        return
      keys.add(code)

      child = Gtk.FlowBoxChild()
      wrap.add(child)
      child.show()

      button = Gtk.Button.new_from_icon_name("delete", Gtk.IconSize.BUTTON)
      button.set_label(get_key_name(code))
      button.set_always_show_image(True)
      button.connect("clicked", delete)
      child.add(button)
      button.show()

    def update(self) -> None:
      self.mode_combo.set_active(self.trigger.mode)
      self.activate_box.foreach(Gtk.Widget.destroy)
      for i in self.trigger.activate_keys:
        self.add_key(self.activate_box, self.trigger.activate_keys, i, True)
      self.deactivate_box.foreach(Gtk.Widget.destroy)
      for i in self.trigger.deactivate_keys:
        self.add_key(self.deactivate_box, self.trigger.deactivate_keys, i, True)

  ID = "pressed"
  NAME = "按键触发"

  def __init__(self) -> None:
    super().__init__()
    self.thread2: threading.Thread | None = None
    self.thread3: threading.Thread | None = None
    self.mode: TriggerPressedMode = 0
    self.activate_keys = set[int]()
    self.deactivate_keys = set[int]()
    self.pressed = set[int]()
    self.handled = set[int]()

  def start(self, action_fn: Callable[[], None], stop_fn: Callable[[], None] | None) -> None:
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
    self.event = threading.Event()
    self.thread = threading.Thread(target=self.run, daemon=True)
    self.thread.start()
    self.thread2 = pynput.keyboard.Listener(self.on_keyboard_press, self.on_keyboard_release)
    self.thread2.start()
    self.thread3 = pynput.mouse.Listener(on_click=self.on_mouse_click)
    self.thread3.start()
  
  def stop(self) -> None:
    if self.thread2:
      kill_thread(self.thread2)
    if self.thread3:
      kill_thread(self.thread3)
    super().stop()

  def serialize(self) -> Any:
    return {
      "mode": self.mode,
      "activate_keys": tuple(self.activate_keys),
      "deactivate_keys": tuple(self.deactivate_keys)
    }

  def deserialize(self, data: Any) -> None:
    self.mode = data["mode"]
    self.activate_keys = set(data["activate_keys"])
    self.deactivate_keys = set(data["deactivate_keys"])

  def on_keyboard_press(self, key: pynput.keyboard.Key | pynput.keyboard.KeyCode | None) -> None:
    if isinstance(key, pynput.keyboard.Key):
      self.press(key.value)
    elif key and key.vk is not None:
      self.press(key.vk)

  def on_keyboard_release(self, key: pynput.keyboard.Key | pynput.keyboard.KeyCode | None) -> None:
    if isinstance(key, pynput.keyboard.Key):
      self.release(key.value)
    elif key and key.vk is not None:
      self.release(key.vk)

  def on_mouse_click(self, x: int, y: int, button: pynput.mouse.Button, pressed: bool) -> None:
    if pressed:
      self.press(-button.value)
    else:
      self.release(-button.value)

  def press(self, code: int) -> None:
    if code in self.pressed:
      return
    self.pressed.add(code)
    unhandled = self.pressed - self.handled
    if self.activate_keys <= unhandled:
      # 按下触发一次，按下触发松开停止，触发键触发停止键停止
      if self.mode in (0, 1, 3):
        self.event.set()
      # 按下触发再按停止
      else:
        if self.event.is_set():
          self.event.clear()
        else:
          self.event.set()
      self.handled.update(self.activate_keys)
    elif self.mode == 3 and self.deactivate_keys <= unhandled:
      self.event.clear()
      self.handled.update(self.deactivate_keys)

  def release(self, code: int) -> None:
    if code not in self.pressed:
      return
    self.pressed.remove(code)
    if code in self.handled:
      self.handled.remove(code)
    # 按下触发松开停止
    if self.mode == 1 and not self.activate_keys <= self.pressed:
      self.event.clear()

  def run(self) -> None:
    while True:
      self.event.wait()
      self.action_fn()
      if self.mode == 0:
        self.event.clear()


class Action():
  ID: str
  NAME: str

  class ConfigWidget(Protocol):
    def __init__(self, action: Any) -> None: ...
    def update(self) -> None: ...

  def exec(self) -> None:
    pass

  def serialize(self) -> Any:
    return {}

  def deserialize(self, data: Any) -> None:
    pass

class ActionSleep(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, action: "ActionSleep") -> None:
      super().__init__()
      self.action = action

      label = Gtk.Label(label="延时")
      self.pack_start(label, False, False, 0)
      label.show()

      self.delay_spin = Gtk.SpinButton.new(Gtk.Adjustment.new(0, 0, 3600, 1, 1, 0), 1, 3)
      self.delay_spin.connect("value-changed", self.changed)
      self.pack_start(self.delay_spin, True, True, 0)
      self.delay_spin.show()

    def changed(self, spin: Gtk.SpinButton) -> None:
      self.action.delay = spin.get_value()

    def update(self) -> None:
      self.delay_spin.set_value(self.action.delay)

  ID = "sleep"
  NAME = "延时"

  def __init__(self) -> None:
    self.delay: float = 0

  def exec(self) -> None:
    time.sleep(self.delay)

  def serialize(self) -> Any:
    return self.delay

  def deserialize(self, data: Any) -> None:
    self.delay = data

class ActionKeyTap(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, action: "ActionKeyTap") -> None:
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.action = action

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

    def add_key(self, code: int, force: bool = False) -> None:
      def delete(button: Gtk.Button) -> None:
        self.action.keys.remove(code)
        child.destroy()

      if code in self.action.keys and not force:
        return
      self.action.keys.add(code)

      child = Gtk.FlowBoxChild()
      self.keys_box.add(child)
      child.show()

      button = Gtk.Button.new_from_icon_name("delete", Gtk.IconSize.BUTTON)
      button.set_label(get_key_name(code))
      button.set_always_show_image(True)
      button.connect("clicked", delete)
      child.add(button)
      button.show()

    def mode_changed(self, combo: Gtk.ComboBoxText) -> None:
      self.action.mode = combo.get_active()
      self.click_box.set_visible(self.action.mode == 0)

    def times_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.times = int(spin.get_value())

    def duration_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.duration = spin.get_value()

    def delay_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.delay = spin.get_value()

    def add_clicked(self, button: Gtk.Button) -> None:
      dialog = KeyDialog(mode=2, buttons=Gtk.ButtonsType.CANCEL)
      if dialog.run() == Gtk.ResponseType.OK and dialog.code is not None:
        self.add_key(dialog.code)
      dialog.destroy()

    def update(self) -> None:
      self.mode_combo.set_active(self.action.mode)
      self.times_spin.set_value(self.action.times)
      self.duration_spin.set_value(self.action.duration)
      self.delay_spin.set_value(self.action.delay)
      self.keys_box.foreach(Gtk.Widget.destroy)
      for i in self.action.keys:
        self.add_key(i, True)

  ID = "key_tap"
  NAME = "点击键盘"

  def __init__(self) -> None:
    self.mode = 0
    self.times = 1
    self.duration = 0
    self.delay = 0
    self.keys = set[int]()

  def exec(self) -> None:
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

  def press(self) -> None:
    for j in self.keys:
      KEYBOARD.press(pynput.keyboard.KeyCode(cast(Any, j)))

  def release(self) -> None:
    for j in self.keys:
      KEYBOARD.release(pynput.keyboard.KeyCode(cast(Any, j)))
  
  def serialize(self) -> Any:
    return {
      "mode": self.mode,
      "times": self.times,
      "duration": self.duration,
      "delay": self.delay,
      "keys": tuple(self.keys)
    }

  def deserialize(self, data: Any) -> None:
    self.mode = data["mode"]
    self.times = data["times"]
    self.duration = data["duration"]
    self.delay = data["delay"]
    self.keys = set[int](data["keys"])

class ActionMouseTap(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, action: "ActionMouseTap") -> None:
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.action = action

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

    def mode_changed(self, combo: Gtk.ComboBoxText) -> None:
      self.action.mode = combo.get_active()
      self.click_box.set_visible(self.action.mode == 0)

    def times_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.times = spin.get_value_as_int()

    def duration_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.duration = spin.get_value()

    def delay_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.delay = spin.get_value()

    def pos_toggled(self, check: Gtk.CheckButton) -> None:
      self.action.position_lock = check.get_active()
      self.position_box.set_visible(self.action.position_lock)
    
    def x_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.position_x = spin.get_value_as_int()
    
    def y_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.position_y = spin.get_value_as_int()

    def locate_clicked(self, button: Gtk.Button) -> None:
      dialog = LocateDialog()
      if dialog.run() == Gtk.ResponseType.OK:
        self.x_spin.set_value(dialog.x)
        self.y_spin.set_value(dialog.y)
      dialog.destroy()

    def change_clicked(self, button: Gtk.Button) -> None:
      dialog = KeyDialog(1, buttons=Gtk.ButtonsType.CANCEL)
      if dialog.run() == Gtk.ResponseType.OK and dialog.code is not None:
        self.action.button = -dialog.code
        button.set_label(get_key_name(dialog.code))
      dialog.destroy()

    def update(self) -> None:
      self.mode_combo.set_active(self.action.mode)
      self.times_spin.set_value(self.action.times)
      self.duration_spin.set_value(self.action.duration)
      self.delay_spin.set_value(self.action.delay)
      self.change_button.set_label(get_key_name(-self.action.button))
      self.pos_check.set_active(self.action.position_lock)
      self.x_spin.set_value(self.action.position_x)
      self.y_spin.set_value(self.action.position_y)

  def __init__(self) -> None:
    self.mode = 0
    self.times = 1
    self.duration = 0
    self.delay = 0
    self.button = 1
    self.position_lock = False
    self.position_x = 0
    self.position_y = 0
  
  def exec(self) -> None:
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

  def press(self) -> None:
    if self.position_lock:
      MOUSE.position = (self.position_x, self.position_y)
    MOUSE.press(pynput.mouse.Button(self.button))

  def release(self) -> None:
    if self.position_lock:
      MOUSE.position = (self.position_x, self.position_y)
    MOUSE.release(pynput.mouse.Button(self.button))

  def serialize(self) -> Any:
    return {
      "mode": self.mode,
      "times": self.times,
      "duration": self.duration,
      "delay": self.delay,
      "button": self.button,
      "position": [self.position_lock, self.position_x, self.position_y]
    }

  def deserialize(self, data: Any) -> None:
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
    def __init__(self, action: "ActionCopy") -> None:
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.action = action

      label = Gtk.Label(label="内容")
      self.pack_start(label, False, True, 0)
      label.show()

      textview = Gtk.TextView()
      self.pack_start(textview, False, True, 0)
      textview.show()

      self.buffer = textview.get_buffer()
      self.buffer.connect("changed", self.buffer_changed)

    def update(self) -> None:
      self.buffer.set_text(self.action.text)
    
    def buffer_changed(self, entry: Gtk.Entry) -> None:
      self.action.text = self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), False)

  ID = "copy"
  NAME = "复制"

  def __init__(self) -> None:
    self.text = ""

  def exec(self) -> None:
    GLib.idle_add(self.do_exec)

  def do_exec(self) -> None:
    CLIPBOARD.set_text(self.text, -1)
    CLIPBOARD.store()

  def serialize(self) -> Any:
    return self.text

  def deserialize(self, data: Any) -> None:
    self.text = data

class ActionType(Action):
  class ConfigWidget(Gtk.Box):
    def __init__(self, action: "ActionType") -> None:
      super().__init__(orientation=Gtk.Orientation.VERTICAL)
      self.action = action

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

    def update(self) -> None:
      self.interval_spin.set_value(self.action.interval)
      self.entry.set_text(self.action.text)

    def interval_changed(self, spin: Gtk.SpinButton) -> None:
      self.action.interval = spin.get_value()
    
    def entry_changed(self, entry: Gtk.Entry) -> None:
      self.action.text = entry.get_text()

  ID = "type"
  NAME = "输入文本（仅限英文）"

  def __init__(self) -> None:
    self.text = ""
    self.interval = 0

  def exec(self) -> None:
    # TODO: interval?
    KEYBOARD.type(self.text)

  def serialize(self) -> Any:
    return {
      "text": self.text,
      "interval": self.interval
    }

  def deserialize(self, data: Any) -> None:
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
  def __init__(self) -> None:
    super().__init__(title="连点器")
    self.set_default_size(800, 600)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    self.add(vbox)
    vbox.show()

    self.scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
    vbox.pack_start(self.scrolled, True, True, 0)
    self.scrolled.show()

    vbox2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    self.scrolled.add(vbox2)
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

    self.import_button = Gtk.Button(label="导入")
    self.import_button.connect("clicked", self.import_clicked)
    hbox.pack_start(self.import_button, True, True, 0)
    self.import_button.show()

    button = Gtk.Button(label="导出")
    button.connect("clicked", self.export_clicked)
    hbox.pack_start(button, True, True, 0)
    button.show()
    
    self.toggle_button = Gtk.Button(label="开始")
    self.toggle_button.connect("clicked", self.toggle_clicked)
    hbox.pack_start(self.toggle_button, True, True, 0)
    self.toggle_button.show()

    self.actions = list[Action]()
    self.running = False

  def add_action(self, index: int) -> tuple[Action, Gtk.Widget]:
    def up(button: Gtk.Button) -> None:
      pos = self.actions.index(action)
      if pos > 0:
        self.actions[pos], self.actions[pos - 1] = self.actions[pos - 1], self.actions[pos]
        pos -= 1
        self.action_box.reorder_child(box, pos)

    def down(button: Gtk.Button) -> None:
      pos = self.actions.index(action)
      if pos < len(self.actions) - 1:
        self.actions[pos], self.actions[pos + 1] = self.actions[pos + 1], self.actions[pos]
        pos += 1
        self.action_box.reorder_child(box, pos)

    def delete(button: Gtk.Button) -> None:
      self.actions.remove(action)
      box.destroy()

    def change(combo: Gtk.ComboBoxText) -> None:
      nonlocal action
      new_action = ACTIONS[store[combo.get_active()][0]]()
      if action is not None:
        cast(Gtk.Widget, config_wrap.get_child()).destroy()
        self.actions[self.actions.index(action)] = new_action
      else:
        self.actions.append(new_action)
      action = new_action
      widget = action.ConfigWidget(cast(Any, action))
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
    action = cast(Action, None)
    combo.set_active(index)

    return (action, cast(Gtk.Widget, config_wrap.get_child()))

  def trigger_changed(self, combo: Gtk.ComboBoxText) -> None:
    self.trigger = TRIGGERS[self.trigger_store[combo.get_active()][0]]()
    if child := self.trigger_wrap.get_child():
      child.destroy()
    child = self.trigger.ConfigWidget(self.trigger)
    self.trigger_wrap.add(child)
    child.show()

  def add_clicked(self, button: Gtk.Button) -> None:
    self.add_action(0)

  def import_clicked(self, button: Gtk.Button) -> None:
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
    if response != Gtk.ResponseType.OK or not filename:
      return
    with open(filename, "r") as f:
      data = json.load(f)
    self.trigger_combo.set_active(TRIGGERS_INDEX[data["trigger"][0]])
    self.trigger.deserialize(data["trigger"][1])
    cast(Action.ConfigWidget, self.trigger_wrap.get_child()).update()
    self.actions.clear()
    self.action_box.foreach(Gtk.Widget.destroy)
    for (name, config) in data["actions"]:
      action, widget = self.add_action(name)
      action.deserialize(config)
      cast(Action.ConfigWidget, widget).update()

  def export_clicked(self, button: Gtk.Button) -> None:
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
    if dialog.run() == Gtk.ResponseType.OK and (filename := dialog.get_filename()) is not None:
      with open(filename, "w") as f:
        json.dump({
          "trigger": [self.trigger.ID, self.trigger.serialize()],
          "actions": [[i.ID, i.serialize()] for i in self.actions]
        }, f)
    dialog.destroy()

  def toggle_clicked(self, button: Gtk.Button) -> None:
    if self.running:
      self.trigger.stop()
    else:
      self.running = True
      self.toggle_button.set_label("停止")
      self.scrolled.set_sensitive(False)
      self.import_button.set_sensitive(False)
      self.trigger.start(self.trigger_action, self.trigger_stop)

  def trigger_action(self) -> None:
    for i in self.actions:
      try:
        i.exec()
      except Exception:
        traceback.print_exc()

  def trigger_stop(self) -> None:
    self.running = False
    self.toggle_button.set_label("开始")
    self.scrolled.set_sensitive(True)
    self.import_button.set_sensitive(True)

if __name__ == "__main__":
  window = MainWindow()
  window.connect("destroy", Gtk.main_quit)
  window.show()
  Gtk.main()
