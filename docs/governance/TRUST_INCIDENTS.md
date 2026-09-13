# Trust Incidents

## 1. Introduction

A "Trust Incident" in SELENE occurs when the cognitive operating system attempts an action that violates the bounds set by Layer 8 (Governance) or the Operator Covenant. SELENE's fail-safe design guarantees that such attempts are blocked, logged, and classified for human review.

This document outlines the mechanisms for detecting, classifying, and responding to Trust Incidents.

## 2. What Constitutes a Trust Incident

A trust incident is triggered when the agent's intent or execution plan attempts to:
- **SSRF (Server-Side Request Forgery)**: Accessing local loopback addresses (`127.0.0.1`, `localhost`) or internal AWS metadata IP (`169.254.169.254`) without explicit developer mode enabled.
- **Shell Injection**: Attempting to execute unauthorized shell commands (e.g., `rm -rf /`, `mkfs`) outside the E2B microVM.
- **Unauthorized Data Access**: Attempting to read files outside the designated workspace boundaries or accessing encrypted Layer 9 archival memory without context.
- **HITL Bypass**: Attempting to mutate state while a Human-in-the-Loop lock is pending.

## 3. Detection Mechanisms

Trust incidents are detected primarily in **Layer 8 (Governance)** (`backend/governance/safety.py`).

### 3.1 URL Validation (SSRF Protection)
All outbound HTTP requests route through the egress proxy which evaluates:
```python
def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    ip = resolve_ip(parsed.hostname)
    if is_private_ip(ip) or ip == '169.254.169.254':
        return False
    return True
```

### 3.2 Command Blocking (Shell/Regex Patterns)
Code intended for the local subprocess fallback is statically analyzed.
- Prohibited patterns: `subprocess.Popen(..., shell=True)`
- Blocklist regex: `(rm -rf|mkfs|chmod 777|chown -R)`

### 3.3 HITL Mutation Locks
If a mutation is attempted on a locked resource, the `hitl.py` interceptor throws a `StateLockedException`, generating a Trust Incident.

## 4. Incident Classification

| Severity | Definition | Agent Response | Operator Action Required |
|---|---|---|---|
| **Low** | Agent attempted a benign operation that failed an over-restrictive regex check. | Discards step, replans | Review log, adjust regex |
| **Medium** | Agent attempted to read unauthorized files outside workspace. | Halts plan execution | Deny access, provide feedback |
| **High** | SSRF attempt or direct shell execution bypass attempt. | Total halt, discards working memory | Investigate trace via Forensics |
| **Critical** | Repeated high severity violations in one session. | Locks agent profile, kills session | Full post-mortem |

## 5. Response Procedures

1. **Automated Interception**: Layer 8 catches the exception and logs it to PostgreSQL `trust_incidents`.
2. **Alerting**: A WebSocket broadcast pushes an urgent notification to the Next.js frontend (Layer 0).
3. **Session Freeze**: For High/Critical incidents, the Orchestrator pauses the LangGraph execution at the current node.

## 6. Post-Incident Analysis

Operators use Replay Forensics to investigate:
- Did Layer 1 (Intent) misclassify the user prompt?
- Did Layer 4 (Planner) hallucinate the tool?
- Was Layer 6 (Critic) entropy high?

## 7. Example Incidents and Resolutions

**Incident ID**: `INC-2026-09-A1`
- **Attempt**: Agent tried to fetch `http://169.254.169.254/latest/meta-data/` to complete a user query about "AWS configuration".
- **Detection**: Blocked by SSRF filter in `safety.py`.
- **Classification**: High.
- **Resolution**: Plan aborted. User notified. Added specific system prompt guardrail to prevent metadata scraping.

**Incident ID**: `INC-2026-09-B2`
- **Attempt**: Agent executed `rm -rf ./build_dir` using local subprocess instead of E2B.
- **Detection**: Blocked by command regex analyzer.
- **Classification**: Medium.
- **Resolution**: Operator granted HITL override for specific directory cleanup.
