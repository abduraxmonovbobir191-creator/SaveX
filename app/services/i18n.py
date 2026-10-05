import json
import os

DEFAULT_LANG = "uz"
SUPPORTED_LANGS = ("uz", "ru", "en")
_LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "locales")
_cache: dict[str, dict] = {}


def _load(lang: str) -> dict:
    if lang not in _cache:
        try:
            with open(os.path.join(_LOCALES_DIR, f"{lang}.json"), encoding="utf-8") as f:
                _cache[lang] = json.load(f)
        except (OSError, ValueError):
            _cache[lang] = {}
    return _cache[lang]


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Localized text by key. Falls back to Uzbek, then to the key itself."""
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    text = _load(lang).get(key) or _load(DEFAULT_LANG).get(key) or key
    return text.format(**kwargs) if kwargs else text


async def get_user_lang(telegram_id: int) -> str:
    from app.database.session import async_session
    from app.database import crud

    try:
        async with async_session() as session:
            user = await crud.get_user(session, telegram_id)
        return user.language if user and user.language in SUPPORTED_LANGS else DEFAULT_LANG
    except Exception:
        return DEFAULT_LANG
