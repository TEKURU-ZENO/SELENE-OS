from .base import BaseConfig

class ProductionConfig(BaseConfig):
    ENVIRONMENT = "production"
    FORCE_HITL_ALL_EXTERNAL_MUTATIONS = True
    LOG_LEVEL = "WARNING"
    BLOCK_SSRF = True
