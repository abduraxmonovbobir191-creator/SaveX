from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def language_kb():
    kb = [
        [KeyboardButton(text="🇺🇿 Oʻzbek"), KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English"), KeyboardButton(text="🇰🇿 Қазақ")],
        [KeyboardButton(text="🇹🇯 Тоҷикӣ"), KeyboardButton(text="🇹🇷 Türkçe")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
