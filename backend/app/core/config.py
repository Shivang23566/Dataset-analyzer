from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Dataset Analyser"
    API_V1_STR: str = "/api"
    
    # SECURITY
    SECRET_KEY: str = "jhjbdvaslidvbaJNAISBibsbasIBSbsaibsAJSB" # TODO: Change this to a secure random string
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # DATABASE
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    # Password "SK@124578" must be URL encoded as "SK%40124578" because '@' is a delimiter
    # Using SQLite for local development
    DATABASE_URL: str = "sqlite+aiosqlite:///./dataset_analyser.db" 

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
