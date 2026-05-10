"""
SELENE OS — Developer SDK & Plugin Boundary
The strict abstraction layer preventing third-party plugins from 
corrupting or modifying core cognition.
"""

from typing import Callable, Dict, Any
from schemas import PluginManifest, Capability
import structlog

logger = structlog.get_logger(__name__)


class SeleneSDK:
    """
    Plugins use this SDK to interface with SELENE.
    They can register capabilities, but they CANNOT access LangGraph or the Planner.
    """
    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self._handlers: Dict[str, Callable] = {}
        
    def register_capability(self, capability_name: str, handler: Callable):
        """Registers a custom capability execution block."""
        if capability_name not in [c["name"] for c in self.manifest.capabilities]:
            logger.error("unauthorized_capability_registration", capability=capability_name)
            raise ValueError(f"Capability {capability_name} not declared in manifest.")
            
        self._handlers[capability_name] = handler
        logger.info("capability_registered", plugin=self.manifest.plugin_id, capability=capability_name)
        
    async def emit_context_event(self, event_name: str, payload: dict):
        """Allows plugins to safely pipe semantic context into the Native Runtime."""
        # Routes to NativeContextLayer. No direct memory writes allowed.
        logger.info("plugin_context_emitted", plugin=self.manifest.plugin_id, event=event_name)

