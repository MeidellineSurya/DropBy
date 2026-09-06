import { useEffect, useState } from "react";

import { ApiError, api } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import type { Redemption } from "../types";
import "./RedemptionQueuePage.css";

// Check-in auto-confirms on the spot now (a location claim, not a QR scan,
// with no business approval gate — see apps/api/app/services/redemption.py).
// This page lists confirmed redemptions still inside the dispute window, so
// a business can flag one as fraudulent or mistaken after the fact. Disputing
// releases the squad's reserved capacity back to the Drop but does not claw
// back XP already awarded.
export function RedemptionQueuePage() {
  const [redemptions, setRedemptions] = useState<Redemption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

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

  return (
    <div>
      <h1>Redemptions</h1>
      {error ? (
        <p className="page-error">{error}</p>
      ) : redemptions.length === 0 ? (
        <p>No redemptions in the last 24 hours — they'll show up here the moment someone checks in at your venue.</p>
      ) : (
        <div className="redemption-list">
          {redemptions.map((redemption) => (
            <div key={redemption.id} className="redemption-card">
              <div className="redemption-card__header">
                <h3>{redemption.drop_title}</h3>
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
              {redemption.disputed_at ? (
                <p className="redemption-card__disputed">Flagged as fraudulent/mistaken</p>
              ) : (
                <div className="redemption-card__actions">
                  <button
                    disabled={busyId === redemption.id}
                    className="redemption-card__reject"
                    onClick={() => dispute(redemption.id)}
                  >
                    Flag as fraudulent
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
