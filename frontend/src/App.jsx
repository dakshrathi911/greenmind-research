import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000/api/dashboard";
const OPTIMIZATION_API_URL = "http://127.0.0.1:8000/api/optimization";

function formatNumber(value, decimals = 0) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function parseCsvText(text) {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",");
  return lines.slice(1).filter(Boolean).map((line) => {
    const values = line.split(",");
    return Object.fromEntries(headers.map((header, index) => [
      header,
      values[index] ?? "",
    ]));
  });
}

function getAnomalyType(anomaly) {
  if (!anomaly) return "normal";
  if (!anomaly.detected && anomaly.is_peak) return "peak";
  if (!anomaly.detected) return "normal";
  if (Number(anomaly.deviation) < 0) return "low";
  return "high";
}

function getAnomalyTitle(anomaly) {
  const type = getAnomalyType(anomaly);

  if (type === "low") return "Unusually Low Energy Demand";
  if (type === "high") return "Unusually High Energy Demand";
  if (type === "peak") return "High-Demand Peak Detected";

  return "Energy Demand Within Expected Range";
}

function getAnomalyBadge(anomaly) {
  const type = getAnomalyType(anomaly);

  if (type === "low") return "LOW-DEMAND ANOMALY";
  if (type === "high") return "HIGH-DEMAND ANOMALY";
  if (type === "peak") return "PEAK PERIOD";

  return "NORMAL";
}

