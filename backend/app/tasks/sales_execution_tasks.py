# ============================================================
# SalesOS AI — Sales Execution Celery Tasks
#
# Background workers for:
# 1. SLA violation monitoring
# 2. Meeting reminder notifications
# ============================================================

from datetime import UTC

from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.sales_execution")


@celery_app.task(name="check_sla_violations")
def check_sla_violations() -> dict:
    """Check all organizations for SLA violations.

    Runs on Celery beat schedule (e.g., every 15 minutes).
    """
    import asyncio

    async def _process():
        from sqlalchemy import select

        from app.db.session import get_async_session
        from app.models.organization import Organization
        from app.services.sla_service import SLAService

        async with get_async_session() as session:
            # Get all active organizations
            stmt = select(Organization)
            result = await session.execute(stmt)
            orgs = list(result.scalars().all())

            total_violations = 0

            for org in orgs:
                try:
                    service = SLAService(session)
                    count = await service.process_violations(org.id)
                    total_violations += count
                except Exception as e:
                    logger.error(
                        "sla_check_error",
                        organization_id=str(org.id),
                        error=str(e),
                    )

            await session.commit()

            logger.info(
                "sla_check_completed",
                organizations=len(orgs),
                total_violations=total_violations,
            )

            return {
                "organizations_checked": len(orgs),
                "total_violations": total_violations,
            }

    return asyncio.run(_process())


@celery_app.task(name="send_meeting_reminders")
def send_meeting_reminders() -> dict:
    """Send reminder notifications for upcoming meetings.

    Runs on Celery beat schedule (e.g., every 10 minutes).
    """
    import asyncio

    async def _process():
        from datetime import datetime, timedelta

        from app.db.session import get_async_session
        from app.repositories.meeting_repo import MeetingRepository
        from app.services.crm_service import CRMService

        now = datetime.now(UTC)
        reminder_window = now + timedelta(minutes=30)

        async with get_async_session() as session:
            repo = MeetingRepository(session)
            meetings = await repo.find_needing_reminders(
                reminder_before=reminder_window,
                reminder_after=now,
            )

            reminded = 0

            for meeting in meetings:
                try:
                    # Log reminder activity
                    crm = CRMService(session)
                    await crm.log_activity(
                        meeting.organization_id,
                        meeting.lead_id,
                        activity_type="meeting_reminder",
                        title=f"🔔 Meeting in {int((meeting.scheduled_at - now).total_seconds() / 60)} min: {meeting.title}",
                        metadata={
                            "meeting_id": str(meeting.id),
                            "scheduled_at": meeting.scheduled_at.isoformat(),
                        },
                    )

                    meeting.reminder_sent = True
                    reminded += 1

                except Exception as e:
                    logger.error(
                        "meeting_reminder_error",
                        meeting_id=str(meeting.id),
                        error=str(e),
                    )

            await session.commit()

            logger.info(
                "meeting_reminders_sent",
                total=len(meetings),
                reminded=reminded,
            )

            return {"total": len(meetings), "reminded": reminded}

    return asyncio.run(_process())
