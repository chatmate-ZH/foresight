"""
eda.py — Exploratory analysis for the D2 insight memo.

Computes real numbers (not fabricated) from the cleaned analysis-ready panel:
demand distribution, top movers, dead stock, seasonality, category patterns,
and promo lift. Saves charts to reports/figures/ and a stats JSON that the
memo is written from.

Run standalone:
    python src/eda.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pipeline import run as run_pipeline

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"figure.dpi": 120, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def compute_stats(panel: pd.DataFrame) -> dict:
    stats = {}
    stats["n_skus"] = int(panel["sku_id"].nunique())
    stats["n_weeks"] = int(panel["week_start"].nunique())
    stats["date_range"] = [str(panel["week_start"].min().date()), str(panel["week_start"].max().date())]
    stats["total_units_sold"] = int(panel["units_sold"].sum())
    stats["total_revenue"] = float(panel["revenue"].sum())

    by_sku = panel.groupby("sku_id")["units_sold"].sum().sort_values(ascending=False)
    stats["top_5_skus"] = by_sku.head(5).to_dict()
    stats["bottom_5_skus"] = by_sku.tail(5).to_dict()

    # dead stock: SKUs with >8 weeks of history and zero sales in the last 8 weeks
    last_week = panel["week_start"].max()
    recent_cutoff = last_week - pd.Timedelta(weeks=8)
    recent_sales = panel[panel["week_start"] > recent_cutoff].groupby("sku_id")["units_sold"].sum()
    has_history = panel.groupby("sku_id")["week_start"].nunique()
    dead_skus = recent_sales[recent_sales == 0].index
    dead_skus = [s for s in dead_skus if has_history.get(s, 0) > 8]
    stats["dead_stock_sku_count"] = len(dead_skus)
    stats["dead_stock_skus"] = list(dead_skus[:15])

    by_cat = panel.groupby("category")["units_sold"].sum().sort_values(ascending=False)
    stats["units_by_category"] = by_cat.to_dict()

    promo_lift = panel.groupby("promo_flag")["units_sold"].mean()
    if 1 in promo_lift.index and 0 in promo_lift.index and promo_lift[0] > 0:
        stats["promo_lift_pct"] = round(100 * (promo_lift[1] / promo_lift[0] - 1), 1)
    else:
        stats["promo_lift_pct"] = None

    weekly_total = panel.groupby("week_start")["units_sold"].sum()
    stats["demand_cv"] = round(float(weekly_total.std() / weekly_total.mean()), 3)
    stats["peak_week"] = str(weekly_total.idxmax().date())
    stats["trough_week"] = str(weekly_total.idxmin().date())

    # concentration: revenue share of top 20% of SKUs (Pareto check)
    rev_by_sku = panel.groupby("sku_id")["revenue"].sum().sort_values(ascending=False)
    top20_n = max(1, int(0.2 * len(rev_by_sku)))
    stats["top20pct_revenue_share"] = round(float(rev_by_sku.head(top20_n).sum() / rev_by_sku.sum() * 100), 1)

    return stats


def make_charts(panel: pd.DataFrame):
    # 1. Weekly total demand trend with seasonality
    weekly = panel.groupby("week_start")["units_sold"].sum()
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(weekly.index, weekly.values, color="#4C3AE3", linewidth=1.5)
    ax.set_title("Total weekly demand across all SKUs")
    ax.set_ylabel("Units sold / week")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "weekly_demand_trend.png")
    plt.close(fig)

    # 2. Demand by category
    by_cat = panel.groupby("category")["units_sold"].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(by_cat.index, by_cat.values, color="#4C3AE3")
    ax.set_title("Total units sold by category")
    ax.set_xlabel("Units sold")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "demand_by_category.png")
    plt.close(fig)

    # 3. Top 10 movers
    top10 = panel.groupby("sku_id")["units_sold"].sum().sort_values(ascending=False).head(10)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(top10.index[::-1], top10.values[::-1], color="#22A06B")
    ax.set_title("Top 10 best-selling SKUs (2-year total units)")
    ax.set_xlabel("Units sold")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "top10_skus.png")
    plt.close(fig)

    # 4. Promo lift
    promo_avg = panel.groupby("promo_flag")["units_sold"].mean()
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.bar(["No promo", "Promo week"], [promo_avg.get(0, 0), promo_avg.get(1, 0)],
           color=["#94A3B8", "#E0575B"])
    ax.set_title("Avg weekly units: promo vs non-promo")
    ax.set_ylabel("Avg units sold / SKU-week")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "promo_lift.png")
    plt.close(fig)

    # 5. Revenue concentration (Pareto)
    rev_by_sku = panel.groupby("sku_id")["revenue"].sum().sort_values(ascending=False).reset_index(drop=True)
    cum_share = rev_by_sku.cumsum() / rev_by_sku.sum() * 100
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(np.arange(1, len(cum_share) + 1) / len(cum_share) * 100, cum_share.values,
             color="#4C3AE3", linewidth=2)
    ax.axhline(80, color="#94A3B8", linestyle="--", linewidth=1)
    ax.set_title("Revenue concentration across SKUs")
    ax.set_xlabel("% of SKUs (ranked by revenue)")
    ax.set_ylabel("Cumulative % of revenue")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "revenue_concentration.png")
    plt.close(fig)


def main():
    panel, log, _ = run_pipeline(save=True)
    stats = compute_stats(panel)
    make_charts(panel)

    with open(ROOT / "reports" / "eda_stats.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)

    print("EDA stats:")
    print(json.dumps(stats, indent=2, default=str))
    print(f"\nCharts saved to {FIG_DIR}")


if __name__ == "__main__":
    main()
