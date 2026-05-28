"""
🌙 SELENE OS — Main Application Entry Point

Strategic Executive Layer for Everyday Navigation & Execution

A context-aware, multi-agent AI operating system that transforms
user intent into planned, verified, and executed outcomes.
"""

import sys
import os

# Ensure backend is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from api.routes import router
from runtime.workers.worker_pool import worker_pool
from mcp.registry.server_registry import server_registry
from connectors.connector_registry import connector_registry, _build_default_connectors
from core.database import init_db
from core.redis_client import redis_client
import structlog
import logging
from logging.handlers import RotatingFileHandler

# ── Structured Logging Configuration ────────────────────────────

os.makedirs(settings.AUDIT_DIR, exist_ok=True)
log_file = os.path.join(settings.AUDIT_DIR, "system.log")

file_handler = RotatingFileHandler(
    log_file, maxBytes=10 * 1024 * 1024, backupCount=5
)
file_handler.setFormatter(logging.Formatter("%(message)s"))

console_handler = logging.StreamHandler()
# Use dev console renderer locally when debugging, JSON in file / production
console_handler.setFormatter(logging.Formatter("%(message)s"))

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    handlers=[file_handler, console_handler],
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# ── FastAPI Application ─────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "🌙 SELENE OS — A proactive multi-agent AI operating system. "
        "Transforms user intent into planned, verified, and executed outcomes."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route Registration ──────────────────────────────────────────

app.include_router(router)


# ── Lifecycle Events ────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info(
        "selene_startup",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT.value,
        llm_provider=settings.LLM_PROVIDER.value,
    )
    print(r"""
    =========================================================

                  S E L E N E   O S   v0.1.3-alpha

      Strategic Executive Layer for Everyday Navigation
                      & Execution

      Cognitive Loop: Observe -> Decide -> Plan -> Verify ->
                      Execute -> Learn

    =========================================================
    """)

    # ── Initialize database (create tables if not exist) ─────
    await init_db()

    # ── Load persistent vector store and execution store caches ─────
    from memory.vector_store import vector_store
    vector_store.load()

    from runtime.execution_store import execution_store
    await execution_store.load_from_db()

    # ── Connect Redis (graceful fallback if unavailable) ─────
    await redis_client.connect()

    # ── Register all MCP server manifests ───────────────────
    server_registry.auto_register_defaults()

    # ── Start execution worker pool ──────────────────────────
    await worker_pool.start()

    # ── Register and start context connectors ─────────────────
    for connector in _build_default_connectors():
        connector_registry.register(connector)
    await connector_registry.start_polling()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("selene_shutdown")
    await connector_registry.stop_polling()
    await worker_pool.stop()
    await redis_client.close()


# ── Root Endpoint ───────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "system": "SELENE OS",
        "version": settings.APP_VERSION,
        "status": "operational",
        "philosophy": "Observe → Decide → Plan → Verify → Execute → Learn",
        "docs": "/docs",
    }


# ── Run with Uvicorn ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
