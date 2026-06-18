"""
SELENE OS — Capability Resolver
Maps abstract Capabilities defined by the Planner to specific Tool implementations.
Factors in ExecutionContext to decide the safest and most effective tool.
"""

from typing import Optional, List
from schemas import Capability, ExecutionContext
from tools.registry import tool_registry, ToolDefinition
import structlog

logger = structlog.get_logger(__name__)


class CapabilityResolver:
    """
    Intelligently resolves a generic capability request to a specific tool.
    Allows decoupling of planner logic from raw tool execution.
    """

    # Mapping of capabilities to a prioritized list of tool names
    _CAPABILITY_MAP = {
        Capability.NAVIGATE_WEB: ["browser_navigate"],
        Capability.FIND_INFORMATION: ["web_search", "browser_scrape", "file_read"],
        Capability.READ_DOCUMENT: ["file_read", "browser_scrape"],
        Capability.MODIFY_SYSTEM: ["file_write", "system_exec"],
        Capability.INTERACT_UI: ["browser_click", "browser_fill"],
        Capability.EXECUTE_CODE: ["system_exec"],
    }

    async def resolve(
        self, 
        capability: Capability, 
        context: ExecutionContext
    ) -> Optional[ToolDefinition]:
        """
        Resolve the best tool for the capability based on context and environment.
        """
        tool_names = self._CAPABILITY_MAP.get(capability, [])
        if not tool_names:
            logger.warning("unresolved_capability", capability=capability.value)
            return None

        # Gather registered and enabled tools for these names
        candidate_tools = []
        for name in tool_names:
            tool_def = tool_registry.get_tool(name)
            if tool_def and tool_def.enabled:
                candidate_tools.append(tool_def)

        if not candidate_tools:
            logger.warning("no_enabled_tools_for_capability", capability=capability.value)
            return None

        # Filter and prioritize based on ExecutionContext
        resolved_tool = self._prioritize_tools(candidate_tools, context)
        
        if resolved_tool:
            logger.info(
                "capability_resolved", 
                capability=capability.value, 
                tool=resolved_tool.name,
                agent=resolved_tool.agent
            )
        else:
            logger.warning("capability_resolution_failed_due_to_context", capability=capability.value)
            
        return resolved_tool

    def _prioritize_tools(
        self, 
        candidates: List[ToolDefinition], 
        context: ExecutionContext
    ) -> Optional[ToolDefinition]:
        """
        Apply environment and context logic to select the best tool.
        """
        from schemas import FilePermissionMode
        
        valid_candidates = []
        
        for tool in candidates:
            # 1. File Permission Enforcement
            if tool.agent == "file_agent":
                if context.file_permission_mode == FilePermissionMode.READ_ONLY and "write" in tool.name:
                    continue  # Skip write tools in read-only mode

            # 2. Add other context-based filtering here (e.g., environment=="production" disables system_exec)
            if context.environment == "production" and tool.agent == "os_agent":
                continue # Example: Prevent OS agent in production

            valid_candidates.append(tool)

        # Return the highest priority valid tool (first in the mapped list)
        return valid_candidates[0] if valid_candidates else None


# Singleton
capability_resolver = CapabilityResolver()
