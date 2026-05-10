"""
SELENE OS — Session Memory Store
In-memory session store for Phase 0/1. Will be upgraded to PostgreSQL in Phase 3.
"""

from collections import defaultdict
from datetime import datetime
from typing import Optional
from schemas import ChatMessage, MessageRole
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)


class SessionStore:
    """
    Manages conversational memory per session.
    
    Phase 0-1: In-memory dict (volatile)
    Phase 3+:  PostgreSQL-backed persistent storage
    """

    def __init__(self, max_messages: int = None):
        self._sessions: dict[str, list[ChatMessage]] = defaultdict(list)
        self._max_messages = max_messages or settings.SESSION_MEMORY_LIMIT

    def add_message(self, session_id: str, role: MessageRole, content: str) -> ChatMessage:
        """Add a message to the session history."""
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
        )
        self._sessions[session_id].append(message)

        # Trim to max context window (keep system messages + recent)
        if len(self._sessions[session_id]) > self._max_messages:
            self._sessions[session_id] = self._sessions[session_id][-self._max_messages:]

        logger.debug(
            "message_stored",
            session_id=session_id,
            role=role.value,
            total_messages=len(self._sessions[session_id]),
        )
        return message

    def get_history(self, session_id: str) -> list[ChatMessage]:
        """Retrieve full conversation history for a session."""
        return self._sessions.get(session_id, [])

    def get_context_window(self, session_id: str, n: int = None) -> list[ChatMessage]:
        """Get the last N messages for LLM context injection."""
        history = self.get_history(session_id)
        limit = n or self._max_messages
        return history[-limit:]

    def clear_session(self, session_id: str) -> bool:
        """Clear all messages in a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("session_cleared", session_id=session_id)
            return True
        return False

    def get_active_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())

    def get_session_stats(self, session_id: str) -> dict:
        """Get stats for a specific session."""
        history = self.get_history(session_id)
        return {
            "session_id": session_id,
            "message_count": len(history),
            "first_message": history[0].timestamp.isoformat() if history else None,
            "last_message": history[-1].timestamp.isoformat() if history else None,
        }


# Singleton
session_store = SessionStore()
