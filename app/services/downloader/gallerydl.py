import glob
import os
import subprocess
import sys
import uuid

COOKIES_PATH = "storage/cookies.txt"
MEDIA_EXT = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv")


def download_sync(url: str, chat_id: int):
    dest = f"storage/temp/gdl_{chat_id}_{uuid.uuid4().hex[:8]}"
    os.makedirs(dest, exist_ok=True)

    cmd = [sys.executable, "-m", "gallery_dl", "-q", "-D", dest, "--range", "1-10"]
    if os.path.exists(COOKIES_PATH):
        cmd += ["--cookies", COOKIES_PATH]
    cmd.append(url)

    try:
        res = subprocess.run(cmd, timeout=90, capture_output=True)
        if res.returncode != 0:
            print("[gallery-dl]", res.stderr.decode(errors="ignore")[-300:])
    except subprocess.TimeoutExpired:
        print("[gallery-dl] timeout")

    files = [
        f for f in glob.glob(os.path.join(dest, "*"))
        if os.path.isfile(f) and f.lower().endswith(MEDIA_EXT)
    ]
    return sorted(files, key=os.path.getmtime)
