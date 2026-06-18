"""
SELENE OS — Connectors Base Architecture
Defines the strict plugin interface for cross-application continuity.
"""

from abc import ABC, abstractmethod
from typing import List
from schemas import NativeContextEvent, ConnectorManifest

class BaseConnector(ABC):
    """
    All integrations (VSCode, Slack, GitHub) must implement this interface.
    Connectors DO NOT have direct access to memory. They only emit semantic context.
    """
    def __init__(self, manifest: ConnectorManifest):
        self.manifest = manifest

    @abstractmethod
    async def poll_context(self) -> List[NativeContextEvent]:
        """
        Gathers raw app data and MUST abstract it into Semantic NativeContextEvents.
        Should never emit raw telemetry or sensitive PII payloads.
        """
        pass
        
    @abstractmethod
    async def execute_capability(self, capability_name: str, params: dict):
        """
        Execute an action if permitted by the Trust Layer.
        """
        pass
