"""Shared telemetry state for GreenMind AI.

The store is the boundary between telemetry sources (historical replay today,
real meters/IoT adapters later) and the intelligence layer.
"""

from __future__ import annotations

import math
from threading import RLock
from typing import Any

import pandas as pd


HISTORY_COLUMNS = ["timestamp", "total_energy"]


class TelemetryStore:
    """Thread-safe, in-memory store for validated energy observations."""

    def __init__(self, max_history: int = 1000) -> None:
        if max_history < 168:
            raise ValueError("max_history must be at least 168 hours.")

        self.max_history = max_history
        self._lock = RLock()
        self._history = pd.DataFrame(columns=HISTORY_COLUMNS)
        self._source = "unknown"
        self._mode = "uninitialized"
        self._updated_at: str | None = None

    @staticmethod
    def _normalize_history(history: pd.DataFrame) -> pd.DataFrame:
        missing = set(HISTORY_COLUMNS) - set(history.columns)
        if missing:
            raise ValueError(
                "Telemetry history is missing columns: "
                + ", ".join(sorted(missing))
            )

        data = history[HISTORY_COLUMNS].copy()
        data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce")
        data["total_energy"] = pd.to_numeric(
            data["total_energy"], errors="coerce"
        )
        data = data.dropna(subset=HISTORY_COLUMNS)

        if not data["total_energy"].map(math.isfinite).all():
            raise ValueError("Energy readings must be finite numbers.")
        if (data["total_energy"] < 0).any():
            raise ValueError("Energy readings cannot be negative.")

        return (
            data.drop_duplicates(subset=["timestamp"], keep="last")
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

    def replace_history(
        self,
        history: pd.DataFrame,
        *,
        source: str,
        mode: str,
    ) -> dict[str, Any]:
        """Replace the active history with a source's current known history."""
        if not source or not mode:
            raise ValueError("Telemetry source and mode are required.")

        data = self._normalize_history(history).tail(self.max_history).copy()

        with self._lock:
            self._history = data.reset_index(drop=True)
            self._source = source
            self._mode = mode
            self._updated_at = (
                str(self._history.iloc[-1]["timestamp"])
                if not self._history.empty
                else None
            )
            return self.snapshot()

    def append_reading(
        self,
        timestamp: Any,
        energy_kw: float,
        *,
        source: str,
        mode: str,
    ) -> dict[str, Any]:
        """Append one validated reading from a streaming telemetry adapter."""
        parsed_timestamp = pd.to_datetime(timestamp, errors="coerce")
        value = float(energy_kw)

        if pd.isna(parsed_timestamp):
            raise ValueError("A valid telemetry timestamp is required.")
        if not math.isfinite(value) or value < 0:
            raise ValueError("Energy reading must be a finite, non-negative number.")
        if not source or not mode:
            raise ValueError("Telemetry source and mode are required.")

        reading = pd.DataFrame(
            [{"timestamp": parsed_timestamp, "total_energy": value}]
        )

        with self._lock:
            if not self._history.empty:
                latest = self._history.iloc[-1]["timestamp"]
                if parsed_timestamp <= latest:
                    raise ValueError(
                        "New telemetry timestamps must be later than the latest reading."
                    )

            combined = pd.concat([self._history, reading], ignore_index=True)
            self._history = combined.tail(self.max_history).reset_index(drop=True)
            self._source = source
            self._mode = mode
            self._updated_at = str(parsed_timestamp)
            return self.snapshot()

    def get_history(self) -> pd.DataFrame:
        """Return a defensive copy of the currently available observations."""
        with self._lock:
            return self._history.copy(deep=True)

    def snapshot(self) -> dict[str, Any]:
        """Return current reading and source metadata in API-friendly form."""
        with self._lock:
            if self._history.empty:
                reading = None
            else:
                latest = self._history.iloc[-1]
                reading = {
                    "timestamp": str(latest["timestamp"]),
                    "energy": round(float(latest["total_energy"]), 2),
                    "unit": "kW",
                }

            return {
                "reading": reading,
                "source": self._source,
                "mode": self._mode,
                "updated_at": self._updated_at,
                "history_length": int(len(self._history)),
            }


telemetry_store = TelemetryStore()
