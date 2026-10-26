# ============================================================
# GREENMIND AI
# 24-HOUR ENERGY OPTIMIZATION ENGINE
# ============================================================

from pathlib import Path

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "models" / "energy_forecaster.joblib"
DATA_PATH = BASE_DIR / "data" / "processed" / "hourly_energy.csv"


# ============================================================
# CONFIGURATION
# ============================================================

FORECAST_HOURS = 24

FEATURES = [
    "hour",
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "lag_1",
    "lag_24",
    "lag_168",
    "rolling_mean_24",
    "rolling_std_24",
    "rolling_mean_168",
]


# ============================================================
# LOAD MODEL
# ============================================================

print("=" * 60)
print("GREENMIND AI - 24-HOUR ENERGY OPTIMIZATION")
print("=" * 60)
print()
print("[1/5] Loading forecasting model...")

model = joblib.load(MODEL_PATH)

print("Forecasting model loaded successfully.")


# ============================================================
# LOAD DATA
# ============================================================

print()
print("[2/5] Loading electricity dataset...")

df = pd.read_csv(DATA_PATH)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["total_energy"] = pd.to_numeric(df["total_energy"], errors="coerce")

df = (
    df.dropna(subset=["timestamp", "total_energy"])
    .sort_values("timestamp")
    .reset_index(drop=True)
)

print(f"Loaded {len(df)} hourly observations.")


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def add_features(data):
    data = data.copy()

    data["hour"] = data["timestamp"].dt.hour
    data["day_of_week"] = data["timestamp"].dt.dayofweek
    data["day_of_month"] = data["timestamp"].dt.day
    data["month"] = data["timestamp"].dt.month
    data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)
    data["lag_1"] = data["total_energy"].shift(1)
    data["lag_24"] = data["total_energy"].shift(24)
    data["lag_168"] = data["total_energy"].shift(168)
    data["rolling_mean_24"] = data["total_energy"].shift(1).rolling(24).mean()
    data["rolling_std_24"] = data["total_energy"].shift(1).rolling(24).std()
    data["rolling_mean_168"] = data["total_energy"].shift(1).rolling(168).mean()

    return data


# ============================================================
# HISTORICAL BASELINE
# ============================================================

def historical_baseline(timestamp, data):
    hour = timestamp.hour
    weekday = timestamp.dayofweek

    matching = data[
        (data["timestamp"].dt.hour == hour)
        & (data["timestamp"].dt.dayofweek == weekday)
    ].iloc[:-1]

    if len(matching) >= 10:
        values = matching["total_energy"].tail(52)
        return float(values.mean())

    matching = data[data["timestamp"].dt.hour == hour].iloc[:-1]

    if len(matching) >= 10:
        values = matching["total_energy"].tail(90)
        return float(values.mean())

    return float(data["total_energy"].tail(168).mean())


# ============================================================
# FORECAST CONFIDENCE
# ============================================================

def calculate_confidence(timestamp, baseline, data):
    hour = timestamp.hour
    weekday = timestamp.dayofweek

    samples = data[
        (data["timestamp"].dt.hour == hour)
        & (data["timestamp"].dt.dayofweek == weekday)
    ].iloc[:-1]

    if len(samples) < 5:
        return 70.0

    values = samples["total_energy"].tail(52)
    std = float(values.std())

    if not np.isfinite(std):
        std = 0

    variability = std / max(baseline, 1)
    sample_factor = min(1.0, len(values) / 52)
    variability_factor = 1 / (1 + variability)

    confidence = 70 + 25 * sample_factor * variability_factor

    return round(max(60, min(95, confidence)), 1)


# ============================================================
# CREATE NEXT-HOUR MODEL FEATURES
# ============================================================

def create_prediction_row(history, future_timestamp):
    values = history["total_energy"].tolist()

    if len(values) < 168:
        raise ValueError("At least 168 historical hours are required.")

    row = {
        "hour": future_timestamp.hour,
        "day_of_week": future_timestamp.dayofweek,
        "day_of_month": future_timestamp.day,
        "month": future_timestamp.month,
        "is_weekend": int(future_timestamp.dayofweek >= 5),
        "lag_1": values[-1],
        "lag_24": values[-24],
        "lag_168": values[-168],
        "rolling_mean_24": pd.Series(values[-24:]).mean(),
        "rolling_std_24": pd.Series(values[-24:]).std(),
        "rolling_mean_168": pd.Series(values[-168:]).mean(),
    }

    return pd.DataFrame([row], columns=FEATURES)


# ============================================================
# 24-HOUR FORECAST
# ============================================================

print()
print("[3/5] Generating 24-hour AI forecast...")


