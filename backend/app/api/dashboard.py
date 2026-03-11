import logging
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.dataset import Dataset
from app.models.session import AnalysisSession
from app.models.download import Download
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ─────────────────────────────────────────────
# HELPER — get or create subscription record
# Syncs Subscription table from User model (source of truth)
# ─────────────────────────────────────────────
async def _get_or_create_subscription(
    user: User, db: AsyncSession
) -> Subscription:
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        # Create new subscription synced from User model
        sub = Subscription(
            user_id=user.id,
            plan=user.subscription_plan or "free",
            status=user.subscription_status or "active",
            expires_at=user.subscription_expires_at,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
    else:
        # Sync existing subscription from User model if mismatched
        needs_sync = (
            sub.plan != (user.subscription_plan or "free")
            or sub.status != (user.subscription_status or "active")
            or sub.expires_at != user.subscription_expires_at
        )
        if needs_sync:
            sub.plan = user.subscription_plan or "free"
            sub.status = user.subscription_status or "active"
            sub.expires_at = user.subscription_expires_at
            await db.commit()
            await db.refresh(sub)

    return sub


# ─────────────────────────────────────────────
# GET /dashboard/summary
# Returns counts and plan info for the top bar
# ─────────────────────────────────────────────
@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # Dataset count
    dataset_result = await db.execute(
        select(func.count(Dataset.id)).where(
            Dataset.user_id == current_user.id,
            Dataset.is_deleted == False,
        )
    )
    dataset_count = dataset_result.scalar_one()

    # Session count
    session_result = await db.execute(
        select(func.count(AnalysisSession.id)).where(
            AnalysisSession.user_id == current_user.id
        )
    )
    session_count = session_result.scalar_one()

    # Download count
    download_result = await db.execute(
        select(func.count(Download.id)).where(
            Download.user_id == current_user.id
        )
    )
    download_count = download_result.scalar_one()

    # Subscription info
    sub = await _get_or_create_subscription(current_user, db)

    # Update last_login
    current_user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "member_since": current_user.created_at.isoformat()
            if current_user.created_at else None,
        },
        "stats": {
            "datasets": dataset_count,
            "sessions": session_count,
            "downloads": download_count,
        },
        "subscription": {
            "plan": current_user.subscription_plan or "free",
            "status": current_user.subscription_status or "active",
            "expires_at": current_user.subscription_expires_at.isoformat()
            if current_user.subscription_expires_at else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
        },
    }


# ─────────────────────────────────────────────
# GET /dashboard/datasets
# Returns all datasets uploaded by the user
# ─────────────────────────────────────────────
@router.get("/datasets")
async def get_user_datasets(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Dataset)
        .where(
            Dataset.user_id == current_user.id,
            Dataset.is_deleted == False,
        )
        .order_by(desc(Dataset.uploaded_at))
    )
    datasets = result.scalars().all()

    return {
        "datasets": [
            {
                "id": d.id,
                "original_filename": d.original_filename,
                "saved_filename": d.saved_filename,
                "file_size_bytes": d.file_size_bytes,
                "row_count": d.row_count,
                "col_count": d.col_count,
                "uploaded_at": d.uploaded_at.isoformat(),
                "last_accessed_at": d.last_accessed_at.isoformat()
                if d.last_accessed_at else None,
            }
            for d in datasets
        ],
        "total": len(datasets),
    }


# ─────────────────────────────────────────────
# DELETE /dashboard/datasets/{dataset_id}
# Soft deletes a dataset record
# ─────────────────────────────────────────────
@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id,
            Dataset.user_id == current_user.id,
            Dataset.is_deleted == False,
        )
    )
    dataset = result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete from Cloudinary if stored there
    if dataset.storage_path and dataset.storage_path.startswith("datalens/"):
        try:
            from app.core.cloudinary_config import delete_from_cloudinary

            delete_from_cloudinary(dataset.storage_path)
        except Exception:
            pass  # Don't fail delete if Cloudinary cleanup fails

    dataset.is_deleted = True
    await db.commit()
    return {"message": "Dataset deleted successfully"}


