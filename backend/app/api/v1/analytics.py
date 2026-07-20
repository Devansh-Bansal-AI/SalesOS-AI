# ============================================================
# SalesOS AI — Analytics REST API Router
# Domain-focused, typed analytics endpoints for workspace reporting.
# Delegates all aggregation calculations to DashboardService.
# ============================================================

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import (
    AgentAnalyticsResponse,
    AnalyticsOverviewResponse,
    PipelineAnalyticsResponse,
    SLAAnalyticsResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get high-level KPI overview",
)
async def get_analytics_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365, description="Timeframe in days")] = 30,
) -> AnalyticsOverviewResponse:
    """Get high-level KPI metrics (leads, conversion rate, revenue, SLA health)."""
    service = DashboardService(db)
    return await service.get_analytics_overview(current_user.organization_id, days=days)


@router.get(
    "/pipeline",
    response_model=PipelineAnalyticsResponse,
    summary="Get pipeline stage counts and funnel velocity",
)
async def get_pipeline_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365, description="Timeframe in days")] = 30,
) -> PipelineAnalyticsResponse:
    """Get stage counts, conversion rates, avg qualification score, and stage velocity."""
    service = DashboardService(db)
    return await service.get_pipeline_analytics(current_user.organization_id, days=days)


@router.get(
    "/agents",
    response_model=AgentAnalyticsResponse,
    summary="Get AI agent performance and cost metrics",
)
async def get_agent_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365, description="Timeframe in days")] = 30,
) -> AgentAnalyticsResponse:
    """Get generic performance, latency, success rate, and token cost metrics for all registered agents."""
    service = DashboardService(db)
    return await service.get_agent_analytics(current_user.organization_id, days=days)


@router.get(
    "/sla",
    response_model=SLAAnalyticsResponse,
    summary="Get SLA compliance and escalation metrics",
)
async def get_sla_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=365, description="Timeframe in days")] = 30,
) -> SLAAnalyticsResponse:
    """Get SLA violations, first response time, compliance rate, and escalations count."""
    service = DashboardService(db)
    return await service.get_sla_analytics(current_user.organization_id, days=days)
