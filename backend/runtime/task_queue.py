"""
SELENE OS — Runtime Distributed Queue (Mocked Redis Streams)
Represents the durable event history and task queue separating Orchestration from Execution.
"""

from typing import Dict, Any, Optional
from schemas import TaskState, PlanNode
import uuid
import time
import structlog

logger = structlog.get_logger(__name__)


class DistributedTaskQueue:
    def __init__(self):
        # Mocking Redis Stream behavior
        self._streams = {}
        self._leases: Dict[str, Dict[str, Any]] = {}

    def enqueue_task(self, node: PlanNode, tenant_id: str, trace_id: str) -> str:
        """Pushes a capability execution task to the stream."""
        job_id = str(uuid.uuid4())
        
        # Enforce Idempotency
        if self._is_idempotency_key_used(node.idempotency_key):
            logger.warning("idempotent_execution_detected", key=node.idempotency_key)
            return "ALREADY_ENQUEUED"
            
        status = TaskState.WAITING_HITL.value if node.requires_confirmation else TaskState.PENDING.value
        payload = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "trace_id": trace_id,
            "node": node.model_dump(),
            "status": status,
            "enqueued_at": time.time()
        }
        
        if tenant_id not in self._streams:
            self._streams[tenant_id] = []
            
        self._streams[tenant_id].append(payload)
        logger.info("task_enqueued", job_id=job_id, capability=node.capability)

        # Register in the execution store for persistence and tracking
        from runtime.execution_store import execution_store
        execution_store.register_job(
            job_id=job_id,
            capability=node.capability.value if hasattr(node.capability, "value") else str(node.capability),
            mcp_server_id=node.params.get("mcp_server_id") or node.affinity_group or "github_mcp_core",
            status=status,
            params=node.params,
            session_id=None,
            task_id=node.id,
            hitl_required=node.requires_confirmation
        )

        return job_id

    def claim_task(self, tenant_id: str, worker_id: str, capability_group: str) -> Optional[Dict[str, Any]]:
        """Worker claims a task and acquires a capability-scoped lease."""
        stream = self._streams.get(tenant_id, [])
        for task in stream:
            if task["status"] == TaskState.PENDING.value:
                # Check capability match (mock logic)
                if task["node"]["capability"] in capability_group:
                    task["status"] = TaskState.LEASED.value
                    
                    # Grant capability-scoped lease
                    lease = {
                        "job_id": task["job_id"],
                        "worker_id": worker_id,
                        "expires_at": time.time() + 60, # 60s lease
                        "last_heartbeat": time.time()
                    }
                    self._leases[task["job_id"]] = lease
                    logger.info("task_leased", job_id=task["job_id"], worker_id=worker_id)
                    return task
        return None
        
    def heartbeat(self, job_id: str) -> bool:
        if job_id in self._leases:
            self._leases[job_id]["last_heartbeat"] = time.time()
            # Auto-extend lease expiration
            self._leases[job_id]["expires_at"] = time.time() + 60
            return True
        return False
        
    def get_dead_leases(self) -> list:
        now = time.time()
        dead = []
        for job_id, lease in self._leases.items():
            if now > lease["expires_at"]:
                dead.append(job_id)
        return dead
        
    def revoke_lease(self, job_id: str):
        if job_id in self._leases:
            del self._leases[job_id]
            logger.warning("lease_revoked", job_id=job_id)

    def set_task_status(self, job_id: str, status: str, params: dict = None) -> bool:
        """Updates status and parameters of a task in the stream (useful for HITL approvals)."""
        for tenant_id, stream in self._streams.items():
            for task in stream:
                if task["job_id"] == job_id:
                    task["status"] = status
                    if params:
                        task["node"]["params"].update(params)
                    logger.info("task_status_updated", job_id=job_id, status=status)
                    return True
        return False

    def _is_idempotency_key_used(self, key: str) -> bool:
        # Mock check
        return False

# Singleton Mock
task_queue = DistributedTaskQueue()

