import type { DropStatus } from "../types";
import "./StatusPill.css";

export const STATUS_LABELS: Record<DropStatus, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  active: "Live",
  paused: "Paused",
  capacity_reached: "Sold out",
  expired: "Expired",
  completed: "Completed",
  cancelled: "Cancelled",
};

// Same semantic mapping as StatusPill.css's backgrounds/text colours —
// exported so other visuals (e.g. OverviewPage's status donut) use the
// exact same colour for a given status rather than a second, driftable
// copy of the mapping.
export const STATUS_COLORS: Record<DropStatus, string> = {
  draft: "var(--color-subtle)",
  scheduled: "var(--color-info)",
  active: "var(--color-secondary)",
  paused: "var(--color-warning)",
  capacity_reached: "var(--color-info)",
  expired: "var(--color-danger)",
  cancelled: "var(--color-danger)",
  completed: "var(--color-secondary)",
};

export function StatusPill({ status }: { status: DropStatus }) {
  return <span className={`status-pill status-pill--${status}`}>{STATUS_LABELS[status]}</span>;
}
