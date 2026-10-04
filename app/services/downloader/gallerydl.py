import glob
import os
import shutil
import subprocess
import sys
import uuid

COOKIES_PATH = "storage/cookies.txt"
MEDIA_EXT = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv")


def _cookies_ok():
    try:
        with open(COOKIES_PATH, encoding="utf-8", errors="ignore") as f:
            head = f.readline()
        return head.startswith("# Netscape") or head.startswith("# HTTP Cookie")
    except OSError:
        return False


def download_sync(url: str, chat_id: int):
    dest = f"storage/temp/gdl_{chat_id}_{uuid.uuid4().hex[:8]}"
    os.makedirs(dest, exist_ok=True)

    cmd = [sys.executable, "-m", "gallery_dl", "-q", "-D", dest,
           "--range", "1-10", "-R", "1", "-o", "sleep-429=2"]
    if _cookies_ok():
        cmd += ["--cookies", COOKIES_PATH]
    cmd.append(url)

    try:
        res = subprocess.run(cmd, timeout=40, capture_output=True)
        if res.returncode != 0:
            print("[gallery-dl]", res.stderr.decode(errors="ignore")[-300:])
    except subprocess.TimeoutExpired:
        print("[gallery-dl] timeout")

    files = [
        f for f in glob.glob(os.path.join(dest, "*"))
        if os.path.isfile(f) and f.lower().endswith(MEDIA_EXT)
    ]
    if not files:
        shutil.rmtree(dest, ignore_errors=True)
    return sorted(files, key=os.path.getmtime)
