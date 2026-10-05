import logging
from datetime import datetime
from html import escape
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.session import async_session
from app.database import crud
from config import ADMIN_IDS

log = logging.getLogger(__name__)


def _target_reached_kb(channel_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Olib tashlash", callback_data=f"ch:remove:{channel_id}")
    kb.button(text="✅ Qoldirish", callback_data=f"ch:keep:{channel_id}")
    kb.adjust(2)
    return kb.as_markup()


async def get_missing_channels(bot: Bot, user_telegram_id: int):
    async with async_session() as session:
        channels = await crud.get_active_channels(session)
        user = await crud.get_user(session, user_telegram_id)

    if user and user.is_premium and user.premium_until and user.premium_until > datetime.utcnow():
        return []

    if not channels:
        return []

    missing = []
    newly_joined = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch.chat_id, user_telegram_id)
            joined = member.status in ("member", "administrator", "creator")
        except Exception as e:
            # Bot removed from the channel / channel deleted: we can't verify anyone, so don't
            # lock every user out because of it. Skip the channel and log it for the admins.
            log.warning("[channels] get_chat_member failed for %s (%s): %r", ch.chat_id, ch.title, e)
            continue

        if joined:
            newly_joined.append(ch)
        else:
            missing.append(ch)

    if newly_joined:
        async with async_session() as session:
            for ch in newly_joined:
                is_new = await crud.record_join_if_new(session, ch.id, user_telegram_id)
                if is_new:
                    ch_fresh = await crud.get_channel_by_id(session, ch.id)
                    if (ch_fresh and ch_fresh.target_count and
                            ch_fresh.joined_count >= ch_fresh.target_count and not ch_fresh.notified):
                        await crud.mark_channel_notified(session, ch_fresh)
                        for admin_id in ADMIN_IDS:
                            try:
                                await bot.send_message(
                                    admin_id,
                                    f"🎯 <b>Maqsadga yetildi!</b>\n\n"
                                    f"Kanal: {escape(ch_fresh.title)}\n"
                                    f"Maqsad: {ch_fresh.target_count} ta yangi a'zo\n"
                                    f"Hozirgi (bot orqali): {ch_fresh.joined_count} ta\n\n"
                                    f"Bu kanalni majburiy ro'yxatdan olib tashlaymi?",
                                    parse_mode="HTML",
                                    reply_markup=_target_reached_kb(ch_fresh.id)
                                )
                            except Exception:
                                pass

    return missing
