"""Regression tests for next-hour forecasting feature alignment."""

import unittest

import numpy as np
import pandas as pd

from data.create_features import build_features


class FeatureEngineeringTests(unittest.TestCase):
    def setUp(self):
        self.source = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2011-01-01 00:00:00", periods=200, freq="h"
                ),
                "total_energy": np.arange(200, dtype=float),
            }
        )
        self.features = build_features(self.source)

    def test_lags_and_rolling_windows_align_to_next_hour_target(self):
        # The first complete row corresponds to source row 167.
        row = self.features.iloc[0]
        self.assertEqual(row["timestamp"], pd.Timestamp("2011-01-07 23:00:00"))
        self.assertEqual(row["lag_1"], 167.0)
        self.assertEqual(row["lag_24"], 144.0)
        self.assertEqual(row["lag_168"], 0.0)
        self.assertAlmostEqual(row["rolling_mean_24"], np.mean(np.arange(144, 168)))
        self.assertAlmostEqual(row["rolling_mean_168"], np.mean(np.arange(168)))
        self.assertAlmostEqual(row["target"], 168.0)

    def test_calendar_features_describe_target_hour(self):
        row = self.features.iloc[0]
        target_timestamp = pd.Timestamp("2011-01-08 00:00:00")
        self.assertEqual(row["hour"], target_timestamp.hour)
        self.assertEqual(row["day_of_week"], target_timestamp.day_of_week)
        self.assertEqual(row["day_of_month"], target_timestamp.day)
        self.assertEqual(row["month"], target_timestamp.month)
        self.assertEqual(row["is_weekend"], 1)

    def test_feature_builder_does_not_mutate_input(self):
        original = self.source.copy(deep=True)
        build_features(self.source)
        pd.testing.assert_frame_equal(self.source, original)


if __name__ == "__main__":
    unittest.main()
