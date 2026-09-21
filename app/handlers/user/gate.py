from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from app.services.channels import get_missing_channels
from app.keyboards.reply import main_menu_kb
from app.keyboards.channels import channels_gate_kb

router = Router()

@router.callback_query(F.data == "gate:check")
async def gate_check(callback: CallbackQuery, bot: Bot):
    missing = await get_missing_channels(bot, callback.from_user.id)
    if missing:
        await callback.answer("❌ Hali barcha kanallarga obuna bo'lmadingiz", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=channels_gate_kb(missing))
        except Exception:
            pass
        return

    try:
        await callback.message.edit_text("✅ Rahmat! Endi botdan to'liq foydalanishingiz mumkin.")
    except Exception:
        pass
    await bot.send_message(callback.from_user.id, "Asosiy menyu:", reply_markup=main_menu_kb())
    await callback.answer()
