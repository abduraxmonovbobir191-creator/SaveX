from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="uz")
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_warned: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_downloads: Mapped[int] = mapped_column(Integer, default=0)
    last_download_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    plan: Mapped[str] = mapped_column(String(20))
    months: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    admin_message_ids: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DownloadHistory(Base):
    __tablename__ = "download_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    media_type: Mapped[str] = mapped_column(String(20), default="video")
    platform: Mapped[str] = mapped_column(String(30), default="Boshqa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    file_id: Mapped[str] = mapped_column(String(300))
    media_type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(200))
    invite_link: Mapped[str] = mapped_column(String(300))
    target_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joined_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ChannelJoinRecord(Base):
    __tablename__ = "channel_join_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PriceSetting(Base):
    __tablename__ = "price_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan: Mapped[str] = mapped_column(String(20))
    months: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
