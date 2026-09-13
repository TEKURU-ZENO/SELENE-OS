# SELENE OS — Backend Dockerfile
# Multi-stage build for production. Dev mode uses mount + hot-reload.

# ── Stage 1: Dependency resolution ──────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /app

# System dependencies for FAISS, cryptography, and compiled extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Production image ─────────────────────────────────────
FROM python:3.11-slim AS production

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data replays artifacts audit exports

# Non-root user for security
RUN groupadd -r selene && useradd -r -g selene -d /app selene && \
    chown -R selene:selene /app
USER selene

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start command — uvicorn with 1 worker in alpha (scale workers separately)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--loop", "uvloop", "--http", "h11"]
