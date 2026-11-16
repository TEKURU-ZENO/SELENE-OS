"""
SELENE OS — Intent & Mode Engine Unit Tests
Covers intent classification, ambiguity penalty & clarification gating,
SparseAutoencoderFilter sparsity, DEPEngine delta alignment, and mode overrides.
"""

import numpy as np

from core.intent_engine import CLARIFICATION_THRESHOLD, detect_intent
from core.mode_engine import SparseAutoencoderFilter, dep_engine, get_mode_prompt, select_mode
from schemas import IntentResult, IntentType, ModeType


def test_intent_task_classification():
    res = detect_intent("please help me create and deploy the project website script")
    assert res.intent == IntentType.TASK
    assert res.mode == ModeType.PERSONAL
    assert res.confidence >= CLARIFICATION_THRESHOLD
    assert res.needs_clarification is False
    assert res.clarification_prompt is None


def test_intent_analysis_and_news_classification():
    analysis = detect_intent("analyze and evaluate why the database works and compare tradeoffs")
    assert analysis.intent == IntentType.ANALYSIS
    assert analysis.mode == ModeType.GLOBAL

    news = detect_intent("what's happening with the latest breaking news today")
    assert news.intent == IntentType.NEWS
    assert news.mode == ModeType.GLOBAL


def test_intent_low_confidence_triggers_clarification():
    unrecognized = detect_intent("quantum entanglement topological invariant manifold")
    assert unrecognized.confidence < CLARIFICATION_THRESHOLD
    assert unrecognized.needs_clarification is True

    ambiguous = detect_intent("create and analyze something")
    assert ambiguous.confidence < CLARIFICATION_THRESHOLD
    assert ambiguous.needs_clarification is True
    assert ambiguous.clarification_prompt is not None


def test_sparse_autoencoder_sparsity_and_normalization():
    sae = SparseAutoencoderFilter(input_dim=64, hidden_dim=32)
    vec = np.zeros(64)
    vec[3] = 2.0
    vec[17] = -1.2

    encoded = sae.encode(vec)
    zero_fraction = float(np.sum(encoded == 0.0)) / len(encoded)
    assert zero_fraction >= 0.45

    reconstructed = sae.reconstruct_and_align(vec)
    assert np.isclose(np.linalg.norm(reconstructed), 1.0, atol=1e-5)


def test_mode_engine_dep_and_profile_override():
    base = [0.0] * 1536
    user = [0.0] * 1536
    user[5] = 2.5
    delta = dep_engine.compute_delta(base, user)
    assert len(delta) == 1536
    assert abs(sum(abs(x) for x in delta)) > 0.0

    low_conf = IntentResult(intent=IntentType.ANALYSIS, mode=ModeType.GLOBAL, confidence=0.7)
    mode = select_mode(low_conf, {"base_embedding": base, "user_embedding": user})
    assert mode == ModeType.PERSONAL

    preferred = select_mode(
        IntentResult(intent=IntentType.TASK, mode=ModeType.PERSONAL, confidence=0.75),
        {"preferred_mode": "GLOBAL"},
    )
    assert preferred == ModeType.GLOBAL
    assert "GLOBAL mode" in get_mode_prompt(ModeType.GLOBAL)
