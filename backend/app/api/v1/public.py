# ============================================================
# SalesOS AI — Public API Routes (No Auth Required)
#
# These endpoints are used by external forms, websites,
# and marketplaces to submit leads without authentication.
# Protected by API key validation instead.
# ============================================================

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.feature_flags import get_feature_flags
from app.db.session import get_db
from app.models.api_key import APIKey
from app.schemas.common import APIResponse
from app.schemas.lead import LeadCreateRequest, LeadResponse
from app.services.lead_service import LeadService

router = APIRouter(prefix="/public", tags=["Public"])


async def validate_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """Validate an API key and return the associated key record."""
    from app.core.security import hash_api_key

    key_hash = hash_api_key(x_api_key)
    stmt = select(APIKey).where(
        APIKey.key_hash == key_hash,
        APIKey.is_active.is_(True),
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise AuthenticationError("Invalid or inactive API key")

    # Check permissions
    if "leads:create" not in api_key.permissions:
        raise AuthorizationError("API key does not have permission to create leads")

    return api_key


@router.post(
    "/leads",
    response_model=APIResponse[LeadResponse],
    status_code=201,
)
async def submit_lead(
    request: LeadCreateRequest,
    api_key: APIKey = Depends(validate_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Submit a lead from an external source (website form, marketplace, etc.).

    Requires a valid API key with leads:create permission.
    """
    flags = get_feature_flags()
    if not await flags.is_enabled(
        "public_lead_submission", organization_id=str(api_key.organization_id)
    ):
        raise AuthorizationError("Public lead submission is disabled")

    service = LeadService(db)
    result = await service.create_lead(api_key.organization_id, request)
    return APIResponse(data=result)
