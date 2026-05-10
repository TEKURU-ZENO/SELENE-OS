"""
SELENE OS — Graph Event Adapter
Translates raw LangGraph state transitions into clean UI events over the EventBus.
"""

import asyncio
from typing import Dict, Any
from core.graph_state import SeleneState
from core.event_bus import event_bus
from schemas import EventType
import structlog

logger = structlog.get_logger(__name__)


class GraphEventAdapter:
    """
    Decouples frontend UI from LangGraph internals.
    Listens to graph state updates and publishes standard SSE-compatible events.
    """

    def publish_state_update(self, session_id: str, current_node: str, state: Dict[str, Any]):
        """Publish status updates to the UI based on graph transitions."""
        
        # 1. Translate Nodes to UI Status Messages
        status_msg = self._translate_node_to_status(current_node)
        if status_msg:
            event_bus.publish(session_id, EventType.SYSTEM_STATE, {"message": status_msg})
            
        # 2. Check for HITL/Interrupts
        if state.get("requires_confirmation") and not state.get("halted"):
            event_bus.publish(session_id, EventType.INTERRUPT, {
                "message": "Execution paused. Awaiting human confirmation.",
                "reason": state.get("error", "Safety policy triggered.")
            })
            
        # 3. Check for Fatal Errors
        if state.get("error") and state.get("halted"):
            event_bus.publish(session_id, EventType.SYSTEM_STATE, {
                "message": f"Execution Halted: {state.get('error')}",
                "status": "failed"
            })
            
    def _translate_node_to_status(self, node_name: str) -> str:
        translations = {
            "intent": "Analyzing cognitive intent...",
            "context": "Retrieving context bundle...",
            "planner": "Formulating execution DAG...",
            "critic": "Validating safety and policy constraints...",
            "capability": "Resolving tool capabilities...",
            "execute": "Executing active task...",
            "validation": "Verifying execution outcome...",
            "reflection": "Reflecting on execution patterns...",
            "memory": "Consolidating memory..."
        }
        return translations.get(node_name, f"Processing {node_name}...")


# Singleton
graph_event_adapter = GraphEventAdapter()
