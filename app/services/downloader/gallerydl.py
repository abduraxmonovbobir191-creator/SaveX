import glob
import logging
import os
import shutil
import subprocess
import sys
import uuid

from app.services.cookies import cookie_file_for

log = logging.getLogger(__name__)

MEDIA_EXT = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv")
MAX_FILES = 20  # Instagram carousels have up to 20 items; the caller sends them in albums of 10


class GalleryDlError(Exception):
    """gallery-dl failed without producing files. The message is its stderr tail
    (it contains no cookie data), used to classify the failure (login redirect, ...)."""


def download_sync(url: str, chat_id: int, dest: str | None = None):
    """Download up to MAX_FILES media files. With `dest` the caller owns (and deletes) the
    folder; without it a private temp folder is created and removed again when nothing was
    found. Raises GalleryDlError when it failed and produced no files."""
    own_dest = dest is None
    if own_dest:
        dest = f"storage/temp/gdl_{chat_id}_{uuid.uuid4().hex[:8]}"
    os.makedirs(dest, exist_ok=True)

    cmd = [sys.executable, "-m", "gallery_dl", "-q", "-D", dest,
           "--range", f"1-{MAX_FILES}", "-R", "1", "-o", "sleep-429=2"]
    cookies = cookie_file_for(url)
    if cookies:
        cmd += ["--cookies", cookies]
    cmd.append(url)

    error = None
    try:
        res = subprocess.run(cmd, timeout=40, capture_output=True)
        if res.returncode != 0:
            error = res.stderr.decode(errors="ignore")[-300:].strip() or f"exit code {res.returncode}"
            log.info("[gallery-dl] %s", error)
    except subprocess.TimeoutExpired:
        log.info("[gallery-dl] timeout")

    files = [
        f for f in glob.glob(os.path.join(dest, "*"))
        if os.path.isfile(f) and f.lower().endswith(MEDIA_EXT)
    ]
    if not files and own_dest:
        shutil.rmtree(dest, ignore_errors=True)
    if not files and error:
        raise GalleryDlError(error)
    return sorted(files, key=os.path.getmtime)
