# ============================================================
# SalesOS AI — Communication Celery Tasks
#
# Background workers for:
# 1. Processing due follow-up sequences
# 2. Sending scheduled emails
# ============================================================

from datetime import UTC

from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

logger = get_logger("tasks.communication")


@celery_app.task(name="process_followup_sequences")
def process_followup_sequences() -> dict:
    """Process all due follow-up sequences.

    Runs on Celery beat schedule (e.g., every 15 minutes).
    """
    import asyncio

    async def _process():
        from app.db.session import get_async_session
        from app.services.followup_service import FollowUpService

        async with get_async_session() as session:
            service = FollowUpService(session)
            due_sequences = await service.get_due_sequences()

            executed = 0
            skipped = 0

            for sequence in due_sequences:
                try:
                    result = await service.execute_step(sequence)
                    if result:
                        executed += 1
                    else:
                        skipped += 1
                except Exception as e:
                    logger.error(
                        "followup_step_error",
                        sequence_id=str(sequence.id),
                        error=str(e),
                    )

            await session.commit()

            logger.info(
                "followup_batch_completed",
                total=len(due_sequences),
                executed=executed,
                skipped=skipped,
            )

            return {
                "total": len(due_sequences),
                "executed": executed,
                "skipped": skipped,
            }

    return asyncio.run(_process())


@celery_app.task(name="send_scheduled_emails")
def send_scheduled_emails() -> dict:
    """Send all emails that are scheduled for now or earlier.

    Runs on Celery beat schedule (e.g., every 5 minutes).
    """
    import asyncio

    async def _process():
        from datetime import datetime

        from app.db.session import get_async_session
        from app.integrations import EmailMessage, get_registry
        from app.repositories.email_repo import EmailRepository

        async with get_async_session() as session:
            repo = EmailRepository(session)
            scheduled = await repo.get_scheduled(datetime.now(UTC))

            sent = 0
            failed = 0

            registry = get_registry()

            for email in scheduled:
                try:
                    provider = registry.get_email()
                    message = EmailMessage(
                        to=email.to_email,
                        subject=email.subject,
                        body_text=email.body_text,
                        body_html=email.body_html,
                        from_email=email.from_email,
                        reply_to=email.reply_to,
                    )
                    result = await provider.send(message)

                    if result.success:
                        email.status = "sent"
                        email.provider = result.provider
                        email.provider_id = result.message_id
                        email.sent_at = datetime.now(UTC)
                        sent += 1
                    else:
                        email.status = "failed"
                        email.error_message = result.error
                        failed += 1

                except Exception as e:
                    email.status = "failed"
                    email.error_message = str(e)
                    failed += 1
                    logger.error(
                        "scheduled_email_error",
                        email_id=str(email.id),
                        error=str(e),
                    )

            await session.commit()

            logger.info(
                "scheduled_email_batch",
                total=len(scheduled),
                sent=sent,
                failed=failed,
            )

            return {"total": len(scheduled), "sent": sent, "failed": failed}

    return asyncio.run(_process())
