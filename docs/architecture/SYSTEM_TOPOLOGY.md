# 🗺️ System Topology

SELENE is distributed across specialized service boundaries to enforce cognitive separation.

## Technical Infrastructure Map

```mermaid
graph TD
    UI[React Next.js UI] --> |SSE Stream| CFR[Cognitive Flight Recorder]
    UI --> |REST| API[FastAPI Backend]

    subgraph "SELENE Runtime (High Trust)"
        API --> Orchestrator[LangGraph Orchestrator]
        Orchestrator --> Planner[Planner Node]
        Orchestrator --> Critic[Critic Node]
        Orchestrator --> Reflector[Reflection Engine]
        
        Planner --> CapabilityAdapter[Capability Adapter]
    end

    subgraph "The Membrane (Strict Governance)"
        CapabilityAdapter --> PolicyGate[Policy Gate]
        PolicyGate --> ExecutionEngine[Execution Engine]
        ExecutionEngine --> ValidationNormalizer[Validation Normalizer]
    end

    subgraph "External Ecosystem (Zero Trust)"
        ExecutionEngine --> |MCP Protocol| GitHubMCP[GitHub MCP Server]
        ExecutionEngine --> |MCP Protocol| SlackMCP[Slack MCP Server]
        ExecutionEngine --> |MCP Protocol| FS_MCP[File System MCP]
    end

    ValidationNormalizer --> |ExecutionReceipt| Orchestrator
    ValidationNormalizer --> |Provenance Hash| EventBus[SSE Event Bus]
    EventBus --> CFR
```

## SSE Flow
The backend uses Server-Sent Events (SSE) to push raw cognitive states (`cognitive_step`, `tamper_lock`) to the frontend. The React UI synthesizes this data into causal reconstruction for the human operator.
