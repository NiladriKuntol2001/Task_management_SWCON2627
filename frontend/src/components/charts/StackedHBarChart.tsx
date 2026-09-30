import { useState } from "react";
import { SERIES } from "./chartTheme";

export interface StackedRow {
  label: string;
  a: number; // first segment (e.g. open)
  b: number; // second segment (e.g. completed)
  detail?: string;
}

/** Two-part horizontal bars (e.g. open vs completed per subject), with a 2px
 *  surface gap between segments, a legend, and a total at the bar end. */
export default function StackedHBarChart({
  rows,
  aLabel,
  bLabel,
  emptyText = "No data yet.",
}: {
  rows: StackedRow[];
  aLabel: string;
  bLabel: string;
  emptyText?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...rows.map((r) => r.a + r.b));

  if (rows.length === 0) return <p className="chart-empty">{emptyText}</p>;

  return (
    <div>
      <div className="chart-legend">
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: SERIES.primary }} />
          {aLabel}
        </span>
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: SERIES.secondary }} />
          {bLabel}
        </span>
      </div>
      <div className="hbar-chart" role="list">
        {rows.map((r, i) => {
          const total = r.a + r.b;
          return (
            <div
              key={r.label}
              role="listitem"
              className={`hbar-row ${hover !== null && hover !== i ? "dimmed" : ""}`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              aria-label={`${r.label}: ${r.a} ${aLabel.toLowerCase()}, ${r.b} ${bLabel.toLowerCase()}`}
            >
              <span className="hbar-label" title={r.label}>
                {r.label}
              </span>
              <span className="hbar-track">
                <span className="hbar-stack" style={{ width: `${(total / max) * 100}%` }}>
                  {r.a > 0 && (
                    <span className="hbar-seg" style={{ flexGrow: r.a, background: SERIES.primary }} />
                  )}
                  {r.b > 0 && (
                    <span className="hbar-seg" style={{ flexGrow: r.b, background: SERIES.secondary }} />
                  )}
                </span>
                {hover === i && (
                  <span className="chart-tooltip hbar-tooltip">
                    <strong>{r.label}</strong>
                    <span>
                      {r.a} {aLabel.toLowerCase()} · {r.b} {bLabel.toLowerCase()}
                    </span>
                    {r.detail && <span className="tooltip-muted">{r.detail}</span>}
                  </span>
                )}
              </span>
              <span className="hbar-value">{total}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
