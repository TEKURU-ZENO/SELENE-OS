"""
SELENE OS — Graph State Definition
Minimal TypedDict for LangGraph. PURELY COGNITIVE.
References large execution/memory states rather than storing them.
"""

from typing import TypedDict, Dict, Any, Optional, List

class SeleneState(TypedDict):
    """
    State representing the current cognitive snapshot of the orchestrator.
    """
    task_id: str
    session_id: str

    user_query: str

    intent: Dict[str, Any]
    context_bundle_ref: str  # ID or hash pointing to MemoryManager/RuntimeStore

    plan_ref: str # ID pointing to ExecutionStore plan
    current_node_id: Optional[str] # The DAG node currently being evaluated

    critic_verdict: Optional[Dict[str, Any]]
    repair_count: int
    repair_context: Optional[Dict[str, Any]]
    resolved_tools: Dict[str, str]
    validation_result: Optional[Dict[str, Any]]
    pending_procedural_updates: List[Dict[str, Any]]

    reflection_ref: Optional[str]

    requires_confirmation: bool
    halted: bool

    retry_count: int
    graph_depth: int

    error: Optional[str]
