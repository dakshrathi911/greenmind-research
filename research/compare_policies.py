
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

df = pd.read_csv(RESULTS / "sensitivity_trials.csv")

scenario_cols = [
    "pue_scenario",
    "carbon_variability",
    "job_count",
    "hourly_capacity",
]

required = scenario_cols + [
    "seed",
    "carbon_aware_reduction_pct",
    "deadline_carbon_reduction_pct",
    "carbon_aware_jobs_missed",
    "deadline_carbon_jobs_missed",
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

if df.duplicated(scenario_cols + ["seed"]).any():
    raise ValueError("Duplicate scenario/seed rows found.")

df["deadline_minus_carbon_aware_pp"] = (
    df["deadline_carbon_reduction_pct"]
    - df["carbon_aware_reduction_pct"]
)

df["missed_jobs_difference"] = (
    df["deadline_carbon_jobs_missed"]
    - df["carbon_aware_jobs_missed"]
)

rows = []

for keys, g in df.groupby(scenario_cols, dropna=False):
    differences = g["deadline_minus_carbon_aware_pp"].dropna()
    n = len(differences)

    mean_diff = differences.mean()
    sd_diff = differences.std(ddof=1) if n > 1 else np.nan
    se = sd_diff / np.sqrt(n) if n > 1 else np.nan

    if n > 1:
        critical = stats.t.ppf(0.975, df=n - 1)
        lower = mean_diff - critical * se
        upper = mean_diff + critical * se
        p_value = (
            stats.ttest_1samp(differences, popmean=0).pvalue
            if sd_diff > 0
            else (1.0 if mean_diff == 0 else 0.0)
        )
    else:
        lower = upper = p_value = np.nan

    missed_diff = g["missed_jobs_difference"]

    rows.append({
        **dict(zip(scenario_cols, keys)),
        "paired_trials": n,
        "mean_deadline_minus_carbon_aware_pp": mean_diff,
        "difference_ci95_lower_pp": lower,
        "difference_ci95_upper_pp": upper,
        "paired_t_test_p_value": p_value,
        "carbon_aware_jobs_missed": int(
            g["carbon_aware_jobs_missed"].sum()
        ),
        "deadline_carbon_jobs_missed": int(
            g["deadline_carbon_jobs_missed"].sum()
        ),
        "missed_jobs_deadline_minus_carbon_aware": int(
            missed_diff.sum()
        ),
    })

summary = pd.DataFrame(rows)

# Descriptive scenario counts; confidence intervals include zero
# when the observed difference is not clearly distinguishable from zero.
summary["ci_excludes_zero"] = (
    (summary["difference_ci95_lower_pp"] > 0)
    | (summary["difference_ci95_upper_pp"] < 0)
)

summary.to_csv(
    RESULTS / "paired_policy_comparison.csv",
    index=False,
)

print("\nPAIRED POLICY COMPARISON")
print("Positive difference = deadline-carbon has greater emissions reduction.")
print("Negative difference = carbon-aware has greater emissions reduction.")

print("\nSCENARIO COUNTS")
print("Total scenarios:", len(summary))
print(
    "Deadline-carbon higher, CI excludes zero:",
    int(
        (
            (summary["mean_deadline_minus_carbon_aware_pp"] > 0)
            & summary["ci_excludes_zero"]
        ).sum()
    ),
)
print(
    "Carbon-aware higher, CI excludes zero:",
    int(
        (
            (summary["mean_deadline_minus_carbon_aware_pp"] < 0)
            & summary["ci_excludes_zero"]
        ).sum()
    ),
)
print(
    "CI includes zero:",
    int((~summary["ci_excludes_zero"]).sum()),
)

print("\nAVERAGE SCENARIO-LEVEL DIFFERENCE")
print(
    summary["mean_deadline_minus_carbon_aware_pp"]
    .mean()
    .round(4),
    "percentage points",
)

print("\nSCENARIOS WITH LARGEST DEADLINE-CARBON ADVANTAGE")
print(
    summary.nlargest(
        5, "mean_deadline_minus_carbon_aware_pp"
    )[
        scenario_cols
        + [
            "mean_deadline_minus_carbon_aware_pp",
            "difference_ci95_lower_pp",
            "difference_ci95_upper_pp",
            "paired_t_test_p_value",
            "missed_jobs_deadline_minus_carbon_aware",
        ]
    ].round(4).to_string(index=False)
)

print("\nSCENARIOS WITH LARGEST CARBON-AWARE ADVANTAGE")
print(
    summary.nsmallest(
        5, "mean_deadline_minus_carbon_aware_pp"
    )[
        scenario_cols
        + [
            "mean_deadline_minus_carbon_aware_pp",
            "difference_ci95_lower_pp",
            "difference_ci95_upper_pp",
            "paired_t_test_p_value",
            "missed_jobs_deadline_minus_carbon_aware",
        ]
    ].round(4).to_string(index=False)
)

print("\nSaved:", RESULTS / "paired_policy_comparison.csv")

