"""
SELENE OS — Context Resolution Layer
Merges disparate connector signals into cohesive workflow inferences.
"""

from typing import List
from schemas import NativeContextEvent, ContextCategory
from native.context_runtime import context_runtime
import structlog

logger = structlog.get_logger(__name__)


class ContextResolutionLayer:
    
    def resolve_current_workflow(self, tenant_id: str) -> str:
        """
        Analyzes the active, un-decayed context signals and attempts to infer
        a unified cross-application workflow.
        """
        events = context_runtime.get_valid_context(tenant_id)
        
        apps_active = {e.app_source for e in events}
        semantics = [e.semantic_event for e in events]
        
        # Example Workflow Inference Logic
        if "vscode" in apps_active and "github" in apps_active:
            if any("commit" in s or "pr" in s for s in semantics):
                logger.info("workflow_resolved", workflow="feature_delivery_workflow")
                return "feature_delivery_workflow"
                
        if "slack" in apps_active and "notion" in apps_active:
            logger.info("workflow_resolved", workflow="documentation_collaboration")
            return "documentation_collaboration"
            
        return "ambient_unfocused"

# Singleton
context_resolution = ContextResolutionLayer()
