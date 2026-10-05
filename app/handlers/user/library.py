from html import escape
from aiogram import Router, F
from aiogram.types import Message, LinkPreviewOptions
from app.database.session import async_session
from app.database import crud
from app.keyboards.reply import main_menu_kb
from app.services.i18n import t

router = Router()

HISTORY_LIMIT = 15


def _history_line(index: int, item) -> str:
    title = escape((item.title or "Media")[:60])
    url = (item.url or "").strip()
    if url.startswith(("http://", "https://")) and not any(c.isspace() for c in url):
        title = f'<a href="{escape(url, quote=True)}">{title}</a>'
    return f"{index}. {title} · {crud.to_tashkent_str(item.created_at)}"


async def _show_history(message: Message, media_type: str, prefix: str):
    async with async_session() as session:
        user = await crud.get_user(session, message.from_user.id)
        items = await crud.get_history_by_type(session, message.from_user.id, media_type, limit=HISTORY_LIMIT)
    lang = user.language if user else None

    if not items:
        await message.answer(t(f"{prefix}_empty", lang), parse_mode="HTML", reply_markup=main_menu_kb())
        return

    lines = [t(f"{prefix}_title", lang, count=len(items)), ""]
    lines += [_history_line(i, item) for i, item in enumerate(items, 1)]
    lines += ["", t("lib_hint", lang)]
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_menu_kb(),
                         link_preview_options=LinkPreviewOptions(is_disabled=True))


@router.message(F.text == "🎬 Videolarim")
async def show_my_videos(message: Message):
    await _show_history(message, "video", "lib_videos")


@router.message(F.text == "🎵 Musiqalarim")
async def show_my_music(message: Message):
    await _show_history(message, "audio", "lib_audio")


@router.message(F.text == "📋 Kutubxona")
async def show_library(message: Message):
    async with async_session() as session:
        items = await crud.get_history(session, message.from_user.id, limit=10)

    if not items:
        await message.answer("📋 <b>Kutubxona</b>\n\nHali hech narsa yuklamagansiz.",
                              parse_mode="HTML", reply_markup=main_menu_kb())
        return

    lines = ["📋 <b>Kutubxona</b> (oxirgi 10 ta)\n"]
    for item in items:
        emoji = "🎬" if item.media_type == "video" else "🖼"
        lines.append(f"{emoji} {item.title or 'Media'}")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_menu_kb())
