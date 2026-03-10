import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.coupon import Coupon, CouponRedemption
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coupons", tags=["coupons"])


class CouponApplyRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Coupon code cannot be empty")
        if len(v) > 50:
            raise ValueError("Coupon code too long")
        # Only allow alphanumeric, hyphens, underscores
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Coupon code contains invalid characters")
        return v


# ─────────────────────────────────────────────
# ENDPOINT 1: POST /coupons/apply
# Validates and redeems a coupon code
# Rate limited: 5 attempts per hour per IP
# ─────────────────────────────────────────────
@router.post("/apply")
@limiter.limit("5/hour")
async def apply_coupon(
    request: Request,
    body: CouponApplyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    code = body.code.strip()
    now = datetime.now(timezone.utc)

    # ── CHECK 1: Is user already Pro with time remaining? ──
    if (
        current_user.subscription_plan == "pro"
        and current_user.subscription_expires_at
        and current_user.subscription_expires_at > now
    ):
        days_left = (current_user.subscription_expires_at - now).days
        raise HTTPException(
            status_code=400,
            detail={
                "error": "already_pro",
                "message": f"You already have Pro access. {days_left} days remaining.",
                "days_remaining": days_left,
            },
        )

    # ── CHECK 2: Find coupon (case-insensitive) ──
    result = await db.execute(
        select(Coupon).where(
            Coupon.code.ilike(code)
        )
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        # Generic message — don't reveal if code exists or not
        logger.warning(
            f"Invalid coupon attempt: code='{code}' user={current_user.id}"
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_coupon",
                "message": "This coupon code is not valid.",
            },
        )

    # ── CHECK 3: Is coupon active? ──
    if not coupon.is_active:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_coupon",
                "message": "This coupon code is not valid.",
            },
        )

    # ── CHECK 4: Has coupon expired? ──
    if coupon.expires_at and coupon.expires_at <= now:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "coupon_expired",
                "message": "This coupon code has expired.",
            },
        )

    # ── CHECK 5: Has coupon reached max uses? ──
    if coupon.uses_count >= coupon.max_uses:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "coupon_exhausted",
                "message": "This coupon code has reached its usage limit.",
            },
        )

    # ── CHECK 6: Has this user already used this coupon? ──
    redemption_check = await db.execute(
        select(CouponRedemption).where(
            CouponRedemption.coupon_id == coupon.id,
            CouponRedemption.user_id == current_user.id,
        )
    )
    existing_redemption = redemption_check.scalar_one_or_none()

    if existing_redemption:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "already_redeemed",
                "message": "You have already used this coupon code.",
            },
        )

    # ── ALL CHECKS PASSED — REDEEM ──

    # Calculate expiry
    if coupon.duration_days == -1:
        # Lifetime — no expiry
        access_expires_at = None
    else:
        access_expires_at = now + timedelta(days=coupon.duration_days)

    # Update user (source of truth)
    current_user.subscription_plan = "pro"
    current_user.subscription_status = "active"
    current_user.subscription_expires_at = access_expires_at
    db.add(current_user)

    # Update subscription table (keep in sync)
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id
        )
    )
    subscription = sub_result.scalar_one_or_none()

    if subscription:
        subscription.plan = "pro"
        subscription.status = "active"
        subscription.expires_at = access_expires_at
        subscription.cancelled_at = None
        subscription.cancel_at_period_end = False
    else:
        subscription = Subscription(
            user_id=current_user.id,
            plan="pro",
            status="active",
            started_at=now,
            expires_at=access_expires_at,
        )
    db.add(subscription)

    # Record the redemption
    redemption = CouponRedemption(
        coupon_id=coupon.id,
        user_id=current_user.id,
        access_expires_at=access_expires_at,
    )
    db.add(redemption)

    # Increment uses count
    coupon.uses_count += 1
    db.add(coupon)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Coupon redemption DB error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong. Please try again.",
        )

    logger.info(
        f"Coupon redeemed: code='{coupon.code}' user={current_user.id} "
        f"duration={coupon.duration_days}days"
    )

    return {
        "status": "success",
        "message": "Coupon applied! You now have Pro access.",
        "plan": "pro",
        "duration_days": coupon.duration_days,
        "expires_at": (
            access_expires_at.isoformat()
            if access_expires_at
            else "lifetime"
        ),
    }


# ─────────────────────────────────────────────
# ENDPOINT 2: GET /coupons/status
# Check if user has an active coupon redemption
# ─────────────────────────────────────────────
@router.get("/status")
async def get_coupon_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    # Get all redemptions for this user
    result = await db.execute(
        select(CouponRedemption, Coupon)
        .join(Coupon, CouponRedemption.coupon_id == Coupon.id)
        .where(CouponRedemption.user_id == current_user.id)
        .order_by(CouponRedemption.redeemed_at.desc())
    )
    redemptions = result.all()

    active_coupon = None
    history = []

    for redemption, coupon in redemptions:
        is_active = False
        if redemption.access_expires_at is None:
            # Lifetime
            is_active = True
        elif redemption.access_expires_at > now:
            is_active = True

        entry = {
            "coupon_code": coupon.code,
            "redeemed_at": redemption.redeemed_at.isoformat(),
            "expires_at": (
                redemption.access_expires_at.isoformat()
                if redemption.access_expires_at
                else "lifetime"
            ),
            "is_active": is_active,
            "duration_days": coupon.duration_days,
        }

        if is_active and active_coupon is None:
            active_coupon = entry

        history.append(entry)

    return {
        "has_active_coupon": active_coupon is not None,
        "active_coupon": active_coupon,
        "redemption_history": history,
        "total_redemptions": len(history),
    }
