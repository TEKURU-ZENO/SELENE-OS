"""
SELENE OS — Capability Execution Worker
Handles READ_DOCUMENT, FIND_INFORMATION, EXECUTE_CODE, and NOTIFY_USER capabilities.
Claims tasks from the Redis Stream, routes them through MCP transports,
and pushes ExecutionReceipts back to the orchestrator.
"""

import asyncio
import hashlib
import json
import time
import uuid
from typing import Any, Dict

import structlog

from mcp.registry.server_registry import server_registry
from mcp.transport.base_transport import get_transport
from runtime.task_queue import task_queue
from runtime.execution_store import execution_store
from runtime.workers.base_worker import BaseExecutionWorker
from schemas import Capability, ExecutionStatus

logger = structlog.get_logger(__name__)


class CapabilityWorker(BaseExecutionWorker):
    """
    Concrete worker for standard read/execute capabilities.
    Resolves the MCP server from the registry, connects via the appropriate
    transport, executes the capability, and emits an ExecutionReceipt.
    """

    SUPPORTED = [
        Capability.READ_DOCUMENT,
        Capability.FIND_INFORMATION,
        Capability.EXECUTE_CODE,
        Capability.NOTIFY_USER,
    ]

    def __init__(self):
        super().__init__(supported_capabilities=self.SUPPORTED)
        # Active transport pool: server_id → (transport, connected_flag)
        self._transports: Dict[str, Any] = {}

    async def start(self):
        self._is_running = True
        logger.info(
            "capability_worker_started",
            worker_id=self.worker_id,
            capabilities=[c.value for c in self.SUPPORTED],
        )

        while self._is_running:
            task = task_queue.claim_task(
                "default_tenant", self.worker_id, [c.value for c in self.SUPPORTED]
            )
            if task:
                await self._execute_with_heartbeat(task)
            else:
                await asyncio.sleep(1.0)

    async def stop(self):
        self._is_running = False
        # Disconnect all open transports
        for server_id, transport in self._transports.items():
            try:
                await transport.disconnect()
            except Exception as e:
                logger.warning("transport_disconnect_error", server_id=server_id, error=str(e))
        self._transports.clear()
        logger.info("capability_worker_stopped", worker_id=self.worker_id)

    async def _execute_with_heartbeat(self, task: dict):
        job_id = task["job_id"]
        node = task["node"]
        capability = node.get("capability")
        server_id = node.get("mcp_server_id", "github_mcp_core")

        async def heartbeat_loop():
            while True:
                task_queue.heartbeat(job_id)
                await asyncio.sleep(20)

        hb_task = asyncio.create_task(heartbeat_loop())

        try:
            logger.info("capability_executing", job_id=job_id, capability=capability, server=server_id)

            result = await self._route_to_mcp(server_id, capability, node.get("params", {}))

            receipt = self._build_receipt(job_id, capability, result, ExecutionStatus.SUCCESS)
            execution_store.record_completion(job_id, receipt)

            logger.info("capability_completed", job_id=job_id, server=server_id)

        except TimeoutError as e:
            logger.warning("capability_timeout", job_id=job_id, error=str(e))
            receipt = self._build_receipt(job_id, capability, {"error": str(e)}, ExecutionStatus.FAILED)
            execution_store.record_completion(job_id, receipt)

        except Exception as e:
            logger.error("capability_failed", job_id=job_id, error=str(e))
            receipt = self._build_receipt(job_id, capability, {"error": str(e)}, ExecutionStatus.FAILED)
            execution_store.record_completion(job_id, receipt)

        finally:
            hb_task.cancel()

    async def _route_to_mcp(self, server_id: str, capability: str, params: dict) -> dict:
        """Resolves the transport, connects if needed, and calls the MCP tool."""
        manifest = server_registry.get_server(server_id)
        if not manifest:
            raise ValueError(f"No registered MCP server for server_id='{server_id}'")

        # Get or create transport
        if server_id not in self._transports:
            transport_kwargs = self._build_transport_kwargs(manifest)
            transport = get_transport(manifest.transport, **transport_kwargs)
            connected = await transport.connect()
            if not connected:
                raise ConnectionError(f"Failed to connect to MCP server '{server_id}'")
            self._transports[server_id] = transport

        transport = self._transports[server_id]
        tool_method = self._capability_to_tool(capability, manifest)
        return await transport.send_request(tool_method, params)

    def _build_transport_kwargs(self, manifest) -> dict:
        """Constructs transport constructor kwargs from the manifest."""
        from mcp.schemas import TransportType
        if manifest.transport == TransportType.STDIO:
            # Default: use the MCP CLI for the server
            commands = {
                "github_mcp_core": ["npx", "-y", "@modelcontextprotocol/server-github"],
                "filesystem_mcp_fallback": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."],
            }
            return {"command": commands.get(manifest.server_id, ["echo", "mock"])}
        elif manifest.transport == TransportType.HTTP:
            ports = {
                "vscode_mcp_core": "http://localhost:6789",
                "slack_mcp_core": "http://localhost:6790",
                "notion_mcp_core": "http://localhost:6791",
            }
            return {"base_url": ports.get(manifest.server_id, "http://localhost:9000")}
        return {}

    def _capability_to_tool(self, capability: str, manifest) -> str:
        """Maps a SELENE abstract capability to the MCP server's concrete tool name."""
        capability_map = {
            Capability.READ_DOCUMENT.value:    "tools/read_file",
            Capability.FIND_INFORMATION.value: "tools/search",
            Capability.EXECUTE_CODE.value:     "tools/run_command",
            Capability.NOTIFY_USER.value:      "tools/send_message",
            Capability.PLUGIN_CAPABILITY.value: "tools/plugin_action",
        }
        return capability_map.get(capability, "tools/unknown")

    def _build_receipt(self, job_id: str, capability: str, result: dict, status: ExecutionStatus) -> dict:
        """Creates a cryptographically hashed ExecutionReceipt."""
        payload = json.dumps({"job_id": job_id, "capability": capability, "result": result}, sort_keys=True)
        receipt_hash = hashlib.sha256(payload.encode()).hexdigest()[:12]
        return {
            "execution_id": f"exec_{uuid.uuid4().hex}",
            "job_id": job_id,
            "capability": capability,
            "status": status.value,
            "result": result,
            "receipt_hash": receipt_hash,
            "completed_at": time.time(),
        }
