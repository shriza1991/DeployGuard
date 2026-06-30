<<<<<<< HEAD
# DeployGuard AI

A skeleton scaffold for DeployGuard AI: an event-driven deployment risk assessment system.

## What is included

- `gateway`: FastAPI service that accepts simplified GitHub webhook payloads and publishes events to Kafka.
- `agent-code-risk`, `agent-infra-risk`, `agent-incident-history`: stub consumers that read from Kafka and publish dummy risk scores.
- `aggregator`: consumer that groups results by `correlation_id` in Redis and publishes final decisions.
- `docker-compose.yml`: Kafka (KRaft), Redis, Qdrant, frontend, gateway, agents, aggregator.

## Run locally

1. Start the environment:

```bash
cd DeployGuard
docker-compose up --build
```

2. Send a test webhook:

```bash
curl -X POST http://localhost:8000/webhook/github \
  -H 'Content-Type: application/json' \
  -d '{"action": "push", "repository": {"name": "example"}}'
```

3. Watch the logs for the aggregator publishing the final decision.

## Notes

- Kafka is run in KRaft mode with a single controller.
- Each consumer uses its own Kafka consumer group. This means all three stub agents will each receive every `deployment-events` message, which is required for parallel fan-out.
- Redis stores correlation state and a 10-second TTL to support timeout fallback.
- Qdrant is included in compose for later incident-history logic, but not yet used in the skeleton.
=======
# DeployGuard
Distributed microservices platform that uses Apache Kafka to orchestrate AI-powered agents for real-time deployment risk analysis. Evaluates code changes, infrastructure metrics, and incident history before generating a unified deployment risk score.
>>>>>>> ef84409f7cc9b730aa805c7e788f80813890c539
