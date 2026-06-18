"""
SELENE OS — Execution Engine
Executes a validated Plan DAG. Uses Capability Resolver to map capabilities to tools.
Passes ExecutionContext to all tool calls.
"""

import time
import asyncio
from typing import Dict

from schemas import (
    ExecutionPlan, ExecutionState, ExecutionResultNode, 
    StepLog, ExecutionStatus, PlanNode, EventType, ExecutionContext,
    FilePermissionMode
)
from core.event_bus import event_bus
from memory.memory_manager import memory_manager
from core.capability_resolver import capability_resolver
from tools.registry import tool_registry
import structlog

logger = structlog.get_logger(__name__)


class ExecutionEngine:
    def __init__(self):
        self._active_states: Dict[str, ExecutionState] = {}

    def get_state(self, plan_id: str) -> ExecutionState:
        return self._active_states.get(plan_id)

    def _build_context(self, session_id: str) -> ExecutionContext:
        """Constructs the strict ExecutionContext for tool sandboxing."""
        return ExecutionContext(
            session_id=session_id,
            user_id="default_user",
            permissions=["web_access", "file_read_write"],
            environment="development",
            file_permission_mode=FilePermissionMode.WRITE_ALLOWED
        )

    async def execute_plan(self, session_id: str, plan: ExecutionPlan) -> ExecutionState:
        state = ExecutionState(plan_id=plan.plan_id, status=ExecutionStatus.RUNNING)
        self._active_states[plan.plan_id] = state
        
        memory_manager.update_working_state(session_id, {"plan_id": plan.plan_id, "status": "running"})
        context = self._build_context(session_id)
        
        logger.info("execution_started", plan_id=plan.plan_id)
        start_time = time.time()
        
        try:
            for node in plan.nodes:
                state.current_node = node.id
                
                if node.checkpoint and node.checkpoint.requires_confirmation:
                    state.status = ExecutionStatus.CHECKPOINT_REACHED
                    event_bus.publish(session_id, EventType.INTERRUPT, {
                        "node_id": node.id,
                        "action": node.checkpoint.action,
                        "reason": node.checkpoint.reason,
                    })
                    logger.warning("execution_checkpoint_reached", node_id=node.id)
                    # HITL simulate pass/fail
                
                # Execute node using Capability Resolver
                result_node = await self._execute_node(session_id, node, context)
                
                state.results.append(result_node)
                
                # We expect the receipt to hold the logs now
                if result_node.receipt:
                    for l in result_node.receipt.logs:
                        state.logs.append(StepLog(node_id=node.id, action=node.action, status=result_node.status, message=l))
                
                if result_node.status == ExecutionStatus.SUCCESS:
                    state.completed_nodes.append(node.id)
                elif result_node.status == ExecutionStatus.FAILED:
                    state.failed_nodes.append(node.id)
                    state.status = ExecutionStatus.FAILED
                    break
            
            if state.status not in (ExecutionStatus.FAILED, ExecutionStatus.CHECKPOINT_REACHED):
                state.status = ExecutionStatus.SUCCESS
                
        except Exception as e:
            logger.error("execution_fatal_error", plan_id=plan.plan_id, error=str(e))
            state.status = ExecutionStatus.FAILED
            
        finally:
            state.total_duration_ms = (time.time() - start_time) * 1000
            
            event_bus.publish(session_id, EventType.SYSTEM_STATE, {
                "plan_id": plan.plan_id,
                "status": state.status.value,
                "duration_ms": state.total_duration_ms
            })
            
            if state.status == ExecutionStatus.SUCCESS:
                memory_manager.clear_working_state(session_id)
            else:
                memory_manager.update_working_state(session_id, {"plan_id": plan.plan_id, "status": state.status.value})
                
        return state

    async def _execute_node(self, session_id: str, node: PlanNode, context: ExecutionContext) -> ExecutionResultNode:
        # 1. Resolve Capability -> Tool
        tool_to_run = None
        if node.capability:
            tool_def = await capability_resolver.resolve(node.capability, context)
            if tool_def:
                tool_to_run = tool_def.name
        elif node.tool:
            # Fallback if explicitly specified (mostly for legacy/tests)
            tool_to_run = node.tool
            
        if not tool_to_run:
            return ExecutionResultNode(
                node_id=node.id, 
                status=ExecutionStatus.FAILED,
                receipt=None
            )
            
        # 2. Execute Tool
        # Merge context into kwargs
        kwargs = node.params.copy()
        kwargs["context"] = context
        
        # We assume the tool returns an ExecutionReceipt directly now
        # because the agents are updated. If it's a legacy dict, handle it.
        try:
            handler = tool_registry.get_handler(tool_to_run)
            if not handler:
                raise ValueError(f"No handler for tool {tool_to_run}")
                
            if asyncio.iscoroutinefunction(handler):
                receipt = await handler(**kwargs)
            else:
                receipt = handler(**kwargs)
                
            return ExecutionResultNode(
                node_id=node.id,
                status=receipt.status if hasattr(receipt, "status") else ExecutionStatus.SUCCESS,
                receipt=receipt if hasattr(receipt, "status") else None
            )
        except Exception as e:
            logger.error("node_execution_error", node_id=node.id, error=str(e))
            return ExecutionResultNode(
                node_id=node.id,
                status=ExecutionStatus.FAILED,
                receipt=None
            )


# Singleton
execution_engine = ExecutionEngine()
