"""
GreenMind AI: repeated-seed evaluation of carbon-aware scheduling.

Runs paired trials using identical synthetic workloads and carbon profiles
for all three policies. Results are illustrative, not real-world measurements.
"""

from pathlib import Path

import pandas as pd

from carbon_experiment import (
    generate_carbon_intensity,
    generate_pue_profile,
    generate_workload,
    run_policy,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "results"
SEEDS = range(30)
JOB_COUNT = 240
POLICY_NAMES = ("baseline", "carbon_aware", "deadline_carbon")


def reduction_pct(baseline_emissions: float, policy_emissions: float) -> float:
    """Return emissions reduction relative to baseline, as a percentage."""
    if baseline_emissions <= 0:
        return 0.0
    return 100.0 * (baseline_emissions - policy_emissions) / baseline_emissions


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trial_rows = []
    policy_rows = []

    for seed in SEEDS:
        jobs = generate_workload(seed=seed, count=JOB_COUNT)
        carbon = generate_carbon_intensity(seed=seed + 1)
        pue = generate_pue_profile(seed=seed + 2)
        results = {
            policy: run_policy(jobs, carbon, policy, pue)
            for policy in POLICY_NAMES
        }
        baseline = results["baseline"]
        aware = results["carbon_aware"]
        deadline = results["deadline_carbon"]
        base_emissions = float(baseline["emissions_kg_co2"])
        aware_emissions = float(aware["emissions_kg_co2"])
        deadline_emissions = float(deadline["emissions_kg_co2"])
        aware_reduction = reduction_pct(base_emissions, aware_emissions)
        deadline_reduction = reduction_pct(base_emissions, deadline_emissions)

        for result in results.values():
            policy_rows.append(
                {
                    "seed": seed,
                    "policy": result["policy"],
                    "jobs_total": result["jobs_total"],
                    "jobs_completed": result["jobs_completed"],
                    "jobs_missed": result["jobs_missed"],
                    "completion_rate_pct": result["completion_rate_pct"],
                    "total_work_units": result["total_work_units"],
                    "completed_work_units": result["completed_work_units"],
                    "missed_work_units": result["missed_work_units"],
                    "work_completion_rate_pct": result["work_completion_rate_pct"],
                    "energy_kwh": result["energy_kwh"],
                    "emissions_kg_co2": result["emissions_kg_co2"],
                    "emissions_kg_co2_per_completed_work_unit": result[
                        "emissions_kg_co2_per_completed_work_unit"
                    ],
                }
            )

        trial_rows.append(
            {
                "seed": seed,
                "jobs_total": JOB_COUNT,
                "total_work_units": baseline["total_work_units"],
                "baseline_completed_work_units": baseline["completed_work_units"],
                "carbon_aware_completed_work_units": aware["completed_work_units"],
                "deadline_carbon_completed_work_units": deadline["completed_work_units"],
                "baseline_work_completion_rate_pct": baseline["work_completion_rate_pct"],
                "carbon_aware_work_completion_rate_pct": aware["work_completion_rate_pct"],
                "deadline_carbon_work_completion_rate_pct": deadline["work_completion_rate_pct"],
                "baseline_emissions_per_completed_work_unit": baseline[
                    "emissions_kg_co2_per_completed_work_unit"
                ],
                "carbon_aware_emissions_per_completed_work_unit": aware[
                    "emissions_kg_co2_per_completed_work_unit"
                ],
                "deadline_carbon_emissions_per_completed_work_unit": deadline[
                    "emissions_kg_co2_per_completed_work_unit"
                ],
                "baseline_jobs_missed": baseline["jobs_missed"],
                "carbon_aware_jobs_missed": aware["jobs_missed"],
                "deadline_carbon_jobs_missed": deadline["jobs_missed"],
                "baseline_completion_rate_pct": baseline["completion_rate_pct"],
                "carbon_aware_completion_rate_pct": aware["completion_rate_pct"],
                "deadline_carbon_completion_rate_pct": deadline["completion_rate_pct"],
                "baseline_energy_kwh": baseline["energy_kwh"],
                "carbon_aware_energy_kwh": aware["energy_kwh"],
                "deadline_carbon_energy_kwh": deadline["energy_kwh"],
                "baseline_emissions_kg_co2": base_emissions,
                "carbon_aware_emissions_kg_co2": aware_emissions,
                "deadline_carbon_emissions_kg_co2": deadline_emissions,
                "emissions_reduction_pct": aware_reduction,
                "deadline_carbon_reduction_pct": deadline_reduction,
            }
        )

    trials = pd.DataFrame(trial_rows)
    policies = pd.DataFrame(policy_rows)

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

    aware_reductions = trials["emissions_reduction_pct"]
    deadline_reductions = trials["deadline_carbon_reduction_pct"]
    overall = pd.DataFrame(
        [
            {
                "trials": len(trials),
                "mean_emissions_reduction_pct": aware_reductions.mean(),
                "std_emissions_reduction_pct": aware_reductions.std(ddof=1),
                "median_emissions_reduction_pct": aware_reductions.median(),
                "min_emissions_reduction_pct": aware_reductions.min(),
                "max_emissions_reduction_pct": aware_reductions.max(),
                "trials_with_positive_reduction": int((aware_reductions > 0).sum()),
                "trials_with_positive_reduction_pct": 100.0 * (aware_reductions > 0).mean(),
                "mean_baseline_jobs_missed": trials["baseline_jobs_missed"].mean(),
                "mean_carbon_aware_jobs_missed": trials["carbon_aware_jobs_missed"].mean(),
                "mean_deadline_carbon_jobs_missed": trials["deadline_carbon_jobs_missed"].mean(),
                "mean_deadline_carbon_reduction_pct": deadline_reductions.mean(),
                "std_deadline_carbon_reduction_pct": deadline_reductions.std(ddof=1),
                "trials_with_positive_deadline_carbon_reduction": int((deadline_reductions > 0).sum()),
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
