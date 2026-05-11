# ⚖️ Governance Model

This document defines the trust blueprint for SELENE OS.

## 1. The Policy Gate
The absolute barrier between Cognition and Execution. Every execution request must pass through `PolicyGate.evaluate_execution_request()`. It verifies context bounds, requested capabilities, and the current trust state before allowing the execution to proceed.

## 2. Trust Classifications
External integrations (MCPs) are strictly classified:
- `VERIFIED_SAFE`: Audited, low-risk, deterministic.
- `TRUSTED`: Approved internal tools.
- `RESTRICTED`: Limited contexts, mandates HITL for writes.
- `EXPERIMENTAL`: Isolated sandbox only.
- `BLOCKED`: Explicitly denied.

## 3. Cognitive Restraint
SELENE operates on the principle of minimal necessary action. The `AttentionBudget` module monitors user context switching. If cognitive load is `HIGH`, SELENE will deliberately downgrade its proactivity tier and suppress non-critical suggestions, logging a `Suggestion Withheld` event.

## 4. Replay Integrity & Provenance
Every execution generates a `ExecutionReceipt`. This receipt is injected with a SHA-256 provenance hash. Any attempt to alter the receipt downstream (e.g., during a Tampering Attack) will cause the Validation Normalizer to trigger a `PROVENANCE COMPROMISED` lockdown.

## 5. Denial Philosophy
Denials are not errors; they are successful governance events. A `DENIED` outcome explicitly documents *why* the action was stopped (e.g., privacy isolation, memory sandboxing) and preserves this explanation in the Cognitive Flight Recorder.
