# End-to-End Sequence Diagrams

This document illustrates the precise sequencing of events across the 10 layers of SELENE OS for various standard operations. 

## 1. Full Query Processing Sequence

This is the standard "happy path" when a user submits a complex prompt requiring planning, context retrieval, and execution.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as L0: FastAPI
    participant ORC as L5: Orchestrator
    participant INT as L1: Intent Engine
    participant MEM as L3/L9: Context & Memory
    participant PLN as L4: Planner
    participant EXC as L7: Execution
    
    User->>API: POST /api/v1/query {prompt}
    API->>ORC: Initialize SeleneState
    ORC->>INT: Analyze Intent
    INT-->>ORC: Intent: MULTI_STEP_TASK
    
    ORC->>MEM: Retrieve Context (BM25 + FAISS)
    MEM-->>ORC: Stratified Memories (Working/Episodic)
    
    ORC->>PLN: Generate Plan with Context
    PLN-->>ORC: Step 1: CmdA, Step 2: CmdB
    
    loop For each step in Plan
        ORC->>EXC: Run capability (E2B Sandbox)
        EXC-->>ORC: Result (stdout/stderr)
    end
    
    ORC->>MEM: Write back execution summary
    ORC->>API: Final Markdown Response
    API->>User: 200 OK {response}
```

## 2. WebSocket Streaming Sequence

For real-time UI updates, SELENE relies on WebSockets rather than HTTP polling.

```mermaid
sequenceDiagram
    actor Client
    participant WS as WebSocket Manager
    participant ORC as LangGraph Runner
    
    Client->>WS: ws://localhost:8000/ws/{session_id}
    WS-->>Client: 101 Switching Protocols
    
    Client->>WS: {"action": "START_TASK", "prompt": "..."}
    WS->>ORC: Spawn Task
    
    ORC->>WS: {"type": "NODE_START", "node": "planner"}
    WS->>Client: (UI shows planner loading)
    
    ORC->>WS: {"type": "TOKEN_STREAM", "chunk": "I will..."}
    WS->>Client: (UI streams text)
    
    ORC->>WS: {"type": "TASK_COMPLETE", "result": "..."}
    WS->>Client: (UI marks finished)
```

## 3. Human-in-the-Loop (HITL) Sequence

When a task violates safety thresholds (e.g., destructive commands).

```mermaid
sequenceDiagram
    participant ORC as Orchestrator
    participant GOV as L8: Governance
    participant DB as Postgres
    participant UI as Next.js Frontend
    
    ORC->>GOV: Propose capability: `rm -rf /`
    GOV->>GOV: Match HITL regex rules
    GOV-->>ORC: hitl_status = PENDING
    
    ORC->>DB: Save state checkpoint (Paused)
    ORC->>UI: Broadcast HITL Request (WebSocket)
    
    UI->>UI: User reviews command
    UI->>DB: POST /api/hitl/approve
    DB->>ORC: Resume state graph
    
    ORC->>L7 Sandbox: Execute `rm -rf /`
```

## 4. Error Handling and Reflection Sequence

When an execution step fails, SELENE OS uses a self-correction loop.

```mermaid
sequenceDiagram
    participant PLN as Planner
    participant EXC as L7: Execution
    participant REF as L6/Reflection
    
    PLN->>EXC: Run `npm install unknown-package`
    EXC-->>PLN: Exit Code 1: 404 Not Found
    
    PLN->>REF: Submit failure for analysis
    REF->>REF: Analyze error trace and stderr
    REF-->>PLN: Suggested Fix: Check package name spelling
    
    PLN->>EXC: Run `npm search unknown-package`
    EXC-->>PLN: Exit Code 0: Suggestions found
    PLN->>EXC: Run `npm install correct-package`
```

## 5. Memory Write-Back & Decay Sequence

Memories in SELENE OS are not static; they decay over time unless reinforced.

```mermaid
sequenceDiagram
    participant ORC as Orchestrator
    participant MEM as Memory Manager
    participant WRK as Background Worker
    
    ORC->>MEM: Add episodic memory (Task summary)
    MEM->>MEM: Assign initial score S=100
    
    loop Every 1 Hour
        WRK->>MEM: Trigger Decay Pass
        MEM->>MEM: S_new = S_old * exp(-0.01 * 1hr)
        MEM->>MEM: If S_new < 10, move to Archival Tier
    end
```
