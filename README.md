<div align="center">

# SELENE OS

**A Next-Generation Multi-Agent Cognitive Operating System**

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/TEKURU-ZENO/SELENE-OS)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)

[Overview](#overview) • [Architecture](#architecture) • [Key Features](#key-features) • [Tech Stack](#technology-stack) • [Quick Start](#quick-start) • [Documentation](#documentation)

</div>

---

## Overview

**SELENE OS** (Self-Evolving Logic & Execution Network Environment) is an advanced, multi-agent cognitive operating system designed to handle complex, multi-step tasks dynamically. Rather than operating as a simple chatbot or a rigid automation script, SELENE OS functions as a comprehensive ecosystem where multiple specialized AI agents collaborate, plan, execute, and learn.

At its core, SELENE OS bridges the gap between natural language intent and safe, isolated execution. It understands user goals, retrieves deep context from a 5-layer stratified memory system, plans multi-step actions, and rigorously validates outputs using statistical metrics like Shannon entropy and JS divergence before presenting them to the user or taking action in its sandboxed environment.

Built with a robust 10-layer architecture, SELENE guarantees high reliability, dynamic personalization through Dynamic Embedding Profiles (DEP), and strict governance via Human-In-The-Loop (HITL) locks and SSRF protections.

---

## Architecture

SELENE OS is built upon a 10-layer cognitive architecture. The flow of information and processing is visualized below:

```mermaid
graph TD
    User([User Request]) --> L0[Layer 0: Ingress Router]
    L0 --> L1[Layer 1: Intent Decomposer]
    L1 --> L2[Layer 2: Personalization DEP]
    L2 --> L3[Layer 3: Context Engine]
    L3 --> L4[Layer 4: Planner]
    
    subgraph L5 Orchestrator [Layer 5: Orchestrator LangGraph]
        L4 --> L5_Graph((Cognitive Nodes))
        L5_Graph <--> L6[Layer 6: Critic Agent]
        L5_Graph <--> L7[Layer 7: Execution Sandbox]
    end
    
    L5_Graph --> L8[Layer 8: Governance]
    L8 -.->|HITL Approval| User
    L8 --> L9[(Layer 9: Memory)]
    L9 -.-> L3
    
    classDef layer fill:#f9f9f9,stroke:#333,stroke-width:2px;
    class L0,L1,L2,L3,L4,L6,L7,L8,L9 layer;
    class L5_Graph layer;
```

---

## Key Features

- **Multi-Agent Orchestration**: Powered by LangGraph, coordinating 10 specialized cognitive nodes to handle distinct phases of problem-solving.
- **Advanced Context Engine**: Hybrid RRF (Reciprocal Rank Fusion) combining dense (FAISS) and sparse (BM25) search at a 70/30 ratio, enhanced by BGE-2 reranking for unparalleled retrieval accuracy.
- **Statistical Validation**: A dedicated Critic Agent evaluates outputs using Shannon entropy ($H(p)$), perplexity ($2^H$), and Jensen-Shannon divergence to minimize hallucinations and enforce logical consistency.
- **Dynamic Personalization**: Employs Dynamic Embedding Profiles (DEP) filtered through Sparse Autoencoders. Adapts dynamically if cosine delta `< 0.85`.
- **Stratified Memory with Decay**: A 5-layer memory system (Working, Episodic, Semantic, Procedural, Archival) featuring exponential temporal decay ($score \times e^{-\lambda \Delta t}$).
- **Secure Execution**: Dual-layer execution strategy using E2B cloud microVMs with seamless local subprocess fallback (30s timeout).
- **Strict Governance**: In-built Human-in-the-Loop (HITL) mutation locks, strict SSRF request validation, and comprehensive shell/code blocking mechanisms.

---

## Technology Stack

| Component | Technologies |
| :--- | :--- |
| **Backend Framework** | FastAPI, Python 3.11+, Pydantic |
| **Agent Orchestration** | LangGraph, LangChain |
| **Vector & Search** | FAISS, BM25, BAAI/bge-reranker-base |
| **Database & Cache** | PostgreSQL, Redis |
| **Execution Sandbox** | E2B Cloud MicroVMs, Subprocess (Local) |
| **Frontend Framework** | Next.js 14, React, TailwindCSS |
| **Infrastructure** | Docker, Docker Compose, Render.com |

---

## Project Structure

```text
SELENE/
├── backend/                  # Core Python FastAPI backend
│   ├── main.py               # Application entry point
│   ├── core/                 # Cognitive processing & LangGraph logic
│   ├── memory/               # 5-layer memory & hybrid search engine
│   ├── governance/           # HITL, security, and execution sandbox
│   ├── services/             # LLM integrations
│   ├── schemas/              # Pydantic data models
│   ├── connectors/           # 3rd-party API integrations
│   ├── workers/              # Background tasks (Celery/RQ)
│   └── testing/              # Pytest suites
├── frontend/                 # Next.js web interface (Git Submodule)
├── docs/                     # Comprehensive system documentation
├── docker-compose.yml        # Multi-container local orchestration
├── render.yaml               # Render.com deployment configuration
├── selene_manifesto.md       # Project vision and principles
└── selene_final_architecture_topology.md # Architectural deep-dive
```

---

## Quick Start

Follow these steps to get a local development environment running.

### 1. Prerequisites
- Python 3.11+
- Node.js 20+ (for frontend)
- Docker & Docker Compose
- API Keys for your chosen LLM (OpenAI, Anthropic, etc.) and E2B

### 2. Clone the Repository
```bash
git clone https://github.com/TEKURU-ZENO/SELENE-OS.git
cd SELENE-OS
git submodule update --init --recursive
```

### 3. Backend Setup
Create a virtual environment and install dependencies:
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Environment Configuration
Copy the example environment file and fill in your keys:
```bash
cp .env.example .env
```
Ensure you set up keys like `OPENAI_API_KEY`, `E2B_API_KEY`, and database URIs.

### 5. Start Infrastructure (Redis & DB)
Run the required backing services using Docker:
```bash
cd ..
docker-compose up -d redis postgres
```

### 6. Run the Backend Server
```bash
cd backend
uvicorn main:app --reload --port 8000
```
The API will be available at `http://localhost:8000`.

### 7. Run the Frontend
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
The UI will be available at `http://localhost:3000`.

---

## Architecture Layers (The 10 Layers)

SELENE's robust capabilities are divided into ten distinct architectural layers:

1. **Layer 0 - Ingress Router**: Built on FastAPI. Handles HTTP endpoints, WebSocket streaming, rate limiting, and JWT authentication.
2. **Layer 1 - Intent Decomposer**: Utilizes LLMs to classify user intent and break down complex requests into multi-intent structural graphs.
3. **Layer 2 - Personalization (DEP)**: Dynamic Embedding Profiles utilizing Sparse Autoencoders to adjust system tone and behavior based on historical interaction vectors.
4. **Layer 3 - Context Engine**: Implements RRF (Reciprocal Rank Fusion) at a 70/30 split between FAISS dense search and BM25 sparse search, capped with BGE-2 reranking.
5. **Layer 4 - Planner**: Generates multi-step, directed acyclic graphs for execution, matching required steps with available system capabilities.
6. **Layer 5 - Orchestrator**: The LangGraph state machine bridging the API to cognitive processing. Manages state transitions across 10 distinct cognitive nodes.
7. **Layer 6 - Critic Agent**: A rigorous validation layer utilizing Shannon entropy ($H(p)$), perplexity, and JS divergence to evaluate LLM outputs for certainty and coherence.
8. **Layer 7 - Execution Sandbox**: Secure code execution via E2B microVMs, with a robust local subprocess fallback utilizing a strict 30-second timeout.
9. **Layer 8 - Governance**: Enforces safety protocols, including Human-in-the-Loop (HITL) mutation locks, SSRF protection on network calls, and shell/command blocking.
10. **Layer 9 - Memory**: A 5-layer stratified system (Working: $\le1$hr, Episodic: $\le24$hr, Semantic: $\le7$d, Procedural: $\le30$d, Archival: $>30$d) with exponential decay functions.

---

## Configuration

Key environment variables to configure in your `.env` file:

```ini
# Core
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Sandbox
E2B_API_KEY=e2b-...

# Storage
DATABASE_URL=postgresql://user:pass@localhost:5432/selene
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET=your_super_secret_key
HITL_ENABLED=true
```

---

## API Reference

The backend provides a robust REST API and WebSocket interface.

- **`POST /api/v1/query`**
  Main entry point for submitting tasks and queries. Triggers the LangGraph orchestrator.
- **`WS /ws`**
  WebSocket connection for real-time streaming of agent thoughts, state transitions, and execution outputs.
- **`GET /health/live`**
  Basic liveness probe for orchestration tools (e.g., Kubernetes).
- **`GET /health/ready`**
  Deep readiness probe checking LLM connectivity, Vector Store availability, and DB connections.
- **`GET /health/metrics`**
  Prometheus-compatible metrics endpoint detailing latency, token usage, and node transition counts.

---

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Architecture Overview](docs/architecture.md)
- [Memory Subsystem](docs/memory.md)
- [Context Engine & RRF](docs/context_engine.md)
- [Critic Agent & Validation](docs/critic.md)
- [Governance & Security](docs/governance.md)
- [Execution Sandbox](docs/sandbox.md)

*(Note: Create these files for full detail.)*

---

## Testing

SELENE uses `pytest` for robust unit and integration testing.

To run the test suite:
```bash
cd backend
pytest -v --cov=core --cov=memory --cov=governance testing/
```

For frontend testing:
```bash
cd frontend
npm run test
```

---

## Deployment

### Docker Deploy
A complete `docker-compose.yml` is provided for immediate full-stack deployment:
```bash
docker-compose up --build -d
```

### Render.com
SELENE is natively configured for deployment on Render.com via the `render.yaml` infrastructure-as-code configuration. Connect your GitHub repository to Render and it will automatically provision the FastAPI backend, Postgres database, and Redis cache.

---

## Contributing

We welcome contributions! Please review our guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Ensure all tests pass and your code is formatted with `black` and `ruff`.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Roadmap

**Current Status**: Alpha v0.1.3

### Upcoming
- [ ] Integration with advanced multi-modal models for visual intent recognition.
- [ ] Decentralized memory synchronization across multiple edge SELENE nodes.
- [ ] Enhanced HITL UI in the Next.js frontend with visual diffs.
- [ ] Deep integration with external APIs via an automated OpenAPI capability matcher.

---
<div align="center">
<i>Built for the future of cognitive computing.</i>
</div>
