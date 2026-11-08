"""
SELENE OS — Hybrid Retrieval & Context Compression
Implements the retrieval pipeline: Dense + Sparse -> Scoring -> RRF -> Stratification -> Compression.
"""

import json
import math
import asyncio
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any
from schemas import (
    ContextBundle, BaseMemory, EpisodicMemory, SemanticMemory, ProceduralMemory, IntentResult
)
from memory.stores import episodic_store, semantic_store, procedural_store, working_store
from memory.context_compressor import context_compressor
import structlog

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run an async coroutine from synchronous code safely."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
        
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


class RetrievalEngine:
    """Orchestrates the Hybrid Retrieval Pipeline."""

    def retrieve(self, query: str, session_id: str, intent_result: IntentResult) -> ContextBundle:
        """Executes the full retrieval and compression pipeline."""
        logger.info("retrieval_started", query=query[:30], intent=intent_result.intent.value)

        # 1. Intent Analysis & Store Selection (Weighting)
        weights = self._get_store_weights(intent_result)

        # 2. Hybrid Search from VectorStore
        from memory.vector_store import vector_store
        hybrid_results = []
        try:
            hybrid_results = run_async(vector_store.search(query, k=15))
        except Exception as e:
            logger.error("hybrid_search_failed_falling_back", error=str(e))

        raw_episodic = []
        raw_semantic = []
        raw_procedural = []

        for res in hybrid_results:
            t = res.get("type", "semantic")
            content = res.get("text", "")
            importance = res.get("importance", 0.5)

            if t == "episodic":
                from schemas import MemoryMetadata
                raw_episodic.append(EpisodicMemory(
                    content=content,
                    event_type=res.get("event_type", "conversation"),
                    metadata=MemoryMetadata(importance=importance, tags=res.get("tags", []), source=res.get("source", "system"))
                ))
            elif t == "procedural":
                from schemas import MemoryMetadata
                raw_procedural.append(ProceduralMemory(
                    content=res.get("workflow_data", {}),
                    trigger_context=content,
                    metadata=MemoryMetadata(importance=importance, source="reflection_engine")
                ))
            else:
                from schemas import MemoryMetadata
                raw_semantic.append(SemanticMemory(
                    content=content,
                    fact_hash=res.get("fact_hash"),
                    metadata=MemoryMetadata(confidence=res.get("confidence", 1.0), importance=importance, tags=res.get("tags", []))
                ))

        # Fallback to local store search if hybrid search returned nothing
        if not hybrid_results:
            raw_episodic = episodic_store.search(query, limit=10)
            raw_semantic = semantic_store.search(query, limit=10)
            raw_procedural = procedural_store.search(query, limit=5)

        # 3. Apply Metadata Scoring, RRF & Exponential Temporal Decay
        scored_episodic = self._apply_rrf_scoring(raw_episodic, weights["episodic"])
        scored_semantic = self._apply_rrf_scoring(raw_semantic, weights["semantic"])
        scored_procedural = self._apply_rrf_scoring(raw_procedural, weights["procedural"])

        # 4. Fetch Working Memory
        working_mem = working_store.get_state(session_id)

        # 5. Stratify retrieved memories into 5 logical layers
        stratified = self._stratify_memories(scored_episodic, scored_semantic, scored_procedural)
        logger.info("memory_stratification_complete", 
                    principles=len(stratified["principles"]),
                    styles=len(stratified["stylistic"]),
                    rules=len(stratified["rules"]),
                    facts=len(stratified["facts"]),
                    logs=len(stratified["logs"]))

        # 6. Context Compression Pipeline
        compressed_bundle = context_compressor.compress(
            session_id=session_id,
            episodic=scored_episodic,
            semantic=scored_semantic,
            procedural=scored_procedural,
            working=working_mem
        )

        # Inject the stratified memory blocks into the semantic context list
        stratified_blocks = []
        for category, items in stratified.items():
            if items:
                stratified_blocks.append(f"[{category.upper()}]")
                for item in items[:3]:  # limit to top 3 per stratum
                    stratified_blocks.append(f"- {item}")
        
        if stratified_blocks:
            compressed_bundle.semantic.insert(0, "\n".join(stratified_blocks))

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
        now = datetime.utcnow()
        for m in memories:
            meta = m.metadata
            
            # Exponential temporal decay calculation (e^(-lambda * dt_hours))
            dt_hours = max(0.0, (now - m.created_at).total_seconds() / 3600.0)
            lambda_val = getattr(meta, "decay_rate", getattr(m, "decay_rate", 0.05))
            decay = math.exp(-lambda_val * dt_hours)
            
            meta.recency_score = decay
            final_score = (meta.importance * meta.confidence * decay) * weight_multiplier
            setattr(m, "_retrieval_score", final_score)
            
        memories.sort(key=lambda x: getattr(x, "_retrieval_score", 0), reverse=True)
        return memories

    def _stratify_memories(self, episodic: List[EpisodicMemory], semantic: List[SemanticMemory], procedural: List[ProceduralMemory]) -> Dict[str, List[str]]:
        stratified = {
            "principles": [],
            "stylistic": [],
            "rules": [],
            "facts": [],
            "logs": []
        }
        
        all_memories = episodic + semantic + procedural
        
        for m in all_memories:
            tags = [t.lower() for t in getattr(m.metadata, "tags", [])]
            content = getattr(m, "content", "")
            if isinstance(content, dict):
                # Format procedural context nicely
                content = f"Workflow trigger: {getattr(m, 'trigger_context', '')} -> {json.dumps(content)}"
            
            content_lower = content.lower()
            
            # Principles Layer
            if "principles" in tags or "guideline" in tags or "principle" in tags:
                stratified["principles"].append(content)
            # Stylistic Patterns Layer
            elif "style" in tags or "tone" in tags or "personalization" in tags:
                stratified["stylistic"].append(content)
            # Rules Layer
            elif "rules" in tags or "policy" in tags or "safety" in tags:
                stratified["rules"].append(content)
            # Facts Layer
            elif isinstance(m, SemanticMemory) or "fact" in tags:
                stratified["facts"].append(content)
            # Logs Layer
            else:
                stratified["logs"].append(content)
                
        return stratified


# Singleton
retrieval_engine = RetrievalEngine()
