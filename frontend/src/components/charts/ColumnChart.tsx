import { useState } from "react";
import { CHROME } from "./chartTheme";
import { useWidth } from "./useWidth";

export interface ColumnDatum {
  label: string;
  value: number;
  color: string;
}

const HEIGHT = 210;
const M = { top: 22, right: 8, bottom: 34, left: 8 };

/** Vertical columns for an ordered set of buckets (e.g. deadline bands).
 *  Rounded 4px data-end anchored to the baseline; value label on top. */
export default function ColumnChart({ data, emptyText = "No data yet." }: { data: ColumnDatum[]; emptyText?: string }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  if (data.every((d) => d.value === 0)) {
    return <p className="chart-empty">{emptyText}</p>;
  }

  const innerW = Math.max(0, width - M.left - M.right);
  const innerH = HEIGHT - M.top - M.bottom;
  const band = innerW / data.length;
  const barW = Math.min(44, band * 0.62);
  const max = Math.max(1, ...data.map((d) => d.value));
  const r = 4;

  return (
    <div ref={ref} className="svg-chart">
      <svg width={width} height={HEIGHT} role="img" aria-label={data.map((d) => `${d.label}: ${d.value}`).join(", ")}>
        <g transform={`translate(${M.left},${M.top})`}>
          {data.map((d, i) => {
            const h = (d.value / max) * innerH;
            const x = i * band + (band - barW) / 2;
            const y = innerH - h;
            const rr = Math.min(r, h);
            const path =
              h > 0
                ? `M${x},${innerH} V${y + rr} Q${x},${y} ${x + rr},${y} H${x + barW - rr} Q${x + barW},${y} ${x + barW},${y + rr} V${innerH} Z`
                : "";
            const dim = hover !== null && hover !== i;
            return (
              <g key={d.label} opacity={dim ? 0.35 : 1}>
                {path && <path d={path} fill={d.color} />}
                <text x={x + barW / 2} y={y - 6} textAnchor="middle" className="svg-value">
                  {d.value}
                </text>
                <text x={i * band + band / 2} y={innerH + 18} textAnchor="middle" className="svg-axis-label">
                  {d.label}
                </text>
                {/* Hit target: the whole band, larger than the mark. */}
                <rect
                  x={i * band}
                  y={0}
                  width={band}
                  height={innerH + 24}
                  fill="transparent"
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                />
              </g>
            );
          })}
          <line x1={0} x2={innerW} y1={innerH} y2={innerH} stroke={CHROME.axis} />
        </g>
      </svg>
      {hover !== null && (
        <div
          className="chart-tooltip svg-tooltip"
          style={{ left: M.left + hover * band + band / 2, top: M.top }}
        >
          <strong>{data[hover].label}</strong>
          <span>
            {data[hover].value} open task{data[hover].value === 1 ? "" : "s"}
          </span>
        </div>
      )}
    </div>
  );
}
