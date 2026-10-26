import { useMemo, useState } from "react";

function EnergyChart({ data }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  const chart = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        points: [],
        path: "",
        areaPath: "",
        min: 0,
        max: 0,
      };
    }

    const width = 900;
    const height = 300;

    const padding = {
      top: 25,
      right: 25,
      bottom: 45,
      left: 45,
    };

    const values = data.map((item) => item.energy);

    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);

    const range = Math.max(maxValue - minValue, 1);

    const points = data.map((item, index) => {
      const x =
        padding.left +
        (index / Math.max(data.length - 1, 1)) *
          (width - padding.left - padding.right);

      const y =
        padding.top +
        (1 - (item.energy - minValue) / range) *
          (height - padding.top - padding.bottom);

      return {
        ...item,
        x,
        y,
      };
    });

    const path = points
      .map((point, index) => {
        return `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`;
      })
      .join(" ");

    const lastPoint = points[points.length - 1];
    const firstPoint = points[0];

    const areaPath = `
      ${path}
      L ${lastPoint.x} ${height - padding.bottom}
      L ${firstPoint.x} ${height - padding.bottom}
      Z
    `;

    return {
      points,
      path,
      areaPath,
      min: minValue,
      max: maxValue,
    };
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="energy-chart-empty">
        No energy data available.
      </div>
    );
  }

  const gridValues = [
    chart.max,
    chart.min + (chart.max - chart.min) * 0.75,
    chart.min + (chart.max - chart.min) * 0.5,
    chart.min + (chart.max - chart.min) * 0.25,
    chart.min,
  ];

  return (
    <div className="energy-chart">

      <svg
        viewBox="0 0 900 300"
        preserveAspectRatio="none"
        className="energy-chart-svg"
      >

        {/* Grid */}

        {gridValues.map((value, index) => {

          const y =
            25 +
            (index / 4) *
              (300 - 25 - 45);

          return (
            <g key={index}>

              <line
                x1="45"
                x2="875"
                y1={y}
                y2={y}
                className="chart-grid-line"
              />

              <text
                x="5"
                y={y + 4}
                className="chart-axis-label"
              >
                {Math.round(value)}
              </text>

            </g>
          );
        })}

        {/* Area */}

        <path
          d={chart.areaPath}
          className="chart-area"
        />

        {/* Main line */}

        <path
          d={chart.path}
          className="chart-path"
        />

        {/* Data points */}

        {chart.points.map((point, index) => (

          <g key={`${point.time}-${index}`}>

            <circle
              cx={point.x}
              cy={point.y}
              r={hoveredPoint === index ? 7 : 4}
              className="chart-point"
              onMouseEnter={() => setHoveredPoint(index)}
              onMouseLeave={() => setHoveredPoint(null)}
            />

            {hoveredPoint === index && (
              <g className="chart-tooltip">

                <rect
                  x={Math.min(point.x - 55, 785)}
                  y={Math.max(point.y - 65, 5)}
                  width="110"
                  height="48"
                  rx="9"
                />

                <text
                  x={Math.min(point.x, 840)}
                  y={Math.max(point.y - 43, 23)}
                  textAnchor="middle"
                  className="tooltip-time"
                >
                  {point.time}
                </text>

                <text
                  x={Math.min(point.x, 840)}
                  y={Math.max(point.y - 25, 41)}
                  textAnchor="middle"
                  className="tooltip-value"
                >
                  {point.energy} kW
                </text>

              </g>
            )}

          </g>

        ))}

        {/* X axis */}

        {chart.points.map((point, index) => {

          const showLabel =
            index === 0 ||
            index === chart.points.length - 1 ||
            index % 2 === 0;

          if (!showLabel) {
            return null;
          }

          return (
            <text
              key={`label-${point.time}`}
              x={point.x}
              y="288"
              textAnchor="middle"
              className="chart-axis-label"
            >
              {point.time}
            </text>
          );
        })}

      </svg>
    </div>
  );
}

export default EnergyChart;