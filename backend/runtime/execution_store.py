"""
SELENE OS — Runtime Execution Store
Decouples Execution State from Graph State.
Tracks DAG nodes, receipts, and execution flow logs outside the orchestration graph.
"""

from typing import Dict, Any, List, Optional
import time
import structlog
from schemas import ExecutionReceipt, ExecutionStatus

logger = structlog.get_logger(__name__)


class ExecutionStore:
    def __init__(self):
        # Maps graph task_id -> Node/Execution states
        self._store: Dict[str, Dict[str, Any]] = {}
        # Maps execution_id -> ExecutionReceipt
        self._receipts: Dict[str, ExecutionReceipt] = {}

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

    def get_receipt(self, execution_id: str) -> Optional[ExecutionReceipt]:
        return self._receipts.get(execution_id)

# Singleton
execution_store = ExecutionStore()
