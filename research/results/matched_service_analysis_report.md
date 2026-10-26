# GreenMind AI — Matched-Service Emissions Analysis

## 1. Purpose

This analysis compares the three scheduling policies on the same set of jobs: only jobs completed by baseline, carbon-aware, and deadline-carbon in the same paired trial are included in matched emissions. The original all-completed-jobs analysis remains the operational outcome analysis.

## 2. Experimental design

- Scenario combinations: **81**
- Paired trials: **810**
- Policies: baseline, carbon-aware, and deadline-carbon.
- Inputs are synthetic; results are not production measurements.

## 3. Matched-service results

Scenario means below summarize ten paired seeds. Coverage is the fraction of all generated work units included in the common completed set. A low coverage value means the matched comparison describes only a limited part of the workload.

| pue_scenario   | carbon_variability   |   job_count |   hourly_capacity |   mean_common_work_coverage_pct |   mean_carbon_aware_matched_reduction_pct |   mean_deadline_carbon_matched_reduction_pct |
|:---------------|:---------------------|------------:|------------------:|--------------------------------:|------------------------------------------:|---------------------------------------------:|
| high_overhead  | high                 |         180 |                 8 |                          99.873 |                                    21.412 |                                       21.659 |
| high_overhead  | high                 |         180 |                12 |                         100     |                                    23.559 |                                       23.696 |
| high_overhead  | high                 |         180 |                16 |                         100     |                                    24.173 |                                       24.188 |
| high_overhead  | high                 |         240 |                 8 |                          99.287 |                                    18.747 |                                       18.661 |
| high_overhead  | high                 |         240 |                12 |                         100     |                                    22.304 |                                       22.489 |
| high_overhead  | high                 |         240 |                16 |                         100     |                                    23.379 |                                       23.462 |
| high_overhead  | high                 |         300 |                 8 |                          98.114 |                                    16.43  |                                       15.943 |
| high_overhead  | high                 |         300 |                12 |                          99.794 |                                    21.312 |                                       21.411 |
| high_overhead  | high                 |         300 |                16 |                         100     |                                    22.959 |                                       23.122 |
| high_overhead  | low                  |         180 |                 8 |                          99.936 |                                     8.081 |                                        8.12  |
| high_overhead  | low                  |         180 |                12 |                         100     |                                     8.81  |                                        8.841 |
| high_overhead  | low                  |         180 |                16 |                         100     |                                     9.063 |                                        9.077 |
| high_overhead  | low                  |         240 |                 8 |                          99.431 |                                     7.032 |                                        6.957 |
| high_overhead  | low                  |         240 |                12 |                         100     |                                     8.304 |                                        8.343 |
| high_overhead  | low                  |         240 |                16 |                         100     |                                     8.684 |                                        8.709 |
| high_overhead  | low                  |         300 |                 8 |                          97.965 |                                     6.319 |                                        6.125 |
| high_overhead  | low                  |         300 |                12 |                          99.819 |                                     8.026 |                                        8.069 |
| high_overhead  | low                  |         300 |                16 |                         100     |                                     8.623 |                                        8.655 |
| high_overhead  | standard             |         180 |                 8 |                          99.873 |                                    14.767 |                                       14.961 |
| high_overhead  | standard             |         180 |                12 |                         100     |                                    16.288 |                                       16.398 |
| high_overhead  | standard             |         180 |                16 |                         100     |                                    16.786 |                                       16.821 |
| high_overhead  | standard             |         240 |                 8 |                          99.287 |                                    12.921 |                                       12.823 |
| high_overhead  | standard             |         240 |                12 |                         100     |                                    15.408 |                                       15.541 |
| high_overhead  | standard             |         240 |                16 |                         100     |                                    16.123 |                                       16.19  |
| high_overhead  | standard             |         300 |                 8 |                          98.166 |                                    11.38  |                                       11.106 |
| high_overhead  | standard             |         300 |                12 |                          99.728 |                                    14.778 |                                       14.829 |
| high_overhead  | standard             |         300 |                16 |                         100     |                                    15.887 |                                       16.016 |
| low_overhead   | high                 |         180 |                 8 |                          99.873 |                                    21.545 |                                       21.796 |
| low_overhead   | high                 |         180 |                12 |                         100     |                                    23.696 |                                       23.834 |
| low_overhead   | high                 |         180 |                16 |                         100     |                                    24.312 |                                       24.326 |
| low_overhead   | high                 |         240 |                 8 |                          99.287 |                                    18.881 |                                       18.775 |
| low_overhead   | high                 |         240 |                12 |                         100     |                                    22.438 |                                       22.622 |
| low_overhead   | high                 |         240 |                16 |                         100     |                                    23.514 |                                       23.597 |
| low_overhead   | high                 |         300 |                 8 |                          98.114 |                                    16.559 |                                       16.057 |
| low_overhead   | high                 |         300 |                12 |                          99.794 |                                    21.454 |                                       21.551 |
| low_overhead   | high                 |         300 |                16 |                         100     |                                    23.109 |                                       23.269 |
| low_overhead   | low                  |         180 |                 8 |                          99.936 |                                     8.308 |                                        8.333 |
| low_overhead   | low                  |         180 |                12 |                         100     |                                     9.039 |                                        9.076 |
| low_overhead   | low                  |         180 |                16 |                         100     |                                     9.295 |                                        9.308 |
| low_overhead   | low                  |         240 |                 8 |                          99.366 |                                     7.196 |                                        7.143 |
| low_overhead   | low                  |         240 |                12 |                         100     |                                     8.522 |                                        8.557 |
| low_overhead   | low                  |         240 |                16 |                         100     |                                     8.914 |                                        8.937 |
| low_overhead   | low                  |         300 |                 8 |                          97.886 |                                     6.518 |                                        6.31  |
| low_overhead   | low                  |         300 |                12 |                          99.819 |                                     8.236 |                                        8.271 |
| low_overhead   | low                  |         300 |                16 |                         100     |                                     8.855 |                                        8.881 |
| low_overhead   | standard             |         180 |                 8 |                          99.873 |                                    14.95  |                                       15.127 |
| low_overhead   | standard             |         180 |                12 |                         100     |                                    16.472 |                                       16.577 |
| low_overhead   | standard             |         180 |                16 |                         100     |                                    16.96  |                                       16.994 |
| low_overhead   | standard             |         240 |                 8 |                          99.287 |                                    13.134 |                                       12.985 |
| low_overhead   | standard             |         240 |                12 |                         100     |                                    15.576 |                                       15.705 |
| low_overhead   | standard             |         240 |                16 |                         100     |                                    16.301 |                                       16.363 |
| low_overhead   | standard             |         300 |                 8 |                          98.166 |                                    11.572 |                                       11.245 |
| low_overhead   | standard             |         300 |                12 |                          99.728 |                                    14.972 |                                       15.016 |
| low_overhead   | standard             |         300 |                16 |                         100     |                                    16.093 |                                       16.197 |
| standard_range | high                 |         180 |                 8 |                          99.873 |                                    22.622 |                                       22.821 |
| standard_range | high                 |         180 |                12 |                         100     |                                    24.736 |                                       24.842 |
| standard_range | high                 |         180 |                16 |                         100     |                                    25.301 |                                       25.328 |
| standard_range | high                 |         240 |                 8 |                          99.335 |                                    19.84  |                                       19.589 |
| standard_range | high                 |         240 |                12 |                         100     |                                    23.492 |                                       23.647 |
| standard_range | high                 |         240 |                16 |                         100     |                                    24.495 |                                       24.557 |
| standard_range | high                 |         300 |                 8 |                          98.14  |                                    17.473 |                                       16.938 |
| standard_range | high                 |         300 |                12 |                          99.755 |                                    22.515 |                                       22.607 |
| standard_range | high                 |         300 |                16 |                         100     |                                    24.179 |                                       24.317 |
| standard_range | low                  |         180 |                 8 |                         100     |                                     9.707 |                                        9.742 |
| standard_range | low                  |         180 |                12 |                         100     |                                    10.558 |                                       10.606 |
| standard_range | low                  |         180 |                16 |                         100     |                                    10.887 |                                       10.904 |
| standard_range | low                  |         240 |                 8 |                          99.416 |                                     8.453 |                                        8.42  |
| standard_range | low                  |         240 |                12 |                          99.95  |                                     9.966 |                                       10.007 |
| standard_range | low                  |         240 |                16 |                         100     |                                    10.424 |                                       10.445 |
| standard_range | low                  |         300 |                 8 |                          97.928 |                                     7.705 |                                        7.461 |
| standard_range | low                  |         300 |                12 |                          99.91  |                                     9.65  |                                        9.756 |
| standard_range | low                  |         300 |                16 |                         100     |                                    10.382 |                                       10.426 |
| standard_range | standard             |         180 |                 8 |                          99.936 |                                    16.189 |                                       16.312 |
| standard_range | standard             |         180 |                12 |                         100     |                                    17.638 |                                       17.724 |
| standard_range | standard             |         180 |                16 |                         100     |                                    18.147 |                                       18.177 |
| standard_range | standard             |         240 |                 8 |                          99.366 |                                    14.186 |                                       14.066 |
| standard_range | standard             |         240 |                12 |                         100     |                                    16.682 |                                       16.778 |
| standard_range | standard             |         240 |                16 |                         100     |                                    17.444 |                                       17.493 |
| standard_range | standard             |         300 |                 8 |                          97.938 |                                    12.678 |                                       12.339 |
| standard_range | standard             |         300 |                12 |                          99.819 |                                    16.154 |                                       16.22  |
| standard_range | standard             |         300 |                16 |                         100     |                                    17.317 |                                       17.385 |

