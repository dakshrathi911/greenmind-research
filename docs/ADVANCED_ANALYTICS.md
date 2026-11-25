# Advanced Analytics API

These endpoints use the active telemetry store and work without external API credentials.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/analytics/overview?days=7` | Period energy totals, averages, peaks, daily summaries and hourly profile |
| GET | `/api/analytics/load-shift?shift_fraction=0.10` | Illustrative demand-shifting scenario with energy-conservation check |
| GET | `/api/analytics/model` | Random Forest feature importance and retrospective one-step error metrics |

The overview supports 7, 30, or 90 days. Energy totals treat each hourly kW reading as one hour of consumption (kWh).

The load-shift scenario moves a configurable share of demand from the highest-demand 20% of observed hours to the lowest-demand 20%. It conserves total energy and is a what-if analysis only; it does not account for service-level constraints, workload deadlines, or facility capacity.

Model diagnostics evaluate predictions retrospectively on the available telemetry. This is not a held-out test set and should not be presented as independent generalization performance. Feature importance describes model reliance, not causality.
