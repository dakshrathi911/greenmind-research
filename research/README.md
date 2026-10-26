# Carbon-aware scheduling experiment

This folder contains the reproducible synthetic scheduling experiments for GreenMind AI.

## Policies compared

- **Baseline:** processes jobs in arrival order and assigns each to the earliest feasible hour.
- **Carbon-aware heuristic:** processes jobs in arrival order and assigns each to its lowest modeled-emissions feasible hour.
- **Deadline-aware carbon heuristic:** processes jobs in earliest-deadline-first order, then assigns each job to the feasible hour with the lowest modeled emissions per work unit.

The simulator reports both job completion and work-unit completion. Missed jobs contribute no scheduled energy or emissions in the current model, so total emissions must always be interpreted alongside completed work. It also reports emissions per completed work unit; this ratio is undefined when no work is completed. These metrics help expose service-level trade-offs but do not, by themselves, create a matched-service comparison.

The model treats 0.8 kWh per work unit as illustrative IT energy and multiplies it by an hourly power usage effectiveness (PUE) profile to estimate facility energy. PUE is a simplified cooling/overhead proxy, not a detailed thermal or cooling-system simulation.

All policies use the same generated workload, hourly capacity limit, deadline windows, and carbon-intensity series within each paired trial. The deadline-aware policy is an offline heuristic because it sorts the full workload before scheduling; it is not a real-time scheduler.

## Run locally

From the repository root, with the project's Python dependencies installed:

```powershell
python .\research\carbon_experiment.py
python .\research\multi_seed_experiment.py
python .\research\sensitivity_analysis.py
python .\\research\\matched_service_analysis.py
python -m unittest discover -s research/tests -v
```

The repeated-seed evaluation runs 30 paired synthetic trials. The sensitivity analysis sweeps four dimensions:

- **PUE range:** low overhead (1.1–1.3), standard range (1.1–1.5), and high overhead (1.3–1.5).
- **Carbon variability:** low, standard, and high multipliers (0.5×, 1.0×, and 1.5× deviations from the profile mean), clipped to the model's 0.15–0.8 kg CO2/kWh bounds.
- **Workload size:** 180, 240, and 300 jobs.
- **Hourly capacity:** 8, 12, and 16 work units.

This produces 81 scenario combinations and 10 paired seeds per combination (810 trials total), with all three policies evaluated on each shared trial. The sensitivity script writes `research/results/sensitivity_trials.csv` and `research/results/sensitivity_summary.csv`. These are scenario analyses within the simulator, not confidence intervals or evidence of real-world savings.

The matched-service analysis reruns the same 81-scenario, 10-seed sweep and compares policy emissions only on the intersection of jobs completed by all three policies in each paired trial. It writes `matched_service_trials.csv`, `matched_service_scenario_summary.csv`, and `matched_service_analysis_report.md`. Always report common-work coverage with matched emissions: conditioning on the shared completed-job set can select a subset of the workload and is not proof of equal service across the full workload. The analysis is still synthetic and does not establish real-world savings.

## Output files

The single-run script writes:

- `research/results/experiment_summary.csv` — aggregate completion, energy, and emissions metrics.
- `research/results/job_schedules.csv` — per-job scheduling decisions and calculated emissions.

The repeated-seed script writes:

- `research/results/multi_seed_trials.csv` — one row per paired seed.
- `research/results/multi_seed_policy_metrics.csv` — metrics by seed and policy.
- `research/results/multi_seed_policy_summary.csv` — per-policy averages and variability.
- `research/results/multi_seed_overall_summary.csv` — paired emissions-reduction summary.

The sensitivity script writes:

- `research/results/sensitivity_trials.csv` — metrics for every scenario/seed combination.
- `research/results/sensitivity_summary.csv` — aggregate metrics for each scenario combination.

Generated result CSVs are outputs; rerun the scripts to regenerate them after changing model assumptions.

## Assumptions and limitations

- Workloads are synthetic and generated with fixed random seeds.
- Grid carbon intensity is a synthetic illustrative profile, in kg CO2/kWh.
- Each work unit consumes a fixed illustrative 0.8 kWh of IT energy; this is not a calibrated server power model.
- Facility energy is estimated as IT energy multiplied by a synthetic PUE profile. The sensitivity sweep tests bounded PUE ranges, but does not simulate cooling physics or measured facility behavior.
- Jobs are indivisible and must be scheduled within their arrival-to-deadline window.
- The default hourly capacity is 12 work units; sensitivity analysis also tests 8 and 16.
- The policies are heuristics, not reinforcement learning, and the experiment does not establish real-world carbon savings.
- The current historical electricity dataset in the parent project is not automatically treated as data-center telemetry or grid-carbon data.
- Sensitivity results depend on the selected synthetic ranges and workload generator; do not generalize beyond the tested assumptions.

## Next research steps

1. Inspect sensitivity results to identify scenarios where emissions reductions weaken or job misses increase.
2. Add paired uncertainty estimates and stronger scheduling baselines.
3. Replace illustrative IT-energy, PUE, and carbon-intensity assumptions with calibrated or authoritative data if suitable sources become available.
4. Consider an RL agent only after the simulator's state, actions, reward, and safety constraints are defined and validated.
