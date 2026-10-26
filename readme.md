# GreenMind AI

GreenMind AI is a research prototype for historical electricity-demand forecasting and simulated carbon-aware workload scheduling. It combines a FastAPI backend, a React/Vite dashboard, an hourly electricity-demand forecasting pipeline, and reproducible synthetic scheduling experiments.

> **Research integrity:** The UCI electricity dataset is historical electricity-load data, not live data-center telemetry. The scheduling experiments use synthetic workloads, carbon-intensity profiles, and PUE profiles. Their emissions reductions are illustrative simulation results, not measured real-world savings.

## Components

- **Forecasting:** Random Forest model trained to predict the next hourly observation from historical demand and calendar features.
- **Energy dashboard:** Displays historical demand, forecasts, anomaly heuristics, and recommendations.
- **Live telemetry demonstration:** Replays rows from the historical dataset. The API labels this as a simulation; it is not a live sensor feed.
- **Scheduling research:** Compares baseline, carbon-aware, and deadline-aware carbon heuristics under synthetic assumptions.
- **Research dashboard:** A static dashboard in `dashboard/` that visualizes the committed matched-service scenario results.

## Requirements

- Python and pip compatible with the pinned dependencies in `requirements.txt`
- Node.js and npm for the React/Vite frontend
- Internet access for the first download of the UCI dataset

## First-time setup (Windows PowerShell)

Run commands from the repository root.

### 1. Create the Python environment and install dependencies

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks environment activation, use the appropriate execution-policy setting for your machine or run the environment's Python executable directly.

### 2. Download and prepare the historical dataset

The raw dataset is large and is intentionally not committed to Git. Download it, aggregate it to hourly demand, and build next-hour forecasting features:

```powershell
python .\data\download_dataset.py
python .\data\preprocess_dataset.py
python .\data\create_features.py
python .\models\train_model.py
```

These steps generate ignored files under `data/raw/`, `data/processed/`, and the trained model artifact `models/energy_forecaster.joblib`. They must be generated on a new clone before starting the API.

### 3. Start the backend

From the repository root, with the virtual environment activated:

```powershell
python -m uvicorn backend.main:app --reload
```

- API root: http://127.0.0.1:8000/
- Interactive API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

Keep this terminal open while using the application.

### 4. Start the React frontend

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite. The React application currently targets the local backend at `http://127.0.0.1:8000`; it is configured for local development and needs an environment-based API URL plus a hosted backend before deployment to a public domain.

## Run tests

From the repository root:

```powershell
python -m unittest discover -s research/tests -v
```

The tests cover scheduling constraints, emissions accounting, matched-service analysis, and regression checks for next-hour feature alignment.

## Run synthetic scheduling experiments

From the repository root:

```powershell
python .\research\carbon_experiment.py
python .\research\multi_seed_experiment.py
python .\research\sensitivity_analysis.py
python .\research\matched_service_analysis.py
```

The scripts write their generated CSVs and reports to `research/results/`. The sensitivity and matched-service sweeps each evaluate 81 combinations of PUE range, carbon variability, workload size, and hourly capacity across 10 seeds. These can take longer than the unit tests. Run them when experiment code or assumptions change, not merely when the separate forecasting model is retrained.

## Research assumptions and limitations

- The forecasting model predicts historical electricity demand; it does not forecast grid carbon intensity.
- The current dataset is historical and its replay is simulated telemetry.
- The carbon-aware scheduler uses heuristic policies, not reinforcement learning.
- Workloads, carbon intensity, and PUE are synthetic. IT energy per work unit is an illustrative constant.
- Matched-service comparisons report emissions for jobs completed by all compared policies; report common-job/work coverage alongside reductions because this comparison can represent only a subset of the workload.
- A heuristic confidence score is not automatically a calibrated prediction interval or probability of correctness.
- Forecasting metrics and scheduling emissions metrics evaluate different components and must be reported separately.

## Repository map

```text
backend/              FastAPI API and historical-data replay simulator
data/                 Dataset download, preprocessing, and feature engineering
models/               Forecasting training, anomaly logic, and optimization
frontend/             React/Vite energy dashboard
research/             Synthetic scheduling experiments, tests, and outputs
dashboard/             Static matched-service research dashboard
.github/workflows/     GitHub Pages deployment workflow
```

For experiment-specific policy definitions, output descriptions, and assumptions, see [research/README.md](research/README.md). For the static research dashboard deployment steps, see [dashboard/README.md](dashboard/README.md).
