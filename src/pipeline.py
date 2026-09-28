"""
pipeline.py — Project FORESIGHT data pipeline (D1).

Ingests the four raw extracts, validates and cleans them, and produces one
analysis-ready weekly SKU-level dataset. Every cleaning decision is logged so
the data-quality report (D2) can be generated from real numbers, not guesses.

Run standalone:
    python src/pipeline.py
Produces:
    data/processed/analysis_ready.parquet
    data/processed/analysis_ready.csv
    reports/data_quality_log.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
PROCESSED.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

CATEGORY_CANONICAL = {
    "furniture": "Furniture", "furniture ": "Furniture",
    "decor": "Decor", "décor": "Decor",
    "lighting": "Lighting",
    "small appliances": "Small Appliances",
    "bed & bath": "Bed & Bath", "bed and bath": "Bed & Bath",
}


def _canon_category(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().map(CATEGORY_CANONICAL).fillna(s)


class DQLog:
    """Small structured logger for cleaning decisions -> feeds the D2 memo."""

    def __init__(self):
        self.entries = []

    def log(self, table, issue, action, n_rows):
        self.entries.append(
            dict(table=table, issue=issue, action=action, rows_affected=int(n_rows))
        )

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.entries, f, indent=2)


def ingest():
    sku = pd.read_csv(RAW / "sku_master.csv")
    calendar = pd.read_csv(RAW / "calendar.csv", parse_dates=["date"])
    sales = pd.read_csv(RAW / "sales_daily.csv", parse_dates=["date"])
    inventory = pd.read_csv(RAW / "inventory_snapshots.csv", parse_dates=["date"])
    return sku, calendar, sales, inventory


def clean_sku_master(sku: pd.DataFrame, log: DQLog) -> pd.DataFrame:
    df = sku.copy()

    n_dupe = df.duplicated(subset=["sku_id"]).sum()
    df = df.drop_duplicates(subset=["sku_id"], keep="first")
    log.log("sku_master", "duplicate sku_id rows", "kept first occurrence, dropped rest", n_dupe)

    before = df["category"].nunique()
    df["category"] = _canon_category(df["category"])
    after = df["category"].nunique()
    log.log(
        "sku_master",
        f"inconsistent category labels ({before} raw variants)",
        f"canonicalised via lookup map to {after} categories",
        (sku["category"].astype(str).str.strip().str.lower().map(CATEGORY_CANONICAL).notna()).sum(),
    )

    n_missing_cost = df["unit_cost"].isna().sum()
    df["unit_cost"] = df.groupby("category")["unit_cost"].transform(
        lambda s: s.fillna(s.median())
    )
    log.log("sku_master", "missing unit_cost", "imputed with category median", n_missing_cost)

    df["launch_date"] = pd.to_datetime(df["launch_date"])
    return df


def clean_sales(sales: pd.DataFrame, valid_skus: set, log: DQLog) -> pd.DataFrame:
    df = sales.copy()

    n_dupe = df.duplicated(subset=["date", "sku_id"]).sum()
    df = df.drop_duplicates(subset=["date", "sku_id"], keep="first")
    log.log("sales_daily", "duplicate (date, sku_id) rows", "kept first occurrence, dropped rest", n_dupe)

    n_negative = (df["units_sold"] < 0).sum()
    df.loc[df["units_sold"] < 0, "units_sold"] = df.loc[df["units_sold"] < 0, "units_sold"].abs()
    log.log("sales_daily", "negative units_sold (data-entry error)", "took absolute value", n_negative)

    n_missing_price = df["unit_price"].isna().sum()
    df["unit_price"] = df.groupby("sku_id")["unit_price"].transform(
        lambda s: s.fillna(s.median())
    )
    df["unit_price"] = df["unit_price"].fillna(df["unit_price"].median())
    log.log("sales_daily", "missing unit_price", "imputed with SKU median (fallback: global median)", n_missing_price)

    n_missing_rev = df["revenue"].isna().sum()
    df["revenue"] = df["units_sold"] * df["unit_price"]
    log.log("sales_daily", "missing/inconsistent revenue", "recomputed as units_sold * unit_price", n_missing_rev)

    n_orphan = (~df["sku_id"].isin(valid_skus)).sum()
    df = df[df["sku_id"].isin(valid_skus)]
    log.log("sales_daily", "sales rows for unknown sku_id (orphaned FK)", "dropped", n_orphan)

    df["promo_flag"] = df["promo_flag"].fillna(0).astype(int)
    return df


def clean_inventory(inv: pd.DataFrame, valid_skus: set, log: DQLog) -> pd.DataFrame:
    df = inv.copy()

    n_dupe = df.duplicated(subset=["date", "sku_id"]).sum()
    df = df.drop_duplicates(subset=["date", "sku_id"], keep="first")
    log.log("inventory_snapshots", "duplicate (date, sku_id) snapshots", "kept first occurrence, dropped rest", n_dupe)

    n_missing_order = df["on_order_units"].isna().sum()
    df["on_order_units"] = df["on_order_units"].fillna(0)
    log.log("inventory_snapshots", "missing on_order_units", "filled with 0 (assume nothing on order)", n_missing_order)

    n_orphan = (~df["sku_id"].isin(valid_skus)).sum()
    df = df[df["sku_id"].isin(valid_skus)]
    log.log("inventory_snapshots", "inventory rows for unknown sku_id", "dropped", n_orphan)

    df["on_hand_units"] = df["on_hand_units"].clip(lower=0)
    return df


def build_weekly_panel(sales: pd.DataFrame, sku: pd.DataFrame, calendar: pd.DataFrame,
                        inventory: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to a weekly SKU-level panel: the analysis-ready dataset."""
    sales = sales.merge(calendar[["date", "week", "month", "season", "is_holiday", "promo_event"]],
                         on="date", how="left")
    sales["iso_year"] = sales["date"].dt.isocalendar().year
    sales["iso_week"] = sales["date"].dt.isocalendar().week
    sales["week_start"] = sales["date"] - pd.to_timedelta(sales["date"].dt.weekday, unit="D")

    weekly = (
        sales.groupby(["sku_id", "week_start"])
        .agg(
            units_sold=("units_sold", "sum"),
            revenue=("revenue", "sum"),
            avg_price=("unit_price", "mean"),
            promo_days=("promo_flag", "sum"),
            holiday_days=("is_holiday", "sum"),
        )
        .reset_index()
    )
    weekly["promo_flag"] = (weekly["promo_days"] > 0).astype(int)

    # attach SKU attributes
    weekly = weekly.merge(sku[["sku_id", "category", "subcategory", "unit_cost", "list_price", "launch_date"]],
                           on="sku_id", how="left")

    # attach nearest inventory snapshot on/before each week_start
    inv_sorted = inventory.sort_values("date")
    weekly_sorted = weekly.sort_values("week_start")
    merged = pd.merge_asof(
        weekly_sorted, inv_sorted.rename(columns={"date": "inv_date"}),
        left_on="week_start", right_on="inv_date", by="sku_id", direction="backward",
        tolerance=pd.Timedelta(days=21),
    )
    merged = merged.drop(columns=["promo_days"])
    merged = merged.sort_values(["sku_id", "week_start"]).reset_index(drop=True)
    return merged


