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
import structlog
import logging


# ── Structured Logging Configuration ────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.DEBUG if settings.DEBUG else logging.INFO
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
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
    
                  S E L E N E   O S   v0.1.0               
    
      Strategic Executive Layer for Everyday Navigation       
                      & Execution                             
    
      Cognitive Loop: Observe -> Decide -> Plan -> Verify ->     
                      Execute -> Learn                         
    
    =========================================================
    """)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("selene_shutdown")


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
