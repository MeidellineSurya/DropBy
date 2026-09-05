import type { BusinessDrop } from "../types";
import { CapacityBar } from "./CapacityBar";
import { StatusPill } from "./StatusPill";
import "./DropCard.css";

interface DropCardProps {
  drop: BusinessDrop;
  onPublish: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onCancel: (id: string) => void;
  busy?: boolean;
}

export function DropCard({ drop, onPublish, onPause, onResume, onCancel, busy }: DropCardProps) {
  return (
    <div className="drop-card">
      <div className="drop-card__header">
        <h3>{drop.title}</h3>
        <StatusPill status={drop.status} />
      </div>
      <p className="drop-card__meta">
        {drop.drop_type === "solo"
          ? "Solo"
          : `${drop.min_group_size}-${drop.max_group_size} people`}{" "}
        &middot; {drop.rarity}
      </p>
      <CapacityBar reserved={drop.reserved_count} capacity={drop.max_capacity_participants} />
      <div className="drop-card__actions">
        {drop.status === "draft" && (
          <button disabled={busy} onClick={() => onPublish(drop.id)}>
            Publish
          </button>
        )}
        {drop.status === "active" && (
          <button disabled={busy} onClick={() => onPause(drop.id)}>
            Pause
          </button>
        )}
        {drop.status === "paused" && (
          <button disabled={busy} onClick={() => onResume(drop.id)}>
            Resume
          </button>
        )}
        {["draft", "scheduled", "active", "paused"].includes(drop.status) && (
          <button disabled={busy} className="drop-card__cancel" onClick={() => onCancel(drop.id)}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
