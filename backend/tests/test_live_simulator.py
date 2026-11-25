import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backend.live_simulator import EnergyStreamSimulator
from backend.telemetry import TelemetryStore


class EnergyStreamSimulatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dataset_path = Path(self.temp_dir.name) / "hourly_energy.csv"

        timestamps = pd.date_range(
            "2026-01-01 00:00:00",
            periods=172,
            freq="h",
        )
        pd.DataFrame(
            {
                "timestamp": timestamps,
                "total_energy": [float(1000 + index) for index in range(172)],
            }
        ).to_csv(self.dataset_path, index=False)

        self.store = TelemetryStore(max_history=200)
        self.telemetry_patch = patch(
            "backend.live_simulator.telemetry_store",
            self.store,
        )
        self.telemetry_patch.start()
        self.addCleanup(self.telemetry_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

        self.simulator = EnergyStreamSimulator(self.dataset_path)

    def test_current_publishes_initial_history(self):
        reading = self.simulator.current()
        snapshot = self.store.snapshot()

        self.assertEqual(reading["stream_position"], 168)
        self.assertEqual(reading["timestamp"], "2026-01-08 00:00:00")
        self.assertEqual(snapshot["reading"]["energy"], 1168.0)
        self.assertEqual(snapshot["history_length"], 169)
        self.assertEqual(snapshot["source"], "UCI dataset replay")
        self.assertEqual(snapshot["mode"], "simulation")

    def test_advance_publishes_next_observation(self):
        reading = self.simulator.advance()
        snapshot = self.store.snapshot()

        self.assertEqual(reading["stream_position"], 169)
        self.assertEqual(reading["energy"], 1169.0)
        self.assertEqual(snapshot["reading"]["energy"], 1169.0)
        self.assertEqual(snapshot["history_length"], 170)

    def test_reset_returns_to_initial_valid_position(self):
        self.simulator.advance()
        reading = self.simulator.reset()
        snapshot = self.store.snapshot()

        self.assertEqual(reading["stream_position"], 168)
        self.assertEqual(reading["energy"], 1168.0)
        self.assertEqual(snapshot["history_length"], 169)

    def test_simulator_rejects_dataset_with_insufficient_history(self):
        short_path = Path(self.temp_dir.name) / "short.csv"
        pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2026-01-01 00:00:00",
                    periods=168,
                    freq="h",
                ),
                "total_energy": [100.0] * 168,
            }
        ).to_csv(short_path, index=False)

        with self.assertRaisesRegex(ValueError, "at least 169"):
            EnergyStreamSimulator(short_path)


if __name__ == "__main__":
    unittest.main()
