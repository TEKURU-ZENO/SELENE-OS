"""
SELENE OS — Orchestrator (Phase 7 LangGraph Integration)
The central brain of SELENE OS.
Now delegates execution flow to the LangGraph Supervisor while streaming events to the UI.
"""

import uuid
import json
import asyncio
from typing import AsyncGenerator
from schemas import ChatRequest
from core.graph_state import SeleneState
from core.graph_supervisor import graph_supervisor
from core.graph_event_adapter import graph_event_adapter
from core.event_bus import event_bus
from core.event_coalescer import event_coalescer
from memory.memory_manager import memory_manager
from schemas import MessageRole
import structlog

logger = structlog.get_logger(__name__)


class Orchestrator:
    """
    The Orchestrator now acts as the bridge between the external world (API/UI)
    and the internal cognitive runtime (LangGraph).
    """

    async def process_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Process a user request via the LangGraph runtime, yielding SSE."""
        session_id = request.session_id or str(uuid.uuid4())
        task_id = f"task_{uuid.uuid4().hex}"
        
        logger.info("cognitive_loop_start", session_id=session_id, task_id=task_id)
        
        # Subscribe to Event Bus for this session
        event_queue = await event_bus.subscribe(session_id)
        
        try:
            # Log initial interaction
            memory_manager.log_interaction(session_id, MessageRole.USER.value, request.input)

            # Initialize minimal Graph State
            initial_state: SeleneState = {
                "task_id": task_id,
                "session_id": session_id,
                "user_query": request.input,
                "intent": {},
                "context_bundle_ref": "",
                "plan_ref": "",
                "current_node_id": None,
                "reflection_ref": None,
                "requires_confirmation": False,
                "halted": False,
                "retry_count": 0,
                "graph_depth": 0,
                "error": None
            }

            # Start LangGraph Supervisor as a background task
            # In a true async environment, we'd run this concurrently and read from the event_queue.
            # Here we loop over the graph state stream and publish UI events.
            
            async for state_patch in graph_supervisor.execute_supervised(initial_state):
                # Identify which node just ran (LangGraph astream yields {node_name: state_patch})
                for node_name, updated_state in state_patch.items():
                    if isinstance(updated_state, dict):
                        # Publish UI status via Event Adapter
                        graph_event_adapter.publish_state_update(session_id, node_name, updated_state)
                        
                        # Forward any events from the EventBus to the SSE stream via Coalescer
                        while not event_queue.empty():
                            event = event_queue.get_nowait()
                            event_coalescer.push(event)
                            
                        if event_coalescer.should_flush(session_id):
                            coalesced = event_coalescer.flush(session_id)
                            for evt in coalesced:
                                yield self._sse_event(evt.type.value, evt.payload)

                if state_patch.get("halted") or any(v.get("halted") for v in state_patch.values() if isinstance(v, dict)):
                    break

            # Final flush of the event queue and coalescer
            while not event_queue.empty():
                event_coalescer.push(event_queue.get_nowait())
                
            coalesced = event_coalescer.flush(session_id)
            for evt in coalesced:
                yield self._sse_event(evt.type.value, evt.payload)

            yield self._sse_event("done", {"session_id": session_id, "task_id": task_id})
            
        finally:
            event_bus.unsubscribe(session_id, event_queue)


    def _sse_event(self, event_type: str, data: dict) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

# Singleton
orchestrator = Orchestrator()
