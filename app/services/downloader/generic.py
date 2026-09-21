import yt_dlp

from app.services.downloader.common import base_opts, run_download


def download_sync(
    url: str,
    height=None,
    audio_only=False,
    output=None,
):
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
        return run_download(opts, url)

    if height:
        opts["format"] = (
            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]"
        )
    else:
        opts["format"] = (
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080]"
        )

    opts["merge_output_format"] = "mp4"

    try:
        return run_download(opts, url)
    except yt_dlp.utils.DownloadError:
        fallback = base_opts()

        if output:
            fallback["outtmpl"] = output

        fallback["format"] = "best"

        return run_download(fallback, url)
