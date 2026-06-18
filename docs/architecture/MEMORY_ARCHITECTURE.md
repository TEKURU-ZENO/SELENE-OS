# 📚 Memory Architecture

SELENE's memory is stratified to prevent cognitive corruption and context leakage.

## Memory Tiers

### 1. Working Memory (Short-Term)
The immediate context window for the current execution DAG. It holds the active `ExecutionReceipt` and intermediate reasoning steps. It is wiped when the session concludes.

### 2. Episodic Memory (Trace Logs)
Immutable logs of specific execution sequences. This forms the basis of the Replay System. Stored as `.selene` export bundles, maintaining strict cryptographic provenance.

### 3. Semantic Memory (Knowledge Base)
Abstracted facts about the user's environment, codebase, and preferences. Compressed and continuously refined by the Reflection Engine.

### 4. Procedural Memory (Skills & Rules)
The "How-To" memory. SELENE extracts successful execution patterns (e.g., how to correctly query a specific MCP) and stores them as procedural rules.
*   **ADR-014 Constraint**: The Reflection Engine cannot directly write to Procedural Memory. All procedural updates must be audited to prevent ungoverned cognitive drift.

### 5. Temporal / Intent Store
Tracks active, deferred, and abandoned intents over time, allowing SELENE to pick up where a user left off without losing the overarching strategic context.
