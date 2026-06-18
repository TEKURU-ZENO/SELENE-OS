"""
SELENE OS — Policy Engine
Decides what actions are allowed, under what conditions, and what requires HITL.
"""

from schemas import Capability, ExecutionContext, ExecutionCheckpoint
import structlog

logger = structlog.get_logger(__name__)


class PolicyEngine:
    """
    Evaluates capabilities against organizational rules and user permissions.
    """

    def evaluate(self, capability: Capability, context: ExecutionContext, action_description: str) -> ExecutionCheckpoint | None:
        """
        Returns an ExecutionCheckpoint if the action requires confirmation or is blocked.
        Returns None if safe to proceed automatically.
        """
        
        # 1. High-Risk Capabilities MUST have HITL unless explicitly bypassed
        if capability in [Capability.MODIFY_SYSTEM, Capability.EXECUTE_CODE]:
            logger.info("policy_hitl_required", capability=capability.value)
            return ExecutionCheckpoint(
                action=action_description,
                requires_confirmation=True,
                rollback_available=False,
                reason=f"{capability.value} is a high-risk operation."
            )
            
        # 2. Web interactions in Production might need HITL
        if capability == Capability.INTERACT_UI and context.environment == "production":
            return ExecutionCheckpoint(
                action=action_description,
                requires_confirmation=True,
                rollback_available=False,
                reason="UI interaction in production requires oversight."
            )
            
        # 3. Read operations are generally safe
        if capability in [Capability.READ_DOCUMENT, Capability.FIND_INFORMATION, Capability.NAVIGATE_WEB]:
            return None
            
        return None

# Singleton
policy_engine = PolicyEngine()
