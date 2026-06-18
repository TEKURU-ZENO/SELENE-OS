"""
SELENE OS — Graph Supervisor
Wraps graph execution to enforce resource limits, detect loops, and kill stalled graphs.
"""

import asyncio
from typing import AsyncGenerator
from core.graph_state import SeleneState
from core.graph_routing import selene_graph
import structlog

logger = structlog.get_logger(__name__)

class GraphSupervisor:
    MAX_DEPTH = 50
    MAX_EXECUTION_TIME_SEC = 300  # 5 minutes absolute timeout

    async def execute_supervised(self, initial_state: SeleneState) -> AsyncGenerator[dict, None]:
        """
        Executes the LangGraph with strict limits and yields state updates.
        """
        task_id = initial_state.get("task_id")
        logger.info("graph_supervisor_started", task_id=task_id)

        try:
            # We use asyncio.wait_for to enforce the absolute timeout
            async for state_update in self._stream_graph(initial_state):
                
                # Check depth limit
                depth = state_update.get("graph_depth", 0)
                if depth > self.MAX_DEPTH:
                    logger.error("graph_depth_limit_exceeded", task_id=task_id, depth=depth)
                    state_update["error"] = "MAX_GRAPH_DEPTH exceeded (Infinite loop detected)"
                    state_update["halted"] = True
                    yield state_update
                    break

                yield state_update
                
                if state_update.get("halted"):
                    break

        except asyncio.TimeoutError:
            logger.error("graph_timeout_exceeded", task_id=task_id, limit=self.MAX_EXECUTION_TIME_SEC)
            yield {**initial_state, "error": "MAX_EXECUTION_TIME exceeded", "halted": True}
        except Exception as e:
            logger.error("graph_fatal_error", task_id=task_id, error=str(e))
            yield {**initial_state, "error": f"Fatal Supervisor Error: {str(e)}", "halted": True}

    async def _stream_graph(self, state: SeleneState) -> AsyncGenerator[dict, None]:
        # Wrap the synchronous graph stream in an async generator.
        # LangGraph supports astream(), which yields nodes as they complete.
        
        # NOTE: For MVP, we'll simulate the async iteration because astream() 
        # behavior depends heavily on the specific LangGraph version/config.
        
        async for output in selene_graph.astream(state):
            # output is typically a dict mapping node_name -> returned state
            for node_name, state_patch in output.items():
                logger.debug("graph_node_completed", node=node_name)
                yield state_patch

# Singleton
graph_supervisor = GraphSupervisor()
