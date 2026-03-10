import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


# ─── Request/Response Models ─────────────────

class OrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    razorpay_key_id: str
    user_email: str
    user_name: str | None


class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ─────────────────────────────────────────────
# ENDPOINT 1: POST /payments/create-order
# Creates a Razorpay order for Pro upgrade
# ─────────────────────────────────────────────
@router.post("/create-order", response_model=OrderResponse)
async def create_order(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if user already has active Pro
    now = datetime.now(timezone.utc)
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
                "expires_at": current_user.subscription_expires_at.isoformat(),
                "days_remaining": days_left,
            },
        )

    # Create Razorpay order
    order_data = {
        "amount": settings.PRO_PLAN_AMOUNT_PAISE,
        "currency": "INR",
        "receipt": f"datalens_user_{current_user.id}_{int(now.timestamp())}",
        "notes": {
            "user_id": str(current_user.id),
            "user_email": current_user.email,
            "plan": "pro",
            "duration_days": str(settings.PRO_PLAN_DURATION_DAYS),
        },
    }

    try:
        order = razorpay_client.order.create(data=order_data)
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create payment order. Please try again.",
        )

    return OrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
        user_email=current_user.email,
        user_name=current_user.full_name,
    )


# ─────────────────────────────────────────────
# ENDPOINT 2: POST /payments/verify-payment
# Verifies Razorpay signature + upgrades to Pro
# ─────────────────────────────────────────────
@router.post("/verify-payment")
async def verify_payment(
    payment: PaymentVerification,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Step 1: Verify Razorpay signature
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": payment.razorpay_order_id,
            "razorpay_payment_id": payment.razorpay_payment_id,
            "razorpay_signature": payment.razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        logger.warning(
            f"Payment signature verification failed for user {current_user.id}"
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "signature_invalid",
                "message": "Payment verification failed. Please contact support.",
            },
        )

    # Step 2: Calculate expiry
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.PRO_PLAN_DURATION_DAYS)

    # If user already has unexpired Pro, extend from current expiry
    if (
        current_user.subscription_plan == "pro"
        and current_user.subscription_expires_at
        and current_user.subscription_expires_at > now
    ):
        expires_at = current_user.subscription_expires_at + timedelta(
            days=settings.PRO_PLAN_DURATION_DAYS
        )

    # Step 3: Update user record
    current_user.subscription_plan = "pro"
    current_user.subscription_status = "active"
    current_user.subscription_expires_at = expires_at
    db.add(current_user)

    # Step 4: Create or update subscription record
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.plan = "pro"
        subscription.status = "active"
        subscription.razorpay_subscription_id = payment.razorpay_payment_id
        subscription.expires_at = expires_at
        subscription.cancelled_at = None
        subscription.cancel_at_period_end = False
    else:
        subscription = Subscription(
            user_id=current_user.id,
            plan="pro",
            status="active",
            razorpay_subscription_id=payment.razorpay_payment_id,
            started_at=now,
            expires_at=expires_at,
        )
    db.add(subscription)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Database update failed after payment: {e}")
        raise HTTPException(
            status_code=500,
            detail="Payment received but account update failed. Contact support.",
        )

    logger.info(
        f"User {current_user.id} upgraded to Pro. Expires: {expires_at.isoformat()}"
    )

    return {
        "status": "success",
        "message": "Payment verified! You are now a Pro user.",
        "plan": "pro",
        "expires_at": expires_at.isoformat(),
        "days_remaining": settings.PRO_PLAN_DURATION_DAYS,
    }


# ─────────────────────────────────────────────
# ENDPOINT 3: POST /payments/webhooks/razorpay
# Handles Razorpay webhook events
# NO JWT AUTH — uses signature verification instead
# ─────────────────────────────────────────────
@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Step 1: Get raw body and signature header
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Step 2: Verify webhook signature
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("Webhook received but RAZORPAY_WEBHOOK_SECRET not set")
        return {"status": "ok", "message": "webhook secret not configured"}

    expected_signature = hmac.new(
        key=settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Step 3: Parse event
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("event", "")
    logger.info(f"Razorpay webhook received: {event_type}")

    # Step 4: Handle payment.captured
    if event_type == "payment.captured":
        payment_entity = (
            event.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        notes = payment_entity.get("notes", {})
        user_id = notes.get("user_id")

        if user_id:
            try:
                result = await db.execute(
                    select(User).where(User.id == int(user_id))
                )
                user = result.scalar_one_or_none()

                if user:
                    now = datetime.now(timezone.utc)
                    expires_at = now + timedelta(
                        days=settings.PRO_PLAN_DURATION_DAYS
                    )

                    # Extend if already Pro
                    if (
                        user.subscription_plan == "pro"
                        and user.subscription_expires_at
                        and user.subscription_expires_at > now
                    ):
                        expires_at = user.subscription_expires_at + timedelta(
                            days=settings.PRO_PLAN_DURATION_DAYS
                        )

                    user.subscription_plan = "pro"
                    user.subscription_status = "active"
                    user.subscription_expires_at = expires_at
                    db.add(user)
                    await db.commit()

                    logger.info(
                        f"Webhook: User {user_id} upgraded to Pro via webhook"
                    )
            except Exception as e:
                logger.error(f"Webhook processing failed: {e}")
                await db.rollback()

    # Step 5: Handle payment.failed
    elif event_type == "payment.failed":
        payment_entity = (
            event.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        notes = payment_entity.get("notes", {})
        user_id = notes.get("user_id")
        logger.warning(f"Payment failed for user {user_id}")

    # Always return 200 — Razorpay retries on non-200
    return {"status": "ok"}


# ─────────────────────────────────────────────
# ENDPOINT 4: GET /payments/status
# Returns current subscription status
# ─────────────────────────────────────────────
@router.get("/status")
async def get_payment_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    # Auto-downgrade if expired
    if (
        current_user.subscription_plan == "pro"
        and current_user.subscription_expires_at
        and current_user.subscription_expires_at <= now
    ):
        current_user.subscription_plan = "free"
        current_user.subscription_status = "expired"
        db.add(current_user)

        # Also update subscription table
        result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == current_user.id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = "expired"
            db.add(sub)

        await db.commit()

    # Fetch subscription record
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()

    days_remaining = 0
    if (
        current_user.subscription_expires_at
        and current_user.subscription_expires_at > now
    ):
        days_remaining = (
            current_user.subscription_expires_at - now
        ).days

    return {
        "plan": current_user.subscription_plan,
        "status": current_user.subscription_status,
        "expires_at": (
            current_user.subscription_expires_at.isoformat()
            if current_user.subscription_expires_at
            else None
        ),
        "days_remaining": days_remaining,
        "amount": "₹219/month",
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "subscription": {
            "id": subscription.id if subscription else None,
            "razorpay_subscription_id": (
                subscription.razorpay_subscription_id
                if subscription
                else None
            ),
            "started_at": (
                subscription.started_at.isoformat()
                if subscription and subscription.started_at
                else None
            ),
        } if subscription else None,
    }
