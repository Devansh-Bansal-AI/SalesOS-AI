# SalesOS AI

**AI-Powered Sales Operations Platform**

SalesOS AI is a production-ready, multi-agent AI Sales Operations Platform that automates the complete customer acquisition lifecycle. The platform combines specialized AI agents, workflow orchestration, CRM integration, and analytics to enable organizations to respond to leads faster, improve sales productivity, and increase conversion rates.

## Architecture

```
Internet → API Gateway (FastAPI) → Decision Engine → LangGraph Agents → Database
```

- **Backend:** FastAPI + SQLAlchemy 2 + Pydantic v2
- **Frontend:** Next.js 15 + React 19 + TypeScript + TailwindCSS + ShadCN UI
- **Database:** PostgreSQL 17 + Redis 7 + Qdrant
- **AI:** LangGraph + Gemini (primary) + OpenAI/Claude (secondary)
- **Background Jobs:** Celery + Redis
- **Deployment:** Docker Compose (dev) → Kubernetes (production)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd salesos-ai

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Start infrastructure services
make up

# Run database migrations
make migrate

# Start backend
make dev-backend

# Start frontend (new terminal)
make dev-frontend
```

### Available Commands

```bash
make help          # Show all available commands
make up            # Start Docker services
make down          # Stop Docker services
make dev-backend   # Run backend dev server
make dev-frontend  # Run frontend dev server
make test          # Run all tests
make lint          # Lint code
make migrate       # Run migrations
```

## Project Structure

```
salesos-ai/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── core/      # Config, security, logging
│   │   ├── db/        # Database connections
│   │   ├── models/    # SQLAlchemy ORM models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── repositories/  # Data access layer
│   │   ├── services/  # Business logic
│   │   ├── agents/    # AI agent implementations
│   │   ├── workflows/ # LangGraph workflows
│   │   ├── events/    # Event bus system
│   │   └── prompts/   # Versioned prompt templates
│   └── tests/
├── frontend/          # Next.js frontend
├── docker/            # Docker configuration
└── docs/              # Documentation
```

## Engineering Principles

1. AI is advisory, not absolute
2. Business logic is deterministic
3. Agents have single responsibilities
4. Every action is auditable
5. LLM-provider independence
6. Security by design
7. API-first architecture
8. Scalability over shortcuts
9. Modularity
10. Observability

## License

Proprietary — All rights reserved.
