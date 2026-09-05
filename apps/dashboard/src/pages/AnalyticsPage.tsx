import { useEffect, useState } from "react";

import { ApiError, api } from "../services/api";
import type { BusinessDrop, DropFunnel } from "../types";
import "./AnalyticsPage.css";

export function AnalyticsPage() {
  const [drops, setDrops] = useState<BusinessDrop[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [funnel, setFunnel] = useState<DropFunnel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listDrops()
      .then((loaded) => {
        setDrops(loaded);
        if (loaded.length > 0) setSelectedId(loaded[0].id);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    api
      .dropFunnel(selectedId)
      .then(setFunnel)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
  }, [selectedId]);

  return (
    <div>
      <h1>Drop analytics</h1>
      {error && <p className="page-error">{error}</p>}
      {drops.length === 0 ? (
        <p>Create a Drop to see performance data.</p>
      ) : (
        <>
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
            {drops.map((drop) => (
              <option key={drop.id} value={drop.id}>
                {drop.title}
              </option>
            ))}
          </select>

          {funnel && (
            <div className="funnel">
              <h2>Discovery funnel</h2>
              <div className="funnel__stages">
                <FunnelStage label="Detect" value={funnel.detect_count} max={funnel.detect_count} />
                <FunnelStage
                  label="Revealed"
                  value={funnel.revealed_count}
                  max={funnel.detect_count}
                />
              </div>

              <h2>Squads</h2>
              <div className="stat-grid">
                <div className="stat-card">
                  <span className="stat-card__value">{funnel.squads_forming}</span>
                  <span className="stat-card__label">Forming</span>
                </div>
                <div className="stat-card">
                  <span className="stat-card__value">{funnel.squads_ready}</span>
                  <span className="stat-card__label">Ready</span>
                </div>
                <div className="stat-card">
                  <span className="stat-card__value">{funnel.squads_checked_in}</span>
                  <span className="stat-card__label">Checked in</span>
                </div>
                <div className="stat-card">
                  <span className="stat-card__value">{funnel.squads_completed}</span>
                  <span className="stat-card__label">Completed</span>
                </div>
                <div className="stat-card">
                  <span className="stat-card__value">
                    {funnel.reserved_count}/{funnel.max_capacity_participants}
                  </span>
                  <span className="stat-card__label">Capacity reserved</span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FunnelStage({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="funnel-stage">
      <div className="funnel-stage__bar-track">
        <div className="funnel-stage__bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span>
        {label}: {value}
      </span>
    </div>
  );
}
