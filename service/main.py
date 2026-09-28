"""
main.py — Project FORESIGHT scoring service (D6).

Run:
    uvicorn service.main:app --reload --port 8000

Endpoints:
    GET  /health                         -> liveness check
    GET  /forecast/{sku_id}              -> weekly forecast for one SKU
    GET  /risk/{sku_id}                  -> risk score + recommended action for one SKU
    GET  /score/{sku_id}                 -> forecast + risk combined for one SKU
    POST /score/batch  {"sku_ids": [...]} -> forecast + risk for a batch of SKUs
    GET  /skus                           -> list of valid SKU ids (for discovery)

Bad input (unknown SKU, empty batch) returns a clean 404/422 — never a 500.
"""
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

app = FastAPI(
    title="FORESIGHT Scoring Service",
    description="Demand forecast + stockout/overstock risk for NorthBay Living SKUs.",
    version="1.0.0",
)

_forecast_df: Optional[pd.DataFrame] = None
_risk_df: Optional[pd.DataFrame] = None


def _load():
    global _forecast_df, _risk_df
    try:
        _forecast_df = pd.read_parquet(PROCESSED / "forecast_output.parquet")
        _risk_df = pd.read_parquet(PROCESSED / "risk_scored.parquet")
    except FileNotFoundError:
        _forecast_df, _risk_df = None, None


_load()


class BatchRequest(BaseModel):
    sku_ids: List[str]


def _check_loaded():
    if _forecast_df is None or _risk_df is None:
        raise HTTPException(
            status_code=503,
            detail="Model outputs not found. Run the pipeline first: "
                   "python src/generate_data.py && python src/pipeline.py "
                   "&& python src/forecast.py && python src/risk.py",
        )


def _forecast_for(sku_id: str):
    rows = _forecast_df[_forecast_df["sku_id"] == sku_id].sort_values("week_start")
    if rows.empty:
        return None
    return [
        dict(
            week_start=str(r["week_start"].date()),
            forecast_units=round(float(r["model_forecast"]), 1),
            lower_80=round(float(r["forecast_lower_80"]), 1),
            upper_80=round(float(r["forecast_upper_80"]), 1),
        )
        for _, r in rows.iterrows()
    ]


def _risk_for(sku_id: str):
    row = _risk_df[_risk_df["sku_id"] == sku_id]
    if row.empty:
        return None
    r = row.iloc[0]
    return dict(
        sku_id=sku_id,
        category=r["category"],
        stockout_risk=round(float(r["stockout_risk"]), 3),
        overstock_risk=round(float(r["overstock_risk"]), 3),
        weeks_of_cover=round(float(r["weeks_of_cover"]), 1),
        quadrant=r["quadrant"],
        recommended_action=r["recommended_action"],
        value_at_stake_rupees=float(r["value_at_stake_rupees"]),
    )


@app.get("/health")
def health():
    return {"status": "ok", "model_outputs_loaded": _forecast_df is not None}


@app.get("/skus")
def list_skus():
    _check_loaded()
    return {"sku_ids": sorted(_risk_df["sku_id"].unique().tolist())}


@app.get("/forecast/{sku_id}")
def get_forecast(sku_id: str):
    _check_loaded()
    result = _forecast_for(sku_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown or unscored sku_id: {sku_id}")
    return {"sku_id": sku_id, "forecast": result}


@app.get("/risk/{sku_id}")
def get_risk(sku_id: str):
    _check_loaded()
    result = _risk_for(sku_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown or unscored sku_id: {sku_id}")
    return result


@app.get("/score/{sku_id}")
def score_sku(sku_id: str):
    _check_loaded()
    forecast = _forecast_for(sku_id)
    risk = _risk_for(sku_id)
    if forecast is None or risk is None:
        raise HTTPException(status_code=404, detail=f"Unknown or unscored sku_id: {sku_id}")
    return {"sku_id": sku_id, "forecast": forecast, "risk": risk}


@app.post("/score/batch")
def score_batch(req: BatchRequest):
    _check_loaded()
    if not req.sku_ids:
        raise HTTPException(status_code=422, detail="sku_ids must be a non-empty list")
    results = []
    for sku_id in req.sku_ids:
        forecast = _forecast_for(sku_id)
        risk = _risk_for(sku_id)
        if forecast is None or risk is None:
            results.append({"sku_id": sku_id, "error": "unknown or unscored sku_id"})
        else:
            results.append({"sku_id": sku_id, "forecast": forecast, "risk": risk})
    return {"results": results}
