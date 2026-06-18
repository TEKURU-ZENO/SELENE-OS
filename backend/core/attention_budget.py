"""
SELENE OS — Attention Budgeting System
Calculates interruption sensitivity, filters cognitive spam, and ensures 
SELENE respects Cognitive Quiet Hours and Trust Controls.
"""

from datetime import datetime
from schemas import ProactiveSuggestion, TrustControls, SuggestionStatus
import structlog

logger = structlog.get_logger(__name__)


class AttentionBudgetManager:
    def __init__(self):
        # Mock tracking of user fatigue: tenant_id -> sensitivity score (0.0 to 1.0)
        self._user_fatigue: dict[str, float] = {}

    def calculate_attention_score(
        self, tenant_id: str, urgency: float, confidence: float, attention_cost: float, controls: TrustControls
    ) -> float:
        """
        Combines urgency, confidence, cost, and historical fatigue into a final score.
        A high score means the suggestion should be surfaced.
        """
        # 1. Quiet Hours Check
        if self._is_quiet_hours(controls):
            # During quiet hours, require extreme urgency/confidence
            if urgency < 0.9 or confidence < 0.9:
                return 0.0

        # 2. Interruption Sensitivity (Fatigue)
        fatigue = self._user_fatigue.get(tenant_id, 0.5)
        
        # Base formula: (Urgency + Confidence) - (Cost + Fatigue)
        # Bounded between 0 and 1.
        raw_score = ((urgency * 1.5) + confidence) - (attention_cost + (fatigue * 2.0))
        final_score = max(0.0, min(1.0, raw_score / 2.5))
        
        return final_score

    def record_suggestion_lifecycle(self, tenant_id: str, suggestion: ProactiveSuggestion):
        """Adjusts the user's fatigue/sensitivity based on how they handled the suggestion."""
        current_fatigue = self._user_fatigue.get(tenant_id, 0.5)
        
        if suggestion.status == SuggestionStatus.ACCEPTED:
            # They liked it, reduce fatigue slightly
            new_fatigue = max(0.0, current_fatigue - 0.1)
        elif suggestion.status in [SuggestionStatus.IGNORED, SuggestionStatus.DISMISSED]:
            # They didn't like it, increase fatigue to prevent cognitive spam
            new_fatigue = min(1.0, current_fatigue + 0.2)
            logger.warning("suggestion_rejected_increasing_fatigue", tenant_id=tenant_id, new_fatigue=new_fatigue)
        elif suggestion.status == SuggestionStatus.DEFERRED:
            # They want it later, neutral fatigue impact
            new_fatigue = current_fatigue
        else:
            new_fatigue = current_fatigue
            
        self._user_fatigue[tenant_id] = new_fatigue

    def _is_quiet_hours(self, controls: TrustControls) -> bool:
        now = datetime.now().time()
        start = controls.quiet_hours_start
        end = controls.quiet_hours_end
        
        if start <= end:
            return start <= now <= end
        else: # Crosses midnight
            return start <= now or now <= end

# Singleton
attention_budget = AttentionBudgetManager()
