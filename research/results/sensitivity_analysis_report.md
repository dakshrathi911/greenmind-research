# GreenMind AI — Sensitivity Analysis Results

## 1. Experimental design

- Scenario combinations: **81**
- Trial rows: **810**
- Total policy evaluations: **2430**, assuming three policy evaluations per trial row.
- Inputs are synthetic and the findings are simulation results, not measurements from a production data center.

## 2. Average emissions reductions

- Carbon-aware policy: **15.565%** mean scenario-level reduction.
- Deadline-carbon policy: **15.463%** mean scenario-level reduction.
- Mean scenario-level difference (deadline-carbon minus carbon-aware): **-0.1024 percentage points**.

These are unweighted averages of scenario-level means, not a pooled estimate across all jobs or trials.

## 3. Job completion and missed jobs

| policy          |   scenario_trial_rows |   total_jobs_across_trials |   jobs_missed |   jobs_completed_estimate |   completion_rate_pct_from_missed_jobs |   mean_reported_completion_rate_pct |
|:----------------|----------------------:|---------------------------:|--------------:|--------------------------:|---------------------------------------:|------------------------------------:|
| Baseline        |                   810 |                     194400 |            18 |                    194382 |                                 99.991 |                              99.993 |
| Carbon-aware    |                   810 |                     194400 |           519 |                    193881 |                                 99.733 |                              99.772 |
| Deadline-carbon |                   810 |                     194400 |           158 |                    194242 |                                 99.919 |                              99.932 |

The total job counts aggregate jobs across scenario-trial rows; they do not represent unique jobs.

## 4. Paired comparison and multiple testing

- Scenarios compared: **81**.
- Scenarios significant before FDR correction: **33**.
- Scenarios significant after Benjamini–Hochberg FDR correction: **6**.

The six comparisons that survive the correction are listed below. A positive difference favors deadline-carbon for emissions reduction; a negative difference favors carbon-aware.

| pue_scenario   | carbon_variability   |   job_count |   hourly_capacity |   mean_deadline_minus_carbon_aware_pp |   paired_t_test_p_value |   fdr_adjusted_p_value |
|:---------------|:---------------------|------------:|------------------:|--------------------------------------:|------------------------:|-----------------------:|
| high_overhead  | high                 |         240 |                12 |                                0.1844 |                  0.0025 |                 0.0351 |
| high_overhead  | high                 |         300 |                16 |                                0.1631 |                  0.0013 |                 0.0351 |
| high_overhead  | standard             |         300 |                16 |                                0.1287 |                  0.0006 |                 0.0351 |
| low_overhead   | high                 |         240 |                12 |                                0.1844 |                  0.0026 |                 0.0351 |
| low_overhead   | high                 |         300 |                16 |                                0.1598 |                  0.0015 |                 0.0351 |
| standard_range | high                 |         300 |                16 |                                0.1376 |                  0.0024 |                 0.0351 |

## 5. Lowest-reduction scenarios

| pue_scenario   | carbon_variability   |   job_count |   hourly_capacity |   carbon_aware_reduction_pct_mean |   deadline_carbon_reduction_pct_mean |   carbon_aware_jobs_missed |   deadline_carbon_jobs_missed |
|:---------------|:---------------------|------------:|------------------:|----------------------------------:|-------------------------------------:|---------------------------:|------------------------------:|
| high_overhead  | low                  |         300 |                 8 |                             7.62  |                                6.646 |                         40 |                            16 |
| low_overhead   | low                  |         300 |                 8 |                             7.846 |                                6.852 |                         41 |                            16 |
| high_overhead  | low                  |         240 |                 8 |                             7.419 |                                6.977 |                         10 |                             1 |
| low_overhead   | low                  |         240 |                 8 |                             7.648 |                                7.229 |                         11 |                             2 |
| standard_range | low                  |         300 |                 8 |                             8.994 |                                7.886 |                         42 |                            14 |
| high_overhead  | low                  |         300 |                12 |                             8.161 |                                8.06  |                          4 |                             0 |
| high_overhead  | low                  |         180 |                 8 |                             8.127 |                                8.117 |                          1 |                             0 |
| low_overhead   | low                  |         300 |                12 |                             8.37  |                                8.262 |                          4 |                             0 |
| low_overhead   | low                  |         180 |                 8 |                             8.354 |                                8.329 |                          1 |                             0 |
| high_overhead  | low                  |         240 |                12 |                             8.304 |                                8.343 |                          0 |                             0 |

## 6. Interpretation

The simulation suggests that both carbon-aware policies can reduce modeled emissions relative to the baseline. Average reductions alone do not capture operational reliability: the deadline-carbon policy missed fewer jobs overall than the carbon-aware policy in this run, but it did not consistently achieve greater emissions reductions.

Six of 81 scenario-specific paired tests remained significant after Benjamini–Hochberg false discovery rate correction at 0.05. These results are scenario-specific and do not establish universal superiority. Confidence intervals and p-values are conditional on the simulation design and its assumptions.

## 7. Limitations

- Workloads, carbon-intensity profiles, and energy parameters are synthetic or modeled.
- Ten paired trials per scenario provide limited precision.
- Scenario-specific tests involve multiple comparisons; FDR correction reduces but does not eliminate inferential limitations.
- Results require validation against realistic workload traces and independently sourced carbon-intensity and energy parameters.
- No real-world emissions savings or production performance are demonstrated by these experiments.
