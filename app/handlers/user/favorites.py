import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.session import async_session
from app.database import crud

router = Router()
FAV_CACHE: dict[str, dict] = {}


def register_favorite_item(file_id: str, media_type: str, title: str) -> str:
    token = uuid.uuid4().hex[:10]
    FAV_CACHE[token] = {"file_id": file_id, "media_type": media_type, "title": title}
    return token


def favorite_button(token: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="❤️ Sevimlilarga qo'shish", callback_data=f"fav:add:{token}")
    return kb.as_markup()


@router.callback_query(F.data.startswith("fav:add:"))
async def add_favorite_cb(callback: CallbackQuery):
    token = callback.data.split(":")[2]
    item = FAV_CACHE.get(token)
    if not item:
        await callback.answer("Bu tugma eskirgan", show_alert=True)
        return
    async with async_session() as session:
        await crud.add_favorite(session, callback.from_user.id, item["file_id"], item["media_type"], item["title"])
    await callback.answer("❤️ Sevimlilarga qo'shildi!", show_alert=True)


@router.message(F.text == "❤️ Sevimlilar")
async def show_favorites(message: Message):
    async with async_session() as session:
        items = await crud.get_favorites(session, message.from_user.id)

    if not items:
        await message.answer("❤️ Sevimlilar ro'yxati bo'sh.")
        return

    for fav in items:
        kb = InlineKeyboardBuilder()
        kb.button(text="🗑 Olib tashlash", callback_data=f"fav:del:{fav.id}")
        try:
            if fav.media_type == "photo":
                await message.answer_photo(fav.file_id, caption=fav.title or "Sevimli", reply_markup=kb.as_markup())
            elif fav.media_type == "audio":
                await message.answer_audio(fav.file_id, caption=fav.title or "Sevimli", reply_markup=kb.as_markup())
            else:
                await message.answer_video(fav.file_id, caption=fav.title or "Sevimli", reply_markup=kb.as_markup())
        except Exception:
            pass


@router.callback_query(F.data.startswith("fav:del:"))
async def del_favorite_cb(callback: CallbackQuery):
    fav_id = int(callback.data.split(":")[2])
    async with async_session() as session:
        await crud.remove_favorite(session, fav_id, callback.from_user.id)
    await callback.answer("🗑 Olib tashlandi")
    try:
        await callback.message.delete()
    except Exception:
        pass
