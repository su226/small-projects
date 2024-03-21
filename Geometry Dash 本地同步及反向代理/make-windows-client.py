#!/usr/bin/python3
import base64
import os
import sys
from urllib.parse import urlparse

ORIG_URL_HTTPS = "https://www.boomlings.com/database"
ORIG_URL_HTTP = urlparse(ORIG_URL_HTTPS)._replace(scheme="http").geturl()

name = input("Server Name: ")
url = input("Server URL: ").rstrip("/")

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

if not os.path.isfile("GeometryDash.exe"):
  print("GeometryDash.exe not found.")
  sys.exit(1)

with open("GeometryDash.exe", "rb") as f:
  data = f.read()
  bytes_orig_url_https = ORIG_URL_HTTPS.encode()
  bytes_replace_url_https = replace_url_https.encode()
  assert len(bytes_orig_url_https) == len(bytes_replace_url_https)
  count = data.count(bytes_orig_url_https)
  if not count:
    print(f"{ORIG_URL_HTTPS!r} not found in GeometryDash.exe, is it valid or already patched?")
    sys.exit(1)
  data = data.replace(bytes_orig_url_https, bytes_replace_url_https)
  base64_orig_url_http = base64.b64encode(ORIG_URL_HTTP.encode())
  base64_replace_url_http = base64.b64encode(replace_url_http.encode())
  assert len(base64_orig_url_http) == len(base64_replace_url_http)
  count = data.count(base64_orig_url_http)
  if not count:
    print(f"{base64_orig_url_http.decode()!r} (base64 of {ORIG_URL_HTTP!r}) not found in GeometryDash.exe, is it valid or already patched?")
    sys.exit(1)
  data = data.replace(base64_orig_url_http, base64_replace_url_http)

with open(f"{name}.exe", "wb") as f:
  f.write(data)
  print(f"Writed executable at {f.name}")
