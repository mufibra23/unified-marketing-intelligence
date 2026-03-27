"""Pydantic schemas for the Unified Marketing Intelligence API."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ── Health ──
class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    data_loaded: bool = True


# ── Attribution ──
class AttributionModelResult(BaseModel):
    channel: str
    model: str
    attribution_share: float
    attributed_conversions: int
    attributed_revenue: float


class AttributionSummary(BaseModel):
    models: list[str]
    channels: list[str]
    results: list[AttributionModelResult]
    total_conversions: int
    total_revenue: float


class ChannelAttribution(BaseModel):
    channel: str
    model_results: list[AttributionModelResult]
    avg_share: float
    removal_effect: Optional[float] = None


# ── Leads ──
class Lead(BaseModel):
    lead_id: str
    name: str
    email: str
    company: str
    industry: str
    lead_source: str
    lead_score: float
    engagement_score: float
    conversion_probability: float
    converted: bool
    days_in_pipeline: int
    last_activity_date: str


class TopLeadsResponse(BaseModel):
    leads: list[Lead]
    total_count: int
    avg_score: float


# ── Segments ──
class SegmentProfile(BaseModel):
    segment_id: int
    segment_name: str
    description: str
    customer_count: int
    avg_lifetime_value: float
    avg_order_frequency: float
    avg_recency_days: int
    churn_rate: float
    top_channel: str
    avg_sentiment: float
    recommended_action: str


class SegmentCustomer(BaseModel):
    customer_id: str
    name: str
    email: str
    rfm_recency: int
    rfm_frequency: int
    rfm_monetary: float
    churn_probability: float
    lifetime_value: float


class SegmentCustomersResponse(BaseModel):
    segment_id: int
    segment_name: str
    customers: list[SegmentCustomer]
    total_in_segment: int


# ── Sentiment ──
class SentimentSummary(BaseModel):
    total_reviews: int
    avg_sentiment: float
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    avg_star_rating: float
    top_positive_topics: list[str]
    top_negative_topics: list[str]


class SentimentAlert(BaseModel):
    date: str
    alert_type: str
    severity: str
    description: str
    affected_segment: str
    recommended_action: str


class SentimentAlertsResponse(BaseModel):
    alerts: list[SentimentAlert]
    total_alerts: int
    high_severity_count: int


# ── Metrics ──
class DailyMetric(BaseModel):
    date: str
    channel: str
    sessions: int
    conversions: int
    revenue: float
    spend: float
    bounce_rate: float
    avg_session_duration: float
    is_anomaly: bool
    anomaly_type: Optional[str] = None


class DailyMetricsResponse(BaseModel):
    metrics: list[DailyMetric]
    total_rows: int
    date_range: dict


class Anomaly(BaseModel):
    date: str
    channel: str
    anomaly_type: str
    sessions: int
    conversions: int
    revenue: float
    spend: float


class AnomaliesResponse(BaseModel):
    anomalies: list[Anomaly]
    total_anomalies: int
