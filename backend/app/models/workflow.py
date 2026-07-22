# ============================================================
# SalesOS AI — Workflow Instance Model
# ============================================================

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkflowInstance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        Index("idx_workflows_org", "organization_id", "status"),
        Index("idx_workflows_lead", "lead_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
