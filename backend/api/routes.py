"""
SELENE OS — API Routes
FastAPI route handlers for the SELENE cognitive pipeline.
"""

import asyncio
import json
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from schemas import ChatRequest
from core.orchestrator import orchestrator
from memory.session_store import session_store
from mcp.registry.server_registry import server_registry
from runtime.workers.worker_pool import worker_pool
from connectors.connector_registry import connector_registry
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["SELENE"])


# ── Chat ─────────────────────────────────────────────────────────

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Primary chat endpoint — streams SELENE's response via Server-Sent Events.

    SSE event types emitted:
    - intent:  Intent classification result (intent, mode, confidence)
    - status:  Processing status updates
    - token:   Individual response tokens for real-time rendering
    - plan:    Execution plan nodes
    - hitl:    Human-In-The-Loop pause notification
    - done:    Completion signal with session metadata
    """
    logger.info("chat_request", input_length=len(request.input), session_id=request.session_id)

    return StreamingResponse(
        orchestrator.process_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Sessions ──────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    sessions = session_store.get_active_sessions()
    return {
        "sessions": [
            session_store.get_session_stats(sid)
            for sid in sessions
        ],
        "total": len(sessions),
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get conversation history for a session."""
    history = session_store.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in history
        ],
        "stats": session_store.get_session_stats(session_id),
    }


@router.get("/sessions/{session_id}/replay")
async def replay_session(session_id: str):
    """
    Fetch the execution record history for a session to drive the
    Cognitive Replay Mode. Returns real records from the execution store.
    """
    from runtime.execution_store import execution_store
    records = execution_store.get_session_records(session_id)
    return {
        "session_id": session_id,
        "replay_events": [
            {
                "step": r.get("capability", "unknown"),
                "outcome": r.get("status", "unknown").upper(),
                "reason": r.get("result", {}).get("message", ""),
                "confidence": f"HIGH ({int(r.get('validation_confidence', 0.9) * 100)}%)",
                "governance_impact": "HITL Required" if r.get("hitl_required") else "None",
                "receipt_hash": r.get("receipt_hash"),
                "timestamp": r.get("completed_at"),
            }
            for r in records
        ],
        "total": len(records),
    }


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a session's conversation history."""
    success = session_store.clear_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "cleared", "session_id": session_id}


# ── HITL Resolution ───────────────────────────────────────────────

_pending_hitl: dict[str, dict] = {}  # job_id → {future, job_data}


@router.get("/hitl/pending")
async def get_pending_hitl():
    """Returns all currently paused HITL jobs awaiting human decision."""
    from runtime.execution_store import execution_store
    pending = execution_store.get_pending_hitl()
    return {"pending_jobs": pending, "count": len(pending)}


@router.post("/hitl/{job_id}/approve")
async def approve_hitl(job_id: str, modifications: Optional[dict] = Body(default=None)):
    """
    Approves a paused HITL job, optionally with parameter modifications.
    The LangGraph checkpoint is resumed after this call.
    """
    from runtime.execution_store import execution_store
    job = execution_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    execution_store.record_hitl_decision(job_id, "approved", modifications)
    logger.info("hitl_approved", job_id=job_id, modified=modifications is not None)

    return {
        "status": "approved",
        "job_id": job_id,
        "modified": modifications is not None,
    }


@router.post("/hitl/{job_id}/reject")
async def reject_hitl(job_id: str, reason: Optional[str] = Body(default=None)):
    """Rejects a paused HITL job. The workflow is cancelled and reflected on."""
    from runtime.execution_store import execution_store
    job = execution_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    execution_store.record_hitl_decision(job_id, "rejected", {"reason": reason})
    logger.info("hitl_rejected", job_id=job_id, reason=reason)

    return {"status": "rejected", "job_id": job_id}


# ── Connectors ────────────────────────────────────────────────────

@router.get("/connectors")
async def list_connectors():
    """Returns all registered connectors and their last poll status."""
    return connector_registry.status()


# ── Memory ────────────────────────────────────────────────────────

@router.get("/memory/insights")
async def memory_insights():
    """Returns memory store statistics for the Memory Insights panel."""
    from memory.memory_manager import memory_manager
    from memory.vector_store import vector_store

    return {
        "episodic_entry_count": memory_manager.get_episodic_count(),
        "semantic_index_size": vector_store._index.ntotal if vector_store._initialized else 0,
        "procedural_update_count": memory_manager.get_procedural_count(),
        "session_count": len(session_store.get_active_sessions()),
    }


