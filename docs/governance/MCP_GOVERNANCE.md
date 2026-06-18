# 🌐 MCP Governance

This document outlines how SELENE strictly regulates interoperability via the Model Context Protocol (MCP).

## 1. Server Manifests
Every external integration must provide an `MCPServerManifest`. This defines the capabilities (e.g., `READ_DOCUMENT`, `NOTIFY_USER`), the transport layer (e.g., `stdio`), and the inherent risk level of the server.

## 2. Trust Classifications
MCP Servers are tagged within the Server Registry with a strict `TrustClassification`:
*   `VERIFIED_SAFE`
*   `TRUSTED`
*   `RESTRICTED`
*   `EXPERIMENTAL`
*   `BLOCKED`

## 3. Capability Routing
The Planner requests abstract capabilities. The `ScoringEngine` maps these capabilities to MCP servers based on a combined score of: Provider Trust, Replay Fidelity Support, Context Alignment, and Latency.

## 4. Sandboxing & Context Validation
Before an MCP executes, the `ContextValidator` ensures the current session context is allowed to interact with the target MCP (e.g., a "personal" workspace context cannot route data to a "corporate_slack" MCP).

## 5. Interoperability Rules
- No raw tool execution bypasses the Policy Gate.
- All writes require HITL unless the MCP is `VERIFIED_SAFE` and the action is deemed low-risk by the Policy Gate.
