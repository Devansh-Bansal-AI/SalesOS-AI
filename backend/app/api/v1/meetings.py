# ============================================================
# SalesOS AI — Meetings API Routes
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_perm
from app.db.session import get_db
from app.schemas.common import APIResponse, PaginationMeta
from app.schemas.sales_execution import (
    MeetingCancelRequest,
    MeetingCreateRequest,
    MeetingListResponse,
    MeetingRescheduleRequest,
    MeetingResponse,
)

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.post(
    "",
    response_model=APIResponse[MeetingResponse],
    status_code=201,
    dependencies=[Depends(require_perm("meetings:create"))],
)
async def book_meeting(
    request: MeetingCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Book a meeting with a lead."""
    from app.services.meeting_service import MeetingService

    service = MeetingService(db)
    result = await service.book_meeting(
        user.organization_id, request, host_user_id=user.id
    )
    return APIResponse(data=result)


@router.get(
    "",
    response_model=APIResponse[list[MeetingListResponse]],
    dependencies=[Depends(require_perm("meetings:read"))],
)
async def list_upcoming_meetings(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    my_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
):
    """List upcoming meetings."""
    from app.services.meeting_service import MeetingService

    service = MeetingService(db)
    user_id = user.id if my_only else None
    items = await service.list_upcoming(
        user.organization_id, user_id=user_id, limit=limit
    )
    return APIResponse(data=items)


@router.get(
    "/{meeting_id}",
    response_model=APIResponse[MeetingResponse],
    dependencies=[Depends(require_perm("meetings:read"))],
)
async def get_meeting(
    meeting_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific meeting."""
    from app.services.meeting_service import MeetingService

    service = MeetingService(db)
    result = await service.get_meeting(user.organization_id, meeting_id)
    return APIResponse(data=result)


@router.patch(
    "/{meeting_id}/reschedule",
    response_model=APIResponse[MeetingResponse],
    dependencies=[Depends(require_perm("meetings:update"))],
)
async def reschedule_meeting(
    meeting_id: UUID,
    request: MeetingRescheduleRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reschedule a meeting."""
    from app.services.meeting_service import MeetingService

    service = MeetingService(db)
    result = await service.reschedule_meeting(
        user.organization_id, meeting_id, request
    )
    return APIResponse(data=result)


@router.post(
    "/{meeting_id}/cancel",
    response_model=APIResponse[MeetingResponse],
    dependencies=[Depends(require_perm("meetings:update"))],
)
async def cancel_meeting(
    meeting_id: UUID,
    request: MeetingCancelRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a meeting."""
    from app.services.meeting_service import MeetingService

    service = MeetingService(db)
    result = await service.cancel_meeting(
        user.organization_id, meeting_id, request
    )
    return APIResponse(data=result)


@router.get(
    "/lead/{lead_id}",
    response_model=APIResponse[list[MeetingListResponse]],
    dependencies=[Depends(require_perm("meetings:read"))],
)
async def list_lead_meetings(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List meetings for a specific lead."""
    from app.services.meeting_service import MeetingService

    service = MeetingService(db)
    offset = (page - 1) * per_page
    items, total = await service.list_by_lead(
        user.organization_id, lead_id, offset=offset, limit=per_page
    )
    total_pages = (total + per_page - 1) // per_page
    return APIResponse(
        data=items,
        meta=PaginationMeta(
            page=page, per_page=per_page, total=total, total_pages=total_pages
        ),
    )
