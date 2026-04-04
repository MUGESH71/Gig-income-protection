# System Architecture

## Overview

GigShield is structured as a **layered architecture** with four distinct tiers:

```
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND TIER                           │
│         Streamlit Dashboard (src/frontend/ui.py)         │
│  • 6 pages: Overview, Dashboard, Register, Simulate,    │
│    Claims, Admin                                         │
└────────────────────────┬────────────────────────────────┘
                         │ calls
┌────────────────────────▼────────────────────────────────┐
│                 APPLICATION TIER                         │
│        GigShieldApp Facade (src/backend/app.py)          │
│  • Single entry point for all UI interactions           │
│  • Orchestrates all backend modules                     │
└──────┬──────────┬──────────────────┬────────────────────┘
       │          │                  │
       ▼          ▼                  ▼
┌──────────┐ ┌────────────┐ ┌───────────────┐
│ routes.py│ │claims_mgr  │ │ database.py   │
│ Business │ │ Auto-claim │ │ JSON persist  │
│ Logic    │ │ pipeline   │ │ layer         │
└────┬─────┘ └─────┬──────┘ └──────┬────────┘
     │             │               │
     ▼             ▼               ▼
┌─────────────────────────────────────────────────────────┐
│                    AI TIER                               │
│  risk_engine.py  │  premium_model.py  │  fraud_detection │
│  prediction_model.py                                    │
└─────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### AI Tier

#### `src/ai/risk_engine.py` — Hyperlocal Risk Engine
- **Input**: City name
- **Process**: Fetches (or simulates) rainfall, AQI, traffic disruption, flood alert
- **Output**: Risk Score 0–100, active triggers, claim eligibility
- **Key function**: `run_risk_assessment(location)` → dict
- **Scenario simulator**: `simulate_scenario(name, location)` for demos

#### `src/ai/premium_model.py` — Dynamic Premium Model
- **Reliability score**: Computed from tenure, work density, missed days, hours
- **Premium formula**: `base × risk_multiplier × reliability_discount`
- **Income loss estimator**: Non-linear disruption fraction model
- **Payout calculator**: Applies fraud adjustment + coverage caps

#### `src/ai/fraud_detection.py` — Fraud Detection Engine
- **5 signals**: Location mismatch, claim frequency, loss plausibility, trigger alignment, temporal anomaly
- **Output**: Fraud score 0–1 + verdict (clean / low / moderate / quarantine)
- **Action**: Quarantine if score ≥ 0.50, partial payout if 0.30–0.49

#### `src/ai/prediction_model.py` — Predictive Model
- **Input**: Current risk score + environment + city
- **Process**: Momentum decay + seasonal component + rain carryover + noise
- **Output**: Next-day risk prediction + personalized worker advisory

---

### Backend Tier

#### `src/backend/claims_manager.py` — Auto-Claim Pipeline
```
User + Risk Assessment
        │
        ▼
[1] Check risk threshold (≥65)
        │
        ▼
[2] Estimate disruption duration → income loss
        │
        ▼
[3] Fraud detection (5 signals)
        │
        ▼
[4] Compute payout (loss × coverage cap × fraud adjustment)
        │
        ▼
[5] Save to claims.json
        │
        ▼
[6] Return "₹XXX credited" message
```

#### `src/backend/routes.py` — Business Logic
- `register_user()` — Creates user + policy atomically
- `get_worker_dashboard()` — Assembles all real-time data for UI
- `trigger_scenario()` — Runs named simulation + processes claim

#### `src/backend/database.py` — Persistence Layer
- CRUD helpers for users, policies, claims
- All data stored as JSON arrays in `data/`
- Sequential ID generation (USR001, POL001, CLM001…)

---

## Data Models

### User
```json
{
  "user_id": "USR001",
  "name": "string",
  "location": "string",
  "lat": float,
  "lon": float,
  "job_type": "string",
  "weekly_income": float,
  "work_hours_per_day": float,
  "work_days_per_week": int,
  "active_weeks": int,
  "missed_days_last_month": int,
  "policy_id": "string"
}
```

### Policy
```json
{
  "policy_id": "POL001",
  "user_id": "USR001",
  "status": "active",
  "weekly_premium": float,
  "coverage_per_day": float,
  "max_weekly_payout": float,
  "risk_score": float,
  "reliability_score": float
}
```

### Claim
```json
{
  "claim_id": "CLM001",
  "user_id": "USR001",
  "trigger": "Heavy Rainfall",
  "risk_score_at_trigger": float,
  "disruption_hours": float,
  "estimated_loss": float,
  "payout_amount": float,
  "fraud_score": float,
  "status": "approved | partial_approved | quarantined",
  "auto_triggered": true,
  "message": "₹XXX credited due to high-risk conditions..."
}
```

---

## Risk Score Algorithm

```
risk_score = (rainfall_normalized × 0.30)
           + (aqi_normalized      × 0.25)
           + (traffic_index       × 0.25)
           + (flood_score         × 0.20)

where:
  rainfall_normalized = min(rainfall_mm / 100, 1) × 100
  aqi_normalized      = min(aqi / 500, 1) × 100
  traffic_index       = disruption_ratio × 100
  flood_score         = 100 if flood_alert else 0
```

---

## Automation Flow

```
Every monitoring cycle:
  For each worker:
    1. Fetch environmental data for their city
    2. Compute risk score
    3. If risk_score ≥ 65 AND active policy:
       a. Estimate income loss
       b. Run fraud detection
       c. Compute payout
       d. Save claim
       e. Notify worker
```

---

## Scalability Path

| Current (MVP) | Production |
|---|---|
| JSON files | PostgreSQL / MongoDB |
| Mock API data | IMD, CPCB, Google Maps APIs |
| Streamlit UI | React + FastAPI |
| Rule-based fraud | ML-based (Isolation Forest / XGBoost) |
| Manual scenario triggers | Cron-based continuous monitoring |
| Single-city | Pan-India with city-specific models |