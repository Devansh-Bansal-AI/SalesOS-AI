# SalesOS AI — Architectural Decision Records (ADRs)

This document records the foundational architectural decisions that govern **SalesOS AI**. These decisions are **FROZEN** and serve as binding technical rules for all current and future development.

---

## ADR-001: Workflow Engine Orchestrates Business Processes

- **Status**: **Accepted & Frozen**
- **Context**: Sales Operations workflows require reliable, multi-step execution with pause/resume capabilities (e.g. waiting for a customer email reply).
- **Decision**: The Workflow Engine (`app/workflows/engine.py`) orchestrates all business processes using deterministic Python code. AI graph orchestrators (such as LangGraph) operate *inside* agent execution nodes, never at the top-level business process layer.
- **Consequences**: Guaranteed reliability, zero workflow hallucination, step-by-step state persistence in `workflow_instances` JSONB.

---

## ADR-002: Decision Engine Owns Deterministic Business Decisions

- **Status**: **Accepted & Frozen**
- **Context**: Deciding whether to auto-book a demo, disqualify a lead, or send outreach must follow clear business policies and SLA rules.
- **Decision**: The Decision Engine (`app/services/decision_engine.py`) owns all business decisions using prioritized, deterministic rules (`AutoBookDemoRule`, `AutoDisqualifyRule`, `HighScoreOutreachRule`, `HumanReviewRule`). LLM evaluation is used strictly as a conservative fallback when enabled by feature flags.
- **Consequences**: Predictable business logic, 100% confidence on rule matches, transparent auditability.

---

## ADR-003: Agents Are Advisory Only

- **Status**: **Accepted & Frozen**
- **Context**: AI agents generate unstructured text, scoring recommendations, and data extractions.
- **Decision**: AI Agents (`BaseAgent`) are advisory plugins. They produce typed recommendations, analysis, and draft content. They never modify database state or execute side-effects directly.
- **Consequences**: Prevents accidental data corruption or unapproved emails; side-effects are handled exclusively by services (`LeadService`, `CommunicationService`, `MeetingService`).

---

## ADR-004: State Machine Validates Lifecycle Transitions

- **Status**: **Accepted & Frozen**
- **Context**: Leads must follow valid sales pipeline stages (`NEW` ➔ `ENRICHED` ➔ `QUALIFIED` ➔ `CONTACTED` ➔ `MEETING_BOOKED` ➔ `CLOSED_WON`).
- **Decision**: The Lead State Machine (`app/services/state_machine.py`) validates and enforces all valid lead lifecycle transitions, preventing illegal status jumps.
- **Consequences**: Clean data integrity across CRM and analytics pipelines.

---

## ADR-005: Agent Registry as Extension Mechanism

- **Status**: **Accepted & Frozen**
- **Context**: New AI capabilities (e.g., objection handling, technical validation) will be added over time.
- **Decision**: The Agent Registry (`app/agents/registry.py`) is the primary extension point for new AI capabilities via the `@register_agent` decorator, ensuring zero core codebase changes when adding agents.
- **Consequences**: Modular plugin architecture; new agents can be added without modifying the core workflow engine.

---

## ADR-006: Versioned Prompt Registry

- **Status**: **Accepted & Frozen**
- **Context**: Prompts evolve over time and require version control and runtime customization.
- **Decision**: Prompts are managed independently from code using the Prompt Registry (`app/prompts/registry.py`), enabling prompt versioning, templating, and runtime overrides per organization.
- **Consequences**: Prompt changes do not require code refactoring; full version traceability.

---

## ADR-007: Event Bus Architecture

- **Status**: **Accepted & Frozen**
- **Context**: System components must react asynchronously to domain changes (e.g. starting a workflow when a lead is created).
- **Decision**: Domain events (`LEAD_CREATED`, `MEETING_SCHEDULED`, etc.) are published via `app/events/bus.py` with strict separation between domain events, application side-effects, and external integration events.
- **Consequences**: Loose coupling between components; easy integration of background Celery workers and Redis pub/sub.
