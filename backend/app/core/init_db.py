import asyncio
from app.core.database import engine, Base
import app.models  # noqa: F401

async def init_db() -> None:
    """
    Only used for development/testing when Alembic is not available.
    In production, use: alembic upgrade head
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables verified on PostgreSQL")

if __name__ == "__main__":
    asyncio.run(init_db())
