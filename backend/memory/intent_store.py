"""
SELENE OS — Intent Store
Separates temporary, active workflows from stable preferences to prevent hallucination.
"""

from typing import List, Dict
from schemas import PendingIntent, TaskState
import structlog

logger = structlog.get_logger(__name__)


class IntentStore:
    def __init__(self):
        # Mock DB: tenant_id -> List[PendingIntent]
        self._intents: Dict[str, List[PendingIntent]] = {}

    def register_intent(self, tenant_id: str, description: str) -> PendingIntent:
        """Saves a short-lived goal so SELENE can track it across interruptions."""
        intent = PendingIntent(
            tenant_id=tenant_id,
            intent_description=description,
        )
        if tenant_id not in self._intents:
            self._intents[tenant_id] = []
        self._intents[tenant_id].append(intent)
        logger.info("intent_registered", tenant_id=tenant_id, intent_id=intent.id)
        return intent

    def resolve_intent(self, intent_id: str, success: bool = True):
        for tenant_intents in self._intents.values():
            for intent in tenant_intents:
                if intent.id == intent_id:
                    intent.status = TaskState.COMPLETED if success else TaskState.FAILED
                    logger.info("intent_resolved", intent_id=intent.id, success=success)
                    return

    def get_active_intents(self, tenant_id: str) -> List[PendingIntent]:
        return [
            intent for intent in self._intents.get(tenant_id, [])
            if intent.status in [TaskState.PENDING, TaskState.EXECUTING, TaskState.WAITING_HITL]
        ]

# Singleton
intent_store = IntentStore()
