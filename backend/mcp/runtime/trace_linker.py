"""
SELENE OS — Trace Linker
Ensures perfect observability by linking every MCP execution to the broader
orchestration trace. Critical for MCP Trust Replay.
"""

from schemas import ExecutionReceipt
import structlog

logger = structlog.get_logger(__name__)

class TraceLinker:
    
    def link_trace(self, receipt: ExecutionReceipt, active_trace_id: str, parent_span_id: str) -> ExecutionReceipt:
        """
        Assigns the correct trace context to the receipt before it hits the EventBus.
        """
        receipt.trace_id = active_trace_id
        receipt.span_id = parent_span_id
        logger.debug(
            "trace_linked", 
            execution_id=receipt.execution_id, 
            trace_id=active_trace_id
        )
        return receipt

trace_linker = TraceLinker()
