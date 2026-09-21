from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.session import async_session
from app.database import crud
from config import ADMIN_IDS

router = Router()

class ChannelStates(StatesGroup):
    waiting_forward = State()
    waiting_target = State()

def is_admin(uid): return uid in ADMIN_IDS

def channels_admin_kb(channels):
    kb = InlineKeyboardBuilder()
    for ch in channels:
        target = f"{ch.joined_count}/{ch.target_count}" if ch.target_count else f"{ch.joined_count}/cheksiz"
        kb.button(text=f"📡 {ch.title} ({target})", callback_data=f"ch:view:{ch.id}")
    kb.button(text="➕ Yangi kanal qo'shish", callback_data="ch:add")
    kb.button(text="⬅️ Panelga qaytish", callback_data="adm:home")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "adm:channels")
async def adm_channels(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    async with async_session() as session:
        channels = await crud.get_active_channels(session)
    text = "📡 <b>Majburiy kanallar</b>\n\n" + (f"{len(channels)} ta faol kanal bor." if channels else "Hozircha kanal yo'q.")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=channels_admin_kb(channels))
    await callback.answer()


@router.callback_query(F.data == "ch:add")
async def ch_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(ChannelStates.waiting_forward)
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Bekor qilish", callback_data="adm:channels")
    await callback.message.edit_text(
        "📡 Kanaldan istalgan xabarni shu chatga <b>forward</b> qiling.\n\n"
        "⚠️ Botni avval o'sha kanalga <b>admin</b> qilib qo'ying!",
        parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()


@router.message(ChannelStates.waiting_forward, F.forward_from_chat)
async def ch_add_received(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    chat = message.forward_from_chat
    try:
        invite_link = await bot.export_chat_invite_link(chat.id)
    except Exception:
        invite_link = f"https://t.me/{chat.username}" if chat.username else None

    if not invite_link:
        await message.answer("❌ Havola olinmadi. Botni kanalga admin qilib, qaytadan urinib ko'ring.")
        await state.clear()
        return

    await state.update_data(chat_id=chat.id, title=chat.title, invite_link=invite_link)
    await state.set_state(ChannelStates.waiting_target)
    await message.answer(
        "🎯 Bu kanal uchun maqsad (necha kishi <b>bot orqali</b> qo'shilganda ogohlantirilsin)?\n\n"
        "Raqam yuboring, yoki cheksiz bo'lsa <code>0</code> yozing.", parse_mode="HTML")


@router.message(ChannelStates.waiting_forward)
async def ch_add_invalid(message: Message):
    await message.answer("❌ Iltimos, kanaldan xabarni forward qiling.")


@router.message(ChannelStates.waiting_target)
async def ch_add_target(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam yuboring.")
        return
    target = int(message.text.strip())
    data = await state.get_data()

    async with async_session() as session:
        await crud.create_channel(session, data["chat_id"], data["title"], data["invite_link"],
                                   target if target > 0 else None)

    await state.clear()
    await message.answer(f"✅ Kanal qo'shildi: {data['title']}")


@router.callback_query(F.data.startswith("ch:view:"))
async def ch_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    channel_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        channel = await crud.get_channel_by_id(session, channel_id)
    if not channel:
        await callback.answer("Topilmadi", show_alert=True)
        return

    target_str = str(channel.target_count) if channel.target_count else "cheksiz"
    text = (f"📡 <b>{channel.title}</b>\n\nHavola: {channel.invite_link}\n"
            f"Maqsad: {target_str}\nHozirgi (bot orqali qo'shilgan): {channel.joined_count}")
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 O'chirish (majburiylikdan)", callback_data=f"ch:remove:{channel.id}")
    kb.button(text="⬅️ Orqaga", callback_data="adm:channels")
    kb.adjust(1)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("ch:remove:"))
async def ch_remove(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    channel_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        channel = await crud.get_channel_by_id(session, channel_id)
        if channel:
            await crud.deactivate_channel(session, channel)
    await callback.answer("🗑 Kanal majburiy ro'yxatdan olib tashlandi", show_alert=True)
    try:
        await callback.message.edit_text("✅ Olib tashlandi.")
    except Exception:
        pass


@router.callback_query(F.data.startswith("ch:keep:"))
async def ch_keep(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await callback.answer("✅ Kanal ro'yxatda qoladi", show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
