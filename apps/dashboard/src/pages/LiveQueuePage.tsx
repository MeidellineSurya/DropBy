import { useEffect, useState } from "react";

import { DropCard } from "../components/DropCard";
import { ApiError, api } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import type { BusinessDrop } from "../types";
import "./LiveQueuePage.css";

// There's no Redemption model yet (owned by the redemption/gamification
// workstream), so this is a live capacity/status board rather than a
// redemption-confirmation queue. Once that workstream lands, a "confirm"
// action per checked-in squad belongs here.
export function LiveQueuePage() {
  const [drops, setDrops] = useState<BusinessDrop[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  function reload() {
    api
      .listDrops()
      .then(setDrops)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
  }

  useEffect(() => {
    reload();
    const socket = connectLiveSocket((event) => {
      const type = (event as { type?: string }).type;
      if (type?.startsWith("drop.")) reload();
    });
    return () => socket?.close();
  }, []);

  async function withBusy(id: string, action: () => Promise<BusinessDrop>) {
    setBusyId(id);
    try {
      const updated = await action();
      setDrops((current) => current.map((drop) => (drop.id === id ? updated : drop)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  if (error) return <p className="page-error">{error}</p>;

  return (
    <div>
      <h1>Drops</h1>
      {drops.length === 0 ? (
        <p>No Drops yet — create one to get started.</p>
      ) : (
        <div className="drop-list">
          {drops.map((drop) => (
            <DropCard
              key={drop.id}
              drop={drop}
              busy={busyId === drop.id}
              onPublish={(id) => withBusy(id, () => api.publishDrop(id))}
              onPause={(id) => withBusy(id, () => api.pauseDrop(id))}
              onResume={(id) => withBusy(id, () => api.resumeDrop(id))}
              onCancel={(id) => withBusy(id, () => api.cancelDrop(id))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
