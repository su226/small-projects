#!/usr/bin/python3
from pykeyboard import PyKeyboard, PyKeyboardEvent
import ctypes
import gi
import os
import shutil
import subprocess
import sys
import threading
import time
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gio

COMMAND = sys.argv[1:]
APP_ID = 387290
GAME_DIR = os.path.abspath(os.path.dirname(__file__))
SAVES_DIR = ""

if sys.platform.startswith("linux"):
  SAVES_DIR = os.path.abspath(GAME_DIR + f"/../../compatdata/{APP_ID}/pfx/drive_c/users/steamuser/Local Settings/Application Data/Ori and the Blind Forest DE")
elif sys.platform == "win32":
  SAVES_DIR = f"{os.environ['APPDATA']}\\Ori and the Blind Forest DE"
else:
  Gtk.MessageDialog(type=Gtk.MessageType.ERROR, text="不支持的操作系统。", buttons=Gtk.ButtonsType.OK).run()
  exit()

BACKUPS_DIR = os.path.join(SAVES_DIR, "backups")
if not os.path.exists(BACKUPS_DIR):
  os.mkdir(BACKUPS_DIR)

class MainWindow(Gtk.Window):
  def __init__(self):
    super().__init__(title="还原备份")
    self.set_default_size(640, 480)
    self.set_deletable(False)
    self.skip_next = False
    self.exit_code = 0

    paned = Gtk.Paned()
    self.add(paned)
    paned.show()

    scrolled = Gtk.ScrolledWindow()
    paned.pack1(scrolled, True, False)
    scrolled.show()

    textview = Gtk.TextView()
    textview.set_editable(False)
    scrolled.add(textview)
    textview.show()

    self.buffer = textview.get_buffer()
    self.log("日志开始")
    
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    paned.pack2(vbox, False, False)
    vbox.show()

    scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
    vbox.pack_start(scrolled, True, True, 0)
    scrolled.show()

    self.store = Gtk.ListStore(str, int, str)
    listiter = self.store.append(["", 0, "1970-01-01 08:00:00"])
    for i in sorted(map(self.parse_backup, os.listdir(BACKUPS_DIR)), reverse=True):
      self.store.append(i[1:])
    GLib.idle_add(self.store.remove, listiter)

    self.treeview = Gtk.TreeView(model=self.store)
    self.treeview.append_column(Gtk.TreeViewColumn("存档", Gtk.CellRendererText(), text=1))
    self.treeview.append_column(Gtk.TreeViewColumn("时间", Gtk.CellRendererText(), text=2))
    scrolled.add(self.treeview)
    self.treeview.show()

    hbox = Gtk.Box()
    vbox.pack_start(hbox, False, True, 0)
    hbox.show()

    button = Gtk.Button(label="删除")
    button.connect("clicked", self.delete_clicked)
    hbox.pack_start(button, True, True, 0)
    button.show()

    button = Gtk.Button(label="还原")
    button.connect("clicked", self.restore_clicked)
    hbox.pack_start(button, True, True, 0)
    button.show()

    # 如果不保存FileMonitor，就不会生效（Bug？）
    self.monitor = Gio.File.new_for_path(SAVES_DIR).monitor(Gio.FileMonitorFlags.NONE, None)
    self.monitor.connect("changed", self.monitor_changed)

    threading.Thread(target=self.open_process).start()

  def open_process(self):
    self.exit_code = subprocess.Popen(COMMAND).wait()
    GLib.idle_add(self.close)    
  
  def delete_clicked(self, button):
    path = self.treeview.get_cursor()[0]
    if path is not None:
      filename = self.store[path][0]
      self.log(f"删除备份 {filename}")
      os.remove(os.path.join(BACKUPS_DIR, filename))
      self.store.remove(self.store.get_iter(path))

  def restore_clicked(self, button):
    path = self.treeview.get_cursor()[0]
    if path is not None:
      filename = self.store[path][0]
      self.log(f"还原备份 {filename}")
      slot = filename[:filename.find("-")]
      target = os.path.join(SAVES_DIR, f"saveFile{slot}.sav")
      self.skip_next = True
      shutil.copy(os.path.join(BACKUPS_DIR, filename), target)

  def monitor_changed(self, monitor, file, other, event):
    if event != Gio.FileMonitorEvent.CHANGES_DONE_HINT:
      return
    if self.skip_next:
      self.skip_next = False
      return
    name = file.get_basename()
    if not name.startswith("saveFile"):
      return
    if name.find("bkup") != -1:
      return
    slot = int(name[8:-4])
    filename_time = time.strftime("%Y_%m_%d-%H_%M_%S")
    display_time = time.strftime("%Y-%m-%d %H:%M:%S")
    filename = f"{slot}-{filename_time}.bak"
    self.log(f"创建备份 {filename}")
    shutil.copy(file.get_path(), os.path.join(BACKUPS_DIR, filename))
    self.store.insert(0, [filename, slot, display_time])

  def log(self, text):
    self.buffer.insert(self.buffer.get_end_iter(), f"{time.strftime('%H:%M:%S')} {text}\n")

  def parse_backup(self, filename):
    str_slot, str_time = os.path.splitext(filename)[0].split("-", 1)
    slot = int(str_slot) + 1
    parsed_time = time.strptime(str_time, "%Y_%m_%d-%H_%M_%S")
    timestamp = time.mktime(parsed_time)
    display_time = time.strftime("%Y-%m-%d %H:%M:%S", parsed_time)
    return (timestamp, filename, slot, display_time)

if __name__ == "__main__":
  window = MainWindow()
  window.connect("destroy", Gtk.main_quit)
  window.show()
  Gtk.main()
  exit(window.exit_code)
