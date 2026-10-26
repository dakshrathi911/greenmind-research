"""Tests for matched-service emissions accounting."""

import unittest

from research.carbon_experiment import Job
from research.matched_service_analysis import (
    benjamini_hochberg,
    matched_service_metrics,
)


class MatchedServiceAnalysisTests(unittest.TestCase):
    def test_uses_only_jobs_completed_by_every_policy(self):
        jobs = [
            Job(job_id=1, arrival=0, deadline=1, work=2),
            Job(job_id=2, arrival=0, deadline=1, work=3),
        ]
        results = {
            "baseline": {
                "schedule": [
                    {"job_id": 1, "status": "completed", "work_units": 2, "emissions_kg_co2": 2.0},
                    {"job_id": 2, "status": "completed", "work_units": 3, "emissions_kg_co2": 4.0},
                ],
                "emissions_kg_co2": 6.0,
                "jobs_missed": 0,
                "completed_work_units": 5,
            },
            "carbon_aware": {
                "schedule": [
                    {"job_id": 1, "status": "completed", "work_units": 2, "emissions_kg_co2": 1.0},
                    {"job_id": 2, "status": "missed", "work_units": 3, "emissions_kg_co2": 0.0},
                ],
                "emissions_kg_co2": 1.0,
                "jobs_missed": 1,
                "completed_work_units": 2,
            },
            "deadline_carbon": {
                "schedule": [
                    {"job_id": 1, "status": "completed", "work_units": 2, "emissions_kg_co2": 1.5},
                    {"job_id": 2, "status": "completed", "work_units": 3, "emissions_kg_co2": 3.0},
                ],
                "emissions_kg_co2": 4.5,
                "jobs_missed": 0,
                "completed_work_units": 5,
            },
        }

        metrics = matched_service_metrics(jobs, results)
        self.assertEqual(metrics["common_completed_jobs"], 1)
        self.assertEqual(metrics["common_completed_work_units"], 2)
        self.assertAlmostEqual(metrics["common_job_coverage_pct"], 50.0)
        self.assertAlmostEqual(metrics["common_work_coverage_pct"], 40.0)
        self.assertAlmostEqual(metrics["baseline_matched_emissions_kg_co2"], 2.0)
        self.assertAlmostEqual(metrics["carbon_aware_matched_reduction_pct"], 50.0)
        self.assertAlmostEqual(metrics["deadline_carbon_matched_reduction_pct"], 25.0)
        self.assertAlmostEqual(
            metrics["deadline_minus_carbon_aware_matched_reduction_pp"], -25.0
        )

    def test_no_common_jobs_returns_nan_reductions(self):
        jobs = [Job(job_id=1, arrival=0, deadline=0, work=2)]
        results = {
            policy: {
                "schedule": [
                    {"job_id": 1, "status": "missed", "work_units": 2, "emissions_kg_co2": 0.0}
                ],
                "emissions_kg_co2": 0.0,
                "jobs_missed": 1,
                "completed_work_units": 0,
            }
            for policy in ("baseline", "carbon_aware", "deadline_carbon")
        }
        metrics = matched_service_metrics(jobs, results)
        self.assertEqual(metrics["common_completed_jobs"], 0)
        self.assertEqual(metrics["common_completed_work_units"], 0)
        self.assertTrue(__import__("math").isnan(metrics["carbon_aware_matched_reduction_pct"]))

    def test_benjamini_hochberg_adjustment_is_monotonic_in_rank_order(self):
        adjusted = benjamini_hochberg([0.01, 0.04, 0.03, float("nan")])
        self.assertAlmostEqual(adjusted[0], 0.03)
        self.assertAlmostEqual(adjusted[1], 0.04)
        self.assertAlmostEqual(adjusted[2], 0.04)
        self.assertTrue(__import__("math").isnan(adjusted[3]))


if __name__ == "__main__":
    unittest.main()
