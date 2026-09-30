import { useState, type MouseEvent } from "react";
import { CHROME } from "./chartTheme";
import { useWidth } from "./useWidth";

export interface LineSeries {
  name: string;
  color: string;
  values: number[];
}

const HEIGHT = 230;
const M = { top: 14, right: 16, bottom: 30, left: 34 };

function niceMax(v: number): number {
  if (v <= 4) return 4;
  const pow = Math.pow(10, Math.floor(Math.log10(v)));
  const steps = [1, 2, 2.5, 5, 10];
  for (const s of steps) {
    if (s * pow >= v) return s * pow;
  }
  return 10 * pow;
}

/** Multi-series line chart on ONE shared y-axis, with a crosshair tooltip.
 *  2px lines, >= 8px hover markers with a surface ring, legend above. */
export default function LineChart({
  series,
  xLabels,
  emptyText = "No activity yet.",
}: {
  series: LineSeries[];
  xLabels: string[];
  emptyText?: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  const n = xLabels.length;
  const rawMax = Math.max(0, ...series.flatMap((s) => s.values));
  if (n === 0 || rawMax === 0) return <p className="chart-empty">{emptyText}</p>;

  const innerW = Math.max(0, width - M.left - M.right);
  const innerH = HEIGHT - M.top - M.bottom;
  const max = niceMax(rawMax);
  const x = (i: number) => (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const y = (v: number) => innerH - (v / max) * innerH;
  const ticks = [0, max / 2, max];
  const labelEvery = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(innerW / 70))));

  const onMove = (e: MouseEvent<SVGRectElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const idx = Math.round((px / Math.max(1, innerW)) * (n - 1));
    setHover(Math.min(n - 1, Math.max(0, idx)));
  };

  return (
    <div>
      <div className="chart-legend">
        {series.map((s) => (
          <span key={s.name} className="legend-item">
            <span className="legend-line" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
      <div ref={ref} className="svg-chart">
        <svg width={width} height={HEIGHT} role="img" aria-label={`Line chart: ${series.map((s) => s.name).join(" and ")}`}>
          <g transform={`translate(${M.left},${M.top})`}>
            {ticks.map((t) => (
              <g key={t}>
                <line x1={0} x2={innerW} y1={y(t)} y2={y(t)} stroke={t === 0 ? CHROME.axis : CHROME.grid} />
                <text x={-8} y={y(t)} dy="0.32em" textAnchor="end" className="svg-axis-label">
                  {Number.isInteger(t) ? t : t.toFixed(1)}
                </text>
              </g>
            ))}
            {xLabels.map((label, i) =>
              i % labelEvery === 0 || i === n - 1 ? (
                <text key={label} x={x(i)} y={innerH + 18} textAnchor="middle" className="svg-axis-label">
                  {label}
                </text>
              ) : null
            )}
            {series.map((s) => (
              <polyline
                key={s.name}
                fill="none"
                stroke={s.color}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
                points={s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ")}
              />
            ))}
            {hover !== null && (
              <g>
                <line x1={x(hover)} x2={x(hover)} y1={0} y2={innerH} stroke={CHROME.muted} strokeDasharray="3 3" />
                {series.map((s) => (
                  <circle
                    key={s.name}
                    cx={x(hover)}
                    cy={y(s.values[hover])}
                    r={4.5}
                    fill={s.color}
                    stroke="#ffffff"
                    strokeWidth={2}
                  />
                ))}
              </g>
            )}
            <rect
              x={0}
              y={0}
              width={innerW}
              height={innerH}
              fill="transparent"
              onMouseMove={onMove}
              onMouseLeave={() => setHover(null)}
            />
          </g>
        </svg>
        {hover !== null && (
          <div
            className="chart-tooltip svg-tooltip"
            style={{ left: M.left + x(hover), top: M.top }}
          >
            <strong>{xLabels[hover]}</strong>
            {series.map((s) => (
              <span key={s.name} className="tooltip-row">
                <span className="legend-line" style={{ background: s.color }} />
                {s.name}: {s.values[hover]}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
