"""
src/ai/risk_engine.py
---------------------
Hyperlocal Risk Engine for GigShield.
Computes a composite Risk Score (0–100) for a given location
using environmental and infrastructure signals:
  - Rainfall intensity
  - Air Quality Index (AQI)
  - Traffic disruption index
  - Flood alert level

In production these would be fetched from real APIs (IMD, CPCB,
Google Maps Platform, etc.). Here we use a rich mock-data layer
that simulates realistic city-level variance.
"""

import random
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Mock environmental data store
# Keyed by city name (lowercase). Each entry holds plausible ranges.
# ---------------------------------------------------------------------------
CITY_MOCK_DATA = {
    "bengaluru": {
        "rainfall_mm": (0, 45),
        "aqi": (60, 180),
        "traffic_disruption": (0.1, 0.7),
        "flood_alert_prob": 0.15,
    },
    "mumbai": {
        "rainfall_mm": (0, 120),
        "aqi": (80, 220),
        "traffic_disruption": (0.3, 0.9),
        "flood_alert_prob": 0.35,
    },
    "delhi": {
        "rainfall_mm": (0, 30),
        "aqi": (150, 400),
        "traffic_disruption": (0.2, 0.85),
        "flood_alert_prob": 0.10,
    },
    "chennai": {
        "rainfall_mm": (0, 80),
        "aqi": (50, 160),
        "traffic_disruption": (0.1, 0.65),
        "flood_alert_prob": 0.20,
    },
    "hyderabad": {
        "rainfall_mm": (0, 55),
        "aqi": (70, 200),
        "traffic_disruption": (0.1, 0.6),
        "flood_alert_prob": 0.12,
    },
}

# Trigger thresholds that cause automatic claim activation
TRIGGER_THRESHOLDS = {
    "rainfall_mm": 40,          # Heavy rain
    "aqi": 200,                 # Hazardous AQI
    "traffic_disruption": 0.70, # Severe congestion / road blockage
    "flood_alert": True,        # Any active flood alert
}

RISK_SCORE_THRESHOLD = 65  # Scores above this auto-trigger a claim


def _get_city_key(location: str) -> str:
    """Normalize location string to match our mock-data keys."""
    return location.strip().lower()


def fetch_environmental_data(location: str, seed: Optional[int] = None) -> dict:
    """
    Simulate fetching real-time environmental data for a city.

    Parameters
    ----------
    location : str   City name (e.g. "Mumbai")
    seed     : int   Optional random seed for reproducible tests.

    Returns
    -------
    dict with keys: rainfall_mm, aqi, traffic_disruption, flood_alert
    """
    if seed is not None:
        random.seed(seed)

    city_key = _get_city_key(location)
    defaults = {
        "rainfall_mm": (0, 50),
        "aqi": (80, 250),
        "traffic_disruption": (0.1, 0.8),
        "flood_alert_prob": 0.15,
    }
    params = CITY_MOCK_DATA.get(city_key, defaults)

    rainfall = round(random.uniform(*params["rainfall_mm"]), 1)
    aqi = int(random.uniform(*params["aqi"]))
    traffic = round(random.uniform(*params["traffic_disruption"]), 2)
    flood_alert = random.random() < params["flood_alert_prob"]

    return {
        "rainfall_mm": rainfall,
        "aqi": aqi,
        "traffic_disruption": traffic,
        "flood_alert": flood_alert,
        "fetched_at": datetime.now().isoformat(),
    }