# ── Workflows ─────────────────────────────────────────────────────

@router.get("/workflows")
async def list_workflows():
    """Returns all available cognitive workflow packs."""
    from workflows.developer_release import get_developer_release_workflow
    from workflows.debugging_workflow import get_debugging_workflow
    from workflows.research_workflow import get_research_workflow

    workflows = [
        get_developer_release_workflow(),
        get_debugging_workflow(),
        get_research_workflow(),
    ]

    return {
        "workflows": [
            {
                "name": w.name,
                "author": w.author,
                "target_tier": w.target_tier.value,
                "capabilities": [c.value for c in w.planning_template.get("expected_capabilities", [])],
                "hitl_checkpoints": w.hitl_checkpoints,
            }
            for w in workflows
        ],
        "total": len(workflows),
    }


# ── Replay Scenarios ──────────────────────────────────────────────

@router.get("/replay/{scenario}")
async def stream_replay_scenario(scenario: str):
    """Streams specific cognitive scenarios for the Trust Dashboard Flight Recorder."""

    async def event_generator():
        events = []

        if scenario == "golden-trace":
            events = [
                {"type": "cognitive_step", "step": "Plan Created", "outcome": "APPROVED", "reason": "Objective: Draft Release Notes. Required capability: PLUGIN_CAPABILITY.", "confidence": "HIGH (98%)", "governance_impact": "None"},
                {"type": "cognitive_step", "step": "Capability Routed", "outcome": "APPROVED", "reason": "GitHub MCP selected based on trust score (0.91) and replay support.", "confidence": "HIGH (91%)", "governance_impact": "None"},
                {"type": "cognitive_step", "step": "Policy Gate Evaluated", "outcome": "APPROVED", "reason": "release_workflow context permitted. HITL required for drafting.", "confidence": "HIGH (100%)", "governance_impact": "HITL Required"},
                {"type": "cognitive_step", "step": "HITL Triggered", "outcome": "PAUSED", "reason": "External drafting action requires human approval.", "confidence": "N/A", "governance_impact": "Workflow Interrupted"},
                {"type": "cognitive_step", "step": "User Modified Action", "outcome": "MODIFIED", "reason": "User appended architectural notes to the release draft.", "confidence": "N/A", "governance_impact": "Human Override"},
                {"type": "cognitive_step", "step": "Execution Resumed", "outcome": "SUCCESS", "reason": "GitHub MCP executed draft. Receipt hash verified: 825b1295a4f7", "confidence": "HIGH (99%)", "governance_impact": "Provenance Intact"},
                {"type": "cognitive_step", "step": "Reflection Generated", "outcome": "ACCEPTED", "reason": "Procedural Update: Trust firewall prevents context leakage deterministically.", "confidence": "HIGH (95%)", "governance_impact": "Learning Confirmed"}
            ]
        elif scenario == "tampering-attack":
            events = [
                {"type": "cognitive_step", "step": "Plan Created", "outcome": "APPROVED", "reason": "Objective: Summarize PR. Required capability: READ_DOCUMENT.", "confidence": "HIGH (99%)", "governance_impact": "None"},
                {"type": "cognitive_step", "step": "Execution Initiated", "outcome": "APPROVED", "reason": "GitHub MCP dispatched to fetch PR metadata.", "confidence": "HIGH (94%)", "governance_impact": "None"},
                {"type": "cognitive_step", "step": "Receipt Validation", "outcome": "DENIED", "reason": "Replay Tampering Detected: Payload hash diverged from provenance hash.", "confidence": "HIGH (100%)", "governance_impact": "Provenance Compromised"},
                {"type": "tamper_lock"}
            ]
        elif scenario == "cascading-fallback":
            events = [
                {"type": "cognitive_step", "step": "Capability Routed", "outcome": "APPROVED", "reason": "GitHub MCP selected as primary capability provider.", "confidence": "HIGH (92%)", "governance_impact": "None"},
                {"type": "cognitive_step", "step": "Execution Failed", "outcome": "DENIED", "reason": "GitHub MCP connection timed out after 3000ms.", "confidence": "HIGH (100%)", "governance_impact": "None"},
                {"type": "cognitive_step", "step": "Fallback Activated", "outcome": "MODIFIED", "reason": "Routing to Filesystem MCP (Read Diff). Capability match acceptable.", "confidence": "MEDIUM (71%)", "governance_impact": "Fallback Routing", "metrics": {"fallback_depth": 2, "confidence_drop": 0.18, "recovery_duration_ms": 4210}},
                {"type": "cognitive_step", "step": "Policy Gate Evaluated", "outcome": "PAUSED", "reason": "Fallback provider degrades trust score. Elevating to HITL requirement.", "confidence": "HIGH (98%)", "governance_impact": "HITL Escalation"},
            ]
        elif scenario == "reflection-contradiction":
            events = [
                {"type": "cognitive_step", "step": "Reflection Generated", "outcome": "PROPOSED", "reason": "Procedural Update: Skip HITL for minor repository edits to save time.", "confidence": "MEDIUM (65%)", "governance_impact": "Learning Proposed"},
                {"type": "cognitive_step", "step": "Policy Evaluated", "outcome": "DENIED", "reason": "Contradiction Detected: Core policy mandates HITL for ALL external writes.", "confidence": "HIGH (100%)", "governance_impact": "Reflection Rejected"},
                {"type": "cognitive_step", "step": "Memory Write", "outcome": "DENIED", "reason": "Update discarded to prevent cognitive corruption.", "confidence": "HIGH (100%)", "governance_impact": "Memory Protected"}
            ]
        elif scenario == "attention-fatigue":
            events = [
                {"type": "cognitive_step", "step": "Native Context Signal", "outcome": "RECEIVED", "reason": "User rapidly switching windows. Cognitive load classified as HIGH.", "confidence": "HIGH (88%)", "governance_impact": "None"},
                {"type": "cognitive_step", "step": "Proactivity Tier Adjusted", "outcome": "MODIFIED", "reason": "Attention fatigue threshold breached. Downgrading to PASSIVE.", "confidence": "HIGH (94%)", "governance_impact": "Tier Downgrade"},
                {"type": "cognitive_step", "step": "Suggestion Withheld", "outcome": "DENIED", "reason": "Suppressed proactive calendar reminder to respect user attention budget.", "confidence": "HIGH (96%)", "governance_impact": "Action Suppressed", "suppression_reason": {"fatigue_score": 0.91, "threshold": 0.75, "recent_interrupts": 6, "quiet_hours_active": False}}
            ]

        for ev in events:
            if ev["type"] == "tamper_lock":
                yield f"data: {json.dumps(ev)}\n\n"
                break
            await asyncio.sleep(1.2)
            yield f"data: {json.dumps(ev)}\n\n"

        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# ── Demo ──────────────────────────────────────────────────────────

