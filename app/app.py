"""
app.py — Project FORESIGHT planning dashboard (D5).

Run:
    streamlit run app/app.py

Reads the pipeline/model outputs from data/processed/. If they don't exist
yet, it tells the user which scripts to run first instead of crashing.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
sys.path.insert(0, str(ROOT / "src"))

st.set_page_config(page_title="FORESIGHT — NorthBay Living Planning Dashboard", layout="wide")


@st.cache_data
def load_data():
    panel = pd.read_parquet(PROCESSED / "analysis_ready.parquet")
    forecast = pd.read_parquet(PROCESSED / "forecast_output.parquet")
    risk = pd.read_parquet(PROCESSED / "risk_scored.parquet")
    return panel, forecast, risk


required_files = ["analysis_ready.parquet", "forecast_output.parquet", "risk_scored.parquet"]
missing = [f for f in required_files if not (PROCESSED / f).exists()]
if missing:
    st.error(
        "Missing pipeline outputs: " + ", ".join(missing) +
        "\n\nRun these first from the project root:\n\n"
        "```\npython src/generate_data.py\npython src/pipeline.py\npython src/forecast.py\npython src/risk.py\n```"
    )
    st.stop()

panel, forecast, risk = load_data()

st.title("📦 FORESIGHT — Demand & Inventory Planning")
st.caption("NorthBay Living · Client Engagement · Data updated from the latest pipeline run")

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")
categories = ["All"] + sorted(risk["category"].dropna().unique().tolist())
sel_category = st.sidebar.selectbox("Category", categories)

quadrants = ["All"] + sorted(risk["quadrant"].unique().tolist())
sel_quadrant = st.sidebar.selectbox("Risk quadrant", quadrants)

sku_options = sorted(risk["sku_id"].unique().tolist())
sel_sku = st.sidebar.selectbox("SKU (for the detail view below)", ["(none)"] + sku_options)

filtered_risk = risk.copy()
if sel_category != "All":
    filtered_risk = filtered_risk[filtered_risk["category"] == sel_category]
if sel_quadrant != "All":
    filtered_risk = filtered_risk[filtered_risk["quadrant"] == sel_quadrant]

# ---------------- KPI row ----------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("SKUs in view", f"{filtered_risk['sku_id'].nunique():,}")
c2.metric("Reorder Now", f"{(filtered_risk['quadrant'] == 'Reorder Now').sum():,}")
c3.metric("Markdown / Clear", f"{(filtered_risk['quadrant'] == 'Markdown / Clear').sum():,}")
c4.metric("Total value at stake", f"₹{filtered_risk['value_at_stake_rupees'].sum():,.0f}")

st.divider()

# ---------------- Decisioning grid ----------------
left, right = st.columns([2, 1])
with left:
    st.subheader("Decisioning grid — stockout vs overstock risk")
    color_map = {
        "Reorder Now": "#E0575B", "Markdown / Clear": "#4C6EF5",
        "Watch / Volatile": "#F0A63A", "Healthy": "#22A06B",
    }
    fig = px.scatter(
        filtered_risk, x="overstock_risk", y="stockout_risk", color="quadrant",
        size="value_at_stake_rupees", size_max=40, hover_name="sku_id",
        hover_data={"category": True, "value_at_stake_rupees": ":,.0f",
                    "recommended_action": True, "overstock_risk": False, "stockout_risk": False},
        color_discrete_map=color_map,
    )
    fig.add_vline(x=0.5, line_dash="dash", line_color="gray")
    fig.add_hline(y=0.5, line_dash="dash", line_color="gray")
    fig.update_layout(xaxis_title="Overstock risk →", yaxis_title="Stockout risk →", height=480)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Risk mix")
    counts = filtered_risk["quadrant"].value_counts().reset_index()
    counts.columns = ["quadrant", "count"]
    fig2 = px.pie(counts, names="quadrant", values="count", color="quadrant",
                   color_discrete_map=color_map, hole=0.45)
    fig2.update_layout(height=480, showlegend=True)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---------------- Prioritised reorder / markdown list ----------------
st.subheader("Prioritised action list")
tab1, tab2, tab3 = st.tabs(["🔴 Reorder Now", "🔵 Markdown / Clear", "🟠 Watch / Volatile"])

display_cols = ["sku_id", "category", "avg_weekly_forecast", "on_hand_units", "weeks_of_cover",
                 "stockout_risk", "overstock_risk", "value_at_stake_rupees", "recommended_action"]

with tab1:
    sub = filtered_risk[filtered_risk["quadrant"] == "Reorder Now"].sort_values(
        "value_at_stake_rupees", ascending=False)
    if sub.empty:
        st.info("No SKUs currently need reordering in this view.")
    else:
        st.dataframe(sub[display_cols], use_container_width=True, hide_index=True)

with tab2:
    sub = filtered_risk[filtered_risk["quadrant"] == "Markdown / Clear"].sort_values(
        "value_at_stake_rupees", ascending=False)
    if sub.empty:
        st.info("No SKUs currently flagged for markdown in this view.")
    else:
        st.dataframe(sub[display_cols], use_container_width=True, hide_index=True)

with tab3:
    sub = filtered_risk[filtered_risk["quadrant"] == "Watch / Volatile"].sort_values(
        "value_at_stake_rupees", ascending=False)
    if sub.empty:
        st.info("No SKUs currently flagged as watch/volatile in this view.")
    else:
        st.dataframe(sub[display_cols], use_container_width=True, hide_index=True)

st.divider()

# ---------------- SKU detail: forecast vs actual ----------------
st.subheader("SKU detail — forecast vs actual demand")
if sel_sku == "(none)":
    st.info("Pick a SKU from the sidebar to see its forecast vs actual history.")
else:
    hist = panel[panel["sku_id"] == sel_sku].sort_values("week_start")
    fut = forecast[forecast["sku_id"] == sel_sku].sort_values("week_start")
    sku_risk = risk[risk["sku_id"] == sel_sku]

    if not sku_risk.empty:
        r = sku_risk.iloc[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Quadrant", r["quadrant"])
        m2.metric("Stockout risk", f"{r['stockout_risk']:.0%}")
        m3.metric("Overstock risk", f"{r['overstock_risk']:.0%}")
        m4.metric("Weeks of cover", f"{r['weeks_of_cover']:.1f}")
        st.caption(f"**Recommended action:** {r['recommended_action']}")

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=hist["week_start"], y=hist["units_sold"],
                                mode="lines", name="Actual demand", line=dict(color="#1F2937")))
    if not fut.empty:
        fig3.add_trace(go.Scatter(x=fut["week_start"], y=fut["model_forecast"],
                                    mode="lines", name="Forecast", line=dict(color="#4C3AE3")))
        fig3.add_trace(go.Scatter(
            x=pd.concat([fut["week_start"], fut["week_start"][::-1]]),
            y=pd.concat([fut["forecast_upper_80"], fut["forecast_lower_80"][::-1]]),
            fill="toself", fillcolor="rgba(76,58,227,0.15)", line=dict(color="rgba(0,0,0,0)"),
            name="80% interval", showlegend=True,
        ))
    fig3.update_layout(height=420, xaxis_title="Week", yaxis_title="Units")
    st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.caption(
    "FORESIGHT · Zidio Development · Data Science & Analytics engagement for NorthBay Living. "
    "Forecast: LightGBM, backtested with rolling-origin CV against a seasonal-naive baseline. "
    "Risk scoring: transparent rule-based (Section 08 of the engagement brief)."
)
