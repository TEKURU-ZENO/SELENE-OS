# 📊 SLOs & Reliability

SELENE treats "trust" not as a subjective feeling, but as a measurable engineering standard. These Service Level Objectives (SLOs) dictate platform health.

| Metric | Target | Description |
| :--- | :--- | :--- |
| **Replay Integrity Accuracy** | 100% | Cryptographic verification of every trace step. |
| **Lease Recovery Success** | >99.9% | System successfully resumes DAG after HITL suspension. |
| **HITL Enforcement Reliability** | 100% | Policy Gate never allows external writes without human approval. |
| **Cross-Context Leakage** | 0 tolerated | Memory bounds are strictly isolated between trust classifications. |
| **Reflection False Acceptance Rate** | <1% | Procedural drift correctly blocked by the Learning Engine. |

## Measuring Operational Performance
*   **Fallback Depth**: Tracked on every cascading capability reroute. High depth indicates primary provider instability.
*   **Confidence Erosion**: The drop in execution confidence over routing hops.
*   **Time-to-Stable-Resolution**: How fast the system resolves a request after encountering an execution failure.
