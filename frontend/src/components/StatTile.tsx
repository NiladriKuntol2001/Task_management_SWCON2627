import type { ReactNode } from "react";
import { Link } from "react-router-dom";

/** KPI tile: one number, one label, optional context line. When `to` is set,
 *  the whole tile links to the filtered list behind the number. */
export default function StatTile({
  value,
  label,
  hint,
  tone = "default",
  to,
}: {
  value: ReactNode;
  label: string;
  hint?: ReactNode;
  tone?: "default" | "danger" | "warning" | "good";
  to?: string;
}) {
  const content = (
    <>
      <div className="stat-label">{label}</div>
      <div className={`stat-value tone-${tone}`}>{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </>
  );
  return to ? (
    <Link to={to} className="stat-tile stat-tile-link">
      {content}
    </Link>
  ) : (
    <div className="stat-tile">{content}</div>
  );
}
