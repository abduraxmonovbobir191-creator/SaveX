from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def region_kb():
    kb = [
        [KeyboardButton(text="Toshkent"), KeyboardButton(text="Samarqand")],
        [KeyboardButton(text="Buxoro"), KeyboardButton(text="Andijon")],
        [KeyboardButton(text="Farg‘ona"), KeyboardButton(text="Namangan")],
        [KeyboardButton(text="Qashqadaryo"), KeyboardButton(text="Surxondaryo")],
        [KeyboardButton(text="Xorazm"), KeyboardButton(text="Navoiy")],
        [KeyboardButton(text="Jizzax"), KeyboardButton(text="Sirdaryo")],
        [KeyboardButton(text="Qoraqalpog‘iston")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
