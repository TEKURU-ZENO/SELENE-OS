"""
SELENE OS — LangGraph Nodes
Pure cognitive operations mapped to state transitions.
Updated for Phase 9: Meta-Cognition, Reflection Engine, and Adaptive Planning Hooks.
"""

import uuid
from typing import Dict, Any, Optional

from core.graph_state import SeleneState
from core.intent_engine import detect_intent
from core.mode_engine import select_mode
from core.capability_resolver import capability_resolver
from core.execution_engine import execution_engine, _is_receipt_success
from memory.memory_manager import memory_manager
from schemas import (
    Capability,
    ContextBundle,
    ExecutionContext,
    ExecutionPlan,
    ExecutionReceipt,
    ExecutionStatus,
    FilePermissionMode,
    IntentResult,
    IntentType,
    ModeType,
    ObjectiveGroup,
    PlanNode,
    RiskLevel,
    ValidationResult,
)
from runtime.execution_store import execution_store

from core.planner import planner_engine
from core.critic import critic_engine

# Phase 9 Reflection Imports
from reflection import (
    operational_reflection,
    tactical_reflection,
    strategic_reflection,
    learning_policy,
    preference_extractor,
    audit_log,
)

import structlog

logger = structlog.get_logger(__name__)


def _find_plan_node(plan: Optional[ExecutionPlan], node_id: Optional[str]) -> Optional[PlanNode]:
    if not plan or not node_id:
        return None
    for node in plan.nodes:
        if node.id == node_id:
            return node
    return None


def _next_plan_node_id(plan: Optional[ExecutionPlan], completed_node_id: Optional[str]) -> Optional[str]:
    if not plan or not plan.nodes:
        return None
    nodes = plan.nodes
    if not completed_node_id:
        return nodes[0].id
    for idx, node in enumerate(nodes):
        if node.id == completed_node_id:
            if idx + 1 < len(nodes):
                return nodes[idx + 1].id
            return None
    return None


# ── 1. Intent Node ────────────────────────────────────────────────
def node_intent(state: SeleneState) -> SeleneState:
    logger.info("node_intent", task_id=state.get("task_id"))
    intent_result = detect_intent(state["user_query"])
    mode = select_mode(intent_result)

    state["intent"] = {
        "intent_type": intent_result.intent.value,
        "mode": mode.value,
        "confidence": intent_result.confidence,
        "needs_clarification": intent_result.needs_clarification,
    }
    state["graph_depth"] += 1
    return state


# Store retrieved context bundles globally to keep state footprint minimal
retrieved_contexts: Dict[str, Any] = {}


# ── 2. Context Node ───────────────────────────────────────────────
def node_context(state: SeleneState) -> SeleneState:
    logger.info("node_context", task_id=state.get("task_id"))

    intent_data = state.get("intent", {})
    intent_val = intent_data.get("intent_type", "task")
    mode_val = intent_data.get("mode", "HYBRID")

    intent_res = IntentResult(
        intent=IntentType(intent_val),
        mode=ModeType(mode_val),
        confidence=intent_data.get("confidence", 1.0),
        needs_clarification=intent_data.get("needs_clarification", False),
    )

    bundle = memory_manager.fetch_context(state["user_query"], state["session_id"], intent_res)

    ref = f"ctx_{uuid.uuid4().hex}"
    retrieved_contexts[ref] = bundle

    state["context_bundle_ref"] = ref
    state["graph_depth"] += 1
    return state


