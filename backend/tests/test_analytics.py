import unittest
from unittest.mock import patch

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.analytics import build_load_shift_scenario, build_overview, router


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=240, freq="h"),
            "total_energy": [float(100 + (index % 24) * 5 + (index % 7)) for index in range(240)],
        })

    def test_overview_returns_period_stats_and_profiles(self):
        result = build_overview(self.history, days=7)
        self.assertEqual(result["period_days"], 7)
        self.assertGreater(result["current_period"]["observations"], 0)
        self.assertTrue(result["daily"])
        self.assertTrue(result["hourly_profile"])
        self.assertIn("energy_kwh", result["current_period"])


    def test_overview_query_accepts_supported_integer_days_and_rejects_others(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("backend.analytics._history", return_value=self.history):
            valid = client.get("/api/analytics/overview?days=7")
            invalid = client.get("/api/analytics/overview?days=14")
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()["period_days"], 7)
        self.assertEqual(invalid.status_code, 422)

    def test_load_shift_conserves_total_energy_and_reports_peak(self):
        result = build_load_shift_scenario(self.history, 0.10)
        self.assertTrue(result["energy_conserved"])
        self.assertAlmostEqual(
            result["baseline"]["total_energy_kwh"],
            result["simulated"]["total_energy_kwh"],
            places=5,
        )
        self.assertGreater(result["moved_energy_kwh"], 0)
        self.assertIn("limitations", result)

    def test_load_shift_rejects_invalid_fraction(self):
        with self.assertRaises(ValueError):
            build_load_shift_scenario(self.history, 0.5)


if __name__ == "__main__":
    unittest.main()
