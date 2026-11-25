# Telemetry API

GreenMind AI exposes the simulator's active telemetry through the FastAPI
backend. The current source is a replay of the processed UCI electricity
dataset; it is simulated historical data, not a live facility meter feed.

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/live/status` | Current reading, stream status, and telemetry metadata |
| GET | `/api/live/history?limit=168` | Most recent readings as JSON |
| GET | `/api/live/quality` | Dataset coverage and hourly continuity diagnostics |
| GET | `/api/live/export?limit=1000` | Download recent readings as CSV |
| POST | `/api/live/advance` | Advance the replay by one hourly observation |
| POST | `/api/live/reset` | Return the replay to its first valid feature position |

## History response

The history endpoint returns a `telemetry` snapshot, a `count`, and a
`readings` array. Each reading contains an ISO-formatted timestamp, energy
value, and unit. The `limit` query parameter accepts values from 1 to 1,000
and defaults to 168.

Example:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/live/history?limit=24"
```

## Data-quality diagnostics

The quality endpoint reports the observation count, time range, expected
hourly observation count, missing hour slots, irregular intervals, and
whether the dataset is continuous at an hourly frequency.

Example:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/live/quality"
```

A dataset can be loaded while still containing time gaps. Check
`is_hourly_contiguous` and `missing_hour_slots` before interpreting a
historical analysis as a complete hourly series.

## CSV export

The export endpoint returns a downloadable CSV containing timestamp,
`energy_kw`, source, and mode columns. The limit accepts values from 1 to
1,000 and defaults to 1,000.

Example:

```powershell
Invoke-WebRequest "http://127.0.0.1:8000/api/live/export?limit=1000" -OutFile greenmind_telemetry.csv
```

The dashboard also provides an **Export CSV** control beside the simulator
controls. Exporting does not advance or otherwise modify the simulation.
