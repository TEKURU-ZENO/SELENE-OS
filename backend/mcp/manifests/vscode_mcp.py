"""
SELENE OS — VSCode MCP Manifest
Trust classification and capability bounds for the VSCode context MCP server.
Provides workspace context signals (active file, diagnostics, open tabs).
Read-only in alpha.
"""

from mcp.schemas import MCPServerManifest, TrustClassification, TransportType
from schemas import Capability, OrganizationalMemoryTier, RiskLevel

vscode_mcp_manifest = MCPServerManifest(
    server_id="vscode_mcp_core",
    name="VSCode Context Server",
    version="1.0.0",
    transport=TransportType.HTTP,  # VSCode extension exposes a local HTTP endpoint

    # ── Context observation only ──
    capabilities=[
        Capability.READ_DOCUMENT,    # Read active file content, workspace structure
        Capability.FIND_INFORMATION, # Search symbols, diagnostics, test results
    ],

    trust_classification=TrustClassification.TRUSTED,
    risk_level=RiskLevel.LOW,

    # ── Memory and Context Bounds ──
    memory_scope=OrganizationalMemoryTier.PERSONAL,  # Workspace is personal context
    allowed_contexts=[
        "engineering_context",
        "debugging_workflow",
        "release_workflow",
        "development_session",
    ],

    # ── Governance ──
    requires_hitl=False,  # Read-only context signals don't require approval
    supports_replay=True,
    supports_idempotency=True,
    enabled=True,  # Active in alpha
)
