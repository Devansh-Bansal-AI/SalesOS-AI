# ============================================================
# SalesOS AI — Activities & Dashboard API Routes
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_perm
from app.db.session import get_db
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.sales_execution import (
    ActivityCreateRequest,
    ActivityResponse,
    AssignmentConfig,
    AssignmentResult,
    ConversionMetrics,
    PipelineMetrics,
    RepPerformance,
    SLAStatus,
)

router = APIRouter(tags=["Sales Execution"])


# ── Activities ──────────────────────────────────────────────


@router.post(
    "/activities",
    response_model=APIResponse[ActivityResponse],
    status_code=201,
    dependencies=[Depends(require_perm("activities:create"))],
)
async def create_activity(
    request: ActivityCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a CRM activity (note, call, task, reminder)."""
    from app.services.activity_service import ActivityService

    service = ActivityService(db)
    result = await service.create_activity(
        user.organization_id, request, user_id=user.id
    )
    return APIResponse(data=result)


@router.get(
    "/leads/{lead_id}/activities",
    response_model=APIResponse[list[ActivityResponse]],
    dependencies=[Depends(require_perm("activities:read"))],
)
async def get_lead_activities(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    activity_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    """Get the CRM timeline for a lead, optionally filtered by type."""
    from app.services.activity_service import ActivityService

    service = ActivityService(db)
    offset = (page - 1) * per_page
    items, total = await service.get_lead_timeline(
        user.organization_id, lead_id,
        activity_type=activity_type, offset=offset, limit=per_page
    )
    total_pages = (total + per_page - 1) // per_page
    return APIResponse(
        data=items,
        meta=PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    )


@router.get(
    "/leads/{lead_id}/activities/counts",
    response_model=APIResponse[dict],
    dependencies=[Depends(require_perm("activities:read"))],
)
async def get_activity_counts(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get activity counts grouped by type for a lead."""
    from app.services.activity_service import ActivityService

    service = ActivityService(db)
    counts = await service.get_activity_counts(user.organization_id, lead_id)
    return APIResponse(data=counts)


# ── Assignment ──────────────────────────────────────────────


@router.post(
    "/leads/{lead_id}/auto-assign",
    response_model=APIResponse[AssignmentResult],
    dependencies=[Depends(require_perm("leads:assign"))],
)
async def auto_assign_lead(
    lead_id: UUID,
    config: AssignmentConfig | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-assign a lead using the Assignment Engine."""
    from app.services.assignment_engine import AssignmentEngine

    engine = AssignmentEngine(db)
    result = await engine.assign(
        user.organization_id, lead_id, config
    )
    return APIResponse(data=result)


# ── SLA ─────────────────────────────────────────────────────


@router.get(
    "/leads/{lead_id}/sla",
    response_model=APIResponse[SLAStatus],
    dependencies=[Depends(require_perm("leads:read"))],
)
async def get_lead_sla_status(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check SLA status for a specific lead."""
    from app.services.sla_service import SLAService

    service = SLAService(db)
    status = await service.check_lead_sla(user.organization_id, lead_id)
    return APIResponse(data=status)


@router.get(
    "/sla/violations",
    response_model=APIResponse[list[SLAStatus]],
    dependencies=[Depends(require_perm("leads:read"))],
)
async def list_sla_violations(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all leads currently violating SLA."""
    from app.services.sla_service import SLAService

    service = SLAService(db)
    violations = await service.find_violations(user.organization_id)
    return APIResponse(data=violations)


# ── Dashboard ───────────────────────────────────────────────


@router.get(
    "/dashboard/pipeline",
    response_model=APIResponse[PipelineMetrics],
    dependencies=[Depends(require_perm("dashboard:read"))],
)
async def get_pipeline_metrics(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get pipeline overview metrics."""
    from app.services.dashboard_service import DashboardService

    service = DashboardService(db)
    metrics = await service.get_pipeline_metrics(user.organization_id, days=days)
    return APIResponse(data=metrics)


@router.get(
    "/dashboard/conversion",
    response_model=APIResponse[ConversionMetrics],
    dependencies=[Depends(require_perm("dashboard:read"))],
)
async def get_conversion_metrics(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get conversion funnel metrics."""
    from app.services.dashboard_service import DashboardService

    service = DashboardService(db)
    metrics = await service.get_conversion_metrics(user.organization_id, days=days)
    return APIResponse(data=metrics)


@router.get(
    "/dashboard/reps",
    response_model=APIResponse[list[RepPerformance]],
    dependencies=[Depends(require_perm("dashboard:read"))],
)
async def get_rep_performance(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get per-rep performance metrics."""
    from app.services.dashboard_service import DashboardService

    service = DashboardService(db)
    reps = await service.get_rep_performance(user.organization_id, days=days)
    return APIResponse(data=reps)
