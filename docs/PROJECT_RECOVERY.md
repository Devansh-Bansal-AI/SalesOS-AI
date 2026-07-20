# SalesOS AI — Project Recovery & Technical Architecture Report

**Platform**: SalesOS AI — Production-Grade AI-Native Sales Operations Platform  
**System Architecture**: Asynchronous Multi-Agent, Event-Driven, Microservices-Ready Monorepo  
**Recovery Timestamp**: July 21, 2026  
**Backend Architecture Policy**: **FROZEN** (Milestones 1–4 Finalized)  
**Status**: Ready for Milestone 6 Execution  

---

## 1. Executive Summary

This document represents the complete recovery analysis of the **SalesOS AI** repository. Every module, service, model, agent, prompt, event handler, task, and route has been inspected against the codebase repository as the single source of truth.

The backend architecture is **frozen**. All foundational patterns — including the Workflow Engine, Decision Engine, Lead State Machine, Agent Registry, Prompt Registry, Event Bus, and LLM Provider Abstractions — are finalized and locked.

Development is currently at the transition to **Milestone 6: Vector Memory (Qdrant RAG Integration), Missing MCP Tool Providers, Analytics API, and Test Suite Completion**.

---

## 2. Architecture Freeze Statement

> [!IMPORTANT]
> **Backend Architecture Freeze Notice**
> The backend architecture of SalesOS AI is **officially frozen after Milestone 4**.
> All future milestones extend the platform by implementing concrete providers, services, repositories, and API endpoints using the existing abstractions. No new architectural patterns, core layer refactors, or structural redesigns shall be introduced without explicit approval.

---

## 3. Architectural Decision Records (ADRs) Summary

| Record ID | Title | Core Decision & Rationale |
| :--- | :--- | :--- |
| **ADR-001** | **Workflow Engine Business Orchestration** | The Workflow Engine (`app/workflows/engine.py`) orchestrates multi-step business processes deterministically. AI orchestrators (such as LangGraph) operate *inside* agent execution nodes, never at the top-level business process layer. |
| **ADR-002** | **Decision Engine Ownership** | The Decision Engine (`app/services/decision_engine.py`) owns all business decisions using prioritized, deterministic rules (`AutoBookDemo`, `AutoDisqualify`, `HighScoreOutreach`, `HumanReview`). LLM evaluation is used strictly as a conservative fallback when enabled by feature flags. |
| **ADR-003** | **Advisory AI Agent Principle** | AI Agents are advisory plugins (`BaseAgent`). They produce typed recommendations, analysis, and draft content. They never modify database state or execute side-effects directly. |
| **ADR-004** | **State Machine Transition Guarding** | The Lead State Machine (`app/services/state_machine.py`) validates and enforces all valid lead lifecycle transitions (`NEW` ➔ `ENRICHED` ➔ `QUALIFIED` ➔ `CONTACTED` ➔ `MEETING_BOOKED` ➔ `CLOSED_WON`). |
| **ADR-005** | **Agent Registry Plugin System** | The Agent Registry (`app/agents/registry.py`) is the primary extension point for new AI capabilities via the `@register_agent` decorator, ensuring zero core codebase changes when adding agents. |
| **ADR-006** | **Versioned Prompt Registry** | Prompts are managed independently from code using the Prompt Registry (`app/prompts/registry.py`), enabling prompt versioning, templating, and runtime overrides per organization. |
| **ADR-007** | **Tiered Event Bus Architecture** | Domain events (`LEAD_CREATED`, `MEETING_SCHEDULED`, etc.) are published via `app/events/bus.py` with strict separation between domain events, application side-effects, and external integration events. |

---

## 4. Architecture Map & Layering Validation

