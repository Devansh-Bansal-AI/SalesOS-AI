# SalesOS AI — Autonomous AI Sales Operations Platform

[![GitHub](https://img.shields.io/badge/GitHub-Devansh--Bansal--AI%2FSalesOS--AI-181717?logo=github)](https://github.com/Devansh-Bansal-AI/SalesOS-AI)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15.0+-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17+-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)

**SalesOS AI** is an enterprise-grade, autonomous, multi-agent Sales Operations (SalesOps) platform designed to automate the end-to-end B2B customer acquisition lifecycle. By orchestrating specialized AI agents alongside deterministic workflow engines, SalesOS AI acts as an autonomous Sales Development Representative (SDR) and Sales Engineer — turning raw leads into booked meetings and qualified revenue opportunities.

---

## 🎯 What We Are Building (End-State Vision)

The goal of **SalesOS AI** is to replace fragmented sales tools and manual data entry with an **intelligent, self-operating sales system**.

```
                           ┌────────────────────────────────────────────────────────┐
                           │                     SalesOS AI                         │
                           └────────────────────────────────────────────────────────┘
                                                       │
  ┌─────────────────┐       ┌──────────────────────────┴──────────────────────────┐       ┌─────────────────┐
  │  Inbound Leads  │ ───►  │                  Autonomous Engine                  │ ───►  │  Booked Demos   │
  │ (Forms, APIs)   │       │  Enrich ──► Qualify ──► Outreach ──► Book Meeting   │       │  & Closed Deals │
  └─────────────────┘       └─────────────────────────────────────────────────────┘       └─────────────────┘
```

### 🧠 Core Autonomous AI Agents

1. 🔍 **Lead Enrichment Agent**
   - Automatically scrapes and aggregates firmographic, technographic, and contact intelligence for new inbound/outbound leads.
   - Integrates company insights, tech stack signals, and industry trends into lead profiles.

2. 📊 **Lead Qualification Agent**
   - Evaluates lead fit using BANT (Budget, Authority, Need, Timeline) and ideal customer profile (ICP) scoring models.
   - Dynamically calculates lead priority scores and routes qualified leads to the optimal sales rep or workflow.

3. ✉️ **Outreach & Communication Agent**
   - Crafts hyper-personalized cold emails, multi-touch sequence follow-ups, and contextual responses.
   - Handles multi-turn email objection handling autonomously while respecting brand guidelines.

4. 📅 **Booking & Scheduling Agent**
   - Coordinates demo booking by inspecting sales rep calendar availability in real time.
   - Handles scheduling links, timezone matching, and calendar invite generation.

5. 💡 **Conversation Intelligence Agent**
   - Analyzes email chains, call transcripts, and chat logs for buyer sentiment, intent signals, and deal health.
   - Recommends next best actions (NBAs) and flags deal risks or SLA breaches to human managers.

---

## 🚀 Key Features & Capabilities

- 🔄 **Event-Driven Lead Lifecycle State Machine**: Full lead lifecycle tracking (`NEW` ➔ `ENRICHED` ➔ `QUALIFIED` ➔ `CONTACTED` ➔ `MEETING_BOOKED` ➔ `CLOSED_WON` / `UNQUALIFIED`).
- 👥 **Rep Assignment & Territory Routing Engine**: Automated distribution of leads based on rep availability, territory rules, and SLA requirements.
- 🚨 **SLA Monitoring & Escalation System**: Real-time background workers that flag unhandled high-priority leads and trigger manager escalations.
- 🛡️ **Human-in-the-Loop (HITL) Guardrails**: Configurable safety gates for high-value leads allowing reps to review and approve AI outreach before sending.
- 🤖 **LLM Agnostic Architecture**: Primary support for Google Gemini with instant fallback support for OpenAI and Anthropic Claude models.
- 💻 **Modern Workspace Web Application**: Next.js 15 command center featuring real-time dashboards, CRM lead management, conversation threads, meeting schedulers, and AI agent monitoring.

---

## 🏗️ Technical Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             Frontend (Next.js 15 / React 19)                             │
│       Dashboard  │  Leads & CRM  │  Conversations  │  Meetings  │  AI Control Center   │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ REST API / WebSockets
┌────────────────────────────────────────▼─────────────────────────────────────────┐
│                              Backend Gateway (FastAPI)                            │
│           Auth & Security  │  Route Handlers  │  Pydantic V2 Schemas                 │
└──────┬─────────────────────────────────┬──────────────────────────────────┬──────┘
       │                                 │                                  │
┌──────▼─────────────────┐     ┌─────────▼─────────────────┐     ┌──────────▼───────────┐
│   Workflow Engine      │     │    Multi-Agent System     │     │   Background Tasks   │
│ (State Machine/Events) │ ──► │  (Enrich/Qualify/Book)    │ ◄── │  (Celery + Workers)  │
└──────┬─────────────────┘     └─────────┬─────────────────┘     └──────────┬───────────┘
       │                                 │                                  │
┌──────▼─────────────────────────────────▼──────────────────────────────────▼───────┐
│                                   Data & Storage                                 │
│    PostgreSQL 17 (ORM)   │   Redis 7 (Cache/Events)   │   Qdrant (Vector RAG)     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Backend API** | Python 3.12 / FastAPI | High-performance asynchronous REST API framework |
| **Database** | PostgreSQL 17 + SQLAlchemy 2 | Relational storage with async ORM & Alembic migrations |
| **Caching & Queues** | Redis 7 + Celery | Event bus, token storage, and distributed background tasks |
| **Vector DB** | Qdrant | Vector embeddings & RAG semantic search for sales knowledge |
| **AI Framework** | LangGraph + Gemini / OpenAI / Claude | Multi-agent state orchestration & prompt management |
| **Frontend** | Next.js 15 / React 19 / TailwindCSS | Modern workspace UI with dark mode & dynamic analytics |
| **Containerization** | Docker & Docker Compose | Containerized dev/prod infrastructure management |

---

## 📂 Repository Structure

```text
SalesOS-AI/
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── agents/           # Specialized AI agents (Enrichment, Qualification, Outreach, Booking)
│   │   ├── api/v1/           # FastAPI REST endpoints (Auth, Leads, Conversations, Meetings)
│   │   ├── core/             # Configuration, security, logging, telemetry
│   │   ├── db/               # PostgreSQL, Redis, and Qdrant session managers
│   │   ├── events/           # Event bus & communication handlers
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # Core business logic & decision engines
│   │   ├── tasks/            # Celery task definitions
│   │   └── workflows/        # Lead lifecycle state machine
│   ├── tests/                # Unit and integration test suites
│   ├── pyproject.toml        # Dependencies & package configuration
│   └── uv.lock               # uv lockfile for deterministic builds
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router (Dashboard, Leads, Conversations, Meetings, AI)
│   │   ├── components/       # UI components & workspace layout
│   │   └── lib/              # API client, auth utilities, custom hooks
│   └── package.json
├── docker/                   # Dockerfiles for Backend, Frontend, and Celery Worker
├── Makefile                  # Helper commands for local dev workflow
├── .env.example              # Template environment configuration
└── README.md                 # Project documentation
```

---

## ⚡ Quick Start & Development Setup

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [Python 3.12+](https://www.python.org/)
- [Node.js 20+](https://nodejs.org/)

### 1. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/Devansh-Bansal-AI/SalesOS-AI.git
cd SalesOS-AI

# Create environment configuration
cp .env.example .env
# Edit .env and configure your GEMINI_API_KEY / Database settings
```

### 2. Launch Infrastructure Services

```bash
# Spin up PostgreSQL, Redis, Qdrant & Celery services via Docker
make up

# Apply database migrations
make migrate
```

### 3. Run Development Servers

In terminal 1 (Backend API):
```bash
make dev-backend
```
*(API will be live at `http://localhost:8000/docs`)*

In terminal 2 (Frontend Web App):
```bash
make dev-frontend
```
*(Workspace App will be live at `http://localhost:3000`)*

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

