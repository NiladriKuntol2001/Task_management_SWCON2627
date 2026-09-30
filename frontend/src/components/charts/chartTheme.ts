import type { PriorityLevel } from "../../types";

// Categorical slots 1-2 of the reference palette (validated as a pair:
// CVD ΔE 24.7, normal-vision ΔE 33.6, both >= 3:1 on the light surface).
export const SERIES = {
  primary: "#2a78d6", // blue
  secondary: "#eb6834", // orange
};

// Priority levels are a severity scale, so they use the fixed status palette
// and are ALWAYS shown next to their text label, never by color alone.
export const PRIORITY_COLORS: Record<PriorityLevel, string> = {
  Low: "#0ca30c",
  Medium: "#fab219",
  High: "#ec835a",
  Critical: "#d03b3b",
};

export const CRITICAL = "#d03b3b";

export const CHROME = {
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  muted: "#898781",
  secondaryInk: "#52514e",
  primaryInk: "#0b0b0b",
};
