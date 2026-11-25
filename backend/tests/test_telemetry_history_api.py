import unittest
from unittest.mock import patch

import pandas as pd

from backend.live_simulator import export_live_history, live_history
from backend.telemetry import TelemetryStore


class TelemetryHistoryEndpointTests(unittest.TestCase):
    def setUp(self):
        self.store = TelemetryStore(max_history=200)
        history = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2026-01-01 00:00:00",
                    periods=5,
                    freq="h",
                ),
                "total_energy": [100.0, 110.0, 120.0, 130.0, 140.0],
            }
        )
        self.store.replace_history(
            history,
            source="UCI dataset replay",
            mode="simulation",
        )
        self.patch_store = patch(
            "backend.live_simulator.telemetry_store",
            self.store,
        )
        self.patch_store.start()
        self.addCleanup(self.patch_store.stop)

    def test_returns_latest_readings_and_source_metadata(self):
        result = live_history(limit=3)

        self.assertEqual(result["count"], 3)
        self.assertEqual(
            [item["energy"] for item in result["readings"]],
            [120.0, 130.0, 140.0],
        )
        self.assertEqual(result["telemetry"]["source"], "UCI dataset replay")
        self.assertEqual(result["telemetry"]["mode"], "simulation")
        self.assertEqual(result["readings"][-1]["unit"], "kW")

    def test_exports_csv_with_source_metadata(self):
        response = export_live_history(limit=2)

        self.assertEqual(response.media_type, "text/csv")
        self.assertIn("energy_kw,source,mode", response.body.decode("utf-8"))
        self.assertIn("UCI dataset replay", response.body.decode("utf-8"))
        self.assertIn("130.0", response.body.decode("utf-8"))
        self.assertIn("140.0", response.body.decode("utf-8"))

    def test_returns_empty_history_when_store_is_empty(self):
        self.store.replace_history(
            pd.DataFrame(columns=["timestamp", "total_energy"]),
            source="test",
            mode="simulation",
        )

        result = live_history(limit=10)

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["readings"], [])
        self.assertIsNone(result["telemetry"]["reading"])


if __name__ == "__main__":
    unittest.main()
