import { useEffect, useState } from "react";

import { ApiError, api } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import type { Redemption } from "../types";
import "./RedemptionQueuePage.css";

// The live queue of squads that have checked in at the venue (scanned the
// Drop's QR) and are waiting on a business to confirm they're legitimate
// before XP is awarded — see apps/api/app/services/redemption.py.
export function RedemptionQueuePage() {
  const [redemptions, setRedemptions] = useState<Redemption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<Record<string, string>>({});

  function reload() {
    api
      .listRedemptions("checked_in")
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

  async function confirm(id: string) {
    setBusyId(id);
    setError(null);
    try {
      const raw = overrides[id];
      const participantCount = raw ? Number(raw) : undefined;
      await api.confirmRedemption(id, participantCount);
      setRedemptions((current) => current.filter((r) => r.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to confirm");
    } finally {
      setBusyId(null);
    }
  }

  async function reject(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await api.rejectRedemption(id);
      setRedemptions((current) => current.filter((r) => r.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reject");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <h1>Live Queue</h1>
      {error && <p className="page-error">{error}</p>}
      {redemptions.length === 0 ? (
        <p>No squads checked in right now — they'll show up here the moment someone scans your Drop's QR.</p>
      ) : (
        <div className="redemption-list">
          {redemptions.map((redemption) => (
            <div key={redemption.id} className="redemption-card">
              <div className="redemption-card__header">
                <h3>{redemption.drop_title}</h3>
                <span className="redemption-card__time">
                  Checked in{" "}
                  {redemption.checked_in_at
                    ? new Date(redemption.checked_in_at).toLocaleTimeString()
                    : "—"}
                </span>
              </div>
              <p className="redemption-card__meta">
                {redemption.member_count} on record &middot; {redemption.xp_reward_base} XP each
                on confirm
              </p>
              <label className="redemption-card__count">
                Actual headcount (optional)
                <input
                  type="number"
                  min={1}
                  placeholder={String(redemption.member_count)}
                  value={overrides[redemption.id] ?? ""}
                  onChange={(e) =>
                    setOverrides((current) => ({ ...current, [redemption.id]: e.target.value }))
                  }
                />
              </label>
              <div className="redemption-card__actions">
                <button
                  disabled={busyId === redemption.id}
                  onClick={() => confirm(redemption.id)}
                >
                  Confirm
                </button>
                <button
                  disabled={busyId === redemption.id}
                  className="redemption-card__reject"
                  onClick={() => reject(redemption.id)}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
