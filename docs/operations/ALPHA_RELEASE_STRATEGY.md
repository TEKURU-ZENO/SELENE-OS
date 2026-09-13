# Alpha Release Strategy: SELENE OS v0.1.3

## 1. Executive Summary
This document outlines the strategy for the Alpha v0.1.3 release of SELENE OS. As an alpha release, the primary goal is validating the 10-layer cognitive architecture, specifically the LangGraph state machine orchestration and memory stratification.

## 2. Release Goals and Scope
- Deploy a stable version of the 10 layers.
- Validate hybrid search (BM25 + FAISS + BGE-2 reranking).
- Gather metrics on Critic Agent (Layer 6) statistical validation.
- Test the HitL (Human-in-the-Loop) mutation locks.

## 3. Feature Completeness Matrix

| Layer | Component | Status | Notes |
|-------|-----------|--------|-------|
| 0 | Ingress Router | Complete | FastAPI + WebSocket functioning |
| 1 | Intent Decomposer | Complete | LLM decomposition working |
| 2 | Personalization (DEP) | Partial | SAE filtering in development |
| 3 | Context Engine | Complete | RRF 70/30 implemented |
| 4 | Planner | Complete | Multi-step plans generated |
| 5 | Orchestrator | Complete | LangGraph state machine active |
| 6 | Critic Agent | Complete | Shannon entropy, perplexity calculated |
| 7 | Execution Sandbox | Partial | E2B active, local fallback needs tuning |
| 8 | Governance | Complete | SSRF, Code blocking active |
| 9 | Memory | Partial | 5-layer stratification active, decay requires tuning |

## 4. Known Limitations
See `KNOWN_LIMITATIONS.md` for a comprehensive list. Key limitations include in-memory FAISS and lack of authentication.

## 5. Test Coverage Status
- **Backend Core**: 82% coverage
- **LangGraph Nodes**: 75% coverage
- **Memory Store**: 90% coverage
- **E2B Sandbox**: 60% coverage (mocks used extensively)
*Goal for Beta: 90% overall coverage.*

## 6. Release Checklist
- [ ] Ensure all tests pass (`pytest backend/testing`).
- [ ] Verify `docker-compose.yml` builds cleanly.
- [ ] Update `CHANGELOG.md` with v0.1.3 notes.
- [ ] Tag the release in GitHub.
- [ ] Trigger Render.com deployment.
- [ ] Verify `/health/live` and `/health/ready` on production.
- [ ] Run basic smoke tests via Next.js frontend.

## 7. Rollback Procedures
If critical issues are discovered post-deployment:
1. Revert the GitHub release tag.
2. In Render Dashboard, select the previous successful deployment and click "Rollback to this deploy".
3. If database migrations were applied, run `alembic downgrade -1` manually via CLI before rolling back code.

## 8. User Feedback Collection
For the Alpha phase, feedback will be collected via:
- GitHub Issues for bug tracking.
- Dedicated Discord channel for qualitative feedback.
- Telemetry data from the metrics endpoint.

## 9. Metrics to Track
- Intent Classification Accuracy (estimated via HitL corrections).
- Context Engine Reranking Latency.
- Critic Agent Rejection Rate (target < 15%).
- Memory Decay accuracy over 72 hours.

## 10. Path to Beta
To transition from Alpha to Beta, the following must be achieved:
- Persistent vector storage (e.g., pgvector or Milvus integration).
- Horizontal scaling capabilities.
- Full JWT authentication integration.
- 90% test coverage.