# ── 3. Planner Node (Adaptive) ────────────────────────────────────
async def node_planner(state: SeleneState) -> SeleneState:
    logger.info("node_planner", task_id=state.get("task_id"), repair_count=state.get("repair_count", 0))

    bundle = retrieved_contexts.get(state.get("context_bundle_ref"))
    if not bundle:
        bundle = ContextBundle(session_id=state["session_id"])

    raw_procedural = []
    planning_prefs = preference_extractor.extract(raw_procedural)

    repair_context = state.get("repair_context", None)

    constraints = {
        "max_depth": 10,
        "allowed_capabilities": ["navigate_web", "find_information", "interact_ui"],
        "environment": "development",
        "avoid_patterns": planning_prefs.avoid_patterns,
        "preferred_capabilities": planning_prefs.preferred_capabilities,
    }

    plan = await planner_engine.generate_plan(
        user_query=state["user_query"],
        context_bundle=bundle,
        constraints=constraints,
        repair_context=repair_context,
    )

    execution_store.initialize_task(state["task_id"])
    execution_store.save_plan(plan)
    state["plan_ref"] = plan.plan_id
    state["graph_depth"] += 1
    return state


# ── 4. Critic Node ────────────────────────────────────────────────
async def node_critic(state: SeleneState) -> SeleneState:
    logger.info("node_critic", task_id=state.get("task_id"))

    plan = execution_store.get_plan(state.get("plan_ref"))
    if not plan:
        plan = ExecutionPlan(
            objective=state.get("user_query", "Fallback"),
            groups=[
                ObjectiveGroup(
                    id="g1",
                    objective="Fallback Group",
                    nodes=[
                        PlanNode(
                            id="n1",
                            capability=Capability.FIND_INFORMATION,
                            objective="Find info",
                            risk_level=RiskLevel.LOW,
                        )
                    ],
                )
            ],
        )
        execution_store.save_plan(plan)
        state["plan_ref"] = plan.plan_id

    verdict = await critic_engine.evaluate_plan(plan)
    state["critic_verdict"] = verdict.model_dump()

    if not verdict.approved:
        next_repair = state.get("repair_count", 0) + 1
        state["repair_count"] = next_repair
        state["repair_context"] = {
            "critical_issues": [i.message for i in verdict.issues],
            "required_changes": verdict.suggested_repairs,
        }
        if next_repair >= 3:
            state["error"] = "Max plan repairs exceeded."
    else:
        state["repair_context"] = None
        state["error"] = None
        state["current_node_id"] = plan.nodes[0].id if plan.nodes else None

    state["graph_depth"] += 1
    return state


# ── 5. Capability Resolver Node ───────────────────────────────────
async def node_capability_resolution(state: SeleneState) -> SeleneState:
    logger.info("node_capability_resolution", task_id=state.get("task_id"), node_id=state.get("current_node_id"))

    plan = execution_store.get_plan(state.get("plan_ref"))
    node = _find_plan_node(plan, state.get("current_node_id"))
    resolved_tools = dict(state.get("resolved_tools") or {})

    if node:
        ctx = ExecutionContext(
            session_id=state["session_id"],
            trace_id=state["task_id"],
            environment="development",
            file_permission_mode=FilePermissionMode.WRITE_ALLOWED,
        )
        tool_def = await capability_resolver.resolve(node.capability, ctx)
        resolved_tools[node.id] = tool_def.name if tool_def else f"mcp:{node.capability.value}"

    state["resolved_tools"] = resolved_tools
    state["graph_depth"] += 1
    return state


# ── 6. Execution Node ─────────────────────────────────────────────
async def node_execution(state: SeleneState) -> SeleneState:
    logger.info("node_execution", task_id=state.get("task_id"), node_id=state.get("current_node_id"))

    plan = execution_store.get_plan(state.get("plan_ref"))
    node = _find_plan_node(plan, state.get("current_node_id"))

    if node:
        if node.requires_confirmation and not node.params.get("hitl_approved"):
            state["requires_confirmation"] = True
            state["graph_depth"] += 1
            return state

        ctx = ExecutionContext(
            session_id=state["session_id"],
            trace_id=state["task_id"],
            environment="development",
            file_permission_mode=FilePermissionMode.WRITE_ALLOWED,
        )
        candidates = await capability_resolver.resolve_candidates(node.capability, ctx)
        if candidates:
            result_node = await execution_engine._execute_node(state["session_id"], node, ctx)
            if result_node.receipt:
                execution_store.save_receipt(state["task_id"], node.id, result_node.receipt)
        else:
            receipt = ExecutionReceipt(
                source_type="mcp",
                source_name="graph_dispatch",
                tool=f"mcp:{node.capability.value}",
                capability=node.capability,
                status=ExecutionStatus.SUCCESS,
                duration_ms=1.0,
                result={"objective": node.objective, "status": "dispatched"},
                logs=[f"Dispatched capability {node.capability.value} for {node.id}"],
            )
            execution_store.save_receipt(state["task_id"], node.id, receipt)

    state["graph_depth"] += 1
    return state


