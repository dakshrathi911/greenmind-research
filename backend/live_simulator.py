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

from io import StringIO
from pathlib import Path
from threading import Lock

import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import Response

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

    def quality_report(self):
        """Summarize timestamp continuity and coverage of the replay dataset."""
        timestamps = self.data["timestamp"]
        start = timestamps.iloc[0]
        end = timestamps.iloc[-1]
        expected_hours = int((end - start).total_seconds() // 3600) + 1
        intervals = timestamps.diff().dropna()
        irregular_intervals = int((intervals != pd.Timedelta(hours=1)).sum())

        return {
            "source": self.SOURCE,
            "mode": self.MODE,
            "total_observations": int(len(self.data)),
            "start_timestamp": start.isoformat(),
            "end_timestamp": end.isoformat(),
            "expected_hourly_observations": expected_hours,
            "missing_hour_slots": max(0, expected_hours - int(len(self.data))),
            "irregular_intervals": irregular_intervals,
            "is_hourly_contiguous": irregular_intervals == 0,
            "current_stream_position": int(self.index),
        }

    def active_history(self):
        """Return all observations available to the AI up to the live point."""
        with self.lock:
            return self.data.iloc[: self.index + 1].copy()

    def _publish_history(self):
        """Publish source history to the shared telemetry store.

        All forecasting and dashboard intelligence reads from this store.
        """
        history = self.data.iloc[: self.index + 1].copy()

        telemetry_store.replace_history(
            history,
            source=self.SOURCE,
            mode=self.MODE,
        )

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


@router.get("/history")
def live_history(limit: int = Query(default=168, ge=1, le=1000)):
    """Return recent telemetry observations with explicit source metadata."""
    history = telemetry_store.get_history().tail(limit)
    readings = [
        {
            "timestamp": row["timestamp"].isoformat(),
            "energy": round(float(row["total_energy"]), 2),
            "unit": "kW",
        }
        for _, row in history.iterrows()
    ]
    return {
        "telemetry": telemetry_store.snapshot(),
        "count": len(readings),
        "readings": readings,
    }


@router.get("/quality")
def live_data_quality():
    """Report hourly continuity and coverage for the replay dataset."""
    return simulator.quality_report()


@router.get("/export")
def export_live_history(limit: int = Query(default=1000, ge=1, le=1000)):
    """Download recent telemetry as a CSV with source metadata."""
    history = telemetry_store.get_history().tail(limit).copy()
    history["source"] = telemetry_store.snapshot()["source"]
    history["mode"] = telemetry_store.snapshot()["mode"]
    history = history.rename(columns={"total_energy": "energy_kw"})

    output = StringIO()
    history.to_csv(output, index=False)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="greenmind_telemetry.csv"'
        },
    )


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
