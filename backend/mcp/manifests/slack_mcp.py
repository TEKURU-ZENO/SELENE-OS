"""
SELENE OS — Slack MCP Manifest
Trust classification and capability bounds for the Slack MCP server.
Restricted in alpha — all message sends require HITL approval.
"""

from mcp.schemas import MCPServerManifest, TrustClassification, TransportType
from schemas import Capability, OrganizationalMemoryTier, RiskLevel

slack_mcp_manifest = MCPServerManifest(
    server_id="slack_mcp_core",
    name="Slack Integration Server",
    version="1.0.0",
    transport=TransportType.HTTP,

    # ── Strict Capability Bounds (beta only) ──
    capabilities=[
        Capability.NOTIFY_USER,      # Send DMs / channel messages
        Capability.PLUGIN_CAPABILITY,  # Draft formatted messages
    ],

    trust_classification=TrustClassification.RESTRICTED,
    risk_level=RiskLevel.HIGH,  # User-facing mutations require extreme caution

    # ── Memory and Context Bounds ──
    memory_scope=OrganizationalMemoryTier.TEAM,
    allowed_contexts=[
        "release_workflow",
        "engineering_context",
        "team_communication",
    ],

    # ── Governance — ALL sends require human approval ──
    requires_hitl=True,
    supports_replay=True,
    supports_idempotency=False,  # Slack doesn't support idempotent delivery natively
    enabled=False,  # Disabled in alpha — enabled in beta
)