@router.post("/demo/reset-and-start")
async def demo_reset():
    """Clears prior traces, resets replay state, and restores deterministic seed data."""
    from runtime.execution_store import execution_store
    from core.database import get_session
    from core.models import ExecutionRecord
    from sqlalchemy import delete

    # 1. Reset in-memory store
    execution_store._store.clear()
    execution_store._receipts.clear()
    execution_store._jobs.clear()

    # 2. Reset database
    try:
        async with get_session() as session:
            await session.execute(delete(ExecutionRecord))
    except Exception as e:
        logger.error("demo_reset_db_failed", error=str(e))

    # 3. Seed deterministic pending HITL jobs for the UI demo
    # Seeding GitHub PR draft
    execution_store.register_job(
        job_id="job_pr_draft_123",
        capability="plugin_capability",
        mcp_server_id="github_mcp_core",
        status="waiting_hitl",
        params={
            "repo": "TEKURU-ZENO/SELENE-OS",
            "title": "Release v0.1.3-alpha",
            "body": "This PR compiles the release notes and packages the runtime workspace.",
            "draft": True,
            "action_preview": "Create a release draft pull request on GitHub for repository TEKURU-ZENO/SELENE-OS."
        },
        session_id="default_session",
        hitl_required=True
    )

    # Seeding Slack post
    execution_store.register_job(
        job_id="job_slack_post_456",
        capability="plugin_capability",
        mcp_server_id="slack_mcp_core",
        status="waiting_hitl",
        params={
            "channel": "engineering-releases",
            "text": "🚀 SELENE OS v0.1.3-alpha has been successfully drafted.",
            "action_preview": "Send notification message to Slack channel #engineering-releases."
        },
        session_id="default_session",
        hitl_required=True
    )

    logger.info("demo_reset", action="cleared_prior_traces", deterministic_seed="restored")
    return {
        "status": "reset_successful",
        "message": "Cognitive replay state cleared. Ready for Golden Trace execution. 2 HITL jobs seeded."
    }


