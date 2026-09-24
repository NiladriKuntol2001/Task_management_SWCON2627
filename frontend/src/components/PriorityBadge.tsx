import type { PriorityLevel } from "../types";

const CLASS_BY_LEVEL: Record<PriorityLevel, string> = {
  Critical: "badge badge-critical",
  High: "badge badge-high",
  Medium: "badge badge-medium",
  Low: "badge badge-low",
};

export default function PriorityBadge({ level, score }: { level: PriorityLevel; score?: number }) {
  return (
    <span className={CLASS_BY_LEVEL[level]}>
      {level}
      {score !== undefined ? ` (${Math.round(score)})` : ""}
    </span>
  );
}
