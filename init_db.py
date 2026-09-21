import asyncio
from app.database.session import engine
from app.database.models import Base

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database jadvallari yaratildi!")

if __name__ == "__main__":
    asyncio.run(init())
