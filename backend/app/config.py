"""
PersonaOS Configuration
Centralized settings loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "PersonaOS"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ── Paths ────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"

    # ── Database ─────────────────────────────────────────────────
    # SQLite for development, PostgreSQL for production
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'personaos.db'}"

    # ── LLM / AI ─────────────────────────────────────────────────
    LLM_PROVIDER: str = "openai"  # openai | anthropic | local
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"           # Model chính: Persona, Story, Chat
    OPENAI_MODEL_LITE: str = "gpt-4o-mini" # Model nhẹ: Comment, Caption, Trend...
    OPENAI_BASE_URL: Optional[str] = None  # For custom endpoints (Azure, proxies, etc.)

    # ── Vector Database (for Memory Engine) ──────────────────────
    VECTOR_DB_PROVIDER: str = "chromadb"  # chromadb | pinecone | qdrant
    CHROMADB_PATH: str = str(BASE_DIR / "data" / "chromadb")

    # ── Social Media APIs (for Publishing Engine) ────────────────
    TIKTOK_ACCESS_TOKEN: Optional[str] = None
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None
    THREADS_ACCESS_TOKEN: Optional[str] = None
    X_API_KEY: Optional[str] = None

    # ── Content Storage ──────────────────────────────────────────
    MEDIA_DIR: Path = BASE_DIR / "data" / "media"
    CONTENT_SCHEDULE_INTERVAL_HOURS: int = 6

    # ── Community Engine ─────────────────────────────────────────
    AUTO_REPLY_ENABLED: bool = False
    AUTO_REPLY_MAX_PER_HOUR: int = 50

    # ── Monetization ─────────────────────────────────────────────
    AFFILIATE_PROGRAM: str = "none"  # amazon | shopee | lazada | tiktok_shop

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
