"""
SELENE OS — Operational Reflection
Analyzes a single execution context (ExecutionReceipt + ValidationResult).
Outputs an OperationalReflection object.
"""

from schemas import ExecutionReceipt, ValidationResult, OperationalReflection
import structlog

logger = structlog.get_logger(__name__)


class OperationalReflectionEngine:
    def analyze(self, receipt: ExecutionReceipt, validation: ValidationResult) -> OperationalReflection:
        """
        Fast, deterministic analysis of immediate execution results.
        No LLM used here.
        """
        logger.info("operational_reflection_started", execution_id=receipt.execution_id)
        
        tool_failure = None
        if receipt.status == "failed" or receipt.error_details:
            tool_failure = f"{receipt.tool}_failed: {receipt.error_details}"
            
        validation_mismatch = not validation.success

        # If it failed but there's a rollback token or it was a checkpoint retry, 
        # we consider if recovery happened. Simplified for MVP.
        recovery_successful = False 
        
        reflection = OperationalReflection(
            execution_id=receipt.execution_id,
            tool_failure=tool_failure,
            recovery_successful=recovery_successful,
            validation_mismatch=validation_mismatch
        )
        
        return reflection

# Singleton
operational_reflection = OperationalReflectionEngine()
