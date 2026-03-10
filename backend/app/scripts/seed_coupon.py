import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.database import engine, AsyncSessionLocal
from app.models.coupon import Coupon
import app.models  # noqa: F401


async def seed():
    async with AsyncSessionLocal() as db:
        # Check if already exists
        result = await db.execute(
            select(Coupon).where(Coupon.code == "Densho_Demo_05")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Coupon 'Densho_Demo_05' already exists (id={existing.id})")
            return

        now = datetime.now(timezone.utc)

        coupon = Coupon(
            code="Densho_Demo_05",
            discount_type="full_access",
            duration_days=7,
            max_uses=5,
            uses_count=0,
            is_active=True,
            expires_at=None,
        )
        db.add(coupon)
        await db.commit()
        await db.refresh(coupon)

        print(f"✅ Coupon created successfully:")
        print(f"   Code: {coupon.code}")
        print(f"   Duration: {coupon.duration_days} days Pro access")
        print(f"   Max uses: {coupon.max_uses}")
        print(f"   ID: {coupon.id}")


if __name__ == "__main__":
    asyncio.run(seed())
