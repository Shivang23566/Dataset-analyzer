from datetime import timedelta
from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas import token as token_schemas
from app.schemas import user as user_schemas

logger = logging.getLogger(__name__)
router = APIRouter()


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
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/signup", response_model=user_schemas.User)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    *,
    db: AsyncSession = Depends(get_db),
    user_in: user_schemas.UserCreate,
) -> Any:
    """
    Create new user without the need to be logged in
    """
    normalized_email = user_in.email.lower().strip()

    result = await db.execute(select(User).filter(User.email == normalized_email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Please login instead.",
        )

    user = User(
        email=normalized_email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

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
    # Always return the same response regardless of whether the user exists.
    # This prevents attackers from probing which emails are registered.
    return {"message": "If an account with that email exists, a recovery link has been sent."}

@router.get("/users/me", response_model=user_schemas.User)
async def read_users_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user
