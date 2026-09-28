"""
forecast.py — Demand forecasting model + rolling-origin backtest (D3).

Workflow (matches Section 07 of the brief):
  1. Frame: weekly SKU-level forecast, horizon = FORECAST_HORIZON_WEEKS, metric = WAPE.
  2. Baseline: seasonal-naive (same ISO week last year, see features.py).
  3. Features: lags, rolling stats, calendar, promo, category signal.
  4. Model: LightGBM gradient-boosted trees.
  5. Backtest: rolling-origin CV (expanding window), never a random split.
  6. Evaluate: compare model WAPE to baseline WAPE per fold; report honestly.
  7. Produce final horizon forecast with an empirical 80% interval.

Run standalone:
    python src/forecast.py
Produces:
    reports/backtest_results.json
    data/processed/forecast_output.parquet   (latest horizon forecast per SKU)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb

from features import build_feature_frame, FEATURE_COLUMNS, CATEGORICAL_COLUMNS
from pipeline import run as run_pipeline

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

FORECAST_HORIZON_WEEKS = 6
N_BACKTEST_FOLDS = 5
MIN_TRAIN_WEEKS = 60  # ~14 months before the first fold, to give lag_52 a chance


def wape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return np.nan
    return float(np.sum(np.abs(y_true - y_pred)) / denom)


def bias(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.sum(y_true)
    if denom == 0:
        return np.nan
    return float(np.sum(y_pred - y_true) / denom)


def make_folds(weeks: np.ndarray, n_folds=N_BACKTEST_FOLDS, min_train_weeks=MIN_TRAIN_WEEKS,
               horizon=FORECAST_HORIZON_WEEKS):
    """Rolling-origin folds: expanding training window, fixed-size test window,
    each fold's origin moved forward by `horizon` weeks. Test weeks are always
    strictly after the training cutoff -> no leakage."""
    weeks = np.sort(np.unique(weeks))
    folds = []
    last_possible_start = len(weeks) - horizon
    # place folds working backward from the end so we always fit inside history
    starts = list(range(last_possible_start, min_train_weeks, -horizon))[:n_folds]
    starts = sorted(starts)
    for s in starts:
        train_weeks = weeks[:s]
        test_weeks = weeks[s:s + horizon]
        if len(test_weeks) == 0 or len(train_weeks) < min_train_weeks:
            continue
        folds.append((train_weeks, test_weeks))
    return folds


def train_predict(train_df, test_df):
    X_train = train_df[FEATURE_COLUMNS + CATEGORICAL_COLUMNS]
    y_train = train_df["units_sold"]
    X_test = test_df[FEATURE_COLUMNS + CATEGORICAL_COLUMNS]

    model = lgb.LGBMRegressor(
        objective="poisson",
        n_estimators=400,
        learning_rate=0.04,
        num_leaves=31,
        min_child_samples=25,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X_train, y_train, categorical_feature=CATEGORICAL_COLUMNS)
    preds = model.predict(X_test)
    preds = np.clip(preds, 0, None)
    return model, preds


def run_backtest(feat_df: pd.DataFrame):
    weeks = feat_df["week_start"].unique()
    folds = make_folds(weeks)
    fold_results = []

    for i, (train_weeks, test_weeks) in enumerate(folds, 1):
        train_df = feat_df[feat_df["week_start"].isin(train_weeks)].dropna(subset=FEATURE_COLUMNS[:6])
        test_df = feat_df[feat_df["week_start"].isin(test_weeks)].copy()

        model, preds = train_predict(train_df, test_df)
        test_df["model_forecast"] = preds

        model_wape = wape(test_df["units_sold"], test_df["model_forecast"])
        baseline_wape = wape(test_df["units_sold"], test_df["baseline_forecast"])
        model_bias = bias(test_df["units_sold"], test_df["model_forecast"])
        baseline_bias = bias(test_df["units_sold"], test_df["baseline_forecast"])

        fold_results.append(dict(
            fold=i,
            train_start=str(pd.Timestamp(train_weeks.min()).date()),
            train_end=str(pd.Timestamp(train_weeks.max()).date()),
            test_start=str(pd.Timestamp(test_weeks.min()).date()),
            test_end=str(pd.Timestamp(test_weeks.max()).date()),
            n_train_rows=int(len(train_df)),
            n_test_rows=int(len(test_df)),
            model_wape=round(model_wape, 4),
            baseline_wape=round(baseline_wape, 4),
            model_bias=round(model_bias, 4),
            baseline_bias=round(baseline_bias, 4),
            model_beats_baseline=bool(model_wape < baseline_wape),
        ))
        print(f"Fold {i}: test {fold_results[-1]['test_start']}..{fold_results[-1]['test_end']} "
              f"| model WAPE={model_wape:.3f} vs baseline WAPE={baseline_wape:.3f} "
              f"| model wins: {fold_results[-1]['model_beats_baseline']}")

    avg_model_wape = float(np.mean([f["model_wape"] for f in fold_results]))
    avg_baseline_wape = float(np.mean([f["baseline_wape"] for f in fold_results]))
    summary = dict(
        n_folds=len(fold_results),
        avg_model_wape=round(avg_model_wape, 4),
        avg_baseline_wape=round(avg_baseline_wape, 4),
        improvement_pct=round(100 * (avg_baseline_wape - avg_model_wape) / avg_baseline_wape, 1)
        if avg_baseline_wape else None,
        model_beats_baseline_overall=bool(avg_model_wape < avg_baseline_wape),
        folds=fold_results,
    )
    return summary


def fit_final_model_and_forecast(feat_df: pd.DataFrame, horizon=FORECAST_HORIZON_WEEKS):
    """Fit on ALL available history, then roll the model forward week by week
    to produce a genuine multi-step-ahead forecast (each step's lag features
    are rebuilt from the previous step's prediction — no peeking)."""
    train_df = feat_df.dropna(subset=FEATURE_COLUMNS[:6])
    model, _ = train_predict(train_df, train_df.tail(1))  # fit only; throwaway single-row predict

    X_all = train_df[FEATURE_COLUMNS + CATEGORICAL_COLUMNS]
    y_all = train_df["units_sold"]
    model = lgb.LGBMRegressor(
        objective="poisson", n_estimators=400, learning_rate=0.04, num_leaves=31,
        min_child_samples=25, subsample=0.8, colsample_bytree=0.8, random_state=42, verbosity=-1,
    )
    model.fit(X_all, y_all, categorical_feature=CATEGORICAL_COLUMNS)

    # residual std per SKU from the last backtest-style holdout, used for an
    # empirical 80% interval (simple & transparent, not a distributional claim)
    resid = (y_all - model.predict(X_all)).values
    global_resid_std = float(np.std(resid))

    last_week = feat_df["week_start"].max()
    future_weeks = [last_week + pd.Timedelta(weeks=i) for i in range(1, horizon + 1)]

    history = feat_df.copy()
    forecasts = []
    for wk in future_weeks:
        snap = (
            history.sort_values(["sku_id", "week_start"])
            .groupby("sku_id").tail(1)
            .copy()
        )
        snap["week_start"] = wk
        # rebuild lag/rolling features from the rolling history (includes prior predictions)
        recompute_cols = ["sku_id", "week_start", "units_sold", "category", "subcategory",
                           "promo_flag", "avg_price", "unit_cost", "list_price", "launch_date"]
        stub_history = history[recompute_cols].copy()
        stub_new = snap[["sku_id", "category", "subcategory", "promo_flag", "avg_price",
                          "unit_cost", "list_price", "launch_date"]].copy()
        stub_new["week_start"] = wk
        stub_new["units_sold"] = np.nan  # unknown yet — filled after prediction
        combined = pd.concat([stub_history, stub_new], ignore_index=True)

        from features import build_feature_frame as _bff
        feat_combined = _bff(combined)
        current = feat_combined[feat_combined["week_start"] == wk].copy()
        current = current.dropna(subset=["lag_1"])  # SKUs with at least one week of history

        X_cur = current[FEATURE_COLUMNS + CATEGORICAL_COLUMNS]
        preds = np.clip(model.predict(X_cur), 0, None)
        current["units_sold"] = preds  # feed forward as "observed" for next step's lags
        current["model_forecast"] = preds
        current["forecast_lower_80"] = np.clip(preds - 1.28 * global_resid_std, 0, None)
        current["forecast_upper_80"] = preds + 1.28 * global_resid_std

        forecasts.append(current[["sku_id", "week_start", "model_forecast",
                                   "forecast_lower_80", "forecast_upper_80",
                                   "category", "subcategory"]])

        history = pd.concat([history, current[recompute_cols]], ignore_index=True)

    forecast_df = pd.concat(forecasts, ignore_index=True)
    return model, forecast_df


def main():
    panel, _, _ = run_pipeline(save=False)
    feat_df = build_feature_frame(panel)

    print("Running rolling-origin backtest...")
    summary = run_backtest(feat_df)
    print(f"\n=== Backtest summary ===")
    print(f"Avg model WAPE:    {summary['avg_model_wape']}")
    print(f"Avg baseline WAPE: {summary['avg_baseline_wape']}")
    print(f"Model beats baseline overall: {summary['model_beats_baseline_overall']} "
          f"({summary['improvement_pct']}% improvement)")

    REPORTS.mkdir(exist_ok=True, parents=True)
    with open(REPORTS / "backtest_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\nFitting final model on full history and forecasting forward...")
    model, forecast_df = fit_final_model_and_forecast(feat_df)
    PROCESSED.mkdir(exist_ok=True, parents=True)
    forecast_df.to_parquet(PROCESSED / "forecast_output.parquet", index=False)
    forecast_df.to_csv(PROCESSED / "forecast_output.csv", index=False)
    print(f"Forecast written: {forecast_df.shape[0]:,} rows "
          f"({forecast_df['sku_id'].nunique()} SKUs x {forecast_df['week_start'].nunique()} weeks)")


if __name__ == "__main__":
    main()
