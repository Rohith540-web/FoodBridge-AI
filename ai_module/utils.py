"""
FoodBridge AI Module
--------------------
Provides freshness prediction, demand scoring, and priority calculation.
Uses only stdlib (math, random) — no numpy/sklearn — so Django startup stays fast.
"""

import math
import random
from django.utils import timezone


# ---------------------------------------------------------------------------
# Freshness Prediction
# ---------------------------------------------------------------------------
CATEGORY_DECAY = {
    'cooked meals': 6,
    'dairy': 12,
    'bakery': 24,
    'fruits': 36,
    'vegetables': 48,
    'packaged': 120,
    'beverages': 168,
    'grains': 240,
}
DEFAULT_DECAY_HOURS = 24


def predict_freshness(category: str, preparation_time) -> float:
    """
    Returns a freshness score between 0.0 (spoiled) and 1.0 (fresh).
    Uses exponential decay based on food category and elapsed time.
    """
    try:
        now = timezone.now()
        if hasattr(preparation_time, 'tzinfo') and preparation_time.tzinfo is None:
            preparation_time = timezone.make_aware(preparation_time)
        elapsed_hours = max(0, (now - preparation_time).total_seconds() / 3600)
        cat_lower = (category or '').lower().strip()
        decay_hours = DEFAULT_DECAY_HOURS
        for key, val in CATEGORY_DECAY.items():
            if key in cat_lower or cat_lower in key:
                decay_hours = val
                break
        score = math.exp(-elapsed_hours / decay_hours)
        return round(min(1.0, max(0.0, score)), 4)
    except Exception:
        return 0.75


# ---------------------------------------------------------------------------
# Demand Score
# ---------------------------------------------------------------------------
HIGH_DEMAND_KEYWORDS = ['slum', 'shelter', 'orphanage', 'old age', 'hospital', 'camp', 'relief']
MED_DEMAND_KEYWORDS  = ['school', 'college', 'hostel', 'community', 'centre', 'center', 'hall']


def predict_demand_score(pickup_location: str) -> float:
    """
    Returns a demand score between 0.0 and 1.0 based on location keywords.
    """
    try:
        loc = (pickup_location or '').lower()
        for kw in HIGH_DEMAND_KEYWORDS:
            if kw in loc:
                return round(random.uniform(0.80, 1.00), 4)
        for kw in MED_DEMAND_KEYWORDS:
            if kw in loc:
                return round(random.uniform(0.55, 0.80), 4)
        return round(random.uniform(0.30, 0.60), 4)
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Priority Score
# ---------------------------------------------------------------------------

def calculate_priority_score(freshness_score: float, demand_score: float) -> float:
    """
    Combines freshness (60%) and demand (40%) into a priority score (0–100).
    """
    try:
        fs = freshness_score if freshness_score is not None else 0.75
        ds = demand_score if demand_score is not None else 0.50
        return round(((fs * 0.6) + (ds * 0.4)) * 100, 2)
    except Exception:
        return 50.0
