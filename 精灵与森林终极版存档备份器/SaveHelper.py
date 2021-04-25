#!/usr/bin/python3
import gi
import inotify.adapters
import os
import shutil
import subprocess
import sys
import threading
import time
import Xlib
import Xlib.display
import Xlib.ext
import Xlib.protocol
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

if sys.argv[1] != "--no-terminal":
  exit(subprocess.Popen(["gnome-terminal", "--", sys.argv[0], "--no-terminal", *sys.argv[1:]]).wait())

COMMAND = sys.argv[2:]
APP_ID = 387290
GAME_DIR = os.path.abspath(os.path.dirname(__file__))
SAVES_DIR = os.path.abspath(GAME_DIR + f"/../../compatdata/{APP_ID}/pfx/drive_c/users/steamuser/Local Settings/Application Data/Ori and the Blind Forest DE")
BACKUPS_DIR = GAME_DIR + "/backups"

skip_next = False
stop = False

def restore(filename):
  print(f"\033[96mRestore backup {filename}\033[0m")
  slot = filename[:filename.find("-")]
  target = f"{SAVES_DIR}/saveFile{slot}.sav"
  global skip_next
  skip_next = True
  shutil.copy(f"{BACKUPS_DIR}/{filename}", target)

def notify_main():
  i = inotify.adapters.Inotify()
  i.add_watch(SAVES_DIR)
  for event in i.event_gen():
    if stop:
      break
    if event is None:
      continue
    _, types, path, filename = event
    if not filename.startswith("saveFile"):
      continue
    if filename.find("bkup") != -1:
      continue
    if types[0] != "IN_CLOSE_WRITE":
      continue
    global skip_next
    if skip_next:
      skip_next = False
      continue
    slot = filename[8:-4]
    strtime = time.strftime("%Y_%m_%d-%H_%M_%S")
    bkpfile = f"{slot}-{strtime}.bak"
    shutil.copy(f"{SAVES_DIR}/{filename}", f"{BACKUPS_DIR}/{bkpfile}")
    print(f"\033[96mCreate backup {bkpfile}\033[0m")

def parse_backup(filename):
  str_slot, str_time = os.path.splitext(filename)[0].split("-", 1)
  slot = int(str_slot) + 1
  parsed_time = time.strptime(str_time, "%Y_%m_%d-%H_%M_%S")
  timestamp = time.mktime(parsed_time)
  display_time = time.strftime("%Y-%m-%d %H:%M:%S", parsed_time)
  return (timestamp, filename, slot, display_time)

def gui_main():
  dialog = Gtk.Dialog()
  dialog.set_default_size(200, 300)
  dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
  dialog.add_button("_Ok", Gtk.ResponseType.OK)
  
  scrolled = Gtk.ScrolledWindow()
  dialog.get_content_area().pack_start(scrolled, True, True, 0)
  scrolled.show()

  liststore = Gtk.ListStore(str, int, str)
  for i in sorted(map(parse_backup, os.listdir(BACKUPS_DIR)), reverse=True):
    liststore.append(i[1:])

  treeview = Gtk.TreeView(model=liststore)
  treeview.append_column(Gtk.TreeViewColumn("Slot", Gtk.CellRendererText(), text=1))
  treeview.append_column(Gtk.TreeViewColumn("Time", Gtk.CellRendererText(), text=2))
  scrolled.add(treeview)
  treeview.show()

  if dialog.run() == Gtk.ResponseType.OK:
    index = treeview.get_cursor()[0]
    if index != None:
      restore(liststore[index][0])

  dialog.destroy()
  GLib.idle_add(Gtk.main_quit)
  Gtk.main() # HACK

def hotkey_main():
  def handle_keys(response):
    if stop:
      exit()
    data = response.data
    while len(data):
      event, data = field.parse_binary_value(data, display.display, None, None)
      if event.type == Xlib.X.KeyPress:
        pressed.add(event.detail)
        if pressed == keys:
          gui_main()
      elif event.type == Xlib.X.KeyRelease:
        pressed.remove(event.detail)

  keys = {37, 50, 27} # Ctrl + Shift + R
  pressed = set()
  display = Xlib.display.Display()
  field = Xlib.protocol.rq.EventField(None)
  context = display.record_create_context(
    0,
    [Xlib.ext.record.AllClients],
    [
      {
        'core_requests': (0, 0),
        'core_replies': (0, 0),
        'ext_requests': (0, 0, 0, 0),
        'ext_replies': (0, 0, 0, 0),
        'delivered_events': (0, 0),
        'device_events': (Xlib.X.KeyReleaseMask, Xlib.X.ButtonReleaseMask),
        'errors': (0, 0),
        'client_started': False,
        'client_died': False,
      }
    ]
  )
  display.record_enable_context(context, handle_keys)

if not os.path.exists(BACKUPS_DIR):
  os.mkdir(BACKUPS_DIR)

threading.Thread(target=notify_main).start()
threading.Thread(target=hotkey_main).start()
code = subprocess.Popen(COMMAND).wait()
stop = True
exit(code)
