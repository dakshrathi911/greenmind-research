from pathlib import Path

import pandas as pd


# ============================================
# GreenMind AI - Dataset Preprocessing
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_FILE = BASE_DIR / "data" / "raw" / "LD2011_2014.txt"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_FILE = PROCESSED_DIR / "hourly_energy.csv"


print("=" * 60)
print("GREENMIND AI - DATA PREPROCESSING")
print("=" * 60)


# --------------------------------------------
# Check input
# --------------------------------------------

if not RAW_FILE.exists():
    raise FileNotFoundError(
        f"Raw dataset not found:\n{RAW_FILE}"
    )

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------
# Load dataset
# --------------------------------------------

print("\n[1/4] Loading raw electricity data...")
print("This may take a little while.")

df = pd.read_csv(
    RAW_FILE,
    sep=";",
    decimal=","
)

print(
    f"Loaded {len(df):,} rows."
)

print(
    f"Found {len(df.columns) - 1} client series."
)


# --------------------------------------------
# Timestamp
# --------------------------------------------

print("\n[2/4] Processing timestamps...")

df = df.rename(
    columns={
        df.columns[0]: "timestamp"
    }
)

df["timestamp"] = pd.to_datetime(
    df["timestamp"]
)

df = df.set_index("timestamp")


# --------------------------------------------
# Aggregate all clients
# --------------------------------------------

print("\n[3/4] Aggregating 370 clients...")

client_columns = [
    column
    for column in df.columns
    if column.startswith("MT_")
]

df["total_energy"] = df[
    client_columns
].sum(axis=1)

# We no longer need the individual client
# columns for the aggregate forecasting model.
total_energy = df[
    ["total_energy"]
].copy()


# --------------------------------------------
# Convert 15-minute data to hourly
# --------------------------------------------

print("Converting 15-minute readings to hourly demand...")

hourly = total_energy.resample(
    "1h"
).mean()

hourly = hourly.reset_index()

hourly["total_energy"] = hourly[
    "total_energy"
].round(3)


# --------------------------------------------
# Save processed dataset
# --------------------------------------------

print("\n[4/4] Saving processed dataset...")

hourly.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\n" + "=" * 60)
print("PREPROCESSING COMPLETE")
print("=" * 60)

print(
    f"\nOutput file:\n{OUTPUT_FILE}"
)

print(
    f"\nHourly observations: {len(hourly):,}"
)

print(
    f"Start: {hourly['timestamp'].min()}"
)

print(
    f"End: {hourly['timestamp'].max()}"
)

print(
    f"Average hourly demand: "
    f"{hourly['total_energy'].mean():,.2f}"
)

print(
    f"Minimum hourly demand: "
    f"{hourly['total_energy'].min():,.2f}"
)

print(
    f"Maximum hourly demand: "
    f"{hourly['total_energy'].max():,.2f}"
)

print("\nFirst 5 rows:")

print(
    hourly.head().to_string(
        index=False
    )
)