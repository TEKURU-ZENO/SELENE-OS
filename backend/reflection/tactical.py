"""
SELENE OS — Tactical Reflection
Aggregates multiple OperationalReflections to identify repeated task patterns.
"""

from typing import List
from schemas import OperationalReflection, TacticalReflection
import structlog

logger = structlog.get_logger(__name__)


class TacticalReflectionEngine:
    def aggregate(self, history: List[OperationalReflection]) -> List[TacticalReflection]:
        """
        Groups operational reflections by pattern.
        """
        logger.info("tactical_reflection_started", history_size=len(history))
        
        failure_counts = {}
        for op in history:
            if op.tool_failure:
                tool_name = op.tool_failure.split("_failed")[0]
                if tool_name not in failure_counts:
                    failure_counts[tool_name] = []
                failure_counts[tool_name].append(op.execution_id)
                
        tactical_reflections = []
        for tool_name, execution_ids in failure_counts.items():
            if len(execution_ids) > 1: # Basic recurrence check
                tactical_reflections.append(TacticalReflection(
                    pattern=f"{tool_name}_consistent_failure",
                    frequency=len(execution_ids),
                    related_operational_ids=execution_ids
                ))
                
        return tactical_reflections

# Singleton
tactical_reflection = TacticalReflectionEngine()
