"""
GreenMind AI research experiment: carbon-aware workload scheduling.

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
    """Create a reproducible synthetic workload shared by all policies."""
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


def generate_pue_profile(seed: int = SEED + 2) -> np.ndarray:
    """Return a synthetic hourly PUE profile; not measured facility data."""
    rng = np.random.default_rng(seed)
    hours = np.arange(HOURS)
    daily_pattern = 1.25 + 0.06 * np.sin(2 * np.pi * (hours - 3) / 24)
    variation = rng.normal(0, 0.015, HOURS)
    return np.clip(daily_pattern + variation, 1.1, 1.5)


def run_policy(
    jobs: list[Job],
    carbon: np.ndarray,
    policy: str,
    pue: np.ndarray | None = None,
    hourly_capacity: int = HOURLY_CAPACITY,
) -> dict:
    """Schedule jobs with a configurable hourly work-capacity limit.

    KWH_PER_WORK_UNIT models IT energy. Facility energy is IT energy multiplied
    by hourly PUE. If no PUE profile is supplied, PUE=1 preserves legacy tests.

    Policies:
    - baseline: arrival order; earliest feasible hour
    - carbon_aware: arrival order; lowest modeled-emissions feasible hour
    - deadline_carbon: earliest-deadline-first; lowest-emissions feasible hour

    deadline_carbon is an offline heuristic, not a real-time scheduler.
    """
    if pue is None:
        pue = np.ones(HOURS, dtype=float)
    if len(carbon) != HOURS or len(pue) != HOURS:
        raise ValueError(f"carbon and pue profiles must each contain {HOURS} values")
    if hourly_capacity <= 0:
        raise ValueError("hourly_capacity must be a positive integer")

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
            if capacity[hour] + job.work <= hourly_capacity
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
                    "pue": None,
                    "it_energy_kwh": 0.0,
                    "energy_kwh": 0.0,
                    "emissions_kg_co2": 0.0,
                }
            )
            continue

        if policy == "baseline":
            chosen_hour = candidates[0]
        else:
            chosen_hour = min(
                candidates,
                key=lambda hour: (
                    pue[hour] * carbon[hour],
                    carbon[hour],
                    hour,
                ),
            )

        capacity[chosen_hour] += job.work
        it_energy = job.work * KWH_PER_WORK_UNIT
        energy = it_energy * float(pue[chosen_hour])
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
                "pue": float(pue[chosen_hour]),
                "it_energy_kwh": it_energy,
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
    pue = generate_pue_profile()

    results = [
        run_policy(jobs, carbon, policy, pue)
        for policy in ("baseline", "carbon_aware", "deadline_carbon")
    ]
    baseline_emissions = results[0]["emissions_kg_co2"]
    summary_rows = []
    for result in results:
        row = {key: value for key, value in result.items() if key != "schedule"}
        row["emissions_reduction_vs_baseline_pct"] = (
            100.0 * (baseline_emissions - result["emissions_kg_co2"]) / baseline_emissions
            if baseline_emissions > 0 else 0.0
        )
        summary_rows.append(row)

    pd.DataFrame(summary_rows).to_csv(
        OUTPUT_DIR / "experiment_summary.csv", index=False
    )
    schedule_rows = [
        {"policy": result["policy"], **row}
        for result in results
        for row in result["schedule"]
    ]
    pd.DataFrame(schedule_rows).to_csv(
        OUTPUT_DIR / "job_schedules.csv", index=False
    )

    print("\nGREENMIND AI — CARBON SCHEDULING EXPERIMENT")
    print("=" * 52)
    print(pd.DataFrame(summary_rows).to_string(index=False))
    print(f"\nResults saved in: {OUTPUT_DIR}")
    print("Limitations: synthetic workload, carbon intensity and PUE profiles;")
    print("fixed illustrative IT energy per work unit; no measured facility data.")


if __name__ == "__main__":
    main()
