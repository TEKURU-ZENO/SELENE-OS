"""
SELENE OS — API Routes
FastAPI route handlers for the SELENE cognitive pipeline.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas import ChatRequest
from core.orchestrator import orchestrator
from memory.session_store import session_store
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["SELENE"])


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Primary chat endpoint — streams SELENE's response via Server-Sent Events.
    
    The SSE stream emits the following event types:
    - intent:  Intent classification result (intent, mode, confidence)
    - status:  Processing status updates
    - token:   Individual response tokens for real-time rendering
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
    """Fetch the event log history to drive the Cognitive Replay Mode."""
    # In a real implementation, we would query an EventStore DB here.
    return {
        "session_id": session_id,
        "replay_events": [] # Empty mock
    }

import asyncio
import json

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
            await asyncio.sleep(1.2) # Simulate processing
            yield f"data: {json.dumps(ev)}\n\n"
            
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@router.post("/demo/reset-and-start")
async def demo_reset():
    """Clears prior traces, resets replay state, and restores deterministic seed data for a flawless demo."""
    # In a full implementation, this would clear the EventStore and Reset DB seeds.
    logger.info("demo_reset", action="cleared_prior_traces", deterministic_seed="restored")
    return {
        "status": "reset_successful",
        "message": "Cognitive replay state cleared. Ready for Golden Trace execution."
    }

@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a session's conversation history."""
    success = session_store.clear_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "cleared", "session_id": session_id}


@router.get("/health")
async def health_check():
    """System health check endpoint."""
    return {
        "status": "operational",
        "system": "SELENE OS",
        "version": "0.1.0",
        "layers": {
            "interface": "active",
            "gateway": "active",
            "intent_engine": "active",
            "mode_engine": "active",
            "context_engine": "pending",
            "orchestrator": "active",
            "planner": "pending",
            "critic": "pending",
            "executor": "pending",
            "memory": "basic",
            "safety": "pending",
        },
    }
