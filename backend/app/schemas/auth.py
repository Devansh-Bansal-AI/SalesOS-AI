# ============================================================
# SalesOS AI — Auth Schemas
# ============================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ── Registration ────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """Organization + admin user registration."""

    organization_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Enforce password complexity: uppercase, lowercase, digit, special char."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class RegisterResponse(BaseModel):
    """Registration response with tokens."""

    user_id: UUID
    organization_id: UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Login ───────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Login credentials."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: "UserProfile"


# ── Token Refresh ──────────────────────────────────────────


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class TokenResponse(BaseModel):
    """New token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


# ── Password Reset ─────────────────────────────────────────


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── User Profile ───────────────────────────────────────────


class UserProfile(BaseModel):
    """Current user profile."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    organization_id: UUID
    organization_name: str | None = None
    avatar_url: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Fix forward reference
LoginResponse.model_rebuild()
