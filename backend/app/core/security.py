# ============================================================
# SalesOS AI — Security Utilities
# JWT management, password hashing, and RBAC enforcement.
# ============================================================

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
)

# ── Password Hashing ────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 for storage and lookup."""
    import hashlib

    return hashlib.sha256(api_key.encode()).hexdigest()


# ── JWT ─────────────────────────────────────────────────────


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "role": role,
        "type": TokenType.ACCESS,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: UUID,
    organization_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token."""
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "type": TokenType.REFRESH,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises AuthenticationError on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}")


def verify_access_token(token: str) -> dict[str, Any]:
    """Decode an access token and verify its type."""
    payload = decode_token(token)
    if payload.get("type") != TokenType.ACCESS:
        raise AuthenticationError("Invalid token type: expected access token")
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """Decode a refresh token and verify its type."""
    payload = decode_token(token)
    if payload.get("type") != TokenType.REFRESH:
        raise AuthenticationError("Invalid token type: expected refresh token")
    return payload


# ── RBAC ────────────────────────────────────────────────────


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    SALES_REP = "sales_rep"
    VIEWER = "viewer"


# Permission matrix — maps (role, action) to allowed.
# Missing entries default to False.
PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN: {
        "leads:create",
        "leads:read",
        "leads:read_all",
        "leads:update",
        "leads:delete",
        "leads:assign",
        "leads:qualify",
        "leads:enrich",
        "conversations:read",
        "conversations:analyze",
        "emails:send",
        "emails:read",
        "meetings:create",
        "meetings:read",
        "meetings:update",
        "meetings:delete",
        "analytics:read",
        "analytics:read_full",
        "agents:configure",
        "agents:read",
        "users:create",
        "users:read",
        "users:update",
        "users:delete",
        "api_keys:create",
        "api_keys:delete",
        "audit:read",
        "org:update",
        "decisions:override",
    },
    Role.MANAGER: {
        "leads:create",
        "leads:read",
        "leads:read_all",
        "leads:update",
        "leads:assign",
        "leads:qualify",
        "leads:enrich",
        "conversations:read",
        "conversations:analyze",
        "emails:send",
        "emails:read",
        "meetings:create",
        "meetings:read",
        "meetings:update",
        "meetings:delete",
        "analytics:read",
        "analytics:read_full",
        "agents:read",
        "users:read",
        "audit:read",
        "decisions:override",
    },
    Role.SALES_REP: {
        "leads:create",
        "leads:read",
        "leads:update",
        "leads:qualify",
        "leads:enrich",
        "conversations:read",
        "conversations:analyze",
        "emails:send",
        "emails:read",
        "meetings:create",
        "meetings:read",
        "meetings:update",
        "analytics:read",
        "decisions:override",
    },
    Role.VIEWER: {
        "leads:read",
        "leads:read_all",
        "conversations:read",
        "emails:read",
        "meetings:read",
        "analytics:read",
        "agents:read",
    },
}


def check_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    role_permissions = PERMISSIONS.get(role, set())
    return permission in role_permissions


def require_permission(role: str, permission: str) -> None:
    """Enforce permission. Raises AuthorizationError if denied."""
    if not check_permission(role, permission):
        raise AuthorizationError(f"Role '{role}' does not have permission '{permission}'")
