import { useEffect, useState } from "react";

import { ApiError, api } from "../services/api";
import type { BusinessOverview } from "../types";
import "./OverviewPage.css";

export function OverviewPage() {
  const [overview, setOverview] = useState<BusinessOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .overview()
      .then(setOverview)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
  }, []);

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
    </div>
  );
}
