"""
src/backend/routes.py
----------------------
Business logic layer for GigShield.
Exposes clean functions that the Streamlit UI (and any future API) calls.

Functions are deliberately framework-agnostic – they return plain dicts,
not HTTP responses, so the UI layer can present data however it likes.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from typing import Optional

from ai.risk_engine import run_risk_assessment, simulate_scenario
from ai.premium_model import compute_reliability_score, compute_premium
from ai.prediction_model import run_prediction_pipeline
from backend.database import (
    get_all_users, get_user, save_user, get_user_by_name,
    get_all_policies, get_policy_by_user, save_policy,
    get_all_claims, get_claims_by_user,
    generate_id,
)
from backend.claims_manager import process_auto_claim, get_user_claims_summary


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_user(
    name: str,
    location: str,
    lat: float,
    lon: float,
    job_type: str,
    weekly_income: float,
    work_hours_per_day: float,
    work_days_per_week: int,
    active_weeks: int = 1,
    missed_days_last_month: int = 0,
) -> dict:
    """
    Register a new gig worker and auto-create their insurance policy.

    1. Generate user record → save to users.json
    2. Compute reliability score
    3. Run risk assessment for their city
    4. Compute premium
    5. Create and save policy
    6. Return combined onboarding data
    """
    all_users = get_all_users()

    # Prevent duplicate names (simple guard)
    if get_user_by_name(name):
        return {"success": False, "reason": f"Worker '{name}' is already registered."}

    user_id = generate_id("USR", all_users, "user_id")
    policy_id = generate_id("POL", get_all_policies(), "policy_id")

    user = {
        "user_id": user_id,
        "name": name,
        "location": location,
        "lat": lat,
        "lon": lon,
        "job_type": job_type,
        "weekly_income": weekly_income,
        "work_hours_per_day": work_hours_per_day,
        "work_days_per_week": work_days_per_week,
        "registered_on": datetime.now().strftime("%Y-%m-%d"),
        "active_weeks": active_weeks,
        "missed_days_last_month": missed_days_last_month,
        "policy_id": policy_id,
    }
    save_user(user)

    # Compute profile scores
    reliability_score = compute_reliability_score(
        active_weeks=active_weeks,
        work_days_per_week=work_days_per_week,
        missed_days_last_month=missed_days_last_month,
        work_hours_per_day=work_hours_per_day,
    )

    risk_data = run_risk_assessment(location)
    risk_score = risk_data["risk_score"]

    premium_data = compute_premium(weekly_income, risk_score, reliability_score)

    policy = {
        "policy_id": policy_id,
        "user_id": user_id,
        "status": "active",
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "weekly_premium": premium_data["final_weekly_premium"],
        "coverage_per_day": premium_data["coverage_per_day"],
        "max_weekly_payout": premium_data["max_weekly_payout"],
        "risk_score": risk_score,
        "reliability_score": reliability_score,
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
    }
    save_policy(policy)

    return {
        "success": True,
        "user": user,
        "policy": policy,
        "reliability_score": reliability_score,
        "risk_data": risk_data,
        "premium_data": premium_data,
    }


# ---------------------------------------------------------------------------
# Dashboard data fetch
# ---------------------------------------------------------------------------

def get_worker_dashboard(user_id: str, seed: Optional[int] = None) -> dict:
    """
    Fetch all data needed to render the worker dashboard:
      - User profile
      - Current risk assessment
      - Policy details
      - Prediction for tomorrow
      - Claims history
    """
    user = get_user(user_id)
    if not user:
        return {"success": False, "reason": "User not found"}

    # Live risk assessment
    risk_data = run_risk_assessment(user["location"], seed=seed)

    # Policy
    policy = get_policy_by_user(user_id)

    # Reliability
    reliability_score = compute_reliability_score(
        active_weeks=user.get("active_weeks", 1),
        work_days_per_week=user.get("work_days_per_week", 6),
        missed_days_last_month=user.get("missed_days_last_month", 0),
        work_hours_per_day=user.get("work_hours_per_day", 8),
    )

    # Premium (recalculated live to reflect current risk)
    premium_data = compute_premium(
        user["weekly_income"], risk_data["risk_score"], reliability_score
    )

    # Prediction
    prediction = run_prediction_pipeline(
        location=user["location"],
        current_risk_score=risk_data["risk_score"],
        current_env_data=risk_data,
        job_type=user["job_type"],
        active_triggers=risk_data["active_triggers"],
        seed=seed,
    )

    # Claims
    claims_summary = get_user_claims_summary(user_id)

    return {
        "success": True,
        "user": user,
        "risk_data": risk_data,
        "policy": policy,
        "reliability_score": reliability_score,
        "premium_data": premium_data,
        "prediction": prediction,
        "claims_summary": claims_summary,
    }


# ---------------------------------------------------------------------------
# Scenario simulation (demo triggers)
# ---------------------------------------------------------------------------

def trigger_scenario(user_id: str, scenario_name: str) -> dict:
    """
    Simulate a named environmental scenario and auto-process any resulting claim.

    Parameters
    ----------
    user_id       : str  Worker to simulate for
    scenario_name : str  One of: heavy_rain, high_aqi, flood_alert,
                         traffic_disruption, normal_day

    Returns
    -------
    dict with risk assessment + claim result (if triggered)
    """
    user = get_user(user_id)
    if not user:
        return {"success": False, "reason": "User not found"}

    risk_data = simulate_scenario(scenario_name, location=user["location"])

    claim_result = None
    if risk_data["claim_eligible"]:
        claim_result = process_auto_claim(user_id, risk_data)

    prediction = run_prediction_pipeline(
        location=user["location"],
        current_risk_score=risk_data["risk_score"],
        current_env_data=risk_data,
        job_type=user["job_type"],
        active_triggers=risk_data["active_triggers"],
    )

    return {
        "success": True,
        "scenario": scenario_name,
        "risk_data": risk_data,
        "claim_result": claim_result,
        "prediction": prediction,
    }


# ---------------------------------------------------------------------------
# Policy management
# ---------------------------------------------------------------------------

def get_all_workers_overview() -> list:
    """Return enriched overview of all workers (for admin view)."""
    users = get_all_users()
    overview = []
    for user in users:
        policy = get_policy_by_user(user["user_id"])
        claims = get_claims_by_user(user["user_id"])
        overview.append({
            **user,
            "policy": policy,
            "total_claims": len(claims),
            "total_payout": sum(
                c.get("payout_amount", 0) for c in claims
                if c.get("status") in ("approved", "partial_approved")
            ),
        })
    return overview