"""
SELENE OS — MCP Server Registry
The interoperability control plane. It registers servers and validates manifests,
but explicitly DOES NOT hold memory or route cognition.
"""

from typing import Dict, List, Optional
from mcp.schemas import MCPServerManifest, TrustClassification
import structlog

logger = structlog.get_logger(__name__)


class MCPServerRegistry:
    def __init__(self):
        self._servers: Dict[str, MCPServerManifest] = {}

    def register_server(self, manifest: MCPServerManifest) -> bool:
        """Validates and registers an MCP server."""
        if manifest.trust_classification == TrustClassification.BLOCKED:
            logger.warning("mcp_server_blocked", server_id=manifest.server_id)
            return False

        # Basic validation
        if not manifest.enabled:
            logger.info("mcp_server_disabled", server_id=manifest.server_id)
            return False

        self._servers[manifest.server_id] = manifest
        logger.info("mcp_server_registered", server_id=manifest.server_id, risk_level=manifest.risk_level.value)
        return True

    def get_server(self, server_id: str) -> Optional[MCPServerManifest]:
        return self._servers.get(server_id)

    def list_servers(self) -> List[MCPServerManifest]:
        return list(self._servers.values())

    def auto_register_defaults(self) -> None:
        """
        Loads and registers all built-in MCP server manifests.
        Called once on application startup before any routing occurs.
        Only manifests with enabled=True are registered.
        """
        from mcp.manifests.github_mcp import github_mcp_manifest
        from mcp.manifests.vscode_mcp import vscode_mcp_manifest
        from mcp.manifests.filesystem_mcp import filesystem_mcp_manifest
        from mcp.manifests.slack_mcp import slack_mcp_manifest
        from mcp.manifests.notion_mcp import notion_mcp_manifest

        manifests = [
            github_mcp_manifest,
            vscode_mcp_manifest,
            filesystem_mcp_manifest,
            slack_mcp_manifest,   # disabled in alpha
            notion_mcp_manifest,  # disabled in alpha
        ]

        registered = 0
        for manifest in manifests:
            if self.register_server(manifest):
                registered += 1

        logger.info(
            "mcp_auto_registration_complete",
            registered=registered,
            total=len(manifests),
        )


# Singleton instance
server_registry = MCPServerRegistry()

