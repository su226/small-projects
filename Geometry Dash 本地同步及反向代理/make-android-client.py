#!/usr/bin/python3
import base64
import os
import sys
from urllib.parse import urlparse

ORIG_URL_HTTPS = "https://www.boomlings.com/database"
ORIG_URL_HTTP = urlparse(ORIG_URL_HTTPS)._replace(scheme="http").geturl()
ORIG_PACKAGE = "com.robtopx.geometryjump"
EXECUTABLE = "libcocos2dcpp.so"

name = input("Server name: ")
url = input("Server URL: ").rstrip("/")
package = input("Package name (empty for unchanged): ")

if len(url) < len(ORIG_URL_HTTPS):
  replace_url_http = url.ljust(len(ORIG_URL_HTTP), "/")
  replace_url_https = url.ljust(len(ORIG_URL_HTTPS), "/")
elif len(url) == len(ORIG_URL_HTTPS) and (parsed_url := urlparse(url)).scheme == "https":
  replace_url_http = parsed_url._replace(scheme="http").geturl()
  replace_url_https = url
  del parsed_url
else:
  print(f"URL is too long. Max length for HTTP URL is {len(ORIG_URL_HTTP)} characters, for HTTPS URL is {len(ORIG_URL_HTTPS)} characters. Current URL {url!r} is {len(url)} characters.")
  sys.exit(1)

if package and len(package) != len(ORIG_PACKAGE):
  print(f"Package name should be EXACTLY {len(ORIG_PACKAGE)} characters. Current package name {package!r} is {len(package)} characters.")

if not os.path.isfile(f"{EXECUTABLE}"):
  print(f"{EXECUTABLE} not found.")
  sys.exit(1)

with open(f"{EXECUTABLE}", "rb") as f:
  data = f.read()
  orig_len = len(data)

  bytes_orig_url_https = ORIG_URL_HTTPS.encode()
  bytes_replace_url_https = replace_url_https.encode()
  assert len(bytes_orig_url_https) == len(bytes_replace_url_https)
  if bytes_orig_url_https not in data:
    print(f"{ORIG_URL_HTTPS!r} not found in {EXECUTABLE}, is it valid or already patched?")
    sys.exit(1)
  data = data.replace(bytes_orig_url_https, bytes_replace_url_https)

  base64_orig_url_http = base64.b64encode(ORIG_URL_HTTP.encode())
  base64_replace_url_http = base64.b64encode(replace_url_http.encode())
  assert len(base64_orig_url_http) == len(base64_replace_url_http)
  if base64_orig_url_http not in data:
    print(f"{base64_orig_url_http.decode()!r} (base64 of {ORIG_URL_HTTP!r}) not found in {EXECUTABLE}, is it valid or already patched?")
    sys.exit(1)
  data = data.replace(base64_orig_url_http, base64_replace_url_http)

  if package:
    orig_data_dir = f"/data/data/{ORIG_PACKAGE}/".encode()
    replace_data_dir = f"/data/data/{package}/".encode()
    assert len(orig_data_dir) == len(replace_data_dir)
    if orig_data_dir not in data:
      print(f"{orig_data_dir.decode()!r} not found in {EXECUTABLE}, is it valid or already patched?")
      sys.exit(1)
    data = data.replace(orig_data_dir, replace_data_dir)

  assert len(data) == orig_len

with open(f"{name}{os.path.splitext(EXECUTABLE)[1]}", "wb") as f:
  f.write(data)
  print(f"Writed executable at {f.name}")
