from pathlib import Path

import pandas as pd


# ============================================================
# GREENMIND AI - PEAK & ANOMALY DETECTION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "hourly_energy.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

def load_energy_data():

    if not DATA_FILE.exists():

        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["timestamp"],
    )

    df = (
        df
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    return df


# ============================================================
# DETECT ANOMALY
# ============================================================

def detect_anomaly(df):

    if len(df) < 168:

        raise ValueError(
            "At least 168 hourly observations "
            "are required."
        )

    current = df.iloc[-1]

    current_energy = float(
        current["total_energy"]
    )

    current_hour = int(
        current["timestamp"].hour
    )

    current_day = int(
        current["timestamp"].dayofweek
    )

    # --------------------------------------------------------
    # Historical data for the same hour
    # --------------------------------------------------------

    same_hour = df[
        df["timestamp"].dt.hour == current_hour
    ].iloc[:-1]

    same_hour = same_hour.tail(28)

    if len(same_hour) < 7:

        same_hour = df.iloc[-168:-1]

    # --------------------------------------------------------
    # Expected demand
    # --------------------------------------------------------

    expected = float(
        same_hour["total_energy"].median()
    )

    # --------------------------------------------------------
    # Historical variability
    # --------------------------------------------------------

    std = float(
        same_hour["total_energy"].std()
    )

    if std <= 0:

        std = max(
            expected * 0.05,
            1
        )

    # --------------------------------------------------------
    # Deviation
    # --------------------------------------------------------

    deviation = (
        (current_energy - expected)
        / expected
    ) * 100

    # --------------------------------------------------------
    # Z-score
    # --------------------------------------------------------

    z_score = (
        current_energy - expected
    ) / std

    absolute_z = abs(z_score)

    # --------------------------------------------------------
    # Anomaly severity
    # --------------------------------------------------------

    if absolute_z >= 3:

        severity = "critical"
        detected = True

    elif absolute_z >= 2:

        severity = "high"
        detected = True

    elif absolute_z >= 1.5:

        severity = "medium"
        detected = True

    else:

        severity = "normal"
        detected = False

    # --------------------------------------------------------
    # Peak detection
    # --------------------------------------------------------

    recent_week = df.tail(168)

    weekly_peak = float(
        recent_week["total_energy"].max()
    )

    peak_threshold = float(
        recent_week["total_energy"].quantile(0.90)
    )

    is_peak = (
        current_energy >= peak_threshold
    )

    # --------------------------------------------------------
    # Human-readable message
    # --------------------------------------------------------

    if severity == "critical":

        if deviation > 0:

            message = (
                "Critical energy anomaly detected. "
                "Current demand is far above the "
                "historical pattern for this period."
            )

        else:

            message = (
                "Critical energy anomaly detected. "
                "Current demand is far below the "
                "historical pattern for this period."
            )

    elif severity == "high":

        if deviation > 0:

            message = (
                "High energy anomaly detected. "
                "Current demand is significantly above "
                "the expected pattern."
            )

        else:

            message = (
                "High energy anomaly detected. "
                "Current demand is significantly below "
                "the expected pattern."
            )

    elif severity == "medium":

        if deviation > 0:

            message = (
                "Moderate energy deviation detected. "
                "Current demand is above the historical "
                "pattern."
            )

        else:

            message = (
                "Moderate energy deviation detected. "
                "Current demand is below the historical "
                "pattern."
            )

    elif is_peak:

        message = (
            "Energy demand is currently within a "
            "high-demand peak period."
        )

    else:

        message = (
            "Energy demand is within the expected "
            "historical range."
        )

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    if severity in ["critical", "high"]:

        if deviation > 0:

            recommendation = (
                "Review non-critical workloads and "
                "investigate unusual energy consumption."
            )

        else:

            recommendation = (
                "Consider scheduling flexible or "
                "energy-intensive workloads during this "
                "lower-demand period."
            )

    elif severity == "medium":

        if deviation > 0:

            recommendation = (
                "Monitor the elevated demand and review "
                "recent workload changes."
            )

        else:

            recommendation = (
                "Consider using this lower-demand period "
                "for flexible workloads where appropriate."
            )

    elif is_peak:

        recommendation = (
            "Avoid starting additional flexible "
            "workloads during this peak period."
        )

    else:

        recommendation = (
            "No immediate action is required."
        )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "detected":
            detected,

        "severity":
            severity,

        "score":
            round(
                absolute_z,
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
                expected,
                2
            ),

        "deviation":
            round(
                deviation,
                2
            ),

        "is_peak":
            bool(
                is_peak
            ),

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
            current_hour,

        "day_of_week":
            current_day,

        "timestamp":
            str(
                current["timestamp"]
            ),

        "message":
            message,

        "recommendation":
            recommendation,
    }


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print(
        "GREENMIND AI - PEAK & ANOMALY DETECTION"
    )
    print("=" * 60)

    print()
    print("[1/3] Loading electricity dataset...")

    data = load_energy_data()

    print(
        f"Loaded {len(data):,} hourly observations."
    )

    print()
    print("[2/3] Analysing current demand...")

    result = detect_anomaly(data)

    print()
    print("[3/3] Detection result")
    print("-" * 40)

    print(
        f"Current demand: "
        f"{result['current_energy']:,.2f} kW"
    )

    print(
        f"Expected demand: "
        f"{result['expected_energy']:,.2f} kW"
    )

    print(
        f"Deviation: "
        f"{result['deviation']:+.2f}%"
    )

    print(
        f"Z-score: "
        f"{result['z_score']:.2f}"
    )

    print(
        f"Anomaly score: "
        f"{result['score']:.2f}"
    )

    print(
        f"Severity: "
        f"{result['severity'].upper()}"
    )

    print(
        f"Peak detected: "
        f"{'YES' if result['is_peak'] else 'NO'}"
    )

    print()
    print("AI message:")

    print(
        result["message"]
    )

    print()
    print("Recommendation:")

    print(
        result["recommendation"]
    )

    print()
    print("=" * 60)
    print(
        "ANOMALY DETECTION COMPLETE"
    )
    print("=" * 60)