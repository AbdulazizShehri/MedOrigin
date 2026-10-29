# MedOrigin Desktop D1 — synthetic-only local Tauri preview

**Status: experimental / unpublished / not reviewed for release.** This standalone Tauri 2 + React/TypeScript app is a *consumer* of the sibling isolated Rust D0 fixture-hash crate. It is not a clinician-facing product, a distributable installer, or a replacement for the Python Research Core.

## What is implemented

- One fixed local window, visibly marked **SYNTHETIC / DEVELOPER PREVIEW**.
- Exactly two native commands: `preview_status` and `hash_fixture`.
- Four *fictional, static in-memory* samples with source-bound SHA-256 golden digests. UI accepts only an enumerated fixture ID; Rust validates it again and enforces a byte cap.
- No application HTTP server in the compiled preview, opener/shell/filesystem/updater plugin, remote assets, application telemetry, model weights, Python worker, application network permission, patient records or EHR interaction. Vite's localhost server is **development-only**. **WebView2 itself may contact external services** even when the app has no network plugin; this is not yet an offline/zero-egress-qualified runtime.
- Tauri capability permits core window functionality only; CSP restricts application fetch to local Tauri IPC, **not WebView2's own background network traffic**. Packaging is disabled (`bundle.active=false`), and the app version is intentionally `0.0.0`.
- Rust errors are stable non-sensitive codes. No user-controlled path, URL or file contents enters the command.

## Local developer qualification (free tooling)

```powershell
cd experiments/desktop-d1-tauri
npm ci --no-audit --no-fund
npm run build
cd src-tauri
cargo fmt --all -- --check
cargo check --locked
cargo test --locked
```

A bundle/uninstaller is **not generated**; verify the native window only by running `npm run tauri dev` on an authorized development device and inspecting its behavior. The general D0 Rust 3-OS evidence is not a substitute for D1 Tauri build evidence on each OS.

## Reproducible native Windows UI and egress checks

From an **interactive** Windows desktop, build the local debug preview with `npm run tauri build -- --debug --no-bundle`, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-uia-smoke.ps1 -ExePath '<absolute-path-to-built-debug-exe>'
# Launch the same executable separately; capture its PID as $p.Id:
$p = Start-Process -FilePath '<absolute-path-to-built-debug-exe>' -PassThru
Start-Sleep -Seconds 5
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-egress-snapshot.ps1 -RootPid $p.Id
Stop-Process -Id $p.Id -Force
```

The UI Automation smoke test verifies all four fictional fixture IDs through **React → Tauri IPC → Rust → React** and checks exact SHA-256 goldens. The invalid-encoding and oversize samples are *expected to hash successfully*; this does **not** mean they pass FHIR validation. The egress audit inspects the root process and descendant WebView2 processes; it exits 2 on any observed non-loopback TCP state (including `SynSent`), and fails closed if process/socket enumeration fails. Its separate `tests/windows-egress-probe-selftest.ps1` runs nine mocked scenarios, including external TCP attempts from nested descendants, unrelated-process exclusion, missing-root fail-closed behavior, socket-enumeration errors, and loopback allowance. It does **not** exercise the actual OS network boundary. A clean snapshot is **not** proof of zero network activity.

For a bounded, multi-sample *negative* observation (no firewall/system changes), monitor a separately launched preview by PID for at least a few seconds:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-egress-window-selftest.ps1
# Launch the synthetic debug preview separately, record $p.Id, then:
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-egress-window.ps1 -RootPid $p.Id -DurationSeconds 15 -SampleIntervalMilliseconds 250
```

The window harness invokes the independent process-tree snapshot repeatedly. It fails with exit **2** and `D1_NETWORK_ISOLATION_NO_GO` upon any sampled external TCP socket (including `SynSent`), exit **1** on missing root, unavailable snapshot, error, unmarked output or insufficient samples, and exit **0** only if at least two snapshots completed without seeing an external TCP socket. Its five mocked self-test scenarios verify clean, direct external, delayed external, probe error and ambiguous-success cases; the existing snapshot has its own nine mocked negative tests.

**Important:** The observation interval may miss short-lived connections and cannot detect every UDP/DNS exchange, WebView2 service-level request, proxy route or network packet. A successful observation is **not** a zero-egress assertion or release gate clearance. Proper application-scoped OS network denial, packet-level evidence and separate IPC/UI qualification are still required. Never install a machine-wide block on the shared `msedgewebview2.exe` runtime.

**Observed security NO-GO on Windows, 2026-10-29:** With the local D1 debug preview running, `msedgewebview2.exe` descendants established **external IPv6 TCP port 443** connections (two to three in repeated snapshots). The same problem persisted with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS='--disable-background-networking --disable-component-update'`. This is a runtime observation, not proof of what content was sent or whether the app initiated the traffic. Do **not** claim the desktop is zero-egress/offline-isolated, or allow PHI, release, or clinical use. Any future resolution requires a separately reviewed, application-scoped OS isolation policy and packet-level verification; do not disable system-wide WebView2 security updates or firewall other applications.

## Known blocks

This independent D1 experiment must remain a **Draft** until a separately accepted topology/language decision (ADR-0003 + proposed ADR-0013), reviewed dependency locks/licenses/advisories, Windows/macOS/Linux app-level tests, verified zero network calls, IPC negative tests, WebView2 behavior, accessibility, process resource budgets and signed installer/uninstall lifecycle receipts. No release, tag, protected-main merge, PHI authorization or clinical-performance claim may be inferred from successful builds.
