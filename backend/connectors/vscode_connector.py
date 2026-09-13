"""
SELENE OS — VSCode Context Connector
Polls a local VSCode extension endpoint (HTTP on localhost:6789) to
observe the active workspace context: open files, diagnostics, and active tab.
All signals are abstracted into NativeContextEvents — no raw file content is emitted.
Read-only in alpha.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import httpx
import structlog

from connectors.base_connector import BaseConnector
from schemas import (
    NativeContextEvent,
    ConnectorManifest,
    ContextCategory,
    Capability,
    OrganizationalMemoryTier,
    RiskLevel,
)

logger = structlog.get_logger(__name__)

VSCODE_ENDPOINT = "http://localhost:6789"


class VSCodeConnector(BaseConnector):
    """
    Observes the developer's VSCode workspace via a companion extension
    that exposes a local HTTP API.

    Context signals emitted:
    - "active_file_changed"      (ACTIVE_WINDOW, 30min half-life)
    - "diagnostics_present"      (WORKFLOW_INTENT, 4hr half-life)
    - "test_run_completed"       (WORKFLOW_INTENT, 4hr half-life)
    - "workspace_switched"       (BEHAVIORAL_PATTERN, 2day half-life)

    If the VSCode extension is not running, the connector logs a warning
    and returns an empty event list — it NEVER crashes the main runtime.
    """

    def __init__(self, tenant_id: str, endpoint: str = VSCODE_ENDPOINT):
        manifest = ConnectorManifest(
            connector_id="vscode_connector",
            name="VSCode Context Connector",
            version="1.0.0",
            capabilities=[Capability.READ_DOCUMENT, Capability.FIND_INFORMATION],
            memory_scope=OrganizationalMemoryTier.PERSONAL,
            risk_level=RiskLevel.LOW,
        )
        super().__init__(manifest)
        self._tenant_id = tenant_id
        self._endpoint = endpoint
        self._last_active_file: str | None = None

    async def poll_context(self) -> List[NativeContextEvent]:
        """
        Polls the VSCode extension for current workspace state.
        Returns empty list silently if the extension is offline.
        """
        events: List[NativeContextEvent] = []
        try:
            async with httpx.AsyncClient(base_url=self._endpoint, timeout=5.0) as client:
                # ── Active File ────────────────────────────────────
                try:
                    resp = await client.get("/active-file")
                    if resp.status_code == 200:
                        data = resp.json()
                        file_path = data.get("path", "")
                        language = data.get("language", "unknown")

                        if file_path and file_path != self._last_active_file:
                            self._last_active_file = file_path
                            events.append(NativeContextEvent(
                                tenant_id=self._tenant_id,
                                app_source="vscode",
                                semantic_event="active_file_changed",
                                category=ContextCategory.ACTIVE_WINDOW,
                                payload={
                                    # Only emit the filename, not the full path (privacy)
                                    "filename": file_path.split("/")[-1].split("\\")[-1],
                                    "language": language,
                                    "is_test_file": "test" in file_path.lower() or "spec" in file_path.lower(),
                                },
                                timestamp=datetime.now(timezone.utc),
                            ))
                except Exception:
                    pass

                # ── Diagnostics ────────────────────────────────────
                try:
                    resp = await client.get("/diagnostics")
                    if resp.status_code == 200:
                        data = resp.json()
                        errors = data.get("errors", [])
                        warnings = data.get("warnings", [])

                        if errors:
                            events.append(NativeContextEvent(
                                tenant_id=self._tenant_id,
                                app_source="vscode",
                                semantic_event="diagnostics_present",
                                category=ContextCategory.WORKFLOW_INTENT,
                                payload={
                                    "error_count": len(errors),
                                    "warning_count": len(warnings),
                                    # Emit error messages but not file content
                                    "error_messages": [e.get("message", "")[:100] for e in errors[:3]],
                                },
                                timestamp=datetime.now(timezone.utc),
                            ))
                except Exception:
                    pass

        except httpx.ConnectError:
            logger.debug("vscode_extension_offline", endpoint=self._endpoint)
        except Exception as e:
            logger.warning("vscode_poll_unexpected_error", error=str(e))

        if events:
            logger.info("vscode_context_polled", events_emitted=len(events))
        return events

    async def execute_capability(self, capability_name: str, params: dict):
        """
        VSCode connector is read-only in alpha.
        No write capabilities are implemented.
        """
        raise NotImplementedError(
            "VSCode connector is read-only in alpha. "
            "Write capabilities (e.g., apply_code_fix) will be added in beta."
        )
