# ============================================================
# GREENMIND AI
# LIVE DATA SIMULATOR
# ============================================================
# Replays the processed UCI electricity dataset as a streaming
# telemetry source for development and demonstration.
#
# The simulator publishes through the shared telemetry store.
# The UCI replay remains simulated data, not live sensor telemetry.
# ============================================================

from pathlib import Path
from threading import Lock

import pandas as pd
from fastapi import APIRouter

from backend.telemetry import telemetry_store


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "hourly_energy.csv"

router = APIRouter(prefix="/api/live", tags=["Live Telemetry"])


class EnergyStreamSimulator:
    """Replay hourly dataset rows through GreenMind's telemetry interface."""

    SOURCE = "UCI dataset replay"
    MODE = "simulation"

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
        self._publish_history()

    def _load_data(self):
        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Telemetry dataset not found: {self.data_path}. "
                "Run the data preparation pipeline first."
            )

        data = pd.read_csv(self.data_path)
        data["timestamp"] = pd.to_datetime(
            data["timestamp"], errors="coerce"
        )
        data["total_energy"] = pd.to_numeric(
            data["total_energy"], errors="coerce"
        )

        data = (
            data.dropna(subset=["timestamp", "total_energy"])
            .sort_values("timestamp")
            .drop_duplicates(subset=["timestamp"], keep="last")
            .reset_index(drop=True)
        )

        if (data["total_energy"] < 0).any():
            raise ValueError("Dataset contains negative energy readings.")

        return data

    def current(self):
        with self.lock:
            self._publish_history()
            return self._serialize(self.data.iloc[self.index])

    def advance(self):
        with self.lock:
            if self.index >= len(self.data) - 1:
                # Loop back to the first position that has enough history.
                self.index = 168
            else:
                self.index += 1

            self._publish_history()
            return self._serialize(self.data.iloc[self.index])

    def reset(self):
        with self.lock:
            self.index = 168
            self._publish_history()
            return self._serialize(self.data.iloc[self.index])

    def active_history(self):
        """Return all observations available to the AI up to the live point."""
        with self.lock:
            return self.data.iloc[: self.index + 1].copy()

    def _publish_history(self):
        """Publish source history to the shared telemetry store.

        The backend.main assignment is a temporary compatibility bridge for
        existing forecasting/dashboard functions. It will be removed when
        those functions consume the telemetry store directly.
        """
        history = self.data.iloc[: self.index + 1].copy()

        telemetry_store.replace_history(
            history,
            source=self.SOURCE,
            mode=self.MODE,
        )

        # Temporary compatibility bridge for the existing AI functions.
        import sys

        backend_main = sys.modules.get("backend.main")
        if backend_main is not None:
            backend_main.energy_df = history

    def _serialize(self, row):
        return {
            "timestamp": str(row["timestamp"]),
            "energy": round(float(row["total_energy"]), 2),
            "unit": "kW",
            "source": self.SOURCE,
            "mode": self.MODE,
            "stream_position": int(self.index),
            "stream_length": int(len(self.data)),
        }


simulator = EnergyStreamSimulator(DATA_PATH)


@router.get("/status")
def live_status():
    """Return the current simulated telemetry reading and source metadata."""
    reading = simulator.current()
    telemetry = telemetry_store.snapshot()
    return {
        "status": "live_simulation",
        "streaming": simulator.running,
        "reading": reading,
        "telemetry": telemetry,
    }


@router.post("/advance")
def advance_live_data():
    """Advance the simulated stream by exactly one hourly observation."""
    reading = simulator.advance()
    return {
        "status": "live_simulation",
        "streaming": simulator.running,
        "reading": reading,
        "telemetry": telemetry_store.snapshot(),
    }


@router.post("/reset")
def reset_live_data():
    """Reset the simulated stream to its first valid feature position."""
    reading = simulator.reset()
    return {
        "status": "live_simulation",
        "streaming": simulator.running,
        "reading": reading,
        "telemetry": telemetry_store.snapshot(),
    }
