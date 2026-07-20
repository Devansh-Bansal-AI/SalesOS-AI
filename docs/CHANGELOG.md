# SalesOS AI — Project Changelog

All notable changes, architectural decisions, and milestone completions for SalesOS AI are documented in this file.

---

## [Unreleased] — Milestone 6 Development

### Added
- **Task 6.2 (MCP Tool Providers Implementation)**:
  - Implemented `SalesOSCompanyResearchProvider` in `app/agents/tools/company_research.py` conforming strictly to `CompanyResearchToolProvider` (firmographic & technographic research synthesis, zero lead scoring/qualification logic).
  - Implemented `SalesOSCalendarProvider` in `app/agents/tools/calendar.py` conforming strictly to `CalendarToolProvider` (pure slot calculation & meeting CRUD, zero working hours policy logic).
  - Added `capabilities()` declaration to `CompanyResearchToolProvider` interface.
  - Registered `SalesOSCompanyResearchProvider` and `SalesOSCalendarProvider` in `app/main.py` lifespan startup.
- **Task 6.1 (Qdrant Vector Memory Integration)**:
  - Created `app/db/qdrant.py` AsyncQdrantClient lifecycle manager and collection setup validator.
  - Implemented `QdrantKnowledgeBaseProvider` in `app/agents/tools/qdrant_kb.py` conforming strictly to `KnowledgeBaseToolProvider`.
  - Added support for configurable collection names (`salesos_knowledge_base`, `conversation_memory`, etc.).
  - Added rich standardized vector payload metadata (`organization_id`, `lead_id`, `conversation_id`, `message_id`, `agent`, `timestamp`, `embedding_version`, `source`).
  - Registered `QdrantKnowledgeBaseProvider` in `app/main.py` lifespan startup and shutdown hooks.
- Created comprehensive documentation suite in `docs/`:
  - `PROJECT_RECOVERY.md` (Architecture freeze & recovery audit)
  - `CURRENT_STATUS.md` (Active development status)
  - `MILESTONE_TRACKER.md` (Milestone progress matrix)
  - `ARCHITECTURE.md` (System architecture & data model specifications)
  - `ADR.md` (Architectural Decision Records ADR-001 through ADR-007)
  - `CHANGELOG.md` (Version & feature log)
  - `ROADMAP.md` (Future vision & milestone targets)

---

## [1.0.0-m5] — 2026-07-20

### Added
- **Workspace Web UI**: Next.js 15 App Router workspace command center (`dashboard`, `leads`, `conversations`, `meetings`, `ai`, `crm`, `settings`).
- **REST API Routes**: Full FastAPI routers for `auth`, `leads`, `conversations`, `meetings`, `sales_execution`, and `public`.
- **Multi-Agent Core**: 5 core AI agents (`QualificationAgent`, `EnrichmentAgent`, `OutreachAgent`, `BookingAgent`, `ConversationIntelligenceAgent`).
- **Deterministic Workflow Engine**: `engine.py` step execution framework & `lead_lifecycle` workflow.
- **Rule-Based Decision Engine**: Prioritized business rules (`AutoBookDemo`, `AutoDisqualify`, `HighScoreOutreach`, `HumanReview`).
- **PostgreSQL 17 Storage**: 14 ORM tables with initial Alembic migration (`12bcca809a32_initial_schema.py`).
- **Celery Tasks**: SLA breach monitors and meeting reminder tasks.
- **LLM Abstraction**: Google Gemini 2.0, OpenAI GPT-4o, Anthropic Claude 3.5 providers.
