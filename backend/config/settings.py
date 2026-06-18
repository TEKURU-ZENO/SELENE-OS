"""
SELENE OS — Configuration Settings
Centralized configuration using Pydantic Settings for type-safe env management.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ALPHA = "alpha"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    """SELENE OS configuration — all values sourced from environment variables."""

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "SELENE OS"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── LLM Configuration ────────────────────────────────────────
    LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./selene.db"
    POSTGRES_URL: Optional[str] = None

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Memory ───────────────────────────────────────────────────
    SESSION_MEMORY_LIMIT: int = 20  # Max messages per session context
    VECTOR_DIMENSION: int = 1536  # OpenAI ada-002 dimensions
    VECTOR_INDEX_PATH: str = "./data/faiss_index"

    # ── Safety ───────────────────────────────────────────────────
    MAX_RETRIES: int = 3
    CONFIDENCE_THRESHOLD: float = 0.7
    REQUIRE_CONFIRMATION_FOR: list[str] = [
        "file_write",
        "system_exec",
        "email_send",
        "browser_action",
    ]
    FORCE_HITL_ALL_EXTERNAL_MUTATIONS: bool = False
    BLOCK_SSRF: bool = True
    REPLAY_DIR: str = "./replays"
    EXPORT_DIR: str = "./exports"
    AUDIT_DIR: str = "./audit"

    # ── Logging ──────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Read profile and apply profile-based defaults
env_val = os.getenv("ENVIRONMENT", "development").lower()
profile_overrides = {}
try:
    if env_val == "alpha":
        from .alpha import AlphaConfig
        profile_overrides = {k: v for k, v in AlphaConfig.__dict__.items() if not k.startswith("__")}
    elif env_val == "production":
        from .production import ProductionConfig
        profile_overrides = {k: v for k, v in ProductionConfig.__dict__.items() if not k.startswith("__")}
    elif env_val == "development":
        from .development import DevelopmentConfig
        profile_overrides = {k: v for k, v in DevelopmentConfig.__dict__.items() if not k.startswith("__")}
except ImportError:
    pass

# Singleton instance
settings = Settings(**profile_overrides)
