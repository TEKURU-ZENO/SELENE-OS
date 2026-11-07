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

def run_denial_test():
    logger.info("starting_mcp_denial_test")
    
    # Mock user controls
    controls = TrustControls(
        tenant_id="tenant_1",
        proactivity_tier=ProactivityTier.SUGGESTIVE,
        allow_autonomous_execution=False,
        default_memory_tier=MemoryTier.LOCAL_PERSISTENT,
        org_tier_clearance=OrganizationalMemoryTier.TEAM
    )
    
    # ── Test 1: Allowed Context ──
    # Simulating a valid release workflow context
    valid_contexts = [ContextCategory.WORKFLOW_INTENT] 
    # Actually wait, GitHub MCP allowed_contexts=["release_workflow", "engineering_context"]
    # Our schema ContextCategory doesn't have "release_workflow" strings, they have categories. 
    # Let's assume the string representation is used for matching.
    
    # ── Test 2: The Attack (Personal Temporal Memory) ──
    class MockTemporalContext:
        value = "personal_temporal_memory"
        
    attack_context = [MockTemporalContext()]
    
    outcome = policy_gate.evaluate_execution_request(
        manifest=github_mcp_manifest,
        active_contexts=attack_context,
        tenant_controls=controls
    )
    
    if not outcome.approved:
        logger.info("test_passed", reason="HARD DENY successfully triggered", policy_reason=outcome.reason)
    else:
        logger.critical("test_failed", reason="MCP was allowed to access restricted memory!")

if __name__ == "__main__":
    run_denial_test()
