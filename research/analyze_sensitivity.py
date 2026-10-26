
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
TRIALS_FILE = RESULTS / "sensitivity_trials.csv"

# Each scenario has 10 paired trials.
# Two-sided 95% t critical value for 9 degrees of freedom.
T_CRITICAL_95_DF9 = 2.262

df = pd.read_csv(TRIALS_FILE)

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
    "baseline_jobs_missed",
    "carbon_aware_jobs_missed",
    "deadline_carbon_jobs_missed",
    "baseline_completion_rate_pct",
    "carbon_aware_completion_rate_pct",
    "deadline_carbon_completion_rate_pct",
]

missing = [col for col in required if col not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

if df.empty:
    raise ValueError("The trial CSV contains no rows.")

# --------------------------------------------------
# 1. Scenario-level means and 95% confidence intervals
# --------------------------------------------------

metrics = [
    "carbon_aware_reduction_pct",
    "deadline_carbon_reduction_pct",
]

rows = []

for keys, group in df.groupby(scenario_cols, dropna=False):
    row = dict(zip(scenario_cols, keys))
    n = len(group)

    for metric in metrics:
        values = group[metric].dropna()
        count = len(values)
        mean = values.mean()

        if count > 1:
            margin = (
                T_CRITICAL_95_DF9
                * values.std(ddof=1)
                / np.sqrt(count)
                if count == 10
                else np.nan
            )
        else:
            margin = np.nan

        row[f"{metric}_mean"] = mean
        row[f"{metric}_ci95_lower"] = (
            mean - margin if pd.notna(margin) else np.nan
        )
        row[f"{metric}_ci95_upper"] = (
            mean + margin if pd.notna(margin) else np.nan
        )
        row[f"{metric}_trials"] = count

        if count != 10:
            print(
                f"WARNING: {keys} has {count} valid values for "
                f"{metric}; CI is only calculated for 10 trials."
            )

    row["trials"] = n
    for col in [
        "baseline_jobs_missed",
        "carbon_aware_jobs_missed",
        "deadline_carbon_jobs_missed",
    ]:
        row[col] = group[col].sum()

    rows.append(row)

scenario_summary = pd.DataFrame(rows)
scenario_summary.to_csv(
    RESULTS / "analysis_scenario_summary.csv", index=False
)

# --------------------------------------------------
# 2. Overall descriptive policy completion summary
# --------------------------------------------------

policies = {
    "Baseline": (
        "baseline_jobs_missed",
        "baseline_completion_rate_pct",
    ),
    "Carbon-aware": (
        "carbon_aware_jobs_missed",
        "carbon_aware_completion_rate_pct",
    ),
    "Deadline-carbon": (
        "deadline_carbon_jobs_missed",
        "deadline_carbon_completion_rate_pct",
    ),
}

overall_rows = []

total_jobs = df["job_count"].sum()

for policy, (miss_col, completion_col) in policies.items():
    missed = df[miss_col].sum()
    completed = total_jobs - missed

    overall_rows.append({
        "policy": policy,
        "scenario_trial_rows": len(df),
        "total_jobs_across_trials": int(total_jobs),
        "jobs_missed": int(missed),
        "jobs_completed_estimate": int(completed),
        "completion_rate_pct_from_missed_jobs": (
            100 * completed / total_jobs if total_jobs else np.nan
        ),
        "mean_reported_completion_rate_pct": df[
            completion_col
        ].mean(),
    })

overall_summary = pd.DataFrame(overall_rows)
overall_summary.to_csv(
    RESULTS / "analysis_policy_summary.csv", index=False
)

# --------------------------------------------------
# 3. Plot mean emissions reduction by carbon variability
# --------------------------------------------------

variability_order = ["low", "standard", "high"]
plot_df = df.copy()
plot_df["carbon_variability"] = pd.Categorical(
    plot_df["carbon_variability"],
    categories=variability_order,
    ordered=True,
)

fig, ax = plt.subplots(figsize=(8, 5))

for policy, metric in [
    ("Carbon-aware", "carbon_aware_reduction_pct"),
    ("Deadline-carbon", "deadline_carbon_reduction_pct"),
]:
    means = (
        plot_df.groupby("carbon_variability", observed=False)[metric]
        .mean()
        .reindex(variability_order)
    )
    ax.plot(
        variability_order,
        means.values,
        marker="o",
        label=policy,
    )

ax.set_title("Mean Emissions Reduction by Carbon Variability")
ax.set_xlabel("Carbon-intensity variability")
ax.set_ylabel("Mean emissions reduction (%)")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(
    RESULTS / "plot_reduction_by_variability.png", dpi=300
)
plt.close(fig)

# --------------------------------------------------
# 4. Plot mean reduction by workload size
# --------------------------------------------------

fig, ax = plt.subplots(figsize=(8, 5))

for policy, metric in [
    ("Carbon-aware", "carbon_aware_reduction_pct"),
    ("Deadline-carbon", "deadline_carbon_reduction_pct"),
]:
    means = (
        df.groupby("job_count")[metric]
        .mean()
        .sort_index()
    )
    ax.plot(
        means.index,
        means.values,
        marker="o",
        label=policy,
    )

ax.set_title("Mean Emissions Reduction by Workload Size")
ax.set_xlabel("Number of jobs")
ax.set_ylabel("Mean emissions reduction (%)")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig(
    RESULTS / "plot_reduction_by_workload.png", dpi=300
)
plt.close(fig)

# --------------------------------------------------
# 5. Plot missed jobs by hourly capacity
# --------------------------------------------------

missed_by_capacity = (
    df.groupby("hourly_capacity")[
        [
            "baseline_jobs_missed",
            "carbon_aware_jobs_missed",
            "deadline_carbon_jobs_missed",
        ]
    ]
    .sum()
    .sort_index()
)

fig, ax = plt.subplots(figsize=(8, 5))
missed_by_capacity.plot(kind="bar", ax=ax)

ax.set_title("Total Missed Jobs by Hourly Capacity")
ax.set_xlabel("Hourly capacity (work units)")
ax.set_ylabel("Missed jobs across scenario trials")
ax.legend([
    "Baseline",
    "Carbon-aware",
    "Deadline-carbon",
])
ax.grid(True, axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(
    RESULTS / "plot_missed_jobs_by_capacity.png", dpi=300
)
plt.close(fig)

# --------------------------------------------------
# 6. Print a concise report
# --------------------------------------------------

print("\nSENSITIVITY ANALYSIS")
print(f"Trial rows: {len(df)}")
print(f"Scenario combinations: {len(scenario_summary)}")
print(f"Total jobs represented across rows: {int(total_jobs)}")

print("\nOVERALL POLICY SUMMARY")
print(overall_summary.round(3).to_string(index=False))

print("\nMEAN SCENARIO-LEVEL REDUCTIONS")
print(
    scenario_summary[
        [
            "carbon_aware_reduction_pct_mean",
            "deadline_carbon_reduction_pct_mean",
        ]
    ].mean().round(3).to_string()
)

print("\nLOWEST DEADLINE-CARBON REDUCTION SCENARIOS")
print(
    scenario_summary.nsmallest(
        10, "deadline_carbon_reduction_pct_mean"
    )[
        scenario_cols
        + [
            "carbon_aware_reduction_pct_mean",
            "deadline_carbon_reduction_pct_mean",
            "deadline_carbon_reduction_pct_ci95_lower",
            "deadline_carbon_reduction_pct_ci95_upper",
            "carbon_aware_jobs_missed",
            "deadline_carbon_jobs_missed",
        ]
    ].round(3).to_string(index=False)
)

print("\nFILES CREATED")
for name in [
    "analysis_scenario_summary.csv",
    "analysis_policy_summary.csv",
    "plot_reduction_by_variability.png",
    "plot_reduction_by_workload.png",
    "plot_missed_jobs_by_capacity.png",
]:
    print(RESULTS / name)