def generate_forecast():
    history = df.copy()
    forecasts = []
    current_timestamp = history.iloc[-1]["timestamp"]

    for hour_offset in range(1, FORECAST_HOURS + 1):
        future_timestamp = current_timestamp + pd.Timedelta(hours=hour_offset)

        X = create_prediction_row(history, future_timestamp)
        prediction = max(0, float(model.predict(X)[0]))
        baseline = historical_baseline(future_timestamp, df)
        confidence = calculate_confidence(future_timestamp, baseline, df)

        forecasts.append(
            {
                "timestamp": future_timestamp,
                "predicted_energy": prediction,
                "historical_baseline": baseline,
                "confidence": confidence,
            }
        )

        history = pd.concat(
            [
                history,
                pd.DataFrame(
                    [{"timestamp": future_timestamp, "total_energy": prediction}]
                ),
            ],
            ignore_index=True,
        )

    return forecasts


# ============================================================
# OPTIMIZATION ANALYSIS
# ============================================================

print()
print("[4/5] Finding optimal energy windows...")


def optimize():
    forecasts = generate_forecast()

    current_timestamp = df.iloc[-1]["timestamp"]
    current_energy = float(df.iloc[-1]["total_energy"])

    current_baseline = historical_baseline(current_timestamp, df)
    current_vs_baseline = ((current_energy - current_baseline) / current_baseline) * 100
    current_is_low = current_vs_baseline <= -5

    for item in forecasts:
        prediction = item["predicted_energy"]
        baseline = item["historical_baseline"]

        vs_baseline = ((prediction - baseline) / baseline) * 100
        vs_current = ((prediction - current_energy) / current_energy) * 100

        item["vs_historical_baseline"] = vs_baseline
        item["vs_current"] = vs_current

        # A future hour is actionable only when it is both:
        # 1. at least 5% below its historical baseline, and
        # 2. lower than the current operating demand.
        item["optimization_opportunity"] = (
            vs_baseline <= -5 and prediction < current_energy
        )

    candidates = [
        item for item in forecasts if item["optimization_opportunity"]
    ]

    candidates.sort(key=lambda x: x["timestamp"])

    windows = []
    current_window = []

    for item in candidates:
        if not current_window:
            current_window = [item]
            continue

        previous = current_window[-1]

        if item["timestamp"] - previous["timestamp"] == pd.Timedelta(hours=1):
            current_window.append(item)
        else:
            windows.append(current_window)
            current_window = [item]

    if current_window:
        windows.append(current_window)

    formatted_windows = []

    for window in windows:
        average_prediction = float(
            np.mean([x["predicted_energy"] for x in window])
        )
        average_baseline = float(
            np.mean([x["historical_baseline"] for x in window])
        )
        average_confidence = float(
            np.mean([x["confidence"] for x in window])
        )

        saving_vs_baseline = (
            (average_baseline - average_prediction) / average_baseline
        ) * 100

        saving_vs_current = (
            (current_energy - average_prediction) / current_energy
        ) * 100

        start = window[0]["timestamp"]
        end = window[-1]["timestamp"] + pd.Timedelta(hours=1)

        if saving_vs_baseline >= 15:
            rating = "excellent"
        elif saving_vs_baseline >= 10:
            rating = "good"
        else:
            rating = "moderate"

        formatted_windows.append(
            {
                "start": start.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
                "start_timestamp": str(start),
                "end_timestamp": str(end),
                "average_predicted_demand": round(average_prediction, 2),
                "average_historical_demand": round(average_baseline, 2),
                "saving_vs_historical_baseline": round(saving_vs_baseline, 2),
                "change_vs_current": round(saving_vs_current, 2),
                "confidence": round(average_confidence, 1),
                "rating": rating,
            }
        )

    formatted_windows.sort(
        key=lambda x: (
            -x["change_vs_current"],
            -x["saving_vs_historical_baseline"],
            -x["confidence"],
        )
    )

    best_window = formatted_windows[0] if formatted_windows else None

    hourly_forecast = []

    for item in forecasts:
        hourly_forecast.append(
            {
                "time": item["timestamp"].strftime("%H:%M"),
                "timestamp": str(item["timestamp"]),
                "predicted_energy": round(item["predicted_energy"], 2),
                "historical_baseline": round(item["historical_baseline"], 2),
                "vs_historical_baseline": round(
                    item["vs_historical_baseline"], 2
                ),
                "vs_current": round(item["vs_current"], 2),
                "confidence": round(item["confidence"], 1),
                "optimization_opportunity": item["optimization_opportunity"],
            }
        )

    if best_window:
        recommendation = (
            "Schedule flexible or energy-intensive workloads during "
            "this forecasted lower-demand window."
        )
    else:
        recommendation = (
            "No future period is currently lower than both the current "
            "demand and its historical baseline. Continue normal operations."
        )

    return {
        "status": "optimization_available" if best_window else "no_optimization_opportunity",
        "generated_at": str(current_timestamp),
        "analysis_period": "Next 24 hours",
        "current_energy": round(current_energy, 2),
        "current_historical_baseline": round(current_baseline, 2),
        "current_vs_historical_baseline": round(current_vs_baseline, 2),
        "current_period_already_low": current_is_low,
        "best_window": best_window,
        "windows": formatted_windows,
        "hourly_forecast": hourly_forecast,
        "recommendation": recommendation,
    }


print()
print("[5/5] Optimization engine ready.")
print("=" * 60)
