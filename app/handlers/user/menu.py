from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from app.keyboards.reply import main_menu_kb
from app.keyboards.inline import help_kb
from app.database.session import async_session
from app.database import crud

router = Router()

@router.message(F.text == "👤 Kabinetim")
async def cabinet(message: Message):
    async with async_session() as session:
        user = await crud.get_or_create_user(session, message.from_user.id, message.from_user.username,
                                              message.from_user.first_name, message.from_user.last_name)
        total = await crud.get_user_total_downloads(session, message.from_user.id)
        platform_rows = await crud.get_user_platform_stats(session, message.from_user.id)

    status, limit_text, expiry_line = "Free", "7", ""
    if user.is_premium and user.premium_until and user.premium_until > datetime.utcnow():
        status = user.premium_type.upper()
        limit_text = "30" if user.premium_type == "plus" else "Cheksiz"
        expiry_line = f"\n⏰ Tugash sanasi: {crud.to_tashkent_str(user.premium_until)}"

    stats_lines = "\n".join(f"  • {p}: {c} ta" for p, c in platform_rows) if platform_rows else "  Hali yo'q"

    await message.answer(
        f"👤 <b>Kabinetim</b>\n\nIsm: {message.from_user.first_name}\n"
        f"ID: <code>{message.from_user.id}</code>\nStatus: {status}\n"
        f"Yuklab olishlar: {user.daily_downloads} / {limit_text}{expiry_line}\n\n"
        f"📊 <b>Statistikangiz</b>\nJami yuklangan: {total} ta\n{stats_lines}",
        parse_mode="HTML", reply_markup=main_menu_kb())

@router.message(F.text == "❓ Yordam")
async def help_handler(message: Message):
    text = (
        "❓ <b>Yordam</b>\n\n"
        "Link yuboring — bot video, rasm yoki musiqani yuklab beradi.\n\n"
        "🌐 <b>Ishlaydigan platformalar:</b>\n"
        "📸 Instagram\n🎵 TikTok\n🐦 Twitter / X\n🧵 Threads\n"
        "📖 Wikipedia\n📌 Pinterest\nva boshqa ko'plab saytlar\n\n"
        "🟢 <b>PLUS tarifi:</b>\n• Kuniga 30 ta yuklash\n• Tezroq yuklash\n• Reklamasiz\n\n"
        "🔵 <b>PRO tarifi:</b>\n• Cheksiz yuklash\n• Maksimal tezlik\n• Reklamasiz\n• Ustuvor navbat\n\n"
        "Savolingiz bo'lsa, pastdagi tugma orqali adminga yozing 👇"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=help_kb())
