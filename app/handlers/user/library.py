from aiogram import Router, F
from aiogram.types import Message
from app.database.session import async_session
from app.database import crud
from app.keyboards.reply import main_menu_kb

router = Router()

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
