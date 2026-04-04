"""
src/backend/app.py
-------------------
GigShield Application Entry Point.

This module wires together all backend components and exposes
a clean `GigShieldApp` class that the Streamlit UI uses as its
single point of contact with the system.

Usage (from Streamlit ui.py):
    from backend.app import GigShieldApp
    app = GigShieldApp()
    dashboard = app.get_dashboard("USR001")
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Optional
from backend.routes import (
    register_user,
    get_worker_dashboard,
    trigger_scenario,
    get_all_workers_overview,
)
from backend.database import get_all_users, get_all_claims, get_all_policies
from ai.risk_engine import SCENARIO_PRESETS


class GigShieldApp:
    """
    Facade over all GigShield business logic.
    The Streamlit UI exclusively interacts with this class.
    """

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
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
        """Register a new gig worker and create their insurance policy."""
        return register_user(
            name=name,
            location=location,
            lat=lat,
            lon=lon,
            job_type=job_type,
            weekly_income=weekly_income,
            work_hours_per_day=work_hours_per_day,
            work_days_per_week=work_days_per_week,
            active_weeks=active_weeks,
            missed_days_last_month=missed_days_last_month,
        )

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_dashboard(self, user_id: str, seed: Optional[int] = None) -> dict:
        """Fetch all data for the worker's personal dashboard."""
        return get_worker_dashboard(user_id, seed=seed)

    # ------------------------------------------------------------------
    # Scenario simulation
    # ------------------------------------------------------------------

    def run_scenario(self, user_id: str, scenario_name: str) -> dict:
        """
        Simulate a named environmental scenario for a worker.

        Available scenarios: heavy_rain, high_aqi, flood_alert,
                             traffic_disruption, normal_day
        """
        return trigger_scenario(user_id, scenario_name)

    @property
    def available_scenarios(self) -> list:
        return list(SCENARIO_PRESETS.keys())

    # ------------------------------------------------------------------
    # Data access helpers
    # ------------------------------------------------------------------

    def list_workers(self) -> list:
        """Return list of all registered users."""
        return get_all_users()

    def all_workers_overview(self) -> list:
        """Return enriched overview (used for admin panel)."""
        return get_all_workers_overview()

    def platform_stats(self) -> dict:
        """High-level platform statistics."""
        users   = get_all_users()
        claims  = get_all_claims()
        policies = get_all_policies()

        total_payout = sum(
            c.get("payout_amount", 0)
            for c in claims
            if c.get("status") in ("approved", "partial_approved")
        )
        active_policies = sum(1 for p in policies if p.get("status") == "active")

        return {
            "total_workers": len(users),
            "active_policies": active_policies,
            "total_claims": len(claims),
            "total_payout_disbursed": round(total_payout, 2),
            "auto_triggered_claims": sum(
                1 for c in claims if c.get("auto_triggered", False)
            ),
        }