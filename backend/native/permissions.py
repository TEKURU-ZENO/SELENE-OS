"""
SELENE OS — Native Trust & Permission Layer
The ultimate privacy gatekeeper. Enforces Context Sandboxing and Memory Tiering.
Connectors MUST pass through this layer; they cannot write to memory directly.
"""

from schemas import ConnectorManifest, ConnectorPermission, TrustControls, MemoryTier
import structlog

logger = structlog.get_logger(__name__)


class NativeTrustManager:
    
    def authorize_connector_action(
        self, connector_id: str, action: ConnectorPermission, controls: TrustControls
    ) -> bool:
        """Validates if the user explicitly granted this connector the requested permission."""
        granted_permissions = controls.connector_permissions.get(connector_id, [])
        
        if action in granted_permissions:
            return True
            
        logger.warning(
            "trust_violation_blocked", 
            connector=connector_id, 
            attempted_action=action.value
        )
        return False
        
    def resolve_memory_tier(self, connector_id: str, controls: TrustControls) -> MemoryTier:
        """
        Enforces Local-First memory segmentation.
        By default, connector context is ephemeral or local persistent, NEVER synced 
        unless explicitly requested by the user.
        """
        # In a real implementation, this checks granular per-connector DB flags.
        # For now, we enforce the global default defined by the user.
        return controls.default_memory_tier

# Singleton
trust_manager = NativeTrustManager()
