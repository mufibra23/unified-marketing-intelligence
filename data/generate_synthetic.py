"""
Synthetic Data Generator for P9: Unified Marketing Intelligence Platform
Generates realistic marketing data simulating outputs from P1-P8.

Run: python data/generate_synthetic.py
"""

import os
import json
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "synthetic")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
N_CUSTOMERS = 5_000
N_DAYS = 365  # 12 months
N_CHANNELS = 8
N_REVIEWS = 2_000
N_ATTRIBUTION_PATHS = 500
N_LEADS = 1_200

CHANNELS = [
    "organic_search", "paid_search", "social_organic",
    "social_paid", "email", "referral", "direct", "display"
]

SEGMENTS = {
    0: {"name": "Champions", "description": "High value, recent, frequent buyers"},
    1: {"name": "Loyal Customers", "description": "Regular buyers with good spend"},
    2: {"name": "At Risk", "description": "Were good customers, haven't bought recently"},
    3: {"name": "Hibernating", "description": "Low engagement across all metrics"},
    4: {"name": "New Customers", "description": "Recent first purchase, potential to grow"},
}

START_DATE = datetime(2025, 4, 1)


def generate_customers():
    """Generate 5,000 customer records with RFM scores and segment assignments."""
    print("Generating customers...")
    customers = []
    for i in range(N_CUSTOMERS):
        segment_id = random.choices([0, 1, 2, 3, 4], weights=[10, 25, 20, 30, 15])[0]

        # RFM scores correlated with segment
        if segment_id == 0:  # Champions
            recency = random.randint(1, 30)
            frequency = random.randint(8, 20)
            monetary = round(random.uniform(500, 5000), 2)
        elif segment_id == 1:  # Loyal
            recency = random.randint(10, 60)
            frequency = random.randint(4, 12)
            monetary = round(random.uniform(200, 2000), 2)
        elif segment_id == 2:  # At Risk
            recency = random.randint(60, 150)
            frequency = random.randint(3, 8)
            monetary = round(random.uniform(150, 1500), 2)
        elif segment_id == 3:  # Hibernating
            recency = random.randint(120, 365)
            frequency = random.randint(1, 3)
            monetary = round(random.uniform(20, 300), 2)
        else:  # New
            recency = random.randint(1, 20)
            frequency = random.randint(1, 2)
            monetary = round(random.uniform(30, 500), 2)

        avg_sentiment = np.clip(np.random.normal(
            {0: 0.7, 1: 0.5, 2: -0.1, 3: -0.3, 4: 0.3}[segment_id], 0.25
        ), -1, 1)

        customers.append({
            "customer_id": f"CUST-{i+1:05d}",
            "name": fake.name(),
            "email": fake.email(),
            "signup_date": fake.date_between(start_date="-3y", end_date="-30d").isoformat(),
            "country": random.choices(
                ["US", "UK", "ID", "SG", "AU", "DE", "JP", "BR"],
                weights=[30, 15, 10, 8, 8, 10, 10, 9]
            )[0],
            "segment_id": segment_id,
            "segment_name": SEGMENTS[segment_id]["name"],
            "rfm_recency": recency,
            "rfm_frequency": frequency,
            "rfm_monetary": monetary,
            "total_touchpoints": random.randint(2, 50),
            "avg_sentiment": round(avg_sentiment, 3),
            "churn_probability": round(np.clip(
                {0: 0.05, 1: 0.12, 2: 0.45, 3: 0.72, 4: 0.20}[segment_id]
                + np.random.normal(0, 0.08), 0, 1
            ), 3),
            "lifetime_value": round(monetary * frequency * random.uniform(0.8, 1.5), 2),
        })

    df = pd.DataFrame(customers)
    df.to_csv(os.path.join(OUTPUT_DIR, "customers.csv"), index=False)
    print(f"  ->{len(df)} customers saved")
    return df


