"""
SELENE OS — MCP Transport Abstraction
Decouples runtime logic from the underlying protocol (stdio, websocket, http).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

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
