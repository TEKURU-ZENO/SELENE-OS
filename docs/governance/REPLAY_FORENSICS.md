# 🕵️‍♂️ Replay Forensics

This document defines the structural mechanics of the SELENE Replay System and the `.selene` bundle format.

## 1. Replay Structure
Replays are not raw token streams; they are structured Directed Acyclic Graph (DAG) traces detailing the exact cognitive steps taken by the Planner, the Critic, and the Execution Engine.

## 2. Provenance Hashing
Every execution receipt is hashed using SHA-256 before being attached to the `ExecutionReceipt` object in memory. 
`hash(payload + timestamp + trust_classification + environment_state)`
This ensures tamper detection. If an external system or man-in-the-middle alters the receipt before it hits the Event Bus, the frontend will trigger a `PROVENANCE COMPROMISED` lockdown.

## 3. The `.selene` Bundle Structure
A `.selene` file is a JSON payload containing the entire forensic snapshot of a session. It includes:
*   `replay_schema_version`: e.g., "1.0.0"
*   `runtime_version`: e.g., "selene-alpha-0.1.3"
*   `trace_classification`: "nominal", "adversarial", "forensic", "governance_failure"
*   `provenance_hash`: The root hash of the session trace.
*   `governance_snapshot`: The exact policies active during execution.
*   `redaction_summary`: Confirmation of PII stripping.
*   `replay_manifest`: The list of `CognitiveStep` objects.

## 4. Redaction Pipeline
Before a `.selene` bundle is generated, the Redaction Pipeline scrubs sensitive keys, PII, and raw file payloads, leaving only the structural metadata necessary for forensic replay.
