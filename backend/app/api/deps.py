# ============================================================
# SalesOS AI — API Dependencies
# FastAPI dependency injection for auth, DB, and permissions.
# ============================================================

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import require_permission, verify_access_token

# ── Current User Context ───────────────────────────────────


@dataclass
class CurrentUser:
    """Authenticated user context injected into route handlers."""
    id: UUID
    organization_id: UUID
    role: str


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
) -> CurrentUser:
    """Extract and validate the current user from the JWT Bearer token.

    Usage:
        async def my_endpoint(user: CurrentUser = Depends(get_current_user)):
            ...
    """
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Invalid authorization header format")

    token = authorization[7:]  # Strip "Bearer "
    payload = verify_access_token(token)

    return CurrentUser(
        id=UUID(payload["sub"]),
        organization_id=UUID(payload["org"]),
        role=payload["role"],
    )


# ── Permission Dependencies ───────────────────────────────


def require_role(*roles: str):
    """Dependency that enforces one of the specified roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint(): ...
    """
    async def _check_role(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise AuthorizationError(
                f"This endpoint requires one of these roles: {', '.join(roles)}"
            )
        return user
    return _check_role


def require_perm(permission: str):
    """Dependency that enforces a specific permission.

    Usage:
        @router.post("/leads", dependencies=[Depends(require_perm("leads:create"))])
        async def create_lead(): ...
    """
    async def _check_perm(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        require_permission(user.role, permission)
        return user
    return _check_perm


# ── Optional Auth ──────────────────────────────────────────


async def get_optional_user(
    authorization: str | None = Header(None, alias="Authorization"),
) -> CurrentUser | None:
    """Like get_current_user but returns None instead of raising for unauthenticated requests."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization)
    except AuthenticationError:
        return None
