# ============================================================
# SalesOS AI — Lead Lifecycle Workflow
#
# Configuration-driven workflow that processes leads from
# creation through qualification, enrichment, and decision.
#
# Execution path:
#   LEAD_CREATED event → start workflow →
#     validate → qualify → enrich → decide → (action)
#
# Each step is a function that receives WorkflowContext
# and returns StepResult. Business logic stays deterministic.
# ============================================================

from datetime import UTC, datetime, timedelta

from app.agents.booking import BookingAgent, BookingInput
from app.agents.enrichment import EnrichmentAgent, EnrichmentInput
from app.agents.outreach import OutreachAgent, OutreachInput
from app.agents.qualification import QualificationAgent, QualificationInput
from app.core.logging import get_logger
from app.repositories.lead_repo import LeadRepository
from app.schemas.communication import EmailSendRequest
from app.schemas.lead import LeadUpdateRequest
from app.schemas.sales_execution import MeetingCreateRequest
from app.services.communication_service import CommunicationService
from app.services.decision_engine import DecisionEngine
from app.services.escalation_service import EscalationService
from app.services.followup_service import FollowUpService
from app.services.lead_service import LeadService
from app.services.meeting_service import MeetingService
from app.workflows.engine import (
    StepResult,
    StepStatus,
    WorkflowContext,
    WorkflowDefinition,
    get_workflow_engine,
)

logger = get_logger("workflow.lead_lifecycle")


# ── Workflow Steps ──────────────────────────────────────────


async def validate_lead(ctx: WorkflowContext) -> StepResult:
    """Step 1: Validate the lead data is sufficient for qualification."""
    email = ctx.get("email")
    if not email:
        return StepResult(
            status=StepStatus.FAILED,
            error="Lead email is required for qualification",
        )

    # Basic validation passed
    logger.info("lead_validated", lead_id=str(ctx.lead_id), email=email)
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"validated": True},
    )


async def qualify_lead(ctx: WorkflowContext) -> StepResult:
    """Step 2: Run the Qualification Agent."""
    if not ctx.session:
        return StepResult(status=StepStatus.FAILED, error="No database session")

    agent = QualificationAgent(ctx.session, ctx.organization_id)

    input_data = QualificationInput(
        email=ctx.get("email", ""),
        first_name=ctx.get("first_name"),
        last_name=ctx.get("last_name"),
        job_title=ctx.get("job_title"),
        company_name=ctx.get("company_name"),
        source=ctx.get("source", "website"),
        message=ctx.get("message"),
    )

    output, agent_run = await agent.run(
        input_data,
        lead_id=ctx.lead_id,
        workflow_id=ctx.workflow_id,
    )

    # Apply qualification to the lead
    lead_service = LeadService(ctx.session)
    await lead_service.apply_qualification(
        ctx.organization_id,
        ctx.lead_id,
        score=output.score,
        priority=output.priority,
        intent=output.intent,
        urgency=output.urgency,
        summary=output.summary,
        confidence=output.confidence,
        reasoning=output.reasoning,
    )

    return StepResult(
        status=StepStatus.COMPLETED,
        data={
            "score": output.score,
            "priority": output.priority,
            "intent": output.intent,
            "urgency": output.urgency,
            "confidence": output.confidence,
            "summary": output.summary,
        },
    )