def run(save=True):
    log = DQLog()
    sku, calendar, sales, inventory = ingest()

    sku_clean = clean_sku_master(sku, log)
    valid_skus = set(sku_clean["sku_id"])
    sales_clean = clean_sales(sales, valid_skus, log)
    inv_clean = clean_inventory(inventory, valid_skus, log)

    panel = build_weekly_panel(sales_clean, sku_clean, calendar, inv_clean)

    if save:
        panel.to_parquet(PROCESSED / "analysis_ready.parquet", index=False)
        panel.to_csv(PROCESSED / "analysis_ready.csv", index=False)
        log.save(REPORTS / "data_quality_log.json")

    return panel, log, dict(sku=sku_clean, sales=sales_clean, inventory=inv_clean, calendar=calendar)


if __name__ == "__main__":
    panel, log, tables = run()
    print(f"Analysis-ready panel: {panel.shape[0]:,} rows x {panel.shape[1]} cols")
    print(f"SKUs: {panel['sku_id'].nunique()}  |  Weeks: {panel['week_start'].nunique()}")
    print(f"Cleaning actions logged: {len(log.entries)} -> reports/data_quality_log.json")
    for e in log.entries:
        print(f"  [{e['table']}] {e['issue']}: {e['action']} ({e['rows_affected']} rows)")
