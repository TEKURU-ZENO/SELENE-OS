# Replay Forensics

## 1. Introduction

The Replay Forensics system is a core component of SELENE's operational transparency. It enables post-hoc analysis of cognitive decisions by capturing the exact LangGraph state at every node transition across the 10 Architectural Layers.

The primary purpose is to trace *why* SELENE took a specific action, validate Layer 6 Critic decisions (DAG dependency integrity, capability bounds, verifiable criteria), and provide regression detection via Golden Traces.

## 2. Trace Format and Structure

Traces are serialized snapshots of the `SeleneState` TypedDict defined in `backend/core/graph_state.py`. 
Each trace payload consists of:

```json
{
  "trace_id": "uuid4",
  "session_id": "user_session",
  "timestamp": "ISO8601",
  "node": "planner",
  "state_diff": {
    "intent": "Decomposed intent data...",
    "plan": ["Step 1", "Step 2"],
    "critic_scores": {
      "static_checks_passed": true,
      "cognitive_checks_passed": true,
      "critic_confidence": 0.95
    }
  },
  "llm_calls": [
    {
      "provider": "openai",
      "model": "gpt-4-turbo",
      "prompt_tokens": 450,
      "completion_tokens": 120,
      "latency_ms": 850
    }
  ]
}
```

## 3. Capturing Traces

Traces are emitted asynchronously by the Orchestrator (`backend/core/orchestrator.py`) using LangGraph's built-in state checking capability, wrapped in a forensic logger.

All transitions between nodes (e.g., `intent` → `context` → `planner`) trigger a trace capture, persisted in the PostgreSQL `forensic_traces` table.

## 4. Replaying and Analyzing Traces

Operators can replay a trace to simulate the cognitive flow:

```bash
# Replay a specific trace ID to debug a node failure
python -m selene.cli replay --trace-id f47ac10b-58cc-4372-a567-0e02b2c3d479
```

During a replay, external side-effects (Layer 7 sandbox execution) are mocked using the recorded outputs from the original trace, ensuring idempotency.

### 4.1 Invariant and DAG Analysis of Traces

Using Layer 6 deterministic and cognitive checks, forensics can identify plan divergence. If a plan failed, operators can inspect the DAG dependency validation issues and cognitive criteria evaluations recorded during execution to pinpoint faulty assumptions or broken prerequisites.

## 5. Golden Trace Validation

A Golden Trace is an idealized execution path for a benchmark task. During CI/CD pipelines, SELENE's current performance is compared against Golden Traces.

### 5.1 Comparing Traces for Regression Detection

When code changes (e.g., updating the RRF 70/30 hybrid search logic in `backend/memory/vector_store.py`), the CI pipeline runs a regression check:

1. Executes a benchmark query.
2. Captures the generated Trace $T_{new}$.
3. Compares $T_{new}$ against Golden Trace $T_{gold}$.
4. If structural similarity $< 0.95$ (cosine similarity of state embeddings), the build fails.

## 6. Integration with CI/CD Pipelines

In `testing/run_forensics.sh`, the pipeline asserts trace stability:
```yaml
test_forensics:
  stage: test
  script:
    - pytest backend/testing/test_forensics.py --run-golden-comparisons
    - pytest backend/testing/scenarios/test_blueprint_mathematics.py
```

## 7. Code References

- **State Definition**: `backend/core/graph_state.py`
- **Trace Persistence**: `backend/memory/memory_manager.py`
- **Forensic API**: `/api/v1/forensics/traces` in `backend/main.py`
- **Validation**: `backend/testing/test_forensics.py`
