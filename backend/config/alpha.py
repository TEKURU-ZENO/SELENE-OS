from .base import BaseConfig

class AlphaConfig(BaseConfig):
    ENVIRONMENT = "alpha"
    FORCE_HITL_ALL_EXTERNAL_MUTATIONS = True
    LOG_LEVEL = "INFO"
    BLOCK_SSRF = True
