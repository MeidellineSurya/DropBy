import { Html5Qrcode } from "html5-qrcode";
import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../services/api";
import type { Redemption } from "../types";
import "./ScanPage.css";

const READER_ID = "dropby-qr-reader";

// Scanning a squad's code IS the verification + confirmation step — the
// business is the one confirming a claim, not the squad's own location or a
// self-reported check-in. See apps/api/app/services/redemption.py.
export function ScanPage() {
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [result, setResult] = useState<Redemption | null>(null);
  const [resultError, setResultError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    const scanner = new Html5Qrcode(READER_ID);
    scannerRef.current = scanner;
    let cancelled = false;

    scanner
      .start(
        { facingMode: "environment" },
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
        if (!cancelled) setScanning(true);
      })
      .catch((err) => {
        if (!cancelled) {
          setCameraError(
            err instanceof Error ? err.message : "Could not access the camera",
          );
        }
      });

    return () => {
      cancelled = true;
      scanner
        .stop()
        .then(() => scanner.clear())
        .catch(() => {
          /* already stopped */
        });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleScan(qrToken: string) {
    const scanner = scannerRef.current;
    if (!scanner) return;
    try {
      await scanner.pause(true);
    } catch {
      /* already paused */
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

  return (
    <div>
      <h1>Scan to confirm</h1>
      <p className="scan-hint">
        Point the camera at a squad's check-in code. Scanning confirms the
        redemption immediately — there's nothing else to approve afterward.
      </p>

      <div className="scan-frame">
        <div id={READER_ID} />
        {cameraError && (
          <p className="page-error">
            {cameraError} — check that this browser has camera permission.
          </p>
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
    </div>
  );
}
