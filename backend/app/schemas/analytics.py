# ============================================================
# SalesOS AI — Analytics Pydantic Response Schemas
# Typed schemas for domain-focused analytics endpoints.
# ============================================================

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsOverviewResponse(BaseModel):
    """High-level KPI metrics response."""
    model_config = ConfigDict(from_attributes=True)

    timeframe_days: int = Field(30, description="Timeframe filter in days")
    total_leads: int = Field(0, description="Total lead volume in timeframe")
    active_leads: int = Field(0, description="Currently active leads")
    qualified_leads: int = Field(0, description="Qualified lead volume")
    overall_conversion_rate: float = Field(0.0, description="Percentage of leads converted")
    meetings_booked: int = Field(0, description="Total meetings booked")
    estimated_won_revenue: float = Field(0.0, description="Estimated won pipeline revenue")
    estimated_lost_revenue: float = Field(0.0, description="Estimated lost pipeline revenue")
    sla_health_percentage: float = Field(100.0, description="Percentage of leads compliant with SLA")


class PipelineAnalyticsResponse(BaseModel):
    """Pipeline visualization & stage conversion metrics."""
    model_config = ConfigDict(from_attributes=True)

    timeframe_days: int = Field(30, description="Timeframe filter in days")
    stage_counts: dict[str, int] = Field(default_factory=dict, description="Counts of leads per stage")
    funnel_conversion_rates: dict[str, float] = Field(
        default_factory=dict, description="Stage-to-stage conversion rates"
    )
    avg_qualification_score: float = Field(0.0, description="Average qualification score (0-100)")
    stage_velocity_days: dict[str, float] = Field(
        default_factory=dict, description="Average days spent per pipeline stage"
    )


class AgentMetricItem(BaseModel):
    """Generic AI agent performance metrics (no hardcoded agent names)."""
    model_config = ConfigDict(from_attributes=True)

    agent: str = Field(..., description="Agent type identifier (e.g. qualification, enrichment)")
    runs: int = Field(0, description="Total executions")
    success_rate: float = Field(100.0, description="Percentage of successful runs (0-100)")
    avg_latency_ms: float = Field(0.0, description="Average execution latency in milliseconds")
    total_tokens: int = Field(0, description="Total LLM tokens consumed")
    estimated_cost_usd: float = Field(0.0, description="Estimated USD cost of LLM tokens")


class AgentAnalyticsResponse(BaseModel):
    """Analytics response for all AI Agents."""
    model_config = ConfigDict(from_attributes=True)

    timeframe_days: int = Field(30, description="Timeframe filter in days")
    agents: list[AgentMetricItem] = Field(default_factory=list, description="Performance metrics per agent")


class SLAAnalyticsResponse(BaseModel):
    """SLA compliance and response metrics."""
    model_config = ConfigDict(from_attributes=True)

    timeframe_days: int = Field(30, description="Timeframe filter in days")
    total_violations: int = Field(0, description="Total SLA breaches")
    first_response_avg_minutes: float = Field(0.0, description="Average minutes to first contact")
    compliance_percentage: float = Field(100.0, description="SLA compliance percentage")
    escalations_count: int = Field(0, description="Total manager escalations created")
