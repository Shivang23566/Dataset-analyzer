import asyncio
from app.core.database import engine, Base
import app.models  # noqa: F401 — registers all models with Base

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully on Neon PostgreSQL")

if __name__ == "__main__":
    asyncio.run(init_db())
