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


print("=" * 60)
print("GREENMIND AI - FEATURE ENGINEERING")
print("=" * 60)


# --------------------------------------------
# Check input
# --------------------------------------------

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Processed dataset not found:\n{INPUT_FILE}"
    )


# --------------------------------------------
# Load hourly data
# --------------------------------------------

print("\n[1/5] Loading hourly energy data...")

df = pd.read_csv(
    INPUT_FILE,
    parse_dates=["timestamp"]
)

df = df.sort_values(
    "timestamp"
).reset_index(drop=True)

print(
    f"Loaded {len(df):,} hourly observations."
)


# --------------------------------------------
# Calendar features
# --------------------------------------------

print("\n[2/5] Creating calendar features...")

df["hour"] = df["timestamp"].dt.hour

df["day_of_week"] = (
    df["timestamp"].dt.dayofweek
)

df["day_of_month"] = (
    df["timestamp"].dt.day
)

df["month"] = (
    df["timestamp"].dt.month
)

df["is_weekend"] = (
    df["day_of_week"] >= 5
).astype(int)


# --------------------------------------------
# Lag features
# --------------------------------------------

print("\n[3/5] Creating historical lag features...")

# Previous hour
df["lag_1"] = (
    df["total_energy"].shift(1)
)

# Same hour on the previous day
df["lag_24"] = (
    df["total_energy"].shift(24)
)

# Same hour one week ago
df["lag_168"] = (
    df["total_energy"].shift(168)
)


# --------------------------------------------
# Rolling features
# --------------------------------------------

print("\n[4/5] Creating rolling statistics...")

# Previous 24 hours
df["rolling_mean_24"] = (
    df["total_energy"]
    .shift(1)
    .rolling(window=24)
    .mean()
)

df["rolling_std_24"] = (
    df["total_energy"]
    .shift(1)
    .rolling(window=24)
    .std()
)

# Previous 7 days
df["rolling_mean_168"] = (
    df["total_energy"]
    .shift(1)
    .rolling(window=168)
    .mean()
)


# --------------------------------------------
# Target
# --------------------------------------------

print("Creating prediction target...")

# The model will predict the NEXT hour.
df["target"] = (
    df["total_energy"].shift(-1)
)


# --------------------------------------------
# Remove rows that cannot have complete
# historical features
# --------------------------------------------

print("Removing incomplete feature rows...")

df = df.dropna().reset_index(
    drop=True
)


# --------------------------------------------
# Select columns
# --------------------------------------------

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

df = df[feature_columns]


# --------------------------------------------
# Save
# --------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# --------------------------------------------
# Summary
# --------------------------------------------

print("\n" + "=" * 60)
print("FEATURE ENGINEERING COMPLETE")
print("=" * 60)

print(
    f"\nOutput file:\n{OUTPUT_FILE}"
)

print(
    f"\nTraining observations: "
    f"{len(df):,}"
)

print(
    f"Features: "
    f"{len(feature_columns) - 2}"
)

print(
    f"\nDate range:"
)

print(
    f"{df['timestamp'].min()} "
    f"→ "
    f"{df['timestamp'].max()}"
)

print("\nColumns:")

for column in df.columns:
    print(f"  - {column}")

print("\nFirst 5 rows:")

print(
    df.head().to_string(
        index=False
    )
)