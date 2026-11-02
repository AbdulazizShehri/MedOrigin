import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

type FixtureId = "patient-minimal" | "patient-invalid-utf8" | "patient-over-limit" | "patient-exact-limit" | "observation-minimal" | "observation-bad-subject" | "bundle-valid" | "bundle-bad-reference" | "bundle-duplicate" | "bundle-wrong-type" | "bundle-linked" | "bundle-dangling";
type PreviewStatus = {
  mode: string;
  data_access: string;
  release_authorized: boolean;
  production_parity_qualified: boolean;
  app_network_plugins_enabled: boolean;
  webview_runtime_egress_qualified: boolean;
};
type EnvelopeResult = {
  contract: string;
  fixture_id: FixtureId;
  bytes: number;
  status: "FHIR_ENVELOPE_OK" | "INVALID_UTF8" | "INVALID_JSON" | "INVALID_FHIR_ENVELOPE" | "INVALID_REFERENCE" | "RESOURCE_TOO_LARGE" | "BUNDLE_GRAPH_OK" | "DUPLICATE_ENTRY" | "INVALID_BUNDLE_TYPE" | "INVALID_BUNDLE_ENVELOPE";
  synthetic_only: boolean;
  full_fhir_r4_validated: boolean;
  release_authorized: boolean;
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
  { id: "observation-minimal", title: "Fictional Observation", kind: "VALID SYNTHETIC", size: "251 B", description: "A fictional Observation referencing Patient/synthetic.", sha: "527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19" },
  { id: "observation-bad-subject", title: "Broken patient reference", kind: "NEGATIVE CASE", size: "253 B", description: "An Observation with a missing fictional Patient reference.", sha: "d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838" },
  { id: "bundle-valid", title: "Linked fictional Bundle", kind: "VALID SYNTHETIC", size: "531 B", description: "A local, fictional Patient and Observation linked in one collection.", sha: "3a530a66c0f2b71908b1282985432e405f0f2f412c7ccc0143aa1972d9447983" },
  { id: "bundle-bad-reference", title: "Bundle missing patient", kind: "NEGATIVE CASE", size: "528 B", description: "An Observation points to a fictional patient not in the bundle.", sha: "4aabcfa54309c83052d62b4fdcf1c6635a6cd3d937551e2ab947899345f9f082" },
  { id: "bundle-duplicate", title: "Duplicate Bundle entry", kind: "NEGATIVE CASE", size: "531 B", description: "Two resource entries share the same fictional fullUrl.", sha: "813f8a3b8fee59ba74abdb293c6cac5cca103b390153730e6e3bc4656540f15b" },
  { id: "bundle-wrong-type", title: "Unsupported Bundle type", kind: "NEGATIVE CASE", size: "532 B", description: "Transaction bundles are intentionally not accepted by this offline preview.", sha: "293c10c8abf055e8c1f84bae4913c7246bf9be5bf53dee0fb3c918e32a8346a7" },
  { id: "bundle-linked", title: "Bundle linked by URN", kind: "VALID SYNTHETIC", size: "559 B", description: "The fictional Observation links to the Patient entry fullUrl URN.", sha: "1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88" },
  { id: "bundle-dangling", title: "Bundle dangling URN", kind: "NEGATIVE CASE", size: "559 B", description: "The Observation points to an absent fictional Patient URN.", sha: "1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229" },
];
const EXPECTED_ENVELOPE_STATUS: Record<FixtureId, EnvelopeResult["status"]> = {
  "patient-minimal": "FHIR_ENVELOPE_OK",
  "patient-invalid-utf8": "INVALID_UTF8",
  "patient-over-limit": "RESOURCE_TOO_LARGE",
  "patient-exact-limit": "FHIR_ENVELOPE_OK",
  "observation-minimal": "FHIR_ENVELOPE_OK",
  "observation-bad-subject": "INVALID_REFERENCE",
  "bundle-valid": "BUNDLE_GRAPH_OK",
  "bundle-bad-reference": "INVALID_REFERENCE",
  "bundle-duplicate": "DUPLICATE_ENTRY",
  "bundle-wrong-type": "INVALID_BUNDLE_TYPE",
  "bundle-linked": "BUNDLE_GRAPH_OK",
  "bundle-dangling": "INVALID_REFERENCE",
};

export default function App() {
  const [status, setStatus] = useState<PreviewStatus | null>(null);
  const [selected, setSelected] = useState<FixtureId>("patient-minimal");
  const [result, setResult] = useState<HashResult | null>(null);
  const [envelope, setEnvelope] = useState<EnvelopeResult | null>(null);
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
    setEnvelope(null);
    setBusy(true);
    try {
      const checked = await invoke<HashResult>("hash_fixture", { fixtureId: selected, maxInputBytes: 65536 });
      if (
        checked.fixture_id !== selected || !checked.synthetic_only || checked.release_authorized ||
        checked.bytes !== Number(chosen.size.replace(/[^0-9]/g, "")) ||
        checked.contract !== "medorigin-desktop-d0-raw-sha256-v1"
      ) {
        throw new Error("Unexpected native hash response contract");
      }
      if (checked.sha256_hex !== chosen.sha) {
        setResult(checked);
        return;
      }
      const inspected = await invoke<EnvelopeResult>("inspect_fhir_fixture_envelope", {
        fixtureId: selected, maxInputBytes: 65536,
      });
      if (
        inspected.fixture_id !== selected || !inspected.synthetic_only ||
        inspected.release_authorized || inspected.full_fhir_r4_validated ||
        inspected.contract !== "medorigin-d0-synthetic-fhir-envelope-v1" ||
        inspected.bytes !== checked.bytes ||
        inspected.status !== EXPECTED_ENVELOPE_STATUS[selected]
      ) {
        throw new Error("Unexpected synthetic FHIR envelope response contract");
      }
      // Do not display a successful hash before validating the second bridge
      // response; otherwise an error in that bridge would be obscured by MATCHES.
      setResult(checked);
      setEnvelope(inspected);
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
                <button className={"fixture" + (selected === fixture.id ? " fixture-selected" : "")} type="button" disabled={busy} onClick={() => { setSelected(fixture.id); setResult(null); setEnvelope(null); setError(""); }} aria-pressed={selected === fixture.id} key={fixture.id}>
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
            {envelope && (
              <div className="envelope-result" role="status">
                <div className="mini-label">FICTIONAL FHIR ENVELOPE CHECK</div>
                <strong>{["FHIR_ENVELOPE_OK", "BUNDLE_GRAPH_OK"].includes(envelope.status) ? "Basic fictional resource fields found" : envelope.status.replace(/_/g, " ")}</strong>
                <p>{envelope.bytes.toLocaleString()} bytes checked. Not a full FHIR R4, clinical, or profile validation.</p>
              </div>
            )}
          </section>
        </div>
        <footer className="notice">
          <span className="notice-icon">i</span>
          <div><strong>Unreleased engineering preview</strong><p>{status ? "Rust command bridge active. Twelve fixed synthetic cases only." : "Local native bridge not yet confirmed."} No clinician workflows, health records, application network plugins, installer qualification, or publishing authorization. WebView2 runtime egress is unqualified.</p></div>
        </footer>
      </main>
    </div>
  );
}
