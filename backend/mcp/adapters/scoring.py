"""
SELENE OS — Capability Resolution Scoring
Provides intelligent, adaptive execution routing. Scores multiple capable MCP 
tools against each other to choose the optimal, safest path.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any

class CapabilityResolutionScore(BaseModel):
    tool_id: str
    trust_score: float = Field(ge=0.0, le=1.0)
    latency_score: float = Field(ge=0.0, le=1.0)
    replay_score: float = Field(ge=0.0, le=1.0)
    context_alignment: float = Field(ge=0.0, le=1.0)
    reliability_score: float = Field(ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)


class ScoringEngine:
    """Calculates the optimal execution path dynamically."""

    def evaluate_tool(self, tool_id: str, descriptor: Any, manifest: Any, active_context_types: list[str]) -> CapabilityResolutionScore:
        # Trust Score
        trust_map = {
            "verified_safe": 1.0,
            "trusted": 0.8,
            "restricted": 0.5,
            "experimental": 0.2,
            "blocked": 0.0
        }
        trust_score = trust_map.get(manifest.trust_classification.value, 0.0)

        # Context Alignment
        alignment_score = 0.0
        if any(ctx in manifest.allowed_contexts for ctx in active_context_types):
            alignment_score = 1.0

        # Replay Support
        replay_score = 1.0 if manifest.supports_replay else 0.2

        # Mock Historical Reliability (eventually fetched from Reflection metrics)
        reliability_score = 0.95 

        # Mock Latency (eventually fetched from Telemetry)
        latency_score = 0.9 

        final_score = (
            (trust_score * 0.4) +
            (alignment_score * 0.3) +
            (reliability_score * 0.15) +
            (replay_score * 0.1) +
            (latency_score * 0.05)
        )

        return CapabilityResolutionScore(
            tool_id=tool_id,
            trust_score=trust_score,
            latency_score=latency_score,
            replay_score=replay_score,
            context_alignment=alignment_score,
            reliability_score=reliability_score,
            final_score=round(final_score, 3)
        )

scoring_engine = ScoringEngine()
