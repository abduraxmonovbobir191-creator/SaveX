import asyncio
import csv
import io
import os
from datetime import datetime
from html import escape
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from app.database.session import async_session
from app.database import crud
from app.database.models import Order
from config import ADMIN_IDS

router = Router()


class AdminStates(StatesGroup):
    broadcast_waiting = State()
    search_waiting = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def main_panel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Statistika", callback_data="adm:stats")
    kb.button(text="🌐 Platform statistikasi", callback_data="adm:platforms")
    kb.button(text="🏆 Top foydalanuvchilar", callback_data="adm:topusers")
    kb.button(text="⏳ Kutayotgan buyurtmalar", callback_data="adm:pending")
    kb.button(text="📜 So'nggi buyurtmalar", callback_data="adm:recent")
    kb.button(text="📄 Buyurtmalar eksporti (CSV)", callback_data="adm:export")
    kb.button(text="👤 Foydalanuvchi qidirish", callback_data="adm:search")
    kb.button(text="📡 Majburiy kanallar", callback_data="adm:channels")
    kb.button(text="💰 Narxlarni boshqarish", callback_data="adm:prices")
    kb.button(text="📢 Xabar yuborish", callback_data="adm:broadcast")
    kb.adjust(1)
    return kb.as_markup()


def user_action_kb(telegram_id: int, is_banned: bool, is_premium: bool):
    kb = InlineKeyboardBuilder()
    if is_banned:
        kb.button(text="✅ Ban olib tashlash", callback_data=f"adm:unban:{telegram_id}")
    else:
        kb.button(text="🚫 Ban qilish", callback_data=f"adm:ban:{telegram_id}")
    kb.button(text="🟢 PLUS 1 oy berish", callback_data=f"adm:grant:plus:1:{telegram_id}")
    kb.button(text="🔵 PRO 1 oy berish", callback_data=f"adm:grant:pro:1:{telegram_id}")
    if is_premium:
        kb.button(text="❌ Premium'ni olib tashlash", callback_data=f"adm:delprem:{telegram_id}")
    kb.button(text="⬅️ Panelga qaytish", callback_data="adm:home")
    kb.adjust(1)
    return kb.as_markup()


def broadcast_audience_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🆓 Faqat Free", callback_data="bc:free")
    kb.button(text="🟢 Faqat PLUS", callback_data="bc:plus")
    kb.button(text="🔵 Faqat PRO", callback_data="bc:pro")
    kb.button(text="👥 Hammaga", callback_data="bc:all")
    kb.button(text="⬅️ Bekor qilish", callback_data="adm:home")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


@router.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🛠 <b>SaveX Admin Panel</b>\n\nBo'limni tanlang:", parse_mode="HTML",
                          reply_markup=main_panel_kb())


@router.callback_query(F.data == "adm:home")
async def adm_home(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.clear()
    await callback.message.edit_text("🛠 <b>SaveX Admin Panel</b>\n\nBo'limni tanlang:", parse_mode="HTML",
                                      reply_markup=main_panel_kb())
    await callback.answer()


@router.callback_query(F.data == "adm:stats")
async def adm_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()

    async with async_session() as session:
        s = await crud.get_admin_stats(session)

    def money(n):
        return f"{n:,}".replace(",", ".")

    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{s['total_users']}</b>\n"
        f"🆕 Bugun qo'shilgan: <b>{s['new_today']}</b>\n"
        f"💎 Premium foydalanuvchilar: <b>{s['premium_users']}</b>\n"
        f"🚫 Ban qilinganlar: <b>{s['banned_users']}</b>\n"
        f"⏳ Kutayotgan buyurtmalar: <b>{s['pending_orders']}</b>\n\n"
        f"💰 Jami daromad: <b>{money(s['total_revenue'])} so'm</b>\n"
        f"💵 Bugungi daromad: <b>{money(s['today_revenue'])} so'm</b>"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Yangilash", callback_data="adm:stats")
    kb.button(text="⬅️ Panelga qaytish", callback_data="adm:home")
    kb.adjust(1)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "adm:platforms")
async def adm_platforms(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    async with async_session() as session:
        rows = await crud.get_platform_stats(session)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Panelga qaytish", callback_data="adm:home")
    if not rows:
        text = "🌐 Hali ma'lumot yo'q."
    else:
        lines = ["🌐 <b>Platform statistikasi</b>\n"]
        for platform, count in sorted(rows, key=lambda r: -r[1]):
            lines.append(f"• {platform}: {count} ta")
        text = "\n".join(lines)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "adm:topusers")
