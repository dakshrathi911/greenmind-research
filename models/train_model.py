from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================
# GreenMind AI - Energy Forecasting Model
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "energy_features.csv"
)

MODEL_DIR = BASE_DIR / "models"
MODEL_FILE = MODEL_DIR / "energy_forecaster.joblib"


print("=" * 60)
print("GREENMIND AI - ENERGY FORECASTING MODEL")
print("=" * 60)


# --------------------------------------------
# Check dataset
# --------------------------------------------

if not DATA_FILE.exists():
    raise FileNotFoundError(
        f"Feature dataset not found:\n{DATA_FILE}"
    )

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------
# Load data
# --------------------------------------------

print("\n[1/6] Loading feature dataset...")

df = pd.read_csv(
    DATA_FILE,
    parse_dates=["timestamp"]
)

df = df.sort_values(
    "timestamp"
).reset_index(drop=True)

print(
    f"Total observations: {len(df):,}"
)


# --------------------------------------------
# Define features
# --------------------------------------------

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

TARGET = "target"


# --------------------------------------------
# Chronological train/test split
# --------------------------------------------

print("\n[2/6] Creating chronological train/test split...")

split_index = int(
    len(df) * 0.80
)

train_df = df.iloc[
    :split_index
].copy()

test_df = df.iloc[
    split_index:
].copy()

X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]

print(
    f"Training observations: {len(train_df):,}"
)

print(
    f"Testing observations: {len(test_df):,}"
)

print(
    f"\nTraining period:"
)

print(
    f"{train_df['timestamp'].min()} "
    f"→ "
    f"{train_df['timestamp'].max()}"
)

print(
    f"\nTesting period:"
)

print(
    f"{test_df['timestamp'].min()} "
    f"→ "
    f"{test_df['timestamp'].max()}"
)


# --------------------------------------------
# Baseline
# --------------------------------------------

print("\n[3/6] Evaluating naive baseline...")

# A simple forecasting strategy:
# next hour ≈ same hour yesterday

baseline_predictions = test_df["lag_24"]

baseline_mae = mean_absolute_error(
    y_test,
    baseline_predictions
)

baseline_rmse = mean_squared_error(
    y_test,
    baseline_predictions
) ** 0.5

baseline_r2 = r2_score(
    y_test,
    baseline_predictions
)

print(
    f"Baseline MAE:  {baseline_mae:,.2f}"
)

print(
    f"Baseline RMSE: {baseline_rmse:,.2f}"
)

print(
    f"Baseline R²:   {baseline_r2:.4f}"
)


# --------------------------------------------
# Train Random Forest
# --------------------------------------------

print("\n[4/6] Training Random Forest...")

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=20,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)

print("Random Forest training complete.")


# --------------------------------------------
# Predictions
# --------------------------------------------

print("\n[5/6] Evaluating model...")

predictions = model.predict(
    X_test
)


# --------------------------------------------
# Metrics
# --------------------------------------------

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5

r2 = r2_score(
    y_test,
    predictions
)


print("\nRandom Forest results:")
print("-" * 40)

print(
    f"MAE:  {mae:,.2f}"
)

print(
    f"RMSE: {rmse:,.2f}"
)

print(
    f"R²:   {r2:.4f}"
)


# --------------------------------------------
# Compare against baseline
# --------------------------------------------

print("\nModel comparison:")
print("-" * 40)

print(
    f"Baseline MAE:       {baseline_mae:,.2f}"
)

print(
    f"Random Forest MAE:   {mae:,.2f}"
)

if mae < baseline_mae:

    improvement = (
        (baseline_mae - mae)
        / baseline_mae
    ) * 100

    print(
        f"\nRandom Forest improves "
        f"MAE by {improvement:.2f}%."
    )

else:

    print(
        "\nRandom Forest did not beat "
        "the baseline."
    )


# --------------------------------------------
# Feature importance
# --------------------------------------------

print("\nFeature importance:")
print("-" * 40)

importance = pd.Series(
    model.feature_importances_,
    index=FEATURES
).sort_values(
    ascending=False
)

for feature, value in importance.items():

    print(
        f"{feature:<20} "
        f"{value:.4f}"
    )


# --------------------------------------------
# Save model
# --------------------------------------------

print("\n[6/6] Saving trained model...")

joblib.dump(
    model,
    MODEL_FILE
)

print(
    f"Model saved to:\n{MODEL_FILE}"
)


# --------------------------------------------
# Save evaluation results
# --------------------------------------------

results = pd.DataFrame(
    [
        {
            "model": "Naive Baseline",
            "MAE": baseline_mae,
            "RMSE": baseline_rmse,
            "R2": baseline_r2,
        },
        {
            "model": "Random Forest",
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
        },
    ]
)

RESULTS_FILE = (
    MODEL_DIR
    / "model_results.csv"
)

results.to_csv(
    RESULTS_FILE,
    index=False
)

print(
    f"Results saved to:\n{RESULTS_FILE}"
)


print("\n" + "=" * 60)
print("MODEL TRAINING COMPLETE")
print("=" * 60)