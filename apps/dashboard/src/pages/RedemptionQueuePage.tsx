import { useEffect, useState } from "react";

import { ApiError, api } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import type { Redemption } from "../types";
import "./RedemptionQueuePage.css";

// "Redemption Log" in the sidebar — a history of what's already been
// confirmed, not a queue of things waiting on this business. A redemption
// is confirmed the moment staff scan a squad's code on the Scan page —
// there's no separate approval step here (see
// apps/api/app/services/redemption.py). This page lists confirmed
// redemptions still inside the dispute window, so a business can flag one
// as fraudulent or mistaken after the fact. Disputing releases the squad's
// reserved capacity back to the Drop but does not claw back XP already
// awarded. Deleting a redemption (below) is separate and permanent — it
// removes the record entirely, also without clawing back XP.
export function RedemptionQueuePage() {
  const [redemptions, setRedemptions] = useState<Redemption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);

  function reload() {
    api
      .listRedemptions()
      .then(setRedemptions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
  }

  useEffect(() => {
    reload();
    const socket = connectLiveSocket((event) => {
      const type = (event as { type?: string }).type;
      if (type?.startsWith("redemption.")) reload();
    });
    return () => socket?.close();
  }, []);

  useEffect(() => {
    const redemptionIds = new Set(redemptions.map((r) => r.id));
    setSelectedIds((current) => {
      const next = new Set([...current].filter((id) => redemptionIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [redemptions]);

  async function dispute(id: string) {
    setBusyId(id);
    setError(null);
    try {
      const updated = await api.disputeRedemption(id);
      setRedemptions((current) => current.map((r) => (r.id === id ? updated : r)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to dispute");
    } finally {
      setBusyId(null);
    }
  }

  function toggleSelected(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function deleteSelected() {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    const confirmed = window.confirm(
      ids.length === 1
        ? "Permanently delete this redemption record? This can't be undone, and it does not claw back any XP already awarded."
        : `Permanently delete these ${ids.length} redemption records? This can't be undone, and it does not claw back any XP already awarded.`,
    );
    if (!confirmed) return;

    setError(null);
    setDeleting(true);
    const results = await Promise.allSettled(ids.map((id) => api.deleteRedemption(id)));
    const failures = results.filter((result) => result.status === "rejected");
    if (failures.length > 0) {
      const first = failures[0] as PromiseRejectedResult;
      const message = first.reason instanceof ApiError ? first.reason.message : "Failed to delete";
      setError(
        failures.length === ids.length ? message : `${failures.length} of ${ids.length} couldn't be deleted: ${message}`,
      );
    }
    setSelectedIds(new Set());
    setDeleting(false);
    reload();
  }

  return (
    <div>
      <div className="redemption-log__header">
        <h1>Redemption Log</h1>
        {selectedIds.size > 0 && (
          <button
            type="button"
            className="redemption-log__delete"
            disabled={deleting}
            onClick={() => void deleteSelected()}
          >
            {deleting ? "Deleting…" : `Delete ${selectedIds.size} selected`}
          </button>
        )}
      </div>
      {error ? (
        <p className="page-error">{error}</p>
      ) : redemptions.length === 0 ? (
        <p>
          No redemptions confirmed in the last 24 hours. Scan a squad's code
          on the Scan page to confirm one — it'll show up here to review or
          flag afterward.
        </p>
      ) : (
        <div className="redemption-list">
          {redemptions.map((redemption) => (
            <div
              key={redemption.id}
              className={`redemption-card ${selectedIds.has(redemption.id) ? "redemption-card--selected" : ""}`}
            >
              <div className="redemption-card__header">
                <label className="redemption-card__select">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(redemption.id)}
                    onChange={() => toggleSelected(redemption.id)}
                    aria-label={`Select redemption for ${redemption.drop_title}`}
                  />
                  <h3>{redemption.drop_title}</h3>
                </label>
                <span className="redemption-card__time">
                  Confirmed{" "}
                  {redemption.confirmed_at
                    ? new Date(redemption.confirmed_at).toLocaleTimeString()
                    : "—"}
                </span>
              </div>
              <p className="redemption-card__meta">
                {redemption.participant_count ?? redemption.member_count} redeemed &middot;{" "}
                {redemption.xp_reward_base} XP each
              </p>
              {redemption.disputed_at && (
                <p className="redemption-card__disputed">Flagged as fraudulent/mistaken</p>
              )}
              <div className="redemption-card__actions">
                {!redemption.disputed_at && (
                  <button
                    disabled={busyId === redemption.id}
                    className="redemption-card__reject"
                    onClick={() => dispute(redemption.id)}
                  >
                    Flag as fraudulent
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
