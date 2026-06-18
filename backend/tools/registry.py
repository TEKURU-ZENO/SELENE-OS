"""
SELENE OS — Tool Registry (Phase 6 Capability Update)
Dynamic tool registration enabling the Capability Resolver to route actions.
"""

from typing import Any, Callable, Optional, List
from schemas import ToolDefinition, RiskLevel, ToolMetadata
import structlog

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """
    Central registry for all tools available to SELENE agents.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable] = {}

    def register(
        self,
        name: str,
        description: str,
        agent: str,
        handler: Callable,
        risk_level: RiskLevel = RiskLevel.LOW,
        requires_confirmation: bool = False,
        rollback_supported: bool = False,
        parameters: dict[str, Any] = None,
    ) -> None:
        """Register a tool with its handler and metadata."""
        metadata = ToolMetadata(
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            rollback_supported=rollback_supported
        )
        
        definition = ToolDefinition(
            name=name,
            description=description,
            agent=agent,
            metadata=metadata,
            parameters=parameters or {},
        )
        self._tools[name] = definition
        self._handlers[name] = handler

        logger.info("tool_registered", name=name, agent=agent, risk=risk_level.value)

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name."""
        return self._tools.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        """Get tool handler by name."""
        return self._handlers.get(name)

    async def execute(self, name: str, **kwargs) -> dict[str, Any]:
        """Execute a registered tool by name."""
        handler = self._handlers.get(name)
        if not handler:
            raise ValueError(f"Tool '{name}' not found in registry")

        definition = self._tools[name]
        if not definition.enabled:
            raise ValueError(f"Tool '{name}' is currently disabled")

        logger.info("tool_executing", name=name, params=list(kwargs.keys()))

        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**kwargs)
            else:
                result = handler(**kwargs)

            # ExecutionReceipt format will be returned by the tool handler itself,
            # or wrapped by the ExecutionEngine. For now, just return the raw tool result.
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            logger.error("tool_execution_error", name=name, error=str(e))
            return {
                "status": "failed",
                "error": str(e),
            }

    def list_tools(self, agent: str = None) -> List[ToolDefinition]:
        """List all registered tools, optionally filtered by agent."""
        tools = list(self._tools.values())
        if agent:
            tools = [t for t in tools if t.agent == agent]
        return tools


# Singleton
tool_registry = ToolRegistry()
