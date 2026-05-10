"""
SELENE OS — Hybrid Retrieval & Context Compression
Implements the retrieval pipeline: Dense + Sparse -> Scoring -> RRF -> Compression.
"""

from typing import List, Dict
from schemas import (
    ContextBundle, BaseMemory, EpisodicMemory, SemanticMemory, ProceduralMemory, IntentResult
)
from memory.stores import episodic_store, semantic_store, procedural_store, working_store
from memory.context_compressor import context_compressor
import structlog

logger = structlog.get_logger(__name__)


class RetrievalEngine:
    """Orchestrates the Hybrid Retrieval Pipeline."""

    def retrieve(self, query: str, session_id: str, intent_result: IntentResult) -> ContextBundle:
        """Executes the full retrieval and compression pipeline."""
        logger.info("retrieval_started", query=query[:30], intent=intent_result.intent.value)

        # 1. Intent Analysis & Store Selection (Weighting)
        weights = self._get_store_weights(intent_result)

        # 2. Mock Dense + Sparse Search
        raw_episodic = episodic_store.search(query, limit=10)
        raw_semantic = semantic_store.search(query, limit=10)
        raw_procedural = procedural_store.search(query, limit=5)

        # 3. Apply Metadata Scoring & RRF
        scored_episodic = self._apply_rrf_scoring(raw_episodic, weights["episodic"])
        scored_semantic = self._apply_rrf_scoring(raw_semantic, weights["semantic"])
        scored_procedural = self._apply_rrf_scoring(raw_procedural, weights["procedural"])

        # 4. Fetch Working Memory
        working_mem = working_store.get_state(session_id)

        # 5. Context Compression Pipeline
        compressed_bundle = context_compressor.compress(
            session_id=session_id,
            episodic=scored_episodic,
            semantic=scored_semantic,
            procedural=scored_procedural,
            working=working_mem
        )

        return compressed_bundle

    def _get_store_weights(self, intent_result: IntentResult) -> Dict[str, float]:
        intent = intent_result.intent.value
        if intent == "task":
            return {"episodic": 0.3, "semantic": 0.8, "procedural": 1.0}
        elif intent == "casual":
            return {"episodic": 1.0, "semantic": 0.4, "procedural": 0.1}
        elif intent == "analysis":
            return {"episodic": 0.5, "semantic": 1.0, "procedural": 0.5}
        else:
            return {"episodic": 0.6, "semantic": 0.6, "procedural": 0.6}

    def _apply_rrf_scoring(self, memories: List[BaseMemory], weight_multiplier: float) -> List[BaseMemory]:
        for m in memories:
            meta = m.metadata
            decay = meta.decay_factor 
            final_score = (meta.importance * meta.confidence * decay) * weight_multiplier
            setattr(m, "_retrieval_score", final_score)
            
        memories.sort(key=lambda x: getattr(x, "_retrieval_score", 0), reverse=True)
        return memories

# Singleton
retrieval_engine = RetrievalEngine()
