"""
SELENE OS — Connector Registry
Manages all active connector instances and runs the background polling loop.
Emitted NativeContextEvents are routed to the NativeContextRuntime.
"""

import asyncio
from typing import List, Dict, Any
import structlog

from connectors.base_connector import BaseConnector
from native.context_runtime import context_runtime

logger = structlog.get_logger(__name__)

# Polling interval in seconds — conservative for alpha
POLL_INTERVAL_SECONDS = 30


class ConnectorRegistry:
    """
    Owns all active connector instances and runs the background polling loop.
    
    On each poll cycle:
    1. Each connector's poll_context() is called concurrently
    2. Emitted NativeContextEvents are ingested by the NativeContextRuntime
    3. Errors in individual connectors don't crash the overall loop
    """

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._poll_task: asyncio.Task | None = None
        self._is_running = False
        self._last_poll_status: Dict[str, Any] = {}

    def register(self, connector: BaseConnector) -> None:
        """Registers a connector to be included in the poll loop."""
        connector_id = connector.manifest.connector_id
        self._connectors[connector_id] = connector
        logger.info("connector_registered", connector_id=connector_id)

    def unregister(self, connector_id: str) -> None:
        self._connectors.pop(connector_id, None)
        logger.info("connector_unregistered", connector_id=connector_id)

    async def start_polling(self) -> None:
        """
        Starts the background polling loop.
        Called from FastAPI startup_event after connectors are registered.
        """
        if self._is_running:
            return
        self._is_running = True
        self._poll_task = asyncio.create_task(self._poll_loop(), name="connector-poll-loop")
        logger.info(
            "connector_polling_started",
            connectors=list(self._connectors.keys()),
            interval_seconds=POLL_INTERVAL_SECONDS,
        )

    async def stop_polling(self) -> None:
        """Cancels the polling loop gracefully."""
        self._is_running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("connector_polling_stopped")

    def status(self) -> dict:
        """Returns the current registry status for the health endpoint."""
        return {
            "running": self._is_running,
            "connectors": list(self._connectors.keys()),
            "last_poll_status": self._last_poll_status,
        }

    # ── Internal polling ─────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Background task: polls all connectors every POLL_INTERVAL_SECONDS."""
        while self._is_running:
            await self._run_poll_cycle()
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _run_poll_cycle(self) -> None:
        """Runs one poll cycle across all registered connectors concurrently."""
        if not self._connectors:
            return

        tasks = {
            connector_id: asyncio.create_task(
                self._poll_single(connector_id, connector),
                name=f"poll-{connector_id}",
            )
            for connector_id, connector in self._connectors.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for connector_id, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                self._last_poll_status[connector_id] = {"status": "error", "error": str(result)}
            else:
                self._last_poll_status[connector_id] = {"status": "ok", "events": result}

    async def _poll_single(self, connector_id: str, connector: BaseConnector) -> int:
        """Polls a single connector and ingests its events. Returns event count."""
        try:
            events = await connector.poll_context()
            for event in events:
                context_runtime.ingest_event(event)
            return len(events)
        except Exception as e:
            logger.warning("connector_poll_error", connector_id=connector_id, error=str(e))
            raise


def _build_default_connectors() -> List[BaseConnector]:
    """
    Instantiates the default set of connectors based on environment config.
    Connectors that lack required credentials are skipped with a warning.
    """
    from config.settings import settings
    import os

    connectors = []

    # ── GitHub Connector ─────────────────────────────────────────
    github_token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
    github_repo = os.getenv("GITHUB_REPO")  # e.g., "myorg/myrepo"

    if github_token and github_repo:
        from connectors.github_connector import GitHubConnector
        connectors.append(GitHubConnector(
            github_token=github_token,
            repo=github_repo,
            tenant_id="default",
        ))
        logger.info("github_connector_configured", repo=github_repo)
    else:
        logger.warning(
            "github_connector_skipped",
            hint="Set GITHUB_TOKEN and GITHUB_REPO environment variables to enable.",
        )

    # ── VSCode Connector ─────────────────────────────────────────
    from connectors.vscode_connector import VSCodeConnector
    connectors.append(VSCodeConnector(tenant_id="default"))
    # VSCode connector degrades gracefully if extension isn't running

    return connectors


# Singleton
connector_registry = ConnectorRegistry()
