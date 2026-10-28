import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

type FixtureId = "patient-minimal" | "patient-invalid-utf8" | "patient-over-limit" | "patient-exact-limit";
type PreviewStatus = {
  mode: string;
  data_access: string;
  release_authorized: boolean;
  production_parity_qualified: boolean;
  app_network_plugins_enabled: boolean;
  webview_runtime_egress_qualified: boolean;
};
type HashResult = {
  contract: string;
  fixture_id: FixtureId;
  bytes: number;
  sha256_hex: string;
  synthetic_only: boolean;
  release_authorized: boolean;
};
const FIXTURES: readonly { id: FixtureId; title: string; kind: string; size: string; sha: string; description: string }[] = [
  { id: "patient-minimal", title: "Minimal Patient", kind: "VALID SYNTHETIC", size: "57 B", description: "A fictional FHIR-shaped resource. No clinical information.", sha: "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0" },
  { id: "patient-invalid-utf8", title: "Invalid encoding", kind: "NEGATIVE CASE", size: "1 B", description: "A single 0xFF byte. Hashing is independent of FHIR parsing.", sha: "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89" },
  { id: "patient-over-limit", title: "Oversize payload", kind: "NEGATIVE CASE", size: "32,769 B", description: "One byte beyond the Python FHIR resource budget.", sha: "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538" },
  { id: "patient-exact-limit", title: "Exact limit", kind: "BOUNDARY CASE", size: "32,768 B", description: "A synthetic Patient padded with whitespace to the limit.", sha: "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e" },
];

export default function App() {
  const [status, setStatus] = useState<PreviewStatus | null>(null);
  const [selected, setSelected] = useState<FixtureId>("patient-minimal");
  const [result, setResult] = useState<HashResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    invoke<PreviewStatus>("preview_status")
      .then((next) => { if (alive) setStatus(next); })
      .catch(() => { if (alive) setError("Native desktop bridge unavailable. Open this preview in Tauri."); });
    return () => { alive = false; };
  }, []);

  const chosen = FIXTURES.find((fixture) => fixture.id === selected)!;
  async function verify() {
    setError("");
    setResult(null);
    setBusy(true);
    try {
      const checked = await invoke<HashResult>("hash_fixture", { fixtureId: selected, maxInputBytes: 65536 });
      if (checked.fixture_id !== selected || !checked.synthetic_only || checked.release_authorized) {
        throw new Error("Unexpected native response contract");
      }
      setResult(checked);
    } catch (reason) {
      setError(typeof reason === "string" ? reason : "The local Rust command refused this request.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="masthead">
        <div className="brand"><span className="brand-mark" aria-hidden="true"><span /><span /><span /></span><span>medorigin</span></div>
        <div className="preview-badge"><span className="live-dot" /> SYNTHETIC / DEVELOPER PREVIEW</div>
      </header>
      <main className="main-content">
        <section className="hero">
          <div className="eyebrow">DESKTOP EXPERIMENT · D1</div>
          <h1>Evidence, locally verified.</h1>
          <p>A minimal Rust-powered preview for fictional test fixtures. No patient data or application network features. WebView2 background egress is not yet isolated.</p>
          <div className="status-strip"><span className="status-pill">LOCAL PROCESS</span><span className="status-pill">READ-ONLY</span><span className="status-pill">NOT RELEASED</span><span className="status-pill">NETWORK ISOLATION NOT VERIFIED</span></div>
        </section>
        <div className="workspace-grid">
          <section className="panel">
            <div className="section-kicker">01 / SAMPLE LIBRARY</div>
            <h2>Choose a fixture</h2>
            <p className="section-help">Each sample is constructed in memory. Paths and uploaded files are not supported.</p>
            <div className="fixture-list">
              {FIXTURES.map((fixture) => (
                <button className={"fixture" + (selected === fixture.id ? " fixture-selected" : "")} type="button" onClick={() => { setSelected(fixture.id); setResult(null); setError(""); }} aria-pressed={selected === fixture.id} key={fixture.id}>
                  <span className="fixture-radio" aria-hidden="true" />
                  <span className="fixture-body"><strong>{fixture.title}</strong><small>{fixture.kind}</small></span>
                  <span className="fixture-size">{fixture.size}</span>
                </button>
              ))}
            </div>
          </section>
          <section className="panel result-panel">
            <div className="section-kicker">02 / VERIFICATION</div>
            <h2>Raw-byte integrity</h2>
            <p className="section-help">{chosen.description}</p>
            <div className="selected-preview">
              <div className="mini-label">SELECTED FIXTURE</div>
              <div className="selected-title">{chosen.title}</div>
              <div className="preview-meta"><span>SHA-256</span><span>{chosen.size}</span></div>
            </div>
            <button className="primary-action" type="button" onClick={verify} disabled={busy || !status}>{busy ? "Verifying locally…" : "Verify with Rust"}<span aria-hidden="true">↗</span></button>
            <div className="verification-output" aria-live="polite">
              {result ? (
                <><span className={"outcome " + (result.sha256_hex === chosen.sha ? "outcome-success" : "outcome-error")}>{result.sha256_hex === chosen.sha ? "✓ MATCHES REFERENCE" : "✕ MISMATCH — BLOCKED"}</span><div className="mini-label">RAW SHA-256 DIGEST</div><code>{result.sha256_hex}</code><div className="output-footnote">Contract: {result.contract}</div></>
              ) : error ? <span className="outcome outcome-error">{error}</span> : <span className="output-placeholder">A local verification result will appear here.</span>}
            </div>
          </section>
        </div>
        <footer className="notice">
          <span className="notice-icon">i</span>
          <div><strong>Unreleased engineering preview</strong><p>{status ? "Rust command bridge active. Four fixed synthetic cases only." : "Local native bridge not yet confirmed."} No clinician workflows, health records, application network plugins, installer qualification, or publishing authorization. WebView2 runtime egress is unqualified.</p></div>
        </footer>
      </main>
    </div>
  );
}
