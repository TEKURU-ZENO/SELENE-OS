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
        Also blocks shell/bash tool execution and code execution capabilities entirely.
        """
        # Block any server/tool associated with shell or bash execution
        server_id_lower = manifest.server_id.lower()
        if "shell" in server_id_lower or "bash" in server_id_lower:
            logger.error(
                "shell_execution_blocked_by_policy",
                server=manifest.server_id,
                reason="Shell/bash execution is strictly prohibited by ContextValidator."
            )
            return False
            
        from schemas import Capability
        if Capability.EXECUTE_CODE in manifest.capabilities:
            logger.error(
                "execute_code_capability_blocked_by_policy",
                server=manifest.server_id,
                reason="EXECUTE_CODE capability is strictly prohibited by ContextValidator."
            )
            return False

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
