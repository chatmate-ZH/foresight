"""
generate_data.py — Synthetic data generator for Project FORESIGHT (NorthBay Living).

Produces four raw extracts matching the brief's data dictionary (Appendix A):
  data/raw/sales_daily.csv
  data/raw/sku_master.csv
  data/raw/calendar.csv
  data/raw/inventory_snapshots.csv

The data is DELIBERATELY imperfect (missing values, duplicates, inconsistent
category labels, a few negative/garbage rows) because cleaning it is part of
the engagement, per the brief: "generating it is not your job... spend it
cleaning, understanding, and modelling the data you are given."

Usage:
    python src/generate_data.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = pd.Timestamp("2024-01-01")
END_DATE = pd.Timestamp("2025-12-31")  # 2 years of daily history
DATES = pd.date_range(START_DATE, END_DATE, freq="D")

CATEGORIES = {
    "Furniture": ["Sofas", "Chairs", "Tables", "Storage"],
    "Decor": ["Wall Art", "Rugs", "Cushions", "Candles"],
    "Lighting": ["Table Lamps", "Floor Lamps", "Pendant Lights"],
    "Small Appliances": ["Kettles", "Toasters", "Blenders", "Air Purifiers"],
    "Bed & Bath": ["Bedding", "Towels", "Bath Accessories"],
}

# Inconsistent label variants injected later to simulate messy category text
CATEGORY_LABEL_VARIANTS = {
    "Furniture": ["Furniture", "furniture", "FURNITURE "],
    "Decor": ["Decor", "Décor", "decor"],
    "Lighting": ["Lighting", "lighting", "LIGHTING"],
    "Small Appliances": ["Small Appliances", "Small appliances", "SMALL APPLIANCES"],
    "Bed & Bath": ["Bed & Bath", "Bed and Bath", "bed & bath"],
}

N_SKUS = 200


def build_sku_master():
    rows = []
    cats = list(CATEGORIES.keys())
    weights = [0.22, 0.28, 0.15, 0.20, 0.15]
    for i in range(1, N_SKUS + 1):
        sku_id = f"NB-{i:04d}"
        cat = RNG.choice(cats, p=weights)
        subcat = RNG.choice(CATEGORIES[cat])
        launch_date = pd.Timestamp("2022-01-01") + pd.Timedelta(
            days=int(RNG.integers(0, (END_DATE - pd.Timestamp("2022-01-01")).days - 30))
        )
        # ~12% of SKUs are "new" launches within the last 90 days of history — sparse history case
        if RNG.random() < 0.12:
            launch_date = END_DATE - pd.Timedelta(days=int(RNG.integers(15, 90)))
        unit_cost = round(float(RNG.uniform(150, 4000)), 2)
        margin_mult = RNG.uniform(1.6, 2.6)
        list_price = round(unit_cost * margin_mult, 2)
        rows.append(
            dict(
                sku_id=sku_id,
                category=cat,
                subcategory=subcat,
                launch_date=launch_date.date().isoformat(),
                unit_cost=unit_cost,
                list_price=list_price,
            )
        )
    df = pd.DataFrame(rows)

    # --- inject messiness: inconsistent category label casing/variants ---
    def messy_cat(cat):
        variants = CATEGORY_LABEL_VARIANTS[str(cat)]
        idx = RNG.choice(len(variants), p=[0.7, 0.2, 0.1])
        return variants[idx]

    mask = RNG.random(len(df)) < 0.35
    df.loc[mask, "category"] = [messy_cat(c) for c in df.loc[mask, "category"]]

    # --- inject a handful of duplicate SKU rows (data extract glitch) ---
    dupe_idx = RNG.choice(df.index, size=5, replace=False)
    df = pd.concat([df, df.loc[dupe_idx]], ignore_index=True)

    # --- inject a few missing unit_cost values ---
    miss_idx = RNG.choice(df.index, size=6, replace=False)
    df.loc[miss_idx, "unit_cost"] = np.nan

    return df.sample(frac=1, random_state=1).reset_index(drop=True)


def build_calendar():
    rows = []
    # simple US-ish holiday list + brand promo calendar
    holidays = {
        "2024-01-01", "2024-02-14", "2024-05-27", "2024-07-04", "2024-11-28",
        "2024-11-29", "2024-12-25", "2025-01-01", "2025-02-14", "2025-05-26",
        "2025-07-04", "2025-11-27", "2025-11-28", "2025-12-25",
    }
    promo_windows = [
        ("2024-01-02", "2024-01-08", "New Year Clearance"),
        ("2024-03-15", "2024-03-22", "Spring Refresh"),
        ("2024-07-01", "2024-07-10", "Summer Sale"),
        ("2024-11-25", "2024-12-02", "Black Friday / Cyber Monday"),
        ("2025-01-02", "2025-01-08", "New Year Clearance"),
        ("2025-03-14", "2025-03-21", "Spring Refresh"),
        ("2025-07-01", "2025-07-10", "Summer Sale"),
        ("2025-11-24", "2025-12-01", "Black Friday / Cyber Monday"),
    ]
    promo_map = {}
    for start, end, name in promo_windows:
        for d in pd.date_range(start, end):
            promo_map[d.date().isoformat()] = name

    for d in DATES:
        iso = d.date().isoformat()
        rows.append(
            dict(
                date=iso,
                week=int(d.isocalendar().week),
                month=d.month,
                season={12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring",
                        5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer",
                        9: "Fall", 10: "Fall", 11: "Fall"}[d.month],
                is_holiday=1 if iso in holidays else 0,
                promo_event=promo_map.get(iso, ""),
            )
        )
    return pd.DataFrame(rows)


def simulate_sales(sku_row, calendar_df):
    """Simulate a daily demand series for one SKU with trend, weekly & annual
    seasonality, promo lift, and noise; zero out days before launch."""
    sku_id = sku_row["sku_id"]
    launch = pd.Timestamp(sku_row["launch_date"])
    base_level = RNG.uniform(0.4, 6.0)  # base units/day, varies hugely by SKU popularity
    trend_per_year = RNG.uniform(-0.15, 0.35)  # mild growth/decline
    weekly_pattern = RNG.uniform(0.8, 1.3, size=7)  # Mon..Sun multipliers
    weekly_pattern = weekly_pattern / weekly_pattern.mean()
    annual_amp = RNG.uniform(0.1, 0.5)

    rows = []
    for i, d in enumerate(calendar_df["date"]):
        dt = pd.Timestamp(d)
        if dt < launch:
            continue
        days_since_launch = (dt - launch).days
        trend = 1 + trend_per_year * (days_since_launch / 365.0)
        annual = 1 + annual_amp * np.sin(2 * np.pi * (dt.dayofyear / 365.0) + RNG.uniform(0, 1))
        weekday_mult = weekly_pattern[dt.weekday()]
        promo_row = calendar_df.iloc[i]
        promo_flag = 1 if promo_row["promo_event"] else 0
        promo_lift = 1.9 if promo_flag else 1.0
        holiday_lift = 1.25 if promo_row["is_holiday"] else 1.0

        lam = max(base_level * trend * annual * weekday_mult * promo_lift * holiday_lift, 0.01)
        units = RNG.poisson(lam)
        rows.append((d, sku_id, units, promo_flag))
    return rows


def build_sales_and_inventory(sku_df, calendar_df):
    sales_rows = []
    for _, sku_row in sku_df.drop_duplicates("sku_id").iterrows():
        sales_rows.extend(simulate_sales(sku_row, calendar_df))

    sales = pd.DataFrame(sales_rows, columns=["date", "sku_id", "units_sold", "promo_flag"])
    price_lookup = sku_df.drop_duplicates("sku_id").set_index("sku_id")["list_price"].to_dict()

    def day_price(row):
        base = price_lookup.get(row["sku_id"], np.nan)
        if pd.isna(base):
            return np.nan
        discount = RNG.uniform(0.75, 0.9) if row["promo_flag"] else 1.0
        noise = RNG.uniform(0.98, 1.02)
        return round(base * discount * noise, 2)

    sales["unit_price"] = sales.apply(day_price, axis=1)
    sales["revenue"] = (sales["units_sold"] * sales["unit_price"]).round(2)

    # --- inject messiness into sales_daily ---
    # 1) missing unit_price on a small % of rows
    miss_idx = sales.sample(frac=0.01, random_state=2).index
    sales.loc[miss_idx, "unit_price"] = np.nan
    sales.loc[miss_idx, "revenue"] = np.nan
    # 2) a few duplicate rows (same sku+date appearing twice — extract glitch)
    dupe_idx = sales.sample(n=40, random_state=3).index
    sales = pd.concat([sales, sales.loc[dupe_idx]], ignore_index=True)
    # 3) a few negative/garbage units_sold (data entry errors)
    err_idx = sales.sample(n=15, random_state=4).index
    sales.loc[err_idx, "units_sold"] = -sales.loc[err_idx, "units_sold"].abs()

    # --- Inventory snapshots (weekly, per SKU) ---
    inv_rows = []
    weekly_dates = pd.date_range(START_DATE, END_DATE, freq="W-MON")
    daily_mean = sales.groupby("sku_id")["units_sold"].mean().clip(lower=0.1)
    for sku_id, sku_row in sku_df.drop_duplicates("sku_id").set_index("sku_id").iterrows():
        avg_daily = daily_mean.get(sku_id, 0.5)
        lead_time = int(RNG.choice([7, 14, 21, 30], p=[0.35, 0.35, 0.2, 0.1]))
        reorder_point = round(avg_daily * lead_time * RNG.uniform(1.1, 1.5), 1)
        on_hand = max(RNG.normal(avg_daily * lead_time * RNG.uniform(0.8, 2.5), avg_daily * 3), 0)
        for wd in weekly_dates:
            if wd < pd.Timestamp(sku_row["launch_date"]):
                continue
            # random walk on hand stock, roughly mean-reverting around a target
            demand_est = avg_daily * 7 * RNG.uniform(0.6, 1.4)
            on_hand = max(on_hand - demand_est + (reorder_point if RNG.random() < 0.18 else 0), 0)
            on_order = round(max(RNG.normal(avg_daily * lead_time * 0.5, avg_daily * 2), 0), 0)
            inv_rows.append(
                dict(
                    date=wd.date().isoformat(),
                    sku_id=sku_id,
                    on_hand_units=round(on_hand, 0),
                    on_order_units=on_order,
                    lead_time_days=lead_time,
                    reorder_point=reorder_point,
                )
            )
    inventory = pd.DataFrame(inv_rows)

    # inject a little inventory messiness: a few missing on_order values, one duplicate snapshot
    miss_idx = inventory.sample(frac=0.01, random_state=5).index
    inventory.loc[miss_idx, "on_order_units"] = np.nan
    dupe_idx = inventory.sample(n=10, random_state=6).index
    inventory = pd.concat([inventory, inventory.loc[dupe_idx]], ignore_index=True)

    return sales, inventory


def main():
    print("Building sku_master...")
    sku_df = build_sku_master()
    print("Building calendar...")
    calendar_df = build_calendar()
    print("Simulating sales_daily and inventory_snapshots (this takes a bit)...")
    sales_df, inventory_df = build_sales_and_inventory(sku_df, calendar_df)

    sku_df.to_csv(RAW_DIR / "sku_master.csv", index=False)
    calendar_df.to_csv(RAW_DIR / "calendar.csv", index=False)
    sales_df.to_csv(RAW_DIR / "sales_daily.csv", index=False)
    inventory_df.to_csv(RAW_DIR / "inventory_snapshots.csv", index=False)

    print(f"sku_master: {sku_df.shape}")
    print(f"calendar: {calendar_df.shape}")
    print(f"sales_daily: {sales_df.shape}")
    print(f"inventory_snapshots: {inventory_df.shape}")
    print("Done. Raw extracts written to", RAW_DIR)


if __name__ == "__main__":
    main()
