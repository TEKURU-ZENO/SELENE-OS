"""
SELENE OS — Proactive Orchestrator
Listens to Cognitive Triggers (Temporal, Behavioral) and evaluates them via the 
Attention Budget before safely pushing suggestions into the main Orchestrator.
"""

import asyncio
from typing import List
from schemas import (
    ProactiveSuggestion, AttentionScore, TrustControls, 
    SuggestionStatus, Event, EventType
)
from core.attention_budget import attention_budget
from core.event_bus import event_bus
from memory.intent_store import intent_store
import structlog

logger = structlog.get_logger(__name__)


class ProactiveRuntime:
    def __init__(self):
        self._is_running = False

    async def start_daemon(self):
        self._is_running = True
        logger.info("proactive_runtime_started")
        
        while self._is_running:
            await self._evaluate_triggers()
            await asyncio.sleep(60) # Run evaluation loop every minute
            
    async def _evaluate_triggers(self):
        """Scans TemporalMemory and IntentStore for triggers."""
        # Mock active tenant and controls
        tenant_id = "default_tenant"
        controls = TrustControls(tenant_id=tenant_id)
        
        active_intents = intent_store.get_active_intents(tenant_id)
        
        suggestions = []
        
        for intent in active_intents:
            # Example: A pending intent that hasn't been completed
            # Generate a lightweight proposed plan
            score = attention_budget.calculate_attention_score(
                tenant_id=tenant_id,
                urgency=0.6,
                confidence=0.8,
                attention_cost=0.3,
                controls=controls
            )
            
            if score > 0.5: # Threshold to bother the user
                sugg = ProactiveSuggestion(
                    tenant_id=tenant_id,
                    title="Resume Intent?",
                    description=f"You previously paused: {intent.intent_description}. Shall I prepare the execution plan?",
                    trigger_source="cognitive",
                    attention_score=AttentionScore(
                        urgency=0.6, confidence=0.8, attention_cost=0.3, final_score=score
                    )
                )
                suggestions.append(sugg)
                
        # Emit suggestions to the UI EventBus
        for sugg in suggestions:
            logger.info("proactive_suggestion_generated", title=sugg.title, score=sugg.attention_score.final_score)
            await event_bus.publish(
                "system_session", # Mock session broadcast
                Event(
                    tenant_id=tenant_id,
                    session_id="system_session",
                    type=EventType.PROACTIVE_SUGGESTION,
                    payload=sugg.model_dump()
                )
            )

# Singleton
proactive_runtime = ProactiveRuntime()