# ── 7. Validation Node ────────────────────────────────────────────
def node_validation(state: SeleneState) -> SeleneState:
    logger.info("node_validation", task_id=state.get("task_id"), node_id=state.get("current_node_id"))

    if state.get("requires_confirmation"):
        state["graph_depth"] += 1
        return state

    plan = execution_store.get_plan(state.get("plan_ref"))
    current_id = state.get("current_node_id")
    task_state = execution_store.get_task_state(state["task_id"]) or {}
    node_meta = task_state.get("nodes", {}).get(current_id or "", {})
    receipt_id = node_meta.get("receipt_id")
    receipt = execution_store.get_receipt(receipt_id) if receipt_id else None

    success = _is_receipt_success(receipt) if receipt is not None else True
    validation_res = ValidationResult(
        success=success,
        passed_criteria=["receipt_verified"] if success else [],
        failed_criteria=[] if success else ["node_execution_failed"],
        confidence=0.95 if success else 0.2,
    )

    state["validation_result"] = validation_res.model_dump()

    if not validation_res.success:
        state["error"] = "Validation failed. Criteria not met."
        state["retry_count"] = state.get("retry_count", 0) + 1
    else:
        state["error"] = None
        state["current_node_id"] = _next_plan_node_id(plan, current_id)

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

    task_state = execution_store.get_task_state(state["task_id"]) or {}
    receipt = None
    for node_info in reversed(list(task_state.get("nodes", {}).values())):
        rid = node_info.get("receipt_id")
        if rid and execution_store.get_receipt(rid):
            receipt = execution_store.get_receipt(rid)
            break

    if receipt is None:
        receipt = ExecutionReceipt(
            tool="mock",
            status=ExecutionStatus.SUCCESS,
            duration_ms=100,
            result=None,
        )

    val_dict = state.get("validation_result") or {
        "success": True,
        "passed_criteria": [],
        "failed_criteria": [],
        "confidence": 1.0,
    }
    validation = ValidationResult.model_validate(val_dict)

    op_ref = operational_reflection.analyze(receipt, validation)
    tactical_refs = tactical_reflection.aggregate([op_ref])
    strat_ref = await strategic_reflection.reflect(tactical_refs)

    existing_memory = []
    approved_updates, _ = learning_policy.evaluate(strat_ref.procedural_updates, existing_memory)

    for update in strat_ref.procedural_updates:
        if update in approved_updates:
            audit_log.record(update, "accepted", "Passed threshold checks.")
        else:
            audit_log.record(update, "rejected", "Failed learning policy constraints.")

    state["reflection_ref"] = f"refl_{uuid.uuid4().hex}"
    state["pending_procedural_updates"] = [u.model_dump() for u in approved_updates]
    state["graph_depth"] += 1
    return state


# ── 10. Memory Update Node ────────────────────────────────────────
def node_memory_update(state: SeleneState) -> SeleneState:
    logger.info("node_memory_update", task_id=state.get("task_id"))

    updates = state.get("pending_procedural_updates", [])
    if updates:
        logger.info("persisting_procedural_updates", count=len(updates))
        for upd in updates:
            memory_manager.learn_workflow(upd, trigger=upd.get("trigger_context", "reflection"))

    state["graph_depth"] += 1
    return state
