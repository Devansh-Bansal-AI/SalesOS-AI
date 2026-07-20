# ============================================================
# SalesOS AI — Communication Event Handlers
#
# Reacts to conversation events:
# - Inbound message → run Conversation Intelligence Agent
# - Analysis complete + high risk → auto-escalate
# - Qualification complete → start outreach/followup
# ============================================================

from app.core.logging import get_logger
from app.events.bus import on
from app.events.types import EventTypes
from app.models.domain_event import DomainEvent

logger = get_logger("communication_handlers")


@on(EventTypes.CONVERSATION_MESSAGE_RECEIVED)
async def handle_inbound_message(event: DomainEvent, session) -> None:
    """When an inbound message is received, analyze it with Conversation Intelligence.

    Flow:
    1. Load lead context
    2. Load conversation history
    3. Run Conversation Intelligence Agent
    4. Store analysis results
    5. Check for auto-escalation
    6. Resume workflow if paused
    """
    from uuid import UUID

    from app.agents.conversation_intelligence import (
        ConversationIntelligenceAgent,
        ConversationIntelligenceInput,
    )
    from app.services.conversation_service import ConversationService
    from app.services.escalation_service import EscalationService

    message_id = event.payload.get("message_id")
    lead_id = event.payload.get("lead_id")
    body_text = event.payload.get("body_text", "")
    channel = event.payload.get("channel", "email")

    if not message_id or not lead_id:
        logger.warning("inbound_message_missing_data", event_id=str(event.id))
        return

    logger.info(
        "analyzing_inbound_message",
        message_id=message_id,
        lead_id=lead_id,
    )

    try:
        # Load lead context
        from app.repositories.lead_repo import LeadRepository
        lead_repo = LeadRepository(session)
        lead = await lead_repo.get_by_id_and_org(
            UUID(lead_id), event.organization_id
        )

        if not lead:
            logger.warning("lead_not_found_for_analysis", lead_id=lead_id)
            return

        # Load conversation history
        conv_service = ConversationService(session)
        recent = await conv_service.get_recent_lead_messages(
            event.organization_id, UUID(lead_id), limit=5
        )
        history = "\n".join(
            f"[{m.direction}] {m.body_text[:200] if m.body_text else ''}"
            for m in recent
        )

        # Run Conversation Intelligence Agent
        agent = ConversationIntelligenceAgent(session, event.organization_id)

        score = None
        stage = "awareness"
        if lead.qualification:
            score = lead.qualification.get("score")
            stage = lead.qualification.get("customer_stage", "awareness")

        input_data = ConversationIntelligenceInput(
            message_id=message_id,
            sender_email=lead.email,
            subject=event.payload.get("subject"),
            body_text=body_text,
            email=lead.email,
            first_name=lead.first_name,
            last_name=lead.last_name,
            company_name=lead.company.name if lead.company else None,
            job_title=lead.job_title,
            current_stage=stage,
            score=score,
            conversation_history=history,
        )

        output, agent_run = await agent.run(
            input_data,
            lead_id=UUID(lead_id),
        )

        # Store analysis on the message
        from app.schemas.communication import ConversationAnalysis

        analysis = ConversationAnalysis(
            sentiment=output.sentiment,
            intent=output.intent,
            buying_signals=output.buying_signals,
            objections=output.objections,
            competitor_mentions=output.competitor_mentions,
            risk_level=output.risk_level,
            customer_stage=output.customer_stage,
            next_best_action=output.next_best_action,
            confidence=output.confidence,
            summary=output.summary,
            memory_update=output.memory_update,
        )

        await conv_service.apply_analysis(
            event.organization_id,
            UUID(message_id),
            analysis,
            agent_run_id=agent_run.id,
        )

        # Auto-escalation check
        escalation_service = EscalationService(session)
        await escalation_service.auto_escalate_from_analysis(
            event.organization_id,
            UUID(lead_id),
            analysis.model_dump(),
            conversation_id=event.aggregate_id,
        )

        # If workflow is paused waiting for reply, resume it
        from sqlalchemy import select

        from app.models.workflow import WorkflowInstance
        from app.workflows.engine import get_workflow_engine

        stmt = select(WorkflowInstance).where(
            WorkflowInstance.lead_id == UUID(lead_id),
            WorkflowInstance.status == "waiting",
        )
        result = await session.execute(stmt)
        waiting_workflow = result.scalar_one_or_none()

        if waiting_workflow:
            engine = get_workflow_engine()
            await engine.resume(
                session,
                waiting_workflow.id,
                event_data={
                    "reply_analysis": analysis.model_dump(),
                    "message_id": message_id,
                },
            )

    except Exception as e:
        logger.error(
            "conversation_analysis_failed",
            message_id=message_id,
            error=str(e),
        )


@on(EventTypes.CONVERSATION_ANALYZED)
async def handle_conversation_analyzed(event: DomainEvent, session) -> None:
    """Log conversation analysis for observability."""
    logger.info(
        "conversation_analyzed",
        lead_id=event.payload.get("lead_id"),
        sentiment=event.payload.get("sentiment"),
        risk=event.payload.get("risk_level"),
        stage=event.payload.get("customer_stage"),
        action=event.payload.get("next_best_action"),
        buying_signals=len(event.payload.get("buying_signals", [])),
        objections=len(event.payload.get("objections", [])),
        competitors=event.payload.get("competitor_mentions", []),
    )


@on(EventTypes.EMAIL_SENT)
async def handle_email_sent(event: DomainEvent, session) -> None:
    """Track email delivery for analytics."""
    logger.info(
        "email_sent_tracked",
        lead_id=event.payload.get("lead_id"),
        to=event.payload.get("to"),
        provider=event.payload.get("provider"),
    )


def register_communication_handlers() -> None:
    """Import this module to register communication event handlers."""
    logger.info("communication_event_handlers_registered")