async def enrich_lead(ctx: WorkflowContext) -> StepResult:
    """Step 3: Run the Enrichment Agent."""
    if not ctx.session:
        return StepResult(status=StepStatus.FAILED, error="No database session")

    # Skip enrichment for low-score or spam leads
    score = ctx.get("score", 0)
    intent = ctx.get("intent", "")
    if score < 20 or intent == "spam":
        logger.info("enrichment_skipped", reason="low_score_or_spam", score=score)
        return StepResult(status=StepStatus.SKIPPED)

    agent = EnrichmentAgent(ctx.session, ctx.organization_id)

    email = ctx.get("email", "")
    domain = email.split("@")[1].lower() if "@" in email else None

    input_data = EnrichmentInput(
        email=email,
        first_name=ctx.get("first_name"),
        last_name=ctx.get("last_name"),
        job_title=ctx.get("job_title"),
        company_name=ctx.get("company_name"),
        domain=domain,
        score=ctx.get("score"),
        intent=ctx.get("intent"),
        urgency=ctx.get("urgency"),
    )

    output, agent_run = await agent.run(
        input_data,
        lead_id=ctx.lead_id,
        workflow_id=ctx.workflow_id,
    )

    # Apply enrichment to the lead
    lead_service = LeadService(ctx.session)

    company_data = None
    if output.company_profile:
        company_data = output.company_profile.model_dump()

    await lead_service.apply_enrichment(
        ctx.organization_id,
        ctx.lead_id,
        enrichment_data={
            "company_profile": output.company_profile.model_dump(),
            "lead_context": output.lead_context.model_dump(),
            "conversation_starters": output.conversation_starters,
            "data_sources": output.data_sources_used,
        },
        company_name=output.company_profile.name,
        company_data=company_data,
    )

    return StepResult(
        status=StepStatus.COMPLETED,
        data={
            "enriched": True,
            "company_name": output.company_profile.name,
            "industry": output.company_profile.industry,
        },
    )


async def evaluate_decision(ctx: WorkflowContext) -> StepResult:
    """Step 4: Run the Decision Engine to determine next action."""
    engine = DecisionEngine()

    decision = await engine.evaluate(
        {
            "score": ctx.get("score", 0),
            "intent": ctx.get("intent", "general"),
            "urgency": ctx.get("urgency", "unknown"),
            "confidence": ctx.get("confidence", 0.5),
            "company_name": ctx.get("company_name"),
            "job_title": ctx.get("job_title"),
        },
        organization_id=str(ctx.organization_id),
    )

    logger.info(
        "decision_evaluated",
        lead_id=str(ctx.lead_id),
        action=decision.action,
        source=decision.source,
        confidence=decision.confidence,
    )

    # Map decision action to next workflow step
    next_step_map = {
        "book_meeting": "schedule_meeting",
        "outreach": "send_outreach",
        "nurture": "start_nurture",
        "watch": "add_to_watch",
        "disqualify": "disqualify",
        "escalate": "escalate_to_human",
    }

    return StepResult(
        status=StepStatus.COMPLETED,
        data={
            "decision_action": decision.action,
            "decision_confidence": decision.confidence,
            "decision_reasoning": decision.reasoning,
            "decision_source": decision.source,
        },
        next_step=next_step_map.get(decision.action),
    )


async def send_outreach(ctx: WorkflowContext) -> StepResult:
    """Step 5a: Generate and send personalized outreach email."""
    if not ctx.session or not ctx.lead_id:
        return StepResult(status=StepStatus.FAILED, error="No database session or lead ID")

    # Load lead to retrieve company and enrichment details
    lead_repo = LeadRepository(ctx.session)
    lead = await lead_repo.get_by_id_and_org(ctx.lead_id, ctx.organization_id)
    if not lead:
        return StepResult(status=StepStatus.FAILED, error=f"Lead {ctx.lead_id} not found")

    enrichment = lead.enrichment or {}
    company_profile = enrichment.get("company_profile") or {}
    lead_context = enrichment.get("lead_context") or {}

    input_data = OutreachInput(
        email=lead.email,
        first_name=lead.first_name,
        last_name=lead.last_name,
        job_title=lead.job_title,
        company_name=company_profile.get("name") or (lead.company.name if lead.company else None),
        score=ctx.get("score"),
        intent=ctx.get("intent"),
        urgency=ctx.get("urgency"),
        industry=company_profile.get("industry"),
        employee_range=company_profile.get("employee_range"),
        pain_points=lead_context.get("pain_points") or [],
        conversation_starters=enrichment.get("conversation_starters") or [],
        template_type="hot_lead" if ctx.get("score", 0) >= 80 else "warm_lead",
    )

    agent = OutreachAgent(ctx.session, ctx.organization_id)
    output, agent_run = await agent.run(
        input_data,
        lead_id=ctx.lead_id,
        workflow_id=ctx.workflow_id,
    )

    # Send generated outreach
    comm_service = CommunicationService(ctx.session)
    req = EmailSendRequest(
        lead_id=ctx.lead_id,
        subject=output.subject,
        body_text=output.body_text,
        body_html=output.body_html,
    )
    email_response = await comm_service.send_email(
        ctx.organization_id,
        req,
        agent_run_id=agent_run.id,
        generated_by="outreach_agent",
    )

    # Update lead status to contacted
    lead_service = LeadService(ctx.session)
    await lead_service.update_lead(
        ctx.organization_id,
        ctx.lead_id,
        LeadUpdateRequest(status="contacted"),
    )

    logger.info(
        "outreach_queued_and_sent", lead_id=str(ctx.lead_id), email_id=str(email_response.id)
    )
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"outreach_queued": True, "email_id": str(email_response.id)},
    )


