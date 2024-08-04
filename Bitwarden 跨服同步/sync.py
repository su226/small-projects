#!/usr/bin/python3
import base64
import gzip
import hashlib
import json
import os
import subprocess as sp
import sys
import time
from tempfile import NamedTemporaryFile

import argon2
import requests
from loguru import logger

BACKUP_PASSWORD = ""
BACKUP_TTL = 30 * 24 * 60 * 60

SERVER_SRC = ""
EMAIL_SRC = ""
PASSWORD_SRC = ""
CLIENT_ID_SRC = ""
CLIENT_SECRET_SRC = ""

SERVER_DST = ""
EMAIL_DST = ""
PASSWORD_DST = ""
CLIENT_ID_DST = ""
CLIENT_SECRET_DST = ""

ENV_SRC = {
    "BITWARDENCLI_APPDATA_DIR": "src",
    "BW_CLIENTID": CLIENT_ID_SRC,
    "BW_CLIENTSECRET": CLIENT_SECRET_SRC,
}
ENV_DST = {
    "BITWARDENCLI_APPDATA_DIR": "dst",
    "BW_CLIENTID": CLIENT_ID_DST,
    "BW_CLIENTSECRET": CLIENT_SECRET_DST,
}

TIME = time.time()
TIME_STR = time.strftime("%Y-%m-%d-%H-%M-%S")

logger.info("Logging in source vault.")
if sp.run(["bw", "config", "server"], env=ENV_SRC, check=True, stdout=sp.PIPE, text=True).stdout != SERVER_SRC:
    sp.run(["bw", "logout", "--raw"], env=ENV_SRC, stderr=sp.DEVNULL)
    sp.run(["bw", "config", "server", SERVER_SRC, "--raw"], env=ENV_SRC, check=True)
    sp.run(["bw", "login", EMAIL_SRC, "--apikey", "--raw"], env=ENV_SRC, check=True)
# Exit code for already logged in and login failed are both 1, run `bw login --check` first.
elif sp.run(["bw", "login", "--check", "--raw"], env=ENV_SRC, stderr=sp.DEVNULL).returncode != 0:
    sp.run(["bw", "login", EMAIL_SRC, "--apikey", "--raw"], env=ENV_SRC, check=True)

logger.info("Backing up source vault.")
ENV_SRC["BW_SESSION"] = sp.run(["bw", "unlock", PASSWORD_SRC, "--raw"], env=ENV_SRC, check=True, stdout=sp.PIPE, text=True).stdout
sp.run(["bw", "sync", "--raw"], env=ENV_SRC, check=True)
backup_src = sp.run(["bw", "export", "--format", "json", "--raw"], env=ENV_SRC, check=True, stdout=sp.PIPE, text=True).stdout
backup_src = json.dumps(json.loads(backup_src), separators=(",", ":"))
os.makedirs("src_backup", 0o700, True)
for file in os.scandir("src_backup"):
    if file.stat().st_mtime < TIME - BACKUP_TTL:
        os.remove(file.path)
os.makedirs("gnupg", 0o700, True)
sp.run(["gpg", "--homedir", "gnupg", "--symmetric", "--cipher-algo", "AES256", "--batch", "--passphrase", BACKUP_PASSWORD, "--output", f"src_backup/{TIME_STR}.json.gz.gpg"], input=gzip.compress(backup_src.encode()), check=True)

logger.info("Logging in destination vault.")
if sp.run(["bw", "config", "server"], env=ENV_DST, check=True, stdout=sp.PIPE, text=True).stdout != SERVER_DST:
    sp.run(["bw", "logout", "--raw"], env=ENV_DST, stderr=sp.DEVNULL)
    sp.run(["bw", "config", "server", SERVER_DST, "--raw"], env=ENV_DST, check=True)
    sp.run(["bw", "login", EMAIL_DST, "--apikey", "--raw"], env=ENV_DST, check=True)
elif sp.run(["bw", "login", "--check", "--raw"], env=ENV_DST, stderr=sp.DEVNULL).returncode != 0:
    sp.run(["bw", "login", EMAIL_DST, "--apikey", "--raw"], env=ENV_DST, check=True)

logger.info("Backing up destination vault.")
ENV_DST["BW_SESSION"] = sp.run(["bw", "unlock", PASSWORD_DST, "--raw"], env=ENV_DST, check=True, stdout=sp.PIPE, text=True).stdout
sp.run(["bw", "sync", "--raw"], env=ENV_DST, check=True)
backup_dst = sp.run(["bw", "export", "--format", "json", "--raw"], env=ENV_DST, check=True, stdout=sp.PIPE, text=True).stdout
backup_dst = json.dumps(json.loads(backup_dst), separators=(",", ":"))
os.makedirs("dst_backup", 0o700, True)
for file in os.scandir("dst_backup"):
    if file.stat().st_mtime < TIME - BACKUP_TTL:
        os.remove(file.path)
sp.run(["gpg", "--homedir", "gnupg", "--symmetric", "--cipher-algo", "AES256", "--batch", "--passphrase", BACKUP_PASSWORD, "--output", f"dst_backup/{TIME_STR}.json.gz.gpg"], input=gzip.compress(backup_dst.encode()), check=True)

logger.info("Purging destination vault.")
with open("dst/data.json") as f:
    data = json.load(f)
    uuid = data["global_account_activeAccountId"]
    kdf_config = data[f"user_{uuid}_kdfConfig_kdfConfig"]
    access_token = data[f"user_{uuid}_token_accessToken"]
match kdf := kdf_config["kdfType"]:
    case 0:  # PBKDF2
        enc_key = hashlib.pbkdf2_hmac("sha256", PASSWORD_DST.encode(), EMAIL_DST.encode(), kdf_config["iterations"])
    case 1:  # Argon2id
        enc_key = argon2.low_level.hash_secret_raw(
            secret=PASSWORD_DST.encode(),
            salt=hashlib.sha256(EMAIL_DST.encode()).digest(),
            time_cost=kdf_config["iterations"],
            memory_cost=kdf_config["memory"] * 1024,
            parallelism=kdf_config["parallelism"],
            hash_len=32,
            type=argon2.Type.ID,
            version=19
        )
    case _:
        raise NotImplementedError(f"Unknown KDF type: {kdf}")
master_password_hash = base64.b64encode(hashlib.pbkdf2_hmac("sha256", enc_key, PASSWORD_DST.encode(), 1)).decode()
response = requests.post(
    f"{SERVER_DST}/api/ciphers/purge",
    json={"masterPasswordHash": master_password_hash},
    headers={"authorization": f"Bearer {access_token}"}
)
if response.status_code != 200:
    logger.error(f"Failed to purge destination vault, status: {response.status_code}.")
    sys.exit(1)

logger.info("Syncing destination vault.")
sp.run(["bw", "sync", "--raw"], env=ENV_DST, check=True)
with NamedTemporaryFile("w") as f:
    f.write(backup_src)
    f.flush()
    sp.run(["bw", "import", "bitwardenjson", f.name, "--raw"], env=ENV_DST, check=True)