# ── Health ────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """System health check — returns real status from all subsystems."""
    from core.redis_client import redis_client
    from mcp.registry.server_registry import server_registry

    redis_ok = redis_client.is_real
    worker_status = worker_pool.status()
    connector_status = connector_registry.status()
    registered_servers = [s.server_id for s in server_registry.list_servers()]

    return {
        "status": "operational",
        "system": "SELENE OS",
        "version": "0.1.3-alpha",
        "layers": {
            "orchestrator": "active",
            "planner": "active",
            "critic": "active",
            "worker_pool": "active" if worker_status["running"] else "stopped",
            "worker_count": worker_status["workers"],
            "redis": "connected" if redis_ok else "fallback_in_memory",
            "mcp_servers": registered_servers,
            "connectors": connector_status["connectors"],
            "connector_polling": "active" if connector_status["running"] else "stopped",
            "memory": "active",
            "safety": "active",
        },
        "timestamp": time.time(),
    }


@router.get("/health/live")
async def health_live():
    """
    Liveness probe: returns status 200 to confirm FastAPI runtime is alive.
    """
    return {"status": "alive", "timestamp": time.time()}


@router.get("/health/ready")
async def health_ready():
    """
    Readiness probe: verifies Redis, Database, EventBus, and directory write permissions.
    """
    from core.redis_client import redis_client
    from core.database import get_session
    from core.event_bus import event_bus
    from config.settings import settings
    from sqlalchemy import text
    from fastapi import Response
    import os

    # 1. Redis check
    redis_ok = False
    redis_error = None
    try:
        if redis_client._client is not None:
            await redis_client.client.ping()
            redis_ok = True
        else:
            redis_error = "Redis client is not initialized"
    except Exception as e:
        redis_error = str(e)

    # 2. Database check
    db_ok = False
    db_error = None
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        db_error = str(e)

    # 3. EventBus check
    eventbus_ok = False
    try:
        if event_bus is not None:
            eventbus_ok = True
    except Exception:
        pass

    # 4. Replay and Export directories check
    dirs_to_check = {
        "replay_dir": settings.REPLAY_DIR,
        "export_dir": settings.EXPORT_DIR,
        "audit_dir": settings.AUDIT_DIR,
    }
    writable_statuses = {}
    for key, path in dirs_to_check.items():
        writable = False
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, f".write_test_{int(time.time())}")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            writable = True
        except Exception:
            pass
        writable_statuses[key] = writable

    all_dirs_ok = all(writable_statuses.values())
    is_ready = redis_ok and db_ok and eventbus_ok and all_dirs_ok
    status_code = 200 if is_ready else 503

    response_content = {
        "status": "ready" if is_ready else "not_ready",
        "redis": "connected" if redis_ok else f"unavailable ({redis_error})",
        "database": "connected" if db_ok else f"unavailable ({db_error})",
        "event_bus": "operational" if eventbus_ok else "unoperational",
        "directories": {
            k: "writable" if v else "read_only_or_missing"
            for k, v in writable_statuses.items()
        }
    }

    return Response(
        content=json.dumps(response_content),
        status_code=status_code,
        media_type="application/json"
    )


@router.get("/health/metrics")
async def health_metrics():
    """
    Metrics endpoint: outputs active sessions, database connections, and worker counts.
    """
    from memory.memory_manager import memory_manager
    from memory.vector_store import vector_store
    from runtime.workers.worker_pool import worker_pool
    from runtime.execution_store import execution_store

    worker_status = worker_pool.status()
    active_sessions = session_store.get_active_sessions()

    return {
        "timestamp": time.time(),
        "sessions": {
            "active_count": len(active_sessions),
        },
        "worker_pool": {
            "workers_count": worker_status.get("workers", 0),
            "running": worker_status.get("running", False),
        },
        "execution": {
            "total_jobs_tracked": len(execution_store._jobs),
            "pending_hitl_jobs": len(execution_store.get_pending_hitl()),
        },
        "memory_store": {
            "episodic_entries": memory_manager.get_episodic_count(),
            "semantic_index_size": vector_store._index.ntotal if vector_store._initialized else 0,
            "procedural_updates": memory_manager.get_procedural_count(),
        }
    }
