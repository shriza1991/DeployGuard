# DeployGuard

> AI-Powered Multi-Agent DevSecOps Deployment Risk Assessment Platform

DeployGuard is an intelligent DevSecOps platform that evaluates software deployments before they reach production. Instead of relying on a single static analysis tool, DeployGuard orchestrates multiple specialized AI agents that independently analyze different aspects of a deployment, aggregates their findings, and produces a unified deployment risk assessment.

The platform is designed around an event-driven architecture using Kafka, Redis, FastAPI, Docker, and Large Language Models (LLMs), enabling scalable, asynchronous, and modular deployment analysis.

---

# Features

- **Multi-Agent AI Deployment Analysis** (Code, Infrastructure, and Historical Incident similarities)
- **Event-Driven Pipeline** powered by Apache Kafka
- **Codebase Indexing & Semantic Context Retrieval** via the stand-alone **Repository Context Service**
- **AI-powered Code Risk Detection** and Security Anti-pattern analysis
- **Infrastructure Security Scanning** (Docker, K8s, Terraform, Actions)
- **Historical Incident Similarity Search** using Qdrant vector database
- **Intelligent Risk Aggregation Engine** with custom decision weights
- **Real-Time Deployment Dashboard** and interactive analytics
- **Rich Frontend Pages:** System Health metrics, Webhook Simulator, Settings, Reports, and Agents overview
- **High-fidelity Bento UI Prototypes** (Stitch)
- **Redis-backed State Persistence** for temporary and final decisions

---

# Architecture

DeployGuard uses an event-driven pipeline combined with HTTP semantic context retrieval.

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
             │ (HTTP Context query)  │                        │ (Similarity Search)
             ▼                       │                        ▼
  Repository Context Service         │                Qdrant Vector DB
(Clones, Embeds & Chunks Code)       │              (Incident Collection)
             │                       │                        ▲
             ├── [Queries Redis/     │                        │
             │    Qdrant for code]   │                        │
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
                            FastAPI REST APIs
                                     │
                                     ▼
                              React Frontend
```

---

# Tech Stack

### Backend & Orchestration
- **FastAPI / Uvicorn:** Core API framework for services
- **Apache Kafka:** Event streaming and messaging broker
- **Redis:** Metadata cache, pipeline staging, and final decisions
- **Docker Compose:** Multi-container orchestration

### AI & Machine Learning
- **Google Gemini:** LLM provider for code risk and infra reasoning
- **Sentence-Transformers:** Semantic vector embedding generation (`all-MiniLM-L6-v2`)
- **Qdrant:** Vector database for semantic code search and incident logs

### Frontend
- **React + TSX:** Interactive UI dashboard
- **Vite:** High-performance build tool
- **Tailwind CSS:** Modern utility-first styling
- **Recharts:** Interactive data visualization charts

---

# Services & Components

### 1. Gateway
Acts as the entry point, ingesting GitHub pull request events or manual webhook payloads and publishing them as `deployment-events` on Kafka.

### 2. Repository Context Service
A stand-alone microservice providing semantic code context to AI agents:
- **Git Cloning:** Clones target git repositories dynamically.
- **AST-Aware Chunking:** Partitions source code and configs into overlapping text tokens.
- **Embedding Generation:** Converts chunks into vector representations via sentence-transformers.
- **Vector Search:** Exposes a semantic search interface for finding specific code behaviors.
- **Technology Manifests:** Detects languages, libraries, and frameworks, writing metadata to Redis.

### 3. Code Risk Agent
Consumes `deployment-events`, queries the Repository Context Service for code background context, and invokes Gemini to analyze changed files for security flaws, auth bypasses, and validation defects.

### 4. Infrastructure Risk Agent
Consumes `deployment-events` and scans environment configurations (Dockerfiles, Docker Compose, Terraform, Kubernetes manifests) for misconfigurations, privileged mode usage, and hardcoded secrets.

### 5. Incident History Agent
Consumes `deployment-events`, generates semantic embeddings of the patch, and performs similarity queries against historical post-mortems stored in Qdrant.

### 6. Aggregator Service
Collects individual agent reports from Kafka, evaluates overall risk score weights, computes final decisions (`SAFE`, `REVIEW`, `BLOCK`), and exposes them via REST APIs.

---

# REST APIs

### Gateway & Ingestion
| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/webhook/github` | Ingests GitHub webhook events |

