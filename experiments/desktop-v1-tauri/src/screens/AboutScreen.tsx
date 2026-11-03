import { useEffect, useState } from 'react';
import { getDesktopStatus, type DesktopStatus } from '../lib/ipc';

export function AboutScreen() {
  const [status, setStatus] = useState<DesktopStatus | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getDesktopStatus()
      .then((s) => !cancelled && setStatus(s))
      .catch(() => !cancelled && setError(true));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <span className="eyebrow">MEDORIGIN / TRUST / ABOUT</span>
      <h1 className="page-title">About &amp; diagnostics</h1>
      <p className="sub">Explicit build identity. No telemetry, no logs with content, no phone-home.</p>

      <section className="panel" aria-label="Build identity">
        <h2>Build identity</h2>
        {error && (
          <div className="error-box" role="alert">
            <strong>Native status unavailable</strong>
            <p>Build identity cannot be trusted because the native host did not answer. This build is unverifiable until it does.</p>
          </div>
        )}
        {!error && !status && <div className="loading-skeleton" aria-label="Loading build identity" />}
        {status && (
          <div className="detail">
            <strong>Runtime</strong>
            <p className="mono">
              contract {status.contract}<br />
              mode {status.mode}<br />
              version {status.app_version}<br />
              token contract {status.token_contract}<br />
              release_authorized {String(status.release_authorized)}<br />
              webview_egress_qualified {String(status.webview_egress_qualified)}
            </p>
          </div>
        )}
        <div className="detail">
          <strong>What this is</strong>
          <p>
            A synthetic developer preview of MedOrigin Desktop v1 (Slice 1). Design tokens and the capability model are drawn from
            PR #870. The product identity (brand, name, icon) is a placeholder — Overlap Forward v2 remains pending separate optical
            approval and is not represented here.
          </p>
        </div>
        <div className="detail">
          <strong>What this is not</strong>
          <p>
            Not a clinical product. Not releasable. Not offline-qualified. Not reviewed for any medical use. No real patient data has
            ever been, or may ever be, processed by this build.
          </p>
        </div>
      </section>
    </>
  );
}
