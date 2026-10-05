"""Login cookies per platform, shared by yt-dlp and gallery-dl.

File for a platform: env `<PLATFORM>_COOKIES` (e.g. INSTAGRAM_COOKIES), default
`<project>/cookies/<platform>.txt` (on the server: /opt/bots/SaveX/cookies/instagram.txt).
Without a platform file the legacy `storage/cookies.txt` is used for every URL.

Cookie contents are never read beyond the first line and never logged.
"""
import logging
import os
import shutil
import time
from urllib.parse import urlparse

from config import ADMIN_IDS, COOKIES_DIR
from app.services.i18n import t, get_user_lang

log = logging.getLogger(__name__)

LEGACY_COOKIES = os.path.join("storage", "cookies.txt")
ALERT_INTERVAL_SECONDS = 600

PLATFORM_TITLES = {
    "instagram": "Instagram",
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "twitter": "Twitter/X",
    "pinterest": "Pinterest",
}
_HOSTS = {
    "instagram": ("instagram.com",),
    "youtube": ("youtube.com", "youtu.be", "youtube-nocookie.com"),
    "tiktok": ("tiktok.com",),
    "twitter": ("twitter.com", "x.com"),
    "pinterest": ("pin.it",),
}

_last_alert: dict[str, float] = {}


def platform_of(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    if "pinterest." in host:
        return "pinterest"
    for platform, domains in _HOSTS.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return platform
    return None


def platform_cookie_path(platform: str) -> str:
    return os.getenv(f"{platform.upper()}_COOKIES") or os.path.join(COOKIES_DIR, f"{platform}.txt")


def _looks_like_netscape(path: str) -> bool:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            head = f.readline()
    except OSError:
        return False
    return head.startswith("# Netscape") or head.startswith("# HTTP Cookie")


def cookie_file_for(url: str) -> str | None:
    """Path of a usable cookies file for this URL, or None."""
    platform = platform_of(url)
    candidates = ([platform_cookie_path(platform)] if platform else []) + [LEGACY_COOKIES]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        if _looks_like_netscape(path):
            return path
        log.warning("[cookies] %s is not in Netscape format (first line must start with "
                    "'# Netscape HTTP Cookie File'), ignoring it", path)
    return None


def copy_for_ytdlp(url: str, dest_dir: str) -> str | None:
    """Private copy for one yt-dlp job. yt-dlp writes the jar back on exit; with a shared file
    parallel jobs could corrupt it. The copy lives in the job dir and is deleted with it."""
    src = cookie_file_for(url)
    if not src:
        return None
    dst = os.path.join(dest_dir, "cookies.txt")
    try:
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o600)
    except OSError as e:
        log.warning("[cookies] cannot copy cookies for yt-dlp: %r", e)
        return None
    return dst


async def alert_admins(bot, platform: str) -> None:
    """Tell the admins that a platform's cookies are missing/expired, at most once per
    ALERT_INTERVAL_SECONDS per platform."""
    now = time.monotonic()
    last = _last_alert.get(platform)
    if last is not None and now - last < ALERT_INTERVAL_SECONDS:
        return
    _last_alert[platform] = now  # set before any await: concurrent failures alert once

    missing = not os.path.isfile(platform_cookie_path(platform)) and not os.path.isfile(LEGACY_COOKIES)
    key = "admin_cookies_missing" if missing else "admin_cookies_expired"
    for admin_id in ADMIN_IDS:
        lang = await get_user_lang(admin_id)
        text = t(key, lang, platform=PLATFORM_TITLES.get(platform, platform), file=f"cookies/{platform}.txt")
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            log.warning("[cookies] cannot alert admin %s: %r", admin_id, e)
