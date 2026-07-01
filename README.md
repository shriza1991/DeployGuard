# DeployGuard

DeployGuard is an event-driven deployment risk analysis platform that ingests deployment-related events, fans them out to specialized analysis agents, and produces a consolidated risk decision before a change is shipped. The system combines deterministic rules, lightweight heuristics, and optional AI-assisted reasoning to help teams assess code changes, infrastructure conditions, and historical incident context in one workflow.

## What DeployGuard does

DeployGuard is designed to answer a simple but important question before deployment:

> "How risky is this change, and what should we pay attention to before rollout?"

To answer that, the platform performs the following steps:

1. Accepts a deployment event from a webhook or other upstream source.
2. Publishes the event to Apache Kafka so multiple agents can process it in parallel.
3. Runs independent analysis agents for:
   - code risk,
   - infrastructure risk,
   - incident-history similarity.
4. Correlates all results by a shared correlation ID.
5. Aggregates the findings into a final deployment decision and publishes it to Kafka.

## System architecture

```text
Client / GitHub webhook
        │
        ▼
   Gateway (FastAPI)
        │
        ▼
   Kafka topic: deployment-events
        │
   ┌────┼───────────────────────┐
   ▼    ▼                       ▼
Code Risk Agent           Infra Risk Agent
   │                         │
   ▼                         ▼
Kafka topic: risk-results   Kafka topic: risk-results
   └──────────────┬──────────────────────┘
                  ▼
         Incident History Agent
                  │
                  ▼
        Kafka topic: risk-results
                  │
                  ▼
            Aggregator
                  │
           Redis + timeout logic
                  │
                  ▼
     Kafka topic: risk-decisions
```

## Core components

### 1. Gateway

Location: [gateway/app.py](gateway/app.py)

The gateway is a FastAPI service that exposes an endpoint at `/webhook/github` and accepts a simplified GitHub-style webhook payload. It generates a correlation ID, wraps the payload into an event, and publishes it to the Kafka topic `deployment-events`.

Responsibilities:

- accept incoming deployment-related events,
- generate a correlation ID for traceability,
- publish the event to Kafka,
- return a confirmation response to the caller.

### 2. Code Risk Agent

Location: [agent-code-risk/app.py](agent-code-risk/app.py)

This agent consumes deployment events and performs deterministic code-change analysis. It inspects the actual patch content and uses a set of analyzers to detect common deployment risks such as:

- security-sensitive changes,
- authentication and access-control modifications,
- database schema or migration changes,
- infrastructure configuration edits,
- large or broad changes,
- removal of validation logic,
- credential or secret exposure,
- changes to critical deployment or infrastructure files.

It produces a risk score, severity, confidence, reasons, recommendations, and metadata, then publishes the result to the `risk-results` topic.

The agent also includes an optional AI reasoning layer in [agent-code-risk/llm_reasoner.py](agent-code-risk/llm_reasoner.py). If an LLM provider is configured, it can add contextual commentary without overriding the deterministic score.

### 3. Infrastructure Risk Agent

Location: [agent-infra-risk/app.py](agent-infra-risk/app.py)

This agent evaluates infrastructure-related deployment risk using heuristics such as:

- deployment time window risk,
- simulated CPU usage,
- simulated error rate,
- simulated latency,
- production environment sensitivity,
- hotfix conditions.

It publishes a structured infrastructure assessment to `risk-results`.

### 4. Incident History Agent

Location: [agent-incident-history/app.py](agent-incident-history/app.py)

This agent looks at the deployment description and compares it against historical incident context. It uses a lightweight embedding-based approach and queries Qdrant for similar incident descriptions. The result includes:

- similarity score,
- number of matched incidents,
- a text snippet of the current description,
- availability information for the vector store.

### 5. Aggregator

Location: [aggregator/app.py](aggregator/app.py)

The aggregator listens for results on `risk-results`, groups them by `correlation_id`, and stores them in Redis. It waits until all expected agents have contributed results or until a timeout expires. Once complete, it publishes a final deployment decision to the `risk-decisions` topic.

Responsibilities:

- correlate agent output,
- manage partial or timed-out results,
- compute a combined final score,
- publish a final decision event.

## Data flow

