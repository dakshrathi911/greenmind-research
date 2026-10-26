# ============================================================
# GREENMIND AI
# ENERGY INTELLIGENCE BACKEND
# ============================================================

from pathlib import Path
from datetime import datetime
import math
import warnings

import joblib
import numpy as np
import pandas as pd

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.optimization_engine import optimize

from backend.live_simulator import router as live_router


warnings.filterwarnings("ignore")


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="GreenMind AI",
    description="AI-powered energy intelligence platform",
    version="1.0.0",
)

app.include_router(live_router)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "energy_forecaster.joblib"
)

DATA_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "hourly_energy.csv"
)


# ============================================================
# MODEL FEATURES
# IMPORTANT:
# These MUST match the Random Forest training features.
# ============================================================

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
# GLOBAL OBJECTS
# ============================================================

model = None
energy_df = None


# ============================================================
# LOAD MODEL
# ============================================================

try:

    model = joblib.load(
        MODEL_PATH
    )

    print(
        "GreenMind AI model loaded successfully."
    )

except Exception as e:

    print(
        f"WARNING: Could not load model: {e}"
    )


# ============================================================
# LOAD ENERGY DATASET
# ============================================================

try:

    energy_df = pd.read_csv(
        DATA_PATH
    )

    energy_df["timestamp"] = pd.to_datetime(
        energy_df["timestamp"]
    )

    energy_df["total_energy"] = pd.to_numeric(
        energy_df["total_energy"],
        errors="coerce"
    )

    energy_df = (
        energy_df
        .dropna(
            subset=[
                "timestamp",
                "total_energy"
            ]
        )
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    print(
        "Energy dataset loaded successfully: "
        f"{len(energy_df)} hourly observations."
    )

except Exception as e:

    energy_df = None

    print(
        f"WARNING: Dataset could not be loaded: {e}"
    )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():

    print()
    print("=" * 60)
    print("GREENMIND AI BACKEND")
    print("=" * 60)

    print(
        "Model:",
        "Loaded" if model is not None else "Not Loaded"
    )

    print(
        "Dataset:",
        "Loaded" if energy_df is not None else "Not Loaded"
    )

    print(
        "Features:",
        FEATURES
    )

    print("=" * 60)
    print()


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "name": "GreenMind AI",
        "description": "AI-powered energy intelligence platform",
        "status": "operational",
        "model_loaded": model is not None,
        "dataset_loaded": energy_df is not None,
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "model_loaded": model is not None,
        "dataset_loaded": energy_df is not None,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# FEATURE CREATION
# ============================================================

def build_prediction_features(df):

    if df is None or len(df) < 168:

        raise ValueError(
            "Not enough historical data to create prediction features."
        )

    data = df.copy()

    data["hour"] = (
        data["timestamp"].dt.hour
    )

    data["day_of_week"] = (
        data["timestamp"].dt.dayofweek
    )

    data["day_of_month"] = (
        data["timestamp"].dt.day
    )

    data["month"] = (
        data["timestamp"].dt.month
    )

    data["is_weekend"] = (
        data["day_of_week"] >= 5
    ).astype(int)

    data["lag_1"] = (
        data["total_energy"].shift(1)
    )

    data["lag_24"] = (
        data["total_energy"].shift(24)
    )

    data["lag_168"] = (
        data["total_energy"].shift(168)
    )

    data["rolling_mean_24"] = (
        data["total_energy"]
        .shift(1)
        .rolling(24)
        .mean()
    )

    data["rolling_std_24"] = (
        data["total_energy"]
        .shift(1)
        .rolling(24)
        .std()
    )

    data["rolling_mean_168"] = (
        data["total_energy"]
        .shift(1)
        .rolling(168)
        .mean()
    )

    data = data.dropna(
        subset=FEATURES
    )

    if len(data) == 0:

        raise ValueError(
            "Unable to construct prediction features."
        )

    return data


# ============================================================
# PREDICTION
# ============================================================

def generate_prediction():

    if model is None:

        raise RuntimeError(
            "Forecasting model is not loaded."
        )

    if energy_df is None:

        raise RuntimeError(
            "Energy dataset is not loaded."
        )

    feature_df = build_prediction_features(
        energy_df
    )

    latest = feature_df.iloc[-1]

    X = pd.DataFrame(
        [
            {
                feature: latest[feature]
                for feature in FEATURES
            }
        ]
    )

    prediction = float(
        model.predict(X)[0]
    )

    current_energy = float(
        energy_df.iloc[-1]["total_energy"]
    )

    if current_energy != 0:

        change = (
            (prediction - current_energy)
            / current_energy
        ) * 100

    else:

        change = 0

    # --------------------------------------------------------
    # Random Forest prediction consistency
    # --------------------------------------------------------

    confidence = 90.0

    try:

        estimators = getattr(
            model,
            "estimators_",
            []
        )

        if len(estimators) > 1:

            tree_predictions = np.array(
                [
                    estimator.predict(X)[0]
                    for estimator in estimators
                ]
            )

            mean_prediction = (
                tree_predictions.mean()
            )

            std_prediction = (
                tree_predictions.std()
            )

            if mean_prediction != 0:

                coefficient_variation = (
                    std_prediction
                    / abs(mean_prediction)
                )

                confidence = (
                    100
                    - coefficient_variation
                    * 100
                )

                confidence = max(
                    50,
                    min(
                        99.9,
                        confidence
                    )
                )

    except Exception:

        confidence = 90.0

    uncertainty = (
        prediction
        * (
            (100 - confidence)
            / 100
        )
    )

    return {

        "value":
            round(
                prediction,
                2
            ),

        "unit":
            "kW",

        "period":
            "Next hour",

        "change":
            round(
                change,
                2
            ),

        "confidence":
            round(
                confidence,
                1
            ),

        "uncertainty":
            round(
                uncertainty,
                2
            ),

        "based_on":
            str(
                energy_df.iloc[-1][
                    "timestamp"
                ]
            ),
    }


# ============================================================
# ENERGY PERFORMANCE
# ============================================================

def calculate_efficiency():

    if energy_df is None:
        return 0

    current = float(
        energy_df.iloc[-1]["total_energy"]
    )

    recent = (
        energy_df["total_energy"]
        .tail(168)
        .iloc[:-1]
    )

    if len(recent) == 0:
        return 0

    baseline = float(
        recent.mean()
    )

    if baseline <= 0:
        return 0

    # This is a relative energy-performance score,
    # NOT a physical data-center efficiency/PUE metric.
    #
    # 100 = current demand equals or is below baseline
    # Lower scores indicate demand above the recent baseline.
    deviation = (
        (current - baseline)
        / baseline
    ) * 100

    score = (
        100
        - max(0, deviation)
    )

    score = max(
        0,
        min(
            100,
            score
        )
    )

    return round(
        score,
        1
    )

# ============================================================
# CARBON FOOTPRINT
# ============================================================

def calculate_carbon():

    if energy_df is None:
        return 0

    current_power_kw = float(
        energy_df.iloc[-1]["total_energy"]
    )

    # The dataset contains hourly power values in kW.
    # For a one-hour interval:
    #
    # kW × 1 hour = kWh
    #
    # This is an estimated grid emission factor.
    # It should eventually be replaced with a configurable,
    # location/time-specific carbon intensity.
    emission_factor_kg_per_kwh = 0.676

    energy_kwh = current_power_kw * 1.0

    carbon_kg = (
        energy_kwh
        * emission_factor_kg_per_kwh
    )

    return round(
        carbon_kg,
        2
    )

# ============================================================
# ENERGY HISTORY
# ============================================================

def generate_energy_history():

    if energy_df is None:
        return []

    history = (
        energy_df
        .tail(24)
        .copy()
    )

    result = []

    for _, row in history.iterrows():

        result.append(
            {
                "time":
                    row[
                        "timestamp"
                    ].strftime(
                        "%H:%M"
                    ),

                "energy":
                    round(
                        float(
                            row[
                                "total_energy"
                            ]
                        ),
                        2
                    ),
            }
        )

    return result


# ============================================================
# ANOMALY DETECTION
# ============================================================

def generate_anomaly():

    if energy_df is None:

        return {
            "detected": False,
            "severity": "normal",
            "score": 0,
            "z_score": 0,
            "current_energy": 0,
            "expected_energy": 0,
            "deviation": 0,
            "is_peak": False,
            "peak_threshold": 0,
            "weekly_peak": 0,
            "hour": 0,
            "day_of_week": 0,
            "timestamp": "",
            "message": "Energy dataset is unavailable.",
            "recommendation": "No recommendation available.",
        }

    data = energy_df.copy()

    data["hour"] = (
        data["timestamp"].dt.hour
    )

    data["day_of_week"] = (
        data["timestamp"].dt.dayofweek
    )

    current = data.iloc[-1]

    current_energy = float(
        current["total_energy"]
    )

    hour = int(
        current["hour"]
    )

    day_of_week = int(
        current["day_of_week"]
    )

    # --------------------------------------------------------
    # Same-hour historical distribution
    # --------------------------------------------------------

    same_hour = data[
        data["hour"] == hour
    ].iloc[:-1]

    if len(same_hour) < 10:

        expected_energy = float(
            data["total_energy"]
            .tail(168)
            .mean()
        )

        standard_deviation = float(
            data["total_energy"]
            .tail(168)
            .std()
        )

    else:

        expected_energy = float(
            same_hour[
                "total_energy"
            ].mean()
        )

        standard_deviation = float(
            same_hour[
                "total_energy"
            ].std()
        )

    if standard_deviation <= 0:
        standard_deviation = 1

    # --------------------------------------------------------
    # Z-score
    # --------------------------------------------------------

    z_score = (
        current_energy
        - expected_energy
    ) / standard_deviation

    anomaly_score = abs(
        z_score
    )

    deviation = (
        (
            current_energy
            - expected_energy
        )
        / expected_energy
    ) * 100 if expected_energy else 0

    # --------------------------------------------------------
    # Peak detection
    # --------------------------------------------------------

    recent_week = data[
        "total_energy"
    ].tail(168)

    weekly_peak = float(
        recent_week.max()
    )

    peak_threshold = float(
        recent_week.quantile(
            0.95
        )
    )

    is_peak = (
        current_energy
        >= peak_threshold
    )

    # --------------------------------------------------------
    # Anomaly severity
    # --------------------------------------------------------

    if anomaly_score >= 3:

        severity = "critical"

    elif anomaly_score >= 2:

        severity = "high"

    elif anomaly_score >= 1.5:

        severity = "medium"

    else:

        severity = "normal"

    detected = (
        anomaly_score >= 2
    )

    # --------------------------------------------------------
    # AI message
    # --------------------------------------------------------

    if detected:

        if deviation < 0:

            message = (
                "High energy anomaly detected. "
                "Current demand is significantly "
                "below the expected pattern."
            )

            recommendation = (
                "Consider scheduling flexible or "
                "energy-intensive workloads during "
                "this lower-demand period."
            )

        else:

            message = (
                "High energy anomaly detected. "
                "Current demand is significantly "
                "above the expected pattern."
            )

            recommendation = (
                "Review non-critical workloads and "
                "investigate unusual energy consumption."
            )

    elif is_peak:

        message = (
            "High-demand peak detected. "
            "Current energy consumption is near "
            "the recent operating maximum."
        )

        recommendation = (
            "Avoid unnecessary energy-intensive "
            "workloads during this peak period."
        )

    else:

        message = (
            "Energy demand is within the expected "
            "historical range."
        )

        recommendation = (
            "Continue normal operations."
        )

    return {

        "detected":
            bool(detected),

        "severity":
            severity,

        "score":
            round(
                anomaly_score,
                2
            ),

        "z_score":
            round(
                z_score,
                2
            ),

        "current_energy":
            round(
                current_energy,
                2
            ),

        "expected_energy":
            round(
                expected_energy,
                2
            ),

        "deviation":
            round(
                deviation,
                2
            ),

        "is_peak":
            bool(is_peak),

        "peak_threshold":
            round(
                peak_threshold,
                2
            ),

        "weekly_peak":
            round(
                weekly_peak,
                2
            ),

        "hour":
            hour,

        "day_of_week":
            day_of_week,

        "timestamp":
            str(
                current[
                    "timestamp"
                ]
            ),

        "message":
            message,

        "recommendation":
            recommendation,
    }


# ============================================================
# RECOMMENDATIONS
# ============================================================

def generate_recommendations(
    prediction,
    anomaly,
):

    recommendations = []

    current_energy = (
        float(
            energy_df.iloc[-1][
                "total_energy"
            ]
        )
        if energy_df is not None
        else 0
    )

    predicted_energy = float(
        prediction.get(
            "value",
            current_energy
        )
    )

    predicted_change = float(
        prediction.get(
            "change",
            0
        )
    )

    # --------------------------------------------------------
    # Low-demand opportunity
    # --------------------------------------------------------

    if predicted_change <= -10:

        recommendations.append(
            {
                "title":
                    "Use the upcoming low-demand period",

                "description":
                    "GreenMind AI predicts a significant "
                    "drop in energy demand. This may be "
                    "a favorable period for flexible or "
                    "energy-intensive workloads.",

                "saving":
                    f"Predicted reduction: "
                    f"{abs(predicted_change):.1f}%",

                "priority":
                    "high",
            }
        )

    # --------------------------------------------------------
    # High-demand warning
    # --------------------------------------------------------

    elif predicted_change >= 10:

        recommendations.append(
            {
                "title":
                    "Reduce flexible workloads",

                "description":
                    "GreenMind AI predicts increased "
                    "energy demand during the next hour. "
                    "Consider delaying non-critical "
                    "energy-intensive workloads.",

                "saving":
                    f"Predicted increase: "
                    f"{predicted_change:.1f}%",

                "priority":
                    "high",
            }
        )

    else:

        recommendations.append(
            {
                "title":
                    "Maintain current workload",

                "description":
                    "Predicted energy demand is relatively "
                    "stable. No major workload adjustment "
                    "is required.",

                "saving":
                    "Stable demand",

                "priority":
                    "low",
            }
        )

    # --------------------------------------------------------
    # Renewable recommendation
    # --------------------------------------------------------

    recommendations.append(
        {
            "title":
                "Increase renewable usage",

            "description":
                "Use available renewable energy during "
                "higher-demand periods to reduce grid "
                "dependence and associated emissions.",

            "saving":
                "Potential carbon reduction",

            "priority":
                "low",
        }
    )

    return recommendations


# ============================================================
# DECISION ENGINE
# ============================================================

def generate_decision(
    prediction,
    anomaly,
    efficiency,
):

    current_energy = float(
        prediction.get(
            "current_energy",
            energy_df.iloc[-1][
                "total_energy"
            ]
            if energy_df is not None
            else 0
        )
    )

    predicted_energy = float(
        prediction.get(
            "value",
            current_energy
        )
    )

    predicted_change = float(
        prediction.get(
            "change",
            0
        )
    )

    confidence = float(
        prediction.get(
            "confidence",
            0
        )
    )

    # --------------------------------------------------------
    # Low-demand opportunity
    # --------------------------------------------------------

    if (
        predicted_change <= -10
        and confidence >= 80
    ):

        return {

            "decision":
                "RUN FLEXIBLE WORKLOADS",

            "status":
                "opportunity",

            "summary":
                "GreenMind AI identifies an upcoming "
                "low-demand period suitable for flexible "
                "energy-intensive workloads.",

            "action":
                "Schedule non-urgent or energy-intensive "
                "workloads during this period.",

            "reason":
                f"Predicted demand is "
                f"{abs(predicted_change):.1f}% lower "
                f"than the current level.",

            "current_energy":
                round(
                    current_energy,
                    2
                ),

            "predicted_energy":
                round(
                    predicted_energy,
                    2
                ),

            "predicted_change":
                round(
                    predicted_change,
                    2
                ),

            "efficiency":
                round(
                    efficiency,
                    1
                ),

            "confidence":
                round(
                    confidence,
                    1
                ),

            "confidence_level":
                (
                    "High"
                    if confidence >= 80
                    else "Moderate"
                ),
        }

    # --------------------------------------------------------
    # High-demand warning
    # --------------------------------------------------------

    if predicted_change >= 10:

        return {

            "decision":
                "REDUCE FLEXIBLE WORKLOADS",

            "status":
                "warning",

            "summary":
                "GreenMind AI predicts an upcoming "
                "high-demand period.",

            "action":
                "Delay non-critical or energy-intensive "
                "workloads where possible.",

            "reason":
                f"Predicted demand is "
                f"{predicted_change:.1f}% higher "
                f"than the current level.",

            "current_energy":
                round(
                    current_energy,
                    2
                ),

            "predicted_energy":
                round(
                    predicted_energy,
                    2
                ),

            "predicted_change":
                round(
                    predicted_change,
                    2
                ),

            "efficiency":
                round(
                    efficiency,
                    1
                ),

            "confidence":
                round(
                    confidence,
                    1
                ),

            "confidence_level":
                (
                    "High"
                    if confidence >= 80
                    else "Moderate"
                ),
        }

    # --------------------------------------------------------
    # Anomaly warning
    # --------------------------------------------------------

    if (
        anomaly.get(
            "detected",
            False
        )
        and anomaly.get(
            "deviation",
            0
        ) > 10
    ):

        return {

            "decision":
                "INVESTIGATE ENERGY SPIKE",

            "status":
                "warning",

            "summary":
                "GreenMind AI detected unusually high "
                "energy demand compared with the historical "
                "pattern.",

            "action":
                "Review current workloads and investigate "
                "the source of the increased demand.",

            "reason":
                "Current demand is significantly above "
                "the historical expected pattern.",

            "current_energy":
                round(
                    current_energy,
                    2
                ),

            "predicted_energy":
                round(
                    predicted_energy,
                    2
                ),

            "predicted_change":
                round(
                    predicted_change,
                    2
                ),

            "efficiency":
                round(
                    efficiency,
                    1
                ),

            "confidence":
                round(
                    confidence,
                    1
                ),

            "confidence_level":
                (
                    "High"
                    if confidence >= 80
                    else "Moderate"
                ),
        }

    # --------------------------------------------------------
    # Stable
    # --------------------------------------------------------

    return {

        "decision":
            "MAINTAIN CURRENT OPERATION",

        "status":
            "stable",

        "summary":
            "GreenMind AI finds no significant upcoming "
            "energy demand change requiring intervention.",

        "action":
            "Continue normal operations and monitor "
            "the next forecast.",

        "reason":
            "Predicted energy demand remains within "
            "the expected operating range.",

        "current_energy":
            round(
                current_energy,
                2
            ),

        "predicted_energy":
            round(
                predicted_energy,
                2
            ),

        "predicted_change":
            round(
                predicted_change,
                2
            ),

        "efficiency":
            round(
                efficiency,
                1
            ),

        "confidence":
            round(
                confidence,
                1
            ),

        "confidence_level":
            (
                "High"
                if confidence >= 80
                else "Moderate"
            ),
    }


# ============================================================
# HISTORICAL INTELLIGENCE
# ============================================================

def generate_historical_intelligence(
    data
):

    if data is None or len(data) < 168:

        return {

            "status":
                "unavailable",

            "current_energy":
                0,

            "same_hour_average":
                0,

            "same_hour_median":
                0,

            "same_weekday_hour_average":
                0,

            "weekly_average":
                0,

            "current_vs_same_hour":
                0,

            "current_vs_weekday_hour":
                0,

            "current_vs_week":
                0,

            "hour":
                0,

            "day_of_week":
                0,

            "timestamp":
                "",

            "insight":
                "Not enough historical data available.",
        }

    working = data.copy()

    working["hour"] = (
        working["timestamp"].dt.hour
    )

    working["day_of_week"] = (
        working["timestamp"].dt.dayofweek
    )

    current_row = working.iloc[-1]

    current_energy = float(
        current_row[
            "total_energy"
        ]
    )

    current_hour = int(
        current_row[
            "hour"
        ]
    )

    current_day = int(
        current_row[
            "day_of_week"
        ]
    )

    # --------------------------------------------------------
    # Same hour
    # --------------------------------------------------------

    same_hour = working[
        working["hour"]
        == current_hour
    ].iloc[:-1]

    # --------------------------------------------------------
    # Same weekday + hour
    # --------------------------------------------------------

    same_weekday_hour = working[
        (
            working["hour"]
            == current_hour
        )
        &
        (
            working["day_of_week"]
            == current_day
        )
    ].iloc[:-1]

    # --------------------------------------------------------
    # Recent 7 days
    # --------------------------------------------------------

    recent_week = working.iloc[
        -168:-1
    ]

    # --------------------------------------------------------
    # Baselines
    # --------------------------------------------------------

    same_hour_average = float(
        same_hour[
            "total_energy"
        ].mean()
    )

    same_hour_median = float(
        same_hour[
            "total_energy"
        ].median()
    )

    same_weekday_hour_average = float(
        same_weekday_hour[
            "total_energy"
        ].mean()
    )

    weekly_average = float(
        recent_week[
            "total_energy"
        ].mean()
    )

    # --------------------------------------------------------
    # Percentage difference
    # --------------------------------------------------------

    def percentage_difference(
        current,
        baseline
    ):

        if baseline == 0:
            return 0

        return (
            (
                current
                - baseline
            )
            / baseline
        ) * 100

    current_vs_same_hour = (
        percentage_difference(
            current_energy,
            same_hour_average
        )
    )

    current_vs_weekday_hour = (
        percentage_difference(
            current_energy,
            same_weekday_hour_average
        )
    )

    current_vs_week = (
        percentage_difference(
            current_energy,
            weekly_average
        )
    )

    # --------------------------------------------------------
    # Historical state
    # --------------------------------------------------------

    if (
        current_vs_same_hour <= -15
        and current_vs_weekday_hour <= -15
    ):

        status = "low"

        insight = (
            "Demand is significantly below both "
            "the historical same-hour pattern and "
            "the typical demand for this weekday."
        )

    elif (
        current_vs_same_hour >= 15
        and current_vs_weekday_hour >= 15
    ):

        status = "high"

        insight = (
            "Demand is significantly above both "
            "the historical same-hour pattern and "
            "the typical demand for this weekday."
        )

    elif current_vs_week <= -10:

        status = "low"

        insight = (
            "Demand is below the recent weekly "
            "baseline, indicating a lower-than-usual "
            "operating period."
        )

    elif current_vs_week >= 10:

        status = "high"

        insight = (
            "Demand is above the recent weekly "
            "baseline, indicating an elevated "
            "operating period."
        )

    else:

        status = "normal"

        insight = (
            "Current demand is behaving within "
            "the normal historical range for "
            "this time."
        )

    return {

        "status":
            status,

        "current_energy":
            round(
                current_energy,
                2
            ),

        "same_hour_average":
            round(
                same_hour_average,
                2
            ),

        "same_hour_median":
            round(
                same_hour_median,
                2
            ),

        "same_weekday_hour_average":
            round(
                same_weekday_hour_average,
                2
            ),

        "weekly_average":
            round(
                weekly_average,
                2
            ),

        "current_vs_same_hour":
            round(
                current_vs_same_hour,
                2
            ),

        "current_vs_weekday_hour":
            round(
                current_vs_weekday_hour,
                2
            ),

        "current_vs_week":
            round(
                current_vs_week,
                2
            ),

        "hour":
            current_hour,

        "day_of_week":
            current_day,

        "timestamp":
            str(
                current_row[
                    "timestamp"
                ]
            ),

        "insight":
            insight,
    }


# ============================================================
# DASHBOARD ENDPOINT
# ============================================================

@app.get("/api/dashboard")
def dashboard():

    if energy_df is None:

        return {
            "error":
                "Energy dataset is not loaded."
        }

    try:

        prediction = (
            generate_prediction()
        )

        current_energy = float(
            energy_df.iloc[-1][
                "total_energy"
            ]
        )

        efficiency = (
            calculate_efficiency()
        )

        carbon = (
            calculate_carbon()
        )

        anomaly = (
            generate_anomaly()
        )

        recommendations = (
            generate_recommendations(
                prediction,
                anomaly
            )
        )

        decision = (
            generate_decision(
                prediction,
                anomaly,
                efficiency
            )
        )

        historical = (
            generate_historical_intelligence(
                energy_df
            )
        )

        return {

            "energy_usage": {

                "value":
                    round(
                        current_energy,
                        2
                    ),

                "unit":
                    "kW",

                "change":
                    0,
            },

            "carbon_footprint": {

                "value":
                    round(
                        carbon,
                        2
                    ),

                "unit":
                    "kg",

                "change":
                    0,
            },

            "efficiency_score": {

                "value":
                    efficiency,

                "unit":
                    "%",

                "change":
                    0,
            },

            "prediction":
                prediction,

            "energy_history":
                generate_energy_history(),

            "recommendations":
                recommendations,

            "anomaly":
                anomaly,

            "decision":
                decision,

            "historical_intelligence":
                historical,
        }

    except Exception as e:

        print(
            "Dashboard error:",
            str(e)
        )

        return {
            "error":
                str(e)
        }


# ============================================================
# PREDICTION ENDPOINT
# ============================================================

@app.get("/api/prediction")
def prediction_endpoint():

    try:

        return {
            "prediction":
                generate_prediction()
        }

    except Exception as e:

        return {
            "error":
                str(e)
        }


# ============================================================
# ANOMALY ENDPOINT
# ============================================================

@app.get("/api/anomaly")
def anomaly_endpoint():

    try:

        return {
            "anomaly":
                generate_anomaly()
        }

    except Exception as e:

        return {
            "error":
                str(e)
        }


# ============================================================
# RECOMMENDATIONS ENDPOINT
# ============================================================

@app.get("/api/recommendations")
def recommendations_endpoint():

    try:

        prediction = (
            generate_prediction()
        )

        anomaly = (
            generate_anomaly()
        )

        return {
            "recommendations":
                generate_recommendations(
                    prediction,
                    anomaly
                )
        }

    except Exception as e:

        return {
            "error":
                str(e)
        }


# ============================================================
# DECISION ENDPOINT
# ============================================================

@app.get("/api/decision")
def decision_endpoint():

    try:

        prediction = (
            generate_prediction()
        )

        anomaly = (
            generate_anomaly()
        )

        efficiency = (
            calculate_efficiency()
        )

        decision = (
            generate_decision(
                prediction,
                anomaly,
                efficiency
            )
        )

        return {
            "decision":
                decision
        }

    except Exception as e:

        return {
            "error":
                str(e)
        }


# ============================================================
# HISTORICAL INTELLIGENCE ENDPOINT
# ============================================================

@app.get("/api/historical")
def historical_endpoint():

    if energy_df is None:

        return {
            "error":
                "Energy dataset is not loaded."
        }

    try:

        historical = (
            generate_historical_intelligence(
                energy_df
            )
        )

        return {
            "historical_intelligence":
                historical
        }

    except Exception as e:

        return {
            "error":
                str(e)
        }


# ============================================================
# OPTIMIZATION ENDPOINT
# ============================================================

@app.get("/api/optimization")
def optimization_endpoint():

    try:

        optimization = optimize()

        return {
            "optimization":
                optimization
        }

    except Exception as e:

        print(
            "Optimization error:",
            str(e)
        )

        return {
            "error":
                str(e)
        }


# ============================================================
# SYSTEM INFORMATION
# ============================================================

@app.get("/api/info")
def info():

    return {

        "project":
            "GreenMind AI",

        "description":
            "AI-powered energy intelligence platform",

        "model":
            "Random Forest",

        "model_loaded":
            model is not None,

        "dataset_loaded":
            energy_df is not None,

        "dataset_rows":
            (
                len(energy_df)
                if energy_df is not None
                else 0
            ),

        "features":
            FEATURES,

        "features_count":
            len(FEATURES),

        "historical_intelligence":
            True,

        "anomaly_detection":
            True,

        "decision_engine":
            True,
    }


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )