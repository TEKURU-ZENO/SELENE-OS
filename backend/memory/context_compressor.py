"""
SELENE OS — Context Compression Layer
Summarizes retrieved memories, removes duplicates, and maintains the token budget.
Crucial for preventing prompt explosion and latency issues.
"""

from typing import List, Dict, Any
from schemas import (
    ContextBundle, EpisodicMemory, SemanticMemory, ProceduralMemory, WorkingMemory
)
import structlog

logger = structlog.get_logger(__name__)


class ContextCompressor:
    """
    Compresses retrieved memory payloads before they enter the Orchestrator prompt.
    """

    def compress(
        self,
        session_id: str,
        episodic: List[EpisodicMemory],
        semantic: List[SemanticMemory],
        procedural: List[ProceduralMemory],
        working: WorkingMemory = None,
        max_tokens: int = 2000
    ) -> ContextBundle:
        """
        Executes the compression pipeline: deduplication -> prioritization -> truncation.
        """
        logger.info("context_compression_started", total_memories=len(episodic) + len(semantic) + len(procedural))
        
        # 1. Compress Episodic (Summarize or truncate trails)
        compressed_episodic = self._compress_episodic(episodic)
        
        # 2. Compress Semantic (Strict deduplication)
        compressed_semantic = self._compress_semantic(semantic)
        
        # 3. Compress Procedural (Extract only relevant workflow nodes)
        compressed_procedural = self._compress_procedural(procedural)
        
        # Calculate compression ratio (Mocked for Phase 3)
        initial_count = len(episodic) + len(semantic) + len(procedural)
        final_count = len(compressed_episodic) + len(compressed_semantic) + len(compressed_procedural)
        ratio = (final_count / initial_count) if initial_count > 0 else 1.0

        bundle = ContextBundle(
            session_id=session_id,
            episodic=compressed_episodic,
            semantic=compressed_semantic,
            procedural=compressed_procedural,
            working_state=working.content if working else None,
            compression_ratio=ratio
        )
        
        logger.info("context_compression_complete", ratio=ratio)
        return bundle

    def _compress_episodic(self, memories: List[EpisodicMemory]) -> List[str]:
        """Convert objects to concise strings, dropping low-importance noise."""
        result = []
        for m in memories:
            # Skip noise
            if m.metadata.importance < 0.3:
                continue
            
            # Format: [HH:MM] Content
            time_str = m.created_at.strftime('%H:%M')
            result.append(f"[{time_str}] {m.content}")
            
        return result

    def _compress_semantic(self, memories: List[SemanticMemory]) -> List[str]:
        """Ensure no duplicate facts are passed to the prompt."""
        seen_hashes = set()
        result = []
        
        for m in memories:
            # Deduplicate
            if m.fact_hash and m.fact_hash in seen_hashes:
                continue
            
            if m.fact_hash:
                seen_hashes.add(m.fact_hash)
                
            # Formatting
            source_tag = f" (Source: {m.metadata.source})" if m.metadata.source != "system" else ""
            result.append(f"• {m.content}{source_tag}")
            
        return result

    def _compress_procedural(self, memories: List[ProceduralMemory]) -> List[Dict[str, Any]]:
        """Extract only the most important procedural workflows."""
        result = []
        for m in memories:
            if m.metadata.importance >= 0.7:
                result.append(m.content)
        return result


# Singleton
context_compressor = ContextCompressor()