1. A webhook is posted to the gateway.
2. The gateway publishes an event to Kafka.
3. Each agent receives the event from the same topic using its own consumer group.
4. Each agent publishes a result to the shared `risk-results` topic.
5. The aggregator assembles all results for the same correlation ID.
6. A final decision is emitted when enough evidence is collected or the timeout is hit.

## Runtime services

The stack is orchestrated by Docker Compose and includes:

- Kafka in KRaft mode for event streaming,
- Redis for aggregation state and timeout tracking,
- Qdrant for incident similarity lookup,
- a static frontend served via Nginx,
- the gateway,
- the three analysis agents,
- the aggregator.

See [docker-compose.yml](docker-compose.yml) for full service definitions and ports.

## Local development and deployment

### Prerequisites

- Docker
- Docker Compose
- Python 3.11+ (optional, if you want to run services outside containers)

### Start the full stack

```bash
docker compose up --build
```

This will start the infrastructure and the application services together.

### Send a sample event

```bash
curl -X POST http://localhost:8000/webhook/github \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "opened",
    "repository": {
      "name": "demo-app",
      "full_name": "acme/demo-app"
    },
    "pull_request": {
      "title": "Rotate API keys for staging",
      "body": "Please review carefully before deployment.",
      "user": {
        "login": "alice"
      }
    }
  }'
```

The response will include a `correlation_id` that you can use to trace the workflow in the logs or downstream topics.

### Watch the pipeline

Useful commands:

```bash
docker compose ps
docker logs -f deployguard_agent_code_risk
docker logs -f deployguard_aggregator
```

## Configuration

The services use environment variables for runtime behavior.

### Shared

- `KAFKA_BROKER`: Kafka bootstrap server, default `kafka:9092`

### Code Risk Agent

- `LLM_PROVIDER`: optional LLM provider (`openai`, `gemini`, `local`, `ollama`, `lmstudio`, or `disabled`)
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `LOCAL_LLM_URL`, `LOCAL_LLM_MODEL`
- `GITHUB_TOKEN`: optional token used to fetch PR file patches from GitHub

### Infrastructure Risk Agent

- `SIMULATED_CPU`
- `SIMULATED_ERROR_RATE`
- `SIMULATED_LATENCY`

### Incident History Agent

- `QDRANT_URL`: default `http://qdrant:6333`

### Aggregator

- `REDIS_URL`: default `redis://redis:6379/0`

## Event and output examples

### Incoming webhook event

```json
{
  "correlation_id": "uuid",
  "payload": {
    "action": "opened",
    "repository": {
      "name": "demo-app"
    },
    "pull_request": {
      "title": "Rotate API keys for staging",
      "body": "Please review carefully before deployment."
    }
  }
}
```

### Agent result example

```json
{
  "agent": "code-risk",
  "correlation_id": "uuid",
  "score": 42,
  "severity": "medium",
  "confidence": 0.8,
  "reasons": [
    "Security-sensitive terms were introduced or modified in the patch."
  ],
  "recommendations": [
    "Review the affected code paths for access control, encryption, and privilege handling."
  ],
  "metadata": {
    "changed_files": 3,
    "changed_lines": 42
  }
}
```

### Final decision example

```json
{
  "correlation_id": "uuid",
  "results": [
    { "agent": "code-risk", "score": 42 },
    { "agent": "infra-risk", "score": 63 },
    { "agent": "incident-history", "score": 35 }
  ],
  "final_score": 46.67,
  "status": "complete"
}
```

## Current implementation notes

- The code-risk agent is currently deterministic and rule-based by default.
- AI reasoning is optional and conservative; it enriches the analysis without replacing the deterministic findings.
- The infrastructure and incident-history agents use heuristic models suitable for local demo and simulation scenarios.
- The system is intentionally modular so that each agent can be upgraded independently over time.

## Project structure

```text
agent-code-risk/      Code risk analysis agent and analyzers
agent-infra-risk/     Infrastructure heuristics agent
agent-incident-history/ Incident similarity agent using Qdrant
aggregator/           Correlates and aggregates results
gateway/              FastAPI webhook gateway
frontend/             Static frontend assets
docs/                 Documentation and supporting materials
```

## Roadmap

Possible future improvements include:

- richer GitHub integration with live PR file fetching and richer metadata,
- stronger incident-history indexing and retrieval,
- more advanced policy and compliance rules,
- dashboard and UI enhancements,
- persistence of decisions and audit history,
- support for deployment approvals and workflow automation.
