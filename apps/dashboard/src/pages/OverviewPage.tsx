import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { CapacityBar } from "../components/CapacityBar";
import { STATUS_COLORS, STATUS_LABELS } from "../components/StatusPill";
import { DonutChart } from "../components/DonutChart";
import { ApiError, api } from "../services/api";
import type { BusinessDrop, BusinessOverview, DropStatus } from "../types";
import "./OverviewPage.css";

const STATUS_ORDER: DropStatus[] = [
  "active",
  "scheduled",
  "draft",
  "paused",
  "capacity_reached",
  "completed",
  "expired",
  "cancelled",
];

export function OverviewPage() {
  const [overview, setOverview] = useState<BusinessOverview | null>(null);
  const [drops, setDrops] = useState<BusinessDrop[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .overview()
      .then(setOverview)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
    // No status filter — every Drop this business has ever created, so the
    // status breakdown below is the whole picture, not just what's live.
    api
      .listDrops()
      .then(setDrops)
      .catch(() => undefined);
  }, []);

  const statusSegments = useMemo(() => {
    if (!drops) return [];
    const counts = new Map<DropStatus, number>();
    for (const drop of drops) counts.set(drop.status, (counts.get(drop.status) ?? 0) + 1);
    return STATUS_ORDER.filter((status) => counts.get(status)).map((status) => ({
      label: STATUS_LABELS[status],
      value: counts.get(status) ?? 0,
      color: STATUS_COLORS[status],
    }));
  }, [drops]);

  const busiestActiveDrops = useMemo(() => {
    if (!drops) return [];
    return drops
      .filter((drop) => drop.status === "active")
      .sort((a, b) => {
        const aPct = a.max_capacity_participants > 0 ? a.reserved_count / a.max_capacity_participants : 0;
        const bPct = b.max_capacity_participants > 0 ? b.reserved_count / b.max_capacity_participants : 0;
        return bPct - aPct;
      })
      .slice(0, 6);
  }, [drops]);

  if (error) return <p className="page-error">{error}</p>;
  if (!overview) return <p>Loading…</p>;

  const capacityPct =
    overview.total_capacity_participants > 0
      ? Math.round(
          (overview.total_reserved_participants / overview.total_capacity_participants) * 100,
        )
      : 0;

  return (
    <div>
      <h1>Overview</h1>
      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-card__value">{overview.active_drops}</span>
          <span className="stat-card__label">Live Drops</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__value">{overview.scheduled_drops}</span>
          <span className="stat-card__label">Scheduled</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__value">{overview.draft_drops}</span>
          <span className="stat-card__label">Drafts</span>
        </div>
        <div className="stat-card">
          <span className="stat-card__value">{capacityPct}%</span>
          <span className="stat-card__label">
            Capacity filled ({overview.total_reserved_participants}/
            {overview.total_capacity_participants})
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-card__value">{overview.distinct_viewers_last_7_days}</span>
          <span className="stat-card__label">Viewers, last 7 days</span>
        </div>
      </div>

      <div className="overview-panels">
        <section className="overview-panel">
          <h2>Drops by status</h2>
          {drops === null ? (
            <p className="form-hint">Loading…</p>
          ) : statusSegments.length === 0 ? (
            <p className="form-hint">Create a Drop to see this break down.</p>
          ) : (
            <DonutChart
              centerLabel="Total Drops"
              centerValue={drops.length}
              legend
              segments={statusSegments}
            />
          )}
        </section>

        <section className="overview-panel">
          <h2>Fullest live Drops</h2>
          {drops === null ? (
            <p className="form-hint">Loading…</p>
          ) : busiestActiveDrops.length === 0 ? (
            <p className="form-hint">No live Drops right now.</p>
          ) : (
            <div className="busiest-drops">
              {busiestActiveDrops.map((drop) => (
                <div className="busiest-drops__row" key={drop.id}>
                  <Link className="busiest-drops__title" to="/drops">
                    {drop.title}
                  </Link>
                  <CapacityBar capacity={drop.max_capacity_participants} reserved={drop.reserved_count} />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
