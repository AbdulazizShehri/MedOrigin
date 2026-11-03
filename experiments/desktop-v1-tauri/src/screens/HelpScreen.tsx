export function HelpScreen() {
  return (
    <>
      <span className="eyebrow">MEDORIGIN / TRUST / HELP &amp; SAFETY</span>
      <h1 className="page-title">Help &amp; safety boundaries</h1>
      <p className="sub">What this preview may and may never do, and how to report a problem.</p>

      <section className="panel" aria-label="Boundaries">
        <h3>Boundaries that are always on</h3>
        <ul className="inline-list">
          <li><b>Synthetic only.</b> Fixtures are FICTIONAL and hash-pinned. No real patient information may be entered, loaded, or generated.</li>
          <li><b>No clinical use.</b> Nothing here diagnoses, prescribes, orders, bills, or writes to any health record.</li>
          <li><b>No Research Core admission.</b> Workspace-derived content never enters research training or evaluation.</li>
          <li><b>No model execution.</b> No model is downloaded, loaded, promoted, or run.</li>
          <li><b>No network use by the app.</b> App-initiated network access is disabled. WebView2 background traffic is unqualified and untrusted.</li>
          <li><b>Honesty over polish.</b> Gated capabilities render as blocked with a reason — never as ready.</li>
        </ul>
      </section>

      <section className="panel" aria-label="Incident workflow">
        <h3>If something looks wrong</h3>
        <ol>
          <li>Stop using the preview. Do not attempt to work around a broken control.</li>
          <li>Record what you did (route, control, exact text) and the build identity from the About screen.</li>
          <li>Report it through the normal engineering channel with the label <span className="mono">medorigin-desktop-v1</span>.</li>
          <li>If you suspect real patient data was involved, treat it as a security incident and follow SECURITY.md.</li>
        </ol>
      </section>

      <section className="panel" aria-label="References">
        <h3>References</h3>
        <ul className="inline-list">
          <li className="status-line"><span className="mono">SECURITY.md</span></li>
          <li className="status-line"><span className="mono">GOVERNANCE.md</span></li>
          <li className="status-line"><span className="mono">docs/design/desktop-v1/SLICE1_SPEC.md</span></li>
        </ul>
      </section>
    </>
  );
}
