# Carbon-aware scheduling experiment

This folder contains the first reproducible research experiment for GreenMind AI.

## Policies compared

- **Baseline:** assigns each job to the earliest feasible hour.
- **Carbon-aware heuristic:** assigns each job to the feasible hour with the lowest configured carbon intensity.

Both policies use the same generated jobs, hourly capacity limit, deadline windows, and carbon-intensity series. This makes the initial comparison controlled and repeatable.

## Run locally

From the repository root, with the project's Python dependencies installed:

```powershell
python .\research\carbon_experiment.py
```

The script writes:

- `research/results/experiment_summary.csv` — aggregate completion, energy, and emissions metrics.
- `research/results/job_schedules.csv` — per-job scheduling decisions and calculated emissions.

Generated results are local experiment outputs and are not required to run the script.

## Assumptions and limitations

- Workloads are synthetic and generated with a fixed random seed.
- Grid carbon intensity is a synthetic illustrative profile, in kg CO2/kWh.
- Each work unit consumes a fixed 0.8 kWh; this is a modeling assumption, not a calibrated data-center power model.
- Jobs are indivisible and must be scheduled within their arrival-to-deadline window.
- Hourly capacity is limited to 12 work units.
- This is a heuristic, not reinforcement learning, and the experiment does not establish real-world carbon savings.
- The current historical electricity dataset in the parent project is not automatically treated as data-center telemetry or grid-carbon data.

## Next research steps

1. Add unit tests and repeated-seed evaluation.
2. Add a configurable power/cooling model and service-level constraints.
3. Add a clearly documented measured or authoritative time-series for grid carbon intensity, if available.
4. Compare against stronger baselines and report uncertainty across trials.
5. Consider an RL agent only after the simulator's state, actions, reward, and safety constraints are defined and validated.