### Deployments & Decisions
| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/deployments` | List paginated deployment summaries |
| GET | `/deployments/{correlation_id}` | Retrieve full deployment details |
| GET | `/deployments/{correlation_id}/timeline` | Retrieve pipeline processing steps & timestamps |
| GET | `/deployments/metrics` | Fetch dashboard counter statistics |
| GET | `/decision/{correlation_id}` | Retrieve final aggregated decision |

### Analytics
| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/analytics/summary` | Fetch period volume, average score, and trends |
| GET | `/analytics/volume` | Fetch daily deployment decision volume |
| GET | `/analytics/decisions` | Fetch distribution counts of SAFE, REVIEW, BLOCK |
| GET | `/analytics/blocks` | List recent blocked deployments and threat causes |
| GET | `/analytics/export` | Export analytic history as a CSV file |

### Incidents
| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/incidents` | List historical incident records |
| GET | `/incidents/{incident_id}` | Retrieve specific incident details |
| POST | `/incidents` | Report a manual post-mortem incident |
| POST | `/incidents/similarity` | Search similarity against historical incidents |

### Agent & System Status
| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/agents/status` | Retrieve latency and online status of AI agents |
| GET | `/health` | Diagnostic status for gateway, aggregator, and agents |

### Repository Context Service (Port 8003)
| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/repository/index` | Clones and indexes a git repository |
| GET | `/repository/status/{repository}` | Get repository indexing status |
| GET | `/repository/manifest/{repository}` | Get repository language/tech manifest |
| DELETE | `/repository/index/{repository}` | Purge repository embeddings and metadata |
| POST | `/repository/search` | Raw semantic search on codebase |
| POST | `/repository/context` | Fetch contextual code blocks using git diff |

---

# Project Structure

```
DeployGuard/
├── gateway/                    # REST gateway, webhook ingestion
├── aggregator/                 # Risk aggregator & analytics endpoints
├── agent-code-risk/            # AI Code Risk Agent
├── agent-infra-risk/           # AI Infrastructure Agent
├── agent-incident-history/     # AI Incident History Similarity Agent
├── repository-context-service/ # Code indexing and vector retrieval microservice
├── frontend/                   # Main React/Vite dashboard app
├── stitch/                     # High-fidelity bento design prototypes
├── docker-compose.yml          # Docker compose orchestration for backing stores
├── README.md                   # Main project documentation
└── docs/                       # Architectural docs & maps
```

---

# Stitch Design Prototypes

The workspace includes interactive design prototypes under the `stitch/` directory:
- **Dashboard Page (`stitch/dashboard_page/`):** Bento-grid style layout summarizing active agent statuses, recent deployments, and system health metrics.
- **Deployments Page (`stitch/deployments_page/`):** Detail screen prototypes highlighting agent decisions, severity cards, and deployment timeline steps.
- **Analytics Page (`stitch/analytics_page/`):** Visualizations for average risk score, overall decision distribution, and CSV export.
- **Incident History Page (`stitch/incident_history_page/`):** Semantic similarity playground and manual incident reporting panel.

---

# Running the Project

### Prerequisites
- Docker & Docker Compose
- Node.js (for frontend local dev)
- Gemini API Key (configured in environment)

### 1. Environment Configuration
Copy `.env.example` to `.env` and fill in the variables:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 2. Start Core Infrastructure & Orchestrated Backend
```bash
docker compose up --build
```

### 3. Run Repository Context Service
```bash
cd repository-context-service
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8003
```

### 4. Run Frontend Locally (Development)
```bash
cd frontend
npm install
npm run dev
```

---

# Current Status

### Backend & Services
- Gateway ✔
- Event-Driven Kafka Channels ✔
- Redis Storage Engine ✔
- Aggregator & Decision Weighting ✔
- REST API (Deployments, Analytics, Incidents, Agents) ✔
- Repository Context Service ✔

### AI Agents
- Code Risk Agent (with Repository Context Integration) ✔
- Infrastructure Risk Agent ✔
- Incident History Agent (with Qdrant Search) ✔

### Frontend
- Dashboard ✔
- Deployments & Details ✔
- Analytics & Trends ✔
- Webhook Simulator ✔
- System Health Monitor ✔
- Settings ✔
- Incident History Playground ✔
- High-fidelity Bento UI Prototypes (Stitch) ✔

---

# Future Improvements
- Integrate Repository Context Service into the main Docker Compose configurations
- User Authentication & Role-Based Access Control (RBAC)
- GitHub OAuth Authentication
- Notification webhooks (Slack, MS Teams, Email)
- CI/CD Actions/Pipeline integration
- Trend forecasting & risk prediction models

---

# License
This project is intended for educational, research, and demonstration purposes.