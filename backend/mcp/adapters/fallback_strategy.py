"""
SELENE OS — Capability Fallback Strategy
Defines resilient interoperability. If a primary capability provider fails,
smoothly routes to an alternative rather than collapsing the workflow.
"""

from typing import List, Optional
import structlog

logger = structlog.get_logger(__name__)

class FallbackStrategy:
    def __init__(self):
        # Maps a primary tool_id to a list of fallback tool_ids
        self._fallback_chains = {
            "github_mcp_read_pr": ["filesystem_mcp_read_diff", "web_mcp_fetch"],
            "slack_mcp_send": ["email_mcp_send", "notification_daemon"]
        }

    def get_fallbacks(self, failed_tool_id: str) -> List[str]:
        return self._fallback_chains.get(failed_tool_id, [])

    def register_fallback(self, primary: str, fallback: str):
        if primary not in self._fallback_chains:
            self._fallback_chains[primary] = []
        self._fallback_chains[primary].append(fallback)
        logger.info("fallback_registered", primary=primary, fallback=fallback)

fallback_strategy = FallbackStrategy()
