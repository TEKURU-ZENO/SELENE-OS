"""
SELENE OS — Runtime Execution Store
Decouples Execution State from Graph State.
Tracks DAG nodes, receipts, and execution flow logs, persisted in SQLite.
"""

import asyncio
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import structlog
from schemas import ExecutionReceipt, ExecutionStatus, TaskState
from core.database import get_session
from core.models import ExecutionRecord
from sqlalchemy import select, update

logger = structlog.get_logger(__name__)


class ExecutionStore:
    def __init__(self):
        # Maps graph task_id -> Node/Execution states
        self._store: Dict[str, Dict[str, Any]] = {}
        # Maps execution_id -> ExecutionReceipt dictionary or object
        self._receipts: Dict[str, Any] = {}
        # Maps job_id -> Job Dict (in-memory cache mirror of DB)
        self._jobs: Dict[str, Dict[str, Any]] = {}

    async def load_from_db(self) -> None:
        """Loads all execution records from database to populate the in-memory cache on startup."""
        try:
            async with get_session() as session:
                result = await session.execute(select(ExecutionRecord))
                records = result.scalars().all()
                for r in records:
                    self._jobs[r.job_id] = {
                        "job_id": r.job_id,
                        "session_id": r.session_id or "default_session",
                        "task_id": r.task_id,
                        "capability": r.capability,
                        "mcp_server_id": r.mcp_server_id,
                        "status": r.status,
                        "result": r.result,
                        "receipt_hash": r.receipt_hash,
                        "validation_confidence": r.validation_confidence or 1.0,
                        "hitl_required": r.hitl_required or False,
                        "hitl_decision": r.hitl_decision,
                        "created_at": r.created_at.timestamp() if r.created_at else time.time(),
                        "completed_at": r.completed_at.timestamp() if r.completed_at else None,
                        "params": r.result.get("params", {}) if (isinstance(r.result, dict) and "params" in r.result) else {}
                    }
                    if r.task_id:
                        self.initialize_task(r.task_id)
                        node_status = ExecutionStatus.SUCCESS if r.status == "success" else (ExecutionStatus.FAILED if r.status == "failed" else ExecutionStatus.PENDING)
                        self._store[r.task_id]["nodes"][r.job_id] = {
                            "status": node_status,
                            "receipt_id": r.id
                        }
                        if node_status == ExecutionStatus.SUCCESS and r.job_id not in self._store[r.task_id]["completed_nodes"]:
                            self._store[r.task_id]["completed_nodes"].append(r.job_id)
                        if node_status == ExecutionStatus.FAILED and r.job_id not in self._store[r.task_id]["failed_nodes"]:
                            self._store[r.task_id]["failed_nodes"].append(r.job_id)

            logger.info("execution_store_loaded_from_db", count=len(self._jobs))
        except Exception as e:
            logger.error("execution_store_load_failed", error=str(e))

    def initialize_task(self, task_id: str) -> None:
        if task_id not in self._store:
            self._store[task_id] = {
                "status": "pending",
                "nodes": {},
                "failed_nodes": [],
                "completed_nodes": [],
                "total_duration_ms": 0.0,
                "start_time": time.time()
            }

    def set_node_status(self, task_id: str, node_id: str, status: ExecutionStatus) -> None:
        self.initialize_task(task_id)
        if node_id not in self._store[task_id]["nodes"]:
            self._store[task_id]["nodes"][node_id] = {"status": status, "receipt_id": None}
        else:
            self._store[task_id]["nodes"][node_id]["status"] = status
            
        if status == ExecutionStatus.SUCCESS and node_id not in self._store[task_id]["completed_nodes"]:
            self._store[task_id]["completed_nodes"].append(node_id)
        if status == ExecutionStatus.FAILED and node_id not in self._store[task_id]["failed_nodes"]:
            self._store[task_id]["failed_nodes"].append(node_id)

    def save_receipt(self, task_id: str, node_id: str, receipt: ExecutionReceipt) -> None:
        self.initialize_task(task_id)
        self._receipts[receipt.execution_id] = receipt
        
        if node_id not in self._store[task_id]["nodes"]:
            self._store[task_id]["nodes"][node_id] = {}
            
        self._store[task_id]["nodes"][node_id]["receipt_id"] = receipt.execution_id
        self.set_node_status(task_id, node_id, receipt.status)

    def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(task_id)

    def get_receipt(self, execution_id: str) -> Optional[Any]:
        return self._receipts.get(execution_id)

    def register_job(self, job_id: str, capability: str, mcp_server_id: str, status: str, params: dict, session_id: str = None, task_id: str = None, hitl_required: bool = False):
        """Registers a job synchronously in cache and triggers async DB write."""
        job_data = {
            "job_id": job_id,
            "session_id": session_id or "default_session",
            "task_id": task_id,
            "capability": capability,
            "mcp_server_id": mcp_server_id,
            "status": status,
            "result": None,
            "receipt_hash": None,
            "validation_confidence": 1.0,
            "hitl_required": hitl_required,
            "hitl_decision": None,
            "created_at": time.time(),
            "completed_at": None,
            "params": params
        }
        self._jobs[job_id] = job_data
        
        # Trigger async write to DB
        asyncio.create_task(self._async_insert_job(job_data))
        logger.info("job_registered", job_id=job_id, capability=capability)

    async def _async_insert_job(self, job_data: dict) -> None:
        try:
            async with get_session() as session:
                record = ExecutionRecord(
                    job_id=job_data["job_id"],
                    session_id=job_data["session_id"],
                    task_id=job_data["task_id"],
                    capability=job_data["capability"],
                    mcp_server_id=job_data["mcp_server_id"],
                    status=job_data["status"],
                    result={"params": job_data["params"]},
                    receipt_hash=job_data["receipt_hash"],
                    validation_confidence=job_data["validation_confidence"],
                    hitl_required=job_data["hitl_required"],
                    hitl_decision=job_data["hitl_decision"],
                    completed_at=None
                )
                session.add(record)
            logger.debug("job_inserted_to_db", job_id=job_data["job_id"])
        except Exception as e:
            logger.error("job_db_insert_failed", job_id=job_data["job_id"], error=str(e))

    def record_completion(self, job_id: str, receipt: dict) -> None:
        """Saves a receipt and records completion of a job."""
        if job_id not in self._jobs:
            self._jobs[job_id] = {
                "job_id": job_id,
                "session_id": "default_session",
                "task_id": None,
                "capability": receipt.get("capability", "unknown"),
                "mcp_server_id": "github_mcp_core",
                "status": "pending",
                "result": None,
                "receipt_hash": None,
                "validation_confidence": 1.0,
                "hitl_required": False,
                "hitl_decision": None,
                "created_at": time.time(),
                "completed_at": None,
                "params": {}
            }
            
        job = self._jobs[job_id]
        job["status"] = receipt.get("status", "success")
        job["result"] = receipt.get("result", {})
        job["receipt_hash"] = receipt.get("receipt_hash")
        job["completed_at"] = receipt.get("completed_at") or time.time()
        
        execution_id = receipt.get("execution_id") or f"exec_{uuid.uuid4().hex}"
        self._receipts[execution_id] = receipt
        
        asyncio.create_task(self._async_update_job_completion(job_id, job))
        logger.info("job_completed_recorded", job_id=job_id, status=job["status"])

    async def _async_update_job_completion(self, job_id: str, job_data: dict) -> None:
        try:
            async with get_session() as session:
                completed_dt = datetime.fromtimestamp(job_data["completed_at"], tz=timezone.utc) if job_data["completed_at"] else datetime.now(timezone.utc)
                stmt = (
                    update(ExecutionRecord)
                    .where(ExecutionRecord.job_id == job_id)
                    .values(
                        status=job_data["status"],
                        result=job_data["result"],
                        receipt_hash=job_data["receipt_hash"],
                        completed_at=completed_dt
                    )
                )
                await session.execute(stmt)
            logger.debug("job_completion_updated_in_db", job_id=job_id)
        except Exception as e:
            logger.error("job_db_completion_update_failed", job_id=job_id, error=str(e))

    def get_session_records(self, session_id: str) -> list[dict]:
        """Returns execution records associated with a session."""
        records = []
        for job in self._jobs.values():
            if job.get("session_id") == session_id:
                records.append(job)
        return sorted(records, key=lambda x: x.get("created_at", 0))

    def get_pending_hitl(self) -> list[dict]:
        """Returns pending HITL jobs."""
        pending = []
        for job in self._jobs.values():
            if job.get("status") in ("waiting_hitl", "paused") or (job.get("hitl_required") and not job.get("hitl_decision")):
                pending.append({
                    "job_id": job["job_id"],
                    "capability": job["capability"],
                    "mcp_server_id": job["mcp_server_id"],
                    "risk_level": "HIGH" if job["capability"] in ("execute_code", "plugin_capability") else "MEDIUM",
                    "action_preview": job["params"].get("action_preview") or f"Execute {job['capability']} on {job['mcp_server_id']}",
                    "params": job["params"]
                })
        return pending

    def get_job(self, job_id: str) -> Optional[dict]:
        return self._jobs.get(job_id)

    def record_hitl_decision(self, job_id: str, decision: str, modifications: Optional[dict] = None):
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job["hitl_decision"] = decision
            if decision == "approved":
                job["status"] = "pending"
                if modifications:
                    job["params"].update(modifications)
                from runtime.task_queue import task_queue
                task_queue.set_task_status(job_id, "pending", modifications)
            elif decision == "rejected":
                job["status"] = "failed"
                from runtime.task_queue import task_queue
                task_queue.set_task_status(job_id, "failed")
                
            asyncio.create_task(self._async_update_hitl_decision(job_id, decision, job["params"], job["status"]))
            logger.info("hitl_decision_recorded", job_id=job_id, decision=decision)

    async def _async_update_hitl_decision(self, job_id: str, decision: str, params: dict, status: str) -> None:
        try:
            async with get_session() as session:
                stmt = (
                    update(ExecutionRecord)
                    .where(ExecutionRecord.job_id == job_id)
                    .values(
                        hitl_decision=decision,
                        status=status,
                        result={"params": params}
                    )
                )
                await session.execute(stmt)
            logger.debug("hitl_decision_updated_in_db", job_id=job_id)
        except Exception as e:
            logger.error("hitl_db_decision_update_failed", job_id=job_id, error=str(e))


# Singleton
execution_store = ExecutionStore()

