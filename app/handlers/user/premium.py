from html import escape
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from app.database.session import async_session
from app.database import crud
from app.keyboards.inline import PLANS, plans_kb, durations_kb, admin_order_kb
from config import ADMIN_IDS

router = Router()
CARD = "5614 6821 1327 2423"
AWAITING_RECEIPT: dict[int, int] = {}

def fmt_username(username: str | None) -> str:
    return f"@{escape(username)}" if username else "username yo'q"


@router.message(F.text == "💎 Premium")
async def premium_handler(message: Message):
    await message.answer("💎 <b>Premium tariflar</b>\n\nQaysi tarifni tanlaysiz?",
                          reply_markup=plans_kb(), parse_mode="HTML")


@router.callback_query(F.data == "plan:back")
async def back_to_plans(callback: CallbackQuery):
    await callback.message.edit_text("💎 <b>Premium tariflar</b>\n\nQaysi tarifni tanlaysiz?",
                                      reply_markup=plans_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("plan:"))
async def show_plan(callback: CallbackQuery):
    plan = callback.data.split(":")[1]
    if plan == "back":
        return
    info = PLANS.get(plan)
    if not info:
        await callback.answer()
        return
    async with async_session() as session:
        prices = await crud.get_plan_prices(session, plan)
    text = f"{info['title']}\n\n" + "\n".join(f"• {f}" for f in info["features"]) + "\n\n⬇️ Muddatni tanlang:"
    await callback.message.edit_text(text, reply_markup=durations_kb(plan, prices))
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy_handler(callback: CallbackQuery):
    # callback_data faqat "buy:<plan>:<months>" — narx hech qachon undan olinmaydi
    # (eski "buy:plan:months:price" tugmalari ham ishlaydi, lekin 4-qism e'tiborga olinmaydi).
    parts = callback.data.split(":")
    try:
        plan, months = parts[1], int(parts[2])
    except (IndexError, ValueError):
        await callback.answer()
        return

    async with async_session() as session:
        prices = await crud.get_plan_prices(session, plan) if plan in PLANS else {}
        price = prices.get(months)
        if price is None:
            await callback.answer("Bu tarif mavjud emas, qaytadan tanlang", show_alert=True)
            return
        user = await crud.get_or_create_user(session, callback.from_user.id, callback.from_user.username,
                                              callback.from_user.first_name, callback.from_user.last_name)
        order = await crud.create_order(session, user.telegram_id, plan, months, price)

    AWAITING_RECEIPT[callback.from_user.id] = order.id

    plan_name = "PLUS" if plan == "plus" else "PRO"
    user_text = (f"✅ <b>Buyurtma qabul qilindi</b>\n\nTarif: {plan_name}\nMuddat: {months} oy\n"
                 f"Summa: {price:,} so'm\n\n💳 Kartaga o'tkazing:\n<code>{CARD}</code>\n\n"
                 f"📸 To'lov qilgach, <b>chek skrinshotini shu chatga rasm qilib yuboring</b>.\n"
                 f"Chekni ko'rib, admin tasdiqlaydi.").replace(",", ".")
    await callback.message.edit_text(user_text, parse_mode="HTML")
    await callback.answer()


@router.message(F.photo)
async def handle_receipt(message: Message, bot: Bot):
    order_id = AWAITING_RECEIPT.get(message.from_user.id)
    if not order_id:
        return

    async with async_session() as session:
        order = await crud.get_order(session, order_id)
        if not order or order.status != "pending":
            AWAITING_RECEIPT.pop(message.from_user.id, None)
            return

    plan_name = "PLUS" if order.plan == "plus" else "PRO"
    caption = (f"🆕 <b>Yangi to'lov cheki — Buyurtma #{order.id}</b>\n\n"
               f"Foydalanuvchi: {escape(message.from_user.full_name)} ({fmt_username(message.from_user.username)})\n"
               f"ID: <code>{message.from_user.id}</code>\nTarif: {plan_name}\n"
               f"Muddat: {order.months} oy\nSumma: {order.price:,} so'm").replace(",", ".")

    photo_id = message.photo[-1].file_id
    sent = {}
    for admin_id in ADMIN_IDS:
        try:
            msg = await bot.send_photo(admin_id, photo_id, caption=caption,
                                        reply_markup=admin_order_kb(order.id), parse_mode="HTML")
            sent[admin_id] = msg.message_id
        except Exception:
            pass

    async with async_session() as session:
        db_order = await crud.get_order(session, order.id)
        if db_order:
            await crud.set_order_admin_messages(session, db_order, sent)

    AWAITING_RECEIPT.pop(message.from_user.id, None)
    await message.answer("✅ Chekingiz adminga yuborildi, tez orada tasdiqlanadi.")
