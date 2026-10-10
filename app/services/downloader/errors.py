"""Map yt-dlp / gallery-dl failures to locale keys (see locales/*.json)."""


class TooLargeError(Exception):
    """The media is bigger than Telegram's upload limit (or yt-dlp skipped it)."""


_RULES = (
    ("err_too_large", ("larger than", "max-filesize", "too large", "too big", "exceeds")),
    ("err_private", ("private", "protected", "only available for registered users who follow")),
    ("err_login", ("sign in", "not a bot", "login", "log in", "cookies", "checkpoint",
                   "confirm your age", "age-restricted", "age restricted", "inappropriate for some users",
                   "authentication", "empty media response")),
    ("err_unsupported", ("unsupported url",)),
    ("err_no_media", ("no video could be found", "no video in this post", "no video formats",
                      "requested format is not available", "no media")),
    ("err_unavailable", ("unavailable", "has been removed", "been deleted", "does not exist",
                         "no longer available", "not available", "404", "not found")),
)


def classify_error(exc: BaseException) -> str:
    if isinstance(exc, TooLargeError):
        return "err_too_large"
    msg = str(exc).lower()
    for key, needles in _RULES:
        if any(n in msg for n in needles):
            return key
    return "err_generic"
