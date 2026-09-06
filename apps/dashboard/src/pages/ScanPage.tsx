import { Html5Qrcode, type CameraDevice } from "html5-qrcode";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { ApiError, api } from "../services/api";
import type { Redemption } from "../types";
import "./ScanPage.css";

const READER_ID = "dropby-qr-reader";
const LAST_CAMERA_KEY = "dropby.scan.lastCameraId";

// Everything that can go wrong getting a live camera feed, distinguished
// because each one needs different guidance — "no camera" and "permission
// denied" are not the same problem for staff to fix, and neither is
// recoverable by silently retrying getUserMedia again.
type CameraStatus =
  | "requesting"
  | "insecure"
  | "unsupported"
  | "unavailable"
  | "denied"
  | "error"
  | "ready";

// Scanning a squad's code IS the verification + confirmation step — the
// business is the one confirming a claim, not the squad's own location or a
// self-reported check-in. See apps/api/app/services/redemption.py.
export function ScanPage() {
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const [status, setStatus] = useState<CameraStatus>("requesting");
  const [statusDetail, setStatusDetail] = useState<string | null>(null);
  const [cameras, setCameras] = useState<CameraDevice[]>([]);
  const [activeCameraId, setActiveCameraId] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<Redemption | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);
  const [manualToken, setManualToken] = useState("");

  // Enumerate cameras once. getUserMedia (which getCameras() calls under the
  // hood) is only available on a secure origin (HTTPS, or localhost) — check
  // that ourselves first so the failure reads as "wrong connection type",
  // not a generic camera error.
  useEffect(() => {
    let cancelled = false;
    if (!window.isSecureContext) {
      setStatus("insecure");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("unsupported");
      return;
    }
    Html5Qrcode.getCameras()
      .then((devices) => {
        if (cancelled) return;
        if (devices.length === 0) {
          setStatus("unavailable");
          return;
        }
        setCameras(devices);
        const remembered = localStorage.getItem(LAST_CAMERA_KEY);
        const preferred =
          devices.find((d) => d.id === remembered) ??
          devices.find((d) => /back|rear|environment/i.test(d.label)) ??
          devices[0];
        setActiveCameraId(preferred.id);
      })
      .catch((err) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        if (/notallowed|permission denied/i.test(message)) {
          setStatus("denied");
        } else if (/notfound/i.test(message)) {
          setStatus("unavailable");
        } else {
          setStatus("error");
          setStatusDetail(message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Start (or restart, on a camera switch) the live scanner once a camera
  // is chosen.
  useEffect(() => {
    if (!activeCameraId) return;
    const scanner = new Html5Qrcode(READER_ID);
    scannerRef.current = scanner;
    let cancelled = false;

    scanner
      .start(
        activeCameraId,
        { fps: 10, qrbox: { width: 260, height: 260 } },
        (decodedText) => {
          // A confirmed code keeps decoding every frame it's in view — pause
          // immediately so one scan doesn't fire this a dozen times while
          // staff hold the phone steady.
          void handleScan(decodedText);
        },
        () => {
          // Per-frame "nothing decoded this frame" — expected constantly
          // while framing the shot, not a real error.
        },
      )
      .then(() => {
        if (cancelled) return;
        setScanning(true);
        setStatus("ready");
        localStorage.setItem(LAST_CAMERA_KEY, activeCameraId);
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("error");
        setStatusDetail(err instanceof Error ? err.message : "Could not start the camera");
      });

    return () => {
      cancelled = true;
      setScanning(false);
      scanner
        .stop()
        .then(() => scanner.clear())
        .catch(() => {
          /* already stopped */
        });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCameraId]);

  async function handleScan(qrToken: string) {
    const scanner = scannerRef.current;
    if (scanner) {
      try {
        await scanner.pause(true);
      } catch {
        /* already paused, or never started (manual entry) */
      }
    }
    setResult(null);
    setResultError(null);
    try {
      const redemption = await api.scanRedemption(qrToken);
      setResult(redemption);
    } catch (err) {
      setResultError(err instanceof ApiError ? err.message : "Could not confirm this code");
    }
  }

  function scanNext() {
    setResult(null);
    setResultError(null);
    scannerRef.current?.resume();
  }

  function retryCameraAccess() {
    // A denied permission can only be undone through the browser's own
    // site-settings UI, not by calling getUserMedia again — a full reload
    // is the simplest way to re-run the request once staff have done that.
    window.location.reload();
  }

  async function submitManualToken(event: FormEvent) {
    event.preventDefault();
    const token = manualToken.trim();
    if (!token) return;
    setManualToken("");
    await handleScan(token);
  }

  return (
    <div>
      <h1>Scan to confirm</h1>
      <p className="scan-hint">
        Point the camera at a squad's check-in code. Scanning confirms the
        redemption immediately — there's nothing else to approve afterward.
      </p>

      <div className="scan-frame">
        <div id={READER_ID} hidden={status !== "ready"} />

        {status === "requesting" && (
          <p className="scan-status">Requesting camera access…</p>
        )}

        {status === "insecure" && (
          <p className="page-error">
            Camera access needs a secure connection — open this page over
            HTTPS, or via localhost, for the browser to allow it. Use the
            code entry below in the meantime.
          </p>
        )}

        {status === "unsupported" && (
          <p className="page-error">
            This browser doesn't support camera capture. Use the code entry
            below instead.
          </p>
        )}

        {status === "unavailable" && (
          <p className="page-error">
            No camera was found on this device. Use the code entry below
            instead.
          </p>
        )}

        {status === "denied" && (
          <div className="page-error">
            <p>
              Camera permission was denied. Allow camera access for this
              site in your browser's site settings, then retry — or use the
              code entry below.
            </p>
            <button type="button" onClick={retryCameraAccess}>
              Retry camera access
            </button>
          </div>
        )}

        {status === "error" && (
          <div className="page-error">
            <p>{statusDetail ?? "Could not access the camera."}</p>
            <button type="button" onClick={retryCameraAccess}>
              Retry
            </button>
          </div>
        )}

        {cameras.length > 1 && status === "ready" && (
          <label className="scan-camera-picker">
            Camera
            <select
              value={activeCameraId ?? ""}
              onChange={(event) => setActiveCameraId(event.target.value)}
            >
              {cameras.map((camera) => (
                <option key={camera.id} value={camera.id}>
                  {camera.label || camera.id}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {(result || resultError) && (
        <div className={`scan-result ${resultError ? "scan-result--error" : "scan-result--ok"}`}>
          {result && (
            <>
              <p className="scan-result__title">✓ Confirmed — {result.drop_title}</p>
              <p className="scan-result__meta">
                {result.participant_count ?? result.member_count} redeemed &middot;{" "}
                {result.xp_reward_base} XP each
              </p>
            </>
          )}
          {resultError && <p className="page-error">{resultError}</p>}
          <button type="button" onClick={scanNext} disabled={!scanning}>
            Scan next
          </button>
        </div>
      )}

      <form className="scan-manual" onSubmit={submitManualToken}>
        <label htmlFor="manual-qr-token">
          Camera not working? Type or paste the squad's code instead.
        </label>
        <div className="scan-manual__row">
          <input
            id="manual-qr-token"
            type="text"
            value={manualToken}
            onChange={(event) => setManualToken(event.target.value)}
            placeholder="group:drop:business:iat:nonce:signature"
          />
          <button type="submit" disabled={!manualToken.trim()}>
            Confirm
          </button>
        </div>
      </form>
    </div>
  );
}
