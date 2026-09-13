# SELENE OS Operations Runbook

## 1. Overview
This runbook provides operational procedures for monitoring, maintaining, and troubleshooting SELENE OS deployments.

## 2. Service Health Monitoring
Operators should continuously monitor the health endpoints provided by the Layer 0 Ingress Router.

### Health Endpoints
- **Liveness (`/health/live`)**: Confirms the process is running.
- **Readiness (`/health/ready`)**: Confirms connections to PostgreSQL and Redis.
- **Metrics (`/health/metrics`)**: Provides deep insights into cognitive layer performance, memory decay rates, and LangGraph node execution times.

## 3. Common Issues and Resolutions

### Issue: Vector Store Out of Memory
**Symptom**: Application crashes with OOM errors during semantic memory retrieval.
**Resolution**: 
1. Restart the application. The in-memory FAISS store rebuilds on restart.
2. If the issue persists, increase the server's RAM or limit the memory horizon in `MemoryManager`.

### Issue: E2B Sandbox Connection Failure
**Symptom**: Execution Sandbox (Layer 7) fails to connect to the cloud microVM.
**Resolution**:
1. Check if `E2B_API_KEY` is valid and not expired.
2. The system automatically falls back to local subprocesses. Monitor logs for "E2B fallback triggered".
3. Check network outbound connectivity on port 443.

## 4. Log Analysis
SELENE OS generates structured JSON logs to facilitate parsing by aggregators (ELK, Datadog).

### Log Rotation Configuration
By default, logs are written to `logs/selene.log` and rotated daily, keeping 14 days of history.
```json
{
  "timestamp": "2023-10-25T12:00:00Z",
  "level": "INFO",
  "layer": "Context Engine",
  "message": "Hybrid search completed",
  "duration_ms": 142
}
```

## 5. Performance Troubleshooting
If the system becomes sluggish (P99 latency > 10s):
1. **Check BGE Reranker**: The BAAI/bge-reranker-base model runs on CPU by default. High CPU usage may indicate a bottleneck in Layer 3 (Context Engine).
2. **Check Redis Queue**: Ensure background tasks are not piling up in Redis.

## 6. Memory/CPU Monitoring
Monitor the host system using standard tools (htop, Prometheus Node Exporter). Focus on:
- CPU spikes during Intent Decomposition (Layer 1) and Critic Validation (Layer 6).
- Memory usage by FAISS and BGE model loading.

## 7. Vector Store Maintenance
The current architecture uses an in-memory FAISS index. 
- **Rebuilds**: The index rebuilds from the PostgreSQL database on every restart.
- **Maintenance**: No manual maintenance required, but restarts can take longer as the dataset grows.

## 8. Database Maintenance
Run `VACUUM ANALYZE` weekly on the PostgreSQL database to optimize query planning, particularly for the Memory stores (working, episodic, semantic, procedural, archival).

## 9. Redis Cache Management
Redis is used for task queuing and transient DEP (Dynamic Embedding Profiles) caching.
- If Redis memory is exhausted, check for stalled tasks.
- Flush command: `redis-cli FLUSHALL` (Use with caution in production).

## 10. Restart Procedures
To restart a Dockerized deployment gracefully:
```bash
docker-compose stop backend
docker-compose start backend
```
Wait 30 seconds for the FAISS index to rebuild before routing traffic.

## 11. Emergency Procedures
In the event of a catastrophic failure or security breach:
1. Revoke `OPENAI_API_KEY` and `E2B_API_KEY`.
2. Stop all containers: `docker-compose down`.
3. Assess SSRF logs in Layer 8 (Governance).
4. Restore PostgreSQL from the latest backup.

## 12. Escalation Matrix
- **L1 Support**: Triage logs and basic restarts.
- **L2 Support**: Database queries and vector store debugging.
- **L3 Engineering**: LLM integration, LangGraph orchestration issues.
