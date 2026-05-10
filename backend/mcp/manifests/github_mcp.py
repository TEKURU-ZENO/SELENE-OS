"""
SELENE OS — GitHub MCP Manifest
The strict capability bounds and trust classification for the GitHub MCP server.
"""

from mcp.schemas import (
    MCPServerManifest, TrustClassification, TransportType
)
from schemas import Capability, OrganizationalMemoryTier, RiskLevel

github_mcp_manifest = MCPServerManifest(
    server_id="github_mcp_core",
    name="GitHub Integration Server",
    version="1.0.0",
    transport=TransportType.STDIO,
    
    # ── Strict Capability Bounds ──
    capabilities=[
        Capability.READ_DOCUMENT,
        Capability.FIND_INFORMATION,
        Capability.PLUGIN_CAPABILITY # Maps to DRAFT_CONTENT
    ],
    
    trust_classification=TrustClassification.TRUSTED,
    risk_level=RiskLevel.MEDIUM,
    
    # ── Memory and Context Bounds ──
    memory_scope=OrganizationalMemoryTier.TEAM,
    allowed_contexts=[
        "release_workflow",
        "engineering_context"
    ],
    
    # ── Governance ──
    requires_hitl=True,  # All actions must be approved via HITL Router
    supports_replay=True,
    supports_idempotency=True,
    enabled=True
)
