from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def channels_gate_kb(channels) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        kb.button(text=f"➕ {ch.title}", url=ch.invite_link)
    kb.button(text="✅ Tekshirdim", callback_data="gate:check")
    kb.adjust(1)
    return kb.as_markup()
