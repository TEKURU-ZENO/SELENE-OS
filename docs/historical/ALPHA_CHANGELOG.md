# SELENE OS Alpha Changelog

This document tracks the historical progression of the SELENE OS Alpha releases, detailing major architectural shifts, new cognitive layers, and core feature implementations.

---

## v0.1.0: Initial Scaffolding
**Date:** Early August 2026
**Commit Hash:** `a1b2c3d`

The foundation of the SELENE project. This release established the basic plumbing and structural boundaries of the OS.

**Features:**
- **Layer 0:** Implemented the FastAPI skeleton with basic REST endpoints.
- **Layer 5:** Drafted the initial LangGraph state machine structure with basic node routing.
- **Memory Stubs:** Created empty interface classes for memory subsystems, setting the stage for future integration.
- **Core Loop:** Basic prompt-in, text-out workflow to validate the backend architecture.

---

## v0.1.1: Alpha Hardening
**Date:** Mid August 2026
**Commit Hash:** `f8e9d0a`

Focus shifted heavily toward security, observability, and infrastructure robustness.

**Features:**
- **Observability:** Added robust structured logging across all components.
- **Infrastructure:** Created `docker-compose.yml` encapsulating FastAPI, PostgreSQL, and Redis.
- **Health Checks:** Implemented `/health/live`, `/health/ready`, and `/health/metrics` endpoints for Kubernetes compatibility.
- **Layer 8 (Governance):**
  - Implemented SSRF (Server-Side Request Forgery) protection by validating outbound URLs against internal CIDR blocks.
  - Added Human-In-The-Loop (HITL) locks, pausing the LangGraph state for sensitive mutations.
  - Implemented strict shell blocking (preventing `shell=True` and blocking risky bash commands).

---

## v0.1.2: Core Implementation
**Date:** Late August 2026
**Commit Hash:** `b4c5d6e`

The "brain" of SELENE comes online. This release connected the cognitive nodes, forming a true autonomous loop.

**Features:**
- **Layer 5 (Orchestrator):** Finalized the LangGraph 10-node state machine (intent → context → planner → critic → capability → execute → validation → hitl → reflection → memory).
- **Layer 1 (Intent Engine):** Integrated LLM-based intent classification to route tasks accurately based on user prompts.
- **Layer 4 (Planner):** Built the multi-step plan generation system, capable of mapping intents to actionable plugins/tools.

---

## v0.1.3: Blueprint Mathematics
**Date:** Early September 2026
**Commit Hash:** `7a8b9c0`

The most technically complex release, implementing the advanced mathematical and statistical models that differentiate SELENE from standard LLM wrappers.

**Features:**
- **Layer 2 (Personalization/DEP):** Implemented Dynamic Embedding Profiles (DEP) using cosine-delta personalization (`cos(DEP_current, DEP_new) < 0.85 → adapt mode`), filtered through Sparse Autoencoders.
- **Layer 3 (Context Engine):** Shipped Reciprocal Rank Fusion (RRF 70/30 hybrid search). Combines BM25 (sparse) + FAISS (dense), followed by a final re-rank pass using `BAAI/bge-reranker-base`.
- **Layer 6 (Critic Agent):** Integrated robust statistical validation for LLM outputs. Calculates Shannon entropy `H(p) = -Σ p_i·log₂(p_i)`, perplexity `2^H`, and Jensen-Shannon divergence `DJS = ½DKL(P||M) + ½DKL(Q||M)` to detect hallucinations.
- **Layer 7 (Execution Sandbox):** Finalized integration with E2B microVMs for secure cloud execution, with a seamless fallback to localized subprocess execution (30s timeout).
- **Layer 9 (Memory):** Released the 5-layer stratification model (working, episodic, semantic, procedural, archival) combined with an exponential temporal decay algorithm: `score × exp(-λ·Δt_hours)` where default `λ=0.01`.
