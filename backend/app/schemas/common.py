# ============================================================
# SalesOS AI — Common Schemas
# Response envelopes, pagination, and shared types.
# ============================================================

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ── Response Envelopes ──────────────────────────────────────


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""

    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 0


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""

    success: bool = True
    data: T | None = None
    meta: PaginationMeta | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Individual error detail."""

    code: str
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    data: None = None
    errors: list[ErrorDetail]


# ── Pagination ──────────────────────────────────────────────


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


# ── Sort ────────────────────────────────────────────────────


class SortParams(BaseModel):
    """Query parameters for sorted endpoints."""

    sort_by: str = "created_at"
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# ── Common Fields ───────────────────────────────────────────


class TimestampSchema(BaseModel):
    """Timestamps included in most response schemas."""

    created_at: datetime
    updated_at: datetime


class IDSchema(BaseModel):
    """Base schema with UUID id."""

    id: UUID

    model_config = ConfigDict(from_attributes=True)


# ── Health Check ────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    environment: str
