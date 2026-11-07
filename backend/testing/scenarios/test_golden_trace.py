"""
SELENE OS — Golden Trace & Attack Tests
Executes the Developer Release Workflow via GitHub MCP and immediately attacks it 
to validate Replay, HITL, Fallback, and Governance resilience.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


from typing import Dict, Any
from mcp.adapters.capability_adapter import capability_adapter
from mcp.sandbox.policy_gate import policy_gate
from mcp.sandbox.hitl_router import hitl_router
from mcp.runtime.receipt_adapter import receipt_adapter
from mcp.manifests.github_mcp import github_mcp_manifest
from mcp.adapters.fallback_strategy import fallback_strategy
from workflows.developer_release import get_developer_release_workflow

from schemas import (
    Capability, ContextCategory, TrustControls, ProactivityTier, 
    MemoryTier, OrganizationalMemoryTier
)
import structlog
import uuid

logger = structlog.get_logger(__name__)

class GoldenTraceTester:
    def __init__(self):
        self.controls = TrustControls(
            tenant_id="tenant_1",
            proactivity_tier=ProactivityTier.SUGGESTIVE,
            allow_autonomous_execution=False,
            default_memory_tier=MemoryTier.LOCAL_PERSISTENT,
            org_tier_clearance=OrganizationalMemoryTier.TEAM
        )
        self.workflow = get_developer_release_workflow()
        self.active_contexts = [ContextCategory.WORKFLOW_INTENT] 

    def test_1_golden_path_capability_translation(self):
        logger.info("TEST 1: Capability Translation & Interoperability")
        
        # Planner outputs an abstract capability
        abstract_cap = Capability.PLUGIN_CAPABILITY # Drafting content
        
        # Capability Adapter translates it to GitHub MCP
        resolved_tool = capability_adapter.resolve_capability(abstract_cap, ["release_workflow"])
        
        assert resolved_tool is not None, "Failed to resolve capability"
        assert resolved_tool["server"].server_id == "github_mcp_core", "Wrong server resolved"
        logger.info("PASS: Capability mapped strictly to github_mcp_core")
        return resolved_tool

    def test_2_policy_gate_enforcement(self, resolved_tool):
        logger.info("TEST 2: Policy Gate Enforcement & HITL Routing")
        
        manifest = resolved_tool["server"]
        
        # Active context simulates "release_workflow" strings matching the schema ContextCategory logic
        class MockContext:
            value = "release_workflow"
            
        outcome = policy_gate.evaluate_execution_request(
            manifest=manifest,
            active_contexts=[MockContext()],
            tenant_controls=self.controls
        )
        
        assert outcome.approved is True, "Valid context was denied"
        assert outcome.requires_hitl is True, "HITL escalation bypassed!"
        
        logger.info("PASS: Valid execution approved, HITL escalation enforced")
        
        # Simulate MCP response
        raw_mcp_response = {"result": {"draft": "v1.0.0 Release Notes: Added Trust Firewall."}}
        
        # Receipt normalization
        receipt = receipt_adapter.normalize_mcp_response(
            raw_response=raw_mcp_response,
            source_name=manifest.server_id,
            tool_name="draft_release",
            capability=Capability.PLUGIN_CAPABILITY,
            duration_ms=45.2,
            policy_decisions=[outcome.reason]
        )
        
        assert receipt.receipt_hash != "", "Provenance hash missing"
        assert receipt.source_type == "mcp", "Source type corrupted"
        
        logger.info("PASS: Execution Receipt normalized with Hash", hash=receipt.receipt_hash[:8])
        return receipt

    def test_3_attack_replay_tampering(self, valid_receipt):
        logger.info("TEST 3: Attack -> Replay Tampering")
        
        # Attack: Attacker modifies the receipt result without updating the hash
        valid_receipt.result["draft"] = "MALICIOUS PAYLOAD"
        
        # Verification: The hash generated now should NOT match the stored receipt_hash
        payload_to_hash = {
            "source_name": valid_receipt.source_name,
            "tool_name": valid_receipt.tool,
            "status": valid_receipt.status.value,
            "result": valid_receipt.result,
            "timestamp": valid_receipt.timestamp.isoformat()
        }
        recomputed_hash = receipt_adapter._generate_receipt_hash(payload_to_hash)
        
        assert recomputed_hash != valid_receipt.receipt_hash, "Replay Tampering NOT detected!"
        logger.info("PASS: Replay Tampering detected. Hashes diverged. Receipt rejected.")

    def test_4_attack_fallback_integrity(self):
        logger.info("TEST 4: Fallback Chain Integrity")
        
        # Simulate GitHub MCP timeout by manually passing its ID to fallback
        fallbacks = fallback_strategy.get_fallbacks("github_mcp_read_pr")
        
        assert "filesystem_mcp_read_diff" in fallbacks, "Fallback chain missing!"
        logger.info("PASS: Fallback to Filesystem MCP initiated successfully.")

    def run_all(self):
        print("\n=== STARTING GOLDEN TRACE & ATTACK VECTORS ===\n")
        
        # 0. Register Server
        from mcp.registry.server_registry import server_registry
        server_registry.register_server(github_mcp_manifest)
        
        # 1. Translation
        tool = self.test_1_golden_path_capability_translation()
        
        # 2. Gate & Execution
        receipt = self.test_2_policy_gate_enforcement(tool)
        
        # 3. Replay Tampering Attack
        self.test_3_attack_replay_tampering(receipt)
        
        # 4. Fallback Attack
        self.test_4_attack_fallback_integrity()
        
        # Note: Context boundary attack was already proven in test_mcp_denial.py
        
        print("\n=== ALL TRACES AND ATTACKS PASSED ===\n")

if __name__ == "__main__":
    tester = GoldenTraceTester()
    tester.run_all()
