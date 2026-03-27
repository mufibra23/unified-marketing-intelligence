"""
Unified Marketing Intelligence Platform — FastAPI
Serves data from P1-P8 as REST endpoints for MCP tools and agents.
"""

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from api.data_loader import load_all
from api.models.schemas import (
    AnomaliesResponse, Anomaly,
    AttributionModelResult, AttributionSummary, ChannelAttribution,
    DailyMetric, DailyMetricsResponse,
    HealthResponse,
    Lead, TopLeadsResponse,
    SegmentCustomer, SegmentCustomersResponse, SegmentProfile,
    SentimentAlert, SentimentAlertsResponse, SentimentSummary,
)

app = FastAPI(
    title="Unified Marketing Intelligence API",
    description="REST API serving marketing data from P1-P8 for the multi-agent orchestration layer.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    """Pre-load data on startup."""
    load_all()


# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────
@app.get("/api/v1/health", response_model=HealthResponse)
def health():
    data = load_all()
    return HealthResponse(data_loaded=len(data) > 0)


# ─────────────────────────────────────────────
# ATTRIBUTION (P6)
# ─────────────────────────────────────────────
@app.get("/api/v1/attribution/summary", response_model=AttributionSummary)
def attribution_summary():
    data = load_all()
    df = data["attribution_models"]
    results = [AttributionModelResult(**row) for row in df.to_dict("records")]
    return AttributionSummary(
        models=df["model"].unique().tolist(),
        channels=df["channel"].unique().tolist(),
        results=results,
        total_conversions=int(df.groupby("model")["attributed_conversions"].sum().mean()),
        total_revenue=float(df.groupby("model")["attributed_revenue"].sum().mean()),
    )


@app.get("/api/v1/attribution/channel/{channel}", response_model=ChannelAttribution)
def attribution_channel(channel: str):
    data = load_all()
    df = data["attribution_models"]
    channel_df = df[df["channel"] == channel]
    if channel_df.empty:
        raise HTTPException(404, f"Channel '{channel}' not found")
    results = [AttributionModelResult(**row) for row in channel_df.to_dict("records")]
    removal = data["removal_effects"].get(channel)
    return ChannelAttribution(
        channel=channel,
        model_results=results,
        avg_share=round(float(channel_df["attribution_share"].mean()), 4),
        removal_effect=removal,
    )


# ─────────────────────────────────────────────
# LEADS (P4)
# ─────────────────────────────────────────────
@app.get("/api/v1/leads/top", response_model=TopLeadsResponse)
def top_leads(
    n: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=0, ge=0, le=100),
):
    data = load_all()
    df = data["leads"]
    filtered = df[df["lead_score"] >= min_score].nlargest(n, "lead_score")
    leads = [Lead(**row) for row in filtered.to_dict("records")]
    return TopLeadsResponse(
        leads=leads,
        total_count=len(filtered),
        avg_score=round(float(filtered["lead_score"].mean()), 1) if len(filtered) > 0 else 0,
    )


@app.get("/api/v1/leads/{lead_id}", response_model=Lead)
def lead_detail(lead_id: str):
    data = load_all()
    df = data["leads"]
    match = df[df["lead_id"] == lead_id]
    if match.empty:
        raise HTTPException(404, f"Lead '{lead_id}' not found")
    return Lead(**match.iloc[0].to_dict())


# ─────────────────────────────────────────────
# SEGMENTS (P5)
# ─────────────────────────────────────────────
@app.get("/api/v1/segments/overview", response_model=list[SegmentProfile])
def segments_overview():
    data = load_all()
    df = data["segments"]
    return [SegmentProfile(**row) for row in df.to_dict("records")]


@app.get("/api/v1/segments/{segment_id}/customers", response_model=SegmentCustomersResponse)
def segment_customers(segment_id: int, limit: int = Query(default=50, ge=1, le=500)):
    data = load_all()
    customers = data["customers"]
    seg_df = customers[customers["segment_id"] == segment_id]
    if seg_df.empty:
        raise HTTPException(404, f"Segment {segment_id} not found")

    segments = data["segments"]
    seg_name = segments[segments["segment_id"] == segment_id].iloc[0]["segment_name"]

    sample = seg_df.head(limit)
    custs = [
        SegmentCustomer(
            customer_id=row["customer_id"],
            name=row["name"],
            email=row["email"],
            rfm_recency=int(row["rfm_recency"]),
            rfm_frequency=int(row["rfm_frequency"]),
            rfm_monetary=float(row["rfm_monetary"]),
            churn_probability=float(row["churn_probability"]),
            lifetime_value=float(row["lifetime_value"]),
        )
        for _, row in sample.iterrows()
    ]
    return SegmentCustomersResponse(
        segment_id=segment_id,
        segment_name=seg_name,
        customers=custs,
        total_in_segment=len(seg_df),
    )


# ─────────────────────────────────────────────
# SENTIMENT (P8)
# ─────────────────────────────────────────────
@app.get("/api/v1/sentiment/summary", response_model=SentimentSummary)
def sentiment_summary():
    data = load_all()
    df = data["reviews"]
    total = len(df)
    label_counts = df["sentiment_label"].value_counts()

    # Top topics
    all_topics = df["topics"].str.split("|").explode()
    pos_topics = df[df["sentiment_label"] == "positive"]["topics"].str.split("|").explode()
    neg_topics = df[df["sentiment_label"] == "negative"]["topics"].str.split("|").explode()

    return SentimentSummary(
        total_reviews=total,
        avg_sentiment=round(float(df["sentiment_score"].mean()), 3),
        positive_pct=round(label_counts.get("positive", 0) / total * 100, 1),
        neutral_pct=round(label_counts.get("neutral", 0) / total * 100, 1),
        negative_pct=round(label_counts.get("negative", 0) / total * 100, 1),
        avg_star_rating=round(float(df["star_rating"].mean()), 2),
        top_positive_topics=pos_topics.value_counts().head(5).index.tolist() if len(pos_topics) > 0 else [],
        top_negative_topics=neg_topics.value_counts().head(5).index.tolist() if len(neg_topics) > 0 else [],
    )


@app.get("/api/v1/sentiment/alerts", response_model=SentimentAlertsResponse)
def sentiment_alerts(severity: Optional[str] = None):
    data = load_all()
    df = data["sentiment_alerts"]
    if severity:
        df = df[df["severity"] == severity]
    alerts = [SentimentAlert(**row) for row in df.to_dict("records")]
    high_count = len([a for a in alerts if a.severity == "high"])
    return SentimentAlertsResponse(
        alerts=alerts,
        total_alerts=len(alerts),
        high_severity_count=high_count,
    )


# ─────────────────────────────────────────────
# DAILY METRICS (P1)
# ─────────────────────────────────────────────
@app.get("/api/v1/metrics/daily", response_model=DailyMetricsResponse)
def daily_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    data = load_all()
    df = data["daily_metrics"].copy()
    if start_date:
        df = df[df["date"] >= start_date]
    if end_date:
        df = df[df["date"] <= end_date]
    if channel:
        df = df[df["channel"] == channel]

    df = df.head(limit)
    # Replace NaN with None for JSON serialization
    records = df.to_dict("records")
    for r in records:
        for k, v in r.items():
            if pd.isna(v):
                r[k] = None
    metrics = [DailyMetric(**row) for row in records]
    return DailyMetricsResponse(
        metrics=metrics,
        total_rows=len(metrics),
        date_range={
            "start": df["date"].min() if len(df) > 0 else None,
            "end": df["date"].max() if len(df) > 0 else None,
        },
    )


@app.get("/api/v1/metrics/anomalies", response_model=AnomaliesResponse)
def anomalies():
    data = load_all()
    df = data["daily_metrics"]
    anom_df = df[df["is_anomaly"] == True].copy()
    anomalies = [
        Anomaly(
            date=row["date"],
            channel=row["channel"],
            anomaly_type=row["anomaly_type"],
            sessions=int(row["sessions"]),
            conversions=int(row["conversions"]),
            revenue=float(row["revenue"]),
            spend=float(row["spend"]),
        )
        for _, row in anom_df.iterrows()
    ]
    return AnomaliesResponse(anomalies=anomalies, total_anomalies=len(anomalies))
