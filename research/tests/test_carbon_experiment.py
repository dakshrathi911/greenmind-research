"""Regression tests for GreenMind AI's synthetic scheduling simulator."""

import unittest

import numpy as np

from research.carbon_experiment import (
    HOURS,
    HOURLY_CAPACITY,
    KWH_PER_WORK_UNIT,
    Job,
    generate_carbon_intensity,
    generate_pue_profile,
    generate_workload,
    run_policy,
)


class WorkloadGenerationTests(unittest.TestCase):
    def test_workload_generation_is_reproducible(self):
        self.assertEqual(
            generate_workload(seed=7, count=20),
            generate_workload(seed=7, count=20),
        )

    def test_carbon_profile_is_reproducible_and_bounded(self):
        first = generate_carbon_intensity(seed=8)
        second = generate_carbon_intensity(seed=8)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(len(first), HOURS)
        self.assertTrue(np.all(first >= 0.15))
        self.assertTrue(np.all(first <= 0.8))

    def test_pue_profile_is_reproducible_and_bounded(self):
        first = generate_pue_profile(seed=9)
        second = generate_pue_profile(seed=9)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(len(first), HOURS)
        self.assertTrue(np.all(first >= 1.1))
        self.assertTrue(np.all(first <= 1.5))


class SchedulingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.carbon = np.linspace(0.2, 0.6, HOURS)

    def test_unknown_policy_raises_value_error(self):
        with self.assertRaises(ValueError):
            run_policy([], self.carbon, "not-a-policy")

    def test_scheduled_jobs_respect_arrival_deadline_and_capacity(self):
        jobs = [
            Job(job_id=1, arrival=0, deadline=2, work=7),
            Job(job_id=2, arrival=0, deadline=1, work=5),
            Job(job_id=3, arrival=1, deadline=2, work=4),
        ]
        result = run_policy(jobs, self.carbon, "carbon_aware")
        used = np.zeros(HOURS, dtype=int)

        self.assertEqual(result["jobs_completed"] + result["jobs_missed"], len(jobs))
        for row in result["schedule"]:
            if row["status"] != "completed":
                continue
            hour = row["scheduled_hour"]
            self.assertGreaterEqual(hour, row["arrival_hour"])
            self.assertLessEqual(hour, row["deadline_hour"])
            used[hour] += row["work_units"]

        self.assertTrue(np.all(used <= HOURLY_CAPACITY))

    def test_configurable_hourly_capacity_is_enforced(self):
        jobs = [
            Job(job_id=1, arrival=0, deadline=1, work=5),
            Job(job_id=2, arrival=0, deadline=1, work=5),
            Job(job_id=3, arrival=0, deadline=1, work=5),
        ]
        result = run_policy(jobs, self.carbon, "baseline", hourly_capacity=8)
        used = np.zeros(HOURS, dtype=int)
        for row in result["schedule"]:
            if row["status"] == "completed":
                used[row["scheduled_hour"]] += row["work_units"]
        self.assertTrue(np.all(used <= 8))

    def test_nonpositive_hourly_capacity_raises_value_error(self):
        with self.assertRaises(ValueError):
            run_policy([], self.carbon, "baseline", hourly_capacity=0)

    def test_energy_and_emissions_match_scheduled_jobs(self):
        jobs = [
            Job(job_id=1, arrival=0, deadline=2, work=2),
            Job(job_id=2, arrival=1, deadline=3, work=3),
        ]
        result = run_policy(jobs, self.carbon, "carbon_aware")
        completed = [row for row in result["schedule"] if row["status"] == "completed"]
        expected_energy = sum(row["work_units"] * KWH_PER_WORK_UNIT for row in completed)
        expected_emissions = sum(
            row["energy_kwh"] * row["carbon_intensity_kg_per_kwh"]
            for row in completed
        )
        self.assertAlmostEqual(result["energy_kwh"], expected_energy)
        self.assertAlmostEqual(result["emissions_kg_co2"], expected_emissions)

    def test_pue_scales_facility_energy_and_emissions(self):
        jobs = [Job(job_id=1, arrival=0, deadline=0, work=2)]
        pue = np.full(HOURS, 1.3)
        result = run_policy(jobs, self.carbon, "baseline", pue)
        row = result["schedule"][0]
        expected_it_energy = 2 * KWH_PER_WORK_UNIT
        self.assertAlmostEqual(row["it_energy_kwh"], expected_it_energy)
        self.assertAlmostEqual(row["energy_kwh"], expected_it_energy * 1.3)
        self.assertAlmostEqual(
            result["emissions_kg_co2"],
            row["energy_kwh"] * row["carbon_intensity_kg_per_kwh"],
        )

    def test_invalid_profile_lengths_raise_value_error(self):
        jobs = [Job(job_id=1, arrival=0, deadline=0, work=1)]
        with self.assertRaises(ValueError):
            run_policy(jobs, self.carbon[:-1], "baseline")
        with self.assertRaises(ValueError):
            run_policy(jobs, self.carbon, "baseline", np.ones(HOURS - 1))

    def test_deadline_carbon_regression_for_seed_28(self):
        jobs = generate_workload(seed=28)
        carbon = generate_carbon_intensity(seed=29)
        pue = generate_pue_profile(seed=30)
        baseline = run_policy(jobs, carbon, "baseline", pue)
        carbon_aware = run_policy(jobs, carbon, "carbon_aware", pue)
        deadline_carbon = run_policy(jobs, carbon, "deadline_carbon", pue)

        self.assertEqual(baseline["jobs_missed"], 0)
        self.assertEqual(carbon_aware["jobs_missed"], 1)
        self.assertEqual(deadline_carbon["jobs_missed"], 0)
        self.assertLess(
            deadline_carbon["emissions_kg_co2"],
            baseline["emissions_kg_co2"],
        )

    def test_deadline_carbon_completes_all_jobs_for_evaluation_seeds(self):
        for seed in range(30):
            with self.subTest(seed=seed):
                jobs = generate_workload(seed=seed, count=240)
                carbon = generate_carbon_intensity(seed=seed + 1)
                pue = generate_pue_profile(seed=seed + 2)
                result = run_policy(jobs, carbon, "deadline_carbon", pue)
                self.assertEqual(result["jobs_missed"], 0)


if __name__ == "__main__":
    unittest.main()
