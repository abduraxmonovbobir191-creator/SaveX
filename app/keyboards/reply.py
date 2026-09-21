from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_kb():
    kb = [
        [KeyboardButton(text="👤 Kabinetim"), KeyboardButton(text="💎 Premium")],
        [KeyboardButton(text="🎬 Videolarim"), KeyboardButton(text="🎵 Musiqalarim")],
        [KeyboardButton(text="❤️ Sevimlilar"), KeyboardButton(text="❓ Yordam")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
