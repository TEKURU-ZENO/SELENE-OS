"""
SELENE OS — Async Database Engine
SQLAlchemy async engine setup. Uses SQLite in development (zero-dependency),
Postgres in production. All stores share the same get_session() context manager.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all SELENE ORM models."""
    pass


def _build_database_url() -> str:
    """
    Returns the correct async database URL based on the environment.
    Development: SQLite (aiosqlite driver, zero-dependency)
    Production:  Postgres (asyncpg driver)
    """
    from config.settings import Environment

    if settings.ENVIRONMENT == Environment.PRODUCTION and settings.POSTGRES_URL:
        # Convert a standard Postgres URL to asyncpg format
        url = settings.POSTGRES_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # Default: async SQLite for development and alpha
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return db_url


DATABASE_URL = _build_database_url()

# ── Engine ────────────────────────────────────────────────────────
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,       # Log SQL in debug mode
    future=True,
    # SQLite-specific: allow the same connection to be used across threads
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

# ── Session factory ───────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.

    Usage:
        async with get_session() as session:
            result = await session.execute(select(Model))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Creates all tables if they don't exist.
    Called once on application startup (before workers start).
    In production, use Alembic migrations instead.
    """
    # Import models to register them with Base.metadata
    import core.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("database_initialized", url=DATABASE_URL.split("@")[-1])  # Redact credentials
