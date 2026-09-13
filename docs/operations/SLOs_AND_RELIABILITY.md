# SLOs and Reliability Targets

## 1. Introduction
This document defines the Service Level Objectives (SLOs), reliability targets, and incident response procedures for SELENE OS Alpha.

## 2. Availability Target
- **Target (Alpha)**: 99.5% uptime
- **Definition**: The percentage of successful requests to the `/health/live` and `/health/ready` endpoints over a rolling 30-day window.

## 3. Latency Targets
Latency targets are crucial given the 10-layer cognitive architecture.
- **P50 Latency**: < 2 seconds for a standard query traversing Layers 0-9.
- **P95 Latency**: < 5 seconds.
- **P99 Latency**: < 10 seconds.
*Note: High latency is often attributed to external LLM calls or E2B sandbox execution.*

## 4. Error Budget
- **Monthly Error Budget**: 0.5% (approx. 3.6 hours of downtime per month).
- **Policy**: If the error budget is exhausted, feature deployments are frozen until reliability is restored to >99.5%.

## 5. Health Check SLIs
Service Level Indicators (SLIs) are monitored via:
- `/health/live`: Measured every 10s.
- `/health/ready`: Measured every 30s.
- PostgreSQL Connection Ping: Monitored internally by the backend.
- Redis Connection Ping: Monitored internally by the backend.

## 6. Monitoring Stack
- **Metrics**: Exposed via `/health/metrics` in Prometheus format.
- **Dashboards**: Grafana dashboards track node transitions in the Orchestrator (Layer 5) and Critic rejections (Layer 6).
- **Logs**: Structured JSON logs collected via Fluentd/ELK stack.

## 7. Alerting Rules
Alerts are routed to PagerDuty or Slack based on severity:
- **High Latency**: P95 > 5s for 5 consecutive minutes.
- **Error Rate**: 5xx HTTP response rate > 1% over 5 minutes.
- **OOM Warning**: Host memory utilization > 85%.
- **Sandbox Failure**: Local fallback triggered > 10 times in 1 hour.

## 8. Incident Severity Levels
- **SEV-1 (Critical)**: Total system outage, database corruption, or security breach. Requires immediate, all-hands response.
- **SEV-2 (High)**: Significant feature degradation (e.g., E2B integration failing, vector search offline). Requires on-call intervention.
- **SEV-3 (Medium)**: Non-critical bugs, latency spikes, or HitL UI issues. Addressed during business hours.
- **SEV-4 (Low)**: Cosmetic issues or minor log noise.

## 9. Recovery Time Objectives (RTO)
- **Database Restoration**: < 30 minutes from backup.
- **Service Restart**: < 5 minutes (including FAISS vector rebuild).
- **Full Cluster Rebuild**: < 2 hours via Render Blueprints.

## 10. Capacity Planning
Currently, SELENE OS is designed for a single-node deployment.
- **CPU Limit**: BGE reranker requires at least 2 dedicated CPU cores.
- **Memory Limit**: Base application requires 2GB RAM. Vector store requires ~1GB per 100k vectors. Minimum recommended host memory is 4GB.
- Future scaling to Kubernetes is planned for the Beta release to support multi-tenant workloads.
