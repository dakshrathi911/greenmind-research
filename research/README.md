# Carbon-aware scheduling experiment

This folder contains the first reproducible research experiment for GreenMind AI.

## Policies compared

- **Baseline:** processes jobs in arrival order and assigns each to the earliest feasible hour.
- **Carbon-aware heuristic:** processes jobs in arrival order and assigns each to its lowest-carbon feasible hour.
- **Deadline-aware carbon heuristic:** processes jobs in earliest-deadline-first order, then assigns each job to the feasible hour with the lowest modeled emissions per work unit.

The model treats 0.8 kWh per work unit as illustrative IT energy and multiplies it by a synthetic hourly power usage effectiveness (PUE) profile to estimate facility energy. PUE is a simplified cooling/overhead proxy, not a detailed thermal or cooling-system simulation.

All policies use the same generated workload, hourly capacity limit, deadline windows, and carbon-intensity series within each trial. The deadline-aware policy is an offline heuristic because it sorts the full workload before scheduling; it is not a real-time scheduler.

## Run locally

From the repository root, with the project's Python dependencies installed:

```powershell
python .\research\carbon_experiment.py
```

Run the repeated-seed evaluation (30 paired synthetic trials) from the repository root:

```powershell
python .\\research\\multi_seed_experiment.py
```

Run the automated regression tests from the repository root:

```powershell
python -m unittest discover -s research/tests -v
```

The tests cover reproducibility, carbon and PUE profile bounds, deadline and capacity constraints, facility-energy and emissions calculations, invalid policy names, and regression behavior across the 30 evaluation seeds.

The single-run script writes:

- `research/results/experiment_summary.csv` — aggregate completion, energy, and emissions metrics.
- `research/results/job_schedules.csv` — per-job scheduling decisions and calculated emissions.

Generated results are local experiment outputs and are not required to run the script.

## Assumptions and limitations

- Workloads are synthetic and generated with a fixed random seed.
- Grid carbon intensity is a synthetic illustrative profile, in kg CO2/kWh.
- Each work unit consumes a fixed illustrative 0.8 kWh of IT energy; this is not a calibrated server power model.
- Hourly facility energy is estimated as IT energy multiplied by a synthetic PUE profile bounded between 1.1 and 1.5. This approximates facility overhead and does not simulate cooling physics or measured facility behavior.
- Jobs are indivisible and must be scheduled within their arrival-to-deadline window.
- Hourly capacity is limited to 12 work units.
- This is a heuristic, not reinforcement learning, and the experiment does not establish real-world carbon savings.
- The current historical electricity dataset in the parent project is not automatically treated as data-center telemetry or grid-carbon data.

## Next research steps

1. Extend tests as the simulator's constraints and scheduling policies evolve.
2. Replace the illustrative IT-energy and PUE assumptions with calibrated power/cooling inputs and service-level constraints, if suitable data is available.
3. Add a clearly documented measured or authoritative time-series for grid carbon intensity, if available.
4. Compare against stronger baselines and report uncertainty across trials.
5. Consider an RL agent only after the simulator's state, actions, reward, and safety constraints are defined and validated.
