import asyncio
from datetime import timedelta
from aiogram import Bot
from app.database.session import async_session
from app.database import crud


async def run_scheduler(bot: Bot):
    while True:
        try:
            async with async_session() as session:
                soon_users = await crud.get_users_expiring_soon(session, timedelta(days=3))
                for user in soon_users:
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            f"⏰ <b>Diqqat!</b>\n\n"
                            f"Sizning <b>{user.premium_type.upper()}</b> obunangiz "
                            f"<b>{crud.to_tashkent_str(user.premium_until)}</b> da tugaydi.\n\n"
                            f"Uzaytirish uchun 💎 Premium tugmasini bosing.",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
                    await crud.mark_warned(session, user)

                expired_users = await crud.get_expired_users(session)
                for user in expired_users:
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            "⌛ Sizning Premium obunangiz muddati tugadi. Endi Free tarifdasiz.\n\n"
                            "Yangilash uchun 💎 Premium tugmasini bosing."
                        )
                    except Exception:
                        pass
                    await crud.expire_user(session, user)
        except Exception:
            pass
        await asyncio.sleep(1800)  # har 30 daqiqada tekshiradi