## 4. Paired statistical comparison

The tested difference is deadline-carbon minus carbon-aware matched emissions reduction in percentage points. Positive values favor deadline-carbon on this matched job set; negative values favor carbon-aware. P-values use paired-seed differences within each scenario, followed by Benjamini-Hochberg correction across scenarios.

- Scenarios with valid paired tests: **81**
- Significant after FDR correction at 0.05: **6**

| pue_scenario   | carbon_variability   |   job_count |   hourly_capacity |   mean_deadline_minus_carbon_aware_matched_reduction_pp |   paired_t_test_p_value |   fdr_adjusted_p_value |
|:---------------|:---------------------|------------:|------------------:|--------------------------------------------------------:|------------------------:|-----------------------:|
| high_overhead  | high                 |         240 |                12 |                                                  0.1844 |                  0.0025 |                 0.0351 |
| high_overhead  | high                 |         300 |                16 |                                                  0.1631 |                  0.0013 |                 0.0351 |
| high_overhead  | standard             |         300 |                16 |                                                  0.1287 |                  0.0006 |                 0.0351 |
| low_overhead   | high                 |         240 |                12 |                                                  0.1844 |                  0.0026 |                 0.0351 |
| low_overhead   | high                 |         300 |                16 |                                                  0.1598 |                  0.0015 |                 0.0351 |
| standard_range | high                 |         300 |                16 |                                                  0.1376 |                  0.0024 |                 0.0351 |

## 5. Interpretation and limitations

- This is a matched-job-set comparison, not a guarantee of equal service across the full workload. Report matched work coverage alongside all emissions results.
- Conditioning on jobs completed by all policies can select a subset that is easier to schedule; results should be interpreted together with missed jobs and full-workload completion rates.
- The simulator uses synthetic workloads, carbon-intensity profiles, PUE profiles, and fixed illustrative IT energy per work unit.
- These experiments do not demonstrate real-world emissions savings or production performance.
