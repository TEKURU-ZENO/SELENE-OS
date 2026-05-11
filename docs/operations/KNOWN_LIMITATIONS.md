# 🌙 SELENE OS — Alpha Known Limitations

*Version: v0.1.3 (Alpha Operational Freeze)*

This is not a marketing document. This is an operational reality check. Do not mistake the following limitations for architectural flaws; they are the intentional bounds of the alpha deployment.

## ⚠️ 1. Unsupported Workflows
*   **Multi-Agent Swarming**: SELENE currently operates as a singular, governed cognitive entity. It does not spawn sub-agents to solve parallel tasks.
*   **Long-Running Autonomous Loops**: The orchestrator is explicitly configured to cap planning loops to 5 steps to prevent runaway resource consumption.
*   **Live Database Mutations**: Database connections are strictly `READ_ONLY` in alpha. Any `WRITE` attempt will trigger an automatic governance denial.

## 🔌 2. Unstable Connectors
*   **Slack MCP**: The `send_direct_message` capability occasionally times out due to async event loop mismatches. This triggers the Cascading Fallback logic.
*   **Jira MCP**: Context compression struggles with Jira issues containing over 50 comments, potentially triggering an Attention Fatigue denial.

## 🔄 3. Known Replay Edge Cases
*   **Asynchronous Race Conditions**: If a human interrupts (HITL) at the exact millisecond a fallback is activated, the Replay Integrity Hash will fail, resulting in a false `PROVENANCE COMPROMISED` lockdown. This is a known UI sync issue, not a core security breach.
*   **.selene Bundle Size**: Extremely long traces may generate `.selene` export bundles exceeding 5MB, which the frontend currently struggles to parse in real-time.

## 🛑 4. False-Positive Governance Conditions
*   **Aggressive Context Firewalls**: The current policy gate (`release_workflow`) is overly strict. If you ask SELENE to draft a release note that casually references a marketing asset, it may trigger a Cross-Domain Blocked denial.
*   **Attention Fatigue Escalation**: The system penalizes rapid context switching. If you rapidly switch tabs during a test session, SELENE will assume cognitive overload and suppress proactive suggestions. 

## ⚖️ 5. Degraded-Trust Behaviors
If SELENE enters a "Degraded Trust" state (e.g., due to repeated fallback routing):
*   It will automatically mandate HITL for *all* external interactions, even read-only APIs.
*   Expect a massive increase in interruption frequency during degraded states.
