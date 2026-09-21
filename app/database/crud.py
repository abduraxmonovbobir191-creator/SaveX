from datetime import datetime, date, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import (
    User, Order, DownloadHistory, Favorite, MandatoryChannel,
    ChannelJoinRecord, PriceSetting
)

FREE_LIMIT = 7
PLUS_LIMIT = 30
PRO_LIMIT = None
TASHKENT_OFFSET = timedelta(hours=5)

DEFAULT_PRICES = {
    "plus": {1: 9900, 3: 34900, 6: 64900},
    "pro": {1: 24900, 3: 74900, 6: 144900},
}


def to_tashkent_str(dt: datetime) -> str:
    if not dt:
        return "-"
    local = dt + TASHKENT_OFFSET
    return local.strftime("%d.%m.%Y %H:%M")


def detect_platform(url: str) -> str:
    u = url.lower()
    if "instagram" in u: return "Instagram"
    if "tiktok" in u: return "TikTok"
    if "twitter" in u or "x.com" in u: return "Twitter/X"
    if "threads" in u: return "Threads"
    if "wikipedia" in u: return "Wikipedia"
    if "pinterest" in u: return "Pinterest"
    if "youtube" in u or "youtu.be" in u: return "YouTube"
    return "Boshqa"


async def get_user(session: AsyncSession, telegram_id: int):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(session: AsyncSession, telegram_id, username, first_name, last_name):
    user = await get_user(session, telegram_id)
    if user:
        changed = False
        if username != user.username:
            user.username = username; changed = True
        if first_name != user.first_name:
            user.first_name = first_name; changed = True
        if last_name != user.last_name:
            user.last_name = last_name; changed = True
        if changed:
            await session.commit()
        return user
    user = User(telegram_id=telegram_id, username=username, first_name=first_name, last_name=last_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def _get_limit(user: User):
    if user.is_premium and user.premium_until and user.premium_until > datetime.utcnow():
        return PLUS_LIMIT if user.premium_type == "plus" else PRO_LIMIT
    return FREE_LIMIT


async def check_and_use_limit(session: AsyncSession, user: User):
    today = date.today()
    if user.last_download_date is None or user.last_download_date.date() != today:
        user.daily_downloads = 0

    limit = _get_limit(user)
    if limit is not None and user.daily_downloads >= limit:
        await session.commit()
        return False, user.daily_downloads, limit

    user.daily_downloads += 1
    user.last_download_date = datetime.utcnow()
    await session.commit()
    return True, user.daily_downloads, limit


async def add_to_history(session: AsyncSession, telegram_id: int, url: str, title: str, media_type: str):
    platform = detect_platform(url)
    session.add(DownloadHistory(user_id=telegram_id, url=url, title=title, media_type=media_type, platform=platform))
    await session.commit()


async def get_history_by_type(session: AsyncSession, telegram_id: int, media_type: str, limit: int = 10):
    result = await session.execute(
        select(DownloadHistory).where(
            DownloadHistory.user_id == telegram_id,
            DownloadHistory.media_type == media_type
        ).order_by(DownloadHistory.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def get_user_total_downloads(session: AsyncSession, telegram_id: int):
    result = await session.execute(
        select(func.count()).select_from(DownloadHistory).where(DownloadHistory.user_id == telegram_id)
    )
    return result.scalar() or 0


async def get_user_platform_stats(session: AsyncSession, telegram_id: int):
    result = await session.execute(
        select(DownloadHistory.platform, func.count())
        .where(DownloadHistory.user_id == telegram_id)
        .group_by(DownloadHistory.platform)
    )
    return result.all()


async def create_order(session: AsyncSession, telegram_id: int, plan: str, months: int, price: int) -> Order:
    order = Order(user_id=telegram_id, plan=plan, months=months, price=price)
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def get_order(session: AsyncSession, order_id: int):
    return await session.get(Order, order_id)


async def set_order_admin_messages(session: AsyncSession, order: Order, mapping: dict):
    order.admin_message_ids = ",".join(f"{k}:{v}" for k, v in mapping.items())
    await session.commit()


async def approve_order(session: AsyncSession, order: Order):
    user = await get_user(session, order.user_id)
    now = datetime.utcnow()
    base = user.premium_until if (user.premium_until and user.premium_until > now) else now
    user.premium_until = base + timedelta(days=30 * order.months)
    user.is_premium = True
    user.premium_type = order.plan
    user.expiry_warned = False
    order.status = "approved"
    await session.commit()


async def reject_order(session: AsyncSession, order: Order):
    order.status = "rejected"
    await session.commit()


async def get_pending_orders_list(session: AsyncSession, limit: int = 10):
    result = await session.execute(
        select(Order).where(Order.status == "pending").order_by(Order.created_at.asc()).limit(limit)
    )
    return result.scalars().all()


async def get_recent_processed_orders(session: AsyncSession, limit: int = 10):
    result = await session.execute(
        select(Order).where(Order.status != "pending").order_by(Order.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def search_user_by_id(session: AsyncSession, telegram_id: int):
    return await get_user(session, telegram_id)


async def search_user_by_phone(session: AsyncSession, phone: str):
    clean = phone.strip().replace(" ", "").replace("-", "")
    if not clean.startswith("+"):
        clean = "+" + clean.lstrip("+")
    result = await session.execute(select(User).where(User.phone == clean))
    user = result.scalar_one_or_none()
    if user:
        return user
    result = await session.execute(select(User).where(User.phone == clean.lstrip("+")))
    return result.scalar_one_or_none()


async def ban_user(session: AsyncSession, user: User):
    user.is_banned = True
    await session.commit()


async def unban_user(session: AsyncSession, user: User):
    user.is_banned = False
    await session.commit()


async def grant_premium_manual(session: AsyncSession, user: User, plan: str, months: int):
    now = datetime.utcnow()
    base = user.premium_until if (user.premium_until and user.premium_until > now) else now
    user.premium_until = base + timedelta(days=30 * months)
    user.is_premium = True
    user.premium_type = plan
    user.expiry_warned = False
    await session.commit()


async def remove_premium_manual(session: AsyncSession, user: User):
    user.is_premium = False
    user.premium_type = None
    user.premium_until = None
    await session.commit()


async def get_all_active_telegram_ids(session: AsyncSession):
    result = await session.execute(select(User.telegram_id).where(User.is_banned == False))
    return [row[0] for row in result.all()]


async def get_audience_ids(session: AsyncSession, audience: str):
    now = datetime.utcnow()
    if audience == "free":
        result = await session.execute(select(User.telegram_id).where(
            User.is_banned == False,
            (User.is_premium == False) | (User.premium_until.is_(None)) | (User.premium_until <= now)
        ))
    elif audience == "plus":
        result = await session.execute(select(User.telegram_id).where(
            User.is_banned == False, User.is_premium == True,
            User.premium_type == "plus", User.premium_until > now
        ))
    elif audience == "pro":
        result = await session.execute(select(User.telegram_id).where(
            User.is_banned == False, User.is_premium == True,
            User.premium_type == "pro", User.premium_until > now
        ))
    else:
        result = await session.execute(select(User.telegram_id).where(User.is_banned == False))
    return [row[0] for row in result.all()]


async def get_users_expiring_soon(session: AsyncSession, within: timedelta):
    now = datetime.utcnow()
    threshold = now + within
    result = await session.execute(
        select(User).where(
            User.is_premium == True,
            User.premium_until.isnot(None),
            User.premium_until <= threshold,
            User.premium_until > now,
            User.expiry_warned == False,
        )
    )
    return result.scalars().all()


async def get_expired_users(session: AsyncSession):
    now = datetime.utcnow()
    result = await session.execute(
        select(User).where(
            User.is_premium == True,
            User.premium_until.isnot(None),
            User.premium_until <= now,
        )
    )
    return result.scalars().all()


async def mark_warned(session: AsyncSession, user: User):
    user.expiry_warned = True
    await session.commit()


async def expire_user(session: AsyncSession, user: User):
    user.is_premium = False
    user.premium_type = None
    user.expiry_warned = False
    await session.commit()


async def get_admin_stats(session: AsyncSession):
    today_start = datetime.combine(date.today(), datetime.min.time())

    total_users = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
    premium_users = (await session.execute(
        select(func.count()).select_from(User).where(User.is_premium == True))).scalar() or 0
    banned_users = (await session.execute(
        select(func.count()).select_from(User).where(User.is_banned == True))).scalar() or 0
    new_today = (await session.execute(
        select(func.count()).select_from(User).where(User.created_at >= today_start))).scalar() or 0
    pending_orders = (await session.execute(
        select(func.count()).select_from(Order).where(Order.status == "pending"))).scalar() or 0
    total_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.price), 0)).where(Order.status == "approved"))).scalar() or 0
    today_revenue = (await session.execute(
        select(func.coalesce(func.sum(Order.price), 0)).where(
            Order.status == "approved", Order.created_at >= today_start))).scalar() or 0

    return {
        "total_users": total_users, "premium_users": premium_users, "banned_users": banned_users,
        "new_today": new_today, "pending_orders": pending_orders,
        "total_revenue": total_revenue, "today_revenue": today_revenue,
    }


