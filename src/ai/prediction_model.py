"""
src/ai/prediction_model.py
---------------------------
Predictive Risk Model for GigShield.

Predicts next-day disruption risk and generates actionable worker advisories.

In a production system this would use:
  - Time-series weather forecasting APIs (IMD, AccuWeather)
  - Historical claim patterns (LSTM / Prophet)
  - City-specific seasonal models

Here we implement a rule-based simulation with stochastic elements
that realistically mimics forecasting output.
"""

import random
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Seasonal risk priors by month for Indian cities
# Values are baseline risk additions (0–30) layered on random noise
# ---------------------------------------------------------------------------
SEASONAL_RISK = {
    # Jan–Mar: relatively dry
    1: 5, 2: 5, 3: 8,
    # Apr–May: rising heat, pre-monsoon storms
    4: 12, 5: 18,
    # Jun–Sep: monsoon season – peak risk
    6: 35, 7: 45, 8: 42, 9: 30,
    # Oct–Nov: post-monsoon, residual flooding
    10: 20, 11: 10,
    # Dec: cool, dry
    12: 5,
}

# City-specific amplifiers for monsoon risk
CITY_MONSOON_FACTOR = {
    "mumbai":    1.4,
    "chennai":   1.3,
    "bengaluru": 1.2,
    "hyderabad": 1.1,
    "delhi":     0.9,  # Monsoon is shorter here
}


def _seasonal_baseline(city: str, month: int) -> float:
    """Return a seasonal baseline risk contribution for the city/month."""
    base = SEASONAL_RISK.get(month, 10)
    factor = CITY_MONSOON_FACTOR.get(city.strip().lower(), 1.0)
    return base * factor


def predict_next_day_risk(
    location: str,
    current_risk_score: float,
    current_env_data: dict,
    seed: Optional[int] = None,
) -> dict:
    """
    Predict the risk score for the next working day.

    Algorithm
    ---------
    1. Start from current risk score as a baseline (with momentum decay)
    2. Add seasonal correction for the upcoming date
    3. Apply stochastic perturbation (weather unpredictability)
    4. Clamp to [0, 100]

    Parameters
    ----------
    location          : str   City name
    current_risk_score: float Today's risk score
    current_env_data  : dict  Today's environmental readings
    seed              : int   Optional seed for reproducibility

    Returns
    -------
    dict with predicted_risk_score, trend, confidence, forecast components
    """
    if seed is not None:
        random.seed(seed)

    tomorrow = datetime.now() + timedelta(days=1)
    month = tomorrow.month

    # Momentum: tomorrow's risk is partly anchored to today's
    momentum = current_risk_score * 0.40

    # Seasonal component
    seasonal = _seasonal_baseline(location, month)

    # Stochastic noise (±15 points to simulate forecast uncertainty)
    noise = random.uniform(-15, 15)

    # Rainfall carryover: heavy rain today → elevated flood risk tomorrow
    rain_carryover = min(current_env_data.get("rainfall_mm", 0) * 0.3, 20)

    predicted = momentum + seasonal * 0.60 + noise + rain_carryover
    predicted = round(max(0, min(predicted, 100)), 2)

    # Trend vs today
    delta = predicted - current_risk_score
    if delta > 5:
        trend = "increasing"
    elif delta < -5:
        trend = "decreasing"
    else:
        trend = "stable"

    # Confidence: lower during monsoon (high variance), higher in dry season
    base_confidence = 0.75
    if month in (6, 7, 8, 9):
        confidence = round(base_confidence - 0.15, 2)
    else:
        confidence = round(base_confidence + 0.05, 2)

    return {
        "predicted_risk_score": predicted,
        "prediction_date": tomorrow.strftime("%Y-%m-%d"),
        "trend": trend,
        "delta": round(delta, 2),
        "confidence": confidence,
        "components": {
            "momentum_from_today": round(momentum, 2),
            "seasonal_component": round(seasonal * 0.60, 2),
            "rain_carryover": round(rain_carryover, 2),
            "random_noise": round(noise, 2),
        },
    }


def generate_worker_advisory(
    predicted_risk_score: float,
    trend: str,
    active_triggers: list,
    job_type: str,
    location: str,
) -> dict:
    """
    Generate personalised action recommendations for the worker
    based on predicted conditions.

    Returns
    -------
    dict with alert_level, message, recommended_actions
    """
    actions = []
    alert_level = "green"
    primary_message = "Conditions look good for tomorrow. Work as normal."

    # Alert level based on predicted score
    if predicted_risk_score >= 75:
        alert_level = "red"
        primary_message = (
            f"⚠️ High disruption risk predicted in {location} tomorrow. "
            "Consider reducing outdoor work hours."
        )
    elif predicted_risk_score >= 55:
        alert_level = "orange"
        primary_message = (
            f"⚠️ Moderate risk predicted in {location} tomorrow. "
            "Stay alert and check conditions before starting work."
        )
    elif predicted_risk_score >= 30:
        alert_level = "yellow"
        primary_message = f"🟡 Mild disruption possible in {location} tomorrow."

    # Job-specific actions
    job_lower = job_type.lower()

    if "delivery" in job_lower or "rider" in job_lower:
        if predicted_risk_score >= 55:
            actions += [
                "Avoid waterlogged routes – use elevated roads",
                "Wear rain gear and ensure bike is serviced",
                "Cluster nearby orders to minimize exposure",
            ]
        else:
            actions.append("Standard route planning is fine")

    elif "cab" in job_lower or "driver" in job_lower:
        if predicted_risk_score >= 55:
            actions += [
                "Monitor traffic apps for real-time diversions",
                "Carry emergency supplies (water, first aid)",
                "Prefer pre-booked rides over street pickups",
            ]
        else:
            actions.append("Normal operations expected")

    else:  # Freelancers, electricians, plumbers etc.
        if predicted_risk_score >= 55:
            actions += [
                "Reschedule outdoor jobs to morning hours",
                "Notify clients of possible delays proactively",
                "Secure tools and equipment against weather",
            ]
        else:
            actions.append("Proceed with scheduled assignments")

    # Trigger-specific additions
    if "Flood Alert" in active_triggers:
        actions.append("Check local flood maps before commuting")
    if "High AQI" in active_triggers:
        actions.append("Wear N95 mask – AQI hazardous for outdoor workers")
    if "Heavy Rainfall" in active_triggers:
        actions.append("Carry waterproofing for documents and electronics")

    # Insurance nudge
    if predicted_risk_score >= 65:
        actions.append(
            "Your GigShield policy is active – auto-claim will trigger if risk threshold is breached"
        )

    return {
        "alert_level": alert_level,
        "primary_message": primary_message,
        "recommended_actions": actions,
        "predicted_risk_score": predicted_risk_score,
        "trend": trend,
    }


def run_prediction_pipeline(
    location: str,
    current_risk_score: float,
    current_env_data: dict,
    job_type: str,
    active_triggers: list,
    seed: Optional[int] = None,
) -> dict:
    """
    Full prediction pipeline: forecast risk → generate advisory.
    This is the primary entry-point used by backend and UI.
    """
    forecast = predict_next_day_risk(
        location, current_risk_score, current_env_data, seed=seed
    )
    advisory = generate_worker_advisory(
        forecast["predicted_risk_score"],
        forecast["trend"],
        active_triggers,
        job_type,
        location,
    )
    return {**forecast, **advisory}