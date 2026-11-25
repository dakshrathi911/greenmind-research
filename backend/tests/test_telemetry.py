import unittest

import pandas as pd

from backend.telemetry import TelemetryStore


class TelemetryStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = TelemetryStore(max_history=168)

    def test_replace_history_sorts_and_reports_latest_reading(self):
        history = pd.DataFrame(
            {
                "timestamp": [
                    "2026-01-01 02:00:00",
                    "2026-01-01 01:00:00",
                ],
                "total_energy": [120.0, 100.0],
            }
        )

        result = self.store.replace_history(
            history, source="test", mode="simulation"
        )

        self.assertEqual(result["reading"]["energy"], 120.0)
        self.assertEqual(result["history_length"], 2)
        self.assertEqual(result["source"], "test")

    def test_append_reading_updates_current_value(self):
        self.store.append_reading(
            "2026-01-01 01:00:00",
            100,
            source="test",
            mode="simulation",
        )
        result = self.store.append_reading(
            "2026-01-01 02:00:00",
            110,
            source="test",
            mode="simulation",
        )

        self.assertEqual(result["reading"]["energy"], 110.0)
        self.assertEqual(result["history_length"], 2)

    def test_append_rejects_non_increasing_timestamp(self):
        self.store.append_reading(
            "2026-01-01 01:00:00",
            100,
            source="test",
            mode="simulation",
        )

        with self.assertRaises(ValueError):
            self.store.append_reading(
                "2026-01-01 01:00:00",
                105,
                source="test",
                mode="simulation",
            )

    def test_append_rejects_negative_and_infinite_values(self):
        for value in (-1, float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.store.append_reading(
                        "2026-01-01 01:00:00",
                        value,
                        source="test",
                        mode="simulation",
                    )

    def test_history_is_returned_as_a_copy(self):
        self.store.append_reading(
            "2026-01-01 01:00:00",
            100,
            source="test",
            mode="simulation",
        )

        history = self.store.get_history()
        history.loc[0, "total_energy"] = 999

        self.assertEqual(
            self.store.snapshot()["reading"]["energy"],
            100.0,
        )


if __name__ == "__main__":
    unittest.main()
