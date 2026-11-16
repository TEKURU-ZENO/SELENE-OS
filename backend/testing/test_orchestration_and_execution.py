"""
SELENE OS — Orchestration, DAG Execution, Routing & Supervisor Tests
Verifies parallel DAG wave execution, dependency/cycle detection, HITL gating,
automatic fallback recovery, CapabilityResolver context filtering, LangGraph
routing, GraphSupervisor depth bounds, and end-to-end Orchestrator SSE streaming.
"""

import asyncio
import os
import shutil
import time
import uuid

import agents  # noqa: F401
from agents.file_agent import WORKSPACE_ROOT
from core.capability_resolver import capability_resolver
from core.event_bus import event_bus
from core.execution_engine import execution_engine
from core.graph_routing import route_after_critic, route_after_intent, route_after_validation
from core.graph_supervisor import graph_supervisor
from core.orchestrator import orchestrator
from schemas import (
    Capability,
    ChatRequest,
    EventType,
    ExecutionContext,
    ExecutionPlan,
    ExecutionReceipt,
    ExecutionStatus,
    FilePermissionMode,
    ObjectiveGroup,
    PlanNode,
    RiskLevel,
)
from tools.registry import tool_registry


async def test_execution_engine_parallel_dag_waves_and_dependencies():
    prev_tools = dict(tool_registry._tools)
    prev_handlers = dict(tool_registry._handlers)
    events = []
    try:
        async def branch_tool(label: str, context: ExecutionContext = None) -> ExecutionReceipt:
            t0 = time.perf_counter()
            await asyncio.sleep(0.03)
            t1 = time.perf_counter()
            events.append((label, t0, t1))
            return ExecutionReceipt(
                tool="dag_branch",
                status=ExecutionStatus.SUCCESS,
                duration_ms=(t1 - t0) * 1000.0,
                result=label,
                logs=[f"branch:{label}"],
            )

        async def join_tool(context: ExecutionContext = None) -> ExecutionReceipt:
            t0 = time.perf_counter()
            events.append(("join", t0, t0))
            return ExecutionReceipt(
                tool="dag_join",
                status=ExecutionStatus.SUCCESS,
                duration_ms=0.5,
                result="joined",
                logs=["joined"],
            )

        tool_registry.register("dag_branch", "Branch step", "test_agent", branch_tool, risk_level=RiskLevel.LOW)
        tool_registry.register("dag_join", "Join step", "test_agent", join_tool, risk_level=RiskLevel.LOW)

        plan = ExecutionPlan(
            objective="Parallel diamond DAG",
            groups=[
                ObjectiveGroup(
                    id="g1",
                    objective="Parallel branches then join",
                    nodes=[
                        PlanNode(id="b1", capability=Capability.FIND_INFORMATION, objective="Branch 1", params={"tool": "dag_branch", "label": "b1"}),
                        PlanNode(id="b2", capability=Capability.FIND_INFORMATION, objective="Branch 2", params={"tool": "dag_branch", "label": "b2"}),
                        PlanNode(id="b3", capability=Capability.FIND_INFORMATION, objective="Branch 3", params={"tool": "dag_branch", "label": "b3"}),
                        PlanNode(id="join", capability=Capability.FIND_INFORMATION, objective="Join", dependencies=["b1", "b2", "b3"], params={"tool": "dag_join"}),
                    ],
                )
            ],
        )

        ctx = ExecutionContext(session_id="test_dag_waves", file_permission_mode=FilePermissionMode.READ_ONLY)
        state = await execution_engine.execute_plan("test_dag_waves", plan, context=ctx)

        assert state.status == ExecutionStatus.SUCCESS
        assert state.waves_executed == 2
        assert state.completed_nodes == ["b1", "b2", "b3", "join"]

        branch_ends = [end for name, _, end in events if name != "join"]
        join_start = next(start for name, start, _ in events if name == "join")
        assert join_start >= max(branch_ends) - 1e-4
    finally:
        tool_registry._tools = prev_tools
        tool_registry._handlers = prev_handlers


