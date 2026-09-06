import { useState } from "react";

import type { BusinessDrop } from "../types";
import { CapacityBar } from "./CapacityBar";
import { StatusPill } from "./StatusPill";
import "./DropCard.css";

const CATEGORY_LABELS: Record<string, string> = {
  food_dining: "Food & dining",
  activity_entertainment: "Activity & entertainment",
  nightlife: "Nightlife",
  wellness_beauty: "Wellness & beauty",
  retail: "Retail",
  other: "Other",
};

interface DropCardProps {
  drop: BusinessDrop;
  onPublish: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onCancel: (id: string) => void;
  busy?: boolean;
}

export function DropCard({ drop, onPublish, onPause, onResume, onCancel, busy }: DropCardProps) {
  const [expanded, setExpanded] = useState(false);

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
        &middot; <span className={`rarity-${drop.rarity}`}>{drop.rarity}</span>
      </p>
      <CapacityBar reserved={drop.reserved_count} capacity={drop.max_capacity_participants} />

      <button
        type="button"
        className="drop-card__details-toggle"
        onClick={() => setExpanded((current) => !current)}
      >
        {expanded ? "Hide details ⌃" : "Show details ⌄"}
      </button>

      {expanded && (
        <dl className="drop-card__details">
          {drop.description && (
            <div className="drop-card__details-row drop-card__details-row--full">
              <dt>Description</dt>
              <dd>{drop.description}</dd>
            </div>
          )}
          <div className="drop-card__details-row">
            <dt>Category</dt>
            <dd>{CATEGORY_LABELS[drop.category] ?? drop.category}</dd>
          </div>
          <div className="drop-card__details-row">
            <dt>Interest tag</dt>
            <dd>{drop.interest_tag}</dd>
          </div>
          <div className="drop-card__details-row">
            <dt>Discount</dt>
            <dd>{drop.discount_percent}%</dd>
          </div>
          <div className="drop-card__details-row">
            <dt>Rarity (computed)</dt>
            <dd className={`drop-card__rarity rarity-${drop.rarity}`}>{drop.rarity}</dd>
          </div>
          <div className="drop-card__details-row">
            <dt>Reveal radius</dt>
            <dd>{drop.discover_radius_m} m</dd>
          </div>
          <div className="drop-card__details-row">
            <dt>Starts</dt>
            <dd>{new Date(drop.starts_at).toLocaleString()}</dd>
          </div>
          <div className="drop-card__details-row">
            <dt>Ends</dt>
            <dd>{new Date(drop.ends_at).toLocaleString()}</dd>
          </div>
          <div className="drop-card__details-row">
            <dt>XP reward (computed)</dt>
            <dd>{drop.xp_reward_base}</dd>
          </div>
        </dl>
      )}

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
