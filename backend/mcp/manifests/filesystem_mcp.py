"""
SELENE OS — Filesystem MCP Manifest
The local filesystem fallback MCP. Activated by the cascading fallback strategy
when primary MCP providers are unavailable. Read-only. Strictly scoped to the
workspace directory.
"""

from mcp.schemas import MCPServerManifest, TrustClassification, TransportType
from schemas import Capability, OrganizationalMemoryTier, RiskLevel

filesystem_mcp_manifest = MCPServerManifest(
    server_id="filesystem_mcp_fallback",
    name="Local Filesystem MCP (Fallback)",
    version="1.0.0",
    transport=TransportType.STDIO,  # Spawns a local process

    # ── Fallback read capabilities only ──
    capabilities=[
        Capability.READ_DOCUMENT,    # Read local files (diffs, configs, logs)
        Capability.FIND_INFORMATION, # Search within local files
    ],

    trust_classification=TrustClassification.RESTRICTED,
    risk_level=RiskLevel.MEDIUM,  # Local filesystem access requires caution

    # ── Memory and Context Bounds ──
    memory_scope=OrganizationalMemoryTier.PERSONAL,
    allowed_contexts=[
        "engineering_context",
        "debugging_workflow",
        "release_workflow",
    ],

    # ── Governance — fallback usage always triggers HITL escalation ──
    requires_hitl=True,  # The Policy Gate escalates when fallback_depth > 1
    supports_replay=True,
    supports_idempotency=True,
    enabled=True,  # Always available as last-resort fallback
)
