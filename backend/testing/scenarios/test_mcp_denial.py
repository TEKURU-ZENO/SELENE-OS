"""
SELENE OS — MCP Denial Test (Golden Trace)
Simulates an aggressive context boundary corruption attempt by the GitHub MCP.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


from mcp.sandbox.policy_gate import policy_gate
from mcp.manifests.github_mcp import github_mcp_manifest
from schemas import ContextCategory, TrustControls, ProactivityTier, MemoryTier, OrganizationalMemoryTier
import structlog

logger = structlog.get_logger(__name__)

def test_mcp_cross_domain_denial():
    """Verify cross-domain context boundary attack is hard-denied by PolicyGate."""
    controls = TrustControls(
        tenant_id="tenant_1",
        proactivity_tier=ProactivityTier.SUGGESTIVE,
        allow_autonomous_execution=False,
        default_memory_tier=MemoryTier.LOCAL_PERSISTENT,
        org_tier_clearance=OrganizationalMemoryTier.TEAM
    )

    class MockTemporalContext:
        value = "personal_temporal_memory"

    attack_context = [MockTemporalContext()]
    outcome = policy_gate.evaluate_execution_request(
        manifest=github_mcp_manifest,
        active_contexts=attack_context,
        tenant_controls=controls
    )
    assert outcome.approved is False, "MCP was allowed to access restricted cross-domain memory!"
    assert "personal_temporal_memory" in outcome.reason or "denied" in outcome.reason.lower()
    logger.info("test_passed", reason="HARD DENY successfully triggered", policy_reason=outcome.reason)


def run_denial_test():
    logger.info("starting_mcp_denial_test")
    test_mcp_cross_domain_denial()

if __name__ == "__main__":
    run_denial_test()