def generate_daily_metrics():
    """Generate 365 days of daily campaign metrics across 8 channels (simulating P1)."""
    print("Generating daily metrics...")
    rows = []
    for day_offset in range(N_DAYS):
        date = START_DATE + timedelta(days=day_offset)
        dow = date.weekday()

        for channel in CHANNELS:
            # Base traffic varies by channel
            base = {
                "organic_search": 1200, "paid_search": 800, "social_organic": 600,
                "social_paid": 500, "email": 400, "referral": 300,
                "direct": 700, "display": 350
            }[channel]

            # Weekend dip
            weekend_factor = 0.7 if dow >= 5 else 1.0
            # Seasonality (Q4 boost)
            month = date.month
            season_factor = 1.3 if month in [10, 11, 12] else (0.85 if month in [1, 2] else 1.0)
            # Random noise
            noise = np.random.normal(1, 0.15)

            sessions = max(10, int(base * weekend_factor * season_factor * noise))
            cvr = np.clip(np.random.normal(
                {"organic_search": 0.032, "paid_search": 0.045, "social_organic": 0.012,
                 "social_paid": 0.028, "email": 0.055, "referral": 0.040,
                 "direct": 0.038, "display": 0.018}[channel], 0.008
            ), 0.001, 0.15)
            conversions = max(0, int(sessions * cvr))
            revenue = round(conversions * np.random.uniform(40, 120), 2)
            spend = round(
                {"organic_search": 0, "paid_search": sessions * 1.8, "social_organic": 0,
                 "social_paid": sessions * 1.2, "email": sessions * 0.05, "referral": 0,
                 "direct": 0, "display": sessions * 0.9}[channel] * np.random.uniform(0.8, 1.2), 2
            )
            bounce_rate = round(np.clip(np.random.normal(
                {"organic_search": 0.42, "paid_search": 0.38, "social_organic": 0.55,
                 "social_paid": 0.48, "email": 0.30, "referral": 0.35,
                 "direct": 0.40, "display": 0.60}[channel], 0.08
            ), 0.05, 0.95), 3)

            # Inject anomalies (~2% of days)
            is_anomaly = random.random() < 0.02
            anomaly_type = None
            if is_anomaly:
                anomaly_type = random.choice(["traffic_spike", "traffic_drop", "cvr_drop", "spend_spike"])
                if anomaly_type == "traffic_spike":
                    sessions = int(sessions * random.uniform(2.5, 4.0))
                elif anomaly_type == "traffic_drop":
                    sessions = max(5, int(sessions * random.uniform(0.1, 0.3)))
                elif anomaly_type == "cvr_drop":
                    conversions = max(0, int(conversions * 0.1))
                elif anomaly_type == "spend_spike":
                    spend = round(spend * random.uniform(3, 5), 2)

            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "channel": channel,
                "sessions": sessions,
                "conversions": conversions,
                "revenue": revenue,
                "spend": spend,
                "bounce_rate": bounce_rate,
                "avg_session_duration": round(np.random.uniform(60, 300), 1),
                "is_anomaly": is_anomaly,
                "anomaly_type": anomaly_type,
            })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "daily_metrics.csv"), index=False)
    print(f"  ->{len(df)} daily metric rows saved ({N_DAYS} days × {N_CHANNELS} channels)")
    return df


def generate_attribution_data():
    """Generate attribution model comparison data (simulating P6)."""
    print("Generating attribution data...")

    # --- Model comparison summary ---
    models = ["first_click", "last_click", "linear", "time_decay", "position_based", "markov_chain"]
    model_results = []
    for channel in CHANNELS:
        base_share = random.uniform(0.05, 0.25)
        for model in models:
            # Each model gives slightly different attribution
            shift = np.random.normal(0, 0.03)
            share = round(np.clip(base_share + shift, 0.01, 0.50), 4)
            model_results.append({
                "channel": channel,
                "model": model,
                "attribution_share": share,
                "attributed_conversions": int(share * 8500),
                "attributed_revenue": round(share * 850000, 2),
            })

    df_models = pd.DataFrame(model_results)
    df_models.to_csv(os.path.join(OUTPUT_DIR, "attribution_model_comparison.csv"), index=False)

    # --- Markov chain transition matrix ---
    states = ["Start"] + CHANNELS + ["Conversion", "Null"]
    n_states = len(states)
    trans_matrix = np.random.dirichlet(np.ones(n_states) * 2, size=n_states)
    # Make Conversion and Null absorbing
    conv_idx = states.index("Conversion")
    null_idx = states.index("Null")
    trans_matrix[conv_idx] = np.zeros(n_states)
    trans_matrix[conv_idx][conv_idx] = 1.0
    trans_matrix[null_idx] = np.zeros(n_states)
    trans_matrix[null_idx][null_idx] = 1.0

    df_trans = pd.DataFrame(trans_matrix, index=states, columns=states).round(4)
    df_trans.to_csv(os.path.join(OUTPUT_DIR, "markov_transition_matrix.csv"))

    # --- Removal effects ---
    removal_effects = {}
    for ch in CHANNELS:
        removal_effects[ch] = round(random.uniform(0.02, 0.35), 4)
    # Normalize
    total = sum(removal_effects.values())
    removal_effects = {k: round(v / total, 4) for k, v in removal_effects.items()}

    with open(os.path.join(OUTPUT_DIR, "markov_removal_effects.json"), "w") as f:
        json.dump(removal_effects, f, indent=2)

    # --- Attribution paths ---
    paths = []
    for i in range(N_ATTRIBUTION_PATHS):
        path_length = random.randint(2, 7)
        touchpoints = random.choices(CHANNELS, k=path_length)
        converted = random.random() < 0.35
        paths.append({
            "path_id": f"PATH-{i+1:04d}",
            "touchpoints": " > ".join(touchpoints),
            "path_length": path_length,
            "converted": converted,
            "revenue": round(random.uniform(50, 500), 2) if converted else 0,
            "days_to_convert": random.randint(1, 30) if converted else None,
        })

    df_paths = pd.DataFrame(paths)
    df_paths.to_csv(os.path.join(OUTPUT_DIR, "attribution_paths.csv"), index=False)

    print(f"  ->{len(df_models)} model comparison rows, {len(df_paths)} paths, transition matrix saved")
    return df_models, df_paths


