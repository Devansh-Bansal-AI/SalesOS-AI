# SalesOS AI — System Architecture Specification

**Status**: **FROZEN** (Milestones 1–4 Finalized)  
**System Design**: Asynchronous Multi-Agent, Event-Driven, Microservices-Ready Monorepo  

---

## 1. High-Level System Architecture

```mermaid
flowchart TB
    classDef client fill:#1f2937,stroke:#60a5fa,stroke-width:2px,color:#fff;
    classDef gateway fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef core fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef async fill:#4c1d95,stroke:#c084fc,stroke-width:2px,color:#fff;
    classDef storage fill:#78350f,stroke:#fbbf24,stroke-width:2px,color:#fff;

    subgraph ClientLayer ["💻 Client Application (Next.js 15 App Router)"]
        direction LR
        Dashboard["📊 Dashboard"]
        CRM["👥 CRM & Leads"]
        Conversations["💬 Conversations"]
        Meetings["📅 Meetings"]
        AICenter["🤖 AI Control Center"]
    end
    class Dashboard,CRM,Conversations,Meetings,AICenter client;

    subgraph GatewayLayer ["⚡ API Gateway (FastAPI Async Core)"]
        direction LR
        Auth["🔒 JWT & Security"]
        Router["🔌 REST / WS Endpoints"]
        Middleware["🛡️ Telemetry & Logging"]
        Auth --> Router --> Middleware
    end
    class Auth,Router,Middleware gateway;

    subgraph CoreLayer ["🧠 Multi-Agent Execution & Workflow Engine"]
        direction TB
        Workflow["🔄 Lifecycle State Machine<br/>(NEW ➔ QUALIFIED ➔ BOOKED)"]
        Decisions["⚙️ Routing & Assignment Engine"]
        Agents["🤖 LangGraph Agents Ensemble<br/>(Enrich | Qualify | Outreach | Book)"]
        Workflow <--> Decisions <--> Agents
    end
    class Workflow,Decisions,Agents core;

    subgraph AsyncLayer ["📡 Task Queue & Event Bus"]
        direction LR
        RedisBus["📡 Redis 7 Event Bus"]
        CeleryWorker["⚙️ Celery Distributed Task Queue"]
        RedisBus <--> CeleryWorker
    end
    class RedisBus,CeleryWorker async;

    subgraph StorageLayer ["🗄️ Persistence & Intelligence Storage"]
        direction LR
        Postgres[("🐘 PostgreSQL 17<br/>(SQLAlchemy 2 ORM)")]
        Qdrant[("🔍 Qdrant Vector DB<br/>(RAG Embeddings)")]
        LLM["🤖 Multi-LLM Gateway<br/>(Gemini / OpenAI / Claude)"]
    end
    class Postgres,Qdrant,LLM storage;

    ClientLayer -->|"REST API / WebSockets"| GatewayLayer
    GatewayLayer --> CoreLayer
    CoreLayer --> AsyncLayer
    CoreLayer --> StorageLayer
    Agents --> LLM
```

---

## 2. Core Architectural Principles

1. **Determinism over Stochastic AI**: Business processes, state transitions, SLA breaches, and routing rules are 100% deterministic code. AI agents operate purely as advisory nodes inside workflows.
2. **Strict Layering**: Dependencies flow strictly downward (`API` ➔ `Services` ➔ `Workflows` ➔ `Decision Engine` ➔ `Agents` ➔ `Repositories` ➔ `Infrastructure`).
3. **Plugin Extensibility**: Agents, prompts, LLM providers, and tool providers are registered dynamically via registries (`AgentRegistry`, `PromptRegistry`, `ToolRegistry`).
4. **Human-in-the-Loop Guardrails**: High-value deals trigger approval gates before outreach dispatch.
5. **Full Auditability**: Every workflow state, decision rule evaluation, agent run, and API execution is recorded in persistent audit logs.

---

## 3. Data Model & Relationships

The database schema consists of 14 core PostgreSQL tables managed via SQLAlchemy 2 ORM and Alembic migrations:

- `users`: User accounts and roles.
- `organizations`: Multi-tenant organization boundaries.
- `leads`: Lead contact, firmographic, status, and score details.
- `companies`: Company profiles and technographic details.
- `activities`: Audit timeline log for CRM interactions.
- `agent_runs`: History of AI agent executions, inputs, outputs, tokens, latency.
- `api_keys`: Hashed organization API keys.
- `audit_logs`: Governance audit log.
- `conversations`: Multi-channel communication threads.
- `domain_events`: Persistent domain event store.
- `emails`: Outbound and inbound email records.
- `meetings`: Booked calendar demo events.
- `messages`: Individual email or chat messages.
- `workflow_instances`: Persisted state of deterministic workflow executions.
