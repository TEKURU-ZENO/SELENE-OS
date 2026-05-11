# 🌙 SELENE OS — Architecture Overview

## Philosophy
SELENE (Strategic Executive Layer for Everyday Navigation & Execution) is a **Cognitive Operating Platform**. It is not an autonomous agent wrapper; it is governed infrastructure designed to enforce restraint, maintain deterministic replayability, and ensure explainable interoperability.

## Cognitive Separation Architecture
The core innovation of SELENE is the strict separation between **Cognitive Intent** (the Planner) and **Execution Reality** (MCP Runtime). 
1. The **Planner** reasons only in abstract capabilities (e.g., `READ_DOCUMENT`, `NOTIFY_USER`).
2. The **Capability Adapter** translates these abstractions into concrete tool routes.
3. The **Policy Gate** evaluates the route against the current Trust Classification.
4. The **Execution Engine** runs the action and returns a cryptographically hashed receipt.

This ensures the brain never directly touches the outside world without passing through a governance firewall.

## System Boundaries
- **Inner Loop**: Reflection, Planner, Critic, Memory Consolidation. (High Trust)
- **The Membrane**: Policy Gate, Validation Normalizer. (Strict Governance)
- **Outer Loop**: MCP Servers, External APIs, File Systems. (Zero Trust Default)

## Orchestration Model
SELENE uses LangGraph to manage the cognitive DAG (Directed Acyclic Graph). This guarantees that every thought process follows a deterministic, interruptible, and resumeable pathway. If a Human-In-The-Loop (HITL) pause occurs, the state is serialized and held indefinitely without context degradation.
