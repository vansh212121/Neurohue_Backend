# src/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Project Metadata ---
    PROJECT_NAME: str = "Auth Service API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Backend service for managing authentication"
    ENVIRONMENT: str = "development"

    # --- API Configuration ---
    API_V1_STR: str = "/api/v1"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    )

    # --- Core Infrastructure Credentials ---
    DATABASE_URL: str

    REDIS_URL: str

    FRONTEND_URL: str = "http://localhost:5173"

    # --- Database Pool Settings (CORRECTED) ---
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_TIMEOUT: int = 30

    # --- Security & JWT Settings ---
    JWT_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # --- Model Configuration ---
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
