from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.database.session import async_session
from app.database import crud
from config import ADMIN_IDS

router = Router()

class Feedback(StatesGroup):
    waiting = State()

REPLY_MAP: dict[tuple[int, int], int] = {}


def fmt_username(username: str | None) -> str:
    return f"@{username}" if username else "username yo'q"


@router.callback_query(F.data == "feedback:start")
async def start_feedback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Feedback.waiting)
    await callback.message.answer("✍️ Xabaringizni shu yerga yozing, men adminga yetkazaman:")
    await callback.answer()


@router.message(Feedback.waiting)
async def relay_feedback(message: Message, state: FSMContext, bot: Bot):
    async with async_session() as session:
        db_user = await crud.get_user(session, message.from_user.id)
    phone = db_user.phone if db_user and db_user.phone else "kiritilmagan"

    caption = (f"📩 <b>Yangi xabar</b>\n\n"
               f"Foydalanuvchi: {message.from_user.full_name}\n"
               f"Username: {fmt_username(message.from_user.username)}\n"
               f"Telefon: <code>{phone}</code>\n"
               f"ID: <code>{message.from_user.id}</code>\n\n"
               f"💬 {message.text}\n\n"
               f"↩️ <i>Javob berish uchun shu xabarga reply qiling</i>")

    photo_id = None
    try:
        photos = await bot.get_user_profile_photos(message.from_user.id, limit=1)
        if photos.total_count > 0:
            photo_id = photos.photos[0][-1].file_id
    except Exception:
        pass

    for admin_id in ADMIN_IDS:
        try:
            if photo_id:
                sent = await bot.send_photo(admin_id, photo_id, caption=caption, parse_mode="HTML")
            else:
                sent = await bot.send_message(admin_id, caption, parse_mode="HTML")
            REPLY_MAP[(admin_id, sent.message_id)] = message.from_user.id
        except Exception:
            pass

    await state.clear()
    await message.answer("✅ Xabaringiz adminga yuborildi. Javobni shu yerda kutib turing.")


@router.message(F.reply_to_message, F.from_user.id.in_(ADMIN_IDS))
async def admin_reply(message: Message, bot: Bot):
    key = (message.from_user.id, message.reply_to_message.message_id)
    target_user_id = REPLY_MAP.get(key)
    if not target_user_id:
        return

    try:
        await bot.send_message(target_user_id, f"💬 <b>Admin javobi:</b>\n\n{message.text}", parse_mode="HTML")
        await message.reply("✅ Foydalanuvchiga yetkazildi.")
    except Exception:
        await message.reply("❌ Yuborib bo'lmadi (foydalanuvchi botni bloklagan bo'lishi mumkin).")
