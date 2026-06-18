"""
SELENE OS — Artifact Store
Tracks screenshots, DOM snapshots, and downloaded files.
"""

import os
from typing import Dict, List
import structlog

logger = structlog.get_logger(__name__)

ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../workspace/artifacts"))
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

class ArtifactStore:
    def __init__(self):
        # Maps execution_id -> list of artifact paths
        self._artifacts: Dict[str, List[str]] = {}

    def register_artifact(self, execution_id: str, path: str) -> None:
        if execution_id not in self._artifacts:
            self._artifacts[execution_id] = []
        self._artifacts[execution_id].append(path)
        logger.debug("artifact_registered", execution_id=execution_id, path=path)

    def get_artifacts(self, execution_id: str) -> List[str]:
        return self._artifacts.get(execution_id, [])

# Singleton
artifact_store = ArtifactStore()