# ─────────────────────────────────────────────
# GET /dashboard/sessions
# Returns all analysis sessions for the user
# ─────────────────────────────────────────────
@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(AnalysisSession)
        .where(AnalysisSession.user_id == current_user.id)
        .order_by(desc(AnalysisSession.created_at))
        .limit(50)
    )
    sessions = result.scalars().all()

    return {
        "sessions": [
            {
                "id": s.id,
                "session_key": s.session_key,
                "session_type": s.session_type,
                "status": s.status,
                "result_summary": s.result_summary,
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat()
                if s.completed_at else None,
                "dataset_id": s.dataset_id,
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


# ─────────────────────────────────────────────
# GET /dashboard/downloads
# Returns all download records for the user
# ─────────────────────────────────────────────
@router.get("/downloads")
async def get_user_downloads(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(Download)
        .where(Download.user_id == current_user.id)
        .order_by(desc(Download.downloaded_at))
        .limit(100)
    )
    downloads = result.scalars().all()

    return {
        "downloads": [
            {
                "id": dl.id,
                "file_type": dl.file_type,
                "original_filename": dl.original_filename,
                "downloaded_at": dl.downloaded_at.isoformat(),
                "session_id": dl.session_id,
            }
            for dl in downloads
        ],
        "total": len(downloads),
    }


# ─────────────────────────────────────────────
# GET /dashboard/profile
# Returns current user's profile info
# ─────────────────────────────────────────────
@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "subscription_plan": current_user.subscription_plan,
        "created_at": current_user.created_at.isoformat()
        if current_user.created_at else None,
        "last_login_at": current_user.last_login_at.isoformat()
        if current_user.last_login_at else None,
    }


# ─────────────────────────────────────────────
# PUT /dashboard/profile
# Updates user's full name
# ─────────────────────────────────────────────
@router.put("/profile")
async def update_profile(
    data: dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if "full_name" in data:
        full_name = str(data["full_name"]).strip()
        if len(full_name) > 100:
            raise HTTPException(
                status_code=400, detail="Name too long (max 100 chars)"
            )
        current_user.full_name = full_name

    await db.commit()
    return {
        "message": "Profile updated successfully",
        "full_name": current_user.full_name,
    }


# ─────────────────────────────────────────────
# PUT /dashboard/password
# Changes user password with current password check
# ─────────────────────────────────────────────
@router.put("/password")
async def change_password(
    data: dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    from app.core.security import verify_password, get_password_hash

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400, detail="Current password is incorrect"
        )
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 8 characters",
        )
    if not any(c.isupper() for c in new_password):
        raise HTTPException(
            status_code=400,
            detail="New password must contain at least one uppercase letter",
        )
    if not any(c.isdigit() for c in new_password):
        raise HTTPException(
            status_code=400,
            detail="New password must contain at least one number",
        )

    current_user.hashed_password = get_password_hash(new_password)
    await db.commit()
    return {"message": "Password changed successfully"}


# ─────────────────────────────────────────────
# GET /dashboard/subscription
# Returns current subscription status (synced)
# ─────────────────────────────────────────────
@router.get("/subscription")
async def get_subscription_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Use helper to ensure Subscription table is synced with User model
    sub = await _get_or_create_subscription(current_user, db)

    return {
        "plan": current_user.subscription_plan or "free",
        "status": current_user.subscription_status or "active",
        "expires_at": current_user.subscription_expires_at.isoformat()
        if current_user.subscription_expires_at else None,
        "subscription": {
            "id": sub.id,
            "razorpay_subscription_id": sub.razorpay_subscription_id,
            "started_at": sub.started_at.isoformat()
            if sub.started_at else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
        },
    }