async def test_execution_engine_detects_missing_and_cyclic_dependencies():
    missing_plan = ExecutionPlan(
        objective="Missing dependency plan",
        groups=[
            ObjectiveGroup(
                id="g_miss",
                objective="Invalid dep",
                nodes=[PlanNode(id="n1", capability=Capability.FIND_INFORMATION, objective="Read", dependencies=["ghost"])],
            )
        ],
    )
    res_miss = await execution_engine.execute_plan("sess_miss", missing_plan)
    assert res_miss.status == ExecutionStatus.FAILED
    assert "n1" in res_miss.failed_nodes

    cycle_plan = ExecutionPlan(
        objective="Cyclic plan",
        groups=[
            ObjectiveGroup(
                id="g_cyc",
                objective="Cycle",
                nodes=[
                    PlanNode(id="a", capability=Capability.FIND_INFORMATION, objective="Node A", dependencies=["b"]),
                    PlanNode(id="b", capability=Capability.FIND_INFORMATION, objective="Node B", dependencies=["a"]),
                ],
            )
        ],
    )
    res_cyc = await execution_engine.execute_plan("sess_cyc", cycle_plan)
    assert res_cyc.status == ExecutionStatus.FAILED
    assert len(res_cyc.failed_nodes) == 1


async def test_execution_engine_hitl_checkpoint_and_approved_resumption():
    tmp_rel = f"test_hitl_{uuid.uuid4().hex[:8]}"
    tmp_abs = os.path.join(WORKSPACE_ROOT, tmp_rel)
    os.makedirs(tmp_abs, exist_ok=True)
    session_id = f"sess_hitl_{uuid.uuid4().hex[:6]}"
    try:
        target = f"{tmp_rel}/gated.txt"
        unapproved_plan = ExecutionPlan(
            objective="Gated file write",
            groups=[
                ObjectiveGroup(
                    id="g_hitl",
                    objective="Write file",
                    nodes=[
                        PlanNode(
                            id="write_1",
                            capability=Capability.MODIFY_SYSTEM,
                            objective="Write gated output",
                            params={"path": target, "content": "approved_content"},
                            risk_level=RiskLevel.HIGH,
                        )
                    ],
                )
            ],
        )

        ctx = ExecutionContext(session_id=session_id, file_permission_mode=FilePermissionMode.WRITE_ALLOWED)
        paused = await execution_engine.execute_plan(session_id, unapproved_plan, context=ctx)
        assert paused.status == ExecutionStatus.CHECKPOINT_REACHED
        assert paused.completed_nodes == []
        assert not os.path.exists(os.path.join(WORKSPACE_ROOT, target))

        history = event_bus.get_history(session_id)
        assert any(e.type == EventType.INTERRUPT for e in history)

        approved_plan = ExecutionPlan(
            objective="Approved file write",
            groups=[
                ObjectiveGroup(
                    id="g_hitl_ok",
                    objective="Write file after HITL",
                    nodes=[
                        PlanNode(
                            id="write_1",
                            capability=Capability.MODIFY_SYSTEM,
                            objective="Write gated output",
                            params={"path": target, "content": "approved_content", "hitl_approved": True},
                            risk_level=RiskLevel.HIGH,
                        )
                    ],
                )
            ],
        )
        resumed = await execution_engine.execute_plan(session_id, approved_plan, context=ctx)
        assert resumed.status == ExecutionStatus.SUCCESS
        assert resumed.completed_nodes == ["write_1"]
        assert os.path.exists(os.path.join(WORKSPACE_ROOT, target))
    finally:
        event_bus.clear_history(session_id)
        shutil.rmtree(tmp_abs, ignore_errors=True)


