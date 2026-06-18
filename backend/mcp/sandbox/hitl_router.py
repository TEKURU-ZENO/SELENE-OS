"""
SELENE OS — HITL Router
Centralizes human escalation logic. Trust and Approval belong in SELENE,
not in the external MCP server.
"""

from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

class HITLRouter:
    def evaluate_hitl_requirement(self, requires_hitl: bool, tool_id: str, tenant_controls: Any) -> bool:
        """
        Determines if the action must pause for human intervention.
        """
        # If the MCP server manifest STRICTLY requires it, we enforce it.
        if requires_hitl:
            return True
            
        # If the tenant controls globally disable autonomous execution, we enforce it.
        if not tenant_controls.allow_autonomous_execution:
            return True
            
        return False
        
    def trigger_escalation(self, execution_id: str, payload: Dict[str, Any]):
        """
        Sends an interrupt to the EventBus, pausing the execution DAG.
        """
        logger.warning("hitl_escalation_triggered", execution_id=execution_id)
        # In full implementation, this calls event_bus.publish(EventType.INTERRUPT, payload)
        pass

hitl_router = HITLRouter()