function getAnomalyIcon(anomaly) {
  const type = getAnomalyType(anomaly);

  if (type === "low") return "↓";
  if (type === "high") return "↑";
  if (type === "peak") return "⚡";

  return "✓";
}

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [optimization, setOptimization] = useState(null);
  const [optimizationLoading, setOptimizationLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeInsight, setActiveInsight] = useState("overview");
  const [researchSummary, setResearchSummary] = useState([]);
  const [matchedSummary, setMatchedSummary] = useState([]);
  const [researchExperiment, setResearchExperiment] = useState([]);
  const [researchLoading, setResearchLoading] = useState(true);
  const [researchError, setResearchError] = useState("");
  const [researchFilters, setResearchFilters] = useState({
    pue: "all", variability: "all", jobs: "all", capacity: "all", view: "matched",
  });

  async function loadDashboard() {
    try {
      const response = await fetch(API_URL);

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const data = await response.json();

      setDashboard(data);
      setError("");
    } catch (err) {
      console.error("Dashboard error:", err);
      setError("Unable to connect to the GreenMind AI backend.");
    } finally {
      setLoading(false);
    }
  }

  async function loadOptimization() {
    try {
      setOptimizationLoading(true);

      const response = await fetch(OPTIMIZATION_API_URL);

      if (!response.ok) {
        throw new Error(
          `Optimization backend returned ${response.status}`
        );
      }

      const data = await response.json();

      setOptimization(data.optimization || data);
    } catch (err) {
      console.error("Optimization error:", err);
    } finally {
      setOptimizationLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
    loadOptimization();

    const interval = setInterval(() => {
      loadDashboard();
      loadOptimization();
    }, 30000);

    return () => clearInterval(interval);
  }, []);
  
  useEffect(() => {
    async function loadResearchData() {
      try {
        const [sensitivityResponse, matchedResponse, experimentResponse] = await Promise.all([
          fetch("/data/sensitivity_summary.csv"),
          fetch("/data/matched_service_scenario_summary.csv"),
          fetch("/data/experiment_summary.csv"),
        ]);
        if (![sensitivityResponse, matchedResponse, experimentResponse].every((response) => response.ok)) {
          throw new Error("Research CSV files could not be loaded.");
        }
        const [sensitivityCsv, matchedCsv, experimentCsv] = await Promise.all([
          sensitivityResponse.text(), matchedResponse.text(), experimentResponse.text(),
        ]);
        setResearchSummary(parseCsvText(sensitivityCsv));
        setMatchedSummary(parseCsvText(matchedCsv));
        setResearchExperiment(parseCsvText(experimentCsv));
      } catch (researchLoadError) {
        console.error("Research data error:", researchLoadError);
        setResearchError("Research results could not be loaded. Pull the latest repository changes and restart the frontend.");
      } finally {
        setResearchLoading(false);
      }
    }
    loadResearchData();
  }, []);

  const chartData = useMemo(
    () => dashboard?.energy_history || [],
    [dashboard]
  );

  const maxEnergy = useMemo(() => {
    if (!chartData.length) return 1;

    return Math.max(
      ...chartData.map((item) => Number(item.energy) || 0)
    );
  }, [chartData]);

  const anomaly = dashboard?.anomaly;
  const anomalyType = getAnomalyType(anomaly);

  const prediction = dashboard?.prediction;

  const predictionChange = Number(
    prediction?.change ?? 0
  );

  const predictionTrend =
    predictionChange < 0
      ? "trend-down"
      : predictionChange > 0
      ? "trend-up"
      : "trend-neutral";

  const decision = dashboard?.decision;
  const historical = dashboard?.historical_intelligence;
  const activeResearchRows = researchFilters.view === "matched" ? matchedSummary : researchSummary;
  const filteredResearchRows = activeResearchRows.filter((row) =>
    (researchFilters.pue === "all" || row.pue_scenario === researchFilters.pue) &&
    (researchFilters.variability === "all" || row.carbon_variability === researchFilters.variability) &&
    (researchFilters.jobs === "all" || String(row.job_count) === researchFilters.jobs) &&
    (researchFilters.capacity === "all" || String(row.hourly_capacity) === researchFilters.capacity)
  );
  const averageOf = (rows, key) => rows.length
    ? rows.reduce((total, row) => total + (Number(row[key]) || 0), 0) / rows.length
    : 0;
  const researchMeanReduction = averageOf(matchedSummary, "mean_carbon_aware_matched_reduction_pct");
  const researchCoverage = averageOf(matchedSummary, "mean_common_work_coverage_pct");
  const significantScenarios = matchedSummary.filter((row) => String(row.significant_fdr_0_05).toLowerCase() === "true").length;


  if (loading && !dashboard) {
    return (
      <div className="app">
        <header className="topbar">
          <div className="brand">
            <div className="brand-logo">🌱</div>

            <div>
              <h1>GreenMind AI</h1>
              <span>Energy Intelligence Platform</span>
            </div>
          </div>
        </header>

        <main className="dashboard">
          <div className="loading-screen">
            <div className="loading-spinner">🌱</div>
            <p>Initializing GreenMind AI...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error && !dashboard) {
    return (
      <div className="app">
        <header className="topbar">
          <div className="brand">
            <div className="brand-logo">🌱</div>

            <div>
              <h1>GreenMind AI</h1>
              <span>Energy Intelligence Platform</span>
            </div>
          </div>

          <div className="system-status">
            <span className="status-dot error-dot" />
            BACKEND OFFLINE
          </div>
        </header>

        <main className="dashboard">
          <div className="error-panel">
            <h2>GreenMind AI is unable to connect</h2>

            <p>
              Start the FastAPI backend and refresh the page.
            </p>

            <button
              className="retry-button"
              onClick={loadDashboard}
            >
              Retry connection
            </button>
          </div>
        </main>
      </div>
    );
  }

  const currentEnergy =
    dashboard?.energy_usage?.value ?? 0;

  const carbon =
    dashboard?.carbon_footprint?.value ?? 0;

  const efficiency =
    dashboard?.efficiency_score?.value ?? 0;

  const confidence =
    prediction?.confidence ?? 0;

  return (
    <div className="app">

      {/* HEADER */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-logo">🌱</div>

          <div>
            <h1>GreenMind AI</h1>
            <span>Energy Intelligence Platform</span>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          AI SYSTEM ONLINE
        </div>
      </header>


      <main className="dashboard">

        {/* METRICS */}
        <section className="metrics-grid">

          <div className="metric-card">
            <div className="metric-header">
              <span>ENERGY USAGE ⚡</span>
              <div className="metric-icon">⚡</div>
            </div>

            <div className="metric-value">
              {formatNumber(currentEnergy, 0)}
              <small> kW</small>
            </div>

            <div className="metric-description">
              Current aggregate demand
            </div>
          </div>


          <div className="metric-card">
            <div className="metric-header">
              <span>CARBON FOOTPRINT ◉</span>
              <div className="metric-icon">◉</div>
            </div>

            <div className="metric-value">
              {formatNumber(carbon, 0)}
              <small> kg CO₂e</small>
            </div>

            <div className="metric-description">
              Estimated emissions for one hour at current demand
            </div>
          </div>


          <div className="metric-card">
            <div className="metric-header">
              <span>ENERGY PERFORMANCE ✦</span>
              <div className="metric-icon">✦</div>
            </div>

            <div className="metric-value">
              {formatNumber(efficiency, 1)}
              <small> %</small>
            </div>

            <div className="metric-description">
              Performance vs recent energy baseline
            </div>

            <div className="efficiency-bar">
              <div
                className="efficiency-fill"
                style={{
                  width: `${Math.max(
                    0,
                    Math.min(100, efficiency)
                  )}%`,
                }}
              />
            </div>
          </div>

        </section>


        {/* MAIN CHART + FORECAST */}
        <section className="main-grid">

          <div className="panel">

            <div className="panel-header">

              <div>
                <h2>Energy Demand</h2>
                <p>Last 24 hours</p>
              </div>

              <div className="live-label">
                ● LIVE DATA
              </div>

            </div>


            <div className="chart-container">

              {chartData.map((item, index) => {

                const energy =
                  Number(item.energy) || 0;

                const height =
                  Math.max(
                    2,
                    (energy / maxEnergy) * 100
                  );

                return (
                  <div
                    className="chart-column"
                    key={`${item.time}-${index}`}
                  >

                    <div
                      className="chart-bar"
                      style={{
                        height: `${height}%`,
                      }}
                      title={`${item.time} — ${formatNumber(
                        energy,
                        2
                      )} kW`}
                    />

                    <span>{item.time}</span>

                  </div>
                );
              })}

            </div>
          </div>


          <div className="panel prediction-panel">

            <div className="panel-header">

              <div>
                <h2>AI Forecast</h2>
                <p>Next hour</p>
              </div>

              <div className="ai-badge">
                AI
              </div>

            </div>


            <div className="prediction-value">
              {formatNumber(prediction?.value, 0)}
              <span>kW</span>
            </div>


            <div
              className={`prediction-change ${predictionTrend}`}
            >
              {predictionChange < 0
                ? "↓"
                : predictionChange > 0
                ? "↑"
                : "→"}

              {" "}
              {Math.abs(predictionChange).toFixed(2)}%

              <span>predicted change</span>
            </div>


            <div className="confidence-section">

              <div className="confidence-header">
                <span>Model confidence</span>

                <strong>
                  {formatNumber(confidence, 1)}%
                </strong>
              </div>


              <div className="confidence-bar">
                <div
                  className="confidence-fill"
                  style={{
                    width: `${Math.max(
                      0,
                      Math.min(100, confidence)
                    )}%`,
                  }}
                />
              </div>


              <p>
                Based on Random Forest prediction
                consistency
              </p>

            </div>


            <div className="prediction-source">
              Based on historical data through{" "}
              <strong>
                {prediction?.based_on ||
                  "available historical data"}
              </strong>
            </div>

          </div>

        </section>


        {/* AI INSIGHTS NAVIGATION */}
        <section className="insights-navigation">

          <div className="insights-nav-header">

            <div>
              <div className="insights-nav-label">
                GREENMIND AI
              </div>

              <h2>AI Insights</h2>
            </div>

            <span className="insights-nav-description">
              Intelligence layers generated from live
              energy patterns
            </span>

          </div>


          <div className="insights-tabs">

            <button
              className={
                activeInsight === "overview"
                  ? "insight-tab active"
                  : "insight-tab"
              }
              onClick={() =>
                setActiveInsight("overview")
              }
            >
              <span className="tab-icon">◉</span>
              Overview
            </button>


            <button
              className={
                activeInsight === "alerts"
                  ? "insight-tab active"
                  : "insight-tab"
              }
              onClick={() =>
                setActiveInsight("alerts")
              }
            >
              <span className="tab-icon">⚠</span>
              Alerts

              {anomaly?.detected && (
                <span className="tab-count alert-count">
                  1
                </span>
              )}
            </button>


            <button
              className={
                activeInsight === "recommendations"
                  ? "insight-tab active"
                  : "insight-tab"
              }
              onClick={() =>
                setActiveInsight("recommendations")
              }
            >
              <span className="tab-icon">✦</span>
              Recommendations

              {dashboard?.recommendations?.length >
                0 && (
                <span className="tab-count">
                  {dashboard.recommendations.length}
                </span>
              )}
            </button>


            <button
              className={
                activeInsight === "decision"
                  ? "insight-tab active"
                  : "insight-tab"
              }
              onClick={() =>
                setActiveInsight("decision")
              }
            >
              <span className="tab-icon">◈</span>
              Decision
            </button>


            <button
              className={
                activeInsight === "historical"
                  ? "insight-tab active"
                  : "insight-tab"
              }
              onClick={() =>
                setActiveInsight("historical")
              }
            >
              <span className="tab-icon">◌</span>
              Historical
            </button>


            <button
              className={
                activeInsight === "optimization"
                  ? "insight-tab active optimization-tab"
                  : "insight-tab optimization-tab"
              }
              onClick={() =>
                setActiveInsight("optimization")
              }
            >
              <span className="tab-icon">⚡</span>
              Optimization
            </button>

          </div>
        </section>


        {/* OVERVIEW */}
        {activeInsight === "overview" && (
          <section className="panel insights-overview-panel">

            <div className="panel-header">

              <div>
                <div className="decision-label">
                  GREENMIND AI
                </div>

                <h2>Intelligence Overview</h2>

                <p>
                  Current AI interpretation of energy
                  conditions
                </p>
              </div>

              <div className="recommendation-icon">
                ✦
              </div>

            </div>


            <div className="overview-grid">

              <div className="overview-card">

                <span>CURRENT CONDITION</span>

                <strong>
                  {historical?.status === "low"
                    ? "LOW DEMAND"
                    : historical?.status === "high"
                    ? "HIGH DEMAND"
                    : "NORMAL"}
                </strong>

                <p>
                  {historical?.insight ||
                    "Energy demand is currently being evaluated."}
                </p>

              </div>


              <div className="overview-card">

                <span>AI DECISION</span>

                <strong>
                  {decision?.decision ||
                    "MAINTAIN CURRENT OPERATION"}
                </strong>

                <p>
                  {decision?.summary ||
                    "No significant intervention is currently required."}
                </p>

              </div>


              <div className="overview-card">

                <span>NEXT HOUR</span>

                <strong>
                  {formatNumber(
                    prediction?.value,
                    0
                  )}{" "}
                  kW
                </strong>

                <p>
                  {predictionChange < 0
                    ? "Demand is expected to decrease."
                    : predictionChange > 0
                    ? "Demand is expected to increase."
                    : "Demand is expected to remain stable."}
                </p>

              </div>

            </div>

          </section>
        )}


        {/* ALERTS */}
        {activeInsight === "alerts" && (
          <section
            className={`panel anomaly-panel anomaly-${anomalyType}`}
          >

            <div className="anomaly-content">

              <div className="anomaly-icon">
                {getAnomalyIcon(anomaly)}
              </div>


              <div className="anomaly-main">

                <div className="anomaly-heading">

                  <div>

                    <div className="anomaly-label">
                      AI ENERGY ALERT
                    </div>

                    <h2>
                      {getAnomalyTitle(anomaly)}
                    </h2>

                  </div>


                  <span className="anomaly-badge">
                    {getAnomalyBadge(anomaly)}
                  </span>

                </div>


                <p className="anomaly-message">
                  {anomaly?.message ||
                    "Energy demand is within the expected historical range."}
                </p>


                <div className="anomaly-stats">

                  <div className="anomaly-stat">
                    <span>Current</span>

                    <strong>
                      {formatNumber(
                        anomaly?.current_energy,
                        0
                      )}{" "}
                      kW
                    </strong>
                  </div>


                  <div className="anomaly-stat">
                    <span>Expected</span>

                    <strong>
                      {formatNumber(
                        anomaly?.expected_energy,
                        0
                      )}{" "}
                      kW
                    </strong>
                  </div>


                  <div className="anomaly-stat">

                    <span>Deviation</span>

                    <strong
                      className={
                        Number(anomaly?.deviation) <
                        0
                          ? "anomaly-negative"
                          : "anomaly-positive"
                      }
                    >
                      {Number(
                        anomaly?.deviation ?? 0
                      ) > 0
                        ? "+"
                        : ""}

                      {Number(
                        anomaly?.deviation ?? 0
                      ).toFixed(2)}
                      %
                    </strong>

                  </div>


                  <div className="anomaly-stat">

                    <span>Z-score</span>

                    <strong>
                      {Number(
                        anomaly?.z_score ?? 0
                      ).toFixed(2)}
                    </strong>

                  </div>

                </div>


                <div className="anomaly-recommendation">

                  <span>
                    💡 AI recommendation
                  </span>

                  <strong>
                    {anomaly?.recommendation ||
                      "No immediate action is required."}
                  </strong>

                </div>

              </div>

            </div>

          </section>
        )}


        {/* RECOMMENDATIONS */}
        {activeInsight === "recommendations" && (
          <section className="panel recommendations-panel">

            <div className="panel-header">

              <div>

                <h2>AI Recommendations</h2>

                <p>
                  Actions generated from current
                  energy patterns
                </p>

              </div>

              <div className="recommendation-icon">
                ✦
              </div>

            </div>


            <div className="recommendations-list">

              {(dashboard?.recommendations ||
                []).map(
                (recommendation, index) => {

                  const priority = (
                    recommendation.priority ||
                    "low"
                  ).toLowerCase();

                  return (
                    <div
                      className={`recommendation-card priority-${priority}`}
                      key={`${recommendation.title}-${index}`}
                    >

                      <div className="recommendation-top">

                        <span
                          className={`priority-badge priority-${priority}`}
                        >
                          {priority.toUpperCase()}{" "}
                          PRIORITY
                        </span>

                      </div>


                      <h3>
                        {recommendation.title}
                      </h3>


                      <p>
                        {recommendation.description}
                      </p>


                      <div className="recommendation-saving">

                        <span>
                          Potential impact
                        </span>

                        <strong>
                          {recommendation.saving}
                        </strong>

                      </div>

                    </div>
                  );
                }
              )}

            </div>

          </section>
        )}


        {/* DECISION */}
        {activeInsight === "decision" && (
          <section
            className={`panel decision-panel decision-${
              decision?.status || "stable"
            }`}
          >

            <div className="decision-header">

              <div>

                <div className="decision-label">
                  GREENMIND AI
                </div>

                <h2>Decision Center</h2>

                <p>
                  Recommended action based on
                  current energy conditions
                </p>

              </div>

              <div className="decision-ai-badge">
                AI
              </div>

            </div>


            <div className="decision-body">

              <div className="decision-main">

                <span className="decision-status">
                  {decision?.status ===
                  "opportunity"
                    ? "OPPORTUNITY"
                    : decision?.status ===
                      "warning"
                    ? "ATTENTION"
                    : "STABLE"}
                </span>

                <h3>
                  {decision?.decision ||
                    "Maintain current operation"}
                </h3>

                <p>
                  {decision?.summary ||
                    "Energy demand is currently within the expected range."}
                </p>

              </div>


              <div className="decision-metrics">

                <div className="decision-metric">
                  <span>CURRENT</span>

                  <strong>
                    {formatNumber(
                      decision?.current_energy,
                      0
                    )}{" "}
                    kW
                  </strong>
                </div>


                <div className="decision-metric">
                  <span>NEXT HOUR</span>

                  <strong>
                    {formatNumber(
                      decision?.predicted_energy,
                      0
                    )}{" "}
                    kW
                  </strong>
                </div>


                <div className="decision-metric">

                  <span>CHANGE</span>

                  <strong
                    className={
                      Number(
                        decision?.predicted_change ||
                          0
                      ) < 0
                        ? "decision-down"
                        : Number(
                            decision?.predicted_change ||
                              0
                          ) > 0
                        ? "decision-up"
                        : ""
                    }
                  >
                    {Number(
                      decision?.predicted_change ||
                        0
                    ) > 0
                      ? "+"
                      : ""}

                    {Number(
                      decision?.predicted_change ||
                        0
                    ).toFixed(2)}
                    %
                  </strong>

                </div>


                <div className="decision-metric">

                  <span>CONFIDENCE</span>

                  <strong>
                    {formatNumber(
                      decision?.confidence,
                      1
                    )}%
                  </strong>

                </div>

              </div>

            </div>


            <div className="decision-action">

              <div className="decision-action-icon">
                💡
              </div>

              <div>

                <span>
                  RECOMMENDED ACTION
                </span>

                <strong>
                  {decision?.action ||
                    "Continue normal operations."}
                </strong>

              </div>

            </div>


            <div className="decision-reason">

              <span>
                Why GreenMind recommends this
              </span>

              <strong>
                {decision?.reason ||
                  "No significant demand deviation requires immediate intervention."}
              </strong>

            </div>

          </section>
        )}


        {/* HISTORICAL */}
        {activeInsight === "historical" && (
          <section className="panel historical-panel">

            <div className="panel-header">

              <div>

                <div className="decision-label">
                  GREENMIND AI
                </div>

                <h2>
                  Historical Intelligence
                </h2>

                <p>
                  Current demand compared with
                  historical operating patterns
                </p>

              </div>

              <div className="recommendation-icon">
                ◌
              </div>

            </div>


            <div className="historical-status">

              <div className="historical-status-icon">

                {historical?.status === "low"
                  ? "↓"
                  : historical?.status === "high"
                  ? "↑"
                  : "✓"}

              </div>

              <div>

                <span>
                  CURRENT HISTORICAL STATE
                </span>

                <strong>
                  {historical?.status === "low"
                    ? "LOW DEMAND"
                    : historical?.status ===
                      "high"
                    ? "HIGH DEMAND"
                    : "NORMAL"}
                </strong>

              </div>

            </div>


            <div className="historical-grid">

              <div className="historical-card">
                <span>CURRENT DEMAND</span>

                <strong>
                  {formatNumber(
                    historical?.current_energy,
                    0
                  )}{" "}
                  kW
                </strong>
              </div>


              <div className="historical-card">
                <span>SAME-HOUR AVERAGE</span>

                <strong>
                  {formatNumber(
                    historical?.same_hour_average,
                    0
                  )}{" "}
                  kW
                </strong>
              </div>


              <div className="historical-card">

                <span>
                  SAME WEEKDAY / HOUR
                </span>

                <strong>
                  {formatNumber(
                    historical?.same_weekday_hour_average,
                    0
                  )}{" "}
                  kW
                </strong>

              </div>


              <div className="historical-card">

                <span>7-DAY AVERAGE</span>

                <strong>
                  {formatNumber(
                    historical?.weekly_average,
                    0
                  )}{" "}
                  kW
                </strong>

              </div>

            </div>


            <div className="historical-comparison">

              <div className="historical-comparison-item">

                <span>VS SAME HOUR</span>

                <strong
                  className={
                    Number(
                      historical?.current_vs_same_hour
                    ) < 0
                      ? "decision-down"
                      : "decision-up"
                  }
                >
                  {Number(
                    historical?.current_vs_same_hour ??
                      0
                  ) > 0
                    ? "+"
                    : ""}

                  {Number(
                    historical?.current_vs_same_hour ??
                      0
                  ).toFixed(2)}
                  %
                </strong>

              </div>


              <div className="historical-comparison-item">

                <span>
                  VS WEEKDAY / HOUR
                </span>

                <strong
                  className={
                    Number(
                      historical?.current_vs_weekday_hour
                    ) < 0
                      ? "decision-down"
                      : "decision-up"
                  }
                >
                  {Number(
                    historical?.current_vs_weekday_hour ??
                      0
                  ) > 0
                    ? "+"
                    : ""}

                  {Number(
                    historical?.current_vs_weekday_hour ??
                      0
                  ).toFixed(2)}
                  %
                </strong>

              </div>


              <div className="historical-comparison-item">

                <span>
                  VS RECENT WEEK
                </span>

                <strong
                  className={
                    Number(
                      historical?.current_vs_week ?? 0
                    ) < 0
                      ? "decision-down"
                      : "decision-up"
                  }
                >
                  {Number(
                    historical?.current_vs_week ?? 0
                  ) > 0
                    ? "+"
                    : ""}

                  {Number(
                    historical?.current_vs_week ?? 0
                  ).toFixed(2)}
                  %
                </strong>

              </div>

            </div>


            <div className="historical-insight">

              <span>
                ✦ AI HISTORICAL INSIGHT
              </span>

              <strong>
                {historical?.insight ||
                  "Historical intelligence is currently unavailable."}
              </strong>

            </div>

          </section>
        )}


        {/* OPTIMIZATION */}
        {activeInsight === "optimization" && (
          <section className="panel optimization-panel">

            <div className="panel-header">

              <div>

                <div className="decision-label">
                  GREENMIND AI
                </div>

                <h2>
                  Energy Optimization
                </h2>

                <p>
                  AI-powered workload scheduling
                  for the next 24 hours
                </p>

              </div>

              <div className="recommendation-icon">
                ⚡
              </div>

            </div>


            {optimizationLoading &&
            !optimization ? (

              <div className="optimization-loading">

                <div className="loading-spinner">
                  ⚡
                </div>

                <p>
                  Analysing upcoming energy
                  demand...
                </p>

              </div>

            ) : optimization?.best_window ? (

              <>

                <div className="optimization-hero">

                  <div className="optimization-hero-main">

                    <span className="optimization-eyebrow">
                      RECOMMENDED WINDOW
                    </span>

                    <h3>
                      {optimization.best_window.start}
                      {" – "}
                      {optimization.best_window.end}
                    </h3>

                    <p>
                      Schedule flexible or
                      energy-intensive workloads
                      during this forecasted
                      low-demand period.
                    </p>

                  </div>


                  <div className="optimization-rating">

                    <span>
                      AI RATING
                    </span>

                    <strong>
                      {String(
                        optimization.best_window
                          .rating ||
                          "excellent"
                      ).toUpperCase()}
                    </strong>

                    <small>
                      {formatNumber(
                        optimization.best_window
                          .confidence,
                        1
                      )}
                      % confidence
                    </small>

                  </div>

                </div>


                <div className="optimization-stats">

                  <div className="optimization-stat">

                    <span>AI FORECAST</span>

                    <strong>
                      {formatNumber(
                        optimization.best_window
                          .average_predicted_demand,
                        0
                      )}

                      <small> kW</small>
                    </strong>

                  </div>


                  <div className="optimization-stat">

                    <span>
                      HISTORICAL EXPECTED
                    </span>

                    <strong>
                      {formatNumber(
                        optimization.best_window
                          .average_historical_demand,
                        0
                      )}

                      <small> kW</small>
                    </strong>

                  </div>


                  <div className="optimization-stat">

                    <span>
                      BELOW HISTORICAL BASELINE
                    </span>

                    <strong className="decision-down">
                      {Math.abs(
                        Number(
                          optimization.best_window
                            .saving_vs_historical_baseline ||
                            0
                        )
                      ).toFixed(2)}
                      %
                    </strong>

                  </div>


                  <div className="optimization-stat">

                    <span>
                      LOWER THAN CURRENT
                    </span>

                    <strong className="decision-down">
                      {Math.abs(
                        Number(
                          optimization.best_window
                            .change_vs_current ||
                            0
                        )
                      ).toFixed(2)}
                      %
                    </strong>

                  </div>

                </div>


                <div className="optimization-chart-section">

                  <div className="optimization-chart-header">

                    <div>

                      <h3>
                        24-Hour AI Forecast
                      </h3>

                      <p>
                        Forecasted demand compared
                        with historical expectations
                      </p>

                    </div>

                    <span>
                      NEXT 24 HOURS
                    </span>

                  </div>


                  <div className="optimization-chart">

                    {(optimization.hourly_forecast ||
                      []).map((item, index) => {

                        const predicted =
                          Number(
                            item.predicted_energy
                          ) || 0;

                        const allValues =
                          (
                            optimization.hourly_forecast ||
                            []
                          ).flatMap((x) => [
                            Number(
                              x.predicted_energy
                            ) || 0,
                            Number(
                              x.historical_baseline
                            ) || 0,
                          ]);

                        const maxValue =
                          Math.max(
                            ...allValues,
                            1
                          );

                        const height =
                          Math.max(
                            4,
                            (predicted /
                              maxValue) *
                              100
                          );

                        // Backend is the single source
                        // of truth for optimization decisions.
                        const isRecommended =
                          Boolean(
                            item.optimization_opportunity
                          );

                        return (
                          <div
                            className={
                              isRecommended
                                ? "optimization-column recommended"
                                : "optimization-column"
                            }
                            key={`${item.timestamp}-${index}`}
                            title={`${item.time} — Forecast ${formatNumber(
                              predicted,
                              0
                            )} kW`}
                          >

                            <div
                              className="optimization-bar"
                              style={{
                                height: `${height}%`,
                              }}
                            />

                            <span>
                              {item.time}
                            </span>

                          </div>
                        );
                      })}

                  </div>


                  <div className="optimization-legend">

                    <span>
                      <i className="legend-dot forecast-dot" />
                      AI forecast
                    </span>

                    <span>
                      <i className="legend-dot opportunity-dot" />
                      Optimization opportunity
                    </span>

                  </div>

                </div>


                <div className="optimization-recommendation">

                  <div className="optimization-recommendation-icon">
                    ✦
                  </div>

                  <div>

                    <span>
                      AI RECOMMENDATION
                    </span>

                    <strong>
                      {optimization.recommendation}
                    </strong>

                  </div>

                </div>

              </>

            ) : (

              <div className="optimization-empty">

                <div className="optimization-empty-icon">
                  ✓
                </div>

                <div>

                  <span>
                    NO SIGNIFICANT OPTIMIZATION
                    WINDOW
                  </span>

                  <h3>
                    Current operations are
                    already efficient
                  </h3>

                  <p>
                    {optimization?.recommendation ||
                      "No meaningful lower-demand period was identified in the next 24 hours."}
                  </p>

                </div>

              </div>

            )}

          </section>
        )}


        {/* RESEARCH RESULTS: synthetic carbon-aware scheduling experiments */}
        <section className="research-section" id="research-results">
          <div className="research-heading">
            <div>
              <span className="research-eyebrow">GREENMIND AI · RESEARCH LAB</span>
              <h2>Carbon-aware Scheduling Research</h2>
              <p>Scenario experiments comparing scheduling policies under different workload, grid-carbon, and facility-overhead assumptions.</p>
            </div>
            <span className="research-status">SIMULATION RESULTS</span>
          </div>
          {researchLoading ? (
            <div className="research-panel research-loading"><span className="loading-spinner">🌱</span><p>Loading research results…</p></div>
          ) : researchError ? (
            <div className="research-panel research-error"><strong>Research data unavailable</strong><p>{researchError}</p></div>
          ) : (
            <>
              <div className="research-kpi-grid">
                <div className="research-kpi"><span>SCENARIO COMBINATIONS</span><strong>{formatNumber(matchedSummary.length)}</strong><small>Across PUE, carbon variability, workload size and capacity</small></div>
                <div className="research-kpi"><span>PAIRED TRIALS</span><strong>{formatNumber(matchedSummary.reduce((sum, row) => sum + (Number(row.trials) || 0), 0))}</strong><small>10 paired seeds per scenario, 3 policies</small></div>
                <div className="research-kpi"><span>MEAN CARBON-AWARE REDUCTION</span><strong>{formatNumber(researchMeanReduction, 2)}%</strong><small>Matched completed jobs, scenario-average</small></div>
                <div className="research-kpi"><span>COMMON-WORK COVERAGE</span><strong>{formatNumber(researchCoverage, 2)}%</strong><small>Average work represented in matched comparisons</small></div>
                <div className="research-kpi"><span>FDR-SIGNIFICANT SCENARIOS</span><strong>{formatNumber(significantScenarios)}</strong><small>Deadline-carbon vs carbon-aware; adjusted p-value below 0.05</small></div>
              </div>
              <div className="research-panel research-experiment-panel">
                <div className="research-panel-heading"><div><h3>Single-run policy comparison</h3><p>One illustrative 240-job experiment from the saved research output</p></div><span className="research-tag">EXPERIMENT SUMMARY</span></div>
                <div className="research-policy-grid">
                  {researchExperiment.map((row) => (
                    <div className="research-policy-card" key={row.policy}>
                      <span className="research-policy-name">{row.policy.replaceAll("_", " ")}</span>
                      <strong>{formatNumber(row.emissions_kg_co2, 2)} <small>kg CO₂</small></strong>
                      <div className="research-policy-meta"><span>{formatNumber(row.completion_rate_pct, 1)}% completed</span><span>{formatNumber(row.emissions_reduction_vs_baseline_pct, 2)}% reduction</span></div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="research-panel">
                <div className="research-panel-heading">
                  <div><h3>Scenario explorer</h3><p>Filter and compare the saved experiment summaries</p></div>
                  <label className="research-select-label">Dataset
                    <select value={researchFilters.view} onChange={(event) => setResearchFilters((old) => ({ ...old, view: event.target.value }))}>
                      <option value="matched">Matched-service analysis</option><option value="sensitivity">Full-workload sensitivity</option>
                    </select>
                  </label>
                </div>
                <div className="research-filters">
                  <label>PUE scenario<select value={researchFilters.pue} onChange={(event) => setResearchFilters((old) => ({ ...old, pue: event.target.value }))}><option value="all">All scenarios</option><option value="low_overhead">Low overhead</option><option value="high_overhead">High overhead</option></select></label>
                  <label>Carbon variability<select value={researchFilters.variability} onChange={(event) => setResearchFilters((old) => ({ ...old, variability: event.target.value }))}><option value="all">All variability</option><option value="low">Low</option><option value="standard">Standard</option><option value="high">High</option></select></label>
                  <label>Jobs<select value={researchFilters.jobs} onChange={(event) => setResearchFilters((old) => ({ ...old, jobs: event.target.value }))}><option value="all">All workloads</option><option value="180">180 jobs</option><option value="240">240 jobs</option><option value="300">300 jobs</option></select></label>
                  <label>Hourly capacity<select value={researchFilters.capacity} onChange={(event) => setResearchFilters((old) => ({ ...old, capacity: event.target.value }))}><option value="all">All capacities</option><option value="8">8 units</option><option value="12">12 units</option><option value="16">16 units</option></select></label>
                  <button className="research-reset" onClick={() => setResearchFilters({ pue: "all", variability: "all", jobs: "all", capacity: "all", view: researchFilters.view })}>Reset filters</button>
                </div>
                <div className="research-chart-legend"><span><i className="research-legend-dot carbon-aware-dot" /> Carbon-aware</span><span><i className="research-legend-dot deadline-dot" /> Deadline-carbon</span></div>
                <div className="research-bars">
                  {filteredResearchRows.slice(0, 18).map((row) => {
                    const carbonReduction = Number(researchFilters.view === "matched" ? row.mean_carbon_aware_matched_reduction_pct : row.mean_carbon_aware_reduction_pct) || 0;
                    const deadlineReduction = Number(researchFilters.view === "matched" ? row.mean_deadline_carbon_matched_reduction_pct : row.mean_deadline_carbon_reduction_pct) || 0;
                    const scale = Math.max(1, ...filteredResearchRows.slice(0, 18).flatMap((item) => [
                      Number(researchFilters.view === "matched" ? item.mean_carbon_aware_matched_reduction_pct : item.mean_carbon_aware_reduction_pct) || 0,
                      Number(researchFilters.view === "matched" ? item.mean_deadline_carbon_matched_reduction_pct : item.mean_deadline_carbon_reduction_pct) || 0,
                    ]));
                    return <div className="research-bar-row" key={`${row.pue_scenario}-${row.carbon_variability}-${row.job_count}-${row.hourly_capacity}`}>
                      <div className="research-bar-label"><strong>{row.pue_scenario.replace("_", " ")} · {row.carbon_variability}</strong><span>{row.job_count} jobs / {row.hourly_capacity} units per hour</span></div>
                      <div className="research-bar-track"><div className="research-bar-fill carbon-aware-fill" style={{ width: `${Math.max(0, carbonReduction / scale * 100)}%` }} /></div><span className="research-bar-value">{formatNumber(carbonReduction, 2)}%</span>
                      <div className="research-bar-track"><div className="research-bar-fill deadline-fill" style={{ width: `${Math.max(0, deadlineReduction / scale * 100)}%` }} /></div><span className="research-bar-value">{formatNumber(deadlineReduction, 2)}%</span>
                    </div>;
                  })}
                </div>
                <div className="research-table-header"><strong>Scenario data</strong><span>{formatNumber(filteredResearchRows.length)} matching scenarios · showing up to 81</span></div>
                <div className="research-table-wrap">
                  <table className="research-table">
                    <thead><tr><th>PUE</th><th>Carbon</th><th>Jobs</th><th>Capacity</th><th>Coverage</th><th>Carbon-aware reduction</th><th>Deadline-carbon reduction</th>{researchFilters.view === "matched" && <th>FDR significant</th>}</tr></thead>
                    <tbody>
                      {filteredResearchRows.map((row) => {
                        const coverage = researchFilters.view === "matched" ? row.mean_common_work_coverage_pct : row.mean_carbon_aware_work_completion_pct;
                        const carbonReduction = researchFilters.view === "matched" ? row.mean_carbon_aware_matched_reduction_pct : row.mean_carbon_aware_reduction_pct;
                        const deadlineReduction = researchFilters.view === "matched" ? row.mean_deadline_carbon_matched_reduction_pct : row.mean_deadline_carbon_reduction_pct;
                        return <tr key={`${row.pue_scenario}-${row.carbon_variability}-${row.job_count}-${row.hourly_capacity}`}>
                          <td>{row.pue_scenario.replace("_", " ")}</td><td>{row.carbon_variability}</td><td>{row.job_count}</td><td>{row.hourly_capacity}</td><td>{formatNumber(coverage, 2)}%</td><td>{formatNumber(carbonReduction, 2)}%</td><td>{formatNumber(deadlineReduction, 2)}%</td>
                          {researchFilters.view === "matched" && <td><span className={String(row.significant_fdr_0_05).toLowerCase() === "true" ? "research-significant yes" : "research-significant"}>{String(row.significant_fdr_0_05).toLowerCase() === "true" ? "Yes" : "No"}</span></td>}
                        </tr>;
                      })}
                    </tbody>
                  </table>
                </div>
                <p className="research-footnote">Interpretation note: all research values come from synthetic simulation inputs, not live data-center measurements. Matched-service emissions compare the same jobs completed by all three policies; coverage is shown because the matched subset may not represent all generated work. The 6 FDR-significant scenario comparisons concern the deadline-carbon versus carbon-aware difference, not a universal claim of superiority.</p>
                <div className="research-links"><a href="https://github.com/dakshrathi911/greenmind-research/blob/main/research/results/matched_service_analysis_report.md" target="_blank" rel="noreferrer">Read matched-service report ↗</a><a href="https://github.com/dakshrathi911/greenmind-research/blob/main/research/results/sensitivity_summary.csv" target="_blank" rel="noreferrer">Sensitivity summary CSV ↗</a><a href="https://github.com/dakshrathi911/greenmind-research/blob/main/research/results/sensitivity_trials.csv" target="_blank" rel="noreferrer">All sensitivity trials CSV ↗</a><a href="https://github.com/dakshrathi911/greenmind-research/blob/main/research/results/matched_service_scenario_summary.csv" target="_blank" rel="noreferrer">Matched-service summary CSV ↗</a><a href="https://github.com/dakshrathi911/greenmind-research/blob/main/research/results/matched_service_trials.csv" target="_blank" rel="noreferrer">All matched-service trials CSV ↗</a><a href="https://github.com/dakshrathi911/greenmind-research/blob/main/research/results/job_schedules.csv" target="_blank" rel="noreferrer">Per-job schedules CSV ↗</a></div>
              </div>
            </>
          )}
        </section>

        {/* FOOTER */}
        <footer>
          <span>GreenMind AI</span>

          <span>
            AI-powered energy intelligence •
            System operational
          </span>
        </footer>

      </main>
    </div>
  );
}

export default App;