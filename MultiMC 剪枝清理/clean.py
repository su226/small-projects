import ctypes.util
import json
import os
import re
from argparse import ArgumentParser
from itertools import chain
from pathlib import Path
from typing import Any, Generator

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio

OBJECT_HASH = re.compile(r"^[0-9a-f]{40}$")
LIBC = ctypes.CDLL(ctypes.util.find_library("c"))


def normalize_library(name: str) -> Generator[str, Any, Any]:
  name = name.split("@", 1)[0]
  name = ":".join(name.split(":", 3)[:3])
  yield name
  if name.startswith("de.oceanlabs.mcp:mcp_config:"):
    yield f"net.minecraft:client:{name[28:]}"


def print_lr(left: str, right: str) -> str:
  pad = max(1, os.get_terminal_size().columns - LIBC.wcswidth(left) - LIBC.wcswidth(right))
  print(f"{left}{pad * ' '}{right}")


def format_size(size: int) -> str:
  size /= 1024
  return f"{size:.1f} KiB" if size < 1024 else f"{size / 1024:.1f} MiB"


def remove_trash(path: Path) -> None:
  Gio.File.new_for_path(str(path)).trash()


def remove_noop(path: Path) -> None:
  pass


def main() -> None:
  parser = ArgumentParser()
  parser.add_argument("--dry-run", "-n", action="store_true")
  args = parser.parse_args()
  total_size = 0
  remove = remove_noop if args.dry_run else remove_trash

  def clean_logs(base: Path) -> None:
    nonlocal total_size
    for root, _, files in base.walk():
      rel_root = root.relative_to(base)
      for file in files:
        if (
          rel_root.parts[:1] == ("logs",)
          or rel_root.parts[:1] == ("crash-reports",)
          or file.endswith(".log")
          or file.endswith(".log.gz")
        ):
          path = root / file
          total_size += (size := path.stat().st_size)
          print_lr(f"Log: {path}", format_size(size))
          remove(path)

  metadatas = set[Path]()
  for instance in Path("instances").iterdir():
    if not instance.is_dir():
      continue
    if (inst := instance / "mmc-pack.json").is_file():
      with inst.open() as f:
        data = json.load(f)
      for component in data["components"]:
        uid = component["uid"]
        if (meta := instance / "patches" / f"{uid}.json").is_file():
          metadatas.add(meta)
        else:
          version = component["cachedVersion"]
          if (meta := Path("meta", uid, f"{version}.json")).is_file():
            metadatas.add(meta)
    if (dir := instance / ".minecraft").is_dir():
      clean_logs(dir)
    if (dir := instance / "minecraft").is_dir():
      clean_logs(dir)

  libraries = set[str]()
  asset_indices = set[str]()
  for meta in metadatas:
    with meta.open() as f:
      data = json.load(f)
    if "mainJar" in data:
      libraries.update(normalize_library(data["mainJar"]["name"]))
    if "libraries" in data:
      libraries.update(chain.from_iterable(normalize_library(library["name"]) for library in data["libraries"]))
    if "mavenFiles" in data:
      libraries.update(chain.from_iterable(normalize_library(library["name"]) for library in data["mavenFiles"]))
    if "assetIndex" in data:
      asset_indices.add(data["assetIndex"]["id"])

  base = Path("libraries")
  for root, dirs, files in base.walk():
    if dirs or not files:
      continue
    *namespace, name, version = root.relative_to(base).parts
    identifier = f"{'.'.join(namespace)}:{name}:{version}"
    if identifier not in libraries:
      total_size += (size := sum((root / file).stat().st_size for file in files))
      print_lr(f"Unused library: {identifier}", format_size(size))
      remove(root)
  if not args.dry_run:
    for root, dirs, files in base.walk(False):
      if not any((root / child).exists() for child in chain(dirs, files)):
        root.rmdir()

  for uid in Path("meta").iterdir():
    if not uid.is_dir():
      continue
    for version in uid.iterdir():
      if not version.is_file() or version.name == "index.json":
        continue
      if version not in metadatas:
        total_size += (size := version.stat().st_size)
        print_lr(f"Unused metadata: {version}", format_size(size))
        remove(version)

  assets = set[str]()
  for index in Path("assets", "indexes").iterdir():
    if not index.is_file():
      continue
    if index.stem not in asset_indices:
      total_size += (size := index.stat().st_size)
      print_lr(f"Unused asset index: {index}", format_size(size))
      remove(index)
      continue
    with index.open() as f:
      data = json.load(f)
    for obj in data["objects"].values():
      assets.add(obj["hash"])

  for i in range(256):
    prefix = f"{i:02x}"
    dir = Path("assets", "objects", prefix)
    if not dir.is_dir():
      continue
    for obj in dir.iterdir():
      if not (obj.is_file() and OBJECT_HASH.fullmatch(obj.name)):
        continue
      if obj.name not in assets:
        total_size += (size := obj.stat().st_size)
        print_lr(f"Unused asset: {obj.name}", format_size(size))
        remove(obj)

  print_lr("Total size", format_size(total_size))

if __name__ == "__main__":
  main()
