"""Load synthetic data into memory at app startup."""

import json
import os
from functools import lru_cache

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "synthetic")


@lru_cache(maxsize=1)
def load_all():
    """Load all datasets. Called once, cached forever."""
    data = {}
    data["customers"] = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))
    data["daily_metrics"] = pd.read_csv(os.path.join(DATA_DIR, "daily_metrics.csv"))
    data["attribution_models"] = pd.read_csv(os.path.join(DATA_DIR, "attribution_model_comparison.csv"))
    data["attribution_paths"] = pd.read_csv(os.path.join(DATA_DIR, "attribution_paths.csv"))
    data["leads"] = pd.read_csv(os.path.join(DATA_DIR, "lead_scores.csv"))
    data["reviews"] = pd.read_csv(os.path.join(DATA_DIR, "sentiment_reviews.csv"))
    data["sentiment_alerts"] = pd.read_csv(os.path.join(DATA_DIR, "sentiment_alerts.csv"))
    data["segments"] = pd.read_csv(os.path.join(DATA_DIR, "segment_profiles.csv"))
    data["markov_transition"] = pd.read_csv(
        os.path.join(DATA_DIR, "markov_transition_matrix.csv"), index_col=0
    )
    with open(os.path.join(DATA_DIR, "markov_removal_effects.json")) as f:
        data["removal_effects"] = json.load(f)

    return data
