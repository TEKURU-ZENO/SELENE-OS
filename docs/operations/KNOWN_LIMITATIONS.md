# Known Limitations in SELENE OS (Alpha)

## 1. Overview
As SELENE OS is currently in an Alpha stage (v0.1.3), several architectural, functional, and environment-specific limitations exist. This document tracks these known issues to inform developers and operators.

## 2. Vector Store Persistence
- **Limitation**: The FAISS vector store is entirely in-memory.
- **Impact**: Upon application restart, the index must be rebuilt from the PostgreSQL database. This increases startup time significantly as the dataset grows.
- **Workaround**: We plan to migrate to pgvector or Milvus for persistent embeddings in the Beta release.

## 3. External API Dependencies
- **Embeddings**: Generating embeddings requires an active `OPENAI_API_KEY`. If absent, the system falls back to zero vectors, destroying semantic search capabilities.
- **E2B Sandbox**: The Execution Sandbox (Layer 7) relies on the `E2B_API_KEY`. While a local subprocess fallback exists, it is limited to a 30s timeout and lacks containerized isolation.

## 4. Model Loading Overhead
- **BGE Reranker**: On first startup, the Context Engine downloads the `BAAI/bge-reranker-base` model (~400MB) from HuggingFace. This delays readiness probes.
- **Impact**: Deployments in air-gapped environments or those with slow internet connections will experience delayed startup.

## 5. Architectural Scalability
- **Single-Process Limitation**: The current orchestration state machine (LangGraph) and memory management operate within a single process.
- **Impact**: The application cannot be horizontally scaled without introducing state inconsistencies in memory layers.

## 6. Security and Authentication
- **No Authentication**: The Alpha release lacks user authentication (e.g., JWT). All endpoints are open.
- **Frontend**: The Next.js frontend acts as a read-only demo and cannot create new sessions securely.
- **Governance Layer**: While Layer 8 blocks SSRF and shell commands, advanced prompt injections have not been fully mitigated.

## 7. Memory Management
- **Transient Conversation History**: Conversation history across restarts is not fully persistent. The episodic and working memory layers do not reliably restore state after a reboot.
- **Memory Decay**: The exponential temporal decay function ($\lambda=0.01$) needs extensive tuning, as memories currently fade too rapidly.

## 8. Windows-Specific Issues
For developers operating on Windows:
- **CRLF Warnings**: Git checkouts may produce CRLF line-ending warnings affecting bash scripts in the `sandbox/` environment.
- **Pycache Noise**: `__pycache__` directories may occasionally interfere with hot-reloading in the backend.

## 9. Dependency Warnings
- **Pydantic V1 Compatibility**: Python 3.14 environments throw Pydantic V1 compatibility warnings due to upstream dependencies in LangChain/LangGraph.
- **Resolution**: A refactor to Pydantic V2 is scheduled for the Beta cycle.

## 10. HitL Constraints
The Human-in-the-Loop (HitL) mutation lock pauses the LangGraph execution. If the human operator does not respond within the Redis timeout window (1 hour), the task is discarded without a grace period.
