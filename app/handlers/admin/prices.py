from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.session import async_session
from app.database import crud
from config import ADMIN_IDS

router = Router()

class PriceStates(StatesGroup):
    waiting_value = State()

def is_admin(uid): return uid in ADMIN_IDS

def prices_kb(prices):
    kb = InlineKeyboardBuilder()
    for plan in ("plus", "pro"):
        for months in (1, 3, 6):
            price = prices[plan][months]
            text = f"{plan.upper()} {months} oy: {price:,} so'm".replace(",", ".")
            kb.button(text=text, callback_data=f"price:edit:{plan}:{months}")
    kb.button(text="⬅️ Panelga qaytish", callback_data="adm:home")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "adm:prices")
async def adm_prices(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    async with async_session() as session:
        prices = await crud.get_all_prices(session)
    await callback.message.edit_text("💰 <b>Narxlarni boshqarish</b>\n\nO'zgartirish uchun tanlang:",
                                      parse_mode="HTML", reply_markup=prices_kb(prices))
    await callback.answer()


@router.callback_query(F.data.startswith("price:edit:"))
async def price_edit_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    _, _, plan, months = callback.data.split(":")
    await state.update_data(plan=plan, months=int(months))
    await state.set_state(PriceStates.waiting_value)
    await callback.message.edit_text(f"💰 {plan.upper()} {months} oy uchun yangi narxni so'mda yuboring (masalan: 9900):")
    await callback.answer()


@router.message(PriceStates.waiting_value)
async def price_edit_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam yuboring.")
        return
    data = await state.get_data()
    new_price = int(message.text.strip())

    async with async_session() as session:
        await crud.set_price(session, data["plan"], data["months"], new_price)

    await state.clear()
    await message.answer(f"✅ {data['plan'].upper()} {data['months']} oy narxi {new_price:,} so'mga o'zgartirildi.".replace(",", "."))
