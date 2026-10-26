"""
GreenMind AI sensitivity analysis for synthetic carbon-aware scheduling.

Runs a paired factorial sweep over PUE range, carbon-intensity variability,
workload size, and hourly capacity. All inputs remain synthetic; outputs are
simulation sensitivity results, not measured real-world savings.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from carbon_experiment import (
    generate_carbon_intensity,
    generate_pue_profile,
    generate_workload,
    run_policy,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "results"
SEEDS = range(10)
POLICIES = ("baseline", "carbon_aware", "deadline_carbon")
PUE_SCENARIOS = {
    "low_overhead": (1.1, 1.3),
    "standard_range": (1.1, 1.5),
    "high_overhead": (1.3, 1.5),
}
CARBON_VARIABILITY = {"low": 0.5, "standard": 1.0, "high": 1.5}
WORKLOAD_COUNTS = (180, 240, 300)
HOURLY_CAPACITIES = (8, 12, 16)


def rescale_profile(profile: np.ndarray, low: float, high: float) -> np.ndarray:
    """Map a reproducible profile's relative shape into a requested range."""
    minimum = float(np.min(profile))
    maximum = float(np.max(profile))
    if maximum == minimum:
        return np.full_like(profile, (low + high) / 2, dtype=float)
    normalized = (profile - minimum) / (maximum - minimum)
    return low + normalized * (high - low)


def vary_carbon(profile: np.ndarray, multiplier: float) -> np.ndarray:
    """Scale deviations from the profile mean while respecting model bounds."""
    mean = float(np.mean(profile))
    return np.clip(mean + multiplier * (profile - mean), 0.15, 0.8)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trial_rows = []

    for pue_name, (pue_low, pue_high) in PUE_SCENARIOS.items():
        for carbon_name, carbon_multiplier in CARBON_VARIABILITY.items():
            for job_count in WORKLOAD_COUNTS:
                for hourly_capacity in HOURLY_CAPACITIES:
                    for seed in SEEDS:
                        jobs = generate_workload(seed=seed, count=job_count)
                        raw_carbon = generate_carbon_intensity(seed=seed + 1)
                        carbon = vary_carbon(raw_carbon, carbon_multiplier)
                        raw_pue = generate_pue_profile(seed=seed + 2)
                        pue = rescale_profile(raw_pue, pue_low, pue_high)

                        results = {
                            policy: run_policy(
                                jobs,
                                carbon,
                                policy,
                                pue,
                                hourly_capacity=hourly_capacity,
                            )
                            for policy in POLICIES
                        }
                        baseline = results["baseline"]
                        aware = results["carbon_aware"]
                        deadline = results["deadline_carbon"]
                        base_emissions = float(baseline["emissions_kg_co2"])

                        def reduction(emissions: float) -> float:
                            if base_emissions <= 0:
                                return 0.0
                            return 100.0 * (base_emissions - emissions) / base_emissions

                        trial_rows.append(
                            {
                                "pue_scenario": pue_name,
                                "pue_min": pue_low,
                                "pue_max": pue_high,
                                "carbon_variability": carbon_name,
                                "carbon_variability_multiplier": carbon_multiplier,
                                "job_count": job_count,
                                "hourly_capacity": hourly_capacity,
                                "seed": seed,
                                "baseline_emissions_kg_co2": base_emissions,
                                "carbon_aware_emissions_kg_co2": aware["emissions_kg_co2"],
                                "deadline_carbon_emissions_kg_co2": deadline["emissions_kg_co2"],
                                "carbon_aware_reduction_pct": reduction(float(aware["emissions_kg_co2"])),
                                "deadline_carbon_reduction_pct": reduction(float(deadline["emissions_kg_co2"])),
                                "baseline_jobs_missed": baseline["jobs_missed"],
                                "carbon_aware_jobs_missed": aware["jobs_missed"],
                                "deadline_carbon_jobs_missed": deadline["jobs_missed"],
                                "baseline_completion_rate_pct": baseline["completion_rate_pct"],
                                "carbon_aware_completion_rate_pct": aware["completion_rate_pct"],
                                "deadline_carbon_completion_rate_pct": deadline["completion_rate_pct"],
                            }
                        )

    trials = pd.DataFrame(trial_rows)
    group_cols = [
        "pue_scenario", "pue_min", "pue_max", "carbon_variability",
        "carbon_variability_multiplier", "job_count", "hourly_capacity",
    ]
    summary = (
        trials.groupby(group_cols, as_index=False)
        .agg(
            trials=("seed", "count"),
            mean_carbon_aware_reduction_pct=("carbon_aware_reduction_pct", "mean"),
            std_carbon_aware_reduction_pct=("carbon_aware_reduction_pct", "std"),
            mean_deadline_carbon_reduction_pct=("deadline_carbon_reduction_pct", "mean"),
            std_deadline_carbon_reduction_pct=("deadline_carbon_reduction_pct", "std"),
            carbon_aware_positive_trials=("carbon_aware_reduction_pct", lambda s: int((s > 0).sum())),
            deadline_carbon_positive_trials=("deadline_carbon_reduction_pct", lambda s: int((s > 0).sum())),
            baseline_jobs_missed=("baseline_jobs_missed", "sum"),
            carbon_aware_jobs_missed=("carbon_aware_jobs_missed", "sum"),
            deadline_carbon_jobs_missed=("deadline_carbon_jobs_missed", "sum"),
            mean_baseline_completion_pct=("baseline_completion_rate_pct", "mean"),
            mean_carbon_aware_completion_pct=("carbon_aware_completion_rate_pct", "mean"),
            mean_deadline_carbon_completion_pct=("deadline_carbon_completion_rate_pct", "mean"),
        )
    )

    trials.to_csv(OUTPUT_DIR / "sensitivity_trials.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "sensitivity_summary.csv", index=False)

    print("\nGREENMIND AI — SENSITIVITY ANALYSIS")
    print("=" * 54)
    print(f"Scenario combinations: {len(summary)}")
    print(f"Paired trials: {len(trials)}")
    print(f"Policies per trial: {len(POLICIES)}")
    print("\nHighest mean deadline-carbon reductions:")
    print(
        summary.sort_values("mean_deadline_carbon_reduction_pct", ascending=False)
        .head(10)
        .round(4)
        .to_string(index=False)
    )
    print(f"\nResults saved in: {OUTPUT_DIR}")
    print("  - sensitivity_trials.csv")
    print("  - sensitivity_summary.csv")
    print("\nInterpretation note: every input is synthetic; this sweep evaluates")
    print("sensitivity within the simulator and does not establish real-world savings.")


if __name__ == "__main__":
    main()
