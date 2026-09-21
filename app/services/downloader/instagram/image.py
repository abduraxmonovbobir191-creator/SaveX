import os

from app.services.downloader.common import base_opts, run_download


def download_sync(url: str, output: str = None):
    opts = base_opts()

    if output:
        opts["outtmpl"] = output

    # Instagram oddiy rasm posti
    opts["format"] = "best"

    return run_download(opts, url)
