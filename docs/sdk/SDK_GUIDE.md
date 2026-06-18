# 🛠️ SDK Guide

This guide details how developers can extend SELENE's capabilities by building governed integrations.

## 1. Registering Capabilities
Capabilities must be registered as abstract verbs, not specific tool names. 
*   **Correct**: `Capability.READ_DOCUMENT`
*   **Incorrect**: `Tool.READ_GITHUB_PR`

## 2. Defining Manifests
When exposing an MCP server to SELENE, you must provide a manifest that clearly defines memory scopes and risk levels.
```python
manifest = MCPServerManifest(
    server_id="custom_tool",
    name="Custom Plugin",
    version="1.0.0",
    transport=TransportType.STDIO,
    capabilities=[Capability.PROCESS_DATA],
    trust_classification=TrustClassification.EXPERIMENTAL,
    risk_level=RiskLevel.LOW,
    memory_scope=OrganizationalMemoryTier.WORKSPACE,
    allowed_contexts=["data_analysis"]
)
```

## 3. Exposing MCP Tools
Tools exposed via MCP should return structured JSON. The SELENE `ReceiptAdapter` will automatically normalize these responses into standard `ExecutionReceipts`.

## 4. Handling Receipts
Ensure your tools return a deterministic output where possible, as SELENE hashes the output payload for provenance verification. If your tool returns highly volatile data (e.g., precise timestamps in the body), you must configure custom redaction rules to prevent false tamper alarms.
