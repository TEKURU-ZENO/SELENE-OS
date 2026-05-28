import os

class BaseConfig:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./selene.db")
    FORCE_HITL_ALL_EXTERNAL_MUTATIONS = False
    LOG_LEVEL = "INFO"
    REPLAY_DIR = os.getenv("REPLAY_DIR", "./replays")
    EXPORT_DIR = os.getenv("EXPORT_DIR", "./exports")
    AUDIT_DIR = os.getenv("AUDIT_DIR", "./audit")
    BLOCK_SSRF = True
