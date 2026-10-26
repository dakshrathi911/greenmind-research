# ============================================================
# GREENMIND AI
# LIVE DATA SIMULATOR
# ============================================================
# Replays the processed UCI electricity dataset as a streaming
# telemetry source for development and demonstration.
#
# This module does NOT claim that the UCI dataset is live.
# It provides a replaceable interface that can later be connected
# to smart meters, IoT devices, or another real-time data source.
# ============================================================

from pathlib import Path
from threading import Lock

import pandas as pd
from fastapi import APIRouter


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "hourly_energy.csv"

router = APIRouter(prefix="/api/live", tags=["Live Telemetry"])


class EnergyStreamSimulator:
    """Replay hourly dataset rows as if they were incoming telemetry."""

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.lock = Lock()
        self.data = self._load_data()

        if len(self.data) < 169:
            raise ValueError(
                "Live simulator requires at least 169 hourly observations."
            )

        # Start with enough history for GreenMind's 168-hour feature window.
        self.index = 168
        self.running = True

    def _load_data(self):
        data = pd.read_csv(self.data_path)
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        data["total_energy"] = pd.to_numeric(
            data["total_energy"], errors="coerce"
        )

        return (
            data.dropna(subset=["timestamp", "total_energy"])
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

    def current(self):
        with self.lock:
            row = self.data.iloc[self.index]
            self._sync_backend_state()
            return self._serialize(row)

    def advance(self):
        with self.lock:
            if self.index >= len(self.data) - 1:
                # Loop back to the first position that has enough history.
                self.index = 168
            else:
                self.index += 1

            self._sync_backend_state()
            return self._serialize(self.data.iloc[self.index])

    def reset(self):
        with self.lock:
            self.index = 168
            self._sync_backend_state()
            return self._serialize(self.data.iloc[self.index])

    def active_history(self):
        """Return all observations available to the AI up to the live point."""
        with self.lock:
            return self.data.iloc[: self.index + 1].copy()

    def _sync_backend_state(self):
        """Make the existing backend AI use the current simulated stream point.

        The import is intentionally deferred until request time to avoid a
        circular import while FastAPI loads the live simulator router.
        """
        import sys

        backend_main = sys.modules.get("backend.main")
        if backend_main is not None:
            backend_main.energy_df = self.data.iloc[: self.index + 1].copy()

    def _serialize(self, row):
        return {
            "timestamp": str(row["timestamp"]),
            "energy": round(float(row["total_energy"]), 2),
            "unit": "kW",
            "source": "UCI dataset replay",
            "mode": "simulation",
            "stream_position": int(self.index),
            "stream_length": int(len(self.data)),
        }


simulator = EnergyStreamSimulator(DATA_PATH)


@router.get("/status")
def live_status():
    """Return the current simulated telemetry reading and sync the AI state."""
    reading = simulator.current()
    return {
        "status": "live_simulation",
        "streaming": simulator.running,
        "reading": reading,
    }


@router.post("/advance")
def advance_live_data():
    """Advance the simulated stream by exactly one hourly observation."""
    reading = simulator.advance()
    return {
        "status": "live_simulation",
        "streaming": simulator.running,
        "reading": reading,
    }


@router.post("/reset")
def reset_live_data():
    """Reset the simulated stream to its first valid feature position."""
    reading = simulator.reset()
    return {
        "status": "live_simulation",
        "streaming": simulator.running,
        "reading": reading,
    }
