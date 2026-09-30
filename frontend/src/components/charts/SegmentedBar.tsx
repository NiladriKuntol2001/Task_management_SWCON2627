import type { LabelCount, PriorityLevel } from "../../types";
import { PRIORITY_COLORS } from "./chartTheme";

/** One horizontal bar split by priority level, with a labeled count per level
 *  beneath it — a compact "where is my open work" read for the student dashboard. */
export default function SegmentedBar({ data }: { data: LabelCount[] }) {
  const total = data.reduce((sum, d) => sum + d.count, 0);

  return (
    <div className="segmented">
      <div className="segmented-bar" role="img" aria-label={data.map((d) => `${d.label}: ${d.count}`).join(", ")}>
        {total === 0 ? (
          <span className="segmented-empty" />
        ) : (
          data
            .filter((d) => d.count > 0)
            .map((d) => (
              <span
                key={d.label}
                className="segmented-seg"
                style={{ flexGrow: d.count, background: PRIORITY_COLORS[d.label as PriorityLevel] }}
                title={`${d.label}: ${d.count}`}
              />
            ))
        )}
      </div>
      <div className="segmented-legend">
        {data.map((d) => (
          <span key={d.label} className="legend-item">
            <span className="legend-swatch" style={{ background: PRIORITY_COLORS[d.label as PriorityLevel] }} />
            {d.label} <strong>{d.count}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}
