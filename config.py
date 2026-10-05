import os
import shutil
import time
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./storage/savex.db")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Login cookies (Netscape format), one file per platform: cookies/<platform>.txt.
# Gitignored and never touched by deploy.sh. See app/services/cookies.py.
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")

STORAGE_DIR = "storage"
TEMP_DIR = os.path.join(STORAGE_DIR, "temp")
STALE_TEMP_SECONDS = 3600


def ensure_runtime_dirs() -> None:
    """Create gitignored runtime dirs (storage/, storage/temp/, the SQLite DB folder)."""
    dirs = [STORAGE_DIR, TEMP_DIR]
    try:
        url = make_url(DATABASE_URL)
        if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
            dirs.append(os.path.dirname(os.path.abspath(url.database)))
    except Exception:
        pass
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    os.makedirs(COOKIES_DIR, mode=0o700, exist_ok=True)


def cleanup_stale_temp() -> None:
    """Remove temp leftovers of crashed/killed jobs (a kill can't run `finally`)."""
    cutoff = time.time() - STALE_TEMP_SECONDS
    try:
        entries = list(os.scandir(TEMP_DIR))
    except OSError:
        return
    for entry in entries:
        try:
            if entry.stat(follow_symlinks=False).st_mtime > cutoff:
                continue
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, ignore_errors=True)
            else:
                os.remove(entry.path)
        except OSError:
            pass
