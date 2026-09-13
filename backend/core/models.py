"""
SELENE OS — ORM Models
SQLAlchemy models for sessions, messages, execution records, memory entries,
and the governance audit log. All tables use UUIDs as primary keys.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Session & Message Records ────────────────────────────────────

class SessionRecord(Base):
    """Represents a SELENE conversation session."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    last_active = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    tenant_id = Column(String(128), nullable=False, default="default")
    message_count = Column(Integer, default=0)

    messages = relationship("MessageRecord", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_sessions_tenant", "tenant_id"),
        Index("idx_sessions_last_active", "last_active"),
    )


class MessageRecord(Base):
    """Stores individual conversation messages within a session."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), nullable=False)          # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    intent = Column(String(128), nullable=True)
    mode = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    session = relationship("SessionRecord", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_session", "session_id"),
        Index("idx_messages_created", "created_at"),
    )


# ── Execution Records ────────────────────────────────────────────

class ExecutionRecord(Base):
    """
    Persists every execution result (receipts) for replay and audit.
    The receipt_hash is a SHA-256 of the payload — tamper-evident.
    """
    __tablename__ = "executions"

    id = Column(String(36), primary_key=True, default=_uuid)
    job_id = Column(String(128), nullable=False, unique=True)
    session_id = Column(String(36), nullable=True)
    task_id = Column(String(128), nullable=True)
    capability = Column(String(64), nullable=False)
    mcp_server_id = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False)        # "success" | "failed" | "denied"
    result = Column(JSON, nullable=True)
    receipt_hash = Column(String(64), nullable=True)   # SHA-256[:12]
    validation_confidence = Column(Float, nullable=True)
    hitl_required = Column(Boolean, default=False)
    hitl_decision = Column(String(32), nullable=True)  # "approved" | "rejected" | "modified"
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_executions_session", "session_id"),
        Index("idx_executions_status", "status"),
        Index("idx_executions_created", "created_at"),
    )


# ── Memory Records ───────────────────────────────────────────────

class MemoryRecord(Base):
    """
    Persists episodic and semantic memory entries.
    Semantic entries include embedding vectors (stored as JSON for SQLite compat).
    """
    __tablename__ = "memory_records"

    id = Column(String(36), primary_key=True, default=_uuid)
    tenant_id = Column(String(128), nullable=False, default="default")
    memory_type = Column(String(32), nullable=False)   # "episodic" | "semantic" | "procedural"
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)
    embedding = Column(JSON, nullable=True)            # float[] stored as JSON for SQLite
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_memory_tenant", "tenant_id"),
        Index("idx_memory_type", "memory_type"),
    )


# ── Audit Log ────────────────────────────────────────────────────

class AuditLogRecord(Base):
    """
    Immutable governance audit trail. Every policy decision, reflection
    acceptance/rejection, and HITL event is recorded here.
    This table is append-only — no updates or deletes.
    """
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=_uuid)
    event_type = Column(String(64), nullable=False)    # "policy_decision" | "reflection" | "hitl" | "execution"
    subject = Column(String(256), nullable=False)      # e.g., capability name, plugin_id, update description
    outcome = Column(String(32), nullable=False)       # "accepted" | "rejected" | "approved" | "denied"
    reason = Column(Text, nullable=True)
    session_id = Column(String(36), nullable=True)
    job_id = Column(String(128), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_created", "created_at"),
        Index("idx_audit_session", "session_id"),
    )
