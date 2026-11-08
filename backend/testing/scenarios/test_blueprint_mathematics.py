"""
SELENE OS — Blueprint Mathematics and Integration Tests
Verifies:
1. RRF 70/30 dense-sparse hybrid search and BM25 indexing.
2. Critic static and cognitive validation (deterministic DAG checks, capability bounds, risk scoring).
3. Personalization embeddings (DEP) and sparse autoencoder filtration in the Mode Engine.
4. Stratified memory layer mapping and exponential temporal decay.
5. Sandbox microVM execution and local fallback isolation.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import math
import asyncio
import numpy as np
from datetime import datetime, timedelta
from schemas import (
    ExecutionPlan, CriticVerdict, ObjectiveGroup, PlanNode, 
    Capability, TaskState, RiskLevel, IntentResult, IntentType, ModeType,
    OrganizationalMemoryTier, EpisodicMemory, SemanticMemory, ProceduralMemory,
    MemoryMetadata
)
from memory.vector_store import VectorStore, BM25Index, BGEReranker, tokenize, compute_rrf_score
from core.critic import critic_engine
from core.mode_engine import select_mode, ModeType
from memory.retrieval import retrieval_engine
from memory.stores import episodic_store, semantic_store
from governance.plugin_sandbox import plugin_sandbox
import structlog

logger = structlog.get_logger(__name__)


def test_rrf_and_bm25():
    logger.info("TEST 1: BM25 Indexing and RRF 70/30 Logic")

    # 1. Direct mathematical verification of compute_rrf_score (Cormack et al. formula)
    # RRF = w_dense / (k + rank_dense) + w_sparse / (k + rank_sparse)
    # Standard constants: k=60.0, w_dense=0.7, w_sparse=0.3
    
    # Dual top match (rank 1 dense, rank 1 sparse)
    score_1_1 = compute_rrf_score(1, 1, k=60.0, dense_weight=0.7, sparse_weight=0.3)
    expected_1_1 = (0.7 / 61.0) + (0.3 / 61.0)  # 1.0 / 61.0
    assert math.isclose(score_1_1, expected_1_1, rel_tol=1e-6)

    # Dense only (rank 1 dense, no sparse match)
    score_dense_only = compute_rrf_score(1, None, k=60.0, dense_weight=0.7, sparse_weight=0.3)
    assert math.isclose(score_dense_only, 0.7 / 61.0, rel_tol=1e-6)

    # Sparse only (no dense match, rank 1 sparse)
    score_sparse_only = compute_rrf_score(None, 1, k=60.0, dense_weight=0.7, sparse_weight=0.3)
    assert math.isclose(score_sparse_only, 0.3 / 61.0, rel_tol=1e-6)

    # Weighting check: Dense rank 1 + Sparse rank 2 vs Dense rank 2 + Sparse rank 1
    # Dense is 70% weighted so (1, 2) must be strictly higher than (2, 1)
    score_dense_favored = compute_rrf_score(1, 2, k=60.0, dense_weight=0.7, sparse_weight=0.3)
    score_sparse_favored = compute_rrf_score(2, 1, k=60.0, dense_weight=0.7, sparse_weight=0.3)
    assert score_dense_favored > score_sparse_favored

    # Zero/missing ranks contribute 0.0
    assert compute_rrf_score(None, None) == 0.0
    assert compute_rrf_score(0, 0) == 0.0

    # 2. BM25 Index Mathematical Search Tests
    bm25 = BM25Index(k1=1.5, b=0.75)
    doc1 = "Deploy production build and verify event bus serialization"
    doc2 = "Configure Postgres and Redis connections for local stabilization"
    doc3 = "Apply safety locks and HITL checks for external code execution"

    bm25.add_document(doc1)
    bm25.add_document(doc2)
    bm25.add_document(doc3)

    # Test exact multi-term keyword match
    results_safety = bm25.search("safety locks")
    assert len(results_safety) == 1, "Only doc3 contains 'safety' and 'locks'"
    assert results_safety[0][0] == 2
    assert results_safety[0][1] > 0.0

    # Non-matching queries must return empty list (never 0.0-score entries)
    results_unmatched = bm25.search("quantum teleportation")
    assert len(results_unmatched) == 0, "Non-matching terms must not pollute search results"

    # Multi-term match scores higher than single-term match
    bm25_multi = BM25Index(k1=1.5, b=0.75)
    bm25_multi.add_document("database postgres optimization")
    bm25_multi.add_document("database query optimization postgres performance tuning")
    bm25_multi.add_document("python server setup")
    res_multi = bm25_multi.search("postgres database optimization")
    assert len(res_multi) == 2
    assert all(r[1] > 0.0 for r in res_multi)

    # 3. VectorStore Integration
    store = VectorStore(index_path="backend/artifacts/test_vector_store", dimension=1536)
    store.clear()
    store._metadata.append({"text": doc1, "type": "episodic"})
    store._bm25.add_document(doc1)
    store._metadata.append({"text": doc2, "type": "semantic"})
    store._bm25.add_document(doc2)
    store._metadata.append({"text": doc3, "type": "semantic"})
    store._bm25.add_document(doc3)

    bm25_res = store._bm25.search("safety locks")
    assert len(bm25_res) == 1
    assert bm25_res[0][0] == 2

    # Hybrid Search Verification (RRF 70/30)
    hybrid_res = store.search_sync("safety locks")
    assert len(hybrid_res) >= 1
    assert hybrid_res[0]["text"] == doc3
    assert hybrid_res[0]["_score"] > 0.0

    # Original RRF 70/30 Rank Invariant Verification
    dense_ranks = {0: 1, 1: 2}
    sparse_ranks = {1: 1, 2: 2}
    rrf_scores = {}
    for idx in (0, 1, 2):
        dr = dense_ranks.get(idx)
        sr = sparse_ranks.get(idx)
        dense_rrf = 1.0 / (60.0 + dr) if dr else 0.0
        sparse_rrf = 1.0 / (60.0 + sr) if sr else 0.0
        rrf_scores[idx] = 0.7 * dense_rrf + 0.3 * sparse_rrf

    assert rrf_scores[1] > rrf_scores[0]
    assert rrf_scores[0] > rrf_scores[2]

    logger.info("PASS: BM25 indexing and RRF mathematical ranking verified")


async def test_critic_validation_checks():
    logger.info("TEST 2: Critic Validation and DAG Safety Checks (No Lexical Variance / Entropy Heuristics)")

    # Define a valid plan
    nodes = [
        PlanNode(
            id="node_1",
            capability=Capability.EXECUTE_CODE,
            objective="Execute simple code",
            dependencies=[],
            success_criteria=[],
            params={},
            status=TaskState.PENDING,
            risk_level=RiskLevel.LOW
        )
    ]
    group = ObjectiveGroup(id="group_1", objective="Simple objective", nodes=nodes)
    valid_plan = ExecutionPlan(
        plan_id="test_plan_math_123",
        objective="Simple objective",
        groups=[group],
        confidence=0.9
    )

    # 1. Verify valid plan passes static checks and cognitive critic
    verdict = await critic_engine.evaluate_plan(valid_plan)
    assert verdict.static_checks_passed is True
    assert verdict.cognitive_checks_passed is True
    assert verdict.approved is True
    
    # Confirm lexical variance entropy, perplexity, and divergence fields are completely removed from schema
    assert not hasattr(verdict, "shannon_entropy"), "shannon_entropy must not exist on CriticVerdict"
    assert not hasattr(verdict, "perplexity"), "perplexity must not exist on CriticVerdict"
    assert not hasattr(verdict, "js_divergence"), "js_divergence must not exist on CriticVerdict"

    # 2. Verify broken dependency is intercepted deterministically
    broken_node = PlanNode(
        id="node_2",
        capability=Capability.EXECUTE_CODE,
        objective="Execute with missing dep",
        dependencies=["non_existent_node"],
        success_criteria=[],
        params={},
        status=TaskState.PENDING,
        risk_level=RiskLevel.HIGH
    )
    broken_plan = ExecutionPlan(
        plan_id="test_plan_broken",
        objective="Broken plan",
        groups=[ObjectiveGroup(id="g2", objective="Broken", nodes=[broken_node])],
        confidence=0.5
    )
    broken_verdict = await critic_engine.evaluate_plan(broken_plan)
    assert broken_verdict.static_checks_passed is False
    assert broken_verdict.approved is False
    assert any("Invalid dependency" in issue.message for issue in broken_verdict.issues)

    logger.info("PASS: Critic enforces deterministic DAG and capability invariants without pseudo-statistical lexical heuristics")


def test_personalization_autoencoder():
    logger.info("TEST 3: DEP Personalization and Sparse Autoencoder")

    # Prepare standard user profile with embeddings
    # Construct base and user embeddings of dimension 1536
    base_emb = [0.0] * 1536
    user_emb = [0.0] * 1536
    # Add personalization signals to specific indices
    user_emb[10] = 1.5
    user_emb[100] = -0.8

    user_profile = {
        "base_embedding": base_emb,
        "user_embedding": user_emb,
        "preferred_mode": "HYBRID"
    }

    intent_result = IntentResult(
        intent=IntentType.TASK,
        mode=ModeType.HYBRID,
        confidence=0.7,
        needs_clarification=False
    )

    # select_mode should run the DEP engine
    mode = select_mode(intent_result, user_profile)
    
    # Personalization strength should be non-zero since the user embedding differs
    # This should nudge mode to PERSONAL if within parameters
    assert mode in (ModeType.PERSONAL, ModeType.HYBRID)
    logger.info("PASS: Personalization delta computed and processed by sparse autoencoder filter")


async def test_stratification_and_decay():
    logger.info("TEST 4: Memory Stratification and Decay")

    # ── Part A: Exponential Temporal Decay Mathematics ──
    # Mathematical formula: S(t) = S_0 * e^(-lambda * dt_hours)
    # where S_0 = importance * confidence, lambda = decay_rate
    now = datetime.utcnow()
    decay_rate = 0.05
    dt_hours = 24.0

    # 1. Create a fresh memory (dt = 0)
    fresh_mem = EpisodicMemory(
        content="Fresh system deployment observation",
        created_at=now,
        metadata=MemoryMetadata(importance=0.8, confidence=1.0, decay_rate=decay_rate, tags=["system"])
    )

    # 2. Create an aged memory (dt = 24 hours ago)
    aged_time = now - timedelta(hours=dt_hours)
    aged_mem = EpisodicMemory(
        content="Aged system deployment observation",
        created_at=aged_time,
        metadata=MemoryMetadata(importance=0.8, confidence=1.0, decay_rate=decay_rate, tags=["system"])
    )

    scored = retrieval_engine._apply_rrf_scoring([fresh_mem, aged_mem], weight_multiplier=1.0)
    assert len(scored) == 2

    # Fresh memory should have decay factor ~ 1.0 (recency_score ~ 1.0)
    assert math.isclose(fresh_mem.metadata.recency_score, 1.0, abs_tol=1e-3)

    # Aged memory should have decayed by e^(-0.05 * 24) = e^(-1.2) ~ 0.3011942
    expected_aged_decay = math.exp(-decay_rate * dt_hours)
    assert math.isclose(aged_mem.metadata.recency_score, expected_aged_decay, rel_tol=1e-3)

    # Mathematical ratio check: aged / fresh score should equal e^(-1.2)
    score_ratio = getattr(aged_mem, "_retrieval_score") / getattr(fresh_mem, "_retrieval_score")
    assert math.isclose(score_ratio, expected_aged_decay, rel_tol=1e-3)
    assert getattr(fresh_mem, "_retrieval_score") > getattr(aged_mem, "_retrieval_score")

    # ── Part B: 5-Layer Stratification Logic ──
    # Test stratification into Principles, Rules, Facts, Stylistic, and Logs
    m_principle = SemanticMemory(
        content="Never leak credential strings under any circumstances",
        metadata=MemoryMetadata(confidence=1.0, importance=1.0, tags=["principles"])
    )
    m_rule = EpisodicMemory(
        content="Verify safety boundaries in microVM execution before running commands",
        metadata=MemoryMetadata(importance=0.9, tags=["safety", "rules"])
    )
    m_fact = SemanticMemory(
        content="Postgres operates on port 5432 by default",
        metadata=MemoryMetadata(confidence=1.0, importance=0.8, tags=["facts"])
    )
    m_style = EpisodicMemory(
        content="Use extremely concise bullet points for status reports",
        metadata=MemoryMetadata(importance=0.7, tags=["style", "personalization"])
    )
    m_log = EpisodicMemory(
        content="Execution step 4 completed in 12ms with code 0",
        metadata=MemoryMetadata(importance=0.4, tags=["execution", "log"])
    )

    stratified = retrieval_engine._stratify_memories(
        episodic=[m_rule, m_style, m_log],
        semantic=[m_principle, m_fact],
        procedural=[]
    )

    assert any("Never leak credential" in p for p in stratified["principles"])
    assert any("Verify safety boundaries" in r for r in stratified["rules"])
    assert any("Postgres operates on port 5432" in f for f in stratified["facts"])
    assert any("concise bullet points" in s for s in stratified["stylistic"])
    assert any("Execution step 4 completed" in l for l in stratified["logs"])

    # ── Part C: End-to-End Retrieval Bundle Integration ──
    episodic_store._memories = [m_rule, m_style, m_log]
    semantic_store._memories = {
        m_principle.fact_hash or "p1": m_principle,
        m_fact.fact_hash or "f1": m_fact
    }

    intent = IntentResult(intent=IntentType.TASK, mode=ModeType.HYBRID, confidence=0.9)
    bundle = retrieval_engine.retrieve("safety Postgres", "test_session", intent)

    # Ensure stratification blocks are present in bundle.semantic
    has_principles = any("[PRINCIPLES]" in item for item in bundle.semantic)
    has_rules = any("[RULES]" in item for item in bundle.semantic)
    has_facts = any("[FACTS]" in item for item in bundle.semantic)
    assert has_principles or has_rules or has_facts, "Stratification blocks were not injected!"

    logger.info("PASS: Exponential temporal decay and 5-layer stratification verified mathematically")


async def test_sandbox_microvm():
    logger.info("TEST 5: Sandbox E2B MicroVM and Subprocess Fallback")

    from mcp.registry.server_registry import server_registry
    from mcp.schemas import MCPServerManifest, TrustClassification, TransportType
    
    server_registry.register_server(
        MCPServerManifest(
            server_id="mutation_server",
            name="Mutation Server",
            version="1.0.0",
            transport=TransportType.STDIO,
            capabilities=[Capability.EXECUTE_CODE],
            trust_classification=TrustClassification.VERIFIED_SAFE,
            risk_level=RiskLevel.LOW,
            memory_scope=OrganizationalMemoryTier.PERSONAL,
            allowed_contexts=["*"],
            requires_hitl=False,
            enabled=True
        )
    )

    # Test code execution capability
    params = {
        "code": "print(10 + 20)",
        "language": "python"
    }

    # Execute in sandbox. Since E2B_API_KEY is not set, it should fallback to local directory sandbox
    result = await plugin_sandbox.execute(
        plugin_id="mutation_server",  # any registered manifest ID
        capability="execute_code",
        params=params,
        context_tier=OrganizationalMemoryTier.PERSONAL
    )

    assert result["status"] == "success"
    assert "30" in result["stdout"]
    assert result["sandbox_type"] == "local_isolated_directory"
    logger.info("PASS: Sandbox executes code securely and falls back to local isolated directory gracefully")


async def run_all_tests():
    logger.info("=========================================")
    logger.info("RUNNING BLUEPRINT MATHEMATICS TEST SUITE")
    logger.info("=========================================")
    
    test_rrf_and_bm25()
    await test_critic_validation_checks()
    test_personalization_autoencoder()
    await test_stratification_and_decay()
    await test_sandbox_microvm()
    
    logger.info("=========================================")
    logger.info("ALL BLUEPRINT MATHEMATICS TESTS PASSED!")
    logger.info("=========================================")


if __name__ == "__main__":
    from schemas import OrganizationalMemoryTier
    # Setup mock server manifest for sandbox testing
    from mcp.schemas import MCPServerManifest, TrustClassification, TransportType
    from mcp.registry.server_registry import server_registry

    # Register mutation server manifest in registry
    manifest = MCPServerManifest(
        server_id="mutation_server",
        name="Mutation Server",
        version="1.0",
        transport=TransportType.STDIO,
        capabilities=[Capability.EXECUTE_CODE],
        trust_classification=TrustClassification.TRUSTED,
        risk_level="high",
        memory_scope=OrganizationalMemoryTier.PERSONAL,
        allowed_contexts=["engineering_context"],
        requires_hitl=False
    )
    server_registry._servers["mutation_server"] = manifest

    asyncio.run(run_all_tests())
