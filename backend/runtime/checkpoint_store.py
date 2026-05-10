"""
SELENE OS — Checkpoint Store
Persists paused graphs, HITL resumes, and rollback states.
"""

from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

class CheckpointStore:
    def __init__(self):
        # Maps task_id -> state dict
        self._checkpoints: Dict[str, Dict[str, Any]] = {}

    def save_checkpoint(self, task_id: str, state: Dict[str, Any]) -> None:
        self._checkpoints[task_id] = state
        logger.info("checkpoint_saved", task_id=task_id)

    def load_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._checkpoints.get(task_id)

    def delete_checkpoint(self, task_id: str) -> None:
        if task_id in self._checkpoints:
            del self._checkpoints[task_id]

# Singleton
checkpoint_store = CheckpointStore()
