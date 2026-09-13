"""
SELENE OS — LangGraph Orchestration Topology
Defines the StateGraph, nodes, and conditional edges, including the Plan Repair Loop.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from core.graph_state import SeleneState
from core.register_nodes import node_registry
import structlog

logger = structlog.get_logger(__name__)

# Edge Routing Functions

def route_after_intent(state: SeleneState) -> Literal["context", "hitl", "reflection"]:
    if state.get("intent", {}).get("needs_clarification", False):
        return "hitl"
    return "context"

def route_after_critic(state: SeleneState) -> Literal["capability", "planner", "reflection"]:
    # Check if the Critic rejected the plan
    critic_verdict = state.get("critic_verdict", {})
    if not critic_verdict.get("approved", False):
        # Repair Loop Logic
        if state.get("repair_count", 0) < 3:
            logger.info("routing_to_planner_for_repair", retry_count=state.get("repair_count"))
            return "planner"
        else:
            logger.error("max_repairs_exceeded_halting")
            state["error"] = "Max plan repairs exceeded."
            return "reflection"
            
    # If approved and no errors
    if state.get("error"):
        return "reflection"
        
    return "capability"

def route_after_validation(state: SeleneState) -> Literal["capability", "hitl", "reflection"]:
    if state.get("requires_confirmation"):
        return "hitl"
        
    if state.get("error"):
        if state.get("retry_count", 0) < 3:
            return "capability"  # Execution retry
        return "reflection"
        
    if not state.get("current_node_id"):
        return "reflection" # DAG Complete
        
    return "capability"

def route_after_hitl(state: SeleneState) -> Literal["capability", "reflection"]:
    if state.get("error"):
        return "reflection"
    return "capability"


def build_graph() -> StateGraph:
    """Constructs the SELENE Cognitive Graph."""
    
    workflow = StateGraph(SeleneState)

    workflow.add_node("intent", node_registry.get("intent"))
    workflow.add_node("context", node_registry.get("context"))
    workflow.add_node("planner", node_registry.get("planner"))
    workflow.add_node("critic", node_registry.get("critic"))
    workflow.add_node("capability", node_registry.get("capability"))
    workflow.add_node("execute", node_registry.get("execute"))
    workflow.add_node("validation", node_registry.get("validation"))
    workflow.add_node("hitl", node_registry.get("hitl"))
    workflow.add_node("reflection", node_registry.get("reflection"))
    workflow.add_node("memory", node_registry.get("memory"))

    workflow.set_entry_point("intent")
    
    workflow.add_conditional_edges("intent", route_after_intent)
    workflow.add_edge("context", "planner")
    workflow.add_edge("planner", "critic")
    
    # ── Plan Repair Loop Edge ──
    workflow.add_conditional_edges("critic", route_after_critic)
    
    workflow.add_edge("capability", "execute")
    workflow.add_edge("execute", "validation")
    
    # ── DAG Traversal Loop Edge ──
    workflow.add_conditional_edges("validation", route_after_validation)
    
    workflow.add_conditional_edges("hitl", route_after_hitl)
    
    workflow.add_edge("reflection", "memory")
    workflow.add_edge("memory", END)

    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    logger.info("langgraph_compiled_with_checkpointer", nodes=len(workflow.nodes))
    return app

# Singleton
selene_graph = build_graph()
