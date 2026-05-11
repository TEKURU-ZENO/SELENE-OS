# 🏛️ Architectural Decision Records (ADRs)

This document logs the "why" behind major structural decisions in SELENE.

## ADR-001: Separation of Planner and Executor
*   **Context**: LLMs cannot be trusted to self-regulate external tool usage natively.
*   **Decision**: Introduced the `CapabilityAdapter` and `PolicyGate`. Planners output abstract capabilities; the runtime handles the concrete MCP execution.
*   **Tradeoff**: Increased latency and system complexity.
*   **Implication**: Enables deterministic governance and tamper-evident replays.

## ADR-014: Reflection Engine Constraints
*   **Context**: Procedural memory drift occurs if models continually overwrite their own rules.
*   **Decision**: The Reflection Engine cannot directly write to Procedural Memory. All procedural updates must pass an `ACCEPTED` state threshold or a human audit.
*   **Tradeoff**: Slower autonomous learning.
*   **Implication**: Prevents ungoverned cognitive drift.

## ADR-023: Provenance Hashing
*   **Context**: Demos and execution traces must be verifiable.
*   **Decision**: All `ExecutionReceipts` are hashed before hitting the orchestrator.
*   **Tradeoff**: Overhead in serialization.
*   **Implication**: Eliminates silent failures and allows the Trust Dashboard to visually lock down if memory is tampered with.
