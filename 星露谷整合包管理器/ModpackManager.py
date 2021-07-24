#!/usr/bin/python3
import gi
import os
import sys
import subprocess
import subprocess
import shutil
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

if hasattr(sys, "_MEIPASS"):
  DIR = os.path.abspath(os.path.dirname(sys.executable))
else:
  DIR = os.path.abspath(os.path.dirname(__file__))
MODPACKS_DIR = os.path.join(DIR, "Modpacks")
MODS_DIR = os.path.join(DIR, "Mods")
if sys.platform == "win32":
  COMMAND = os.path.join(DIR, "StardewModdingAPI")
else:
  COMMAND = os.path.join(DIR, "StardewValley")

class ModpackEditDialog(Gtk.Dialog):
  def __init__(self, parent, name, mods):
    super().__init__(parent, title=f"编辑整合包\"{name}\"")
    self.set_default_size(300, 400)

    self.liststore = Gtk.ListStore(str, bool)
    self.mods = mods
    for i in sorted(mods.items()):
      self.liststore.append(i)

    scrolled = Gtk.ScrolledWindow()
    self.get_content_area().pack_start(scrolled, True, True, 0)
    scrolled.show()

    treeview = Gtk.TreeView(model=self.liststore, headers_visible=False)
    scrolled.add(treeview)
    treeview.show()

    self.toggle = Gtk.CellRendererToggle()
    self.toggle.connect("toggled", self.on_toggled)
    treeview.append_column(Gtk.TreeViewColumn("启用", self.toggle, active=1))
    treeview.append_column(Gtk.TreeViewColumn("名称", Gtk.CellRendererText(), text=0))
  
  def on_toggled(self, widget, path):
    name = self.liststore[path][0]
    self.liststore[path][1] = self.mods[name] = not self.mods[name]

class MainWindow(Gtk.Window):
  def __init__(self):
    super().__init__(title="选择整合包")
    self.set_default_size(300, 400)
    self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

    headerbar = Gtk.HeaderBar(show_close_button=True)
    self.set_titlebar(headerbar)
    headerbar.show()

    add_button = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
    add_button.connect("clicked", lambda w: self.add_modpack())
    headerbar.pack_start(add_button)
    add_button.show()

    scrolled = Gtk.ScrolledWindow()
    self.add(scrolled)
    scrolled.show()

    self.modpack_items = {}
    self.listbox = Gtk.ListBox()
    scrolled.add(self.listbox)
    self.listbox.show()

    for i in os.listdir(MODPACKS_DIR):
      self.show_modpack(i)

  def add_modpack(self):
    dialog = Gtk.MessageDialog(
      parent=self, 
      text="输入整合包名",
      message_type=Gtk.MessageType.QUESTION,
      buttons=Gtk.ButtonsType.OK_CANCEL
    )
    entry = Gtk.Entry()
    dialog.get_message_area().add(entry)
    entry.show()

    if dialog.run() == Gtk.ResponseType.OK:
      name = entry.get_text()
      modpack_dir = os.path.join(MODPACKS_DIR, name)
      if os.path.exists(modpack_dir):
        dialog2 = Gtk.MessageDialog(
          parent=dialog,
          text="整合包已存在",
          message_type=Gtk.MessageType.ERROR,
          buttons=Gtk.ButtonsType.OK
        )
        dialog2.run()
        dialog2.destroy()
      else:
        os.makedirs(modpack_dir)
        self.show_modpack(name)
    dialog.destroy()
  
  def show_modpack(self, name):
    row = Gtk.ListBoxRow()
    self.listbox.add(row)
    self.modpack_items[name] = row
    row.show()

    box = Gtk.Box()
    row.add(box)
    box.show()

    label = Gtk.Label(label=name, xalign=0)
    box.pack_start(label, True, True, 8)
    label.show()

    edit_button = Gtk.Button.new_from_icon_name("document-edit", Gtk.IconSize.BUTTON)
    edit_button.connect("clicked", lambda w: self.edit_modpack(name))
    box.pack_start(edit_button, False, False, 0)
    edit_button.show()

    launch_button = Gtk.Button.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
    launch_button.connect("clicked", lambda w: self.launch_modpack(name))
    box.pack_start(launch_button, False, False, 0)
    launch_button.show()
  
  def edit_modpack(self, name):
    mods = dict.fromkeys(os.listdir(MODS_DIR), False)
    mods_dir = os.path.join(MODPACKS_DIR, name, "Mods")
    if os.path.exists(mods_dir):
      mods |= dict.fromkeys(os.listdir(mods_dir), True)

    dialog = ModpackEditDialog(self, name, mods)
    dialog.add_button("_Delete", 1)
    dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("_Ok", Gtk.ResponseType.OK)

    response = dialog.run()
    if response == Gtk.ResponseType.OK:
      if not os.path.exists(mods_dir):
        os.makedirs(mods_dir)
      for i in os.listdir(mods_dir):
        os.remove(os.path.join(mods_dir, i))
      for i, enabled in mods.items():
        if enabled:
          os.symlink(os.path.join(MODS_DIR, i), os.path.join(mods_dir, i))
    elif response == 1:
      self.delete_modpack(name, dialog)
    dialog.destroy()
  
  def delete_modpack(self, name, parent):
    dialog = Gtk.MessageDialog(
      parent=parent,
      text=f"是否要删除\"{name}\"？",
      secondary_text="所有的存档都会被删除！",
      message_type=Gtk.MessageType.QUESTION,
      buttons=Gtk.ButtonsType.OK_CANCEL
    )
    if dialog.run() == Gtk.ResponseType.OK:
      shutil.rmtree(os.path.join(MODPACKS_DIR, name))
      self.listbox.remove(self.modpack_items[name])
      del self.modpack_items[name]
    dialog.destroy()

  def launch_modpack(self, name):
    modpack_dir = os.path.join(MODPACKS_DIR, name)
    os.environ["XDG_CONFIG_HOME"] = modpack_dir
    os.environ["USERPROFILE"] = modpack_dir
    os.environ["SMAPI_MODS_PATH"] = os.path.join(modpack_dir, "Mods")
    subprocess.Popen([COMMAND])
    self.close()

if __name__ == "__main__":
  if not os.path.exists(MODPACKS_DIR):
    os.makedirs(MODPACKS_DIR)
  if os.getenv("LC_ALL") == "C":
    os.environ["LC_ALL"] = os.getenv("LANG")
  window = MainWindow()
  window.connect("destroy", Gtk.main_quit)
  window.show()
  Gtk.main()
