from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from app.database.session import async_session
from app.database import crud
from app.keyboards.reply import main_menu_kb
from app.keyboards.channels import channels_gate_kb
from app.services.channels import get_missing_channels

router = Router()

REGIONS = [
    "Toshkent shahri", "Toshkent viloyati", "Andijon", "Farg'ona", "Namangan",
    "Samarqand", "Buxoro", "Navoiy", "Qashqadaryo", "Surxondaryo",
    "Jizzax", "Sirdaryo", "Xorazm", "Qoraqalpog'iston"
]

class Registration(StatesGroup):
    language = State()
    phone = State()
    region = State()


def language_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇷🇺 Русский")]],
        resize_keyboard=True
    )

def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True
    )

def region_kb():
    kb, row = [], []
    for i, r in enumerate(REGIONS, 1):
        row.append(KeyboardButton(text=r))
        if i % 2 == 0:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    async with async_session() as session:
        user = await crud.get_user(session, message.from_user.id)

    if user and user.phone:
        name = message.from_user.first_name or "Do'st"
        await message.answer(f"Assalomu alaykum, {name}!\n\nSaveX botiga xush kelibsiz.\nLink yuboring.",
                              reply_markup=main_menu_kb())
        return

    await state.set_state(Registration.language)
    await message.answer("Tilni tanlang / Выберите язык:", reply_markup=language_kb())


@router.message(Registration.language)
async def process_language(message: Message, state: FSMContext):
    lang = "ru" if "рус" in message.text.lower() else "uz"
    await state.update_data(language=lang)
    await state.set_state(Registration.phone)
    await message.answer("📱 Telefon raqamingizni yuboring:", reply_markup=phone_kb())


@router.message(Registration.phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(Registration.region)
    await message.answer("📍 Viloyatingizni tanlang:", reply_markup=region_kb())


@router.message(Registration.phone)
async def process_phone_invalid(message: Message):
    await message.answer("Iltimos, pastdagi tugma orqali telefon raqamingizni yuboring.")


@router.message(Registration.region)
async def process_region(message: Message, state: FSMContext):
    if message.text not in REGIONS:
        await message.answer("Iltimos, ro'yxatdagi tugmalardan birini tanlang.")
        return

    data = await state.get_data()
    async with async_session() as session:
        user = await crud.get_or_create_user(session, message.from_user.id, message.from_user.username,
                                              message.from_user.first_name, message.from_user.last_name)
        user.phone = data.get("phone")
        user.language = data.get("language", "uz")
        user.region = message.text
        await session.commit()

    await state.clear()

    missing = await get_missing_channels(message.bot, message.from_user.id)
    if missing:
        await message.answer(
            "✅ Ro'yxatdan o'tdingiz!\n\n"
            "📡 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
            "💎 Yoki Premium xarid qilib, kanallarsiz foydalaning!",
            reply_markup=channels_gate_kb(missing)
        )
        return

    await message.answer(
        "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\nEndi link yuboring — video, rasm yoki musiqa yuklab beraman.",
        reply_markup=main_menu_kb()
    )
