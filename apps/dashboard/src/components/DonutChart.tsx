import "./DonutChart.css";

export interface DonutSegment {
  label: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  segments: DonutSegment[];
  size?: number;
  thickness?: number;
  centerLabel?: string;
  centerValue?: string | number;
  /** Renders a colour-swatch legend below the chart. Off by default since
   *  some callers (e.g. a chart sitting next to its own stat cards) don't
   *  need a second copy of the same numbers. */
  legend?: boolean;
  /** Denominator for each segment's share of the ring, if it isn't just
   *  "every segment adds up to the whole" — e.g. a single "Reserved"
   *  segment against a Drop's total capacity, where the remaining space
   *  isn't a segment of its own, just empty track. Defaults to the sum of
   *  every segment's value. */
  total?: number;
}

// A dependency-free ring chart — this app has no charting library, and one
// SVG ring with a handful of segments doesn't need one. Segments with 0
// value are skipped so an all-zero data set (e.g. a Drop with no squads
// yet) renders as an empty track rather than a stray sliver.
export function DonutChart({
  segments,
  size = 140,
  thickness = 18,
  centerLabel,
  centerValue,
  legend = false,
  total: totalOverride,
}: DonutChartProps) {
  const total = totalOverride ?? segments.reduce((sum, segment) => sum + segment.value, 0);
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  let cumulative = 0;

  return (
    <div className="donut-chart-block">
      <div className="donut-chart" style={{ width: size, height: size }}>
        <svg height={size} viewBox={`0 0 ${size} ${size}`} width={size}>
          <circle
            cx={size / 2}
            cy={size / 2}
            fill="none"
            r={radius}
            stroke="var(--color-border)"
            strokeWidth={thickness}
          />
          {total > 0 &&
            segments
              .filter((segment) => segment.value > 0)
              .map((segment) => {
                const dash = (segment.value / total) * circumference;
                const offset = -cumulative;
                cumulative += dash;
                return (
                  <circle
                    cx={size / 2}
                    cy={size / 2}
                    fill="none"
                    key={segment.label}
                    r={radius}
                    stroke={segment.color}
                    strokeDasharray={`${dash} ${circumference - dash}`}
                    strokeDashoffset={offset}
                    strokeWidth={thickness}
                    transform={`rotate(-90 ${size / 2} ${size / 2})`}
                  />
                );
              })}
        </svg>
        {(centerLabel !== undefined || centerValue !== undefined) && (
          <div className="donut-chart__center">
            {centerValue !== undefined && (
              <span className="donut-chart__value">{centerValue}</span>
            )}
            {centerLabel !== undefined && (
              <span className="donut-chart__label">{centerLabel}</span>
            )}
          </div>
        )}
      </div>
      {legend && (
        <ul className="chart-legend">
          {segments.map((segment) => (
            <li key={segment.label}>
              <span className="chart-legend__swatch" style={{ background: segment.color }} />
              <span className="chart-legend__label">{segment.label}</span>
              <span className="chart-legend__value">{segment.value}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
