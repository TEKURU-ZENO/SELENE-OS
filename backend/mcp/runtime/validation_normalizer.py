"""
SELENE OS — Validation Normalizer
Ensures that execution receipts meet success criteria and assigns a
validation_confidence score for downstream reflection.
"""

from typing import Dict, Any, List
from schemas import ExecutionReceipt, SuccessCriterion
import structlog

logger = structlog.get_logger(__name__)

class ValidationNormalizer:
    
    def validate_receipt(self, receipt: ExecutionReceipt, criteria: List[SuccessCriterion]) -> ExecutionReceipt:
        """
        Validates the receipt against Planner success criteria.
        Injects a validation_confidence score.
        """
        if receipt.status == "failed":
            receipt.validation_confidence = 1.0 # High confidence that it failed
            return receipt
            
        passed_all = True
        ambiguity_score = 0.0
        
        # Mock criteria evaluation
        for criterion in criteria:
            # Example: check if result contains expected key
            if isinstance(receipt.result, dict) and criterion.expected in receipt.result:
                pass
            else:
                passed_all = False
                ambiguity_score += 0.2
                
        if passed_all:
            receipt.validation_confidence = 1.0
        else:
            # Maybe it partially succeeded
            receipt.validation_confidence = max(0.1, 1.0 - ambiguity_score)
            
        logger.info(
            "receipt_validated", 
            execution_id=receipt.execution_id, 
            confidence=receipt.validation_confidence
        )
        
        return receipt

validation_normalizer = ValidationNormalizer()