async def get_platform_stats(session: AsyncSession):
    result = await session.execute(
        select(DownloadHistory.platform, func.count()).group_by(DownloadHistory.platform)
    )
    return result.all()


async def get_top_users(session: AsyncSession, limit: int = 10):
    result = await session.execute(
        select(DownloadHistory.user_id, func.count().label("cnt"))
        .group_by(DownloadHistory.user_id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = result.all()
    output = []
    for user_id, cnt in rows:
        user = await get_user(session, user_id)
        name = user.first_name if user else str(user_id)
        output.append((name, user_id, cnt))
    return output


# ---------- Sevimlilar ----------

async def add_favorite(session: AsyncSession, user_id: int, file_id: str, media_type: str, title: str):
    session.add(Favorite(user_id=user_id, file_id=file_id, media_type=media_type, title=title))
    await session.commit()


async def get_favorites(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Favorite).where(Favorite.user_id == user_id).order_by(Favorite.created_at.desc())
    )
    return result.scalars().all()


async def remove_favorite(session: AsyncSession, favorite_id: int, user_id: int):
    fav = await session.get(Favorite, favorite_id)
    if fav and fav.user_id == user_id:
        await session.delete(fav)
        await session.commit()


# ---------- Majburiy kanallar ----------

async def create_channel(session: AsyncSession, chat_id: int, title: str, invite_link: str, target_count):
    channel = MandatoryChannel(chat_id=chat_id, title=title, invite_link=invite_link, target_count=target_count)
    session.add(channel)
    await session.commit()
    return channel


async def get_active_channels(session: AsyncSession):
    result = await session.execute(select(MandatoryChannel).where(MandatoryChannel.is_active == True))
    return result.scalars().all()


async def get_channel_by_id(session: AsyncSession, channel_id: int):
    return await session.get(MandatoryChannel, channel_id)


async def deactivate_channel(session: AsyncSession, channel: MandatoryChannel):
    channel.is_active = False
    await session.commit()


async def record_join_if_new(session: AsyncSession, channel_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(ChannelJoinRecord).where(
            ChannelJoinRecord.channel_id == channel_id,
            ChannelJoinRecord.user_id == user_id
        )
    )
    if result.scalar_one_or_none():
        return False

    session.add(ChannelJoinRecord(channel_id=channel_id, user_id=user_id))
    channel = await session.get(MandatoryChannel, channel_id)
    if channel:
        channel.joined_count += 1
    await session.commit()
    return True


async def mark_channel_notified(session: AsyncSession, channel: MandatoryChannel):
    channel.notified = True
    await session.commit()


# ---------- Narxlar ----------

async def get_all_prices(session: AsyncSession):
    result = await session.execute(select(PriceSetting))
    rows = result.scalars().all()
    prices = {plan: dict(months_map) for plan, months_map in DEFAULT_PRICES.items()}
    for row in rows:
        prices.setdefault(row.plan, {})[row.months] = row.price
    return prices


async def get_plan_prices(session: AsyncSession, plan: str):
    all_prices = await get_all_prices(session)
    return all_prices.get(plan, DEFAULT_PRICES.get(plan, {}))


async def set_price(session: AsyncSession, plan: str, months: int, price: int):
    result = await session.execute(
        select(PriceSetting).where(PriceSetting.plan == plan, PriceSetting.months == months)
    )
    row = result.scalar_one_or_none()
    if row:
        row.price = price
    else:
        session.add(PriceSetting(plan=plan, months=months, price=price))
    await session.commit()
