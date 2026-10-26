"""
GreenMind AI: repeated-seed evaluation of carbon-aware scheduling.

Runs paired trials: each seed uses the same synthetic workload and carbon
profile for both policies. Outputs trial-level metrics and descriptive
statistics. Inputs remain synthetic; results are not real-world measurements.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from carbon_experiment import (
    HOURS,
    generate_carbon_intensity,
    generate_workload,
    run_policy,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "results"
SEEDS = range(30)
JOB_COUNT = 240


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trial_rows = []
    policy_rows = []
    reductions = []

    for seed in SEEDS:
        jobs = generate_workload(seed=seed, count=JOB_COUNT)
        carbon = generate_carbon_intensity(seed=seed + 1)

        baseline = run_policy(jobs, carbon, "baseline")
        aware = run_policy(jobs, carbon, "carbon_aware")

        base_emissions = float(baseline["emissions_kg_co2"])
        aware_emissions = float(aware["emissions_kg_co2"])
        reduction_pct = (
            100.0 * (base_emissions - aware_emissions) / base_emissions
            if base_emissions > 0
            else 0.0
        )
        reductions.append(reduction_pct)

        for result in (baseline, aware):
            policy_rows.append(
                {
                    "seed": seed,
                    "policy": result["policy"],
                    "jobs_total": result["jobs_total"],
                    "jobs_completed": result["jobs_completed"],
                    "jobs_missed": result["jobs_missed"],
                    "completion_rate_pct": result["completion_rate_pct"],
                    "energy_kwh": result["energy_kwh"],
                    "emissions_kg_co2": result["emissions_kg_co2"],
                }
            )

        trial_rows.append(
            {
                "seed": seed,
                "jobs_total": JOB_COUNT,
                "baseline_jobs_missed": baseline["jobs_missed"],
                "carbon_aware_jobs_missed": aware["jobs_missed"],
                "baseline_completion_rate_pct": baseline["completion_rate_pct"],
                "carbon_aware_completion_rate_pct": aware["completion_rate_pct"],
                "baseline_energy_kwh": baseline["energy_kwh"],
                "carbon_aware_energy_kwh": aware["energy_kwh"],
                "baseline_emissions_kg_co2": base_emissions,
                "carbon_aware_emissions_kg_co2": aware_emissions,
                "emissions_reduction_pct": reduction_pct,
            }
        )

    trials = pd.DataFrame(trial_rows)
    policies = pd.DataFrame(policy_rows)
    reduction_values = trials["emissions_reduction_pct"]

    summary_rows = []
    for policy, group in policies.groupby("policy", sort=False):
        summary_rows.append(
            {
                "policy": policy,
                "trials": len(group),
                "mean_emissions_kg_co2": group["emissions_kg_co2"].mean(),
                "std_emissions_kg_co2": group["emissions_kg_co2"].std(ddof=1),
                "mean_energy_kwh": group["energy_kwh"].mean(),
                "mean_completion_rate_pct": group["completion_rate_pct"].mean(),
                "total_jobs_missed": int(group["jobs_missed"].sum()),
            }
        )

    overall = pd.DataFrame(
        [
            {
                "trials": len(trials),
                "mean_emissions_reduction_pct": reduction_values.mean(),
                "std_emissions_reduction_pct": reduction_values.std(ddof=1),
                "median_emissions_reduction_pct": reduction_values.median(),
                "min_emissions_reduction_pct": reduction_values.min(),
                "max_emissions_reduction_pct": reduction_values.max(),
                "trials_with_positive_reduction": int((reduction_values > 0).sum()),
                "trials_with_positive_reduction_pct": 100.0 * (reduction_values > 0).mean(),
                "mean_baseline_jobs_missed": trials["baseline_jobs_missed"].mean(),
                "mean_carbon_aware_jobs_missed": trials["carbon_aware_jobs_missed"].mean(),
            }
        ]
    )

    trials.to_csv(OUTPUT_DIR / "multi_seed_trials.csv", index=False)
    policies.to_csv(OUTPUT_DIR / "multi_seed_policy_metrics.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(
        OUTPUT_DIR / "multi_seed_policy_summary.csv", index=False
    )
    overall.to_csv(OUTPUT_DIR / "multi_seed_overall_summary.csv", index=False)

    print("\nGREENMIND AI — MULTI-SEED CARBON SCHEDULING EVALUATION")
    print("=" * 62)
    print(f"Trials: {len(trials)} | Jobs per trial: {JOB_COUNT}")
    print("\nPer-policy summary:")
    print(pd.DataFrame(summary_rows).round(4).to_string(index=False))
    print("\nPaired emissions-reduction summary:")
    print(overall.round(4).to_string(index=False))
    print(f"\nResults saved in: {OUTPUT_DIR}")
    print("  - multi_seed_trials.csv")
    print("  - multi_seed_policy_metrics.csv")
    print("  - multi_seed_policy_summary.csv")
    print("  - multi_seed_overall_summary.csv")
    print("\nInterpretation note: all inputs are synthetic. Statistics describe")
    print("these simulated trials and do not establish real-world savings.")


if __name__ == "__main__":
    main()
