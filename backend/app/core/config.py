import logging
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List

logger = logging.getLogger(__name__)

_DEFAULT_SECRET = "change-me-in-env-file"


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"

    # JWT
    SECRET_KEY: str = _DEFAULT_SECRET
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Pro Plan
    PRO_PLAN_AMOUNT_PAISE: int = 21900
    PRO_PLAN_DURATION_DAYS: int = 30

    # Admin
    ADMIN_SECRET_KEY: str = _DEFAULT_SECRET

    # Email (Gmail SMTP)
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM_NAME: str = "DataLens"

    # OTP
    OTP_EXPIRY_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    USE_CLOUDINARY: bool = True

    # Cache
    CACHE_BACKEND: str = "file"  # "file" or "redis"
    REDIS_URL: str | None = None
    CACHE_DIR: str = "./cache"
    MODEL_CACHE_TTL: int = 86400   # 24 hours
    DF_CACHE_TTL: int = 3600       # 1 hour

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Prevent default SECRET_KEY from being used in production."""
        is_production = (
            os.getenv("RENDER") is not None
            or os.getenv("ENVIRONMENT", "").lower() == "production"
        )
        if v == _DEFAULT_SECRET:
            if is_production:
                raise ValueError(
                    "SECRET_KEY must be changed from the default value in production. "
                    "Set a strong random SECRET_KEY in your environment variables."
                )
            logger.warning(
                "⚠️  Using default SECRET_KEY — acceptable for development only. "
                "Set a strong SECRET_KEY before deploying to production."
            )
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