async def test_execution_engine_automatic_fallback_on_primary_failure():
    prev_tools = dict(tool_registry._tools)
    prev_handlers = dict(tool_registry._handlers)
    try:
        async def failing_primary(context: ExecutionContext = None) -> ExecutionReceipt:
            return ExecutionReceipt(
                tool="primary_flaky",
                status=ExecutionStatus.FAILED,
                duration_ms=1.0,
                result=None,
                error_details="Primary endpoint timed out",
            )

        async def healthy_backup(context: ExecutionContext = None) -> ExecutionReceipt:
            return ExecutionReceipt(
                tool="healthy_backup",
                status=ExecutionStatus.SUCCESS,
                duration_ms=1.0,
                result={"ok": True},
                logs=["backup_ok"],
            )

        tool_registry.register("primary_flaky", "Flaky tool", "test_agent", failing_primary)
        tool_registry.register("healthy_backup", "Backup tool", "test_agent", healthy_backup)

        plan = ExecutionPlan(
            objective="Test automatic tool fallback",
            groups=[
                ObjectiveGroup(
                    id="g_fb",
                    objective="Fallback test",
                    nodes=[
                        PlanNode(
                            id="n_fb",
                            capability=Capability.FIND_INFORMATION,
                            objective="Query with fallback",
                            params={"tool": "primary_flaky", "fallback_tools": ["healthy_backup"]},
                        )
                    ],
                )
            ],
        )
        ctx = ExecutionContext(session_id="sess_fb", file_permission_mode=FilePermissionMode.READ_ONLY)
        state = await execution_engine.execute_plan("sess_fb", plan, context=ctx)
        assert state.status == ExecutionStatus.SUCCESS
        assert state.results[0].receipt.tool == "healthy_backup"
        assert any("Recovered via fallback tool" in log for log in state.results[0].receipt.logs)
    finally:
        tool_registry._tools = prev_tools
        tool_registry._handlers = prev_handlers


async def test_capability_resolver_respects_permissions_and_environment():
    ro_ctx = ExecutionContext(session_id="s1", file_permission_mode=FilePermissionMode.READ_ONLY, environment="development")
    # MODIFY_SYSTEM prioritizes file_write (filtered out in READ_ONLY), leaving system_exec
    mod_tool = await capability_resolver.resolve(Capability.MODIFY_SYSTEM, ro_ctx)
    assert mod_tool is None or mod_tool.name != "file_write"

    prod_ctx = ExecutionContext(session_id="s2", file_permission_mode=FilePermissionMode.WRITE_ALLOWED, environment="production")
    exec_tool = await capability_resolver.resolve(Capability.EXECUTE_CODE, prod_ctx)
    assert exec_tool is None  # os_agent blocked in production


def test_graph_routing_branches():
    assert route_after_intent({"intent": {"needs_clarification": True}}) == "hitl"
    assert route_after_intent({"intent": {"needs_clarification": False}}) == "context"

    assert route_after_critic({"critic_verdict": {"approved": False}, "repair_count": 1}) == "planner"
    assert route_after_critic({"critic_verdict": {"approved": False}, "repair_count": 3}) == "reflection"
    assert route_after_critic({"critic_verdict": {"approved": True}}) == "capability"

    assert route_after_validation({"requires_confirmation": True}) == "hitl"
    assert route_after_validation({"error": "boom", "retry_count": 1}) == "capability"
    assert route_after_validation({"error": "boom", "retry_count": 3}) == "reflection"
    assert route_after_validation({"current_node_id": None}) == "reflection"
    assert route_after_validation({"current_node_id": "node_2"}) == "capability"


async def test_graph_supervisor_max_depth_breaker():
    original_stream = graph_supervisor._stream_graph

    async def runaway_stream(state):
        for depth in (10, graph_supervisor.MAX_DEPTH + 1):
            yield "planner", {**state, "graph_depth": depth}

    graph_supervisor._stream_graph = runaway_stream
    try:
        init_state = {
            "task_id": "t_loop",
            "session_id": "s_loop",
            "user_query": "loop",
            "intent": {},
            "context_bundle_ref": "",
            "plan_ref": "",
            "current_node_id": None,
            "critic_verdict": None,
            "repair_count": 0,
            "repair_context": None,
            "resolved_tools": {},
            "validation_result": None,
            "pending_procedural_updates": [],
            "reflection_ref": None,
            "requires_confirmation": False,
            "halted": False,
            "retry_count": 0,
            "graph_depth": 0,
            "error": None,
        }
        outputs = [patch async for _, patch in graph_supervisor.execute_supervised(init_state)]
        assert outputs[-1]["halted"] is True
        assert "MAX_GRAPH_DEPTH" in outputs[-1]["error"]
    finally:
        graph_supervisor._stream_graph = original_stream


async def test_orchestrator_end_to_end_sse_stream():
    events = [evt async for evt in orchestrator.process_stream(ChatRequest(input="analyze system logs"))]
    assert len(events) >= 5
    assert events[-1].startswith("event: done")
    assert not any("MAX_GRAPH_DEPTH" in evt for evt in events)
