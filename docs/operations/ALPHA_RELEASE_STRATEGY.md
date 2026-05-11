# SELENE OS — Internal Alpha Release Strategy

## Objective

Move SELENE from a desktop-local architecture freeze into a controlled Internal Alpha deployment without compromising governance, trust guarantees, or operational stability.

---

# Phase 1 — Local Stabilization (1–2 Days)

Before exposing SELENE to even a few operators, stabilize the local runtime.

## Tasks

### Backend

* Freeze Python dependencies:

  ```bash
  pip freeze > requirements-lock.txt
  ```
* Add `.env.example`
* Separate secrets from code
* Enable structured rotating logs
* Ensure Redis/Postgres boot reliably

### Frontend

* Build production bundle:

  ```bash
  npm run build
  ```
* Verify SSE reconnect behavior
* Verify replay rendering in production mode

### Infrastructure

* Create:

  * `/artifacts`
  * `/replays`
  * `/audit`
  * `/exports`
* Ensure `.selene` exports persist safely

---

# Phase 2 — Containerization (Strongly Recommended)

Do NOT deploy directly from your desktop runtime.

Containerize the platform first.

## Suggested Architecture

### Docker Compose Stack

Services:

* frontend (Next.js)
* backend (FastAPI)
* redis
* postgres
* worker
* nginx (optional)

## Minimal Deployment Layout

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

  backend:
    build: ./backend
    ports:
      - "8000:8000"

  redis:
    image: redis:7

  postgres:
    image: postgres:16

  worker:
    build: ./backend
    command: python -m runtime.worker
```

## Why Containerize?

Because SELENE depends on:

* deterministic replay
* distributed execution
* reproducible runtime state
* stable governance behavior

Containers guarantee:

* reproducibility
* deployment parity
* rollback safety
* easier debugging

---

# Phase 3 — Internal Alpha Infrastructure

## Recommended Hosting

### Cheap + Fast Setup

| Layer          | Recommendation            |
| -------------- | ------------------------- |
| Frontend       | Vercel                    |
| Backend        | Railway / Render / Fly.io |
| Redis          | Upstash Redis             |
| Postgres       | Neon / Supabase           |
| Object Storage | Cloudflare R2             |

This is enough for alpha.

---

# Phase 4 — Security Hardening Before Humans

## Absolute Requirements

### 1. Disable Dangerous Execution

Until fully audited:

* NO unrestricted shell execution
* NO autonomous writes
* NO unrestricted filesystem access

### 2. Force HITL

Set:

```python
FORCE_HITL_ALL_EXTERNAL_MUTATIONS = True
```

for alpha.

### 3. Connector Isolation

Do not expose:

* personal Slack
* personal GitHub
* production repos

Use:

* sandbox orgs
* fake repos
* dedicated test workspaces

---

# Phase 5 — Internal Operator Deployment

## Recommended Group Size

Start with:

```text
5–10 operators
```

Do NOT scale wider yet.

## Operator Types

You want:

| Operator Type            | Why                          |
| ------------------------ | ---------------------------- |
| Technical engineer       | Finds system flaws           |
| Non-technical user       | Finds UX confusion           |
| Skeptical user           | Finds trust gaps             |
| Fast multitasker         | Tests attention fatigue      |
| Security-minded operator | Tests governance assumptions |

---

# Phase 6 — Operational Workflow

## Create a Private Alpha Discord/Slack

Channels:

```text
#trust-incidents
#governance-confusion
#replay-analysis
#false-denials
#operator-feedback
```

This becomes the real telemetry layer.

---

# Phase 7 — Deployment Branding

Do NOT market SELENE as:

* AGI
* autonomous superintelligence
* self-evolving AI

Position it as:

```text
Governed Cognitive Infrastructure
```

and:

```text
Explainable Cognitive Runtime
```

This framing aligns with the actual architecture.

---

# Phase 8 — What NOT To Do

## Avoid These Mistakes

### ❌ Public launch too early

You do not yet want internet-scale chaos.

### ❌ Plugin marketplace immediately

Governance needs real telemetry first.

### ❌ Autonomous execution demos

Your moat is restraint, not recklessness.

### ❌ Benchmark obsession

Your differentiation is trust + replay + governance.

---

# Phase 9 — The Ideal Alpha Flow

## Recommended Timeline

### Week 1

Internal operators only

### Week 2

Connector stabilization

### Week 3

Workflow pack tuning

### Week 4

Governance calibration

### Week 5

Replay export auditing

### Week 6

Decision:

* private beta
* or extended alpha

---

# Phase 10 — Success Criteria

SELENE Alpha succeeds IF:

* Operators understand interruptions
* Replay traces become useful
* Governance denials feel rational
* HITL modifications feel seamless
* Trust increases over time
* Users understand WHY actions occurred

NOT if:

* it automates everything
* it acts autonomously
* it feels magical

---

# Final Operational Principle

```text
SELENE should feel disciplined, not impressive.
```

That is the moat.
