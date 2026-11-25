"""Configurable electricity-grid carbon-intensity provider.

Electricity Maps is queried only when both an API token and a zone are
configured. Otherwise GreenMind uses its documented fallback factor.
"""

from __future__ import annotations

import json
import os
import time
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FALLBACK_INTENSITY_GCO2_PER_KWH = 676.0
DEFAULT_API_BASE_URL = "https://api.electricitymaps.com/v5"


class CarbonIntensityProvider:
    """Fetch grid carbon intensity with a safe, explicit fallback."""

    def __init__(self, cache_seconds: int = 900) -> None:
        self.cache_seconds = cache_seconds
        self._lock = RLock()
        self._cached_result: dict | None = None
        self._cached_at = 0.0

    def get_intensity(self) -> dict:
        token = os.getenv("ELECTRICITY_MAPS_API_TOKEN", "").strip()
        zone = os.getenv("ELECTRICITY_MAPS_ZONE", "").strip()

        if not token or not zone:
            missing = []
            if not token:
                missing.append("ELECTRICITY_MAPS_API_TOKEN")
            if not zone:
                missing.append("ELECTRICITY_MAPS_ZONE")
            return self._fallback(
                "Configure " + " and ".join(missing) + " to enable live grid data."
            )

        with self._lock:
            if (
                self._cached_result is not None
                and time.monotonic() - self._cached_at < self.cache_seconds
            ):
                return dict(self._cached_result)

            try:
                result = self._fetch_latest(token, zone)
                self._cached_result = result
                self._cached_at = time.monotonic()
                return dict(result)
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                return self._fallback(
                    f"Electricity Maps request unavailable ({type(exc).__name__})."
                )
            except Exception:
                # Provider failures must never take the dashboard offline.
                return self._fallback("Electricity Maps request failed unexpectedly.")

    def _fetch_latest(self, token: str, zone: str) -> dict:
        base_url = os.getenv(
            "ELECTRICITY_MAPS_API_BASE_URL",
            DEFAULT_API_BASE_URL,
        ).rstrip("/")
        query = urlencode({"zone": zone})
        request = Request(
            f"{base_url}/carbon-intensity/latest?{query}",
            headers={
                "auth-token": token,
                "Accept": "application/json",
                "User-Agent": "GreenMind-AI/1.0",
            },
            method="GET",
        )

        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        value = payload.get("carbonIntensity")
        if value is None:
            value = payload.get("carbon_intensity")
        intensity = float(value)
        if intensity <= 0:
            raise ValueError("Provider returned a non-positive carbon intensity.")

        return {
            "carbon_intensity_gco2_per_kwh": round(intensity, 3),
            "source": "electricity_maps",
            "source_label": "Electricity Maps",
            "mode": "external_grid_data",
            "zone": payload.get("zone", zone),
            "datetime": payload.get("datetime"),
            "is_estimated": bool(payload.get("isEstimated", False)),
            "is_fallback": False,
            "fallback_reason": None,
            "emission_factor_type": payload.get("emissionFactorType", "lifecycle"),
        }

    @staticmethod
    def _fallback(reason: str) -> dict:
        return {
            "carbon_intensity_gco2_per_kwh": FALLBACK_INTENSITY_GCO2_PER_KWH,
            "source": "configured_fallback",
            "source_label": "GreenMind fallback factor",
            "mode": "fallback_estimate",
            "zone": None,
            "datetime": None,
            "is_estimated": True,
            "is_fallback": True,
            "fallback_reason": reason,
            "emission_factor_type": "legacy_fixed_factor",
        }


carbon_intensity_provider = CarbonIntensityProvider()