async def adm_topusers(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    async with async_session() as session:
        top = await crud.get_top_users(session, limit=10)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Panelga qaytish", callback_data="adm:home")
    if not top:
        text = "🏆 Hali ma'lumot yo'q."
    else:
        lines = ["🏆 <b>Top 10 foydalanuvchi</b>\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, (name, uid, cnt) in enumerate(top, 1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            lines.append(f"{medal} {escape(str(name))} (ID: {uid}) — {cnt} ta yuklash")
        text = "\n".join(lines)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "adm:pending")
async def adm_pending(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer()

    async with async_session() as session:
        orders = await crud.get_pending_orders_list(session, limit=10)

    if not orders:
        kb = InlineKeyboardBuilder()
        kb.button(text="⬅️ Panelga qaytish", callback_data="adm:home")
        await callback.message.edit_text("✅ Hozircha kutayotgan buyurtma yo'q.", reply_markup=kb.as_markup())
        await callback.answer()
        return

    from app.keyboards.inline import admin_order_kb
    await callback.message.edit_text(f"⏳ <b>{len(orders)} ta kutayotgan buyurtma:</b>", parse_mode="HTML")
    for o in orders:
        price_str = f"{o.price:,}".replace(",", ".")
        text = (f"🆔 Buyurtma #{o.id}\nUser ID: <code>{o.user_id}</code>\n"
                f"Tarif: {o.plan.upper()}\nMuddat: {o.months} oy\nSumma: {price_str} so'm")
        await bot.send_message(callback.from_user.id, text, parse_mode="HTML", reply_markup=admin_order_kb(o.id))
        await asyncio.sleep(0.1)
    await callback.answer()


@router.callback_query(F.data == "adm:recent")
async def adm_recent(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()

    async with async_session() as session:
        orders = await crud.get_recent_processed_orders(session, limit=10)

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Panelga qaytish", callback_data="adm:home")

    if not orders:
        await callback.message.edit_text("📜 Hali buyurtmalar tarixi yo'q.", reply_markup=kb.as_markup())
        await callback.answer()
        return

    lines = ["📜 <b>So'nggi buyurtmalar:</b>\n"]
    for o in orders:
        emoji = "✅" if o.status == "approved" else "❌"
        price_str = f"{o.price:,}".replace(",", ".")
        lines.append(f"{emoji} #{o.id} — user {o.user_id} — {o.plan.upper()} {o.months} oy — {price_str} so'm")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "adm:export")
async def adm_export(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()

    async with async_session() as session:
        result = await session.execute(select(Order).order_by(Order.created_at.desc()))
        orders = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "User ID", "Plan", "Months", "Price", "Status", "Created At"])
    for o in orders:
        writer.writerow([o.id, o.user_id, o.plan, o.months, o.price, o.status, o.created_at])

    os.makedirs("storage/temp", exist_ok=True)
    path = f"storage/temp/orders_export_{callback.from_user.id}.csv"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(buf.getvalue())
        await callback.message.answer_document(FSInputFile(path), caption="📄 Buyurtmalar tarixi (CSV)")
    finally:
        if os.path.exists(path):
            os.remove(path)
    await callback.answer()


@router.callback_query(F.data == "adm:search")
async def adm_search_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminStates.search_waiting)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Bekor qilish", callback_data="adm:home")
    await callback.message.edit_text(
        "🔍 Foydalanuvchi <b>Telegram ID'sini</b> yoki <b>telefon raqamini</b> yuboring:\n\n"
        "Masalan: <code>7365900953</code> yoki <code>+998901234567</code>",
        parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()


async def _send_user_card(message: Message, user):
    status = "Free"
    if user.is_premium and user.premium_until and user.premium_until > datetime.utcnow():
        status = f"{user.premium_type.upper()} (tugash: {crud.to_tashkent_str(user.premium_until)})"
    ban_status = "🚫 Ban qilingan" if user.is_banned else "✅ Faol"
    username_line = f"@{escape(user.username)}" if user.username else "username yo'q"
    phone_line = escape(user.phone or "kiritilmagan")

    text = (f"👤 <b>Foydalanuvchi</b>\n\n"
            f"Ism: {escape(user.first_name or '')} {escape(user.last_name or '')}\n"
            f"Username: {username_line}\n"
            f"Telefon: <code>{phone_line}</code>\n"
            f"ID: <code>{user.telegram_id}</code>\n"
            f"Holat: {ban_status}\nStatus: {status}\n"
            f"Kunlik yuklash: {user.daily_downloads}\nViloyat: {escape(user.region or '-')}\n"
            f"Ro'yxatdan o'tgan: {crud.to_tashkent_str(user.created_at)}")

    kb_markup = user_action_kb(user.telegram_id, user.is_banned, user.is_premium)

    try:
        photos = await message.bot.get_user_profile_photos(user.telegram_id, limit=1)
        if photos.total_count > 0:
            await message.answer_photo(photos.photos[0][-1].file_id, caption=text,
                                        parse_mode="HTML", reply_markup=kb_markup)
            return
    except Exception:
        pass

    await message.answer(text, parse_mode="HTML", reply_markup=kb_markup)


@router.message(AdminStates.search_waiting)
async def adm_search_result(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    query = message.text.strip()
    async with async_session() as session:
        if query.replace("+", "").isdigit() and (query.startswith("+") or len(query) >= 9):
            user = await crud.search_user_by_phone(session, query)
        elif query.isdigit():
            user = await crud.search_user_by_id(session, int(query))
        else:
            user = None

    if not user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
        return

    await state.clear()
    await _send_user_card(message, user)


@router.callback_query(F.data.startswith("adm:ban:"))
async def adm_ban(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    telegram_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        user = await crud.search_user_by_id(session, telegram_id)
        if user:
            await crud.ban_user(session, user)
    await callback.answer("🚫 Foydalanuvchi ban qilindi", show_alert=True)
    try:
        await bot.send_message(telegram_id, "🚫 Siz botdan foydalanish huquqidan mahrum qilindingiz.")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:unban:"))
async def adm_unban(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    telegram_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        user = await crud.search_user_by_id(session, telegram_id)
        if user:
            await crud.unban_user(session, user)
    await callback.answer("✅ Ban olib tashlandi", show_alert=True)
    try:
        await bot.send_message(telegram_id, "✅ Sizga botdan foydalanish huquqi qaytarildi.")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:grant:"))
async def adm_grant(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    _, _, plan, months, telegram_id = callback.data.split(":")
    months, telegram_id = int(months), int(telegram_id)

    async with async_session() as session:
        user = await crud.search_user_by_id(session, telegram_id)
        if user:
            await crud.grant_premium_manual(session, user, plan, months)

    await callback.answer(f"✅ {plan.upper()} {months} oyga berildi", show_alert=True)
    try:
        await bot.send_message(telegram_id, f"🎁 Sizga admin tomonidan {plan.upper()} tarifi {months} oyga berildi!")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:delprem:"))
async def adm_delprem(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    telegram_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        user = await crud.search_user_by_id(session, telegram_id)
        if user:
            await crud.remove_premium_manual(session, user)
    await callback.answer("❌ Premium olib tashlandi", show_alert=True)


@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast_audience(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await callback.message.edit_text("📢 Kimlarga yuboramiz?", reply_markup=broadcast_audience_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("bc:"))
async def adm_broadcast_pick(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    audience = callback.data.split(":")[1]
    await state.update_data(audience=audience)
    await state.set_state(AdminStates.broadcast_waiting)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Bekor qilish", callback_data="adm:home")
    await callback.message.edit_text("✍️ Xabar matnini (yoki rasm/video) yuboring:", reply_markup=kb.as_markup())
    await callback.answer()


@router.message(AdminStates.broadcast_waiting)
async def adm_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    audience = data.get("audience", "all")
    await state.clear()

    async with async_session() as session:
        ids = await crud.get_audience_ids(session, audience)

    status = await message.answer(f"📤 Yuborilmoqda... (0/{len(ids)})")
    sent, failed = 0, 0
    for i, telegram_id in enumerate(ids, 1):
        try:
            await bot.copy_message(telegram_id, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
        if i % 20 == 0:
            try:
                await status.edit_text(f"📤 Yuborilmoqda... ({i}/{len(ids)})")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await status.edit_text(f"✅ Yuborish tugadi!\n\n✅ Yetkazildi: {sent}\n❌ Yetkazilmadi: {failed}")
