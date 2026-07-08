# DeployGuard Frontend API Map

> Generated from backend source analysis. Documents **all existing FastAPI HTTP endpoints**, their request/response shapes, and which frontend pages should consume them.
>
> **Last analyzed:** 2026-07-09

---

## Architecture Overview

DeployGuard uses an event-driven pipeline. Most backend services are **Kafka consumers**, not REST APIs. Only three services expose HTTP endpoints today:

| Service | Source | Default Port | Docker Exposed | Role |
|---------|--------|--------------|----------------|------|
| **Gateway** | `gateway/app.py` | 8000 | Yes (`8000:8000`) | Ingest GitHub webhooks → Kafka |
| **Aggregator** | `aggregator/main.py`, `aggregator/api.py` | 8002 | Yes (`8002:8002`) | Aggregate agent results → REST query |
| **Incident History Agent (health only)** | `agent-incident-history/incident_history/health.py` | 8080 | No (internal) | Liveness / dependency check |

**Non-HTTP backend components** (Kafka-only, no REST surface):

| Component | Source | Input Topic | Output Topic |
|-----------|--------|-------------|--------------|
| Code Risk Agent | `agent-code-risk/app.py` | `deployment-events` | `risk-results` |
| Infra Risk Agent | `agent-infra-risk/app.py` | `deployment-events` | `risk-results` |
| Incident History Agent | `agent-incident-history/app.py` | `deployment-events` | `risk-results` |
| Aggregator consumer | `aggregator/kafka_consumer.py` | `risk-results` | `deployment-decisions` (Kafka) |

### Frontend Proxy Paths

The integrated React app (`frontend/`) and production nginx (`frontend/nginx.conf`) proxy backend calls:

| Browser path | Rewrites to | Target service |
|--------------|-------------|----------------|
| `/api/gateway/*` | `/*` | `http://gateway:8000` (or `localhost:8000` in Vite dev) |
| `/api/aggregator/*` | `/*` | `http://aggregator:8002` (or `localhost:8002` in Vite dev) |

Vite dev proxy: `frontend/vite.config.ts`

---

## Shared Pydantic / Data Models

### Gateway — `GitHubWebhookPayload`

