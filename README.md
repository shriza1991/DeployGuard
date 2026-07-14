# DeployGuard

> AI-Powered Multi-Agent DevSecOps Deployment Risk Assessment Platform

DeployGuard is an intelligent DevSecOps platform that evaluates software deployments before they reach production. Instead of relying on a single static analysis tool, DeployGuard orchestrates multiple specialized AI agents that independently analyze different aspects of a deployment, aggregates their findings, and produces a unified deployment risk assessment.

The platform is designed around an event-driven architecture using Kafka, Redis, FastAPI, Docker, and Large Language Models (LLMs), enabling scalable, asynchronous, and modular deployment analysis.

---

# Features

- Multi-Agent AI Deployment Analysis
- Event-Driven Architecture using Apache Kafka
- AI-powered Code Risk Detection
- Infrastructure Security Analysis
- Historical Incident Similarity Search
- Intelligent Risk Aggregation Engine
- Real-Time Deployment Dashboard
- Deployment History & Detailed Reports
- Analytics & Risk Metrics
- Redis-backed Data Persistence
- Dockerized Microservice Architecture
- REST API for Frontend Integration

---

# Architecture

```
                        GitHub PR / Webhook
                                │
                                ▼
                        Gateway (FastAPI)
                                │
                                ▼
                     Kafka Topic (deployment-events)
                                │
        ┌───────────────────────┼────────────────────────┐
        │                       │                        │
        ▼                       ▼                        ▼
 Code Risk Agent         Infra Risk Agent      Incident History Agent
        │                       │                        │
        └───────────────────────┼────────────────────────┘
                                ▼
                     Kafka Topic (risk-results)
                                │
                                ▼
                        Aggregator Service
                                │
                 Decision Engine + Redis Storage
                                │
                                ▼
                       FastAPI REST Endpoints
                                │
                                ▼
                         React Frontend
```

---

# Tech Stack

## Backend

- FastAPI
- Python
- Apache Kafka
- Redis
- Docker Compose

## AI & Machine Learning

- Google Gemini
- Vector Embeddings
- Qdrant Vector Database

## Frontend

- React
- Vite
- Tailwind CSS
- Recharts

## Infrastructure

- Docker
- Kafka
- Redis
- Qdrant

---

# Multi-Agent System

DeployGuard consists of three independent AI agents that analyze every deployment.

## Code Risk Agent

Analyzes application source code for:

- Authentication issues
- Removed validations
- Dangerous code modifications
- Security anti-patterns
- Risky business logic

Outputs:

- Risk Score
- Severity
- Confidence
- Recommendations
- Explanation

---

## Infrastructure Risk Agent

Evaluates deployment infrastructure including:

- Docker
- Kubernetes
- Terraform
- Docker Compose
- GitHub Actions
- Infrastructure Secrets

Detects issues such as:

- Privileged containers
- Public cloud resources
- Open security groups
- Root containers
- Hardcoded credentials
- Misconfigured infrastructure

Outputs:

- Risk Score
- Severity
- Confidence
- Recommendations

---

## Incident History Agent

Uses semantic similarity search over historical deployment incidents.

Pipeline:

Deployment →
Embedding Generation →
Qdrant Similarity Search →
LLM Analysis →
Recommendations

Outputs:

- Similar historical incidents
- Similarity confidence
- Lessons learned
- Preventive recommendations

---

# Aggregation Engine

The Aggregator waits until every agent has submitted its analysis.

Once all results are available, the Decision Engine:

- Collects agent outputs
- Computes overall deployment risk
- Determines deployment decision
- Generates recommendations
- Stores results in Redis
- Exposes final decision through REST APIs

Possible deployment decisions include:

- APPROVED
- REVIEW
- BLOCKED

---

# Event Flow

```
GitHub Webhook
        │
        ▼
Gateway
        │
        ▼
Kafka (deployment-events)
        │
        ▼
AI Agents
        │
        ▼
Kafka (risk-results)
        │
        ▼
Aggregator
        │
        ▼
Decision Engine
        │
        ▼
Redis
        │
        ▼
REST APIs
        │
        ▼
Frontend Dashboard
```

---

# REST APIs

## Deployments

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/deployments` | List all deployments |
| GET | `/deployments/{correlation_id}` | Deployment details |
| GET | `/deployments/metrics` | Dashboard metrics |

---

## Analytics

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/analytics/summary` | Overall deployment statistics |
| GET | `/analytics/volume` | Deployment volume over time |
| GET | `/analytics/decisions` | Decision distribution |
| GET | `/analytics/blocks` | Blocked deployment analytics |
| GET | `/analytics/export` | Export analytics as CSV |

---

## Decision

| Method | Endpoint |
|---------|----------|
| GET | `/decision/{correlation_id}` |

---

# Dashboard

The Dashboard provides an operational overview of deployment health.

Features include:

- Total Deployments
- Approved Deployments
- Blocked Deployments
- Average Risk Score
- Recent Deployments
- Overall Deployment Status

---

# Deployment Details

Each deployment contains:

- Repository Information
- Author
- Commit Metadata
- Risk Score
- Deployment Decision
- AI Agent Results
- Recommendations
- Historical Incident Matches

---

# Analytics

The Analytics module provides deployment insights through interactive visualizations.

Available metrics include:

- Deployment Volume
- Average Risk Score
- Average Confidence
- Decision Distribution
- Blocked Deployments
- Historical Trends

---

# Redis Data Model

Deployment metadata:

```
meta:<correlation_id>
```

Final deployment decisions:

```
decision:<correlation_id>
```

Temporary aggregation state is automatically cleaned after successful processing.

---

# Running the Project

Clone the repository:

```bash
git clone <repository-url>
cd DeployGuard
```

Start all services:

```bash
docker compose up --build
```

Services started include:

- Gateway
- Aggregator
- Code Risk Agent
- Infrastructure Risk Agent
- Incident History Agent
- Kafka
- Redis
- Qdrant
- Frontend

---

# Project Structure

```
DeployGuard/

├── gateway/
├── aggregator/
├── agents/
│   ├── code-risk/
│   ├── infra-risk/
│   └── incident-history/
├── frontend/
├── shared/
├── docker-compose.yml
├── README.md
└── docs/
```

---

# Current Status

## Backend

- Gateway ✔
- Kafka Integration ✔
- Redis Integration ✔
- Aggregator ✔
- Decision Engine ✔
- REST APIs ✔
- Multi-Agent Pipeline ✔

## Frontend

- Dashboard ✔
- Deployments ✔
- Deployment Details ✔
- Analytics (In Progress)

---

# Future Improvements

- User Authentication & Role-Based Access Control
- GitHub OAuth Integration
- Slack & Microsoft Teams Notifications
- Email Alerting
- CI/CD Pipeline Integrations
- Risk Trend Forecasting
- Explainable AI (XAI) Visualizations
- Multi-Repository Support
- Policy-Based Deployment Rules

---

# Contributors

Built as part of an AI-powered DevSecOps platform demonstrating event-driven architecture, multi-agent orchestration, LLM integration, and modern cloud-native deployment analysis.

---

# License

This project is intended for educational, research, and demonstration purposes.