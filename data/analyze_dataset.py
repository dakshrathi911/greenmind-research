from pathlib import Path
import pandas as pd


# ============================================
# GreenMind AI - Dataset Analysis
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "raw" / "LD2011_2014.txt"


print("=" * 60)
print("GREENMIND AI - ELECTRICITY DATASET ANALYSIS")
print("=" * 60)

print(f"\nDataset:")
print(DATA_FILE)

if not DATA_FILE.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_FILE}"
    )


# --------------------------------------------
# Read header only
# --------------------------------------------

print("\n[1/5] Reading dataset structure...")

header = pd.read_csv(
    DATA_FILE,
    sep=";",
    nrows=0
)

print(f"Number of columns: {len(header.columns)}")

client_columns = [
    column
    for column in header.columns
    if column.startswith("MT_")
]

print(f"Number of client series: {len(client_columns)}")


# --------------------------------------------
# Read timestamps + data
# --------------------------------------------

print("\n[2/5] Loading dataset...")

df = pd.read_csv(
    DATA_FILE,
    sep=";",
    decimal=","
)

# Rename first column
df = df.rename(
    columns={
        df.columns[0]: "timestamp"
    }
)

df["timestamp"] = pd.to_datetime(
    df["timestamp"]
)

print("Dataset loaded successfully.")


# --------------------------------------------
# Basic information
# --------------------------------------------

print("\n[3/5] Basic information")

print("-" * 40)

print(
    f"Rows: {len(df):,}"
)

print(
    f"Clients: {len(client_columns):,}"
)

print(
    f"Start: {df['timestamp'].min()}"
)

print(
    f"End: {df['timestamp'].max()}"
)

print(
    f"Duration: "
    f"{df['timestamp'].max() - df['timestamp'].min()}"
)


# --------------------------------------------
# Missing values
# --------------------------------------------

print("\n[4/5] Data quality")

print("-" * 40)

missing_values = df[client_columns].isna().sum().sum()

total_values = (
    len(df) * len(client_columns)
)

missing_percentage = (
    missing_values / total_values
) * 100

print(
    f"Missing values: {missing_values:,}"
)

print(
    f"Missing percentage: "
    f"{missing_percentage:.4f}%"
)


# --------------------------------------------
# Zero values
# --------------------------------------------

zero_values = (
    (df[client_columns] == 0)
    .sum()
    .sum()
)

zero_percentage = (
    zero_values / total_values
) * 100

print(
    f"Zero values: {zero_values:,}"
)

print(
    f"Zero percentage: "
    f"{zero_percentage:.2f}%"
)


# --------------------------------------------
# Aggregate demand
# --------------------------------------------

print("\n[5/5] Aggregate energy analysis")

print("-" * 40)

df["total_energy"] = df[
    client_columns
].sum(axis=1)

print(
    f"Average aggregate demand: "
    f"{df['total_energy'].mean():,.2f}"
)

print(
    f"Minimum aggregate demand: "
    f"{df['total_energy'].min():,.2f}"
)

print(
    f"Maximum aggregate demand: "
    f"{df['total_energy'].max():,.2f}"
)


# --------------------------------------------
# Highest-demand clients
# --------------------------------------------

print("\nTop 10 clients by average demand:")

client_means = (
    df[client_columns]
    .mean()
    .sort_values(
        ascending=False
    )
)

for client, value in client_means.head(10).items():

    print(
        f"{client}: {value:,.2f}"
    )


# --------------------------------------------
# Dataset sample
# --------------------------------------------

print("\nFirst 5 timestamps:")

print(
    df[
        ["timestamp", "total_energy"]
    ].head().to_string(
        index=False
    )
)


print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)