def compute_risk_score(env_data: dict) -> dict:
    """
    Compute a composite Risk Score (0–100) from environmental signals.

    Scoring weights
    ---------------
    Rainfall      : 30 %  (heavy rain severely disrupts gig work)
    AQI           : 25 %  (outdoor workers bear direct health risk)
    Traffic       : 25 %  (disruption reduces reachable job volume)
    Flood alert   : 20 %  (binary but high-impact)

    Each component is normalized to [0, 100] before weighting.
    """
    # --- Rainfall component (0–100) ---
    # Cap at 100 mm/hr for normalization
    rain_score = min(env_data["rainfall_mm"] / 100 * 100, 100)

    # --- AQI component (0–100) ---
    # AQI scale: 0–500 (India NAQI). Normalize to 0-100.
    aqi_score = min(env_data["aqi"] / 500 * 100, 100)

    # --- Traffic disruption component (0–100) ---
    traffic_score = env_data["traffic_disruption"] * 100  # already 0-1

    # --- Flood alert component (0 or 100) ---
    flood_score = 100 if env_data["flood_alert"] else 0

    # Weighted composite
    composite = (
        rain_score    * 0.30 +
        aqi_score     * 0.25 +
        traffic_score * 0.25 +
        flood_score   * 0.20
    )
    composite = round(min(composite, 100), 2)

    # Identify active triggers (those that breach thresholds)
    active_triggers = []
    if env_data["rainfall_mm"] >= TRIGGER_THRESHOLDS["rainfall_mm"]:
        active_triggers.append("Heavy Rainfall")
    if env_data["aqi"] >= TRIGGER_THRESHOLDS["aqi"]:
        active_triggers.append("High AQI")
    if env_data["traffic_disruption"] >= TRIGGER_THRESHOLDS["traffic_disruption"]:
        active_triggers.append("Traffic Disruption")
    if env_data["flood_alert"]:
        active_triggers.append("Flood Alert")

    return {
        "risk_score": composite,
        "components": {
            "rain_score": round(rain_score, 2),
            "aqi_score": round(aqi_score, 2),
            "traffic_score": round(traffic_score, 2),
            "flood_score": flood_score,
        },
        "active_triggers": active_triggers,
        "claim_eligible": composite >= RISK_SCORE_THRESHOLD,
    }


def get_risk_level(risk_score: float) -> str:
    """Map numeric risk score to a human-readable risk level."""
    if risk_score < 30:
        return "Low"
    elif risk_score < 55:
        return "Moderate"
    elif risk_score < 75:
        return "High"
    else:
        return "Critical"


def run_risk_assessment(location: str, seed: Optional[int] = None) -> dict:
    """
    Full pipeline: fetch data → compute score → return enriched result.

    This is the primary entry-point used by the backend and Streamlit UI.
    """
    env_data = fetch_environmental_data(location, seed=seed)
    risk_result = compute_risk_score(env_data)

    return {
        **env_data,
        **risk_result,
        "risk_level": get_risk_level(risk_result["risk_score"]),
        "location": location,
    }


# ---------------------------------------------------------------------------
# Simulate specific trigger scenarios (used by demo / testing)
# ---------------------------------------------------------------------------
SCENARIO_PRESETS = {
    "heavy_rain": {
        "rainfall_mm": 75,
        "aqi": 120,
        "traffic_disruption": 0.80,
        "flood_alert": False,
        "fetched_at": datetime.now().isoformat(),
    },
    "high_aqi": {
        "rainfall_mm": 5,
        "aqi": 320,
        "traffic_disruption": 0.45,
        "flood_alert": False,
        "fetched_at": datetime.now().isoformat(),
    },
    "flood_alert": {
        "rainfall_mm": 95,
        "aqi": 180,
        "traffic_disruption": 0.90,
        "flood_alert": True,
        "fetched_at": datetime.now().isoformat(),
    },
    "traffic_disruption": {
        "rainfall_mm": 10,
        "aqi": 150,
        "traffic_disruption": 0.85,
        "flood_alert": False,
        "fetched_at": datetime.now().isoformat(),
    },
    "normal_day": {
        "rainfall_mm": 2,
        "aqi": 90,
        "traffic_disruption": 0.25,
        "flood_alert": False,
        "fetched_at": datetime.now().isoformat(),
    },
}


def simulate_scenario(scenario_name: str, location: str = "Unknown") -> dict:
    """
    Return a fully computed risk assessment for a named preset scenario.
    Useful for demo triggers and testing claim automation.
    """
    if scenario_name not in SCENARIO_PRESETS:
        raise ValueError(
            f"Unknown scenario '{scenario_name}'. "
            f"Available: {list(SCENARIO_PRESETS.keys())}"
        )
    env_data = {**SCENARIO_PRESETS[scenario_name]}
    risk_result = compute_risk_score(env_data)

    return {
        **env_data,
        **risk_result,
        "risk_level": get_risk_level(risk_result["risk_score"]),
        "location": location,
        "scenario": scenario_name,
    }