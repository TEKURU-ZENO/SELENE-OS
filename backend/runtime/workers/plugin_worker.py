"""
SELENE OS — Plugin Execution Worker
Handles PLUGIN_CAPABILITY tasks. Routes through the PluginSandbox with strict
OrganizationalMemoryTier enforcement before any plugin handler is invoked.
"""

import asyncio
import hashlib
import json
import time
import uuid

import structlog

from governance.plugin_sandbox import plugin_sandbox
from runtime.task_queue import task_queue
from runtime.execution_store import execution_store
from runtime.workers.base_worker import BaseExecutionWorker
from schemas import Capability, ExecutionStatus, OrganizationalMemoryTier

logger = structlog.get_logger(__name__)


class PluginWorker(BaseExecutionWorker):
    """
    Dedicated worker for PLUGIN_CAPABILITY tasks.
    All execution is sandboxed — no direct MCP transport calls are made here.
    Instead, the PluginSandbox is responsible for enforcing memory tier
    isolation and routing to the registered plugin handler.
    """

    SUPPORTED = [Capability.PLUGIN_CAPABILITY]

    def __init__(self):
        super().__init__(supported_capabilities=self.SUPPORTED)

    async def start(self):
        self._is_running = True
        logger.info("plugin_worker_started", worker_id=self.worker_id)

        while self._is_running:
            task = task_queue.claim_task(
                "default_tenant", self.worker_id, [Capability.PLUGIN_CAPABILITY.value]
            )
            if task:
                await self._execute_with_heartbeat(task)
            else:
                await asyncio.sleep(1.0)

    async def stop(self):
        self._is_running = False
        logger.info("plugin_worker_stopped", worker_id=self.worker_id)

    async def _execute_with_heartbeat(self, task: dict):
        job_id = task["job_id"]
        node = task["node"]
        plugin_id = node.get("plugin_id", "unknown_plugin")
        capability = node.get("capability", Capability.PLUGIN_CAPABILITY.value)
        params = node.get("params", {})

        # Determine memory tier from node context (default to PERSONAL for safety)
        tier_str = node.get("memory_tier", OrganizationalMemoryTier.PERSONAL.value)
        try:
            context_tier = OrganizationalMemoryTier(tier_str)
        except ValueError:
            context_tier = OrganizationalMemoryTier.PERSONAL

        async def heartbeat_loop():
            while True:
                task_queue.heartbeat(job_id)
                await asyncio.sleep(20)

        hb_task = asyncio.create_task(heartbeat_loop())

        try:
            logger.info(
                "plugin_executing",
                job_id=job_id,
                plugin_id=plugin_id,
                capability=capability,
                tier=context_tier.value,
            )

            sandbox_result = await plugin_sandbox.execute(
                plugin_id=plugin_id,
                capability=capability,
                params=params,
                context_tier=context_tier,
            )

            receipt = self._build_receipt(job_id, capability, sandbox_result, ExecutionStatus.SUCCESS)
            execution_store.record_completion(job_id, receipt)
            logger.info("plugin_completed", job_id=job_id, plugin_id=plugin_id)

        except PermissionError as e:
            logger.error("plugin_permission_denied", job_id=job_id, error=str(e))
            receipt = self._build_receipt(
                job_id, capability, {"error": "PERMISSION_DENIED", "detail": str(e)}, ExecutionStatus.DENIED
            )
            execution_store.record_completion(job_id, receipt)

        except Exception as e:
            logger.error("plugin_failed", job_id=job_id, error=str(e))
            receipt = self._build_receipt(
                job_id, capability, {"error": str(e)}, ExecutionStatus.FAILED
            )
            execution_store.record_completion(job_id, receipt)

        finally:
            hb_task.cancel()

    def _build_receipt(self, job_id: str, capability: str, result: dict, status: ExecutionStatus) -> dict:
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
