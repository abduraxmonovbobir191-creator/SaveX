import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from app.handlers import setup_routers
from app.database.session import engine
from app.database.models import Base
from app.services.scheduler import run_scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(setup_routers())

    asyncio.create_task(run_scheduler(bot))

    print("✅ SaveX bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
