"""
SELENE OS — MCP Transport Abstraction
Decouples runtime logic from the underlying protocol (stdio, websocket, http).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.schemas import TransportType


class BaseTransport(ABC):
    """
    Abstract interface for MCP transport layers.
    Ensures that adding a new transport method doesn't require rewriting the runtime.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Tear down the connection cleanly."""
        pass

    @abstractmethod
    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request and await the response."""
        pass

    @abstractmethod
    async def emit_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Fire-and-forget notification."""
        pass


def get_transport(transport_type: "TransportType", **kwargs) -> "BaseTransport":
    """
    Factory function — returns the correct concrete transport for a given type.

    Args:
        transport_type: TransportType enum value (STDIO, HTTP, WEBSOCKET)
        **kwargs:       Passed to the transport constructor.
                        STDIO  → command: list[str], env: dict | None
                        HTTP   → base_url: str, headers: dict | None, timeout: int

    Returns:
        An uninitialised BaseTransport subclass. Call .connect() before use.
    """
    from mcp.schemas import TransportType
    from mcp.transport.stdio_transport import StdioTransport
    from mcp.transport.http_transport import HttpTransport

    if transport_type == TransportType.STDIO:
        return StdioTransport(**kwargs)
    elif transport_type == TransportType.HTTP:
        return HttpTransport(**kwargs)
    else:
        raise NotImplementedError(
            f"Transport type '{transport_type}' is not yet implemented. "
            f"Supported: STDIO, HTTP"
        )

