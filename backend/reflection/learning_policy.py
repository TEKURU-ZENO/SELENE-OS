"""
SELENE OS — Learning Policy Engine
The final gatekeeper. Prevents noisy learning, handles confidence thresholds,
and detects contradictions before writing to Procedural Memory.
"""

from typing import List, Tuple
from schemas import ProceduralUpdate
import structlog

logger = structlog.get_logger(__name__)


class LearningPolicyEngine:
    CONFIDENCE_THRESHOLD = 0.85
    MIN_RECURRENCE = 2

    def evaluate(self, proposed_updates: List[ProceduralUpdate], existing_memory: List[ProceduralUpdate]) -> Tuple[List[ProceduralUpdate], List[str]]:
        """
        Filters proposed updates based on thresholds and contradictions.
        Returns (approved_updates, rejection_reasons).
        """
        approved = []
        reasons = []
        
        for update in proposed_updates:
            # 1. Confidence Check
            if update.confidence < self.CONFIDENCE_THRESHOLD:
                reasons.append(f"Rejected: Confidence {update.confidence} below threshold {self.CONFIDENCE_THRESHOLD}.")
                continue
                
            # 2. Recurrence Check
            if update.recurrence_count < self.MIN_RECURRENCE:
                reasons.append(f"Rejected: Recurrence {update.recurrence_count} below threshold {self.MIN_RECURRENCE}.")
                continue
                
            # 3. Contradiction Detection
            # Naive contradiction check: If recommendation differs for same trigger context
            contradiction_found = False
            for memory in existing_memory:
                if memory.trigger_context == update.trigger_context and memory.recommendation != update.recommendation:
                    contradiction_found = True
                    # Lower confidence of both or request more evidence
                    reasons.append(f"Rejected: Contradicts existing memory for {update.trigger_context}.")
                    break
                    
            if not contradiction_found:
                approved.append(update)
                logger.info("procedural_update_approved", context=update.trigger_context)
                
        return approved, reasons

# Singleton
learning_policy = LearningPolicyEngine()
