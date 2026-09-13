# System Topology

## Overview
SELENE OS is deployed as a multi-service containerized architecture. It separates the cognitive backend, user-facing frontend, and data persistence layers to ensure scalability, security, and independent deployment cycles.

## Network Topology Diagram
```mermaid
graph TD
    User[User / Client] --> Frontend[Next.js Frontend :3000]
    Frontend --> Backend[FastAPI Backend :8000]
    Backend --> PG[(PostgreSQL :5432)]
    Backend --> Redis[(Redis :6379)]
    Backend --> FAISS[(FAISS Local Index)]
    Backend --> Sandbox[Execution Sandbox / E2B]
    Backend --> LLM[External LLM Providers]
```

## Service Definitions and Ports
1. **Frontend**: Next.js application handling the chat interface, graph visualization, and HITL approval screens.
   - **Port**: 3000
   - **Protocol**: HTTP/WebSocket
2. **Backend**: FastAPI server hosting the LangGraph runtime, Orchestrator, and Ingress Router.
   - **Port**: 8000
   - **Protocol**: HTTP/REST, WebSocket (for streaming execution logs)
3. **PostgreSQL**: Relational storage for user accounts, governance logs, and structured memory metadata.
   - **Port**: 5432
4. **Redis**: In-memory caching for DEP profiles, working memory, and LangGraph checkpointer state.
   - **Port**: 6379
5. **FAISS**: Local file-backed vector store (persisted to volume).

## Docker Service Definitions
The `docker-compose.yml` configures the local deployment:
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DB_URL=postgresql://user:pass@postgres:5432/selene
    depends_on:
      postgres:
        condition: service_healthy
  
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      
  redis:
    image: redis:7
    ports: ["6379:6379"]
```

## Health Check Chain
SELENE implements a cascaded health check system:
- `/health/live`: Basic process liveness.
- `/health/ready`: Verifies connections to Postgres, Redis, and FAISS initialization.
- `/health/metrics`: Exposes LangGraph node execution times and memory latency (Prometheus format).

## Deployment Topology (Render.com)
For cloud deployment, `render.yaml` defines a Blueprint:
- **Web Service**: FastAPI backend.
- **Static Site / Web Service**: Next.js frontend.
- **Managed PostgreSQL**: Fully managed DB instance.
- **Managed Redis**: Fully managed caching layer.
The E2B sandbox connects out via outbound API calls, requiring no incoming port bindings.
