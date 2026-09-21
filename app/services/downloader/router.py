from urllib.parse import urlparse


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    host = host.removeprefix("www.")

    if "instagram.com" in host:
        return "instagram"

    if "threads.net" in host or "threads.com" in host:
        return "threads"

    if "tiktok.com" in host:
        return "tiktok"

    if "pinterest." in host:
        return "pinterest"

    if "twitter.com" in host or host == "x.com":
        return "twitter"

    if "wikipedia.org" in host:
        return "wikipedia"

    if "linkedin.com" in host:
        return "linkedin"

    if "vk.com" in host or "vkvideo.ru" in host:
        return "vk_video"

    if "youtube.com" in host or host == "youtu.be":
        return "youtube"

    if "capcut.com" in host:
        return "capcut"

    if "canva.com" in host:
        return "canva"

    if "edits.com" in host:
        return "edits"

    if "toki" in host:
        return "toki"

    if "facebook.com" in host or "fb.watch" in host:
        return "facebook"

    if "t.me" in host or "telegram.me" in host:
        return "telegram"

    return "generic"


def detect_instagram_type(url: str) -> str:
    path = urlparse(url).path.lower()

    if "/reel/" in path or "/tv/" in path:
        return "video"

    if "/p/" in path:
        return "post"

    return "unknown"


def get_downloader(url: str):
    platform = detect_platform(url)

    # Instagram
    if platform == "instagram":
        ig_type = detect_instagram_type(url)

        if ig_type == "video":
            from app.services.downloader.instagram.video import download_sync
            return download_sync

        if ig_type == "post":
            from app.services.downloader.instagram.image import download_sync
            return download_sync

    # Hozircha qolgan platformalar generic downloaderga o'tadi.
    # Keyin har biriga o'z faylini beramiz.
    from app.services.downloader.generic import download_sync
    return download_sync
