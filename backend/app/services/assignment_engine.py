# ============================================================
# SalesOS AI — Assignment Engine
#
# Reusable engine for lead assignment. NOT just "assign user."
#
# Strategies:
#   Round Robin  → Fair rotation through active reps
#   Load-Based   → Fewest active leads
#   Territory    → Match by lead attributes (e.g., region)
#   Skill-Based  → Match by lead requirements (e.g., enterprise)
#   Manual       → Explicit assignment (passthrough)
# ============================================================

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.events.bus import publish
from app.events.types import EventTypes
from app.models.lead import Lead
from app.models.user import User
from app.schemas.sales_execution import AssignmentConfig, AssignmentResult, AssignmentStrategy

logger = get_logger("assignment_engine")

# Module-level state for round-robin tracking
_round_robin_index: dict[str, int] = {}


class AssignmentEngine:
    """Reusable lead assignment engine with pluggable strategies.

    Usage:
        engine = AssignmentEngine(session)
        result = await engine.assign(org_id, lead_id, config)
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def assign(
        self,
        organization_id: UUID,
        lead_id: UUID,
        config: AssignmentConfig | None = None,
        *,
        manual_user_id: UUID | None = None,
    ) -> AssignmentResult:
        """Assign a lead using the configured strategy.

        If manual_user_id is provided, uses manual strategy regardless of config.
        """
        config = config or AssignmentConfig()

        if manual_user_id:
            return await self._assign_manual(organization_id, lead_id, manual_user_id)

        strategy = config.strategy
        candidates = await self._get_eligible_reps(organization_id, config)

        if not candidates:
            if config.fallback_user_id:
                return await self._assign_manual(organization_id, lead_id, config.fallback_user_id)
            raise ValueError("No eligible sales reps available for assignment")

        result: AssignmentResult

        if strategy == AssignmentStrategy.ROUND_ROBIN:
            result = await self._round_robin(organization_id, lead_id, candidates)
        elif strategy == AssignmentStrategy.LOAD_BASED:
            result = await self._load_based(organization_id, lead_id, candidates, config)
        elif strategy == AssignmentStrategy.TERRITORY:
            result = await self._territory_based(organization_id, lead_id, candidates)
        elif strategy == AssignmentStrategy.SKILL_BASED:
            result = await self._skill_based(organization_id, lead_id, candidates)
        else:
            result = await self._round_robin(organization_id, lead_id, candidates)

        # Update lead
        lead = await self.session.get(Lead, lead_id)
        if lead:
            lead.assigned_to = result.assigned_to
            await self.session.flush()

        # Publish event
        await publish(
            self.session,
            event_type=EventTypes.LEAD_ASSIGNED,
            organization_id=organization_id,
            aggregate_type="lead",
            aggregate_id=lead_id,
            payload={
                "assigned_to": str(result.assigned_to),
                "strategy": result.strategy_used,
                "reason": result.reason,
            },
        )

        logger.info(
            "lead_assigned",
            lead_id=str(lead_id),
            assigned_to=str(result.assigned_to),
            strategy=result.strategy_used,
        )

        return result

    # ── Strategies ──────────────────────────────────────

    async def _round_robin(
        self,
        organization_id: UUID,
        lead_id: UUID,
        candidates: list[User],
    ) -> AssignmentResult:
        """Fair rotation through all active reps."""
        org_key = str(organization_id)
        index = _round_robin_index.get(org_key, 0)

        selected = candidates[index % len(candidates)]
        _round_robin_index[org_key] = index + 1

        return AssignmentResult(
            assigned_to=selected.id,
            strategy_used=AssignmentStrategy.ROUND_ROBIN,
            reason=f"Round-robin rotation (position {index % len(candidates) + 1}/{len(candidates)})",
            candidates_evaluated=len(candidates),
        )

    async def _load_based(
        self,
        organization_id: UUID,
        lead_id: UUID,
        candidates: list[User],
        config: AssignmentConfig,
    ) -> AssignmentResult:
        """Assign to the rep with fewest active leads."""
        lead_counts: list[tuple[User, int]] = []

        for user in candidates:
            count_stmt = (
                select(func.count())
                .select_from(Lead)
                .where(
                    Lead.organization_id == organization_id,
                    Lead.assigned_to == user.id,
                    Lead.status.in_(["new", "contacted", "qualified", "nurture"]),
                    Lead.deleted_at.is_(None),
                )
            )
            result = await self.session.execute(count_stmt)
            count = result.scalar_one()

            if count < config.max_leads_per_rep:
                lead_counts.append((user, count))

        if not lead_counts:
            # All reps at capacity — pick the one with fewest
            for user in candidates:
                count_stmt = (
                    select(func.count())
                    .select_from(Lead)
                    .where(
                        Lead.organization_id == organization_id,
                        Lead.assigned_to == user.id,
                        Lead.status.in_(["new", "contacted", "qualified", "nurture"]),
                        Lead.deleted_at.is_(None),
                    )
                )
                result = await self.session.execute(count_stmt)
                lead_counts.append((user, result.scalar_one()))

        # Sort by count ascending
        lead_counts.sort(key=lambda x: x[1])
        selected = lead_counts[0][0]

        return AssignmentResult(
            assigned_to=selected.id,
            strategy_used=AssignmentStrategy.LOAD_BASED,
            reason=f"Lowest active lead count ({lead_counts[0][1]} leads)",
            candidates_evaluated=len(candidates),
        )

    async def _territory_based(
        self,
        organization_id: UUID,
        lead_id: UUID,
        candidates: list[User],
    ) -> AssignmentResult:
        """Assign based on territory (lead attributes like region/industry).

        In production, this would match lead.custom_fields['region'] to
        user territory configuration. For now, falls back to round-robin.
        """
        # TODO: Implement territory matching when territory config is added
        # For now, use round-robin as fallback
        result = await self._round_robin(organization_id, lead_id, candidates)
        return AssignmentResult(
            assigned_to=result.assigned_to,
            strategy_used=AssignmentStrategy.TERRITORY,
            reason="Territory fallback to round-robin (territory config not set)",
            candidates_evaluated=result.candidates_evaluated,
        )

    async def _skill_based(
        self,
        organization_id: UUID,
        lead_id: UUID,
        candidates: list[User],
    ) -> AssignmentResult:
        """Assign based on skill matching (enterprise leads → senior reps).

        In production, this would match lead.qualification['priority'] to
        user skill configuration. For now, falls back to load-based.
        """
        # TODO: Implement skill matching when user skill profiles are added
        config = AssignmentConfig()
        result = await self._load_based(organization_id, lead_id, candidates, config)
        return AssignmentResult(
            assigned_to=result.assigned_to,
            strategy_used=AssignmentStrategy.SKILL_BASED,
            reason="Skill-based fallback to load-based (skill profiles not set)",
            candidates_evaluated=result.candidates_evaluated,
        )

    async def _assign_manual(
        self,
        organization_id: UUID,
        lead_id: UUID,
        user_id: UUID,
    ) -> AssignmentResult:
        """Manual assignment override."""
        user = await self.session.get(User, user_id)
        if not user or user.organization_id != organization_id:
            raise ValueError(f"User {user_id} not found in organization")

        return AssignmentResult(
            assigned_to=user_id,
            strategy_used=AssignmentStrategy.MANUAL,
            reason="Manual assignment",
            candidates_evaluated=1,
        )

    # ── Helpers ─────────────────────────────────────────

    async def _get_eligible_reps(
        self,
        organization_id: UUID,
        config: AssignmentConfig,
    ) -> list[User]:
        """Get all active sales reps eligible for assignment."""
        stmt = (
            select(User)
            .where(
                User.organization_id == organization_id,
                User.is_active.is_(True),
                User.role.in_(["sales_rep", "sales_manager", "admin"]),
                User.deleted_at.is_(None),
            )
            .order_by(User.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
