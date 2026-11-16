"""
SELENE OS — Execution Engine
Executes a validated Plan DAG in topological parallel waves.
Uses CapabilityResolver + SafetyLayer + PolicyEngine to enforce governance
and automatically recover across fallback tools on primary tool failure.
"""

import asyncio
import inspect
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import structlog

from core.capability_resolver import capability_resolver
from core.event_bus import event_bus
from memory.memory_manager import memory_manager
from safety.policy_engine import policy_engine
from safety.safety_layer import safety_layer
from schemas import (
    EventType,
    ExecutionContext,
    ExecutionPlan,
    ExecutionReceipt,
    ExecutionResultNode,
    ExecutionState,
    ExecutionStatus,
    FilePermissionMode,
    PlanNode,
    StepLog,
    TaskState,
)
from tools.registry import tool_registry

logger = structlog.get_logger(__name__)

_SUCCESS_STATUSES = {
    ExecutionStatus.SUCCESS,
    TaskState.COMPLETED,
    ExecutionStatus.SUCCESS.value,
    TaskState.COMPLETED.value,
}


def _is_receipt_success(receipt: Any) -> bool:
    """Normalize success detection across TaskState and ExecutionStatus receipts."""
    if receipt is None:
        return False
    status = getattr(receipt, "status", None)
    if status in _SUCCESS_STATUSES:
        return True
    if hasattr(status, "value") and status.value in _SUCCESS_STATUSES:
        return True
    return False


