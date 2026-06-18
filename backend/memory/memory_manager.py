"""
SELENE OS — Memory Manager
Central facade coordinating the Tri-partite Memory System and Retrieval.
"""

from typing import Dict, Any, List
from schemas import IntentResult, ContextBundle, MemoryType
from memory.stores import episodic_store, semantic_store, procedural_store, working_store
from memory.retrieval import retrieval_engine
import structlog

logger = structlog.get_logger(__name__)


class MemoryManager:
    """
    Facade for all memory operations.
    The Orchestrator interacts ONLY with this manager, not the underlying stores.
    """

    def fetch_context(self, query: str, session_id: str, intent_result: IntentResult) -> ContextBundle:
        """Fetch the optimal compressed context bundle for the orchestrator."""
        return retrieval_engine.retrieve(query, session_id, intent_result)

    def log_interaction(self, session_id: str, role: str, content: str) -> None:
        """Log a conversational turn into episodic memory."""
        episodic_store.add(
            content=f"[{role.upper()}] {content}",
            event_type="conversation",
            importance=0.4
        )

    def learn_fact(self, fact_content: str, confidence: float = 0.8) -> None:
        """Save a discrete fact to semantic memory."""
        semantic_store.add_or_update(
            content=fact_content,
            confidence=confidence,
            importance=0.7
        )

    def learn_workflow(self, workflow_data: Dict[str, Any], trigger: str) -> None:
        """Save an execution pattern to procedural memory."""
        procedural_store.add(
            workflow_data=workflow_data,
            trigger_context=trigger,
            importance=0.9
        )

    def update_working_state(self, session_id: str, state_data: Dict[str, Any]) -> None:
        """Update the active task state in working memory."""
        working_store.set_state(session_id, state_data)

    def clear_working_state(self, session_id: str) -> None:
        """Clear the active task state when completed or aborted."""
        working_store.clear(session_id)


# Singleton
memory_manager = MemoryManager()
