from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

PLANS = {
    "plus": {
        "title": "🟢 PLUS tarifi",
        "features": ["Kuniga 30 ta yuklash", "Tezroq yuklash", "Reklamasiz foydalanish"],
    },
    "pro": {
        "title": "🔵 PRO tarifi",
        "features": ["Cheksiz yuklash", "Maksimal tezlik", "Reklamasiz foydalanish", "Ustuvor navbat"],
    },
}

def plans_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 PLUS", callback_data="plan:plus")
    kb.button(text="🔵 PRO", callback_data="plan:pro")
    kb.adjust(2)
    return kb.as_markup()

def durations_kb(plan: str, prices: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for months, price in prices.items():
        text = f"{months} oy — {price:,} so'm".replace(",", ".")
        kb.button(text=text, callback_data=f"buy:{plan}:{months}")
    kb.button(text="⬅️ Ortga", callback_data="plan:back")
    kb.adjust(1)
    return kb.as_markup()

def admin_order_kb(order_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"order:approve:{order_id}")
    kb.button(text="❌ Rad etish", callback_data=f"order:reject:{order_id}")
    kb.adjust(2)
    return kb.as_markup()

def quality_kb(token: str, available_heights: list[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    all_qualities = [(240, "🟢"), (360, "🟢"), (480, "🔵"), (720, "🟣"), (1080, "🟡")]
    for height, emoji in all_qualities:
        if height in available_heights:
            kb.button(text=f"{emoji} {height}p", callback_data=f"dl:{token}:{height}")
    kb.button(text="🎵 Faqat MP3 (audio)", callback_data=f"dl:{token}:audio")
    kb.adjust(3, 3, 1)
    return kb.as_markup()

def help_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📩 Adminga xabar yuborish", callback_data="feedback:start")
    kb.adjust(1)
    return kb.as_markup()


def mp3_kb(token: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎵 MP3 yuklab olish", callback_data=f"dl:{token}:audio")
    return kb.as_markup()