def _prepare_handler_kwargs(handler: Callable, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
    """Filters and maps PlanNode params to match the target tool handler signature."""
    raw_params = dict(params or {})
    if "file_path" in raw_params and "path" not in raw_params:
        raw_params["path"] = raw_params["file_path"]
    raw_params["context"] = context

    try:
        sig = inspect.signature(handler)
    except (TypeError, ValueError):
        return raw_params

    accepts_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if accepts_varkw:
        return raw_params

    return {k: v for k, v in raw_params.items() if k in sig.parameters}


class ExecutionEngine:
    def __init__(self):
        self._active_states: Dict[str, ExecutionState] = {}

    def get_state(self, plan_id: str) -> Optional[ExecutionState]:
        return self._active_states.get(plan_id)

    def _build_context(
        self,
        session_id: str,
        environment: str = "development",
        file_permission_mode: FilePermissionMode = FilePermissionMode.WRITE_ALLOWED,
    ) -> ExecutionContext:
        """Constructs the strict ExecutionContext for tool sandboxing."""
        return ExecutionContext(
            session_id=session_id,
            trace_id=f"trace_{uuid.uuid4().hex}",
            user_id="default_user",
            permissions=["web_access", "file_read_write"],
            environment=environment,
            file_permission_mode=file_permission_mode,
        )

    async def execute_plan(
        self,
        session_id: str,
        plan: ExecutionPlan,
        context: Optional[ExecutionContext] = None,
    ) -> ExecutionState:
        state = ExecutionState(plan_id=plan.plan_id, status=ExecutionStatus.RUNNING)
        self._active_states[plan.plan_id] = state

        memory_manager.update_working_state(session_id, {"plan_id": plan.plan_id, "status": "running"})
        exec_context = context or self._build_context(session_id)

        logger.info("execution_started", plan_id=plan.plan_id)
        start_time = time.time()

        all_nodes: List[PlanNode] = list(plan.nodes)
        node_map: Dict[str, PlanNode] = {n.id: n for n in all_nodes}
        pending_ids: List[str] = [n.id for n in all_nodes]
        completed_set = set()

        try:
            # Verify all declared dependencies exist before running any wave
            for node in all_nodes:
                missing = [dep for dep in node.dependencies if dep not in node_map]
                if missing:
                    state.failed_nodes.append(node.id)
                    state.status = ExecutionStatus.FAILED
                    state.logs.append(
                        StepLog(
                            node_id=node.id,
                            action=node.objective,
                            status=ExecutionStatus.FAILED,
                            message=f"Missing dependencies: {missing}",
                        )
                    )
                    return state

            while pending_ids:
                ready_nodes = [
                    node_map[nid]
                    for nid in pending_ids
                    if all(dep in completed_set for dep in node_map[nid].dependencies)
                ]

                if not ready_nodes:
                    # Cycle or unresolvable dependency stall
                    stalled = pending_ids[0]
                    state.failed_nodes.append(stalled)
                    state.status = ExecutionStatus.FAILED
                    state.logs.append(
                        StepLog(
                            node_id=stalled,
                            action=node_map[stalled].objective,
                            status=ExecutionStatus.FAILED,
                            message="Dependency deadlock or cycle detected in execution DAG.",
                        )
                    )
                    break

                state.waves_executed += 1
                state.current_node = ready_nodes[0].id

                # Pre-dispatch HITL / Checkpoint gate
                checkpoint_hit = False
                for node in ready_nodes:
                    hitl_reason = self._check_hitl_required(node, exec_context)
                    if hitl_reason:
                        state.status = ExecutionStatus.CHECKPOINT_REACHED
                        event_bus.publish(
                            session_id,
                            EventType.INTERRUPT,
                            {
                                "node_id": node.id,
                                "action": node.checkpoint.action if node.checkpoint else node.objective,
                                "reason": hitl_reason,
                            },
                        )
                        state.logs.append(
                            StepLog(
                                node_id=node.id,
                                action=node.objective,
                                status=ExecutionStatus.CHECKPOINT_REACHED,
                                message=f"Paused for HITL approval: {hitl_reason}",
                            )
                        )
                        logger.warning("execution_checkpoint_reached", node_id=node.id, reason=hitl_reason)
                        checkpoint_hit = True
                        break

                if checkpoint_hit:
                    break

                # Execute ready DAG wave concurrently
                wave_results = await asyncio.gather(
                    *(self._execute_node(session_id, node, exec_context) for node in ready_nodes)
                )

                wave_failed = False
                for node, result_node in zip(ready_nodes, wave_results):
                    pending_ids.remove(node.id)
                    state.results.append(result_node)

                    if result_node.receipt and getattr(result_node.receipt, "logs", None):
                        for log_msg in result_node.receipt.logs:
                            state.logs.append(
                                StepLog(
                                    node_id=node.id,
                                    action=node.objective,
                                    status=result_node.status,
                                    message=log_msg,
                                )
                            )
                    elif result_node.receipt and result_node.receipt.error_details:
                        state.logs.append(
                            StepLog(
                                node_id=node.id,
                                action=node.objective,
                                status=result_node.status,
                                message=result_node.receipt.error_details,
                            )
                        )

                    if result_node.status == ExecutionStatus.SUCCESS:
                        state.completed_nodes.append(node.id)
                        completed_set.add(node.id)
                    else:
                        state.failed_nodes.append(node.id)
                        state.status = ExecutionStatus.FAILED
                        wave_failed = True

                if wave_failed:
                    break

            if state.status not in (ExecutionStatus.FAILED, ExecutionStatus.CHECKPOINT_REACHED):
                state.status = ExecutionStatus.SUCCESS

        except Exception as e:
            logger.error("execution_fatal_error", plan_id=plan.plan_id, error=str(e))
            state.status = ExecutionStatus.FAILED

        finally:
            state.total_duration_ms = (time.time() - start_time) * 1000

            event_bus.publish(
                session_id,
                EventType.SYSTEM_STATE,
                {
                    "plan_id": plan.plan_id,
                    "status": state.status.value,
                    "duration_ms": state.total_duration_ms,
                    "waves_executed": state.waves_executed,
                },
            )

            if state.status == ExecutionStatus.SUCCESS:
                memory_manager.clear_working_state(session_id)
            else:
                memory_manager.update_working_state(
                    session_id, {"plan_id": plan.plan_id, "status": state.status.value}
                )

        return state

    def _check_hitl_required(self, node: PlanNode, context: ExecutionContext) -> Optional[str]:
        """Checks node checkpoints and PolicyEngine for mandatory human confirmation."""
        if node.params.get("hitl_approved"):
            return None
        if node.checkpoint and node.checkpoint.requires_confirmation:
            return node.checkpoint.reason
        if node.requires_confirmation:
            return f"Node '{node.id}' marked requires_confirmation=True."
        policy_checkpoint = policy_engine.evaluate(node.capability, context, node.objective)
        if policy_checkpoint and policy_checkpoint.requires_confirmation:
            return policy_checkpoint.reason
        return None

    async def _resolve_candidate_tool_names(self, node: PlanNode, context: ExecutionContext) -> List[str]:
        """Builds an ordered list of candidate tool names including fallback tools."""
        candidates: List[str] = []

        explicit_tool = getattr(node, "tool", None) or node.params.get("tool")
        if explicit_tool:
            tool_def = tool_registry.get_tool(explicit_tool)
            if tool_def and tool_def.enabled:
                candidates.append(explicit_tool)

        if node.capability:
            resolved_defs = await capability_resolver.resolve_candidates(node.capability, context)
            for tdef in resolved_defs:
                if tdef.name not in candidates:
                    candidates.append(tdef.name)

        for fb_tool in node.params.get("fallback_tools", []):
            tool_def = tool_registry.get_tool(fb_tool)
            if tool_def and tool_def.enabled and fb_tool not in candidates:
                candidates.append(fb_tool)

        return candidates

    async def _execute_node(
        self, session_id: str, node: PlanNode, context: ExecutionContext
    ) -> ExecutionResultNode:
        # 1. Cross-cutting SafetyLayer check against node objective / requested tool
        target_action = str(node.params.get("tool") or node.objective)
        safety_check = safety_layer.classify_action(target_action)
        if safety_check.blocked:
            return ExecutionResultNode(
                node_id=node.id,
                status=ExecutionStatus.FAILED,
                receipt=ExecutionReceipt(
                    tool=target_action,
                    capability=node.capability,
                    status=ExecutionStatus.FAILED,
                    duration_ms=0.0,
                    result=None,
                    error_details=safety_check.reason or "Blocked by SafetyLayer.",
                ),
            )

        # 2. Resolve ordered candidate tools (primary + fallbacks)
        candidate_tools = await self._resolve_candidate_tool_names(node, context)
        if not candidate_tools:
            return ExecutionResultNode(
                node_id=node.id,
                status=ExecutionStatus.FAILED,
                receipt=ExecutionReceipt(
                    tool=node.capability.value,
                    capability=node.capability,
                    status=ExecutionStatus.FAILED,
                    duration_ms=0.0,
                    result=None,
                    error_details=f"No enabled context-compliant tool for capability {node.capability.value}.",
                ),
            )

        # 3. Try primary tool and fall back automatically on failure
        last_receipt: Optional[ExecutionReceipt] = None
        last_error: Optional[str] = None
        attempt_logs: List[str] = []

        for idx, tool_name in enumerate(candidate_tools):
            tool_safety = safety_layer.classify_action(tool_name)
            if tool_safety.blocked:
                attempt_logs.append(f"Skipped blocked tool {tool_name}")
                continue

            handler = tool_registry.get_handler(tool_name)
            if not handler:
                attempt_logs.append(f"Missing handler for {tool_name}")
                continue

            kwargs = _prepare_handler_kwargs(handler, node.params, context)
            try:
                if inspect.iscoroutinefunction(handler):
                    receipt = await handler(**kwargs)
                else:
                    receipt = handler(**kwargs)

                if hasattr(receipt, "status"):
                    if _is_receipt_success(receipt):
                        if idx > 0:
                            receipt.logs = attempt_logs + list(receipt.logs or []) + [
                                f"Recovered via fallback tool '{tool_name}'."
                            ]
                        return ExecutionResultNode(
                            node_id=node.id,
                            status=ExecutionStatus.SUCCESS,
                            receipt=receipt,
                        )
                    last_receipt = receipt
                    last_error = receipt.error_details or f"Tool {tool_name} returned failed status."
                    attempt_logs.append(f"Tool {tool_name} failed: {last_error}")
                else:
                    return ExecutionResultNode(
                        node_id=node.id,
                        status=ExecutionStatus.SUCCESS,
                        receipt=ExecutionReceipt(
                            tool=tool_name,
                            capability=node.capability,
                            status=ExecutionStatus.SUCCESS,
                            duration_ms=0.0,
                            result=receipt,
                            logs=attempt_logs,
                        ),
                    )
            except Exception as e:
                last_error = str(e)
                attempt_logs.append(f"Tool {tool_name} raised error: {last_error}")
                logger.warning("node_tool_attempt_failed", node_id=node.id, tool=tool_name, error=last_error)

        if last_receipt is not None:
            last_receipt.logs = attempt_logs + list(last_receipt.logs or [])
            return ExecutionResultNode(
                node_id=node.id,
                status=ExecutionStatus.FAILED,
                receipt=last_receipt,
            )

        return ExecutionResultNode(
            node_id=node.id,
            status=ExecutionStatus.FAILED,
            receipt=ExecutionReceipt(
                tool=candidate_tools[-1],
                capability=node.capability,
                status=ExecutionStatus.FAILED,
                duration_ms=0.0,
                result=None,
                logs=attempt_logs,
                error_details=last_error or "All candidate tools failed.",
            ),
        )


# Singleton
execution_engine = ExecutionEngine()
