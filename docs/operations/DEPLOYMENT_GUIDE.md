# SELENE OS Deployment Guide

## 1. Introduction
Welcome to the comprehensive deployment guide for SELENE OS. This operating system is a 10-layer cognitive multi-agent architecture designed to provide an intelligent, autonomous environment. This guide will walk you through deploying SELENE OS locally, via Docker, or to cloud providers like Render.com.

## 2. Prerequisites
Before beginning the deployment, ensure that the following prerequisites are installed on your target system:
- **Python 3.11+**: Required for the backend architecture, particularly FastAPI and LangGraph nodes.
- **Node.js 18+**: Required to build and serve the Next.js frontend submodule.
- **Docker**: For containerized deployment.
- **PostgreSQL 15**: Used as the primary relational database.
- **Redis 7**: Used for caching and pub/sub message brokering.

## 3. Local Development Setup (Step-by-Step)
For local development, it is highly recommended to run the backend and frontend separately to leverage hot-reloading.

### Step 3.1: Clone the Repository
```bash
git clone https://github.com/tekuru-zeno/selene-os.git
cd selene-os
```

### Step 3.2: Set Up Backend Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3.3: Set Up Frontend Environment
```bash
cd ../frontend
npm install
```

### Step 3.4: Configure Environment Variables
Copy `.env.example` to `.env` in the `backend/` directory. See the Environment Variables Reference below for details.

### Step 3.5: Run Services
Start the backend server:
```bash
cd backend
uvicorn main:app --reload --port 8000
```
Start the frontend server:
```bash
cd frontend
npm run dev
```

## 4. Environment Variables Reference
The following environment variables are supported in the `.env` file for the backend:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | None | `postgresql://user:pass@localhost:5432/selene` |
| `REDIS_URL` | Redis connection string | None | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API Key for embeddings | None | `sk-...` |
| `E2B_API_KEY` | E2B Sandbox API Key | None | `e2b_...` |
| `VECTOR_INDEX_PATH` | Path to FAISS index | `vector_store.index` | `/app/data/vector_store.index` |
| `VECTOR_DIMENSION` | Dimension of the vector store | `1536` | `1536` |
| `LOG_LEVEL` | Application logging level | `INFO` | `DEBUG` |
| `PORT` | API Port | `8000` | `8000` |
| `ENABLE_SSR` | Enable Server-Side Rendering | `True` | `True` |

## 5. Docker Deployment
The easiest way to deploy SELENE OS is using Docker Compose.

```bash
docker-compose up -d
```
This command builds and starts the required services defined in `docker-compose.yml`.

### Docker Compose Service Definitions
- **backend**: The FastAPI application serving the 10 cognitive layers.
- **postgres**: PostgreSQL 15 database instance for relational data.
- **redis**: Redis 7 cache and broker for async tasks.
- **frontend**: The Next.js frontend application (optional depending on config).

## 6. Render.com Deployment
For cloud deployment, SELENE OS includes a `render.yaml` configuration.

### Deployment Steps on Render
1. Connect your GitHub repository to Render.
2. In the Render Dashboard, choose **Blueprints** and create a new Blueprint.
3. Select the `selene-os` repository.
4. Render will automatically provision the PostgreSQL, Redis, and Web Services defined in `render.yaml`.

## 7. Health Check Validation
SELENE OS exposes several health check endpoints to validate deployment success.

- **`/health/live`**: Returns 200 OK if the API server is running. Used for liveness probes.
- **`/health/ready`**: Returns 200 OK only if database, redis, and vector stores are connected.
- **`/health/metrics`**: Exposes Prometheus-compatible metrics for monitoring CPU, memory, and cognitive load.

## 8. Database Migrations
Migrations are handled using Alembic. Run migrations after setting up the database:
```bash
cd backend
alembic upgrade head
```

## 9. SSL/TLS Configuration
For production deployments, SSL/TLS should be terminated at a reverse proxy (e.g., Nginx, Traefik) or via the cloud provider (e.g., Render, AWS ALB).

### Example Nginx Config:
```nginx
server {
    listen 443 ssl;
    server_name selene.example.com;

    ssl_certificate /etc/letsencrypt/live/selene.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/selene.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 10. Reverse Proxy Setup
If deploying locally or on bare metal, ensure your reverse proxy handles WebSockets properly, as SELENE OS Layer 0 (Ingress Router) uses WebSockets for real-time streaming of cognitive processing steps.

## 11. Scaling Considerations
Currently, SELENE OS is a single-process architecture. When planning for scale:
- Ensure Redis is scaled to handle increased task routing.
- Increase the replica count for the frontend.
- Backend horizontal scaling is planned for future versions, requiring distributed memory management.

## 12. Troubleshooting
If the backend fails to start, verify that the `VECTOR_INDEX_PATH` is writable, as FAISS requires write access to serialize the index.
