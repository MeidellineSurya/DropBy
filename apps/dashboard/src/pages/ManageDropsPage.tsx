import { useEffect, useState } from "react";

import { DropCard } from "../components/DropCard";
import { ApiError, api } from "../services/api";
import { connectLiveSocket } from "../services/ws";
import type { BusinessDrop } from "../types";
import "./ManageDropsPage.css";

// Every Drop this business owns, with publish/pause/resume/cancel actions —
// a management list, not a queue of things awaiting confirmation. That's a
// separate page now (RedemptionQueuePage, "Redemption Log" in the sidebar);
// this file used to be called LiveQueuePage from when the two were still
// one page and redemption confirmation hadn't been built yet.
export function ManageDropsPage() {
  const [drops, setDrops] = useState<BusinessDrop[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);

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

  // A Drop that's since been deleted elsewhere (or one this page never
  // knew about) shouldn't linger in the selection set.
  useEffect(() => {
    const dropIds = new Set(drops.map((drop) => drop.id));
    setSelectedIds((current) => {
      const next = new Set([...current].filter((id) => dropIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [drops]);

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
        ? "Permanently delete this Drop? This can't be undone. Drops with squad activity can't be deleted — cancel those instead."
        : `Permanently delete these ${ids.length} Drops? This can't be undone. Any with squad activity will be skipped — cancel those instead.`,
    );
    if (!confirmed) return;

    setError(null);
    setDeleting(true);
    const results = await Promise.allSettled(ids.map((id) => api.deleteDrop(id)));
    const failures = results
      .map((result, index) => ({ result, id: ids[index] }))
      .filter((entry): entry is { result: PromiseRejectedResult; id: string } =>
        entry.result.status === "rejected",
      );
    if (failures.length > 0) {
      const messages = failures.map(({ result }) =>
        result.reason instanceof ApiError ? result.reason.message : "Failed to delete",
      );
      setError(
        failures.length === ids.length
          ? messages[0]
          : `${failures.length} of ${ids.length} couldn't be deleted: ${messages[0]}`,
      );
    }
    setSelectedIds(new Set());
    setDeleting(false);
    reload();
  }

  if (error) return <p className="page-error">{error}</p>;

  return (
    <div>
      <div className="manage-drops__header">
        <h1>Manage Drops</h1>
        {selectedIds.size > 0 && (
          <button
            type="button"
            className="manage-drops__delete"
            disabled={deleting}
            onClick={() => void deleteSelected()}
          >
            {deleting ? "Deleting…" : `Delete ${selectedIds.size} selected`}
          </button>
        )}
      </div>
      {drops.length === 0 ? (
        <p>No Drops yet — create one to get started.</p>
      ) : (
        <div className="drop-list">
          {drops.map((drop) => (
            <DropCard
              key={drop.id}
              drop={drop}
              busy={busyId === drop.id}
              selected={selectedIds.has(drop.id)}
              onToggleSelect={() => toggleSelected(drop.id)}
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
