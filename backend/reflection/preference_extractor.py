"""
SELENE OS — Preference Extractor
Translates raw Procedural Updates into clean PlanningPreferences constraints.
Prevents procedural memory blobs from polluting the Planner's prompt.
"""

from typing import List
from schemas import ProceduralUpdate, PlanningPreferences
import structlog

logger = structlog.get_logger(__name__)


class PreferenceExtractor:
    def extract(self, procedural_memory: List[ProceduralUpdate]) -> PlanningPreferences:
        """
        Distills rules from procedural memory into strict planner constraints.
        """
        logger.debug("preference_extraction_started", memory_size=len(procedural_memory))
        
        prefs = PlanningPreferences()
        
        for update in procedural_memory:
            # MVP extraction logic
            if update.category == "tool_preference":
                if "Avoid" in update.recommendation:
                    prefs.avoid_patterns.append(update.recommendation)
                elif "Prefer" in update.recommendation:
                    # simplistic parse
                    prefs.preferred_capabilities[update.trigger_context] = update.recommendation
                    
        return prefs

# Singleton
preference_extractor = PreferenceExtractor()