async def start_nurture(ctx: WorkflowContext) -> StepResult:
    """Step 5b: Start automated nurture sequence."""
    if not ctx.session or not ctx.lead_id:
        return StepResult(status=StepStatus.FAILED, error="No database session or lead ID")

    followup_service = FollowUpService(ctx.session)
    sequence = await followup_service.start_sequence(
        ctx.organization_id,
        ctx.lead_id,
        name="automated_followup",
    )

    # Update lead status to nurture
    lead_service = LeadService(ctx.session)
    await lead_service.update_lead(
        ctx.organization_id,
        ctx.lead_id,
        LeadUpdateRequest(status="nurture"),
    )

    logger.info("nurture_started", lead_id=str(ctx.lead_id), sequence_id=str(sequence.id))
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"nurture_started": True, "sequence_id": str(sequence.id)},
    )


async def schedule_meeting(ctx: WorkflowContext) -> StepResult:
    """Step 5c: Booking agent recommended meeting setup."""
    if not ctx.session or not ctx.lead_id:
        return StepResult(status=StepStatus.FAILED, error="No database session or lead ID")

    # Load lead
    lead_repo = LeadRepository(ctx.session)
    lead = await lead_repo.get_by_id_and_org(ctx.lead_id, ctx.organization_id)
    if not lead:
        return StepResult(status=StepStatus.FAILED, error=f"Lead {ctx.lead_id} not found")

    enrichment = lead.enrichment or {}
    company_profile = enrichment.get("company_profile") or {}

    input_data = BookingInput(
        email=lead.email,
        first_name=lead.first_name,
        last_name=lead.last_name,
        job_title=lead.job_title,
        company_name=company_profile.get("name") or (lead.company.name if lead.company else None),
        score=ctx.get("score"),
        intent=ctx.get("intent"),
        urgency=ctx.get("urgency"),
        priority=ctx.get("priority"),
        conversation_summary=lead.notes or "",
    )

    agent = BookingAgent(ctx.session, ctx.organization_id)
    output, agent_run = await agent.run(
        input_data,
        lead_id=ctx.lead_id,
        workflow_id=ctx.workflow_id,
    )

    # Map agent meeting types to allowed schema categories
    # API schema accepts: demo, discovery, follow_up, onboarding, custom
    agent_meeting_type = output.meeting_type
    if agent_meeting_type in ("demo", "discovery"):
        meeting_type = agent_meeting_type
    elif agent_meeting_type == "follow_up":
        meeting_type = "follow_up"
    else:
        meeting_type = "custom"

    # Default booking scheduled_at to 24 hours from now
    scheduled_at = datetime.now(UTC) + timedelta(days=1)

    meeting_service = MeetingService(ctx.session)
    req = MeetingCreateRequest(
        lead_id=ctx.lead_id,
        title=output.title,
        description=output.description or f"AI Recommended Meeting: {output.title}",
        meeting_type=meeting_type,
        scheduled_at=scheduled_at,
        duration_minutes=output.duration_minutes,
        timezone="UTC",
    )

    meeting_response = await meeting_service.book_meeting(
        ctx.organization_id,
        req,
        host_user_id=lead.assigned_to,
        agent_run_id=agent_run.id,
    )

    logger.info(
        "meeting_queued_and_booked", lead_id=str(ctx.lead_id), meeting_id=str(meeting_response.id)
    )
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"meeting_queued": True, "meeting_id": str(meeting_response.id)},
    )


