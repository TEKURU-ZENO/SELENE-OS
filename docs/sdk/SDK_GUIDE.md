# SELENE OS SDK & Integration Guide

## Overview

SELENE OS exposes a robust API surface powered by Layer 0 (Ingress Router) running on FastAPI. It provides integration points for various clients, enabling both stateful real-time interactions via WebSockets and traditional stateless operations via REST APIs. 

The integration layer allows external applications to interact with the cognitive LangGraph state machine, query the context engine, trigger workflow packs, and observe the AI's internal reasoning loop.

---

## REST API Reference

### 1. Unified Query Endpoint

The primary entry point for stateless interactions.

- **URL:** `/api/v1/query`
- **Method:** `POST`
- **Description:** Submits a natural language request or explicit command to the SELENE Orchestrator (Layer 5).

#### Request Body Schema

```json
{
  "query": "Analyze the log files in /var/log/nginx and summarize errors.",
  "session_id": "optional-uuid-for-tracking",
  "mode": "auto", // Can be 'auto', 'research', 'code', 'analysis'
  "stream": false
}
```

#### Response Body Schema

```json
{
  "request_id": "req-12345",
  "status": "completed",
  "intent": {
    "primary": "FILE_ANALYSIS",
    "confidence": 0.94
  },
  "plan": [
    "Locate /var/log/nginx",
    "Extract lines containing ERROR or FAIL",
    "Summarize frequency and root causes"
  ],
  "result": "Found 45 error lines. Primary cause: connection timeout...",
  "critic_verdict": {
    "approved": true,
    "entropy": 1.24
  }
}
```

---

## WebSocket API Reference

For tasks that take significant time (e.g., complex multi-step reasoning, agent execution), the WebSocket API provides real-time streaming of state transitions.

- **URL:** `/ws/v1/session/{session_id}`
- **Protocol:** WebSocket

### Message Formats

**Client to Server (Input):**
```json
{
  "type": "input",
  "content": "Please rewrite the previous function to be async."
}
```

**Server to Client (Stream Events):**
```json
{
  "type": "state_update",
  "node": "planner",
  "timestamp": "2026-09-13T23:36:53Z",
  "data": {
    "current_step": "Decomposing user request"
  }
}
```

---

## Health Check Endpoints

SELENE uses standard Kubernetes-style health probes for orchestration compatibility.

- `GET /health/live`: Returns `200 OK` if the FastAPI application loop is running.
- `GET /health/ready`: Returns `200 OK` if dependencies (Redis, Postgres, FAISS) are reachable.
- `GET /health/metrics`: Prometheus-compatible metrics endpoint detailing token usage, latency, and cache hits.

---

## Authentication

*Note: Currently in Alpha, Authentication is disabled by default. The following is the planned JWT-based architecture.*

All endpoints under `/api/v1` and `/ws/v1` will require a valid JSON Web Token (JWT) in the `Authorization` header.

```http
Authorization: Bearer <your_token>
```

Tokens are verified against the central identity service. Scopes include `selene:read`, `selene:write`, and `selene:execute`.

---

## Request and Response Schemas

Core entities mapped in the SELENE architecture (refer to `backend/schemas/`):

### SeleneState (TypedDict for LangGraph)
Tracks the lifecycle of a request through the 10-layer cognitive OS.
```python
class SeleneState(TypedDict):
    input: str
    intent: IntentModel
    context: List[Document]
    plan: List[Step]
    sandbox_output: str
    critic_scores: CriticVerdict
    final_response: str
```

### CriticVerdict
Used by Layer 6 (Critic Agent) to validate statistical divergence and Shannon entropy.
```python
class CriticVerdict(BaseModel):
    is_valid: bool
    shannon_entropy_hp: float
    js_divergence: float
    feedback: str
```

### MemoryMetadata
Used by Layer 9 (Memory) to define the temporal decay and layer stratification.
```python
class MemoryMetadata(BaseModel):
    layer: Literal["working", "episodic", "semantic", "procedural", "archival"]
    decay_rate_lambda: float
    timestamp: datetime
    access_count: int
```

---

## Python Client Example

```python
import requests
import json

SELENE_URL = "http://localhost:8000/api/v1/query"
HEADERS = {"Content-Type": "application/json"}

def run_selene_query(prompt: str):
    payload = {
        "query": prompt,
        "mode": "auto"
    }
    
    response = requests.post(SELENE_URL, json=payload, headers=HEADERS)
    response.raise_for_status()
    
    data = response.json()
    print(f"Status: {data['status']}")
    print(f"Result: {data['result']}")
    
if __name__ == "__main__":
    run_selene_query("Scan the docker-compose.yml for exposed ports.")
```

---

## JavaScript/TypeScript Client Example

```typescript
async function querySelene(prompt: string) {
    const url = 'http://localhost:8000/api/v1/query';
    const payload = {
        query: prompt,
        mode: 'auto'
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        
        const data = await response.json();
        console.log("SELENE Output:", data.result);
    } catch (error) {
        console.error("Query failed:", error);
    }
}

querySelene("Summarize the intent engine logic.");
```

---

## Rate Limiting Behavior

Layer 0 implements Redis-backed sliding-window rate limiting.

- **Default Limits:** 100 requests per minute per IP.
- **Headers Returned:**
  - `X-RateLimit-Limit`: The configured limit.
  - `X-RateLimit-Remaining`: Remaining capacity.
  - `X-RateLimit-Reset`: Timestamp when the limit resets.

Exceeding the limit results in a `429 Too Many Requests` status code.

---

## Error Codes and Handling

Standard REST error patterns are followed:

- `400 Bad Request`: Schema validation failure (Pydantic).
- `401 Unauthorized`: Missing or invalid JWT.
- `403 Forbidden`: Action blocked by Layer 8 (Governance) - e.g., SSRF or shell command blocking.
- `422 Unprocessable Entity`: The planner failed to decompose the request.
- `500 Internal Server Error`: Backend crash.

*Example Governance Error (403):*
```json
{
  "error": "Governance Block",
  "message": "Execution of 'rm -rf' is strictly prohibited by safety policies."
}
```

---

## Webhook Integration Patterns

For asynchronous batch processing, you can register a webhook URL in the initial query payload.

```json
{
  "query": "Perform a massive repository analysis.",
  "webhook_url": "https://yourapp.com/webhooks/selene"
}
```

SELENE will return a `202 Accepted` immediately. Upon completion, a POST request containing the final `SeleneState` will be dispatched to your webhook URL. This is ideal for CI/CD pipeline integration and scheduled procedural workflows.
