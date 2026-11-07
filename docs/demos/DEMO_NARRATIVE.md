# Demo Narrative for SELENE OS

## 1. Introduction

This narrative guides a presenter through a standard demonstration of SELENE OS. The objective is to highlight all 10 architectural layers working in harmony, emphasizing speed, cognitive validation, safety, and memory retrieval.

**Demo Scenario**: A researcher user interacts with SELENE to analyze a complex local repository, search the web for missing documentation, write an analysis script, and execute it securely.

## 2. Demo Environment Setup

- Ensure `docker-compose up` is running (FastAPI backend, Redis, Postgres).
- Start the Next.js frontend.
- Have a local directory `c:\Users\Dev Mehta\Desktop\SELENE` loaded as the workspace.
- Have a valid E2B API key configured for Layer 7 sandboxing.

## 3. Step-by-Step Walkthrough

### Phase 1: Ingress & Intent Classification (Layers 0, 1)

**User Input**: "Find the hybrid search RRF logic in our codebase, then write a script to benchmark its FAISS vs BM25 performance based on standard IR metrics found online."

**What to show**:
The frontend UI lighting up. The terminal logs showing the request hitting Layer 0 (FastAPI Ingress router).
**Talking Points**:
- "Notice how fast the request is received by Layer 0."
- "Layer 1 (Intent Decomposer) breaks this complex prompt into two distinct intents: code search, and external research + execution."

### Phase 2: Personalization & Context Engine (Layers 2, 3)

**What to show**:
Terminal logs outputting the Dynamic Embedding Profile (DEP) similarity score and the context retrieval results.
**Talking Points**:
- "Layer 2 checks my personal DEP. It sees I prefer technical, pythonic outputs (cosine-delta adaptation)."
- "Layer 3 (Context Engine) uses Reciprocal Rank Fusion (70% dense FAISS, 30% sparse BM25) reranked by BGE-2 to find `backend/memory/vector_store.py`."

### Phase 3: Planning & Criticism (Layers 4, 5, 6)

**What to show**:
A LangGraph visualizer (or debug UI) showing node transitions from `planner` to `critic`.
**Talking Points**:
- "Layer 4 generates a multi-step plan."
- "Before we execute, Layer 6 (Critic) validates the plan. It enforces deterministic DAG integrity and runs cognitive verification against verifiable success criteria to ensure plan soundness before dispatch."

### Phase 4: Execution & Governance (Layers 7, 8)

**What to show**:
The system prompting the user for approval to install benchmark dependencies.
**Talking Points**:
- "Layer 7 wants to run a benchmark script, but installing external PIP packages triggers a Layer 8 Governance HITL (Human-in-the-Loop) lock."
- "Observe the SSRF and shell protections active here."
*Presenter clicks 'Approve'*
- "The code now executes securely inside an E2B microVM, completely isolated from our local host."

### Phase 5: Memory Stratification (Layers 9)

**What to show**:
The final output presented to the user, and a background task saving to memory.
**Talking Points**:
- "The benchmark results are summarized."
- "Finally, Layer 9 stores this result in Working Memory. Over time, exponential decay ($S_{t} = S_0 \times \exp(-0.01 \cdot \Delta t)$) will transition important facts to Archival Memory, keeping the context window pristine."

## 4. Expected Outputs

- **Screenshots to Highlight**:
  - The clean Next.js chat interface.
  - The Layer 8 HITL Modal displaying risk levels and code diffs.
  - The LangGraph debug console showing the 10-layer trace.
  - A successful completion message with Mermaid visualization of the benchmark results.

## 5. Conclusion

This flow comprehensively demonstrates SELENE OS not merely as an LLM wrapper, but as a verifiable, cognitively constrained, and robust autonomous system.
