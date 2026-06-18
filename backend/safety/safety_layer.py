"""
SELENE OS — Safety Module (Cross-Cutting)
Applied at: planning, execution, and response layers.

🔧 NOT a top layer. This is a cross-cutting concern invoked by the orchestrator
at multiple pipeline stages: before planning, before execution, and before response.
"""

from typing import Optional
from datetime import datetime
from schemas import (
    RiskLevel, SafetyCheck, SafetyAuditEntry, SafetyAction,
    PlanNode, ExecutionPlan,
)
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)


# ── Risk Classification Rules ────────────────────────────────────

# Actions that require human confirmation
HIGH_RISK_ACTIONS = {
    "file_write", "file_delete", "system_exec", "email_send",
    "browser_action", "database_modify", "deploy", "install",
    "api_call_mutation", "credential_access",
}

# Actions that are outright blocked without override
BLOCKED_ACTIONS = {
    "system_shutdown", "format_disk", "delete_all",
    "credential_export", "network_config_change",
}

# Safe actions that execute without confirmation
SAFE_ACTIONS = {
    "web_search", "file_read", "analyze", "summarize",
    "generate_text", "explain", "calculate",
}


class SafetyLayer:
    """
    Cross-cutting safety enforcement.
    
    Invoked by the orchestrator at:
    1. Planning stage — validate plan nodes for risk
    2. Execution stage — gate individual actions
    3. Response stage — flag unsafe content
    """

    def __init__(self):
        self._audit_log: list[SafetyAuditEntry] = []

    # ── Action Classification ────────────────────────────────

    def classify_action(self, action: str, context: dict = None) -> SafetyCheck:
        """Classify an action's risk level and determine if it needs confirmation."""
        action_lower = action.lower().strip()

        # Check blocked actions
        for blocked in BLOCKED_ACTIONS:
            if blocked in action_lower:
                check = SafetyCheck(
                    action=action,
                    risk_level=RiskLevel.CRITICAL,
                    requires_confirmation=False,
                    blocked=True,
                    reason=f"Action '{action}' is blocked by safety policy.",
                )
                self._log_audit(action, RiskLevel.CRITICAL, SafetyAction.REJECT, "auto_blocked")
                logger.warning("safety_blocked", action=action)
                return check

        # Check high-risk actions
        for risky in HIGH_RISK_ACTIONS:
            if risky in action_lower:
                check = SafetyCheck(
                    action=action,
                    risk_level=RiskLevel.HIGH,
                    requires_confirmation=True,
                    blocked=False,
                    reason=f"Action '{action}' requires user confirmation.",
                )
                logger.info("safety_confirmation_required", action=action)
                return check

        # Check confirmed-safe actions
        for safe in SAFE_ACTIONS:
            if safe in action_lower:
                return SafetyCheck(
                    action=action,
                    risk_level=RiskLevel.LOW,
                    requires_confirmation=False,
                    blocked=False,
                )

        # Default: medium risk, no confirmation needed
        return SafetyCheck(
            action=action,
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=False,
            blocked=False,
        )

    # ── Plan Validation ──────────────────────────────────────

    def validate_plan(self, plan: ExecutionPlan) -> list[SafetyCheck]:
        """
        Validate all nodes in a plan for safety.
        Returns a list of safety checks — orchestrator uses these to
        gate execution or request confirmation.
        """
        checks = []
        for node in plan.nodes:
            check = self.classify_action(node.action)
            node.risk_level = check.risk_level  # Annotate the node
            checks.append(check)

        blocked_count = sum(1 for c in checks if c.blocked)
        confirm_count = sum(1 for c in checks if c.requires_confirmation)

        logger.info(
            "safety_plan_validated",
            plan_id=plan.plan_id,
            total_nodes=len(plan.nodes),
            blocked=blocked_count,
            needs_confirmation=confirm_count,
        )

        return checks

    # ── Audit Logging ────────────────────────────────────────

    def _log_audit(
        self,
        action: str,
        risk_level: RiskLevel,
        decision: SafetyAction,
        actor: str = "system",
        details: dict = None,
    ):
        """Record a safety decision in the audit log."""
        entry = SafetyAuditEntry(
            action=action,
            risk_level=risk_level,
            decision=decision,
            actor=actor,
            details=details,
        )
        self._audit_log.append(entry)
        logger.info(
            "safety_audit",
            action=action,
            risk=risk_level.value,
            decision=decision.value,
        )

    def record_decision(
        self,
        action: str,
        risk_level: RiskLevel,
        decision: SafetyAction,
        actor: str = "user",
    ):
        """Record a user's safety decision (approve/reject/edit)."""
        self._log_audit(action, risk_level, decision, actor)

    def get_audit_log(self, limit: int = 100) -> list[SafetyAuditEntry]:
        """Retrieve recent audit entries."""
        return self._audit_log[-limit:]

    def get_stats(self) -> dict:
        """Get safety statistics."""
        if not self._audit_log:
            return {"total": 0, "approved": 0, "rejected": 0, "blocked": 0}

        return {
            "total": len(self._audit_log),
            "approved": sum(1 for e in self._audit_log if e.decision == SafetyAction.APPROVE),
            "rejected": sum(1 for e in self._audit_log if e.decision == SafetyAction.REJECT),
            "blocked": sum(1 for e in self._audit_log if e.risk_level == RiskLevel.CRITICAL),
        }


# Singleton
safety_layer = SafetyLayer()
