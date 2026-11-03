import { useEffect, useMemo, useState } from 'react';
import { CircleAlert, ShieldCheck } from 'lucide-react';
import { getDesktopStatus, type DesktopStatus } from '../lib/ipc';
import { ROUTES, STATUS_LABEL } from '../lib/routes';
import { StatusChip } from '../components/StatusChip';

type StatusState =
  | { kind: 'loading' }
  | { kind: 'ready'; status: DesktopStatus }
  | { kind: 'error' };

export function HomeScreen() {
  const [state, setState] = useState<StatusState>({ kind: 'loading' });
  const [filter, setFilter] = useState('');

  useEffect(() => {
    let cancelled = false;
    getDesktopStatus()
      .then((status) => {
        if (!cancelled) setState({ kind: 'ready', status });
      })
      .catch(() => {
        if (!cancelled) setState({ kind: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return ROUTES;
    return ROUTES.filter((r) => `${r.label} ${r.reason} ${r.group} ${STATUS_LABEL[r.status]}`.toLowerCase().includes(q));
  }, [filter]);

  return (
    <>
      <span className="eyebrow">MEDORIGIN / LOCAL WORKSPACE / SYNTHETIC DEVELOPER PREVIEW</span>
      <h1 className="page-title">Home</h1>
      <p className="sub">A calm, precise shell for MedOrigin's authorized, synthetic-only capabilities. Nothing here is clinical, and nothing here claims to be.</p>

      <div className="honesty-banner" role="note" aria-label="Honesty notice">
        <ShieldCheck size={18} aria-hidden="true" className="brand-icon" />
        <span>
          <b>SYNTHETIC — NOT EGRESS-QUALIFIED</b>
          <br />
          App-initiated network access is disabled; WebView2 background traffic is unqualified. D1 NO-GO (2026-10-29) stands.
        </span>
      </div>

      <section className="panel" aria-label="Environment">
        <h2>Environment</h2>
        {state.kind === 'loading' && <div className="loading-skeleton" aria-label="Loading native status" />}
        {state.kind === 'error' && (
          <div className="error-box" role="alert">
            <strong>Native status unavailable</strong>
            <p>The native host did not answer or returned an unexpected payload, so every label below is untrusted. Restart the preview; if the failure persists, treat the build as broken and report it.</p>
          </div>
        )}
        {state.kind === 'ready' && (
          <ul className="inline-list" aria-label="Runtime flags">
            <li className="status-line">
              <span className="dot ok" aria-hidden="true" />
              Mode <span className="mono">&nbsp;{state.status.mode}</span>
            </li>
            <li className="status-line">
              <span className="dot ok" aria-hidden="true" />
              App network plugins: <b>none</b>
            </li>
            <li className="status-line">
              <span className="dot warn" aria-hidden="true" />
              WebView2 egress qualified: <b>no</b>
            </li>
            <li className="status-line">
              <span className="dot bad" aria-hidden="true" />
              Release authorized: <b>no — do not ship, do not print, do not cite as clinical software</b>
            </li>
            <li className="status-line">
              <span className="dot" aria-hidden="true" />
              Build <span className="mono">v{state.status.app_version}</span> · token contract <span className="mono">{state.status.token_contract}</span>
            </li>
          </ul>
        )}
      </section>

      <div className="search-row">
        <h2>Feature integration inventory — 28 sections</h2>
        <input
          type="search"
          className="search-box"
          placeholder="Filter capabilities…"
          aria-label="Filter capabilities"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="surface" role="table" aria-label="Capability inventory" aria-rowcount={filtered.length + 1}>
        <div role="rowgroup">
          <div className="cap-header" role="row">
            <span role="columnheader">Capability</span>
            <span role="columnheader">Status</span>
            <span role="columnheader">Desktop</span>
          </div>
        </div>
        <div role="rowgroup">
          {filtered.length === 0 && <div className="empty">No matching capabilities. Clear the filter to see the full inventory.</div>}
          {filtered.map((r) => (
            <div className="cap-row" role="row" key={r.path}>
              <span role="cell">
                <strong>{r.label}</strong>
                <small>{r.reason}</small>
              </span>
              <span role="cell"><StatusChip status={r.status} /></span>
              <span role="cell" className="mono">{r.path}</span>
            </div>
          ))}
        </div>
      </div>

      <p className="sub sub-spaced">
        <CircleAlert size={14} aria-hidden="true" /> UI implemented ≠ backend connected ≠ qualified ≠ clinically authorized. Only the FHIR fixture inspector invokes a native command.
      </p>
    </>
  );
}

