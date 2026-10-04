import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from config import BOT_TOKEN
from app.handlers import setup_routers
from app.database.session import engine
from app.database.models import Base
from app.services.scheduler import run_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    local_server = TelegramAPIServer.from_base('http://127.0.0.1:8081')
    session = AiohttpSession(api=local_server)
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.include_router(setup_routers())

    asyncio.create_task(run_scheduler(bot))

    print("✅ SaveX bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
