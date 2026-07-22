# ============================================================
# SalesOS AI — Lead & LeadScore Models
# ============================================================

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("idx_leads_org_status", "organization_id", "status"),
        Index("idx_leads_org_priority", "organization_id", "priority"),
        Index("idx_leads_email", "organization_id", "email"),
        Index("idx_leads_source", "organization_id", "source"),
        Index("idx_leads_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    # Contact Info
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Classification
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # AI Outputs
    qualification: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    enrichment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Engagement
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_follow_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    follow_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Metadata
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    company = relationship("Company", lazy="joined")
    scores = relationship(
        "LeadScore", back_populates="lead", lazy="selectin", order_by="LeadScore.created_at.desc()"
    )
    conversations = relationship("Conversation", back_populates="lead", lazy="noload")
    activities = relationship(
        "Activity", back_populates="lead", lazy="noload", order_by="Activity.created_at.desc()"
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.email


class LeadScore(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "lead_scores"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_score_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_confidence_range"),
        Index("idx_lead_scores_lead", "lead_id", "created_at"),
    )

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Relationships
    lead = relationship("Lead", back_populates="scores")
