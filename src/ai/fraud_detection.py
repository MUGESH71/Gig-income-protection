"""
src/ai/fraud_detection.py
--------------------------
Fraud Detection Engine for GigShield.

Generates a Fraud Score (0.0–1.0) for each claim by analyzing:
  1. Location mismatch   – Was the worker in the reported area?
  2. Claim frequency     – Is this worker filing claims unusually often?
  3. Loss plausibility   – Does the estimated loss match their income profile?
  4. Trigger alignment   – Does the claimed trigger match known risk data?
  5. Temporal anomaly    – Is the claim timestamp suspicious?

Score interpretation
--------------------
  0.00–0.19 : Very Low   → Auto-approve
  0.20–0.29 : Low        → Auto-approve with flag
  0.30–0.49 : Moderate   → Partial payout, flag for review
  0.50+     : High       → Quarantine for manual investigation
"""

import random
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Weights for each fraud signal (must sum to 1.0)
# ---------------------------------------------------------------------------
SIGNAL_WEIGHTS = {
    "location_mismatch": 0.30,
    "claim_frequency":   0.25,
    "loss_plausibility": 0.25,
    "trigger_alignment": 0.10,
    "temporal_anomaly":  0.10,
}

# Maximum claims per 30-day window before frequency flag is raised
MAX_CLAIMS_PER_MONTH = 3

# Suspiciously high loss-to-income ratio
MAX_PLAUSIBLE_LOSS_RATIO = 0.85  # loss should be ≤ 85% of daily income


def _score_location_mismatch(
    claimed_location: str,
    registered_location: str,
    gps_variance_km: float = 0.0,
) -> float:
    """
    Check if the claim location matches the worker's registered city.

    In production this uses GPS coordinates + geofencing.
    Here we simulate via city name matching and an optional GPS
    variance parameter (km from registered address centroid).

    Returns
    -------
    float  Partial fraud signal [0, 1]
    """
    # City-level check
    if claimed_location.strip().lower() != registered_location.strip().lower():
        return 0.90  # Very suspicious – different city

    # GPS variance check (0 = exact match, increases with distance)
    if gps_variance_km > 50:
        return 0.80
    elif gps_variance_km > 20:
        return 0.40
    elif gps_variance_km > 5:
        return 0.15
    return 0.0  # No mismatch detected


def _score_claim_frequency(
    recent_claims: list[dict],
    window_days: int = 30,
) -> float:
    """
    Evaluate how many claims were filed in the recent window.

    Parameters
    ----------
    recent_claims : list  All historical claims for this worker
    window_days   : int   Rolling window to count claims within

    Returns
    -------
    float  Partial fraud signal [0, 1]
    """
    cutoff = datetime.now() - timedelta(days=window_days)
    recent_count = 0
    for claim in recent_claims:
        try:
            claim_dt = datetime.fromisoformat(claim.get("timestamp", ""))
            if claim_dt >= cutoff:
                recent_count += 1
        except (ValueError, TypeError):
            continue

    if recent_count == 0:
        return 0.0
    elif recent_count <= MAX_CLAIMS_PER_MONTH:
        # Normal – slight increase per claim
        return round(recent_count * 0.05, 2)
    else:
        # Beyond threshold – exponential suspicion
        excess = recent_count - MAX_CLAIMS_PER_MONTH
        return min(0.10 + excess * 0.20, 1.0)


def _score_loss_plausibility(
    estimated_loss: float,
    daily_income: float,
    disruption_hours: float,
    work_hours_per_day: float,
) -> float:
    """
    Verify that the claimed loss is realistic given income and disruption time.

    Returns
    -------
    float  Partial fraud signal [0, 1]
    """
    if daily_income <= 0:
        return 0.50  # Cannot validate – treat as moderately suspicious

    loss_ratio = estimated_loss / daily_income

    # Loss > daily income is impossible (can't lose more than you earn)
    if loss_ratio > 1.0:
        return 0.95

    # Loss > 85% of daily income with < 6 disruption hours is unlikely
    if loss_ratio > MAX_PLAUSIBLE_LOSS_RATIO:
        if disruption_hours < work_hours_per_day * 0.5:
            return 0.70  # Claiming big loss for short disruption

    # Reasonable range
    if loss_ratio <= 0.60:
        return 0.0
    else:
        # Gradual suspicion increase as ratio climbs
        return round((loss_ratio - 0.60) / 0.40 * 0.30, 2)


