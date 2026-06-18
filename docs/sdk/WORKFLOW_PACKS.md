# 📦 Workflow Packs

Workflow packs define reusable DAG topologies for common cognitive pathways.

## 1. Shared Workflows
Workflow templates define the sequence of generic capability execution (e.g., `READ_ISSUE -> DRAFT_SUMMARY -> NOTIFY_USER`). They are abstracted away from specific MCP implementations.

## 2. HITL Templates
Packs can specify predefined HITL interruption points. For example, the `developer_release` pack injects a hard pause before `EXECUTE_DRAFT` is allowed to proceed, regardless of the trust classification of the active MCP.

## 3. Telemetry Expectations
Packs must annotate which nodes are considered "Governance Impactful" so the Cognitive Flight Recorder can correctly highlight them during playback.
