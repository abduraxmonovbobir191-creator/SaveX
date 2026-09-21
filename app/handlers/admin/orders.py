from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from app.database.session import async_session
from app.database import crud
from config import ADMIN_IDS

router = Router()

@router.callback_query(F.data.startswith("order:"))
async def handle_order_decision(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    _, action, order_id = callback.data.split(":")
    order_id = int(order_id)

    async with async_session() as session:
        order = await crud.get_order(session, order_id)
        if not order or order.status != "pending":
            await callback.answer("Bu buyurtma allaqachon ko'rib chiqilgan", show_alert=True)
            return

        if action == "approve":
            await crud.approve_order(session, order)
            user_text = f"✅ To'lovingiz tasdiqlandi! {order.plan.upper()} tarifi {order.months} oyga faollashtirildi."
            status_label = "✅ TASDIQLANDI"
        else:
            await crud.reject_order(session, order)
            user_text = "❌ To'lovingiz tasdiqlanmadi. Admin bilan bog'laning."
            status_label = "❌ RAD ETILDI"

        try:
            await bot.send_message(order.user_id, user_text)
        except Exception:
            pass

        if order.admin_message_ids:
            for pair in order.admin_message_ids.split(","):
                aid, mid = pair.split(":")
                try:
                    await bot.edit_message_reply_markup(chat_id=int(aid), message_id=int(mid), reply_markup=None)
                except Exception:
                    pass

    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=(callback.message.caption or "") + f"\n\n{status_label}")
        else:
            await callback.message.edit_text((callback.message.text or "") + f"\n\n{status_label}")
    except Exception:
        pass
    await callback.answer()