def _score_trigger_alignment(
    trigger: str,
    env_risk_score: float,
) -> float:
    """
    Check whether the risk score at claim time supports the reported trigger.

    A 'Flood Alert' claim with a risk score of 20 is inconsistent.

    Returns
    -------
    float  Partial fraud signal [0, 1]
    """
    HIGH_RISK_TRIGGERS = {"Flood Alert", "Heavy Rainfall"}
    MEDIUM_RISK_TRIGGERS = {"High AQI", "Traffic Disruption"}

    if trigger in HIGH_RISK_TRIGGERS and env_risk_score < 55:
        return 0.75   # Strong trigger, low risk score → mismatch
    elif trigger in MEDIUM_RISK_TRIGGERS and env_risk_score < 35:
        return 0.50
    return 0.0


def _score_temporal_anomaly(timestamp_str: str) -> float:
    """
    Flag claims filed at unusual times (e.g. middle of the night).

    Returns
    -------
    float  Partial fraud signal [0, 1]
    """
    try:
        claim_dt = datetime.fromisoformat(timestamp_str)
        hour = claim_dt.hour
        # Claims between 00:00–04:00 are slightly suspicious
        if 0 <= hour < 4:
            return 0.35
    except (ValueError, TypeError):
        pass
    return 0.0


def compute_fraud_score(
    claimed_location: str,
    registered_location: str,
    estimated_loss: float,
    daily_income: float,
    disruption_hours: float,
    work_hours_per_day: float,
    trigger: str,
    env_risk_score: float,
    recent_claims: list,
    claim_timestamp: Optional[str] = None,
    gps_variance_km: float = 0.0,
) -> dict:
    """
    Compute the composite Fraud Score and return a full signal breakdown.

    Returns
    -------
    dict with fraud_score, signals, verdict
    """
    if claim_timestamp is None:
        claim_timestamp = datetime.now().isoformat()

    # Compute individual signals
    signals = {
        "location_mismatch": _score_location_mismatch(
            claimed_location, registered_location, gps_variance_km
        ),
        "claim_frequency": _score_claim_frequency(recent_claims),
        "loss_plausibility": _score_loss_plausibility(
            estimated_loss, daily_income, disruption_hours, work_hours_per_day
        ),
        "trigger_alignment": _score_trigger_alignment(trigger, env_risk_score),
        "temporal_anomaly": _score_temporal_anomaly(claim_timestamp),
    }

    # Weighted composite score
    fraud_score = sum(
        signals[k] * SIGNAL_WEIGHTS[k] for k in signals
    )
    fraud_score = round(min(fraud_score, 1.0), 4)

    # Human-readable verdict
    if fraud_score < 0.20:
        verdict = "clean"
    elif fraud_score < 0.30:
        verdict = "low_suspicion"
    elif fraud_score < 0.50:
        verdict = "moderate_suspicion"
    else:
        verdict = "high_suspicion_quarantine"

    return {
        "fraud_score": fraud_score,
        "signals": signals,
        "verdict": verdict,
        "flagged": fraud_score >= 0.30,
        "quarantined": fraud_score >= 0.50,
    }


def get_fraud_label(fraud_score: float) -> str:
    """Return a display label for a given fraud score."""
    if fraud_score < 0.20:
        return "✅ Clean"
    elif fraud_score < 0.30:
        return "🟡 Low Risk"
    elif fraud_score < 0.50:
        return "🟠 Moderate – Review"
    else:
        return "🔴 High – Quarantined"