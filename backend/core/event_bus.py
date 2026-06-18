"""
SELENE OS — Execution Event Bus
Decouples orchestration logging and execution state from UI reactivity.
Provides observability, replayability, and multi-client support.
"""

import asyncio
from typing import Callable, Dict, List, Any
from collections import defaultdict
import uuid
import structlog
from schemas import Event, EventType

logger = structlog.get_logger(__name__)


class EventBus:
    """
    Publish-Subscribe Event Bus for SELENE.
    
    Agents and tools publish events here.
    The Orchestrator / API layer subscribes to stream events to the frontend.
    """

    def __init__(self):
        # session_id -> list of subscriber queues
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        # Event history for replayability/analytics (session_id -> list of events)
        self._history: Dict[str, List[Event]] = defaultdict(list)

    def publish(self, session_id: str, event_type: EventType, payload: Dict[str, Any]) -> Event:
        """
        Publish an event to the bus.
        """
        event = Event(
            session_id=session_id,
            type=event_type,
            payload=payload
        )
        
        # Store in history
        self._history[session_id].append(event)
        
        logger.debug(
            "event_published",
            session_id=session_id,
            event_type=event_type.value,
            event_id=event.id
        )

        # Notify subscribers
        for queue in self._subscribers.get(session_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("event_bus_queue_full", session_id=session_id)

        return event

    async def subscribe(self, session_id: str) -> asyncio.Queue:
        """
        Subscribe to a session's event stream.
        Returns an asyncio.Queue that yields Event objects.
        """
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[session_id].append(queue)
        logger.info("event_bus_subscribed", session_id=session_id)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        """
        Remove a subscription.
        """
        if session_id in self._subscribers and queue in self._subscribers[session_id]:
            self._subscribers[session_id].remove(queue)
            logger.info("event_bus_unsubscribed", session_id=session_id)
            
            # Cleanup empty session lists
            if not self._subscribers[session_id]:
                del self._subscribers[session_id]

    def get_history(self, session_id: str) -> List[Event]:
        """Get the event history for a session."""
        return self._history.get(session_id, [])

    def clear_history(self, session_id: str) -> None:
        """Clear the event history for a session."""
        if session_id in self._history:
            del self._history[session_id]


# Singleton
event_bus = EventBus()
