"""
SELENE OS — Execution Receipt Adapter
The primary cognitive safety membrane. Intercepts raw MCP outputs and
translates them into standard, hash-verified ExecutionReceipts.
"""

from typing import Dict, Any, Optional
import hashlib
import json
from datetime import datetime
import uuid

from schemas import ExecutionReceipt, TaskState, Capability

class ReceiptAdapter:
    
    def _generate_receipt_hash(self, payload: Dict[str, Any]) -> str:
        """Creates a tamper-evident hash for the execution provenance."""
        # Ensure consistent ordering for JSON hashing
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def normalize_mcp_response(
        self, 
        raw_response: Dict[str, Any], 
        source_name: str, 
        tool_name: str,
        capability: Capability,
        duration_ms: float,
        parent_hash: Optional[str] = None,
        policy_decisions: list[str] = None
    ) -> ExecutionReceipt:
        
        # In a real scenario, map raw_response status to TaskState
        status = TaskState.COMPLETED if not raw_response.get("error") else TaskState.FAILED
        
        # Build the payload to hash
        payload_to_hash = {
            "source_name": source_name,
            "tool_name": tool_name,
            "status": status.value,
            "result": raw_response.get("result", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        receipt_hash = self._generate_receipt_hash(payload_to_hash)

        receipt = ExecutionReceipt(
            execution_id=str(uuid.uuid4()),
            source_type="mcp",
            source_name=source_name,
            tool=tool_name,
            capability=capability,
            status=status,
            duration_ms=duration_ms,
            receipt_hash=receipt_hash,
            parent_receipt_hash=parent_hash,
            result=raw_response.get("result", {}),
            result_summary={"raw_summary": "Extracted from MCP response"},
            policy_decisions=policy_decisions or [],
            error_details=raw_response.get("error")
        )
        
        return receipt

receipt_adapter = ReceiptAdapter()
