# ============================================================
# SalesOS AI — Lead API Routes
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_perm
from app.db.session import get_db
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.lead import (
    LeadAssignRequest,
    LeadCreateRequest,
    LeadFilterParams,
    LeadListResponse,
    LeadResponse,
    LeadUpdateRequest,
)
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["Leads"])


# ── Create ──────────────────────────────────────────────────


@router.post(
    "",
    response_model=APIResponse[LeadResponse],
    status_code=201,
    dependencies=[Depends(require_perm("leads:create"))],
)
async def create_lead(
    request: LeadCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new lead. Triggers qualification workflow automatically."""
    service = LeadService(db)
    result = await service.create_lead(
        user.organization_id, request, created_by=user.id
    )
    return APIResponse(data=result)


# ── List ────────────────────────────────────────────────────


@router.get(
    "",
    response_model=APIResponse[list[LeadListResponse]],
    dependencies=[Depends(require_perm("leads:read"))],
)
async def list_leads(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
    source: str | None = None,
    assigned_to: UUID | None = None,
    search: str | None = None,
):
    """List leads with filtering and pagination."""
    service = LeadService(db)
    filters = LeadFilterParams(
        status=status,
        priority=priority,
        source=source,
        assigned_to=assigned_to,
        search=search,
    )
    offset = (page - 1) * per_page
    items, total = await service.list_leads(
        user.organization_id, filters=filters, offset=offset, limit=per_page
    )
    total_pages = (total + per_page - 1) // per_page
    return APIResponse(
        data=items,
        meta=PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    )


# ── Get ─────────────────────────────────────────────────────


@router.get(
    "/{lead_id}",
    response_model=APIResponse[LeadResponse],
    dependencies=[Depends(require_perm("leads:read"))],
)
async def get_lead(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single lead by ID."""
    service = LeadService(db)
    result = await service.get_lead(user.organization_id, lead_id)
    return APIResponse(data=result)


# ── Update ──────────────────────────────────────────────────


@router.patch(
    "/{lead_id}",
    response_model=APIResponse[LeadResponse],
    dependencies=[Depends(require_perm("leads:update"))],
)
async def update_lead(
    lead_id: UUID,
    request: LeadUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update lead fields."""
    service = LeadService(db)
    result = await service.update_lead(
        user.organization_id, lead_id, request, updated_by=user.id
    )
    return APIResponse(data=result)


# ── Delete ──────────────────────────────────────────────────


@router.delete(
    "/{lead_id}",
    response_model=APIResponse,
    dependencies=[Depends(require_perm("leads:delete"))],
)
async def delete_lead(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a lead."""
    service = LeadService(db)
    await service.delete_lead(user.organization_id, lead_id)
    return APIResponse(data=None)


# ── Assign ──────────────────────────────────────────────────


@router.post(
    "/{lead_id}/assign",
    response_model=APIResponse[LeadResponse],
    dependencies=[Depends(require_perm("leads:assign"))],
)
async def assign_lead(
    lead_id: UUID,
    request: LeadAssignRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a lead to a user."""
    service = LeadService(db)
    result = await service.assign_lead(
        user.organization_id, lead_id, request.user_id, assigned_by=user.id
    )
    return APIResponse(data=result)


# ── Timeline ───────────────────────────────────────────────


@router.get(
    "/{lead_id}/timeline",
    response_model=APIResponse,
    dependencies=[Depends(require_perm("leads:read"))],
)
async def get_lead_timeline(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
):
    """Get the activity timeline for a lead."""
    from app.services.crm_service import CRMService

    crm = CRMService(db)
    offset = (page - 1) * per_page
    activities, total = await crm.get_timeline(
        user.organization_id, lead_id, offset=offset, limit=per_page
    )

    # Serialize activities
    items = [
        {
            "id": str(a.id),
            "type": a.activity_type,
            "title": a.title,
            "description": a.description,
            "metadata": a.metadata_,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in activities
    ]

    total_pages = (total + per_page - 1) // per_page
    return APIResponse(
        data=items,
        meta=PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    )
