"""
src/frontend/ui.py
-------------------
GigShield Streamlit Dashboard.

Run with:
    streamlit run src/frontend/ui.py

Sections
--------
1.  Platform Overview   – headline KPIs
2.  Worker Dashboard    – personal risk, premium, prediction
3.  Register Worker     – onboarding form
4.  Simulate Scenario   – trigger demo events with auto-claim
5.  Claims History      – per-worker or global claim log
6.  Admin Panel         – all workers overview
"""

import sys
import os
# Ensure project root is on the path
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_ROOT, "src"))

import streamlit as st
import json
from datetime import datetime

from backend.app import GigShieldApp

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GEI — Parametric Insurance for Gig Workers",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Custom CSS — deep navy + amber accent aesthetic
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0d1117;
    color: #e6edf3;
  }
  h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {
    font-family: 'Syne', sans-serif;
  }
  .block-container { padding-top: 1.5rem; }

  /* KPI Cards */
  .kpi-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.5rem;
  }
  .kpi-label {
    font-size: 0.78rem;
    color: #8b949e;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
  }
  .kpi-value {
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: #f0b429;
    line-height: 1;
  }
  .kpi-sub {
    font-size: 0.75rem;
    color: #8b949e;
    margin-top: 0.25rem;
  }

  /* Alert banners */
  .alert-green  { background:#0d3321; border-left:4px solid #3fb950; padding:1rem; border-radius:8px; margin:.5rem 0; }
  .alert-yellow { background:#2d2b00; border-left:4px solid #d29922; padding:1rem; border-radius:8px; margin:.5rem 0; }
  .alert-orange { background:#3d1f00; border-left:4px solid #f0883e; padding:1rem; border-radius:8px; margin:.5rem 0; }
  .alert-red    { background:#3b0d0c; border-left:4px solid #f85149; padding:1rem; border-radius:8px; margin:.5rem 0; }

  /* Credit notification */
  .credit-banner {
    background: linear-gradient(90deg, #0a3d0a, #0d4a1a);
    border: 1px solid #3fb950;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #3fb950;
    margin: 1rem 0;
    box-shadow: 0 0 20px rgba(63,185,80,0.15);
  }

  /* Risk gauge */
  .risk-badge {
    display:inline-block;
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.85rem;
    font-family: 'Syne', sans-serif;
  }
  .risk-low      { background:#0d3321; color:#3fb950; border:1px solid #3fb950; }
  .risk-moderate { background:#2d2b00; color:#d29922; border:1px solid #d29922; }
  .risk-high     { background:#3d1f00; color:#f0883e; border:1px solid #f0883e; }
  .risk-critical { background:#3b0d0c; color:#f85149; border:1px solid #f85149; }

  /* Metric pill row */
  .pill-row { display:flex; gap:1rem; flex-wrap:wrap; margin:.5rem 0; }
  .pill {
    background:#1c2333; border:1px solid #30363d; border-radius:8px;
    padding:0.5rem 0.9rem; font-size:0.82rem; color:#c9d1d9;
  }
  .pill b { color:#f0b429; }

  /* Sidebar styling */
  section[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
  }
  section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.9rem;
    padding: 0.3rem 0;
  }

  /* Button overrides */
  .stButton > button {
    background: linear-gradient(135deg, #f0b429, #e09000);
    color: #0d1117;
    font-weight: 700;
    font-family: 'Syne', sans-serif;
    border: none;
    border-radius: 8px;
    padding: 0.55rem 1.5rem;
    transition: opacity 0.2s;
  }
  .stButton > button:hover { opacity: 0.88; }

  /* Tabs */
  .stTabs [data-baseweb="tab"] {
    font-family: 'Syne', sans-serif;
    font-size: 0.88rem;
    font-weight: 600;
  }
  .stTabs [aria-selected="true"] { border-bottom-color: #f0b429 !important; }

  /* Dataframe */
  .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }

  /* Divider */
  hr { border-color: #21262d; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# App instance (cached across reruns)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_app():
    return GigShieldApp()

app = get_app()


# ──────────────────────────────────────────────────────────────────────────────
# Helper renderers
# ──────────────────────────────────────────────────────────────────────────────

def kpi(label: str, value: str, sub: str = ""):
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>"""


def risk_badge(level: str) -> str:
    cls = f"risk-{level.lower()}"
    icons = {"low": "🟢", "moderate": "🟡", "high": "🟠", "critical": "🔴"}
    icon = icons.get(level.lower(), "⚪")
    return f'<span class="risk-badge {cls}">{icon} {level}</span>'


def alert_box(level: str, msg: str):
    st.markdown(f'<div class="alert-{level}">{msg}</div>', unsafe_allow_html=True)


def credit_banner(msg: str):
    st.markdown(f'<div class="credit-banner">💚 {msg}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar navigation
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 1.5rem;">
      <span style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;color:#f0b429;">🛡️ GigShield</span><br>
      <span style="font-size:0.78rem;color:#8b949e;">Parametric Insurance for Gig Workers</span>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        [
            "🏠  Platform Overview",
            "📊  Worker Dashboard",
            "➕  Register Worker",
            "⚡  Simulate Scenario",
            "📋  Claims History",
            "🗂️  Admin Panel",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("<span style='font-size:0.75rem;color:#8b949e;'>Built for India's 15M+ gig workers</span>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 1 — Platform Overview
# ──────────────────────────────────────────────────────────────────────────────
if page == "🏠  Platform Overview":
    st.markdown("## 🛡️ GEI Platform")
    st.markdown("<span style='color:#8b949e;'>Real-time parametric insurance powered by AI — zero paperwork, zero waiting.</span>", unsafe_allow_html=True)
    st.markdown("---")

    stats = app.platform_stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(kpi("Registered Workers", str(stats["total_workers"]), "across India"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Active Policies", str(stats["active_policies"]), "auto-managed"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Claims Processed", str(stats["total_claims"]), "100% auto-triggered"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Total Disbursed", f"₹{stats['total_payout_disbursed']:,.0f}", "instant payouts"), unsafe_allow_html=True)
    with c5: st.markdown(kpi("Zero-Touch Claims", str(stats["auto_triggered_claims"]), "no manual filing"), unsafe_allow_html=True)

    st.markdown("---")

    col_l, col_r = st.columns([1.4, 1])

    with col_l:
        st.markdown("### How GEI Works")
        st.markdown("""
        <div style="display:grid;gap:.75rem;margin-top:.5rem;">
          <div class="kpi-card" style="padding:.8rem 1rem;">
            <b style="color:#f0b429;">① Environmental Monitoring</b><br>
            <span style="font-size:.85rem;color:#8b949e;">Real-time data: Rainfall, AQI, Traffic, Flood Alerts — updated continuously for every city.</span>
          </div>
          <div class="kpi-card" style="padding:.8rem 1rem;">
            <b style="color:#f0b429;">② AI Risk Engine</b><br>
            <span style="font-size:.85rem;color:#8b949e;">Hyperlocal risk score (0–100) computed from multiple signals with city-specific weights.</span>
          </div>
          <div class="kpi-card" style="padding:.8rem 1rem;">
            <b style="color:#f0b429;">③ Dynamic Premium</b><br>
            <span style="font-size:.85rem;color:#8b949e;">Weekly premium adjusts to your risk profile and reliability score — fair pricing, always.</span>
          </div>
          <div class="kpi-card" style="padding:.8rem 1rem;">
            <b style="color:#f0b429;">④ Zero-Touch Claims</b><br>
            <span style="font-size:.85rem;color:#8b949e;">Risk score breaches threshold → claim auto-filed → payout credited in seconds. No forms needed.</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown("### Automation Triggers")
        triggers = [
            ("🌧️", "Heavy Rainfall", "> 40 mm/hr", "orange"),
            ("😷", "High AQI", "> 200 NAQI", "red"),
            ("🌊", "Flood Alert", "Active alert", "red"),
            ("🚦", "Traffic Disruption", "> 70% index", "orange"),
            ("☀️", "Normal Day", "Risk < 30", "green"),
        ]
        for icon, name, cond, color in triggers:
            st.markdown(
                f'<div class="alert-{color}" style="padding:.6rem .8rem;margin-bottom:.3rem;">'
                f'<b>{icon} {name}</b> — <span style="font-size:.82rem;">{cond}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("### Supported Job Types")
        for jt in ["🛵 Delivery Rider", "🚕 Cab Driver", "⚡ Electrician", "🔧 Plumber", "🏠 Home Services"]:
            st.markdown(f"- {jt}")


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 2 — Worker Dashboard
# ──────────────────────────────────────────────────────────────────────────────
elif page == "📊  Worker Dashboard":
    st.markdown("## 📊 Worker Dashboard")

    workers = app.list_workers()
    if not workers:
        st.warning("No workers registered yet. Use **Register Worker** to add one.")
        st.stop()

    worker_names = {f"{w['name']} ({w['user_id']})": w["user_id"] for w in workers}
    selected_label = st.selectbox("Select Worker", list(worker_names.keys()))
    user_id = worker_names[selected_label]

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

    with st.spinner("Fetching live data…"):
        data = app.get_dashboard(user_id)

    if not data["success"]:
        st.error(data["reason"])
        st.stop()

    user     = data["user"]
    risk     = data["risk_data"]
    policy   = data["policy"]
    pred     = data["prediction"]
    claims   = data["claims_summary"]
    premium  = data["premium_data"]
    rel      = data["reliability_score"]

    # ── Profile row ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="kpi-card" style="display:flex;align-items:center;gap:1.5rem;padding:1rem 1.5rem;">
      <div style="font-size:2.5rem;">{'🛵' if 'Delivery' in user['job_type'] else '🚕' if 'Cab' in user['job_type'] else '🔧'}</div>
      <div>
        <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;">{user['name']}</div>
        <div class="pill-row">
          <div class="pill">📍 {user['location']}</div>
          <div class="pill">💼 {user['job_type']}</div>
          <div class="pill">🪙 <b>₹{user['weekly_income']:,}</b>/week</div>
          <div class="pill">📅 Since {user['registered_on']}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── KPI row ──────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(kpi("Risk Score", f"{risk['risk_score']:.0f}/100", risk['risk_level']), unsafe_allow_html=True)
    with k2: st.markdown(kpi("Reliability Score", f"{rel:.0f}/100", "worker consistency"), unsafe_allow_html=True)
    with k3: st.markdown(kpi("Weekly Premium", f"₹{premium['final_weekly_premium']:.0f}", f"covers ₹{premium['coverage_per_day']:.0f}/day"), unsafe_allow_html=True)
    with k4: st.markdown(kpi("Total Claimed", f"₹{claims['total_payout']:,}", f"{claims['total_claims']} claims"), unsafe_allow_html=True)

    st.markdown("---")

    left, right = st.columns(2)

    # ── Left: Risk assessment ─────────────────────────────────────────────
    with left:
        st.markdown("### 🌍 Live Risk Assessment")
        st.markdown(f"Risk Level: {risk_badge(risk['risk_level'])}", unsafe_allow_html=True)

        # Environmental readings
        ec1, ec2 = st.columns(2)
        with ec1:
            rain = risk.get("rainfall_mm", 0)
            rain_color = "red" if rain >= 40 else "orange" if rain >= 20 else "green"
            st.markdown(f'<div class="alert-{rain_color}"><b>🌧️ Rainfall</b><br><span style="font-size:1.4rem;font-weight:700;">{rain} mm</span></div>', unsafe_allow_html=True)

            traffic = risk.get("traffic_disruption", 0)
            t_color = "red" if traffic >= 0.7 else "orange" if traffic >= 0.45 else "green"
            st.markdown(f'<div class="alert-{t_color}"><b>🚦 Traffic Disruption</b><br><span style="font-size:1.4rem;font-weight:700;">{traffic*100:.0f}%</span></div>', unsafe_allow_html=True)

        with ec2:
            aqi = risk.get("aqi", 0)
            aqi_color = "red" if aqi >= 200 else "orange" if aqi >= 100 else "green"
            st.markdown(f'<div class="alert-{aqi_color}"><b>😷 AQI</b><br><span style="font-size:1.4rem;font-weight:700;">{aqi}</span></div>', unsafe_allow_html=True)

            flood = risk.get("flood_alert", False)
            st.markdown(f'<div class="alert-{"red" if flood else "green"}"><b>🌊 Flood Alert</b><br><span style="font-size:1.4rem;font-weight:700;">{"ACTIVE ⚠️" if flood else "None"}</span></div>', unsafe_allow_html=True)

        # Active triggers
        triggers = risk.get("active_triggers", [])
        if triggers:
            st.markdown(f"""
            <div class="alert-orange" style="margin-top:.5rem;">
              <b>⚡ Active Triggers:</b> {' &nbsp;|&nbsp; '.join(triggers)}
            </div>""", unsafe_allow_html=True)

        # Claim eligibility
        if risk.get("claim_eligible"):
            alert_box("red", "🚨 <b>Claim Eligible!</b> Risk score exceeds threshold. Auto-claim will be triggered.")
        else:
            alert_box("green", "✅ Risk within normal range. No claim trigger required.")

    # ── Right: Policy + Prediction ───────────────────────────────────────
    with right:
        st.markdown("### 📄 Policy Details")
        if policy:
            st.markdown(f"""
            <div class="kpi-card">
              <div class="pill-row">
                <div class="pill">ID: <b>{policy['policy_id']}</b></div>
                <div class="pill">Status: <b style="color:#3fb950;">{policy['status'].upper()}</b></div>
                <div class="pill">Since: <b>{policy['start_date']}</b></div>
              </div>
              <div class="pill-row" style="margin-top:.5rem;">
                <div class="pill">Premium: <b>₹{policy['weekly_premium']:.0f}/wk</b></div>
                <div class="pill">Coverage: <b>₹{policy['coverage_per_day']:.0f}/day</b></div>
                <div class="pill">Max Payout: <b>₹{policy['max_weekly_payout']:,.0f}/wk</b></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 🔮 Tomorrow's Forecast")
        pred_score = pred.get("predicted_risk_score", 0)
        pred_level = "Low" if pred_score < 30 else "Moderate" if pred_score < 55 else "High" if pred_score < 75 else "Critical"
        trend_icon = "📈" if pred["trend"] == "increasing" else "📉" if pred["trend"] == "decreasing" else "➡️"

        st.markdown(f"""
        <div class="kpi-card">
          <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.75rem;">
            <div>
              <div class="kpi-label">Predicted Risk</div>
              <div class="kpi-value">{pred_score:.0f}</div>
            </div>
            <div>
              <div class="kpi-label">Trend</div>
              <div style="font-size:1.5rem;">{trend_icon} {pred['trend'].title()}</div>
            </div>
            <div>
              <div class="kpi-label">Confidence</div>
              <div style="font-size:1.2rem;font-weight:700;color:#f0b429;">{pred['confidence']*100:.0f}%</div>
            </div>
          </div>
          <div style="font-size:.88rem;color:#c9d1d9;margin-bottom:.5rem;">{pred.get('primary_message','')}</div>
        </div>
        """, unsafe_allow_html=True)

        actions = pred.get("recommended_actions", [])
        if actions:
            st.markdown("**📌 Recommended Actions**")
            for a in actions:
                st.markdown(f"- {a}")

    # ── Claims history ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Recent Claims")
    recent = claims.get("claims", [])
    if recent:
        for claim in reversed(recent[-5:]):
            status_color = "green" if claim["status"] == "approved" else "orange" if claim["status"] == "partial_approved" else "red"
            credit_banner(claim.get("message", "Claim processed"))
            st.markdown(f"""
            <div class="pill-row">
              <div class="pill">ID: <b>{claim['claim_id']}</b></div>
              <div class="pill">Trigger: <b>{claim['trigger']}</b></div>
              <div class="pill">Risk: <b>{claim['risk_score_at_trigger']:.0f}</b></div>
              <div class="pill">Payout: <b>₹{claim['payout_amount']:,.0f}</b></div>
              <div class="pill">Fraud: <b>{claim['fraud_score']:.2f}</b></div>
              <div class="pill">Date: <b>{claim['timestamp'][:10]}</b></div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No claims yet for this worker.")


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 3 — Register Worker
# ──────────────────────────────────────────────────────────────────────────────
elif page == "➕  Register Worker":
    st.markdown("## ➕ Register New Worker")
    st.markdown("<span style='color:#8b949e;'>Fill in the details to onboard a gig worker and create their policy instantly.</span>", unsafe_allow_html=True)
    st.markdown("---")

    with st.form("registration_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full Name", placeholder="e.g. Ravi Kumar")
            location = st.selectbox("City", ["Bengaluru", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad"])
            job_type = st.selectbox("Job Type", ["Delivery Rider", "Cab Driver", "Freelance Electrician", "Plumber", "Home Services", "Courier", "Food Delivery"])
            weekly_income = st.number_input("Weekly Income (₹)", min_value=500, max_value=50000, value=4500, step=100)

        with c2:
            work_hours = st.slider("Work Hours per Day", 2, 14, 8)
            work_days  = st.slider("Work Days per Week", 1, 7, 6)
            active_weeks = st.number_input("Active Weeks on Platform", min_value=0, max_value=200, value=4)
            missed_days  = st.number_input("Missed Days Last Month", min_value=0, max_value=30, value=1)

        # City coordinates (simplified)
        city_coords = {
            "Bengaluru": (12.9716, 77.5946), "Mumbai": (19.0760, 72.8777),
            "Delhi": (28.7041, 77.1025), "Chennai": (13.0827, 80.2707),
            "Hyderabad": (17.3850, 78.4867), "Pune": (18.5204, 73.8567),
            "Kolkata": (22.5726, 88.3639), "Ahmedabad": (23.0225, 72.5714),
        }

        submitted = st.form_submit_button("🛡️ Register & Create Policy")

    if submitted:
        if not name.strip():
            st.error("Please enter the worker's name.")
        else:
            lat, lon = city_coords.get(location, (20.0, 77.0))
            with st.spinner("Creating profile and policy…"):
                result = app.register(
                    name=name.strip(),
                    location=location,
                    lat=lat, lon=lon,
                    job_type=job_type,
                    weekly_income=weekly_income,
                    work_hours_per_day=work_hours,
                    work_days_per_week=work_days,
                    active_weeks=int(active_weeks),
                    missed_days_last_month=int(missed_days),
                )

            if not result["success"]:
                st.error(result["reason"])
            else:
                user   = result["user"]
                policy = result["policy"]
                premium = result["premium_data"]
                risk   = result["risk_data"]
                rel    = result["reliability_score"]

                st.success(f"✅ {name} registered successfully!")

                r1, r2, r3, r4 = st.columns(4)
                with r1: st.markdown(kpi("Worker ID", user["user_id"]), unsafe_allow_html=True)
                with r2: st.markdown(kpi("Policy ID", policy["policy_id"]), unsafe_allow_html=True)
                with r3: st.markdown(kpi("Weekly Premium", f"₹{policy['weekly_premium']:.0f}"), unsafe_allow_html=True)
                with r4: st.markdown(kpi("Coverage/Day", f"₹{policy['coverage_per_day']:.0f}"), unsafe_allow_html=True)

                st.markdown(f"""
                <div class="kpi-card" style="margin-top:1rem;">
                  <b>📊 Profile Summary</b>
                  <div class="pill-row" style="margin-top:.5rem;">
                    <div class="pill">Risk Score: <b>{risk['risk_score']:.0f}/100</b> ({risk['risk_level']})</div>
                    <div class="pill">Reliability: <b>{rel:.0f}/100</b></div>
                    <div class="pill">Risk Multiplier: <b>×{premium['risk_multiplier']}</b></div>
                    <div class="pill">Reliability Discount: <b>×{premium['reliability_discount']}</b></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 4 — Simulate Scenario
# ──────────────────────────────────────────────────────────────────────────────
elif page == "⚡  Simulate Scenario":
    st.markdown("## ⚡ Simulate Environmental Scenario")
    st.markdown("<span style='color:#8b949e;'>Simulate real-world triggers and watch the auto-claim system respond.</span>", unsafe_allow_html=True)
    st.markdown("---")

    workers = app.list_workers()
    if not workers:
        st.warning("No workers registered yet.")
        st.stop()

    worker_names = {f"{w['name']} ({w['user_id']})": w["user_id"] for w in workers}

    col1, col2 = st.columns([1.5, 1])
    with col1:
        selected_label = st.selectbox("Select Worker", list(worker_names.keys()))
        user_id = worker_names[selected_label]

    scenario_info = {
        "heavy_rain":        ("🌧️", "Heavy Rainfall",     "75 mm/hr rain — severe outdoor disruption"),
        "high_aqi":          ("😷", "High AQI",           "AQI 320 — hazardous air quality"),
        "flood_alert":       ("🌊", "Flood Alert",        "Active flood + 95 mm rain — extreme risk"),
        "traffic_disruption":("🚦", "Traffic Disruption", "85% traffic index — roads blocked"),
        "normal_day":        ("☀️", "Normal Day",         "Low-risk conditions — no claim expected"),
    }

    with col2:
        scenario_labels = {
            f"{v[0]} {v[1]}": k for k, v in scenario_info.items()
        }
        chosen_label = st.selectbox("Choose Scenario", list(scenario_labels.keys()))
        scenario_key = scenario_labels[chosen_label]

    # Show scenario description
    icon, name, desc = scenario_info[scenario_key]
    alert_box("orange" if scenario_key != "normal_day" else "green",
              f"<b>{icon} {name}</b> — {desc}")

    if st.button(f"▶️ Run Scenario: {name}"):
        with st.spinner(f"Simulating {name}…"):
            result = app.run_scenario(user_id, scenario_key)

        risk = result["risk_data"]
        claim = result.get("claim_result")
        pred  = result.get("prediction", {})

        st.markdown("---")
        st.markdown(f"### Results for **{name}**")

        # Risk metrics
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.markdown(kpi("Risk Score", f"{risk['risk_score']:.0f}/100", risk['risk_level']), unsafe_allow_html=True)
        with m2: st.markdown(kpi("Rainfall", f"{risk['rainfall_mm']} mm"), unsafe_allow_html=True)
        with m3: st.markdown(kpi("AQI", str(risk['aqi'])), unsafe_allow_html=True)
        with m4: st.markdown(kpi("Traffic", f"{risk['traffic_disruption']*100:.0f}%"), unsafe_allow_html=True)

        st.markdown(f"Risk Level: {risk_badge(risk['risk_level'])}", unsafe_allow_html=True)

        triggers = risk.get("active_triggers", [])
        if triggers:
            alert_box("red", "⚡ <b>Active Triggers:</b> " + " &nbsp;|&nbsp; ".join(triggers))

        # Claim result
        st.markdown("---")
        st.markdown("### 💳 Claim Processing Result")

        if claim is None:
            alert_box("green", "✅ <b>No claim triggered.</b> Risk score below threshold — worker can continue normally.")
        elif not claim.get("success"):
            alert_box("yellow", f"⚠️ Claim not processed: {claim.get('reason', 'Unknown reason')}")
        else:
            if claim["status"] == "approved":
                credit_banner(claim["message"])
            elif claim["status"] == "partial_approved":
                alert_box("orange", f"🟡 {claim['message']}")
            else:
                alert_box("red", f"🔴 {claim['message']}")

            detail_c1, detail_c2 = st.columns(2)
            with detail_c1:
                st.markdown(f"""
                <div class="kpi-card">
                  <b>Claim Details</b>
                  <div class="pill-row" style="margin-top:.5rem;">
                    <div class="pill">ID: <b>{claim['claim_id']}</b></div>
                    <div class="pill">Status: <b>{claim['status'].replace('_',' ').title()}</b></div>
                  </div>
                  <div class="pill-row">
                    <div class="pill">Est. Loss: <b>₹{claim['estimated_loss']:,.0f}</b></div>
                    <div class="pill">Payout: <b>₹{claim['payout']:,.0f}</b></div>
                    <div class="pill">Disruption: <b>{claim['disruption_hours']}h</b></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with detail_c2:
                st.markdown(f"""
                <div class="kpi-card">
                  <b>Fraud Detection</b>
                  <div class="pill-row" style="margin-top:.5rem;">
                    <div class="pill">Score: <b>{claim['fraud_score']:.3f}</b></div>
                    <div class="pill">{claim['fraud_label']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # Prediction
        if pred:
            st.markdown("---")
            st.markdown("### 🔮 Next-Day Prediction")
            trend_icon = "📈" if pred.get("trend") == "increasing" else "📉" if pred.get("trend") == "decreasing" else "➡️"
            alert_box(
                "orange" if pred.get("predicted_risk_score", 0) >= 55 else "green",
                f"{trend_icon} <b>Tomorrow's predicted risk: {pred.get('predicted_risk_score', 0):.0f}/100</b> — {pred.get('primary_message', '')}"
            )
            for action in pred.get("recommended_actions", []):
                st.markdown(f"- {action}")


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 5 — Claims History
# ──────────────────────────────────────────────────────────────────────────────
elif page == "📋  Claims History":
    st.markdown("## 📋 Claims History")
    st.markdown("---")

    from backend.database import get_all_claims, get_all_users
    all_claims = get_all_claims()
    all_users  = {u["user_id"]: u["name"] for u in get_all_users()}

    view_mode = st.radio("View", ["All Claims", "By Worker"], horizontal=True)

    if view_mode == "By Worker":
        workers = app.list_workers()
        if not workers:
            st.info("No workers registered.")
            st.stop()
        wmap = {f"{w['name']} ({w['user_id']})": w["user_id"] for w in workers}
        sel = st.selectbox("Select Worker", list(wmap.keys()))
        uid = wmap[sel]
        claims_to_show = [c for c in all_claims if c.get("user_id") == uid]
    else:
        claims_to_show = all_claims

    if not claims_to_show:
        st.info("No claims found.")
        st.stop()

    # Summary
    approved = sum(1 for c in claims_to_show if c.get("status") == "approved")
    total_paid = sum(c.get("payout_amount", 0) for c in claims_to_show if c.get("status") in ("approved", "partial_approved"))

    s1, s2, s3, s4 = st.columns(4)
    with s1: st.markdown(kpi("Total Claims", str(len(claims_to_show))), unsafe_allow_html=True)
    with s2: st.markdown(kpi("Approved", str(approved)), unsafe_allow_html=True)
    with s3: st.markdown(kpi("Total Paid Out", f"₹{total_paid:,.0f}"), unsafe_allow_html=True)
    with s4: st.markdown(kpi("Auto-Triggered", str(sum(1 for c in claims_to_show if c.get("auto_triggered")))), unsafe_allow_html=True)

    st.markdown("---")

    for claim in reversed(claims_to_show):
        worker_name = all_users.get(claim.get("user_id", ""), "Unknown")
        status_color = "green" if claim["status"] == "approved" else "orange" if claim["status"] == "partial_approved" else "red"

        with st.expander(f"🗂 {claim['claim_id']} — {worker_name} — {claim['trigger']} — ₹{claim.get('payout_amount',0):,.0f}", expanded=False):
            credit_banner(claim.get("message", "Claim processed"))
            st.markdown(f"""
            <div class="pill-row">
              <div class="pill">Worker: <b>{worker_name}</b></div>
              <div class="pill">Policy: <b>{claim.get('policy_id','—')}</b></div>
              <div class="pill">Risk Score: <b>{claim.get('risk_score_at_trigger', 0):.0f}</b></div>
              <div class="pill">Disruption: <b>{claim.get('disruption_hours', 0)}h</b></div>
              <div class="pill">Est. Loss: <b>₹{claim.get('estimated_loss', 0):,.0f}</b></div>
              <div class="pill">Payout: <b>₹{claim.get('payout_amount', 0):,.0f}</b></div>
              <div class="pill">Fraud Score: <b>{claim.get('fraud_score', 0):.3f}</b></div>
              <div class="pill">Status: <b>{claim['status'].replace('_',' ').title()}</b></div>
              <div class="pill">Date: <b>{claim.get('timestamp', '')[:10]}</b></div>
            </div>
            """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE 6 — Admin Panel
# ──────────────────────────────────────────────────────────────────────────────
elif page == "🗂️  Admin Panel":
    st.markdown("## 🗂️ Admin Panel — All Workers")
    st.markdown("---")

    overview = app.all_workers_overview()
    if not overview:
        st.info("No workers registered yet.")
        st.stop()

    stats = app.platform_stats()
    a1, a2, a3, a4 = st.columns(4)
    with a1: st.markdown(kpi("Workers", str(stats["total_workers"])), unsafe_allow_html=True)
    with a2: st.markdown(kpi("Active Policies", str(stats["active_policies"])), unsafe_allow_html=True)
    with a3: st.markdown(kpi("Claims", str(stats["total_claims"])), unsafe_allow_html=True)
    with a4: st.markdown(kpi("Disbursed", f"₹{stats['total_payout_disbursed']:,.0f}"), unsafe_allow_html=True)

    st.markdown("---")

    for w in overview:
        policy = w.get("policy") or {}
        with st.expander(f"👤 {w['name']} ({w['user_id']}) — {w['job_type']} — {w['location']}", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""
                <div class="pill-row">
                  <div class="pill">Income: <b>₹{w['weekly_income']:,}/wk</b></div>
                  <div class="pill">Hours: <b>{w['work_hours_per_day']}h/day</b></div>
                  <div class="pill">Days: <b>{w['work_days_per_week']}/wk</b></div>
                  <div class="pill">Active Since: <b>{w['registered_on']}</b></div>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                if policy:
                    st.markdown(f"""
                    <div class="pill-row">
                      <div class="pill">Policy: <b>{policy.get('policy_id','—')}</b></div>
                      <div class="pill">Premium: <b>₹{policy.get('weekly_premium',0):.0f}/wk</b></div>
                      <div class="pill">Cover/Day: <b>₹{policy.get('coverage_per_day',0):.0f}</b></div>
                      <div class="pill">Claims: <b>{w.get('total_claims',0)}</b></div>
                      <div class="pill">Paid Out: <b>₹{w.get('total_payout',0):,.0f}</b></div>
                    </div>
                    """, unsafe_allow_html=True)