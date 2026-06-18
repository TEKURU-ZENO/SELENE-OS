"""
SELENE OS — Cognitive Health Dashboard Metrics
Operational observability for the meta-cognitive layer.
"""

from schemas import CognitiveHealthMetrics
import structlog

logger = structlog.get_logger(__name__)


class HealthMetricsTracker:
    def __init__(self):
        self._metrics = CognitiveHealthMetrics(
            avg_dag_depth=0.0,
            planner_repair_rate=0.0,
            critic_rejection_rate=0.0,
            tool_success_rate=0.0,
            timeout_distribution={},
            accepted_learnings_count=0,
            rejected_learnings_count=0,
            contradiction_frequency=0.0,
            hitl_interrupt_frequency=0.0,
            hitl_modification_rate=0.0
        )
        
    def get_current_metrics(self) -> CognitiveHealthMetrics:
        """Fetch the current aggregated system health metrics."""
        return self._metrics

# Singleton
health_tracker = HealthMetricsTracker()
