import type { DropStatus } from "../types";
import "./StatusPill.css";

const LABELS: Record<DropStatus, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  active: "Live",
  paused: "Paused",
  capacity_reached: "Sold out",
  expired: "Expired",
  completed: "Completed",
  cancelled: "Cancelled",
};

export function StatusPill({ status }: { status: DropStatus }) {
  return <span className={`status-pill status-pill--${status}`}>{LABELS[status]}</span>;
}
