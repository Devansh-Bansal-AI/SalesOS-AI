# ============================================================
# SalesOS AI — CRM Dashboard Service
#
# Aggregation queries for pipeline, conversion, and rep metrics.
# Powers the dashboard APIs.
# ============================================================

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.lead import Lead, LeadScore
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.sales_execution import (
    ConversionMetrics,
    PipelineMetrics,
    RepPerformance,
)

logger = get_logger("dashboard_service")


class DashboardService:
    """Aggregation queries for CRM dashboard metrics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pipeline_metrics(
        self,
        organization_id: UUID,
        *,
        days: int = 30,
    ) -> PipelineMetrics:
        """Get pipeline overview metrics."""
        since = datetime.now(UTC) - timedelta(days=days)

        # Count by status
        stmt = (
            select(
                Lead.status,
                func.count(Lead.id),
            )
            .where(
                Lead.organization_id == organization_id,
                Lead.created_at >= since,
                Lead.deleted_at.is_(None),
            )
            .group_by(Lead.status)
        )
        result = await self.session.execute(stmt)
        status_counts = {row[0]: row[1] for row in result.all()}

        # Total
        total = sum(status_counts.values())

        # Average qualification score
        avg_stmt = (
            select(func.avg(LeadScore.score))
            .where(
                LeadScore.organization_id == organization_id,
                LeadScore.created_at >= since,
            )
        )
        avg_result = await self.session.execute(avg_stmt)
        avg_score = avg_result.scalar_one_or_none() or 0.0

        return PipelineMetrics(
            total_leads=total,
            new_leads=status_counts.get("new", 0),
            qualified_leads=status_counts.get("qualified", 0),
            in_conversation=status_counts.get("contacted", 0),
            meetings_booked=status_counts.get("meeting_booked", 0),
            converted=status_counts.get("converted", 0),
            disqualified=status_counts.get("disqualified", 0),
            avg_qualification_score=round(float(avg_score), 1),
        )

    async def get_conversion_metrics(
        self,
        organization_id: UUID,
        *,
        days: int = 30,
    ) -> ConversionMetrics:
        """Get conversion funnel metrics."""
        since = datetime.now(UTC) - timedelta(days=days)

        # Get status counts
        stmt = (
            select(
                Lead.status,
                func.count(Lead.id),
            )
            .where(
                Lead.organization_id == organization_id,
                Lead.created_at >= since,
                Lead.deleted_at.is_(None),
            )
            .group_by(Lead.status)
        )
        result = await self.session.execute(stmt)
        counts = {row[0]: row[1] for row in result.all()}

        total = sum(counts.values()) or 1  # Avoid division by zero
        qualified = counts.get("qualified", 0) + counts.get("meeting_booked", 0) + counts.get("converted", 0)
        with_meetings = counts.get("meeting_booked", 0) + counts.get("converted", 0)
        converted = counts.get("converted", 0)

        return ConversionMetrics(
            lead_to_qualified_rate=round(qualified / total * 100, 1),
            qualified_to_meeting_rate=round(
                with_meetings / qualified * 100, 1
            ) if qualified else 0.0,
            meeting_to_conversion_rate=round(
                converted / with_meetings * 100, 1
            ) if with_meetings else 0.0,
            overall_conversion_rate=round(converted / total * 100, 1),
        )

    async def get_rep_performance(
        self,
        organization_id: UUID,
        *,
        days: int = 30,
    ) -> list[RepPerformance]:
        """Get performance metrics for each sales rep."""
        since = datetime.now(UTC) - timedelta(days=days)

        # Get all active reps
        user_stmt = (
            select(User)
            .where(
                User.organization_id == organization_id,
                User.is_active.is_(True),
                User.role.in_(["sales_rep", "sales_manager"]),
                User.deleted_at.is_(None),
            )
        )
        user_result = await self.session.execute(user_stmt)
        users = list(user_result.scalars().all())

        performances: list[RepPerformance] = []

        for user in users:
            # Active leads count
            active_stmt = (
                select(func.count())
                .select_from(Lead)
                .where(
                    Lead.organization_id == organization_id,
                    Lead.assigned_to == user.id,
                    Lead.status.in_(["new", "contacted", "qualified", "nurture", "meeting_booked"]),
                    Lead.deleted_at.is_(None),
                )
            )
            active_result = await self.session.execute(active_stmt)
            active_leads = active_result.scalar_one()

            # Meetings booked
            meeting_stmt = (
                select(func.count())
                .select_from(Meeting)
                .where(
                    Meeting.organization_id == organization_id,
                    Meeting.host_user_id == user.id,
                    Meeting.created_at >= since,
                    Meeting.status.in_(["pending", "confirmed", "completed"]),
                )
            )
            meeting_result = await self.session.execute(meeting_stmt)
            meetings_booked = meeting_result.scalar_one()

            # Conversions
            conversion_stmt = (
                select(func.count())
                .select_from(Lead)
                .where(
                    Lead.organization_id == organization_id,
                    Lead.assigned_to == user.id,
                    Lead.status == "converted",
                    Lead.updated_at >= since,
                    Lead.deleted_at.is_(None),
                )
            )
            conv_result = await self.session.execute(conversion_stmt)
            conversions = conv_result.scalar_one()

            performances.append(RepPerformance(
                user_id=user.id,
                user_name=user.full_name,
                active_leads=active_leads,
                meetings_booked=meetings_booked,
                conversions=conversions,
            ))

        # Sort by conversions desc
        performances.sort(key=lambda p: p.conversions, reverse=True)
        return performances