async def disqualify_lead(ctx: WorkflowContext) -> StepResult:
    """Step 5d: Disqualify lead."""
    if ctx.session and ctx.lead_id:
        lead_service = LeadService(ctx.session)
        await lead_service.update_lead(
            ctx.organization_id,
            ctx.lead_id,
            LeadUpdateRequest(status="disqualified"),
        )
    logger.info("lead_disqualified", lead_id=str(ctx.lead_id))
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"disqualified": True},
    )


async def add_to_watch(ctx: WorkflowContext) -> StepResult:
    """Step 5e: Log CRM activity for watch list and set to nurture."""
    if ctx.session and ctx.lead_id:
        # Log watching activity
        from app.services.crm_service import CRMService

        crm = CRMService(ctx.session)
        await crm.log_activity(
            ctx.organization_id,
            ctx.lead_id,
            activity_type="lead_watching",
            title="👀 Lead added to watch list",
            description=ctx.get("decision_reasoning") or "Added to watch list by decision engine",
        )
        # Update status to nurture
        lead_service = LeadService(ctx.session)
        await lead_service.update_lead(
            ctx.organization_id,
            ctx.lead_id,
            LeadUpdateRequest(status="nurture"),
        )

    logger.info("lead_watching", lead_id=str(ctx.lead_id))
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"watching": True},
    )


async def escalate_to_human(ctx: WorkflowContext) -> StepResult:
    """Step 5f: Escalate to human review."""
    if ctx.session and ctx.lead_id:
        escalation_service = EscalationService(ctx.session)
        await escalation_service.escalate(
            ctx.organization_id,
            ctx.lead_id,
            reason=ctx.get("decision_reasoning") or "Workflow execution escalation",
            severity="medium",
        )
    logger.info(
        "lead_escalated",
        lead_id=str(ctx.lead_id),
        reason=ctx.get("decision_reasoning"),
    )
    return StepResult(
        status=StepStatus.COMPLETED,
        data={"escalated": True, "reason": ctx.get("decision_reasoning")},
    )


# ── Workflow Registration ───────────────────────────────────


def register_lead_lifecycle_workflow() -> None:
    """Register the lead lifecycle workflow with the engine."""
    workflow = WorkflowDefinition(
        name="Lead Lifecycle",
        workflow_type="lead_lifecycle",
        description="Process leads from creation through qualification, enrichment, and decision",
    )

    # Core pipeline
    workflow.add_step("validate", validate_lead, next_step="qualify")
    workflow.add_step("qualify", qualify_lead, next_step="enrich", on_error="escalate_to_human")
    workflow.add_step("enrich", enrich_lead, next_step="decide", on_error="decide")
    workflow.add_step("decide", evaluate_decision)  # next_step set dynamically

    # Decision outcome steps (terminal)
    workflow.add_step("send_outreach", send_outreach)
    workflow.add_step("start_nurture", start_nurture)
    workflow.add_step("schedule_meeting", schedule_meeting)
    workflow.add_step("disqualify", disqualify_lead)
    workflow.add_step("add_to_watch", add_to_watch)
    workflow.add_step("escalate_to_human", escalate_to_human)

    engine = get_workflow_engine()
    engine.register(workflow)

    logger.info("lead_lifecycle_workflow_registered")
