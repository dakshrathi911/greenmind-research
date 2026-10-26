from pathlib import Path

import pandas as pd


# ============================================
# GreenMind AI - Feature Engineering
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "hourly_energy.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "energy_features.csv"
)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build leakage-safe features for a one-hour-ahead energy forecast.

    Each input row at time t predicts the energy value at t+1 hour.
    Therefore calendar fields describe t+1, while lag and rolling
    features use only observations available through time t.
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    target_timestamp = df["timestamp"] + pd.Timedelta(hours=1)
    df["hour"] = target_timestamp.dt.hour
    df["day_of_week"] = target_timestamp.dt.day_of_week
    df["day_of_month"] = target_timestamp.dt.day
    df["month"] = target_timestamp.dt.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # At time t, the latest observed value is the one-hour-ahead
    # target's lag_1. The 24h and 168h lags are aligned to t+1.
    df["lag_1"] = df["total_energy"]
    df["lag_24"] = df["total_energy"].shift(23)
    df["lag_168"] = df["total_energy"].shift(167)

    # Rolling windows include the latest known observation at t.
    df["rolling_mean_24"] = df["total_energy"].rolling(window=24).mean()
    df["rolling_std_24"] = df["total_energy"].rolling(window=24).std()
    df["rolling_mean_168"] = df["total_energy"].rolling(window=168).mean()

    # Predict the next observed hour.
    df["target"] = df["total_energy"].shift(-1)

    feature_columns = [
        "timestamp",
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
        "target",
    ]

    return df[feature_columns].dropna().reset_index(drop=True)


def main() -> None:
    print("=" * 60)
    print("GREENMIND AI - FEATURE ENGINEERING")
    print("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Processed dataset not found:\n{INPUT_FILE}")

    print("\n[1/5] Loading hourly energy data...")
    source = pd.read_csv(INPUT_FILE, parse_dates=["timestamp"])
    print(f"Loaded {len(source):,} hourly observations.")

    print("\n[2/5] Creating next-hour calendar features...")
    print("\n[3/5] Creating correctly aligned historical lag features...")
    print("\n[4/5] Creating rolling statistics and prediction target...")
    features = build_features(source)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(OUTPUT_FILE, index=False)

    print("\n" + "=" * 60)
    print("FEATURE ENGINEERING COMPLETE")
    print("=" * 60)
    print(f"\nOutput file:\n{OUTPUT_FILE}")
    print(f"\nTraining observations: {len(features):,}")
    print(f"Features: {len(features.columns) - 2}")
    print(f"\nDate range:\n{features['timestamp'].min()} → {features['timestamp'].max()}")
    print("\nColumns:")
    for column in features.columns:
        print(f"  - {column}")
    print("\nFirst 5 rows:")
    print(features.head().to_string(index=False))


if __name__ == "__main__":
    main()
