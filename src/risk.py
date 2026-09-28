"""
risk.py — Stockout / overstock risk scoring & decisioning (D4, Section 08).

Transparent, explainable rules (no black box):

  Stockout risk: compare forecast demand over the SKU's lead time against
  on-hand + on-order stock. If projected stock at the end of lead time falls
  below a safety buffer, the SKU is at risk of stocking out.

  Overstock risk: compare on-hand stock against forecast demand over a
  forward window (the full forecast horizon). If on-hand covers demand for
  far longer than a "healthy" number of weeks of cover, the SKU is
  overstocked.

  Each SKU gets a 0-1 risk score on each axis, a quadrant (Section 08.2),
  a recommended action, and a rupee value at stake.

Run standalone (after forecast.py has produced data/processed/forecast_output.parquet):
    python src/risk.py
Produces:
    data/processed/risk_scored.parquet / .csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

OVERSTOCK_WEEKS_COVER_THRESHOLD = 8  # holding > 8 weeks of forecast demand = overstocked
SAFETY_BUFFER_WEEKS = 1.0            # extra weeks of cover wanted beyond lead time


def load_inputs():
    forecast = pd.read_parquet(PROCESSED / "forecast_output.parquet")
    panel = pd.read_parquet(PROCESSED / "analysis_ready.parquet")
    return forecast, panel


def latest_inventory_position(panel: pd.DataFrame) -> pd.DataFrame:
    """Most recent known on-hand/on-order/lead-time/reorder-point per SKU."""
    inv = (
        panel.dropna(subset=["on_hand_units"])
        .sort_values(["sku_id", "week_start"])
        .groupby("sku_id")
        .tail(1)[["sku_id", "on_hand_units", "on_order_units", "lead_time_days",
                   "reorder_point", "unit_cost", "list_price"]]
    )
    return inv


def score_risk(forecast: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    inv = latest_inventory_position(panel)
    horizon_weeks = forecast["week_start"].nunique()

    agg = (
        forecast.groupby("sku_id")
        .agg(
            avg_weekly_forecast=("model_forecast", "mean"),
            total_horizon_forecast=("model_forecast", "sum"),
            category=("category", "first"),
            subcategory=("subcategory", "first"),
        )
        .reset_index()
    )
    df = agg.merge(inv, on="sku_id", how="left")
    df["lead_time_weeks"] = (df["lead_time_days"].fillna(14) / 7.0).clip(lower=0.5)
    df["available_stock"] = df["on_hand_units"].fillna(0) + df["on_order_units"].fillna(0)

    # --- Stockout risk ---
    df["demand_over_lead_time"] = df["avg_weekly_forecast"] * (df["lead_time_weeks"] + SAFETY_BUFFER_WEEKS)
    df["projected_shortfall"] = df["demand_over_lead_time"] - df["available_stock"]
    denom = df["demand_over_lead_time"].replace(0, np.nan)
    df["stockout_risk"] = (df["projected_shortfall"] / denom).clip(0, 1).fillna(0)

    # --- Overstock risk ---
    df["weeks_of_cover"] = df["on_hand_units"].fillna(0) / df["avg_weekly_forecast"].replace(0, np.nan)
    df["weeks_of_cover"] = df["weeks_of_cover"].fillna(999)
    df["overstock_risk"] = ((df["weeks_of_cover"] - OVERSTOCK_WEEKS_COVER_THRESHOLD)
                             / OVERSTOCK_WEEKS_COVER_THRESHOLD).clip(0, 1)

    # --- rupee value at stake ---
    df["sales_at_risk_rupees"] = (df["projected_shortfall"].clip(lower=0) * df["list_price"]).round(0)
    excess_units = (df["on_hand_units"].fillna(0)
                     - df["avg_weekly_forecast"] * OVERSTOCK_WEEKS_COVER_THRESHOLD).clip(lower=0)
    df["capital_locked_rupees"] = (excess_units * df["unit_cost"]).round(0)

    # --- quadrant + recommended action (Section 08.2) ---
    def quadrant(row):
        hi_stock = row["stockout_risk"] >= 0.5
        hi_over = row["overstock_risk"] >= 0.5
        if hi_stock and hi_over:
            return "Watch / Volatile"
        if hi_stock:
            return "Reorder Now"
        if hi_over:
            return "Markdown / Clear"
        return "Healthy"

    action_map = {
        "Reorder Now": "Raise a replenishment order before stock runs out.",
        "Markdown / Clear": "Promote or discount to free up capital.",
        "Watch / Volatile": "Investigate — demand is erratic; review manually.",
        "Healthy": "No action needed; leave as is.",
    }

    df["quadrant"] = df.apply(quadrant, axis=1)
    df["recommended_action"] = df["quadrant"].map(action_map)
    df["value_at_stake_rupees"] = np.where(
        df["quadrant"] == "Markdown / Clear", df["capital_locked_rupees"],
        np.where(df["quadrant"].isin(["Reorder Now", "Watch / Volatile"]),
                 df["sales_at_risk_rupees"], 0)
    )

    cols = ["sku_id", "category", "subcategory", "avg_weekly_forecast", "total_horizon_forecast",
            "on_hand_units", "on_order_units", "lead_time_days", "weeks_of_cover",
            "stockout_risk", "overstock_risk", "quadrant", "recommended_action",
            "sales_at_risk_rupees", "capital_locked_rupees", "value_at_stake_rupees"]
    return df[cols].sort_values("value_at_stake_rupees", ascending=False).reset_index(drop=True)


def main():
    forecast, panel = load_inputs()
    scored = score_risk(forecast, panel)
    scored.to_parquet(PROCESSED / "risk_scored.parquet", index=False)
    scored.to_csv(PROCESSED / "risk_scored.csv", index=False)

    print(f"Risk-scored {len(scored)} SKUs")
    print(scored["quadrant"].value_counts())
    print(f"\nTotal sales at risk (stockouts): Rs {scored['sales_at_risk_rupees'].sum():,.0f}")
    print(f"Total capital locked (overstock): Rs {scored['capital_locked_rupees'].sum():,.0f}")
    print("\nTop 5 by value at stake:")
    print(scored.head(5)[["sku_id", "quadrant", "value_at_stake_rupees", "recommended_action"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
