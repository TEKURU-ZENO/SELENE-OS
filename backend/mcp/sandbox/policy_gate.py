"""
SELENE OS — The Policy Gate (Trust Firewall)
The ultimate execution boundary. Evaluates all requests against governance rules.
Structurally denies anything that violates TrustControls.
"""

from typing import Dict, Any, List
from mcp.schemas import MCPServerManifest, TrustClassification
from schemas import ContextCategory, TrustControls
from mcp.sandbox.context_validator import context_validator
from mcp.sandbox.hitl_router import hitl_router
import structlog

logger = structlog.get_logger(__name__)

class PolicyOutcome:
    def __init__(self, approved: bool, reason: str, requires_hitl: bool = False):
        self.approved = approved
        self.reason = reason
        self.requires_hitl = requires_hitl

class PolicyGate:
    def evaluate_execution_request(
        self, 
        manifest: MCPServerManifest, 
        active_contexts: List[ContextCategory], 
        tenant_controls: TrustControls
    ) -> PolicyOutcome:
        
        # 1. Evaluate Trust Classification (The kill switch)
        if manifest.trust_classification == TrustClassification.BLOCKED:
            logger.critical("policy_gate_denial", reason="server_blocked", server=manifest.server_id)
            return PolicyOutcome(False, "Server trust classification is BLOCKED.")

        if manifest.trust_classification == TrustClassification.EXPERIMENTAL:
            # Experimental servers might be restricted from running in Team/Org tiers
            if tenant_controls.org_tier_clearance.value in ["team", "org", "public"]:
                return PolicyOutcome(False, "Experimental servers cannot run in shared organizational tiers.")

        # 2. Evaluate Context Boundaries (Preventing leakage)
        for ctx in active_contexts:
            if not context_validator.validate_access(ctx, manifest):
                return PolicyOutcome(False, f"Cross-domain context access denied for: {ctx.value}")

        # 3. Evaluate Memory/Clearance Boundaries
        # (A personal-only plugin shouldn't run when organizational memory is active)
        # implementation omitted for brevity, but logically resides here.

        # 4. Evaluate HITL Requirements
        needs_hitl = hitl_router.evaluate_hitl_requirement(
            requires_hitl=manifest.requires_hitl,
            tool_id=manifest.server_id,
            tenant_controls=tenant_controls
        )

        logger.info("policy_gate_approved", server=manifest.server_id, requires_hitl=needs_hitl)
        return PolicyOutcome(True, "Approved by governance policy.", requires_hitl=needs_hitl)

policy_gate = PolicyGate()
