"""
SELENE OS — Alpha Hardening & Health Integration Tests
Verifies health check endpoints, SSRF blocking, external mutation locks, and shell/bash block.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


import asyncio
from config.settings import settings
from mcp.sandbox.policy_gate import policy_gate
from mcp.sandbox.context_validator import context_validator
from mcp.schemas import MCPServerManifest, TrustClassification, TransportType
from schemas import Capability, ContextCategory, TrustControls, ProactivityTier, MemoryTier, OrganizationalMemoryTier
from agents.browser_agent import browser_agent
from agents.web_agent import web_agent
import structlog

logger = structlog.get_logger(__name__)

def test_ssrf_protection():
    # 1. Test SSRF Protection
    logger.info("TEST 1: SSRF Protection Validator")
    assert not browser_agent._is_ssrf_safe("http://localhost:8000"), "SSRF: localhost was not blocked!"
    assert not browser_agent._is_ssrf_safe("http://127.0.0.1"), "SSRF: loopback IPv4 was not blocked!"
    assert not browser_agent._is_ssrf_safe("http://[::1]/some-endpoint"), "SSRF: loopback IPv6 was not blocked!"
    assert not browser_agent._is_ssrf_safe("http://169.254.169.254/latest/meta-data"), "SSRF: link-local IP was not blocked!"
    assert not browser_agent._is_ssrf_safe("http://192.168.1.10"), "SSRF: private Class C IP was not blocked!"
    assert not browser_agent._is_ssrf_safe("http://10.0.0.1"), "SSRF: private Class A IP was not blocked!"
    assert browser_agent._is_ssrf_safe("https://github.com"), "SSRF: public hostname was blocked!"
    assert browser_agent._is_ssrf_safe("https://www.google.com/search?q=selene"), "SSRF: public URL was blocked!"

    assert not web_agent._is_ssrf_safe("http://localhost"), "SSRF: web_agent allowed localhost!"
    assert web_agent._is_ssrf_safe("https://example.com"), "SSRF: web_agent blocked public domain!"
    logger.info("PASS: SSRF Protection blocks loopback, link-local, and private IP spaces")


def test_policy_gate_mutation_hitl():
    # 2. Test FORCE_HITL_ALL_EXTERNAL_MUTATIONS Override in PolicyGate
    logger.info("TEST 2: PolicyGate Mutation HITL Lock")

    prev_flag = settings.FORCE_HITL_ALL_EXTERNAL_MUTATIONS
    settings.FORCE_HITL_ALL_EXTERNAL_MUTATIONS = True
    try:
        controls = TrustControls(
            tenant_id="tenant_1",
            proactivity_tier=ProactivityTier.SUGGESTIVE,
            allow_autonomous_execution=True,
            default_memory_tier=MemoryTier.LOCAL_PERSISTENT,
            org_tier_clearance=OrganizationalMemoryTier.TEAM
        )

        class MockContext:
            value = "engineering_context"

        read_only_manifest = MCPServerManifest(
            server_id="read_only_server",
            name="Read Only Server",
            version="1.0",
            transport=TransportType.STDIO,
            capabilities=[Capability.READ_DOCUMENT],
            trust_classification=TrustClassification.TRUSTED,
            risk_level="low",
            memory_scope=OrganizationalMemoryTier.TEAM,
            allowed_contexts=["engineering_context"],
            requires_hitl=False
        )

        mutation_manifest = MCPServerManifest(
            server_id="mutation_server",
            name="Mutation Server",
            version="1.0",
            transport=TransportType.STDIO,
            capabilities=[Capability.MODIFY_SYSTEM],
            trust_classification=TrustClassification.TRUSTED,
            risk_level="medium",
            memory_scope=OrganizationalMemoryTier.TEAM,
            allowed_contexts=["engineering_context"],
            requires_hitl=False
        )

        outcome_read = policy_gate.evaluate_execution_request(
            manifest=read_only_manifest,
            active_contexts=[MockContext()],
            tenant_controls=controls
        )
        assert outcome_read.approved is True, "Read-only server request was denied"
        assert outcome_read.requires_hitl is False, "Read-only capability was incorrectly forced into HITL"

        outcome_mut = policy_gate.evaluate_execution_request(
            manifest=mutation_manifest,
            active_contexts=[MockContext()],
            tenant_controls=controls
        )
        assert outcome_mut.approved is True, "Mutation server request was denied"
        assert outcome_mut.requires_hitl is True, "Mutation capability did not trigger forced HITL"
        logger.info("PASS: FORCE_HITL_ALL_EXTERNAL_MUTATIONS correctly intercepts mutations and exempts reads")
    finally:
        settings.FORCE_HITL_ALL_EXTERNAL_MUTATIONS = prev_flag


def test_context_validator_blocks_shell_and_code():
    # 3. Test Shell/Bash and EXECUTE_CODE blocking in ContextValidator
    logger.info("TEST 3: ContextValidator Shell & Code Execution Block")

    class MockContext:
        value = "engineering_context"

    ctx = MockContext()

    shell_manifest = MCPServerManifest(
        server_id="local_shell_server",
        name="Local Shell",
        version="1.0",
        transport=TransportType.STDIO,
        capabilities=[Capability.READ_DOCUMENT],
        trust_classification=TrustClassification.TRUSTED,
        risk_level="high",
        memory_scope=OrganizationalMemoryTier.TEAM,
        allowed_contexts=["engineering_context"],
        requires_hitl=False
    )

    code_manifest = MCPServerManifest(
        server_id="generic_runner",
        name="Generic Code Runner",
        version="1.0",
        transport=TransportType.STDIO,
        capabilities=[Capability.EXECUTE_CODE],
        trust_classification=TrustClassification.TRUSTED,
        risk_level="high",
        memory_scope=OrganizationalMemoryTier.TEAM,
        allowed_contexts=["engineering_context"],
        requires_hitl=False
    )

    assert not context_validator.validate_access(ctx, shell_manifest), "ContextValidator allowed a shell server!"
    assert not context_validator.validate_access(ctx, code_manifest), "ContextValidator allowed EXECUTE_CODE capability!"
    logger.info("PASS: ContextValidator blocks shell server name and EXECUTE_CODE capability")


def run_hardening_tests():
    logger.info("STARTING HARDENING INTEGRATION TESTS")
    test_ssrf_protection()
    test_policy_gate_mutation_hitl()
    test_context_validator_blocks_shell_and_code()
    logger.info("ALL HARDENING INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_hardening_tests()
