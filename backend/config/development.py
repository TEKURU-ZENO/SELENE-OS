from .base import BaseConfig

class DevelopmentConfig(BaseConfig):
    ENVIRONMENT = "development"
    FORCE_HITL_ALL_EXTERNAL_MUTATIONS = False
    LOG_LEVEL = "DEBUG"
    BLOCK_SSRF = False # Allowed for local testing
