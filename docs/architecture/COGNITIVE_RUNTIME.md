# 🧠 Cognitive Runtime Specification

## The Core Loop
The SELENE Cognitive Runtime operates on a continuous, interruptible LangGraph DAG:
`Observe -> Decide -> Plan -> Verify -> Execute -> Learn`

## 1. The Planner
The Planner generates intent. It does not select specific tools. It maps user requests and environmental signals to abstract `Capabilities`.

## 2. The Critic
The Critic evaluates the Planner's intent against the `LearningPolicyEngine`. It scores the plan for cognitive friction and alignment with user preferences.

## 3. Capability Resolution & DAG Routing
The runtime dynamically maps capabilities to connected MCP servers using an adaptive scoring engine based on:
- Capability Match
- Provider Trust Score
- Historical Latency
- Replay Fidelity Support

## 4. Repair Loops & Cascading Fallbacks
If a selected provider fails (e.g., timeout, connection refused), the orchestrator triggers a Repair Loop. The `FallbackStrategy` automatically reroutes the capability to the next highest-scoring provider, logging the `confidence_drop` and `fallback_depth`.

## 5. HITL Flow
Any action that violates the Policy Gate (e.g., writing to an external system, operating in a Degraded Trust state) triggers a `PAUSED` outcome. The DAG execution is suspended, returning control to the human Executive Layer.
