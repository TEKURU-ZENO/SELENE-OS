# Architectural Decision Records (ADRs)

This document tracks the crucial architectural decisions made during the design and development of SELENE OS.

---

## ADR-001: LangGraph over Autogen/CrewAI

**Status:** Accepted
**Context:** SELENE required a framework to orchestrate complex multi-agent workflows and cognitive loops. Existing frameworks like Autogen or CrewAI were considered.
**Decision:** We chose LangGraph as the core orchestration engine (Layer 5).
**Consequences:** 
- Provides highly deterministic routing via conditional edges.
- Enforces strict state management using `TypedDict` (`SeleneState`), eliminating state drift.
- Allows fine-grained visualization of the cognitive nodes (intent, plan, critic, execute, etc.).
- Requires slightly more boilerplate than higher-level frameworks but offers absolute control over the graph topology.

---

## ADR-002: FAISS over Pinecone/Weaviate

**Status:** Accepted
**Context:** Layer 3 (Context Engine) needed a vector database to perform dense embeddings search for semantic memory retrieval.
**Decision:** We selected Meta's FAISS (Facebook AI Similarity Search) over managed SaaS alternatives (Pinecone) or heavier self-hosted systems (Weaviate).
**Consequences:**
- Zero-cost, in-process execution natively in Python.
- No network latency or external dependency for core memory operations.
- Requires managing local index persistence on disk, handled seamlessly via our volume mounts.
- Extremely fast for the scale of personal OS context windows.

---

## ADR-003: RRF Fusion over Simple Vector Search

**Status:** Accepted
**Context:** Relying solely on dense embeddings (FAISS) often missed exact keyword matches (e.g., variable names, specific IDs).
**Decision:** We implemented a Hybrid Search architecture using Reciprocal Rank Fusion (RRF). We combine FAISS (dense) and BM25 (sparse lexical search), weighted via RRF (α=0.7 dense, 0.3 sparse).
**Consequences:**
- Drastically improved recall across both conceptual queries and exact term lookups.
- Requires maintaining two separate indexes (BM25 token index and FAISS vector index).
- Slightly increased computational overhead, offset by the massive boost in retrieval accuracy, especially when followed by `BAAI/bge-reranker-base`.

---

## ADR-004: E2B over Direct Subprocess

**Status:** Accepted
**Context:** The AI agent (Layer 7) needs the ability to execute generated code to solve tasks, which presents severe security risks if run directly on the host machine.
**Decision:** We integrated E2B cloud microVMs as the primary execution sandbox.
**Consequences:**
- Maximum security isolation (network, compute, filesystem) from the host environment.
- Eliminates the risk of the agent accidentally deleting workspace files or exposing secrets.
- Introduces an external API dependency and potential latency.
- *Mitigation:* We implemented a local subprocess fallback with strict 30s timeouts and Governance blocking rules for offline/degraded environments.

---

## ADR-005: 5-Layer Memory Stratification

**Status:** Accepted
**Context:** Standard RAG pipelines treat all information equally, leading to bloated context windows and forgotten immediate instructions.
**Decision:** We adopted a 5-layer stratified memory system inspired by human cognitive psychology: working (≤1hr), episodic (≤24hr), semantic (≤7d), procedural (≤30d), and archival (>30d).
**Consequences:**
- Context injection is highly relevant to the temporal dimension of the task.
- Requires a background cron worker to apply exponential time-decay mathematics (`score × exp(-λ·Δt_hours)`) to demote memory records across layers over time.
- Highly efficient context windows that stay strictly within LLM token limits.

---

## ADR-006: Deterministic DAG & Cognitive Verification for Critic Validation

**Status:** Accepted (Updated from deprecated lexical variance heuristics)
**Context:** The system needed an automated, robust way to detect if a plan was flawed, missing dependencies, or ungrounded before executing risky operations. Measuring token lexical variance across temperatures was dropped as it reflects temperature diversity rather than plan soundness or hallucination.
**Decision:** We implemented Layer 6 (Critic Agent) using deterministic DAG graph validation (dependency resolution, capability bounds, objective size constraints) combined with LLM cognitive verification of verifiable success criteria and semantic sequence logic.
**Consequences:**
- Provides 100% deterministic interception of broken DAG dependencies and capability mismatches before code runs.
- Removes unreliable token entropy heuristics that falsely flagged valid high-diversity completions.
- Cleanly triggers the repair loop back to Layer 4 (Planner) or escalates to Layer 8 (HITL) with actionable diagnostics.

---

## ADR-007: FastAPI over Flask/Django

**Status:** Accepted
**Context:** The API ingress router (Layer 0) required a modern, highly concurrent web framework.
**Decision:** We selected FastAPI.
**Consequences:**
- Async-native architecture perfectly complements concurrent LLM requests and WebSocket streaming.
- Automatic generation of OpenAPI schemas.
- Deep integration with Pydantic, enforcing strict schema validation out-of-the-box for `SeleneState` and intents.

---

## ADR-008: PostgreSQL + Redis over MongoDB

**Status:** Accepted
**Context:** We needed storage solutions for user data, session states, and rate-limiting.
**Decision:** We chose a relational architecture (PostgreSQL) paired with in-memory caching (Redis), instead of a NoSQL document store (MongoDB).
**Consequences:**
- PostgreSQL guarantees relational integrity for complex user-role-permission structures and workflow pack tracking.
- Redis handles sliding-window rate limiting, WebSocket pub/sub, and ephemeral state caching efficiently.
- Standardized via `docker-compose.yml` for easy deployment.
