import os

import yt_dlp

from app.services.downloader.common import base_opts, run_download


NO_VIDEO_SIGNALS = [
    "no video",
    "no video formats",
    "requested format is not available",
]


def download_sync(url: str, height=None, audio_only=False, output=None):
    opts = base_opts()

    if output:
        opts["outtmpl"] = output

    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }
        ]

        info, filename = run_download(opts, url)

        base = os.path.splitext(filename)[0]
        return info, base + ".mp3"

    opts["merge_output_format"] = "mp4"

    if height:
        opts["format"] = (
            f"bestvideo[height<={height}][ext=mp4]+"
            f"bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+"
            f"bestaudio/"
            f"best[height<={height}]"
        )
    else:
        opts["format"] = (
            "bestvideo[height<=1080][ext=mp4]+"
            "bestaudio[ext=m4a]/"
            "bestvideo[height<=1080]+"
            "bestaudio/"
            "best[height<=1080]"
        )

    try:
        return run_download(opts, url)

    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()

        if not any(signal in msg for signal in NO_VIDEO_SIGNALS):
            raise

        fallback = base_opts()

        if output:
            fallback["outtmpl"] = output

        fallback["format"] = "best"

        return run_download(fallback, url)
