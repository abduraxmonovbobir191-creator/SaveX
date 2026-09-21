from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def quality_kb():
    kb = [
        [InlineKeyboardButton(text="🟢 360p", callback_data="q:360")],
        [InlineKeyboardButton(text="🟡 480p", callback_data="q:480")],
        [InlineKeyboardButton(text="🔵 720p", callback_data="q:720")],
        [InlineKeyboardButton(text="🔴 1080p", callback_data="q:1080")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="q:cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
