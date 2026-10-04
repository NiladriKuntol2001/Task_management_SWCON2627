export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** "in 3 days", "2 hours ago" — used next to deadlines so urgency reads at a glance. */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const diffMs = new Date(iso).getTime() - now.getTime();
  const abs = Math.abs(diffMs);
  const minutes = Math.round(abs / 60000);
  const hours = Math.round(abs / 3600000);
  const days = Math.round(abs / 86400000);
  let text: string;
  if (minutes < 60) text = `${minutes} min`;
  else if (hours < 48) text = `${hours} h`;
  else text = `${days} days`;
  return diffMs >= 0 ? `in ${text}` : `${text} ago`;
}

export function formatNumber(n: number): string {
  return n.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

/** The main administrator always has user ID 1. */
export const ROOT_ADMIN_ID = 1;
