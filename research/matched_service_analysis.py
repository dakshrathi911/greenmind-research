"""Matched-service emissions analysis for GreenMind AI.

For each paired synthetic trial, compare policy emissions on the intersection
of jobs completed by all three policies. This isolates emissions for an
identical job set, while explicitly reporting how much of the workload that
intersection covers. It does not prove real-world savings or remove selection
effects caused by conditioning on commonly completed jobs.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

try:  # Support both package imports in tests and direct script execution.
    from .carbon_experiment import (
        generate_carbon_intensity,
        generate_pue_profile,
        generate_workload,
        run_policy,
    )
    from .sensitivity_analysis import (
        CARBON_VARIABILITY,
        HOURLY_CAPACITIES,
        PUE_SCENARIOS,
        WORKLOAD_COUNTS,
        rescale_profile,
        vary_carbon,
    )
except ImportError:  # python research/matched_service_analysis.py
    from carbon_experiment import (
        generate_carbon_intensity,
        generate_pue_profile,
        generate_workload,
        run_policy,
    )
    from sensitivity_analysis import (
        CARBON_VARIABILITY,
        HOURLY_CAPACITIES,
        PUE_SCENARIOS,
        WORKLOAD_COUNTS,
        rescale_profile,
        vary_carbon,
    )

OUTPUT_DIR = Path(__file__).resolve().parent / "results"
POLICIES = ("baseline", "carbon_aware", "deadline_carbon")
SCENARIO_COLUMNS = [
    "pue_scenario",
    "carbon_variability",
    "job_count",
    "hourly_capacity",
]


def matched_service_metrics(jobs, results):
    """Calculate policy emissions on jobs completed by every policy.

    Args:
        jobs: Shared list of Job objects for the paired trial.
        results: Mapping from policy name to run_policy() result.

    Returns:
        A dictionary containing common-job coverage and matched emissions.
    """
    completed_by_policy = {}
    for policy in POLICIES:
        completed_by_policy[policy] = {
            row["job_id"]: row
            for row in results[policy]["schedule"]
            if row["status"] == "completed"
        }

    common_ids = set.intersection(
        *(set(completed_by_policy[policy]) for policy in POLICIES)
    )
    jobs_by_id = {job.job_id: job for job in jobs}
    total_work_units = sum(job.work for job in jobs)
    common_work_units = sum(jobs_by_id[job_id].work for job_id in common_ids)

    output = {
        "total_jobs": len(jobs),
        "common_completed_jobs": len(common_ids),
        "common_job_coverage_pct": (
            100.0 * len(common_ids) / len(jobs) if jobs else np.nan
        ),
        "total_work_units": total_work_units,
        "common_completed_work_units": common_work_units,
        "common_work_coverage_pct": (
            100.0 * common_work_units / total_work_units
            if total_work_units else np.nan
        ),
    }

    matched_emissions = {}
    for policy in POLICIES:
        emissions = sum(
            completed_by_policy[policy][job_id]["emissions_kg_co2"]
            for job_id in common_ids
        )
        matched_emissions[policy] = float(emissions)
        output[f"{policy}_matched_emissions_kg_co2"] = float(emissions)
        output[f"{policy}_full_emissions_kg_co2"] = float(
            results[policy]["emissions_kg_co2"]
        )
        output[f"{policy}_jobs_missed"] = int(results[policy]["jobs_missed"])
        output[f"{policy}_completed_work_units"] = int(
            results[policy]["completed_work_units"]
        )

    baseline_emissions = matched_emissions["baseline"]
    for policy in ("carbon_aware", "deadline_carbon"):
        reduction = (
            100.0 * (
                baseline_emissions - matched_emissions[policy]
            ) / baseline_emissions
            if baseline_emissions > 0 else np.nan
        )
        output[f"{policy}_matched_reduction_pct"] = reduction

    output["deadline_minus_carbon_aware_matched_reduction_pp"] = (
        output["deadline_carbon_matched_reduction_pct"]
        - output["carbon_aware_matched_reduction_pct"]
        if pd.notna(output["deadline_carbon_matched_reduction_pct"])
        and pd.notna(output["carbon_aware_matched_reduction_pct"])
        else np.nan
    )
    return output


def benjamini_hochberg(p_values):
    """Return BH-adjusted p-values, preserving NaNs and input order."""
    values = np.asarray(p_values, dtype=float)
    adjusted = np.full(values.shape, np.nan, dtype=float)
    valid_indices = np.flatnonzero(np.isfinite(values))
    if not len(valid_indices):
        return adjusted

    valid_p = values[valid_indices]
    order = np.argsort(valid_p)
    sorted_p = valid_p[order]
    ranks = np.arange(1, len(sorted_p) + 1)
    sorted_adjusted = sorted_p * len(sorted_p) / ranks
    sorted_adjusted = np.minimum.accumulate(sorted_adjusted[::-1])[::-1]
    sorted_adjusted = np.clip(sorted_adjusted, 0.0, 1.0)

    adjusted_valid = np.empty_like(sorted_adjusted)
    adjusted_valid[order] = sorted_adjusted
    adjusted[valid_indices] = adjusted_valid
    return adjusted


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trial_rows = []

    for pue_name, (pue_low, pue_high) in PUE_SCENARIOS.items():
        for carbon_name, carbon_multiplier in CARBON_VARIABILITY.items():
            for job_count in WORKLOAD_COUNTS:
                for hourly_capacity in HOURLY_CAPACITIES:
                    for seed in range(10):
                        jobs = generate_workload(seed=seed, count=job_count)
                        raw_carbon = generate_carbon_intensity(seed=seed + 1)
                        carbon = vary_carbon(raw_carbon, carbon_multiplier)
                        raw_pue = generate_pue_profile(seed=seed + 2)
                        pue = rescale_profile(raw_pue, pue_low, pue_high)
                        results = {
                            policy: run_policy(
                                jobs, carbon, policy, pue,
                                hourly_capacity=hourly_capacity,
                            )
                            for policy in POLICIES
                        }
                        metrics = matched_service_metrics(jobs, results)
                        trial_rows.append({
                            "pue_scenario": pue_name,
                            "pue_min": pue_low,
                            "pue_max": pue_high,
                            "carbon_variability": carbon_name,
                            "carbon_variability_multiplier": carbon_multiplier,
                            "job_count": job_count,
                            "hourly_capacity": hourly_capacity,
                            "seed": seed,
                            **metrics,
                        })

    trials = pd.DataFrame(trial_rows)
    trials_path = OUTPUT_DIR / "matched_service_trials.csv"
    trials.to_csv(trials_path, index=False)

    summary_rows = []
    for keys, group in trials.groupby(SCENARIO_COLUMNS, dropna=False):
        row = dict(zip(SCENARIO_COLUMNS, keys))
        row["trials"] = len(group)
        for col in [
            "common_completed_jobs",
            "common_job_coverage_pct",
            "common_completed_work_units",
            "common_work_coverage_pct",
            "baseline_matched_emissions_kg_co2",
            "carbon_aware_matched_emissions_kg_co2",
            "deadline_carbon_matched_emissions_kg_co2",
            "carbon_aware_matched_reduction_pct",
            "deadline_carbon_matched_reduction_pct",
            "deadline_minus_carbon_aware_matched_reduction_pp",
        ]:
            row[f"mean_{col}"] = group[col].mean()
            row[f"std_{col}"] = group[col].std(ddof=1)

        differences = group[
            "deadline_minus_carbon_aware_matched_reduction_pp"
        ].dropna()
        n = len(differences)
        mean_diff = differences.mean() if n else np.nan
        sd_diff = differences.std(ddof=1) if n > 1 else np.nan
        if n > 1 and sd_diff > 0:
            se = sd_diff / np.sqrt(n)
            critical = stats.t.ppf(0.975, df=n - 1)
            lower = mean_diff - critical * se
            upper = mean_diff + critical * se
            p_value = stats.ttest_1samp(differences, popmean=0).pvalue
        elif n > 1:
            lower = upper = mean_diff
            p_value = 1.0 if mean_diff == 0 else 0.0
        else:
            lower = upper = p_value = np.nan

        row.update({
            "valid_paired_trials": n,
            "mean_deadline_minus_carbon_aware_matched_reduction_pp": mean_diff,
            "difference_ci95_lower_pp": lower,
            "difference_ci95_upper_pp": upper,
            "paired_t_test_p_value": p_value,
        })
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    summary["fdr_adjusted_p_value"] = benjamini_hochberg(
        summary["paired_t_test_p_value"].to_numpy()
    )
    summary["significant_fdr_0_05"] = (
        summary["fdr_adjusted_p_value"] < 0.05
    )
    summary_path = OUTPUT_DIR / "matched_service_scenario_summary.csv"
    summary.to_csv(summary_path, index=False)

    valid = summary["paired_t_test_p_value"].notna()
    significant = summary["significant_fdr_0_05"].sum()
    report_lines = [
        "# GreenMind AI — Matched-Service Emissions Analysis",
        "",
        "## 1. Purpose",
        "",
        "This analysis compares the three scheduling policies on the same set "
        "of jobs: only jobs completed by baseline, carbon-aware, and "
        "deadline-carbon in the same paired trial are included in matched "
        "emissions. The original all-completed-jobs analysis remains the "
        "operational outcome analysis.",
        "",
        "## 2. Experimental design",
        "",
        f"- Scenario combinations: **{len(summary)}**",
        f"- Paired trials: **{len(trials)}**",
        "- Policies: baseline, carbon-aware, and deadline-carbon.",
        "- Inputs are synthetic; results are not production measurements.",
        "",
        "## 3. Matched-service results",
        "",
        "Scenario means below summarize ten paired seeds. Coverage is the "
        "fraction of all generated work units included in the common completed "
        "set. A low coverage value means the matched comparison describes "
        "only a limited part of the workload.",
        "",
        summary[[
            "pue_scenario",
            "carbon_variability",
            "job_count",
            "hourly_capacity",
            "mean_common_work_coverage_pct",
            "mean_carbon_aware_matched_reduction_pct",
            "mean_deadline_carbon_matched_reduction_pct",
        ]].round(3).to_markdown(index=False),
        "",
        "## 4. Paired statistical comparison",
        "",
        "The tested difference is deadline-carbon minus carbon-aware matched "
        "emissions reduction in percentage points. Positive values favor "
        "deadline-carbon on this matched job set; negative values favor "
        "carbon-aware. P-values use paired-seed differences within each "
        "scenario, followed by Benjamini-Hochberg correction across scenarios.",
        "",
        f"- Scenarios with valid paired tests: **{int(valid.sum())}**",
        f"- Significant after FDR correction at 0.05: **{int(significant)}**",
        "",
        summary.loc[summary["significant_fdr_0_05"], [
            "pue_scenario",
            "carbon_variability",
            "job_count",
            "hourly_capacity",
            "mean_deadline_minus_carbon_aware_matched_reduction_pp",
            "paired_t_test_p_value",
            "fdr_adjusted_p_value",
        ]].round(4).to_markdown(index=False)
        if significant else "No scenario comparisons remained significant after FDR correction.",
        "",
        "## 5. Interpretation and limitations",
        "",
        "- This is a matched-job-set comparison, not a guarantee of equal service "
        "across the full workload. Report matched work coverage alongside all "
        "emissions results.",
        "- Conditioning on jobs completed by all policies can select a subset "
        "that is easier to schedule; results should be interpreted together "
        "with missed jobs and full-workload completion rates.",
        "- The simulator uses synthetic workloads, carbon-intensity profiles, "
        "PUE profiles, and fixed illustrative IT energy per work unit.",
        "- These experiments do not demonstrate real-world emissions savings "
        "or production performance.",
        "",
    ]
    report_path = OUTPUT_DIR / "matched_service_analysis_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print("GREENMIND AI — MATCHED-SERVICE ANALYSIS")
    print("=" * 48)
    print(f"Scenarios: {len(summary)} | Paired trials: {len(trials)}")
    print(f"Scenarios with valid tests: {int(valid.sum())}")
    print(f"FDR-significant matched-service comparisons: {int(significant)}")
    print(f"Saved: {trials_path}")
    print(f"Saved: {summary_path}")
    print(f"Saved: {report_path}")


if __name__ == "__main__":
    main()
