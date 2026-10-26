
from pathlib import Path

import numpy as np
import pandas as pd

RESULTS = Path(__file__).resolve().parent / "results"
INPUT = RESULTS / "paired_policy_comparison.csv"
OUTPUT = RESULTS / "paired_policy_comparison_corrected.csv"

df = pd.read_csv(INPUT)

p_col = "paired_t_test_p_value"
p = pd.to_numeric(df[p_col], errors="coerce")
valid = p.notna()
p_valid = p[valid].to_numpy()

# Benjamini-Hochberg FDR-adjusted p-values.
m = len(p_valid)
adjusted = np.full(m, np.nan)

if m:
    order = np.argsort(p_valid)
    sorted_p = p_valid[order]
    ranks = np.arange(1, m + 1)

    sorted_adjusted = sorted_p * m / ranks

    # Enforce monotonicity of adjusted p-values.
    sorted_adjusted = np.minimum.accumulate(
        sorted_adjusted[::-1]
    )[::-1]
    sorted_adjusted = np.clip(sorted_adjusted, 0, 1)

    adjusted[order] = sorted_adjusted

df["fdr_adjusted_p_value"] = np.nan
df.loc[valid, "fdr_adjusted_p_value"] = adjusted

df["significant_unadjusted_0_05"] = (
    df[p_col] < 0.05
)
df["significant_fdr_0_05"] = (
    df["fdr_adjusted_p_value"] < 0.05
)

df.to_csv(OUTPUT, index=False)

diff_col = "mean_deadline_minus_carbon_aware_pp"

print("\nMULTIPLE-TESTING CORRECTION")
print("Scenarios with valid p-values:", m)
print(
    "Significant before correction:",
    int(df["significant_unadjusted_0_05"].sum()),
)
print(
    "Significant after Benjamini-Hochberg FDR correction:",
    int(df["significant_fdr_0_05"].sum()),
)

print("\nCORRECTED SIGNIFICANT SCENARIOS")
cols = [
    "pue_scenario",
    "carbon_variability",
    "job_count",
    "hourly_capacity",
    diff_col,
    p_col,
    "fdr_adjusted_p_value",
]

significant = df[df["significant_fdr_0_05"]].sort_values(
    "fdr_adjusted_p_value"
)

if significant.empty:
    print("No scenarios remain significant at FDR 0.05.")
else:
    print(significant[cols].round(4).to_string(index=False))

print("\nSAVED:", OUTPUT)
