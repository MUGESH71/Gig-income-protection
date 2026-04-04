"""
src/ai/premium_model.py
-----------------------
Dynamic Premium Calculator for GigShield.

Premium Formula
---------------
  base_premium     = 5% of weekly income
  risk_multiplier  = derived from Risk Score (0–100)
  reliability_disc = derived from Worker Reliability Score (0–100)

  final_premium = base_premium × risk_multiplier × reliability_discount

The model also computes the daily coverage amount (payout per disrupted day)
and the maximum weekly payout cap.
"""

from typing import Optional


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
BASE_PREMIUM_RATE = 0.05          # 5% of weekly income
MIN_PREMIUM = 50                  # Absolute floor in ₹
MAX_PREMIUM_RATE = 0.15           # Cap at 15% of weekly income

COVERAGE_MULTIPLIER = 1.0         # Daily payout = 1× daily income by default
MAX_WEEKLY_PAYOUT_FACTOR = 1.0    # Max weekly payout ≤ 1× weekly income


# ---------------------------------------------------------------------------
# Risk multiplier table
# Risk Score → multiplier on base premium
# High risk → higher premium
# ---------------------------------------------------------------------------
def _risk_multiplier(risk_score: float) -> float:
    """
    Convert risk score (0-100) into a premium multiplier.

    Tiers:
      0–29   (Low)      → 0.80  (5% discount for low-risk workers)
      30–54  (Moderate) → 1.00  (base rate)
      55–74  (High)     → 1.30  (30% loading)
      75–100 (Critical) → 1.60  (60% loading)
    """
    if risk_score < 30:
        return 0.80
    elif risk_score < 55:
        return 1.00
    elif risk_score < 75:
        return 1.30
    else:
        return 1.60


# ---------------------------------------------------------------------------
# Reliability discount table
# Reliability Score → discount factor (< 1.0 means cheaper premium)
# Consistent workers are rewarded.
# ---------------------------------------------------------------------------
def _reliability_discount(reliability_score: float) -> float:
    """
    Convert reliability score (0-100) into a discount multiplier.

    Tiers:
      0–49   → 1.10  (10% loading – unreliable pattern)
      50–69  → 1.00  (no adjustment)
      70–84  → 0.95  (5% discount)
      85–100 → 0.88  (12% discount – highly reliable)
    """
    if reliability_score < 50:
        return 1.10
    elif reliability_score < 70:
        return 1.00
    elif reliability_score < 85:
        return 0.95
    else:
        return 0.88


def compute_reliability_score(
    active_weeks: int,
    work_days_per_week: int,
    missed_days_last_month: int,
    work_hours_per_day: float,
) -> float:
    """
    Compute a Worker Reliability Score (0–100).

    Factors
    -------
    1. Tenure bonus        : longer active history → higher base
    2. Work-day density    : more days/week → higher score
    3. Missed-day penalty  : each missed day deducts points
    4. Hours consistency   : working 6–10 hr/day is the sweet-spot

    Returns
    -------
    float  Reliability score in [0, 100]
    """
    # 1. Tenure (capped at 52 weeks = 1 year for full bonus)
    tenure_score = min(active_weeks / 52, 1.0) * 40  # max 40 pts

    # 2. Work-day density (max 6 days/week considered optimal)
    day_density_score = min(work_days_per_week / 6, 1.0) * 30  # max 30 pts

    # 3. Missed-day penalty (lose 5 pts per missed day, floored at 0)
    miss_penalty = min(missed_days_last_month * 5, 20)
    consistency_score = max(0, 20 - miss_penalty)  # max 20 pts

    # 4. Hours consistency (6–10 hr/day is optimal)
    if 6 <= work_hours_per_day <= 10:
        hours_score = 10
    elif work_hours_per_day < 6:
        hours_score = max(0, work_hours_per_day / 6 * 10)
    else:
        # Working too many hours is also slightly risky
        hours_score = max(5, 10 - (work_hours_per_day - 10) * 1.5)

    total = tenure_score + day_density_score + consistency_score + hours_score
    return round(min(total, 100), 2)


