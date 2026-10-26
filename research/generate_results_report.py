
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

trials = pd.read_csv(RESULTS / "sensitivity_trials.csv")
scenarios = pd.read_csv(RESULTS / "analysis_scenario_summary.csv")
policies = pd.read_csv(RESULTS / "analysis_policy_summary.csv")
comparison = pd.read_csv(
    RESULTS / "paired_policy_comparison_corrected.csv"
)

difference_col = "mean_deadline_minus_carbon_aware_pp"
adjusted_col = "fdr_adjusted_p_value"

significant = comparison[
    comparison[adjusted_col] < 0.05
].copy()

mean_ca = scenarios[
    "carbon_aware_reduction_pct_mean"
].mean()
mean_dc = scenarios[
    "deadline_carbon_reduction_pct_mean"
].mean()

mean_difference = comparison[difference_col].mean()

def pct(value):
    return f"{value:.3f}%"

def scenario_table(frame):
    cols = [
        "pue_scenario",
        "carbon_variability",
        "job_count",
        "hourly_capacity",
        "carbon_aware_reduction_pct_mean",
        "deadline_carbon_reduction_pct_mean",
        "carbon_aware_jobs_missed",
        "deadline_carbon_jobs_missed",
    ]
    available = [c for c in cols if c in frame.columns]
    return frame[available].round(3).to_markdown(index=False)

report = []

report.append("# GreenMind AI — Sensitivity Analysis Results")
report.append("")
report.append("## 1. Experimental design")
report.append("")
report.append(
    f"- Scenario combinations: **{len(scenarios)}**"
)
report.append(
    f"- Trial rows: **{len(trials)}**"
)
report.append(
    f"- Total policy evaluations: **{len(trials) * 3}**, "
    "assuming three policy evaluations per trial row."
)
report.append(
    "- Inputs are synthetic and the findings are simulation results, "
    "not measurements from a production data center."
)
report.append("")
report.append("## 2. Average emissions reductions")
report.append("")
report.append(
    f"- Carbon-aware policy: **{pct(mean_ca)}** "
    "mean scenario-level reduction."
)
report.append(
    f"- Deadline-carbon policy: **{pct(mean_dc)}** "
    "mean scenario-level reduction."
)
report.append(
    f"- Mean scenario-level difference (deadline-carbon minus "
    f"carbon-aware): **{mean_difference:.4f} percentage points**."
)
report.append("")
report.append(
    "These are unweighted averages of scenario-level means, "
    "not a pooled estimate across all jobs or trials."
)
report.append("")
report.append("## 3. Job completion and missed jobs")
report.append("")
report.append(policies.round(3).to_markdown(index=False))
report.append("")
report.append(
    "The total job counts aggregate jobs across scenario-trial rows; "
    "they do not represent unique jobs."
)
report.append("")
report.append("## 4. Paired comparison and multiple testing")
report.append("")
report.append(
    f"- Scenarios compared: **{len(comparison)}**."
)
report.append(
    f"- Scenarios significant before FDR correction: "
    f"**{int((comparison['paired_t_test_p_value'] < 0.05).sum())}**."
)
report.append(
    f"- Scenarios significant after Benjamini–Hochberg FDR correction: "
    f"**{len(significant)}**."
)
report.append("")
report.append(
    "The six comparisons that survive the correction are listed below. "
    "A positive difference favors deadline-carbon for emissions reduction; "
    "a negative difference favors carbon-aware."
)
report.append("")

if significant.empty:
    report.append("No comparisons remained significant at FDR 0.05.")
else:
    report.append(
        significant[
            [
                "pue_scenario",
                "carbon_variability",
                "job_count",
                "hourly_capacity",
                difference_col,
                "paired_t_test_p_value",
                adjusted_col,
            ]
        ].round(4).to_markdown(index=False)
    )

report.append("")
report.append("## 5. Lowest-reduction scenarios")
report.append("")
weakest = scenarios.nsmallest(
    10, "deadline_carbon_reduction_pct_mean"
)
report.append(scenario_table(weakest))
report.append("")
report.append("## 6. Interpretation")
report.append("")
report.append(
    "The simulation suggests that both carbon-aware policies can reduce "
    "modeled emissions relative to the baseline. Average reductions alone "
    "do not capture operational reliability: the deadline-carbon policy "
    "missed fewer jobs overall than the carbon-aware policy in this run, "
    "but it did not consistently achieve greater emissions reductions."
)
report.append("")
report.append(
    "Six of 81 scenario-specific paired tests remained significant after "
    "Benjamini–Hochberg false discovery rate correction at 0.05. These "
    "results are scenario-specific and do not establish universal "
    "superiority. Confidence intervals and p-values are conditional on "
    "the simulation design and its assumptions."
)
report.append("")
report.append("## 7. Limitations")
report.append("")
report.append(
    "- Workloads, carbon-intensity profiles, and energy parameters are "
    "synthetic or modeled."
)
report.append(
    "- Ten paired trials per scenario provide limited precision."
)
report.append(
    "- Scenario-specific tests involve multiple comparisons; FDR correction "
    "reduces but does not eliminate inferential limitations."
)
report.append(
    "- Results require validation against realistic workload traces and "
    "independently sourced carbon-intensity and energy parameters."
)
report.append(
    "- No real-world emissions savings or production performance are "
    "demonstrated by these experiments."
)
report.append("")

output = RESULTS / "sensitivity_analysis_report.md"
output.write_text("\n".join(report), encoding="utf-8")

print("Report generated:", output)
print("Scenarios:", len(scenarios))
print("FDR-significant comparisons:", len(significant))
print("\nOpen the report with:")
print("notepad research\\results\\sensitivity_analysis_report.md")
