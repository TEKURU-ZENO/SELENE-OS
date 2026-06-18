"""
SELENE OS — Native Context Layer
Manages semantic context emitted by connectors, enforcing Context Expiration (differential half-life).
"""

from typing import List, Dict
from datetime import datetime, timedelta
from schemas import NativeContextEvent, ContextCategory
import structlog

logger = structlog.get_logger(__name__)


class NativeContextRuntime:
    def __init__(self):
        # tenant_id -> List[NativeContextEvent]
        self._active_context: Dict[str, List[NativeContextEvent]] = {}

    def ingest_event(self, event: NativeContextEvent):
        """Receives semantic context from a connector and adds it to the active pool."""
        if event.tenant_id not in self._active_context:
            self._active_context[event.tenant_id] = []
            
        self._active_context[event.tenant_id].append(event)
        logger.info("context_ingested", app=event.app_source, semantic=event.semantic_event)
        
    def get_valid_context(self, tenant_id: str) -> List[NativeContextEvent]:
        """Returns context that has NOT decayed past its half-life."""
        self._decay_context(tenant_id)
        return self._active_context.get(tenant_id, [])

    def _decay_context(self, tenant_id: str):
        """Purges context signals that exceed their defined temporal bounds."""
        if tenant_id not in self._active_context:
            return
            
        now = datetime.utcnow()
        valid = []
        
        for event in self._active_context[tenant_id]:
            age = now - event.timestamp
            
            # Differential Half-Life Logic
            if event.category == ContextCategory.ACTIVE_WINDOW and age < timedelta(minutes=30):
                valid.append(event)
            elif event.category == ContextCategory.WORKFLOW_INTENT and age < timedelta(hours=4):
                valid.append(event)
            elif event.category == ContextCategory.BEHAVIORAL_PATTERN and age < timedelta(days=2):
                valid.append(event)
            elif event.category == ContextCategory.PROCEDURAL_PREF and age < timedelta(weeks=4):
                valid.append(event)
            else:
                logger.debug("context_decayed", event=event.semantic_event)
                
        self._active_context[tenant_id] = valid

# Singleton
context_runtime = NativeContextRuntime()
