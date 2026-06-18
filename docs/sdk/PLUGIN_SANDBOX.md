# 🧱 Plugin Sandbox

All plugins and MCP servers interacting with SELENE must adhere to strict sandbox rules.

## 1. Prohibited Actions
- Bypassing the `PolicyGate` execution pathway.
- Writing raw data directly into SELENE's Episodic or Procedural Memory stores.
- Accessing cross-domain contexts (e.g., a personal tool reading corporate memory tiers).

## 2. Memory Boundaries
Plugins are restricted to the `MemoryScope` defined in their manifest. The `ContextValidator` enforces this strictly.

## 3. Governance Requirements
Plugins operating in `RESTRICTED` or `EXPERIMENTAL` classifications must handle asynchronous executions natively, as the Policy Gate will actively insert HITL pauses before allowing their actions to complete.

## 4. Replay Expectations
Plugins must support replay fidelity. If a tool's output cannot be deterministically cached or replayed, it will severely penalize its Trust Score during Capability Routing.
