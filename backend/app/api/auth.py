from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas import token as token_schemas
from app.schemas import user as user_schemas

router = APIRouter()

@router.post("/login", response_model=token_schemas.Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    print(f"DEBUG: Login attempt for {form_data.username}")
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    
    if user:
        print(f"DEBUG: User found: {user.email}")
        print(f"DEBUG: Stored hash: {user.hashed_password}")
        is_valid = security.verify_password(form_data.password, user.hashed_password)
        print(f"DEBUG: Password valid: {is_valid}")
    else:
        print("DEBUG: User not found")

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
async def signup(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: user_schemas.UserCreate,
) -> Any:
    """
    Create new user without the need to be logged in
    """
    result = await db.execute(select(User).filter(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Password Recovery
    """
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    
    if not user:
        # Don't reveal if user exists or not for security reasons, or do 404 if preferred.
        # Here we mimic standard behavior:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
        
    # Mock sending email
    print(f"DEBUG: Sending password reset email to {email}")
    return {"message": "Password recovery email sent"}

@router.get("/users/me", response_model=user_schemas.User)
async def read_users_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user
