"""
SELENE OS — Event Coalescer
Batches and debounces raw runtime logs into semantic cognitive events 
to preserve frontend Cognitive Calm.
"""

import time
from typing import List, Dict, Any
from schemas import Event, EventType
import structlog

logger = structlog.get_logger(__name__)


class EventCoalescer:
    def __init__(self, debounce_ms: int = 500):
        self.debounce_ms = debounce_ms
        self._buffer: Dict[str, List[Event]] = {} # session_id -> [Event]
        self._last_flush: Dict[str, float] = {}

    def push(self, event: Event) -> None:
        """Push a raw event into the coalescer."""
        if event.session_id not in self._buffer:
            self._buffer[event.session_id] = []
            self._last_flush[event.session_id] = time.time()
            
        self._buffer[event.session_id].append(event)
        
    def should_flush(self, session_id: str) -> bool:
        if session_id not in self._last_flush:
            return False
        return (time.time() - self._last_flush[session_id]) * 1000 >= self.debounce_ms

    def flush(self, session_id: str) -> List[Event]:
        """
        Translates raw execution logs into semantic UI events.
        """
        if session_id not in self._buffer:
            return []
            
        raw_events = self._buffer.pop(session_id)
        self._last_flush[session_id] = time.time()
        
        coalesced_events = []
        exec_logs = []
        
        for evt in raw_events:
            if evt.type == EventType.EXECUTION_LOG:
                exec_logs.append(evt)
            else:
                coalesced_events.append(evt) # Pass through high-level events
                
        # Coalesce execution logs
        if exec_logs:
            # Instead of 10 "tool_progress" events, we emit 1 summarized event
            summary_msg = f"Executed {len(exec_logs)} sub-tasks."
            if len(exec_logs) == 1:
                summary_msg = exec_logs[0].payload.get("message", summary_msg)
                
            coalesced_events.append(Event(
                session_id=session_id,
                type=EventType.EXECUTION_LOG,
                payload={"message": summary_msg, "batch_size": len(exec_logs)}
            ))
            
        return coalesced_events

# Singleton
event_coalescer = EventCoalescer()
