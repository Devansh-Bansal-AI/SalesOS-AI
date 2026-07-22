# ============================================================
# SalesOS AI — AI Sales Copilot API Router
# ============================================================

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_perm
from app.db.session import get_db
from app.schemas.common import APIResponse
from app.schemas.copilot import (
    CopilotQueryRequest,
    CopilotQueryResponse,
    DealPrepResponse,
    EmailDraftRequest,
    EmailDraftResponse,
)
from app.services.copilot_service import CopilotService

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])


@router.post(
    "/query",
    response_model=APIResponse[CopilotQueryResponse],
    dependencies=[Depends(require_perm("leads:read"))],
)
async def query_copilot(
    request: CopilotQueryRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query the SDR AI Sales Copilot for real-time sales guidance."""
    service = CopilotService(db)
    result = await service.query_copilot(user.organization_id, request)
    return APIResponse(data=result)


@router.post(
    "/draft-email",
    response_model=APIResponse[EmailDraftResponse],
    dependencies=[Depends(require_perm("leads:write"))],
)
async def draft_email(
    request: EmailDraftRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a custom, tone-controlled outreach email draft."""
    service = CopilotService(db)
    result = await service.draft_email(user.organization_id, request)
    return APIResponse(data=result)


@router.get(
    "/deal-prep/{lead_id}",
    response_model=APIResponse[DealPrepResponse],
    dependencies=[Depends(require_perm("leads:read"))],
)
async def get_deal_prep(
    lead_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get synthesized deal briefing, buyer sentiment, and objection playbook for a lead."""
    service = CopilotService(db)
    result = await service.prepare_deal_brief(user.organization_id, lead_id)
    return APIResponse(data=result)
