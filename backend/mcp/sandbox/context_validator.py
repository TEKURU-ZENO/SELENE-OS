"""
SELENE OS — Context Validator
Prevents cross-domain cognitive leakage.
Ensures an MCP server only accesses context explicitly allowed by its manifest.
"""

from typing import List
from schemas import ContextCategory
from mcp.schemas import MCPServerManifest
import structlog

logger = structlog.get_logger(__name__)

class ContextValidator:
    def validate_access(self, requested_context: ContextCategory, manifest: MCPServerManifest) -> bool:
        """
        Denies access if the requested context category is not explicitly allowed.
        """
        if requested_context.value not in manifest.allowed_contexts:
            logger.error(
                "context_access_denied", 
                server=manifest.server_id, 
                requested=requested_context.value,
                allowed=manifest.allowed_contexts
            )
            return False
        return True

context_validator = ContextValidator()
