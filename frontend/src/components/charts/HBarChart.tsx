import { useState } from "react";

export interface HBarDatum {
  label: string;
  value: number;
  color: string;
  /** Extra line for the tooltip, e.g. "3 overdue". */
  detail?: string;
}

/** Horizontal bars for a handful of categories. Each bar is labeled by name
 *  (left) and value (right), so color is never the only carrier of meaning. */
export default function HBarChart({
  data,
  unit = "",
  emptyText = "No data yet.",
}: {
  data: HBarDatum[];
  unit?: string;
  emptyText?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...data.map((d) => d.value));

  if (data.every((d) => d.value === 0)) {
    return <p className="chart-empty">{emptyText}</p>;
  }

  return (
    <div className="hbar-chart" role="list">
      {data.map((d, i) => (
        <div
          key={d.label}
          role="listitem"
          className={`hbar-row ${hover !== null && hover !== i ? "dimmed" : ""}`}
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(null)}
          aria-label={`${d.label}: ${d.value}${unit}`}
        >
          <span className="hbar-label">{d.label}</span>
          <span className="hbar-track">
            <span
              className="hbar-fill"
              style={{ width: `${(d.value / max) * 100}%`, background: d.color }}
            />
            {hover === i && (
              <span className="chart-tooltip hbar-tooltip">
                <strong>{d.label}</strong>
                <span>
                  {d.value}
                  {unit}
                </span>
                {d.detail && <span className="tooltip-muted">{d.detail}</span>}
              </span>
            )}
          </span>
          <span className="hbar-value">{d.value}</span>
        </div>
      ))}
    </div>
  );
}
