import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_admin
from app.models.user import User
from app.models.coupon import Coupon, CouponRedemption
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Request Models ──────────────────────────

class CreateCouponRequest(BaseModel):
    code: str
    duration_days: int
    max_uses: int = 1
    expires_in_days: int | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Coupon code cannot be empty")
        if len(v) > 50:
            raise ValueError("Coupon code too long (max 50 chars)")
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Code can only contain letters, numbers, hyphens, underscores"
            )
        return v

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v != -1 and v < 1:
            raise ValueError(
                "duration_days must be a positive integer or -1 for lifetime"
            )
        if v > 365:
            raise ValueError("duration_days cannot exceed 365")
        return v

    @field_validator("max_uses")
    @classmethod
    def validate_max_uses(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_uses must be at least 1")
        if v > 10000:
            raise ValueError("max_uses cannot exceed 10,000")
        return v


class UpdateCouponRequest(BaseModel):
    is_active: bool | None = None
    max_uses: int | None = None
    expires_in_days: int | None = None


# ─────────────────────────────────────────────
# ENDPOINT 1: GET /admin/dashboard
# Admin overview — counts and quick stats
# ─────────────────────────────────────────────
@router.get("/dashboard")
async def admin_dashboard(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    # Total users
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar_one()

    # Pro users
    pro_count = await db.execute(
        select(func.count(User.id)).where(
            User.subscription_plan == "pro"
        )
    )
    total_pro = pro_count.scalar_one()

    # Total coupons
    coupon_count = await db.execute(select(func.count(Coupon.id)))
    total_coupons = coupon_count.scalar_one()

    # Active coupons
    active_coupon_count = await db.execute(
        select(func.count(Coupon.id)).where(
            Coupon.is_active == True
        )
    )
    active_coupons = active_coupon_count.scalar_one()

    # Total redemptions
    redemption_count = await db.execute(
        select(func.count(CouponRedemption.id))
    )
    total_redemptions = redemption_count.scalar_one()

    return {
        "stats": {
            "total_users": total_users,
            "pro_users": total_pro,
            "free_users": total_users - total_pro,
            "total_coupons": total_coupons,
            "active_coupons": active_coupons,
            "total_redemptions": total_redemptions,
        },
    }


# ─────────────────────────────────────────────
# ENDPOINT 2: POST /admin/coupons/create
# Create a new coupon code
# ─────────────────────────────────────────────
@router.post("/coupons/create")
async def create_coupon(
    body: CreateCouponRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # Check if code already exists (case-insensitive)
    existing = await db.execute(
        select(Coupon).where(Coupon.code.ilike(body.code))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="A coupon with this code already exists.",
        )

    now = datetime.now(timezone.utc)

    # Calculate coupon expiry (when the code itself stops working)
    expires_at = None
    if body.expires_in_days is not None and body.expires_in_days > 0:
        expires_at = now + timedelta(days=body.expires_in_days)

    coupon = Coupon(
        code=body.code,
        discount_type="full_access",
        duration_days=body.duration_days,
        max_uses=body.max_uses,
        uses_count=0,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(coupon)

    try:
        await db.commit()
        await db.refresh(coupon)
    except Exception as e:
        await db.rollback()
        logger.error(f"Coupon creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create coupon.",
        )

    logger.info(
        f"Admin {current_user.id} created coupon: {coupon.code} "
        f"(duration={coupon.duration_days}d, max_uses={coupon.max_uses})"
    )

    return {
        "status": "success",
        "message": f"Coupon '{coupon.code}' created successfully.",
        "coupon": {
            "id": coupon.id,
            "code": coupon.code,
            "duration_days": coupon.duration_days,
            "max_uses": coupon.max_uses,
            "uses_count": coupon.uses_count,
            "is_active": coupon.is_active,
            "expires_at": coupon.expires_at.isoformat()
            if coupon.expires_at else "never",
            "created_at": coupon.created_at.isoformat(),
        },
    }


# ─────────────────────────────────────────────
# ENDPOINT 3: GET /admin/coupons/list
# List ALL coupons with full details
# ─────────────────────────────────────────────
@router.get("/coupons/list")
async def list_coupons(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Coupon).order_by(desc(Coupon.created_at))
    )
    coupons = result.scalars().all()

    coupon_list = []
    for c in coupons:
        # Determine real status
        status = "active"
        if not c.is_active:
            status = "disabled"
        elif c.expires_at and c.expires_at <= now:
            status = "expired"
        elif c.uses_count >= c.max_uses:
            status = "exhausted"

        coupon_list.append({
            "id": c.id,
            "code": c.code,
            "duration_days": c.duration_days,
            "duration_label": (
                "Lifetime" if c.duration_days == -1
                else f"{c.duration_days} days"
            ),
            "max_uses": c.max_uses,
            "uses_count": c.uses_count,
            "uses_remaining": max(0, c.max_uses - c.uses_count),
            "is_active": c.is_active,
            "status": status,
            "expires_at": c.expires_at.isoformat()
            if c.expires_at else "never",
            "created_at": c.created_at.isoformat(),
        })

    return {
        "coupons": coupon_list,
        "total": len(coupon_list),
    }


# ─────────────────────────────────────────────
# ENDPOINT 4: GET /admin/coupons/{coupon_id}/details
# Full details of one coupon including redemptions
# ─────────────────────────────────────────────
@router.get("/coupons/{coupon_id}/details")
async def get_coupon_details(
    coupon_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # Get coupon
    result = await db.execute(
        select(Coupon).where(Coupon.id == coupon_id)
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    # Get all redemptions for this coupon
    redemptions_result = await db.execute(
        select(CouponRedemption, User)
        .join(User, CouponRedemption.user_id == User.id)
        .where(CouponRedemption.coupon_id == coupon.id)
        .order_by(desc(CouponRedemption.redeemed_at))
    )
    redemptions = redemptions_result.all()

    now = datetime.now(timezone.utc)
    status = "active"
    if not coupon.is_active:
        status = "disabled"
    elif coupon.expires_at and coupon.expires_at <= now:
        status = "expired"
    elif coupon.uses_count >= coupon.max_uses:
        status = "exhausted"

    return {
        "coupon": {
            "id": coupon.id,
            "code": coupon.code,
            "duration_days": coupon.duration_days,
            "max_uses": coupon.max_uses,
            "uses_count": coupon.uses_count,
            "uses_remaining": max(0, coupon.max_uses - coupon.uses_count),
            "is_active": coupon.is_active,
            "status": status,
            "expires_at": coupon.expires_at.isoformat()
            if coupon.expires_at else "never",
            "created_at": coupon.created_at.isoformat(),
        },
        "redemptions": [
            {
                "user_id": user.id,
                "user_email": user.email,
                "user_name": user.full_name,
                "redeemed_at": redemption.redeemed_at.isoformat(),
                "access_expires_at": (
                    redemption.access_expires_at.isoformat()
                    if redemption.access_expires_at
                    else "lifetime"
                ),
            }
            for redemption, user in redemptions
        ],
        "total_redemptions": len(redemptions),
    }


# ─────────────────────────────────────────────
# ENDPOINT 5: PUT /admin/coupons/{coupon_id}/update
# Update coupon settings (enable/disable, change limits)
# ─────────────────────────────────────────────
@router.put("/coupons/{coupon_id}/update")
async def update_coupon(
    coupon_id: int,
    body: UpdateCouponRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Coupon).where(Coupon.id == coupon_id)
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    changes = []

    if body.is_active is not None:
        coupon.is_active = body.is_active
        changes.append(
            f"is_active → {body.is_active}"
        )

    if body.max_uses is not None:
        if body.max_uses < coupon.uses_count:
            raise HTTPException(
                status_code=400,
                detail=f"max_uses cannot be less than current uses ({coupon.uses_count})",
            )
        coupon.max_uses = body.max_uses
        changes.append(f"max_uses → {body.max_uses}")

    if body.expires_in_days is not None:
        if body.expires_in_days <= 0:
            coupon.expires_at = None
            changes.append("expires_at → never")
        else:
            coupon.expires_at = datetime.now(timezone.utc) + timedelta(
                days=body.expires_in_days
            )
            changes.append(
                f"expires_at → {coupon.expires_at.isoformat()}"
            )

    db.add(coupon)
    await db.commit()

    logger.info(
        f"Admin {current_user.id} updated coupon {coupon.code}: "
        f"{', '.join(changes)}"
    )

    return {
        "status": "success",
        "message": f"Coupon '{coupon.code}' updated.",
        "changes": changes,
        "coupon": {
            "id": coupon.id,
            "code": coupon.code,
            "is_active": coupon.is_active,
            "max_uses": coupon.max_uses,
            "uses_count": coupon.uses_count,
            "expires_at": coupon.expires_at.isoformat()
            if coupon.expires_at else "never",
        },
    }


# ─────────────────────────────────────────────
# ENDPOINT 6: DELETE /admin/coupons/{coupon_id}
# Permanently delete a coupon
# ─────────────────────────────────────────────
@router.delete("/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(Coupon).where(Coupon.id == coupon_id)
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    coupon_code = coupon.code
    await db.delete(coupon)
    await db.commit()

    logger.info(
        f"Admin {current_user.id} deleted coupon: {coupon_code}"
    )

    return {
        "status": "success",
        "message": f"Coupon '{coupon_code}' permanently deleted.",
    }


# ─────────────────────────────────────────────
# ENDPOINT 7: GET /admin/users/list
# List all users with subscription info
# ─────────────────────────────────────────────
@router.get("/users/list")
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(User).order_by(desc(User.created_at))
    )
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "subscription_plan": u.subscription_plan,
                "subscription_status": u.subscription_status,
                "subscription_expires_at": (
                    u.subscription_expires_at.isoformat()
                    if u.subscription_expires_at
                    else None
                ),
                "is_superuser": u.is_superuser,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat()
                if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat()
                if u.last_login_at else None,
            }
            for u in users
        ],
        "total": len(users),
    }


# ─────────────────────────────────────────────
# ENDPOINT 8: PUT /admin/users/{user_id}/plan
# Manually change a user's subscription plan
# ─────────────────────────────────────────────
@router.put("/users/{user_id}/plan")
async def update_user_plan(
    user_id: int,
    body: dict[str, Any],
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan = body.get("plan", "").strip().lower()
    if plan not in ("free", "pro"):
        raise HTTPException(
            status_code=400, detail="Plan must be 'free' or 'pro'"
        )

    duration_days = body.get("duration_days", 30)
    now = datetime.now(timezone.utc)

    if plan == "pro":
        if duration_days == -1:
            expires_at = None
        else:
            expires_at = now + timedelta(days=duration_days)

        user.subscription_plan = "pro"
        user.subscription_status = "active"
        user.subscription_expires_at = expires_at
    else:
        user.subscription_plan = "free"
        user.subscription_status = "active"
        user.subscription_expires_at = None

    db.add(user)

    # Sync subscription table
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = sub_result.scalar_one_or_none()
    if sub:
        sub.plan = user.subscription_plan
        sub.status = user.subscription_status
        sub.expires_at = user.subscription_expires_at
        db.add(sub)

    await db.commit()

    logger.info(
        f"Admin {current_user.id} changed user {user_id} "
        f"plan to {plan}"
    )

    return {
        "status": "success",
        "message": f"User {user.email} plan changed to '{plan}'.",
        "user": {
            "id": user.id,
            "email": user.email,
            "plan": user.subscription_plan,
            "expires_at": (
                user.subscription_expires_at.isoformat()
                if user.subscription_expires_at
                else None
            ),
        },
    }