def generate_lead_scores():
    """Generate lead scoring data (simulating P4)."""
    print("Generating lead scores...")
    leads = []
    for i in range(N_LEADS):
        score = round(np.clip(np.random.beta(2, 5) * 100, 0, 100), 1)
        converted = score > 60 and random.random() < (score / 120)

        leads.append({
            "lead_id": f"LEAD-{i+1:05d}",
            "name": fake.name(),
            "email": fake.company_email(),
            "company": fake.company(),
            "industry": random.choice([
                "SaaS", "E-commerce", "Fintech", "Healthcare", "Education",
                "Manufacturing", "Retail", "Media"
            ]),
            "lead_source": random.choice([
                "organic_search", "paid_search", "social", "referral",
                "webinar", "content_download", "demo_request"
            ]),
            "lead_score": score,
            "engagement_score": round(np.clip(score + np.random.normal(0, 15), 0, 100), 1),
            "page_views": random.randint(1, 50),
            "email_opens": random.randint(0, 20),
            "time_on_site_minutes": round(random.uniform(0.5, 45), 1),
            "converted": converted,
            "conversion_probability": round(np.clip(score / 100 + np.random.normal(0, 0.1), 0, 1), 3),
            "days_in_pipeline": random.randint(1, 90),
            "last_activity_date": fake.date_between(
                start_date="-60d", end_date="today"
            ).isoformat(),
        })

    df = pd.DataFrame(leads)
    df.to_csv(os.path.join(OUTPUT_DIR, "lead_scores.csv"), index=False)
    print(f"  ->{len(df)} leads saved")
    return df