SalesOS AI follows a strict, unidirectional layered architecture:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     1. Presentation Layer (Next.js 15 App Router)               │
│         Dashboard  │  Leads & CRM  │  Conversations  │  Meetings  │  AI Center   │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ REST API / WebSockets
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                        2. API Layer (FastAPI /api/v1/ Routers)                  │
│       auth.py  │  leads.py  │  conversations.py  │  meetings.py  │  sales_exec.py   │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                     3. Business Services Layer (app/services/)                  │
│    LeadService │ ConversationService │ MeetingService │ SLAService │ AuthService │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                      4. Workflow Engine (app/workflows/engine.py)               │
│        Deterministic Step Execution │ Context Serialization │ Pause/Resume       │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                   5. Decision Engine (app/services/decision_engine.py)          │
│       Rule Evaluation (AutoBook/AutoDisqualify/Outreach/HumanReview) + LLM      │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                   6. Lead State Machine (app/services/state_machine.py)         │
│          NEW ➔ ENRICHED ➔ QUALIFIED ➔ CONTACTED ➔ MEETING_BOOKED ➔ CLOSED_WON      │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                     7. Agent Registry (app/agents/registry.py)                  │
│   QualificationAgent │ EnrichmentAgent │ OutreachAgent │ BookingAgent │ IntelAgent │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                     8. Prompt Registry (app/prompts/registry.py)                │
│    qualification_v1 │ enrichment_v1 │ outreach_v1 │ booking_v1 │ intel_v1         │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│               9. LLM Provider Abstraction (app/integrations/llm/)               │
│             Google Gemini (Primary) │ OpenAI GPT-4o │ Anthropic Claude          │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│             10. MCP Tool Providers & Repositories (app/agents/tools.py)        │
│    PostgresCRMProvider │ CompanyResearch │ CalendarProvider │ KnowledgeBase (Qdrant) │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│               11. Infrastructure & Storage (PostgreSQL 17 / Redis 7 / Qdrant)    │
│           Relational ORM  │  Event Bus & Cache  │  Vector RAG Embeddings        │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼────────────────────────────────────────┐
│              12. Async Processing (app/events/bus.py & app/tasks/celery_app.py) │
│           Domain Events  │  SLA Monitors  │  Follow-Up Tasks  │  Reminders          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Milestone Alignment Matrix

| Milestone | Description | Status | Status Details |
| :--- | :--- | :--- | :--- |
| **Milestone 1** | Infrastructure, Async DB, Config, Security & Auth | **COMPLETED** | Fully operational (`FastAPI`, `PostgreSQL 17`, `Redis 7`, `Alembic`, `JWT`). |
| **Milestone 2** | Lead Domain Engine, State Machine, SLA & CRM | **COMPLETED** | Fully operational (`LeadService`, `StateMachine`, `AssignmentEngine`, `SLAService`). |
| **Milestone 3** | Workflow Engine & Decision Engine | **COMPLETED** | Fully operational (`WorkflowEngine`, `DecisionEngine`, `lead_lifecycle` workflow). |
| **Milestone 4** | Multi-Agent AI Core & Provider Abstraction | **COMPLETED** | Base agents, LLM providers (Gemini, OpenAI, Claude), Agent Registry, Prompt Registry, Tool Registry interfaces. |
| **Milestone 5** | Workspace Web UI & Primary REST APIs | **COMPLETED** | Next.js 15 App Router workspace UI, `auth`, `leads`, `conversations`, `meetings`, `sales_execution` API routers. |
| **Milestone 6** | Vector Memory (Qdrant), Tool Implementations, Analytics & Tests | **PENDING (Current)** | Concrete implementations of defined tool interfaces (`qdrant_kb`, `company_research`, `calendar`), `/api/v1/analytics`, and Pytest test suite. |

---

## 6. System Evaluation Across Independent Dimensions

Rather than a single merged score, the system is evaluated across 3 independent technical dimensions:

### 🌟 Dimension A: Architecture Maturity — `9.5 / 10` (High)
- Unidirectional layering, frozen abstractions, deterministic business logic, plugin registries for agents and prompts.
- Complete domain event bus and feature flag isolation.

### ⚙️ Dimension B: Implementation Completeness — `85% Complete`
- Core database schema (14 tables), 5 AI agents, lead workflow, state transitions, sales execution, and UI are fully written.
- Pending items are concrete implementations of defined interfaces (`QdrantKnowledgeBaseProvider`, `CompanyResearchToolProvider`, `CalendarToolProvider`) and the analytics endpoint.

### 🧪 Dimension C: Test Coverage — `Low (~15%)`
- Fixture infrastructure (`conftest.py`) exists, but unit and integration test files need implementation during Milestone 6.

---

## 7. Next Execution Plan

### Active Target: **Milestone 6 — Vector Memory (Qdrant RAG), MCP Tool Providers & Analytics API**

### Immediate Task: **Task 6.1 — Qdrant Vector Client & Knowledge Base Tool Provider**

### Files to Create:
- `backend/app/db/qdrant.py`
- `backend/app/agents/tools/qdrant_kb.py`
- `backend/app/agents/tools/company_research.py`
- `backend/app/agents/tools/calendar.py`
- `backend/app/api/v1/analytics.py`

### Files to Modify:
- `backend/app/main.py`
- `backend/app/api/v1/router.py`
