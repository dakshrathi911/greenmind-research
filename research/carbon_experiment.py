"""
GreenMind AI research experiment: carbon-aware workload scheduling.

This experiment compares:
- baseline: earliest feasible hour
- carbon-aware heuristic: lowest-carbon feasible hour

All workload and carbon-intensity inputs are synthetic. Results are
illustrative and must not be reported as measured real-world savings.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
HOURS = 168
HOURLY_CAPACITY = 12
KWH_PER_WORK_UNIT = 0.8
OUTPUT_DIR = Path(__file__).resolve().parent / "results"


@dataclass(frozen=True)
class Job:
    job_id: int
    arrival: int
    deadline: int
    work: int


def generate_workload(seed: int = SEED, count: int = 240) -> list[Job]:
    """Create a reproducible synthetic workload shared by both policies."""
    rng = np.random.default_rng(seed)
    jobs = []

    for job_id in range(1, count + 1):
        arrival = int(rng.integers(0, HOURS - 8))
        work = int(rng.integers(1, 5))
        slack = int(rng.integers(2, 9))
        jobs.append(
            Job(
                job_id=job_id,
                arrival=arrival,
                deadline=min(arrival + slack, HOURS - 1),
                work=work,
            )
        )

    return sorted(jobs, key=lambda job: (job.arrival, job.job_id))


def generate_carbon_intensity(seed: int = SEED + 1) -> np.ndarray:
    """Return synthetic kg CO2/kWh values; not measured grid data."""
    rng = np.random.default_rng(seed)
    hours = np.arange(HOURS)
    daily_pattern = 0.42 + 0.16 * np.sin(2 * np.pi * (hours - 7) / 24)
    variation = rng.normal(0, 0.025, HOURS)
    return np.clip(daily_pattern + variation, 0.15, 0.8)


def run_policy(jobs: list[Job], carbon: np.ndarray, policy: str) -> dict:
    """Schedule jobs under a shared per-hour capacity constraint.

    Policies:
    - baseline: process jobs in arrival order; use the earliest feasible hour
    - carbon_aware: process jobs in arrival order; use the lowest-carbon hour
    - deadline_carbon: process earliest deadlines first; use the lowest-carbon
      feasible hour for each job
    """
    capacity = np.zeros(HOURS, dtype=int)
    schedule = []
    total_energy = 0.0
    total_emissions = 0.0
    missed_deadlines = 0

    if policy == "deadline_carbon":
        ordered_jobs = sorted(
            jobs, key=lambda job: (job.deadline, job.arrival, job.job_id)
        )
    elif policy in ("baseline", "carbon_aware"):
        ordered_jobs = jobs
    else:
        raise ValueError(f"Unknown policy: {policy}")

    for job in ordered_jobs:
        candidates = [
            hour
            for hour in range(job.arrival, job.deadline + 1)
            if capacity[hour] + job.work <= HOURLY_CAPACITY
        ]

        if not candidates:
            missed_deadlines += 1
            schedule.append(
                {
                    "job_id": job.job_id,
                    "arrival_hour": job.arrival,
                    "deadline_hour": job.deadline,
                    "work_units": job.work,
                    "scheduled_hour": None,
                    "status": "missed",
                    "carbon_intensity_kg_per_kwh": None,
                    "energy_kwh": 0.0,
                    "emissions_kg_co2": 0.0,
                }
            )
            continue

        if policy == "baseline":
            chosen_hour = candidates[0]
        else:
            chosen_hour = min(
                candidates, key=lambda hour: (carbon[hour], hour)
            )

        capacity[chosen_hour] += job.work
        energy = job.work * KWH_PER_WORK_UNIT
        emissions = energy * float(carbon[chosen_hour])
        total_energy += energy
        total_emissions += emissions

        schedule.append(
            {
                "job_id": job.job_id,
                "arrival_hour": job.arrival,
                "deadline_hour": job.deadline,
                "work_units": job.work,
                "scheduled_hour": chosen_hour,
                "status": "completed",
                "carbon_intensity_kg_per_kwh": float(carbon[chosen_hour]),
                "energy_kwh": energy,
                "emissions_kg_co2": emissions,
            }
        )

    completed = len(jobs) - missed_deadlines
    return {
        "policy": policy,
        "jobs_total": len(jobs),
        "jobs_completed": completed,
        "jobs_missed": missed_deadlines,
        "completion_rate_pct": 100.0 * completed / len(jobs) if jobs else 0.0,
        "energy_kwh": total_energy,
        "emissions_kg_co2": total_emissions,
        "schedule": schedule,
    }

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = generate_workload()
    carbon = generate_carbon_intensity()

    baseline = run_policy(jobs, carbon, "baseline")
    carbon_aware = run_policy(jobs, carbon, "carbon_aware")

    baseline_emissions = baseline["emissions_kg_co2"]
    aware_emissions = carbon_aware["emissions_kg_co2"]
    reduction_pct = (
        100.0 * (baseline_emissions - aware_emissions) / baseline_emissions
        if baseline_emissions > 0
        else 0.0
    )

    summary_rows = []
    for result in (baseline, carbon_aware):
        summary_rows.append(
            {
                key: value
                for key, value in result.items()
                if key != "schedule"
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary["emissions_reduction_vs_baseline_pct"] = [0.0, reduction_pct]
    summary.to_csv(OUTPUT_DIR / "experiment_summary.csv", index=False)

    schedule_rows = []
    for result in (baseline, carbon_aware):
        for row in result["schedule"]:
            schedule_rows.append({"policy": result["policy"], **row})

    pd.DataFrame(schedule_rows).to_csv(
        OUTPUT_DIR / "job_schedules.csv", index=False
    )

    print("\nGREENMIND AI — CARBON SCHEDULING EXPERIMENT")
    print("=" * 52)
    print(summary.to_string(index=False))
    print(f"\nResults saved in: {OUTPUT_DIR}")
    print("  - experiment_summary.csv")
    print("  - job_schedules.csv")
    print("\nLimitations: synthetic workload, synthetic carbon intensity,")
    print("and a fixed illustrative energy-per-work-unit assumption.")


if __name__ == "__main__":
    main()