def generate_sentiment_data():
    """Generate customer reviews with sentiment (simulating P8)."""
    print("Generating sentiment data...")

    POSITIVE_TOPICS = [
        "fast shipping", "great support", "easy to use", "good value",
        "beautiful design", "reliable product", "helpful team",
        "smooth checkout", "quick response", "love the app"
    ]
    NEGATIVE_TOPICS = [
        "slow delivery", "poor support", "confusing UI", "overpriced",
        "buggy app", "wrong item", "no response", "hidden fees",
        "broken product", "terrible experience"
    ]

    reviews = []
    for i in range(N_REVIEWS):
        sentiment_score = round(np.random.normal(0.1, 0.45), 3)
        sentiment_score = np.clip(sentiment_score, -1, 1)

        if sentiment_score > 0.3:
            label = "positive"
            topics = random.sample(POSITIVE_TOPICS, k=random.randint(1, 3))
            star_rating = random.choices([4, 5], weights=[30, 70])[0]
        elif sentiment_score < -0.3:
            label = "negative"
            topics = random.sample(NEGATIVE_TOPICS, k=random.randint(1, 3))
            star_rating = random.choices([1, 2], weights=[40, 60])[0]
        else:
            label = "neutral"
            topics = random.sample(POSITIVE_TOPICS + NEGATIVE_TOPICS, k=random.randint(1, 2))
            star_rating = 3

        # Churn signal: negative sentiment + low engagement
        churn_signal = sentiment_score < -0.2 and random.random() < 0.6

        reviews.append({
            "review_id": f"REV-{i+1:05d}",
            "customer_id": f"CUST-{random.randint(1, N_CUSTOMERS):05d}",
            "date": fake.date_between(start_date="-12m", end_date="today").isoformat(),
            "source": random.choice(["app_store", "google_play", "trustpilot", "support_ticket", "social_media"]),
            "text": fake.paragraph(nb_sentences=random.randint(2, 5)),
            "sentiment_score": sentiment_score,
            "sentiment_label": label,
            "star_rating": star_rating,
            "topics": "|".join(topics),
            "churn_signal": churn_signal,
        })

    df = pd.DataFrame(reviews)
    df.to_csv(os.path.join(OUTPUT_DIR, "sentiment_reviews.csv"), index=False)

    # --- Sentiment alerts (negative spikes) ---
    alerts = []
    for day_offset in range(N_DAYS):
        date = START_DATE + timedelta(days=day_offset)
        if random.random() < 0.08:  # ~8% of days have alerts
            alerts.append({
                "date": date.strftime("%Y-%m-%d"),
                "alert_type": random.choice(["sentiment_spike", "negative_volume", "topic_shift"]),
                "severity": random.choice(["low", "medium", "high"]),
                "description": random.choice([
                    "Negative sentiment spike in app_store reviews",
                    "Unusual volume of support tickets about billing",
                    "New negative topic cluster: 'payment issues'",
                    "Social media mentions turned negative overnight",
                    "Star rating average dropped below 3.0",
                ]),
                "affected_segment": random.choice(list(SEGMENTS.values()))["name"],
                "recommended_action": random.choice([
                    "Review recent app update feedback",
                    "Escalate to customer success team",
                    "Check billing system for errors",
                    "Prepare social media response",
                    "Investigate product quality reports",
                ]),
            })

    df_alerts = pd.DataFrame(alerts)
    df_alerts.to_csv(os.path.join(OUTPUT_DIR, "sentiment_alerts.csv"), index=False)

    print(f"  ->{len(df)} reviews + {len(df_alerts)} sentiment alerts saved")
    return df, df_alerts


def generate_segment_profiles():
    """Generate segment profile summaries (simulating P5)."""
    print("Generating segment profiles...")
    profiles = []
    for seg_id, seg_info in SEGMENTS.items():
        profiles.append({
            "segment_id": seg_id,
            "segment_name": seg_info["name"],
            "description": seg_info["description"],
            "customer_count": random.randint(300, 1500),
            "avg_lifetime_value": round(random.uniform(100, 5000), 2),
            "avg_order_frequency": round(random.uniform(1, 15), 1),
            "avg_recency_days": random.randint(5, 200),
            "churn_rate": round(random.uniform(0.03, 0.75), 3),
            "top_channel": random.choice(CHANNELS),
            "avg_sentiment": round(random.uniform(-0.5, 0.8), 3),
            "recommended_action": {
                0: "Reward program, VIP access, cross-sell premium",
                1: "Upsell campaigns, loyalty program enrollment",
                2: "Win-back campaign, personalized discount, feedback survey",
                3: "Re-engagement email series, steep discount offer",
                4: "Onboarding sequence, welcome offer, product education",
            }[seg_id],
        })

    df = pd.DataFrame(profiles)
    df.to_csv(os.path.join(OUTPUT_DIR, "segment_profiles.csv"), index=False)
    print(f"  ->{len(df)} segment profiles saved")
    return df


def main():
    print("=" * 60)
    print("P9 Synthetic Data Generator")
    print("Simulating outputs from P1-P8")
    print("=" * 60)

    customers = generate_customers()
    daily_metrics = generate_daily_metrics()
    attr_models, attr_paths = generate_attribution_data()
    leads = generate_lead_scores()
    reviews, alerts = generate_sentiment_data()
    segments = generate_segment_profiles()

    # Summary stats
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Customers:          {len(customers):,}")
    print(f"Daily metric rows:  {len(daily_metrics):,}")
    print(f"Attribution models: {len(attr_models):,}")
    print(f"Attribution paths:  {len(attr_paths):,}")
    print(f"Leads:              {len(leads):,}")
    print(f"Reviews:            {len(reviews):,}")
    print(f"Sentiment alerts:   {len(alerts):,}")
    print(f"Segment profiles:   {len(segments):,}")
    print(f"\nAll files saved to: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
