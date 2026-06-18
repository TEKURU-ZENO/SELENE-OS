"""
SELENE OS — Learning Audit Log
Tracks why a procedural update was accepted, the evidence used, and confidence evolution.
"""

from schemas import LearningAuditEntry, ProceduralUpdate
import structlog

logger = structlog.get_logger(__name__)

class AuditLog:
    def __init__(self):
        self._logs = []
        
    def record(self, update: ProceduralUpdate, action: str, reason: str):
        entry = LearningAuditEntry(
            procedural_update=update,
            action_taken=action,
            reason=reason
        )
        self._logs.append(entry)
        logger.info("audit_log_recorded", action=action, update_context=update.trigger_context)
        
    def get_logs(self):
        return self._logs

# Singleton
audit_log = AuditLog()
