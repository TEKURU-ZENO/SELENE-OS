"""
SELENE OS — Cognitive Governance Layer
Enforces platform policies, validates plugin trust classifications, and maintains audit logs.
"""

from schemas import PluginManifest, RiskLevel
import structlog

logger = structlog.get_logger(__name__)


class PolicyEnforcer:
    
    def verify_plugin(self, manifest: PluginManifest) -> bool:
        """
        Validates if a plugin meets the platform's safety criteria before installation.
        """
        if manifest.trust_classification.risk_level == RiskLevel.CRITICAL:
            logger.error("plugin_rejected", reason="critical_risk_level", plugin=manifest.plugin_id)
            return False
            
        if "modify_system" in manifest.trust_classification.execution_scope and not manifest.requires_approval:
            logger.error("plugin_rejected", reason="unapproved_system_modification", plugin=manifest.plugin_id)
            return False
            
        manifest.trust_classification.verification_status = "verified"
        logger.info("plugin_verified_and_approved", plugin=manifest.plugin_id)
        return True

    def audit_execution(self, plugin_id: str, capability: str, success: bool):
        """Records execution history for trust scoring and abuse detection."""
        logger.info("audit_log", plugin=plugin_id, capability=capability, success=success)

# Singleton
policy_enforcer = PolicyEnforcer()
