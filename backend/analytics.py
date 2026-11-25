"""Self-contained analytics endpoints built from the active telemetry history.

All scenario outputs are analytical simulations, not measured facility savings.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from backend.telemetry import telemetry_store

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _history() -> pd.DataFrame:
    data = telemetry_store.get_history()
    if data.empty:
        raise HTTPException(status_code=503, detail="Telemetry history is unavailable.")
    data = data.sort_values("timestamp").reset_index(drop=True)
    return data


def build_overview(data: pd.DataFrame, days: int = 7) -> dict:
    if days not in (7, 30, 90):
        raise ValueError("days must be 7, 30, or 90")
    frame = data.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    end = frame["timestamp"].max()
    start = end - pd.Timedelta(days=days)
    current = frame[frame["timestamp"] > start].copy()
    previous = frame[
        (frame["timestamp"] <= start)
        & (frame["timestamp"] > start - pd.Timedelta(days=days))
    ].copy()

    def stats(part: pd.DataFrame) -> dict:
        values = part["total_energy"].astype(float)
        if values.empty:
            return {"observations": 0, "energy_kwh": 0.0, "average_kw": 0.0,
                    "peak_kw": 0.0, "minimum_kw": 0.0, "std_dev_kw": 0.0}
        return {
            "observations": int(len(values)),
            "energy_kwh": round(float(values.sum()), 3),
            "average_kw": round(float(values.mean()), 3),
            "peak_kw": round(float(values.max()), 3),
            "minimum_kw": round(float(values.min()), 3),
            "std_dev_kw": round(float(values.std(ddof=0)), 3),
        }

    current_stats = stats(current)
    previous_stats = stats(previous)
    delta = None
    if previous_stats["energy_kwh"] > 0:
        delta = round(
            (current_stats["energy_kwh"] - previous_stats["energy_kwh"])
            / previous_stats["energy_kwh"] * 100, 2
        )

    daily = current.assign(
        date=current["timestamp"].dt.strftime("%Y-%m-%d")
    ).groupby("date", as_index=False)["total_energy"].agg(
        energy_kwh="sum", average_kw="mean", peak_kw="max"
    )
    hourly = current.assign(hour=current["timestamp"].dt.hour).groupby(
        "hour", as_index=False
    )["total_energy"].mean().rename(columns={"total_energy": "average_kw"})

    return {
        "period_days": days,
        "source": telemetry_store.snapshot()["source"],
        "mode": telemetry_store.snapshot()["mode"],
        "current_period": current_stats,
        "previous_period": previous_stats,
        "energy_change_pct": delta,
        "daily": [
            {**row, "energy_kwh": round(float(row["energy_kwh"]), 3),
             "average_kw": round(float(row["average_kw"]), 3),
             "peak_kw": round(float(row["peak_kw"]), 3)}
            for row in daily.to_dict(orient="records")
        ],
        "hourly_profile": [
            {"hour": int(row["hour"]), "average_kw": round(float(row["average_kw"]), 3)}
            for row in hourly.to_dict(orient="records")
        ],
        "interpretation": "Hourly kW observations are treated as one-hour intervals; summed values are estimated kWh.",
    }


def build_load_shift_scenario(data: pd.DataFrame, shift_fraction: float = 0.10) -> dict:
    if not 0 < shift_fraction <= 0.25:
        raise ValueError("shift_fraction must be greater than 0 and at most 0.25")
    original = data["total_energy"].astype(float).to_numpy(copy=True)
    if len(original) < 10:
        raise ValueError("At least 10 observations are required for scenario analysis.")

    adjusted = original.copy()
    count = max(1, int(len(original) * 0.20))
    high_indices = np.argsort(original)[-count:]
    low_indices = np.argsort(original)[:count]
    moved = 0.0
    for source_idx in high_indices:
        amount = max(0.0, adjusted[source_idx] * shift_fraction)
        adjusted[source_idx] -= amount
        moved += amount
    if len(low_indices):
        adjusted[low_indices] += moved / len(low_indices)

    before_peak = float(np.max(original))
    after_peak = float(np.max(adjusted))
    total_before = float(np.sum(original))
    total_after = float(np.sum(adjusted))
    return {
        "scenario": "Illustrative load shifting",
        "assumption": f"Shift {shift_fraction:.0%} of demand from the highest-demand 20% of observed hours into the lowest-demand 20%.",
        "observations": int(len(original)),
        "baseline": {
            "total_energy_kwh": round(total_before, 3),
            "peak_kw": round(before_peak, 3),
            "average_kw": round(float(np.mean(original)), 3),
        },
        "simulated": {
            "total_energy_kwh": round(total_after, 3),
            "peak_kw": round(after_peak, 3),
            "average_kw": round(float(np.mean(adjusted)), 3),
        },
        "peak_reduction_pct": round((before_peak - after_peak) / before_peak * 100, 3) if before_peak else 0.0,
        "energy_conservation_difference_kwh": round(total_after - total_before, 8),
        "energy_conserved": bool(np.isclose(total_before, total_after, rtol=1e-9, atol=1e-6)),
        "moved_energy_kwh": round(moved, 3),
        "limitations": [
            "This is a mathematical what-if scenario, not a dispatch instruction.",
            "It assumes flexible workloads can move between selected hours without service, capacity, or latency constraints.",
            "It does not claim energy savings; total energy is intentionally conserved.",
        ],
    }


@router.get("/overview")
def analytics_overview(days: Literal[7, 30, 90] = Query(7)):
    return build_overview(_history(), days)


@router.get("/load-shift")
def load_shift_scenario(shift_fraction: float = Query(0.10, gt=0, le=0.25)):
    return build_load_shift_scenario(_history(), shift_fraction)


@router.get("/model")
def model_diagnostics():
    # Import lazily to avoid a module-import cycle with the main FastAPI app.
    from backend.main import model, FEATURES, get_energy_history, build_prediction_features

    data = get_energy_history()
    if model is None or data is None:
        raise HTTPException(status_code=503, detail="Forecasting model or telemetry history is unavailable.")

    feature_rows = build_prediction_features(data)
    estimators = getattr(model, "estimators_", [])
    importance = []
    if hasattr(model, "feature_importances_"):
        importance = [
            {"feature": name, "importance": round(float(value), 6)}
            for name, value in zip(FEATURES, model.feature_importances_)
        ]
        importance.sort(key=lambda item: item["importance"], reverse=True)

    evaluation = {"status": "insufficient_history", "samples": 0}
    if len(data) >= 169 and len(feature_rows) >= 2:
        X = feature_rows[FEATURES]
        actual = data["total_energy"].shift(-1).reindex(feature_rows.index).dropna()
        X = X.loc[actual.index]
        if len(X):
            predicted = np.asarray(model.predict(X), dtype=float)
            actual_values = actual.to_numpy(dtype=float)
            errors = predicted - actual_values
            mae = float(np.mean(np.abs(errors)))
            rmse = float(np.sqrt(np.mean(errors ** 2)))
            denominator = float(np.sum((actual_values - np.mean(actual_values)) ** 2))
            r2 = 1 - float(np.sum(errors ** 2)) / denominator if denominator > 0 else None
            evaluation = {
                "status": "evaluated_on_available_history",
                "samples": int(len(actual_values)),
                "mae_kw": round(mae, 4),
                "rmse_kw": round(rmse, 4),
                "r2": round(r2, 4) if r2 is not None else None,
                "method": "Retrospective one-step predictions on available telemetry; not a held-out test set.",
            }

    return {
        "model_type": type(model).__name__,
        "features": FEATURES,
        "feature_importance": importance,
        "tree_count": len(estimators),
        "evaluation": evaluation,
        "confidence_note": "Random Forest tree spread is not a calibrated probability interval.",
    }
