"""
SELENE OS — Intent Engine (Restructured)
Classifies user input with confidence-based routing.

UPGRADE: If confidence < threshold → triggers clarification instead of guessing.

Phase 0-1: Rule-based + keyword classification
Phase 2+:  LLM-powered intent classification
"""

import re
from schemas import IntentType, IntentResult, ModeType
from config.settings import settings
import structlog

logger = structlog.get_logger(__name__)

# Confidence below this triggers a clarification request
CLARIFICATION_THRESHOLD = 0.6


# ── Keyword Patterns ─────────────────────────────────────────────

TASK_PATTERNS = [
    r"\b(create|build|make|write|generate|implement|setup|deploy|fix|debug|update|install|configure|prepare|finish|complete|organize|automate|schedule|send|email|open|run|execute|start|launch)\b",
    r"\b(help me|can you|please|i need|i want)\b.*\b(do|make|create|build|write|fix|send|open)\b",
    r"\b(portfolio|project|app|website|code|script|report|document)\b",
]

ANALYSIS_PATTERNS = [
    r"\b(analyze|analyse|compare|evaluate|review|assess|audit|inspect|explain|breakdown|summarize|investigate|examine|understand)\b",
    r"\b(what|why|how)\b.*\b(does|is|are|was|were|works?|happened?|means?)\b",
    r"\b(difference between|pros and cons|trade.?offs?)\b",
]

NEWS_PATTERNS = [
    r"\b(news|latest|trending|update|current|today|headline|breaking|recent)\b",
    r"\b(what'?s?\s+(new|happening|going on))\b",
]

CASUAL_PATTERNS = [
    r"\b(hi|hello|hey|sup|yo|good\s*(morning|afternoon|evening|night)|thanks|thank you|bye|goodbye)\b",
    r"\b(who are you|what are you|what can you do|how are you)\b",
    r"^.{0,15}$",  # Very short messages are likely casual
]

EXPLORE_PATTERNS = [
    r"\b(tell me about|what is|show me|explore|discover|learn about|research|find out)\b",
    r"\b(curious|wondering|interested in)\b",
]


def detect_intent(query: str) -> IntentResult:
    """
    Classify user query into an intent category with confidence-based routing.
    
    If confidence < CLARIFICATION_THRESHOLD → sets needs_clarification = True
    so the orchestrator can ask the user to clarify instead of guessing.
    """
    query_lower = query.lower().strip()

    # Score each category
    scores = {
        IntentType.TASK: _score_patterns(query_lower, TASK_PATTERNS),
        IntentType.ANALYSIS: _score_patterns(query_lower, ANALYSIS_PATTERNS),
        IntentType.NEWS: _score_patterns(query_lower, NEWS_PATTERNS),
        IntentType.CASUAL: _score_patterns(query_lower, CASUAL_PATTERNS),
        IntentType.EXPLORE: _score_patterns(query_lower, EXPLORE_PATTERNS),
    }

    # Find best and second-best scores
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_intent, best_score = sorted_scores[0]
    second_intent, second_score = sorted_scores[1]

    # Calculate confidence
    if best_score == 0:
        best_intent = IntentType.CASUAL
        confidence = 0.4
    else:
        # Base confidence from match count
        confidence = min(0.95, 0.45 + (best_score * 0.18))
        
        # Penalize if second-best is close (ambiguous intent)
        if second_score > 0 and best_score > 0:
            ambiguity_penalty = (second_score / best_score) * 0.15
            confidence -= ambiguity_penalty

    confidence = round(max(0.1, confidence), 2)

    # ── Confidence-Based Routing ─────────────────────────────
    needs_clarification = confidence < CLARIFICATION_THRESHOLD
    clarification_prompt = None

    if needs_clarification:
        clarification_prompt = _generate_clarification(
            query, best_intent, second_intent, confidence
        )

    # Map intent → default mode
    mode = _intent_to_mode(best_intent)

    result = IntentResult(
        intent=best_intent,
        mode=mode,
        confidence=confidence,
        needs_clarification=needs_clarification,
        clarification_prompt=clarification_prompt,
    )

    logger.info(
        "intent_classified",
        query=query[:60],
        intent=result.intent.value,
        mode=result.mode.value,
        confidence=result.confidence,
        needs_clarification=result.needs_clarification,
    )

    return result


def _score_patterns(text: str, patterns: list[str]) -> int:
    """Count how many patterns match the text."""
    score = 0
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            score += 1
    return score


def _intent_to_mode(intent: IntentType) -> ModeType:
    """Map intent type to the default operating mode."""
    mapping = {
        IntentType.TASK: ModeType.PERSONAL,
        IntentType.ANALYSIS: ModeType.GLOBAL,
        IntentType.NEWS: ModeType.GLOBAL,
        IntentType.CASUAL: ModeType.HYBRID,
        IntentType.EXPLORE: ModeType.HYBRID,
    }
    return mapping.get(intent, ModeType.HYBRID)


def _generate_clarification(
    query: str,
    best: IntentType,
    second: IntentType,
    confidence: float,
) -> str:
    """Generate a clarification prompt when intent is ambiguous."""
    templates = {
        (IntentType.TASK, IntentType.ANALYSIS): (
            "I want to make sure I help you correctly — would you like me to "
            "**take action** on this, or **analyze/explain** it?"
        ),
        (IntentType.TASK, IntentType.EXPLORE): (
            "I can either **execute this as a task** or **explore it in depth** — "
            "which would you prefer?"
        ),
        (IntentType.ANALYSIS, IntentType.EXPLORE): (
            "Should I provide a **structured analysis** or a more **exploratory overview**?"
        ),
    }

    key = (best, second)
    reverse_key = (second, best)

    if key in templates:
        return templates[key]
    elif reverse_key in templates:
        return templates[reverse_key]
    else:
        return (
            f"I'm not fully sure how to approach this (confidence: {confidence:.0%}). "
            "Could you clarify what you'd like me to do?"
        )
