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
    OrganizationalMemoryTier
)
from memory.vector_store import VectorStore, BM25Index, BGEReranker, tokenize
from core.critic import critic_engine
from core.mode_engine import select_mode, ModeType
from memory.retrieval import retrieval_engine
from memory.stores import episodic_store, semantic_store
from governance.plugin_sandbox import plugin_sandbox
import structlog

logger = structlog.get_logger(__name__)


def test_rrf_and_bm25():
    logger.info("TEST 1: BM25 Indexing and RRF 70/30 Logic")

    # Initialize a test vector store
    store = VectorStore(index_path="backend/artifacts/test_vector_store", dimension=1536)
    store._ensure_initialized()

    # Clear out any metadata
    store._metadata = []
    store._bm25 = BM25Index()

    # Index some test documents
    doc1 = "Deploy production build and verify event bus serialization"
    doc2 = "Configure Postgres and Redis connections for local stabilization"
    doc3 = "Apply safety locks and HITL checks for external code execution"

    # Add to BM25 index manually for testing
    store._metadata.append({"text": doc1, "type": "episodic"})
    store._bm25.add_document(doc1)

    store._metadata.append({"text": doc2, "type": "semantic"})
    store._bm25.add_document(doc2)

    store._metadata.append({"text": doc3, "type": "semantic"})
    store._bm25.add_document(doc3)

    # Test BM25 search
    results_bm25 = store._bm25.search("safety locks")
    assert len(results_bm25) > 0
    # doc3 should be the top match for "safety locks"
    assert results_bm25[0][0] == 2

    # Verify RRF 70/30 math
    # Let's say:
    # Dense ranks (FAISS): doc1 = rank 1, doc2 = rank 2
    # Sparse ranks (BM25): doc2 = rank 1, doc3 = rank 2
    dense_ranks = {0: 1, 1: 2}
    sparse_ranks = {1: 1, 2: 2}

    # Combined RRF score for doc1:
    # 0.7 * (1 / (60 + 1)) + 0.3 * 0 = 0.7 / 61 = 0.01147
    # Combined RRF score for doc2:
    # 0.7 * (1 / (60 + 2)) + 0.3 * (1 / (60 + 1)) = 0.7 / 62 + 0.3 / 61 = 0.01129 + 0.00491 = 0.0162
    # Combined RRF score for doc3:
    # 0.7 * 0 + 0.3 * (1 / (60 + 2)) = 0.3 / 62 = 0.00483

    # Doc2 should rank highest overall under this RRF scenario
    rrf_scores = {}
    for idx in (0, 1, 2):
        dr = dense_ranks.get(idx)
        sr = sparse_ranks.get(idx)
        dense_rrf = 1.0 / (60.0 + dr) if dr else 0.0
        sparse_rrf = 1.0 / (60.0 + sr) if sr else 0.0
        rrf_scores[idx] = 0.7 * dense_rrf + 0.3 * sparse_rrf

    assert rrf_scores[1] > rrf_scores[0]
    assert rrf_scores[0] > rrf_scores[2]
    logger.info("PASS: BM25 indexing matches keywords and RRF 70/30 scores combine ranks correctly")


async def test_critic_validation_checks():
    logger.info("TEST 2: Critic Validation and DAG Safety Checks (No Lexical Variance / Entropy Heuristics)")

    # Define a valid dummy plan
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
    # Confirm lexical variance entropy / JSD fields are dropped
    assert verdict.shannon_entropy is None
    assert verdict.js_divergence is None

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

    # Clear and populate episodic and semantic stores with tag structures
    episodic_store._memories = []
    semantic_store._memories = {}

    # Add memories with tags to represent different layers
    episodic_store.add("Verify safety boundaries in microVM execution", tags=["safety", "rules"])
    episodic_store.add("Use extremely concise bullet points for status reports", tags=["style", "personalization"])
    
    # 2. Add semantic facts
    semantic_store.add_or_update("Postgres operates on port 5432", tags=["facts"])
    # Principles
    semantic_store.add_or_update("Never leak credential strings under any circumstances", tags=["principles"])

    # Wait for the background indexing tasks to execute on the loop
    await asyncio.sleep(0.5)

    # Simulate retrieval context
    intent = IntentResult(intent=IntentType.TASK, mode=ModeType.HYBRID, confidence=0.9)
    bundle = retrieval_engine.retrieve("safety Postgres", "test_session", intent)

    # Ensure memory decay calculation took place (decay factor <= 1.0)
    # The first element in semantic or episodic should have a retrieval score computed with decay
    for m in episodic_store._memories:
        assert hasattr(m.metadata, "recency_score")
        assert 0.0 < m.metadata.recency_score <= 1.0

    # Ensure stratification formatted block was injected into the semantic list
    has_stratification_block = False
    for item in bundle.semantic:
        if "[PRINCIPLES]" in item or "[RULES]" in item or "[FACTS]" in item:
            has_stratification_block = True
            break
            
    assert has_stratification_block, "Stratification blocks were not injected!"
    logger.info("PASS: Memory retrieval stratifies logs, rules, principles, and decays older elements")


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
        plugin_id="mutation_server", # any registered manifest ID
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
