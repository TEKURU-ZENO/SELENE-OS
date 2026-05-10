"""
SELENE OS — Mode Engine
Selects the operating mode (GLOBAL / HYBRID / PERSONAL) based on intent and context.

Phase 0-1: Deterministic mapping from intent
Phase 2+:  Latent space user modeling with DEP embeddings
"""

from schemas import IntentResult, ModeType
import structlog

logger = structlog.get_logger(__name__)


# ── Mode-Specific System Prompt Augmentations ────────────────────

MODE_PROMPTS = {
    ModeType.GLOBAL: """
Operating in GLOBAL mode.
- Prioritize factual accuracy and objectivity
- Use structured, formal language
- Cite sources when possible
- Avoid speculation or subjective commentary
- Focus on deterministic, verifiable information
""",
    ModeType.HYBRID: """
Operating in HYBRID mode.
- Balance factual accuracy with conversational warmth
- Adapt tone based on the query complexity
- Provide context-aware suggestions
- Be helpful and approachable while maintaining precision
""",
    ModeType.PERSONAL: """
Operating in PERSONAL mode.
- Deeply personalized responses adapted to the user's style
- Proactive suggestions based on user patterns
- Creative and expressive when appropriate
- Anticipate user needs and preferences
- Use a conversational, tailored communication style
""",
}


def select_mode(intent_result: IntentResult, user_profile: dict = None) -> ModeType:
    """
    Determine the operating mode based on intent classification and user context.
    
    Phase 2+ will incorporate user profile embeddings for dynamic mode selection.
    """
    mode = intent_result.mode

    # Phase 2+: Override based on user profile preferences
    if user_profile:
        preferred_mode = user_profile.get("preferred_mode")
        if preferred_mode and isinstance(preferred_mode, ModeType):
            # User preference overrides default mapping (if confidence is moderate)
            if intent_result.confidence < 0.8:
                mode = preferred_mode

    logger.info(
        "mode_selected",
        intent=intent_result.intent.value,
        mode=mode.value,
        confidence=intent_result.confidence,
    )

    return mode


def get_mode_prompt(mode: ModeType) -> str:
    """Get the system prompt augmentation for the selected mode."""
    return MODE_PROMPTS.get(mode, MODE_PROMPTS[ModeType.HYBRID])
