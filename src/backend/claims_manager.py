"""
src/backend/claims_manager.py
------------------------------
Automated Claims Processing Engine for GigShield.

Responsibilities
----------------
1. Evaluate whether conditions warrant a claim (risk threshold check)
2. Compute payout using premium_model helpers
3. Run fraud detection on each claim
4. Persist approved / quarantined claims to data/claims.json
5. Return a human-readable credit notification message
"""

from datetime import datetime
from typing import Optional

# Internal imports
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.premium_model import estimate_work_loss, compute_payout
from ai.fraud_detection import compute_fraud_score, get_fraud_label
from backend.database import (
    get_user,
    get_policy_by_user,
    get_claims_by_user,
    save_claim,
    get_all_claims,
    generate_id,
)

RISK_THRESHOLD = 65  # Minimum risk score to trigger a claim


def _default_disruption_hours(triggers: list) -> float:
    """
    Estimate disruption duration from active triggers.
    Real system would use duration from event feed; here we simulate.
    """
    if "Flood Alert" in triggers:
        return 9.0
    elif "Heavy Rainfall" in triggers:
        return 6.0
    elif "High AQI" in triggers:
        return 4.0
    elif "Traffic Disruption" in triggers:
        return 3.0
    return 2.0


def process_auto_claim(
    user_id: str,
    risk_assessment: dict,
    disruption_hours: Optional[float] = None,
) -> dict:
    """
    Core claim processing pipeline.

    Steps
    -----
    1. Validate user + policy exist
    2. Check risk threshold
    3. Estimate income loss
    4. Run fraud detection
    5. Compute final payout
    6. Save claim record
    7. Return result dict

    Parameters
    ----------
    user_id         : str   Worker identifier
    risk_assessment : dict  Output from risk_engine.run_risk_assessment()
    disruption_hours: float Override auto-estimated disruption duration

    Returns
    -------
    dict with claim details and user-facing message
    """
    # --- 1. Load user and policy ---
    user = get_user(user_id)
    if not user:
        return {"success": False, "reason": f"User {user_id} not found"}

    policy = get_policy_by_user(user_id)
    if not policy or policy.get("status") != "active":
        return {"success": False, "reason": "No active policy found"}

    # --- 2. Threshold gate ---
    risk_score = risk_assessment.get("risk_score", 0)
    if risk_score < RISK_THRESHOLD:
        return {
            "success": False,
            "reason": f"Risk score {risk_score:.1f} below threshold {RISK_THRESHOLD}",
            "risk_score": risk_score,
        }

    active_triggers = risk_assessment.get("active_triggers", [])
    primary_trigger = active_triggers[0] if active_triggers else "Environmental Risk"

    # --- 3. Estimate income loss ---
    if disruption_hours is None:
        disruption_hours = _default_disruption_hours(active_triggers)

    daily_income = policy["coverage_per_day"]  # proxy for daily income
    estimated_loss = estimate_work_loss(
        daily_income=daily_income,
        disruption_hours=disruption_hours,
        work_hours_per_day=user.get("work_hours_per_day", 8),
    )

    # --- 4. Fraud detection ---
    recent_claims = get_claims_by_user(user_id)
    fraud_result = compute_fraud_score(
        claimed_location=risk_assessment.get("location", user["location"]),
        registered_location=user["location"],
        estimated_loss=estimated_loss,
        daily_income=daily_income,
        disruption_hours=disruption_hours,
        work_hours_per_day=user.get("work_hours_per_day", 8),
        trigger=primary_trigger,
        env_risk_score=risk_score,
        recent_claims=recent_claims,
        claim_timestamp=datetime.now().isoformat(),
    )
    fraud_score = fraud_result["fraud_score"]

    # --- 5. Compute payout ---
    payout_result = compute_payout(
        estimated_loss=estimated_loss,
        coverage_per_day=policy["coverage_per_day"],
        max_weekly_payout=policy["max_weekly_payout"],
        fraud_score=fraud_score,
    )
    final_payout = payout_result["final_payout"]
    payout_status = payout_result["payout_status"]

    # --- 6. Determine claim status ---
    if fraud_result["quarantined"]:
        claim_status = "quarantined"
    elif payout_status == "partial_payout":
        claim_status = "partial_approved"
    else:
        claim_status = "approved"

    # --- 7. Build user-facing message ---
    if claim_status == "approved":
        message = (
            f"₹{final_payout:.0f} credited due to high-risk conditions "
            f"({primary_trigger}) in your area"
        )
    elif claim_status == "partial_approved":
        message = (
            f"₹{final_payout:.0f} partially credited (fraud review applied) "
            f"due to {primary_trigger} in your area"
        )
    else:
        message = (
            "Claim queued for manual review due to anomalous signals. "
            "Our team will contact you within 24 hours."
        )

    # --- 8. Persist claim ---
    all_claims = get_all_claims()
    claim_id = generate_id("CLM", all_claims, "claim_id")

    claim_record = {
        "claim_id": claim_id,
        "user_id": user_id,
        "policy_id": policy["policy_id"],
        "trigger": primary_trigger,
        "active_triggers": active_triggers,
        "risk_score_at_trigger": risk_score,
        "disruption_hours": disruption_hours,
        "estimated_loss": estimated_loss,
        "payout_amount": final_payout,
        "fraud_score": fraud_score,
        "fraud_verdict": fraud_result["verdict"],
        "status": claim_status,
        "auto_triggered": True,
        "timestamp": datetime.now().isoformat(),
        "message": message,
    }
    save_claim(claim_record)

    return {
        "success": True,
        "claim_id": claim_id,
        "status": claim_status,
        "payout": final_payout,
        "message": message,
        "fraud_label": get_fraud_label(fraud_score),
        "fraud_score": fraud_score,
        "estimated_loss": estimated_loss,
        "disruption_hours": disruption_hours,
        "risk_score": risk_score,
        "triggers": active_triggers,
    }


def get_user_claims_summary(user_id: str) -> dict:
    """Return a summary of a user's claim history."""
    claims = get_claims_by_user(user_id)
    total_paid = sum(
        c.get("payout_amount", 0)
        for c in claims
        if c.get("status") in ("approved", "partial_approved")
    )
    return {
        "total_claims": len(claims),
        "approved": sum(1 for c in claims if c.get("status") == "approved"),
        "partial": sum(1 for c in claims if c.get("status") == "partial_approved"),
        "quarantined": sum(1 for c in claims if c.get("status") == "quarantined"),
        "total_payout": round(total_paid, 2),
        "claims": claims,
    }