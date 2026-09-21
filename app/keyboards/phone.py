from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def phone_kb():
    kb = [
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
