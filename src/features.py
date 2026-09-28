"""
features.py — Feature engineering for the FORESIGHT demand model.

All features are computed strictly from information available at or before
the week being featurized (shift-based lags/rolling windows), so nothing
here can leak future information into training. This is enforced by never
using .rolling()/.shift() with negative offsets and by sorting on
(sku_id, week_start) before any groupby-transform.
"""
import numpy as np
import pandas as pd

LAGS = [1, 2, 3, 4, 8, 52]
ROLLING_WINDOWS = [4, 8, 12]


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["iso_week"] = df["week_start"].dt.isocalendar().week.astype(int)
    df["month"] = df["week_start"].dt.month
    df["weekofyear_sin"] = np.sin(2 * np.pi * df["iso_week"] / 52)
    df["weekofyear_cos"] = np.cos(2 * np.pi * df["iso_week"] / 52)
    df["weeks_since_launch"] = (
        (df["week_start"] - df["launch_date"]).dt.days // 7
    ).clip(lower=0)
    return df


def add_lag_and_rolling_features(df: pd.DataFrame, target="units_sold") -> pd.DataFrame:
    df = df.sort_values(["sku_id", "week_start"]).copy()
    g = df.groupby("sku_id")[target]

    for lag in LAGS:
        df[f"lag_{lag}"] = g.shift(lag)

    for w in ROLLING_WINDOWS:
        # shift(1) first so the current week's own value never enters its own window
        shifted = df.groupby("sku_id")[target].shift(1)
        df[f"roll_mean_{w}"] = shifted.groupby(df["sku_id"]).transform(
            lambda s: s.rolling(w, min_periods=1).mean()
        )
        df[f"roll_std_{w}"] = shifted.groupby(df["sku_id"]).transform(
            lambda s: s.rolling(w, min_periods=2).std()
        )

    df["promo_flag_lag1"] = df.groupby("sku_id")["promo_flag"].shift(1)
    df["price_lag1"] = df.groupby("sku_id")["avg_price"].shift(1)

    # category-level rolling demand (helps sparse-history / new SKUs)
    cat_weekly = (
        df.groupby(["category", "week_start"])[target].sum().reset_index()
        .rename(columns={target: "cat_units_sold"})
    )
    cat_weekly = cat_weekly.sort_values(["category", "week_start"])
    cat_weekly["cat_roll_mean_8"] = cat_weekly.groupby("category")["cat_units_sold"].transform(
        lambda s: s.shift(1).rolling(8, min_periods=1).mean()
    )
    df = df.merge(cat_weekly[["category", "week_start", "cat_roll_mean_8"]],
                   on=["category", "week_start"], how="left")

    return df


def add_seasonal_naive_baseline(df: pd.DataFrame, target="units_sold") -> pd.DataFrame:
    """Baseline: demand from the same ISO week last year (lag 52); falls back
    to lag_4 (last month) for SKUs without a year of history, then to the
    SKU's expanding mean."""
    df = df.copy()
    expanding_mean = (
        df.sort_values(["sku_id", "week_start"])
        .groupby("sku_id")[target]
        .apply(lambda s: s.shift(1).expanding().mean())
        .reset_index(level=0, drop=True)
    )
    df["baseline_forecast"] = df["lag_52"].fillna(df["lag_4"]).fillna(expanding_mean).fillna(0)
    return df


FEATURE_COLUMNS = (
    [f"lag_{l}" for l in LAGS]
    + [f"roll_mean_{w}" for w in ROLLING_WINDOWS]
    + [f"roll_std_{w}" for w in ROLLING_WINDOWS]
    + ["promo_flag_lag1", "price_lag1", "cat_roll_mean_8",
       "weekofyear_sin", "weekofyear_cos", "weeks_since_launch",
       "promo_flag", "unit_cost", "list_price"]
)
CATEGORICAL_COLUMNS = ["category", "subcategory"]


def build_feature_frame(panel: pd.DataFrame) -> pd.DataFrame:
    df = add_time_features(panel)
    df = add_lag_and_rolling_features(df)
    df = add_seasonal_naive_baseline(df)
    for c in CATEGORICAL_COLUMNS:
        df[c] = df[c].astype("category")
    return df
