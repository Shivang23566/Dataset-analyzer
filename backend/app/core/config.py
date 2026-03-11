from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # JWT
    SECRET_KEY: str = "change-me-in-env-file"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
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
    ADMIN_SECRET_KEY: str = "change-me-in-env-file"

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    USE_CLOUDINARY: bool = True

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
