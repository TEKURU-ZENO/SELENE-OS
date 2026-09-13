"""
SELENE OS — Notion MCP Manifest
Trust classification and capability bounds for the Notion MCP server.
Read-only in alpha. Write capabilities enabled in beta after governance validation.
"""

from mcp.schemas import MCPServerManifest, TrustClassification, TransportType
from schemas import Capability, OrganizationalMemoryTier, RiskLevel

notion_mcp_manifest = MCPServerManifest(
    server_id="notion_mcp_core",
    name="Notion Integration Server",
    version="1.0.0",
    transport=TransportType.HTTP,

    # ── READ-ONLY in alpha ──
    capabilities=[
        Capability.READ_DOCUMENT,    # Read pages, databases, blocks
        Capability.FIND_INFORMATION, # Search across workspace
    ],

    trust_classification=TrustClassification.TRUSTED,
    risk_level=RiskLevel.LOW,  # Read-only = low risk

    # ── Memory and Context Bounds ──
    memory_scope=OrganizationalMemoryTier.TEAM,
    allowed_contexts=[
        "research_workflow",
        "documentation_context",
        "engineering_context",
    ],

    # ── Governance ──
    requires_hitl=False,  # Reads don't require HITL
    supports_replay=True,
    supports_idempotency=True,
    enabled=False,  # Disabled in alpha — enabled in beta
)
