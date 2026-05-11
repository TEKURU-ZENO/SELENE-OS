# 📜 Alpha Changelog

This log tracks the evolution of SELENE OS during the Alpha phase.

## [v0.1.3] - 2026-05-11
### Frozen
- Core architecture and UI terminology frozen for Internal Operator Sessions.
### Added
- "Why am I seeing this?" panel to the Cognitive Flight Recorder for empathetic human-in-the-loop explanations.
- Operational Reliability Panel (SLOs) tracking replay integrity and lease recovery success.
- Immutable Session IDs and Trace IDs injected into the UI header.
- Dynamic `.selene` export functionality for cognitive trace sharing.

## [v0.1.2] - 2026-05-10
### Added
- Adversarial Trace Matrix implementation (`tampering-attack`, `cascading-fallback`, `attention-fatigue`).
- Dynamic scenario selector for Trust Dashboard simulations.
- Provenance lockdown visualization (`PROVENANCE COMPROMISED`).

## [v0.1.1] - 2026-05-09
### Changed
- Refactored `CapabilityAdapter` to map Planners to MCP abstract tools.
- Expanded `ExecutionReceipt` schema to support provenance hashing.

## [v0.1.0] - 2026-05-08
### Initial
- Core LangGraph Orchestrator deployed.
- Foundational `PolicyGate` integration.
