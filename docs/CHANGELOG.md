# SalesOS AI — Project Changelog

All notable changes, architectural decisions, and milestone completions for SalesOS AI are documented in this file.

---

## [Unreleased] — Milestone 6 Development

### Added
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
