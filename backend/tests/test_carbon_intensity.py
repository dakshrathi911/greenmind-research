import json
import os
import unittest
from unittest.mock import patch

from backend.carbon_intensity import (
    CarbonIntensityProvider,
    FALLBACK_INTENSITY_GCO2_PER_KWH,
)


class CarbonIntensityProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = CarbonIntensityProvider(cache_seconds=0)

    def test_uses_explicit_fallback_when_configuration_is_missing(self):
        with patch.dict(
            os.environ,
            {
                "ELECTRICITY_MAPS_API_TOKEN": "",
                "ELECTRICITY_MAPS_ZONE": "",
            },
            clear=False,
        ):
            result = self.provider.get_intensity()

        self.assertTrue(result["is_fallback"])
        self.assertEqual(
            result["carbon_intensity_gco2_per_kwh"],
            FALLBACK_INTENSITY_GCO2_PER_KWH,
        )
        self.assertIn("ELECTRICITY_MAPS_API_TOKEN", result["fallback_reason"])

    def test_parses_external_carbon_intensity(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(
                    {
                        "carbonIntensity": 412.5,
                        "zone": "TEST",
                        "datetime": "2026-11-25T10:00:00Z",
                        "isEstimated": False,
                    }
                ).encode("utf-8")

        with patch.dict(
            os.environ,
            {
                "ELECTRICITY_MAPS_API_TOKEN": "test-token",
                "ELECTRICITY_MAPS_ZONE": "TEST",
            },
            clear=False,
        ), patch("backend.carbon_intensity.urlopen", return_value=FakeResponse()) as request:
            result = self.provider.get_intensity()

        self.assertFalse(result["is_fallback"])
        self.assertEqual(result["carbon_intensity_gco2_per_kwh"], 412.5)
        self.assertEqual(result["zone"], "TEST")
        self.assertEqual(request.call_args.kwargs["timeout"], 5)

    def test_provider_failure_returns_fallback(self):
        with patch.dict(
            os.environ,
            {
                "ELECTRICITY_MAPS_API_TOKEN": "test-token",
                "ELECTRICITY_MAPS_ZONE": "TEST",
            },
            clear=False,
        ), patch(
            "backend.carbon_intensity.urlopen",
            side_effect=TimeoutError("network unavailable"),
        ):
            result = self.provider.get_intensity()

        self.assertTrue(result["is_fallback"])
        self.assertIn("unavailable", result["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
