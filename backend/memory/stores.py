"""
SELENE OS — Memory Stores (Episodic, Semantic, Procedural, Working)
Implements the Tri-partite + Working memory architecture.

For Phase 3 MVP, these are in-memory with FAISS capabilities mocked.
Phase 5 integrates real pgvector/FAISS.
"""

from typing import List, Dict, Any, Optional
import time
import hashlib
from schemas import (
    EpisodicMemory, SemanticMemory, ProceduralMemory, WorkingMemory,
    MemoryMetadata, MemoryType
)
import structlog

logger = structlog.get_logger(__name__)


# ── Episodic Store ("What happened?") ──────────────────────────

class EpisodicStore:
    def __init__(self):
        self._memories: List[EpisodicMemory] = []

    def add(self, content: str, event_type: str = "conversation", importance: float = 0.5, tags: List[str] = None) -> EpisodicMemory:
        mem = EpisodicMemory(
            content=content,
            event_type=event_type,
            metadata=MemoryMetadata(importance=importance, tags=tags or [], source="system")
        )
        self._memories.append(mem)
        logger.debug("episodic_memory_added", event_type=event_type)
        return mem

    def get_recent(self, limit: int = 10) -> List[EpisodicMemory]:
        """Get the most recent episodic events."""
        return sorted(self._memories, key=lambda x: x.created_at, reverse=True)[:limit]
    
    def search(self, query: str, limit: int = 5) -> List[EpisodicMemory]:
        # Mock Dense/Sparse search
        matches = [m for m in self._memories if query.lower() in m.content.lower()]
        return sorted(matches, key=lambda x: x.metadata.importance, reverse=True)[:limit]


# ── Semantic Store ("What is true?") ───────────────────────────

class SemanticStore:
    def __init__(self):
        self._memories: Dict[str, SemanticMemory] = {}

    def _hash_fact(self, content: str) -> str:
        """Generate a stable hash for a semantic fact to ensure deduplication."""
        return hashlib.sha256(content.lower().strip().encode('utf-8')).hexdigest()

    def add_or_update(self, content: str, confidence: float = 1.0, importance: float = 0.8, tags: List[str] = None) -> SemanticMemory:
        """
        Add a new fact or update the confidence/access time of an existing one.
        Prevents hallucinated facts from becoming permanent without deduplication.
        """
        fact_hash = self._hash_fact(content)
        
        if fact_hash in self._memories:
            mem = self._memories[fact_hash]
            mem.metadata.access_count += 1
            mem.metadata.confidence = min(1.0, mem.metadata.confidence + 0.1) # Boost confidence
            from datetime import datetime
            mem.last_accessed = datetime.utcnow()
            logger.debug("semantic_memory_updated", fact_hash=fact_hash)
            return mem
        else:
            mem = SemanticMemory(
                content=content,
                fact_hash=fact_hash,
                metadata=MemoryMetadata(confidence=confidence, importance=importance, tags=tags or [])
            )
            self._memories[fact_hash] = mem
            logger.debug("semantic_memory_added", content=content[:30])
            return mem

    def search(self, query: str, limit: int = 5) -> List[SemanticMemory]:
        # Mock search
        matches = [m for m in self._memories.values() if query.lower() in m.content.lower()]
        return sorted(matches, key=lambda x: x.metadata.confidence * x.metadata.importance, reverse=True)[:limit]


# ── Procedural Store ("How does the user operate?") ─────────────

class ProceduralStore:
    def __init__(self):
        self._memories: List[ProceduralMemory] = []

    def add(self, workflow_data: Dict[str, Any], trigger_context: str, importance: float = 0.9) -> ProceduralMemory:
        mem = ProceduralMemory(
            content=workflow_data,
            trigger_context=trigger_context,
            metadata=MemoryMetadata(importance=importance, source="reflection_engine")
        )
        self._memories.append(mem)
        logger.info("procedural_memory_added", trigger=trigger_context)
        return mem

    def search(self, context_query: str, limit: int = 3) -> List[ProceduralMemory]:
        # Mock search based on trigger context
        matches = [m for m in self._memories if context_query.lower() in m.trigger_context.lower()]
        return sorted(matches, key=lambda x: x.metadata.importance, reverse=True)[:limit]


# ── Working Memory ("Active task state") ───────────────────────

class WorkingMemoryStore:
    def __init__(self):
        self._sessions: Dict[str, WorkingMemory] = {}

    def set_state(self, session_id: str, state_data: Dict[str, Any]) -> WorkingMemory:
        """Update the active working memory for a session."""
        mem = WorkingMemory(
            session_id=session_id,
            content=state_data,
            metadata=MemoryMetadata(importance=1.0) # Always highest importance
        )
        self._sessions[session_id] = mem
        logger.debug("working_memory_updated", session_id=session_id)
        return mem

    def get_state(self, session_id: str) -> Optional[WorkingMemory]:
        return self._sessions.get(session_id)
    
    def clear(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]


# Singleton Instances
episodic_store = EpisodicStore()
semantic_store = SemanticStore()
procedural_store = ProceduralStore()
working_store = WorkingMemoryStore()
