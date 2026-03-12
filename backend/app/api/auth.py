from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib
import logging

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Request, status

# Security logger for auth events
security_logger = logging.getLogger("security.auth")


def log_security_event(event_type: str, email: str, ip: str, success: bool, details: str = ""):
    """Log security-relevant authentication events."""
    security_logger.info(
        "AUTH_EVENT | type=%s | email=%s | ip=%s | success=%s | details=%s",
        event_type, email, ip, success, details,
    )
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.email_verification import EmailVerification
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas import token as token_schemas
from app.schemas import user as user_schemas
from app.services.email_service import email_service
from app.utils.otp import generate_otp, get_otp_expiry, hash_otp, is_otp_expired, verify_otp

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas for OTP flow ─────────────────────────────────────

class InitiateSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class InitiateSignupResponse(BaseModel):
    message: str
    email: str
    expires_in_minutes: int


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendOTPRequest(BaseModel):
    email: EmailStr


class RefreshRequest(BaseModel):
    refresh_token: str


def _hash_refresh_token(token: str) -> str:
    """SHA-256 hash for safe DB storage of refresh tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


async def _create_and_store_refresh_token(user_id: int, db: AsyncSession) -> str:
    """Generate a refresh token JWT, store its hash in the DB, and return the raw token."""
    raw_token = security.create_refresh_token(user_id)
    token_hash = _hash_refresh_token(raw_token)
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(db_token)
    await db.flush()
    return raw_token


# ── Login (unchanged) ────────────────────────────────────────

@router.post("/login", response_model=token_schemas.Token)
@limiter.limit("10/minute")
async def login_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    normalized_email = form_data.username.lower().strip()
    result = await db.execute(select(User).filter(User.email == normalized_email))
    user = result.scalars().first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        log_security_event("login_attempt", normalized_email, request.client.host if request.client else "unknown", False, "invalid_credentials")
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        log_security_event("login_attempt", normalized_email, request.client.host if request.client else "unknown", False, "inactive_user")
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = await _create_and_store_refresh_token(user.id, db)
    await db.commit()
    log_security_event("login_attempt", normalized_email, request.client.host if request.client else "unknown", True)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# ── Step 1: Initiate Signup (send OTP) ───────────────────────

@router.post("/signup/initiate", response_model=InitiateSignupResponse)
@limiter.limit("5/minute")
async def initiate_signup(
    request: Request,
    background_tasks: BackgroundTasks,
    *,
    db: AsyncSession = Depends(get_db),
    body: InitiateSignupRequest,
) -> Any:
    """
    Step 1 of signup: validate input, store pending verification, send OTP email.
    Does NOT create the user account yet.
    """
    normalized_email = body.email.lower().strip()

    # Check if email is already registered
    existing = await db.execute(select(User).filter(User.email == normalized_email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please login instead.",
        )

    # Rate-limit: block if an unused OTP was created within cooldown window
    cooldown_cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
    recent = await db.execute(
        select(EmailVerification).where(
            and_(
                EmailVerification.email == normalized_email,
                EmailVerification.created_at > cooldown_cutoff,
                EmailVerification.is_used == False,  # noqa: E712
            )
        )
    )
    if recent.scalars().first():
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {settings.OTP_RESEND_COOLDOWN_SECONDS} seconds before requesting a new code.",
        )

    # Delete old pending verifications for this email
    old_rows = await db.execute(
        select(EmailVerification).where(EmailVerification.email == normalized_email)
    )
    for old in old_rows.scalars().all():
        await db.delete(old)

    # Generate & hash OTP
    otp = generate_otp(6)
    otp_hash, salt = hash_otp(otp)

    verification = EmailVerification(
        email=normalized_email,
        otp_hash=f"{otp_hash}:{salt}",
        expires_at=get_otp_expiry(settings.OTP_EXPIRY_MINUTES),
        temp_password_hash=security.get_password_hash(body.password),
        temp_full_name=body.full_name,
    )
    db.add(verification)
    await db.commit()

    # Send email in background (non-blocking)
    background_tasks.add_task(
        email_service.send_verification_email,
        normalized_email,
        otp,
        body.full_name,
    )

    log_security_event("otp_initiated", normalized_email, request.client.host if request.client else "unknown", True)

    return InitiateSignupResponse(
        message="Verification code sent to your email.",
        email=normalized_email,
        expires_in_minutes=settings.OTP_EXPIRY_MINUTES,
    )


# ── Step 2: Verify OTP & create account ──────────────────────

@router.post("/signup/verify")
@limiter.limit("10/minute")
async def verify_otp_and_create_account(
    request: Request,
    *,
    db: AsyncSession = Depends(get_db),
    body: VerifyOTPRequest,
) -> Any:
    """
    Step 2 of signup: verify OTP, create user, return access token.
    """
    normalized_email = body.email.lower().strip()
    otp_input = body.otp.strip()

    if not otp_input.isdigit() or len(otp_input) != 6:
        raise HTTPException(status_code=400, detail="Invalid verification code format.")

    # Find the latest pending verification for this email
    result = await db.execute(
        select(EmailVerification)
        .where(
            and_(
                EmailVerification.email == normalized_email,
                EmailVerification.is_used == False,  # noqa: E712
            )
        )
        .order_by(EmailVerification.created_at.desc())
    )
    verification = result.scalars().first()

    if not verification:
        raise HTTPException(
            status_code=400,
            detail="No pending verification found. Please request a new code.",
        )

    if is_otp_expired(verification.expires_at):
        raise HTTPException(
            status_code=400,
            detail="Verification code has expired. Please request a new one.",
        )

    if verification.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=400,
            detail="Too many failed attempts. Please request a new code.",
        )

    # Verify OTP
    stored_hash, salt = verification.otp_hash.split(":")
    if not verify_otp(otp_input, stored_hash, salt):
        verification.attempts += 1
        await db.commit()
        remaining = settings.OTP_MAX_ATTEMPTS - verification.attempts
        log_security_event("otp_verify_failed", normalized_email, request.client.host if request.client else "unknown", False, f"attempt={verification.attempts}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid verification code. {remaining} attempts remaining.",
        )

    # OTP correct — double-check no user was created in the meantime
    race_check = await db.execute(select(User).filter(User.email == normalized_email))
    if race_check.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="An account with this email was just created. Please login.",
        )

    # Create user
    new_user = User(
        email=normalized_email,
        hashed_password=verification.temp_password_hash,
        full_name=verification.temp_full_name,
        is_active=True,
        is_superuser=False,
    )
    db.add(new_user)

    verification.is_used = True
    await db.commit()
    await db.refresh(new_user)

    # Issue token pair (access + refresh)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        new_user.id, expires_delta=access_token_expires
    )
    refresh_token = await _create_and_store_refresh_token(new_user.id, db)
    await db.commit()

    log_security_event("signup_completed", normalized_email, request.client.host if request.client else "unknown", True)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "subscription_plan": new_user.subscription_plan,
        },
    }


# ── Resend OTP ───────────────────────────────────────────────

@router.post("/signup/resend-otp")
@limiter.limit("3/minute")
async def resend_otp(
    request: Request,
    background_tasks: BackgroundTasks,
    *,
    db: AsyncSession = Depends(get_db),
    body: ResendOTPRequest,
) -> Any:
    """Resend OTP for a pending signup."""
    normalized_email = body.email.lower().strip()

    result = await db.execute(
        select(EmailVerification)
        .where(
            and_(
                EmailVerification.email == normalized_email,
                EmailVerification.is_used == False,  # noqa: E712
            )
        )
        .order_by(EmailVerification.created_at.desc())
    )
    verification = result.scalars().first()

    if not verification:
        raise HTTPException(
            status_code=400,
            detail="No pending signup found. Please start signup again.",
        )

    # Enforce cooldown
    cooldown_until = verification.created_at + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
    now = datetime.now(timezone.utc)
    # Handle naive datetimes
    if cooldown_until.tzinfo is None:
        now = now.replace(tzinfo=None)
    if now < cooldown_until:
        diff = cooldown_until - now
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {int(diff.total_seconds())} seconds before requesting a new code.",
        )

    # Generate new OTP
    otp = generate_otp(6)
    otp_hash, salt = hash_otp(otp)

    verification.otp_hash = f"{otp_hash}:{salt}"
    verification.created_at = datetime.now(timezone.utc)
    verification.expires_at = get_otp_expiry(settings.OTP_EXPIRY_MINUTES)
    verification.attempts = 0

    await db.commit()

    background_tasks.add_task(
        email_service.send_verification_email,
        normalized_email,
        otp,
        verification.temp_full_name,
    )

    return {
        "message": "New verification code sent.",
        "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
    }


# ── Legacy signup (DISABLED — email verification required) ───

@router.post(
    "/signup",
    deprecated=True,
    summary="[DEPRECATED] Direct signup - Use /signup/initiate instead",
    response_model=dict,
    responses={
        410: {"description": "Endpoint deprecated"},
    },
)
@limiter.limit("5/minute")
async def signup_deprecated(
    request: Request,
    *,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    DEPRECATED: Direct signup is no longer supported.
    All new signups must go through email verification.

    Use the following flow instead:
    1. POST /auth/signup/initiate - Send OTP to email
    2. POST /auth/signup/verify  - Verify OTP and create account
    """
    log_security_event(
        "legacy_signup_blocked",
        "unknown",
        request.client.host if request.client else "unknown",
        False,
        "attempted use of deprecated /signup endpoint",
    )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "endpoint_deprecated",
            "message": "Direct signup is no longer supported. Please use the OTP verification flow.",
            "migration": {
                "step1": "POST /auth/signup/initiate with {email, password, full_name}",
                "step2": "POST /auth/signup/verify with {email, otp}",
            },
        },
    )