def compute_premium(
    weekly_income: float,
    risk_score: float,
    reliability_score: float,
) -> dict:
    """
    Compute the final weekly premium and coverage details.

    Parameters
    ----------
    weekly_income     : float  Worker's average weekly earnings (₹)
    risk_score        : float  From the Risk Engine (0–100)
    reliability_score : float  Worker's reliability score (0–100)

    Returns
    -------
    dict with premium breakdown
    """
    base_premium = weekly_income * BASE_PREMIUM_RATE

    r_mult = _risk_multiplier(risk_score)
    r_disc = _reliability_discount(reliability_score)

    adjusted_premium = base_premium * r_mult * r_disc

    # Apply floor and ceiling
    final_premium = max(MIN_PREMIUM, adjusted_premium)
    max_allowed   = weekly_income * MAX_PREMIUM_RATE
    final_premium = min(final_premium, max_allowed)
    final_premium = round(final_premium, 2)

    # Daily income and coverage
    daily_income   = round(weekly_income / 6, 2)   # assuming 6-day work week
    coverage_per_day = round(daily_income * COVERAGE_MULTIPLIER, 2)
    max_weekly_payout = round(weekly_income * MAX_WEEKLY_PAYOUT_FACTOR, 2)

    return {
        "weekly_income": weekly_income,
        "base_premium": round(base_premium, 2),
        "risk_multiplier": r_mult,
        "reliability_discount": r_disc,
        "adjusted_premium": round(adjusted_premium, 2),
        "final_weekly_premium": final_premium,
        "coverage_per_day": coverage_per_day,
        "max_weekly_payout": max_weekly_payout,
        "daily_income": daily_income,
        "premium_to_income_ratio": round(final_premium / weekly_income * 100, 2),
    }


def estimate_work_loss(
    daily_income: float,
    disruption_hours: float,
    work_hours_per_day: float,
) -> float:
    """
    Estimate income loss from a disruption event.

    Loss is proportional to the fraction of the work-day disrupted.
    A full-day disruption (≥ work_hours_per_day) results in 100% daily loss.

    Parameters
    ----------
    daily_income       : float  Expected income on a normal day (₹)
    disruption_hours   : float  Hours the worker was unable to work
    work_hours_per_day : float  Worker's typical daily hours

    Returns
    -------
    float  Estimated income loss (₹)
    """
    disruption_fraction = min(disruption_hours / work_hours_per_day, 1.0)
    # Non-linear penalty: partial disruptions hurt disproportionately
    # (setup costs, lost momentum, rejected orders etc.)
    adjusted_fraction = disruption_fraction ** 0.85
    estimated_loss = round(daily_income * adjusted_fraction, 2)
    return estimated_loss


def compute_payout(
    estimated_loss: float,
    coverage_per_day: float,
    max_weekly_payout: float,
    fraud_score: float,
) -> dict:
    """
    Compute the actual claim payout after applying coverage limits and
    fraud score adjustment.

    Parameters
    ----------
    estimated_loss    : float  Predicted income loss (₹)
    coverage_per_day  : float  Maximum coverage per disrupted day (₹)
    max_weekly_payout : float  Hard cap on weekly payouts (₹)
    fraud_score       : float  Fraud probability (0–1); high score reduces payout

    Returns
    -------
    dict with payout details
    """
    # Cap raw payout at coverage limit
    raw_payout = min(estimated_loss, coverage_per_day)

    # Fraud adjustment: linearly reduce payout if fraud suspected
    # Above 0.5 fraud score → payout is quarantined for manual review
    if fraud_score >= 0.50:
        adjusted_payout = 0
        status = "quarantined_fraud_review"
    elif fraud_score >= 0.30:
        # Partial payout with a fraud loading reduction
        fraud_reduction = (fraud_score - 0.30) / 0.20  # 0-1 within 0.30–0.50
        adjusted_payout = round(raw_payout * (1 - fraud_reduction * 0.4), 2)
        status = "partial_payout"
    else:
        adjusted_payout = raw_payout
        status = "full_payout"

    # Apply weekly cap
    final_payout = min(adjusted_payout, max_weekly_payout)
    final_payout = round(final_payout, 2)

    return {
        "estimated_loss": estimated_loss,
        "raw_payout": round(raw_payout, 2),
        "fraud_adjustment": round(raw_payout - adjusted_payout, 2),
        "final_payout": final_payout,
        "payout_status": status,
    }