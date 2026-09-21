import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import yt_dlp


COOKIES_PATH = "storage/cookies.txt"

EXECUTOR = ThreadPoolExecutor(max_workers=8)
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(5)


def base_opts():
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "socket_timeout": 25,
        "retries": 2,
        "ignoreerrors": True,
    }

    if os.path.exists(COOKIES_PATH):
        opts["cookiefile"] = COOKIES_PATH

    return opts


def extract_info_sync(url: str):
    opts = base_opts()

    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def estimate_size(info: dict, height=None, audio_only=False):
    if audio_only:
        candidates = [
            f for f in info.get("formats", [])
            if f.get("acodec") != "none"
        ]

        if not candidates:
            return info.get("filesize") or info.get("filesize_approx")

        candidates.sort(
            key=lambda f: (
                f.get("abr") or 0,
                f.get("filesize") or f.get("filesize_approx") or 0,
            ),
            reverse=True,
        )

        f = candidates[0]
        return f.get("filesize") or f.get("filesize_approx")

    formats = info.get("formats", [])

    if not formats:
        return info.get("filesize") or info.get("filesize_approx")

    if height:
        video = [
            f for f in formats
            if f.get("vcodec") != "none"
            and (f.get("height") or 0) <= height
        ]
    else:
        video = [
            f for f in formats
            if f.get("vcodec") != "none"
            and (f.get("height") or 0) <= 1080
        ]

    audio = [
        f for f in formats
        if f.get("acodec") != "none"
        and f.get("vcodec") == "none"
    ]

    video.sort(
        key=lambda f: (
            f.get("height") or 0,
            f.get("fps") or 0,
            f.get("filesize") or f.get("filesize_approx") or 0,
        ),
        reverse=True,
    )

    audio.sort(
        key=lambda f: (
            f.get("abr") or 0,
            f.get("filesize") or f.get("filesize_approx") or 0,
        ),
        reverse=True,
    )

    if video and audio:
        vs = video[0].get("filesize") or video[0].get("filesize_approx")
        aus = audio[0].get("filesize") or audio[0].get("filesize_approx")

        if vs is not None and aus is not None:
            return vs + aus

    if video:
        return video[0].get("filesize") or video[0].get("filesize_approx")

    return info.get("filesize") or info.get("filesize_approx")


def run_download(opts: dict, url: str):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

        if not info:
            raise RuntimeError("Media topilmadi")

        filename = ydl.prepare_filename(info)

        if info.get("requested_downloads"):
            real = info["requested_downloads"][0].get("filepath")

            if real and os.path.exists(real):
                filename = real

        return info, filename


async def get_loop_run(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(EXECUTOR, func, *args)