# ── Forgot Password (stub) ──────────────────────────────────

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    email: str,
) -> Any:
    """
    Password Recovery (stub — no email service configured).
    Always returns 200 to prevent email enumeration.
    """
    return {"message": "If an account with that email exists, a recovery link has been sent."}


# ── Current User ─────────────────────────────────────────────

@router.get("/users/me", response_model=user_schemas.User)
async def read_users_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


# ── Refresh Token ────────────────────────────────────────────

@router.post("/refresh")
@limiter.limit("30/minute")
async def refresh_tokens(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Exchange a valid refresh token for a new access + refresh token pair (rotation)."""
    from jose import JWTError as pyjwt_JWTError

    try:
        payload = security.decode_token(body.refresh_token)
    except pyjwt_JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token")

    user_id = int(payload["sub"])
    token_hash = _hash_refresh_token(body.refresh_token)

    # Look up the token in DB (must exist and not be revoked)
    result = await db.execute(
        select(RefreshToken).where(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    )
    stored_token = result.scalars().first()

    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")

    if stored_token.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Revoke old refresh token (rotation)
    stored_token.revoked_at = datetime.now(timezone.utc)

    # Issue new pair
    access_token = security.create_access_token(user_id)
    new_refresh_token = await _create_and_store_refresh_token(user_id, db)
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


# ── Logout ───────────────────────────────────────────────────

@router.post("/logout")
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Revoke the provided refresh token."""
    token_hash = _hash_refresh_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
    )
    stored_token = result.scalars().first()
    if stored_token:
        stored_token.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    return {"message": "Logged out successfully"}
