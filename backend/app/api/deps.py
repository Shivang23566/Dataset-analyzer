from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.models.dataset import Dataset
from app.schemas import token as token_schemas

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = token_schemas.TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    result = await db.execute(select(User).filter(User.id == int(token_data.sub)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Auto-downgrade expired Pro users
    if (
        current_user.subscription_plan == "pro"
        and current_user.subscription_expires_at
        and current_user.subscription_expires_at <= datetime.now(timezone.utc)
    ):
        current_user.subscription_plan = "free"
        current_user.subscription_status = "expired"
        db.add(current_user)
        try:
            await db.flush()
        except Exception:
            pass

    return current_user


async def require_pro(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that blocks free users from accessing Pro features.
    Checks both the User.subscription_plan field AND the
    Subscriptions table for active status and expiry.
    """
    # Check subscription table for most accurate status
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id
        )
    )
    sub = result.scalar_one_or_none()

    is_pro = False

    if sub and sub.plan == "pro" and sub.status == "active":
        # Check if subscription has expired
        if sub.expires_at is None:
            is_pro = True  # lifetime / no expiry
        elif sub.expires_at > datetime.now(timezone.utc):
            is_pro = True  # not expired yet
        else:
            # Expired — downgrade user in database
            sub.status = "expired"
            current_user.subscription_plan = "free"
            await db.commit()

    # Also check User.subscription_plan as fallback
    # (covers coupon-granted access set directly on user)
    if not is_pro and current_user.subscription_plan == "pro":
        if (
            current_user.subscription_expires_at is None
            or current_user.subscription_expires_at
            > datetime.now(timezone.utc)
        ):
            is_pro = True
        else:
            current_user.subscription_plan = "free"
            await db.commit()

    if not is_pro:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "pro_required",
                "message": "This feature requires a Pro subscription.",
                "upgrade_url": "/upgrade",
            },
        )

    return current_user


async def check_dataset_limit(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that blocks free users from uploading more
    than 3 datasets. Pro users have no limit.
    """
    # Pro users skip the check entirely
    if current_user.subscription_plan == "pro":
        return current_user

    result = await db.execute(
        select(func.count(Dataset.id)).where(
            Dataset.user_id == current_user.id,
            Dataset.is_deleted == False,
        )
    )
    count = result.scalar_one()

    if count >= 3:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "dataset_limit_reached",
                "message": "Free plan allows a maximum of 3 datasets. "
                "Upgrade to Pro for unlimited uploads.",
                "upgrade_url": "/upgrade",
                "current_count": count,
                "limit": 3,
            },
        )

    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency that blocks non-admin users.
    Only users with is_superuser=True can access admin endpoints.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "admin_required",
                "message": "You do not have admin access.",
            },
        )
    return current_user
