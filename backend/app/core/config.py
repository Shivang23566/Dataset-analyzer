import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

def _default_secret_key() -> str:
    """Generate a secure random key. Override via SECRET_KEY env var or .env file."""
    return secrets.token_urlsafe(64)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    PROJECT_NAME: str = "Dataset Analyser"
    API_V1_STR: str = "/api"

    # SECURITY — set SECRET_KEY in .env or environment for stable tokens across restarts
    SECRET_KEY: str = _default_secret_key()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # DATABASE
    DATABASE_URL: str = "postgresql+asyncpg://neondb_owner:npg_cIBGg2De5vTq@ep-lingering-boat-a1b88cbr-pooler.ap-southeast-1.aws.neon.tech/neondb?ssl=require"

    # CORS — all common dev origins; override via CORS_ORIGINS env var in production
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"

settings = Settings()