**File:** `gateway/app.py`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repository` | `dict \| null` | No | GitHub repo object (`name`, `full_name`, etc.) |
| `action` | `str \| null` | No | Webhook action (e.g. `opened`, `synchronize`) |
| `sender` | `dict \| null` | No | GitHub user who triggered the event |
| `head_commit` | `dict \| null` | No | Commit metadata (`message`, `author`, `id`) |
| `pull_request` | `dict \| null` | No | PR metadata (`title`, `body`, `user`, `url`) |

All fields are optional. The gateway wraps the payload in a Kafka event with a generated `correlation_id`.

---

### Aggregator — `LLMResult`

**File:** `aggregator/models.py`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | `str \| null` | `"unavailable"` | LLM provider name |
| `available` | `bool \| null` | `false` | Whether LLM reasoning succeeded |
| `summary` | `str \| null` | `""` | LLM executive summary |
| `risk_reasoning` | `list[str]` | `[]` | LLM risk reasoning bullets |
| `recommendations` | `list[str]` | `[]` | LLM recommendations |
| `confidence` | `float \| null` | `0.0` | LLM confidence (0.0–1.0) |

---

### Aggregator — `AgentResult`

**File:** `aggregator/models.py` (schema reference; stored/returned as plain dicts in practice)

| Field | Type | Description |
|-------|------|-------------|
| `agent` | `str` | Agent identifier: `code-risk`, `infra-risk`, or `incident-history` |
| `correlation_id` | `str` | Deployment correlation UUID |
| `score` | `int` | Risk score 0–100 |
| `severity` | `str` | `low`, `medium`, `high`, or `critical` |
| `confidence` | `float` | Agent confidence 0.0–1.0 |
| `reasons` | `list[str]` | Deterministic risk reasons |
| `recommendations` | `list[str]` | Remediation suggestions |
| `metadata` | `dict` | Agent-specific metadata (files scanned, infra findings, etc.) |
| `similar_incidents` | `list[dict] \| null` | Present on `incident-history` agent only |
| `llm` | `LLMResult \| null` | Nested LLM output |

**`similar_incidents` item shape** (from incident-history agent):

```json
{
  "incident_id": "INC-101",
  "similarity": 0.854,
  "severity": "critical",
  "outcome": "rollback",
  "title": "Authentication middleware removed"
}
```

---

### Aggregator — `FinalDecision`

**File:** `aggregator/models.py`, produced by `aggregator/decision_engine.py`

| Field | Type | Description |
|-------|------|-------------|
| `correlation_id` | `str` | Deployment correlation UUID |
| `overall_score` | `int` | Weighted risk score 0–100 |
| `overall_confidence` | `float` | Average agent confidence |
| `decision` | `str` | `SAFE`, `REVIEW`, or `BLOCK` |
| `severity` | `str` | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `agents` | `dict[str, dict]` | Full per-agent results keyed by agent name |
| `summary` | `str` | Executive summary string |
| `reasons` | `list[str]` | Merged, deduplicated reasons |
| `recommendations` | `list[str]` | Merged, deduplicated recommendations |
| `generated_at` | `str` | ISO-8601 UTC timestamp |

**Decision rules** (for frontend display logic):

- `overall_score >= 60` → `BLOCK`
- `overall_score >= 30` → `REVIEW`
- else → `SAFE`
- Any agent with `severity == CRITICAL` → force `BLOCK`

---

## HTTP Endpoint Reference

---

### 1. GitHub Webhook — Trigger Deployment

| Property | Value |
|----------|-------|
| **Endpoint** | `POST /webhook/github` |
| **Service** | Gateway |
| **Public URL (via proxy)** | `POST /api/gateway/webhook/github` |
| **HTTP Method** | `POST` |
| **Content-Type** | `application/json` |

#### Expected Request

Body: `GitHubWebhookPayload` (all fields optional). Example as sent by `frontend/src/api/client.ts`:

```json
{
  "repository": {
    "name": "payments-api",
    "full_name": "myorg/payments-api"
  },
  "pull_request": {
    "title": "Optimize postgres connection pooling",
    "body": "Adjusts pool settings and adds connection timeouts.",
    "user": { "login": "deployguard-gui" }
  },
  "head_commit": {
    "message": "fix: database connection pool exhaustion",
    "author": { "name": "developer" },
    "id": "abc12345"
  }
}
```

#### Expected Response

**200 OK**

```json
{
  "status": "sent",
  "correlation_id": "cf6691cc-b711-4b61-9e7f-2806952df01d",
  "topic": "deployment-events"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"sent"` on success |
| `correlation_id` | `string` | UUID to poll for aggregated decision |
| `topic` | `string` | Kafka topic name (`deployment-events`) |

#### Frontend Pages That Should Consume This

| Page | Path | Usage |
|------|------|-------|
| **Dashboard** | `frontend/src/pages/Dashboard.tsx` | "Simulate Webhook" form → `api.triggerDeployment()` |
| **Analytics** | `frontend/src/pages/Analytics.tsx` | "Simulate Scan" modal → triggers deployment pipeline |
| **Dashboard (Stitch)** | `stitch/dashboard_page/src/Dashboard.tsx` | "New Deployment" modal — **currently mock only**; should call this endpoint |
| **Analytics (Stitch)** | `stitch/analytics_page/src/Analytics.tsx` | "Trigger Scan Hook" — **currently mock only**; should call this endpoint |

---

### 2. Aggregator Health Check

| Property | Value |
|----------|-------|
| **Endpoint** | `GET /health` |
| **Service** | Aggregator |
| **Public URL (via proxy)** | `GET /api/aggregator/health` |
| **HTTP Method** | `GET` |

#### Expected Request

No body or query parameters.

#### Expected Response

**200 OK**

```json
{
  "status": "healthy"
}
```

#### Frontend Pages That Should Consume This

| Page | Path | Usage |
|------|------|-------|
| **Dashboard** | `frontend/src/pages/Dashboard.tsx` | Agent Status / system health panel (not wired today) |
| **Dashboard (Stitch)** | `stitch/dashboard_page/src/Dashboard.tsx` | "Agent Status" bento card — **currently simulated latency** |
| **Ops / Status footer** | `stitch/analytics_page/src/Analytics.tsx` | Footer "Status" link — **not wired** |

---

### 3. Get Deployment Decision

| Property | Value |
|----------|-------|
| **Endpoint** | `GET /decision/{correlation_id}` |
| **Service** | Aggregator |
| **Public URL (via proxy)** | `GET /api/aggregator/decision/{correlation_id}` |
| **HTTP Method** | `GET` |
| **Path Parameter** | `correlation_id` — UUID returned by the gateway webhook |

#### Expected Request

No body. Path param only.

#### Expected Response

**200 OK — Final decision ready**

Returns a `FinalDecision` object:

```json
{
  "correlation_id": "cf6691cc-b711-4b61-9e7f-2806952df01d",
  "overall_score": 74,
  "overall_confidence": 0.89,
  "decision": "BLOCK",
  "severity": "HIGH",
  "agents": {
    "code-risk": {
      "agent": "code-risk",
      "correlation_id": "cf6691cc-b711-4b61-9e7f-2806952df01d",
      "score": 72,
      "severity": "high",
      "confidence": 0.91,
      "reasons": ["Disabled OAuth verification"],
      "recommendations": ["Restore authentication guards"],
      "metadata": {},
      "llm": {
        "provider": "gemini",
        "available": true,
        "summary": "...",
        "risk_reasoning": ["..."],
        "recommendations": ["..."],
        "confidence": 0.88
      }
    },
    "infra-risk": { "...": "..." },
    "incident-history": {
      "...": "...",
      "similar_incidents": [
        {
          "incident_id": "INC-101",
          "similarity": 0.85,
          "severity": "critical",
          "outcome": "rollback",
          "title": "Authentication middleware removed"
        }
      ]
    }
  },
  "summary": "The deployment is blocked due to high-risk changes...",
  "reasons": ["Disabled OAuth validation creates immediate security vulnerability."],
  "recommendations": ["Do NOT merge without disabling privileged security context."],
  "generated_at": "2026-07-08T18:45:12.123456+00:00"
}
```

**202 Accepted — Aggregation in progress**

Returned when partial agent results exist but final decision is not yet stored:

```json
{
  "status": "pending",
  "correlation_id": "cf6691cc-b711-4b61-9e7f-2806952df01d",
  "collected_agents": ["code-risk", "infra-risk"],
  "message": "Deployment risk aggregation is in progress."
}
```

**404 Not Found — Unknown or expired deployment**

```json
{
  "detail": "No deployment found or decision expired for correlation_id: {correlation_id}"
}
```

> Final decisions expire from Redis after **1 hour** (`aggregator/redis_store.py`).

#### Frontend Pages That Should Consume This

| Page | Path | Usage |
|------|------|-------|
| **Dashboard** | `frontend/src/pages/Dashboard.tsx` | Poll every 3s for pending deployments via `api.getDecision()` |
| **Deployments** | `frontend/src/pages/Deployments.tsx` | Load selected deployment detail: agent cards, timeline, explainability |
| **Analytics** | `frontend/src/pages/Analytics.tsx` | Derive blocked-deployment table and agent score breakdowns |
| **Dashboard (Stitch)** | `stitch/dashboard_page/src/Dashboard.tsx` | Recent deployments table metrics — **currently mock** |
| **Deployments (Stitch)** | `stitch/deployments_page/src/components/Deployments.tsx` | Agent cards, timeline, AI summary — **currently mock** |
| **Analytics (Stitch)** | `stitch/analytics_page/src/Analytics.tsx` | High-risk blocks table, agent performance — **currently mock** |

---

### 4. Incident History Agent Health Check

| Property | Value |
|----------|-------|
| **Endpoint** | `GET /health` |
| **Service** | Incident History Agent |
| **Default URL** | `http://agent-incident-history:8080/health` (internal only; **not exposed in docker-compose**) |
| **HTTP Method** | `GET` |

#### Expected Request

No body or query parameters.

#### Expected Response

**200 OK**

```json
{
  "status": "ok",
  "agent": "incident-history",
  "qdrant_available": true,
  "embedding_provider": "sentence-transformer",
  "llm_provider": "gemini"
}
```

#### Frontend Pages That Should Consume This

| Page | Path | Usage |
|------|------|-------|
| **Dashboard** | `frontend/src/pages/Dashboard.tsx` | Agent Status panel (not wired today) |
| **Dashboard (Stitch)** | `stitch/dashboard_page/src/Dashboard.tsx` | "Agent Status" card — **currently simulated** |
| **Analytics (Stitch)** | `stitch/analytics_page/src/Analytics.tsx` | "Agent Performance Metrics" section — **currently static** |

---

## Endpoint-to-Frontend Page Matrix

### Integrated Frontend (`frontend/`)

| Frontend Page | Route (typical) | Existing Backend Endpoints Used | Data Source Today |
|---------------|-----------------|--------------------------------|-------------------|
| **Dashboard** | `/` | `POST /api/gateway/webhook/github`, `GET /api/aggregator/decision/{id}` | Hybrid: local mock cache + real API |
| **Deployments** | `/deployments` | `GET /api/aggregator/decision/{id}` (via cached list) | Hybrid: local mock cache + decision API |
| **Analytics** | `/analytics` | Indirect via deployment list | Local mock cache only (client-side aggregation) |
| **Incident History** | `/incidents` | *None* | Fully mocked (`MOCK_INCIDENTS`, `calculateSimilarity()`) |

### Stitch Design Prototypes (`stitch/*`)

| Stitch Page | Directory | Backend Integration | Notes |
|-------------|-----------|---------------------|-------|
| **Dashboard** | `stitch/dashboard_page/` | None | All data is in-component mock state |
| **Deployments** | `stitch/deployments_page/` | None | Static agent cards, timeline, incidents |
| **Analytics** | `stitch/analytics_page/` | None | Static charts and mock blocked deployments |
| **Incident History** | `stitch/incident_history_page/` | None | `INITIAL_INCIDENTS` mock array |

---

## Frontend Data Needs vs. Backend Gaps

The UI designs imply several REST endpoints that **do not exist yet**. Documented here so integration work can be scoped.

### Dashboard Endpoints (not implemented)

| Proposed Endpoint | Method | Expected Request | Expected Response | Target Page |
|-------------------|--------|------------------|-------------------|-------------|
| `/deployments` | `GET` | Query: `?project=`, `?since=`, `?decision=`, `?page=` | Paginated list of deployment summaries | Dashboard, Analytics |
| `/deployments/metrics` | `GET` | Query: `?project=`, `?period=24h\|7d\|30d` | `{ total, safe, review, blocked, avgRisk, avgConfidence }` | Dashboard |
| `/agents/status` | `GET` | — | `{ agents: [{ name, status, latency_ms, region }] }` | Dashboard Agent Status panel |

### Deployment Detail Endpoints (not implemented)

| Proposed Endpoint | Method | Expected Request | Expected Response | Target Page |
|-------------------|--------|------------------|-------------------|-------------|
| `/deployments/{correlation_id}` | `GET` | Path: `correlation_id` | Full `FinalDecision` + webhook metadata (repo, PR title, author) | Deployments detail view |
| `/deployments/{correlation_id}/timeline` | `GET` | Path: `correlation_id` | Pipeline stage timestamps (Webhook → Gateway → Kafka → agents → Aggregator → Decision) | Deployments timeline |

> **Workaround today:** `GET /decision/{correlation_id}` provides the aggregated result and nested `agents`, but not webhook metadata or pipeline timestamps.

### Analytics Endpoints (not implemented)

| Proposed Endpoint | Method | Expected Request | Expected Response | Target Page |
|-------------------|--------|------------------|-------------------|-------------|
| `/analytics/summary` | `GET` | Query: `?range=7d\|14d\|30d\|90d` | `{ totalAnalyzed, avgRiskScore, avgConfidence, totalBlocked, trends }` | Analytics metric cards |
| `/analytics/volume` | `GET` | Query: `?range=` | Time-series: `{ date, safe, review, blocked }[]` | Analytics bar chart |
| `/analytics/decisions` | `GET` | Query: `?range=` | `{ SAFE, REVIEW, BLOCK }` counts | Analytics donut chart |
| `/analytics/blocks` | `GET` | Query: `?severity=`, `?search=` | Recent high-risk blocked deployments | Analytics blocks table |
| `/analytics/export` | `GET` | Query: `?range=`, `?format=csv` | CSV file stream | Analytics Export CSV button |

> **Workaround today:** `frontend/src/pages/Analytics.tsx` computes all metrics client-side from the local deployment cache.

### Incident History Endpoints (not implemented)

| Proposed Endpoint | Method | Expected Request | Expected Response | Target Page |
|-------------------|--------|------------------|-------------------|-------------|
| `/incidents` | `GET` | Query: `?search=`, `?severity=`, `?repo=`, `?since=`, `?page=` | Paginated incident archive from Qdrant | Incident History list |
| `/incidents/{incident_id}` | `GET` | Path: `incident_id` | Full incident document | Incident History detail panel |
| `/incidents/similarity` | `POST` | `{ "text": "deployment change description..." }` | Ranked `SimilarIncident[]` with scores | Incident History similarity playground |
| `/incidents` | `POST` | Manual incident report body | Created incident record | Incident History "Report Manual Incident" |

> **Workaround today:** Incident similarity runs inside the Kafka agent pipeline only. The integrated frontend's `api.calculateSimilarity()` is fully mocked in `frontend/src/api/client.ts`.

---

## Recommended Polling Pattern (Dashboard / Deployments)

For deployments triggered via the gateway:

```
1. POST /api/gateway/webhook/github          → receive correlation_id
2. Poll GET /api/aggregator/decision/{id}     → every 2–3 seconds
   - 202 + status:"pending"  → keep polling; optionally show collected_agents
   - 200 + decision field    → render final result
   - 404                     → expired or invalid id
3. Stop polling after timeout (~15s matches aggregator TIMEOUT_SECONDS=10 + buffer)
```

Implemented in: `frontend/src/pages/Dashboard.tsx` (lines 71–85) and `frontend/src/api/client.ts` (`getDecision`, `triggerDeployment`).

---

## Kafka Message Shapes (Non-HTTP, for Context)

These are not REST endpoints but define the data eventually surfaced through `GET /decision/{correlation_id}`.

### `deployment-events` topic (Gateway → Agents)

```json
{
  "correlation_id": "uuid",
  "payload": { /* GitHubWebhookPayload fields */ }
}
```

### `risk-results` topic (Agents → Aggregator)

Each agent publishes an `AgentResult`-shaped message (see model above).

### `deployment-decisions` topic (Aggregator → downstream)

Publishes the final `FinalDecision` object to Kafka (not directly consumed by the frontend today).

---

## Service Port Quick Reference

| Service | Host (Docker) | Host (Local Dev) | Path Prefix |
|---------|---------------|------------------|-------------|
| Gateway | `gateway:8000` | `localhost:8000` | `/api/gateway` |
| Aggregator | `aggregator:8002` | `localhost:8002` | `/api/aggregator` |
| Incident History health | `agent-incident-history:8080` | Not exposed | — |
| Frontend (nginx) | `frontend:80` | `localhost:3000` | — |
| Qdrant | `qdrant:6333` | `localhost:6333` | — (vector DB, no app REST) |
| Redis | `redis:6379` | `localhost:6379` | — (cache, no app REST) |

---

## Summary

| Category | Count |
|----------|-------|
| **FastAPI applications** | 3 (Gateway, Aggregator, Incident History health) |
| **Production HTTP endpoints** | 4 |
| **Endpoints consumed by integrated frontend today** | 2 (`POST /webhook/github`, `GET /decision/{id}`) |
| **Endpoints with no frontend consumer yet** | 2 (`GET /health` on Aggregator and Incident History agent) |
| **Frontend pages requiring future backend APIs** | Dashboard metrics, Analytics aggregates, Incident History CRUD/search |

The integrated `frontend/` app is the authoritative consumer of the real backend. The `stitch/*` pages are UI prototypes using in-memory mock data and should be wired to the same proxy paths when merged into the main application.
