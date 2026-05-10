"""
SELENE OS — LangGraph Nodes
Pure cognitive operations mapped to state transitions.
Updated for Phase 9: Meta-Cognition, Reflection Engine, and Adaptive Planning Hooks.
"""

import uuid
from typing import Dict, Any

from core.graph_state import SeleneState
from core.intent_engine import detect_intent
from core.mode_engine import select_mode
from core.capability_resolver import capability_resolver
from memory.memory_manager import memory_manager
from schemas import IntentResult, ExecutionStatus, ValidationResult, ExecutionReceipt
from runtime.execution_store import execution_store
from tools.registry import tool_registry

from core.planner import planner_engine
from core.critic import critic_engine

# Phase 9 Reflection Imports
from reflection import (
    operational_reflection, tactical_reflection, 
    strategic_reflection, learning_policy, 
    preference_extractor, audit_log
)

import structlog
logger = structlog.get_logger(__name__)


# ── 1. Intent Node ────────────────────────────────────────────────
def node_intent(state: SeleneState) -> SeleneState:
    logger.info("node_intent", task_id=state.get("task_id"))
    intent_result = detect_intent(state["user_query"])
    mode = select_mode(intent_result)
    
    state["intent"] = {
        "intent_type": intent_result.intent.value,
        "mode": mode.value,
        "confidence": intent_result.confidence,
        "needs_clarification": intent_result.needs_clarification
    }
    state["graph_depth"] += 1
    return state


# ── 2. Context Node ───────────────────────────────────────────────
def node_context(state: SeleneState) -> SeleneState:
    logger.info("node_context", task_id=state.get("task_id"))
    state["context_bundle_ref"] = f"ctx_{uuid.uuid4().hex}"
    state["graph_depth"] += 1
    return state


# ── 3. Planner Node (Adaptive) ────────────────────────────────────
async def node_planner(state: SeleneState) -> SeleneState:
    logger.info("node_planner", task_id=state.get("task_id"), repair_count=state.get("repair_count", 0))
    
    from schemas import ContextBundle
    bundle = ContextBundle(session_id=state["session_id"])
    
    # Phase 9: Adaptive Planning Hook
    # Fetch procedural memory and extract constraints
    raw_procedural = [] # Mock fetching from memory_manager
    planning_prefs = preference_extractor.extract(raw_procedural)
    
    repair_context = state.get("repair_context", None)
    
    # Pass planning_prefs as constraints
    constraints = {
        "max_depth": 10,
        "allowed_capabilities": ["navigate_web", "find_information", "interact_ui"],
        "environment": "development",
        "avoid_patterns": planning_prefs.avoid_patterns,
        "preferred_capabilities": planning_prefs.preferred_capabilities
    }
    
    plan = await planner_engine.generate_plan(
        user_query=state["user_query"],
        context_bundle=bundle,
        constraints=constraints,
        repair_context=repair_context
    )
    
    execution_store.initialize_task(state["task_id"])
    state["plan_ref"] = plan.plan_id
    state["graph_depth"] += 1
    return state


# ── 4. Critic Node ────────────────────────────────────────────────
async def node_critic(state: SeleneState) -> SeleneState:
    logger.info("node_critic", task_id=state.get("task_id"))
    from schemas import ExecutionPlan, ObjectiveGroup, PlanNode, Capability, RiskLevel
    
    plan = ExecutionPlan(
        objective="Mock",
        groups=[ObjectiveGroup(id="g1", objective="o1", nodes=[
            PlanNode(id="n1", capability=Capability.FIND_INFORMATION, objective="Find info", risk_level=RiskLevel.LOW)
        ])]
    )
    
    verdict = await critic_engine.evaluate_plan(plan)
    state["critic_verdict"] = verdict.model_dump()
    
    if not verdict.approved:
        state["repair_count"] = state.get("repair_count", 0) + 1
        state["repair_context"] = {
            "critical_issues": [i.message for i in verdict.issues],
            "required_changes": verdict.suggested_repairs
        }
    else:
        state["repair_context"] = None
        state["current_node_id"] = "n1" 
        
    state["graph_depth"] += 1
    return state


# ── 5. Capability Resolver Node ───────────────────────────────────
def node_capability_resolution(state: SeleneState) -> SeleneState:
    logger.info("node_capability_resolution", task_id=state.get("task_id"))
    state["graph_depth"] += 1
    return state


# ── 6. Execution Node ─────────────────────────────────────────────
def node_execution(state: SeleneState) -> SeleneState:
    logger.info("node_execution", task_id=state.get("task_id"))
    state["graph_depth"] += 1
    return state


# ── 7. Validation Node ────────────────────────────────────────────
def node_validation(state: SeleneState) -> SeleneState:
    logger.info("node_validation", task_id=state.get("task_id"))
    
    validation_res = ValidationResult(
        success=True,
        passed_criteria=["dom_contains_success"],
        failed_criteria=[],
        confidence=0.95
    )
    
    # Save validation res to state for reflection
    state["validation_result"] = validation_res.model_dump()
    
    if not validation_res.success:
        state["error"] = "Validation failed. Criteria not met."
        
    state["current_node_id"] = None 
    
    state["graph_depth"] += 1
    return state


# ── 8. HITL Node ──────────────────────────────────────────────────
def node_hitl(state: SeleneState) -> SeleneState:
    logger.info("node_hitl", task_id=state.get("task_id"))
    state["halted"] = True
    state["graph_depth"] += 1
    return state


# ── 9. Reflection Node (Phase 9 Integration) ──────────────────────
async def node_reflection(state: SeleneState) -> SeleneState:
    """Executes the full Reflection Pipeline."""
    logger.info("node_reflection", task_id=state.get("task_id"))
    
    # 1. Gather inputs
    receipt = ExecutionReceipt(tool="mock", status=ExecutionStatus.SUCCESS, duration_ms=100, result=None)
    val_dict = state.get("validation_result", {"success": True, "passed_criteria": [], "failed_criteria": [], "confidence": 1.0})
    validation = ValidationResult.model_validate(val_dict)
    
    # 2. Operational Reflection
    op_ref = operational_reflection.analyze(receipt, validation)
    
    # 3. Tactical Reflection (Simulate historical aggregation)
    tactical_refs = tactical_reflection.aggregate([op_ref])
    
    # 4. Strategic Reflection
    strat_ref = await strategic_reflection.reflect(tactical_refs)
    
    # 5. Learning Policy Engine
    existing_memory = [] # Mock DB fetch
    approved_updates, rejections = learning_policy.evaluate(strat_ref.procedural_updates, existing_memory)
    
    # 6. Audit Log & Memory Update Prep
    for update in strat_ref.procedural_updates:
        if update in approved_updates:
            audit_log.record(update, "accepted", "Passed threshold checks.")
        else:
            audit_log.record(update, "rejected", "Failed learning policy constraints.")
            
    # Save reflection ref
    state["reflection_ref"] = f"refl_{uuid.uuid4().hex}"
    
    # Attach updates to be persisted by node_memory_update
    state["pending_procedural_updates"] = [u.model_dump() for u in approved_updates]
    
    state["graph_depth"] += 1
    return state


# ── 10. Memory Update Node ────────────────────────────────────────
def node_memory_update(state: SeleneState) -> SeleneState:
    logger.info("node_memory_update", task_id=state.get("task_id"))
    
    # Persist pending_procedural_updates to MemoryManager
    updates = state.get("pending_procedural_updates", [])
    if updates:
        logger.info("persisting_procedural_updates", count=len(updates))
        # memory_manager.store_procedural(...)
        
    state["graph_depth"] += 1
    return state
