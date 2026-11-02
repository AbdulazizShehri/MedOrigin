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

### Additional read-only, exact-image process attribution

The older `windows-egress-snapshot.ps1` accepts just a PID and therefore cannot establish the *identity* of a newly inspected process after restart or PID reuse. For stronger **nonrelease evidence only**, run `tests/windows-attributed-egress-preflight.ps1`, passing the **actual native D1 preview image**, SHA-256 measured independently, and the PID returned from launching that same executable:

```powershell
$exe = '<absolute path to YOUR locally compiled medorigin-desktop-d1-preview.exe>'
$p = Start-Process -FilePath $exe -PassThru
try {
  $sha = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-attributed-egress-preflight.ps1 -RootPid $p.Id -ExpectedRootExecutable $exe -ExpectedSha256 $sha
}
finally { if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
```

The preflight checks exact executable filename/hash and the root CIM process image path/start timestamp, includes nested descendants, reads TCP all states and UDP endpoint count, then checks **the root AND every observed descendant creation timestamp again**, and rehashes the on-disk D1 executable at the end to detect mid-observation replacement (without claiming to attest loaded PE memory). A missing/changed process identity, unreadable socket inventory or wrong SHA is a hard nonzero `NO_GO`. An observed non-loopback TCP attempt is also nonzero `NO_GO`. **Zero sockets observed still returns nonzero `NO_GO`** because polling is not OS-enforced packet denial or DNS/UDP egress attribution. This preflight does not change host firewall rules, disable Edge updates or take packet payloads. Its `tests/windows-attributed-egress-selftest.ps1` exercises **14/14 mocked scenarios** on Windows and can be run without building D1. These mocked scenarios demonstrate parser/attribution logic, **not that the real WebView2 runtime is offline**. The standalone D1 debug executable was **not present** during the 2026-11-03 test pass, so no new real WebView2 egress claim is made from this round.

The UI Automation smoke test verifies all four fictional fixture IDs through **React → Tauri IPC → Rust → React** and checks exact SHA-256 goldens. The invalid-encoding and oversize samples are *expected to hash successfully*; this does **not** mean they pass FHIR validation. The egress audit inspects the root process and descendant WebView2 processes; it exits 2 on any observed non-loopback TCP state (including `SynSent`), and fails closed if process/socket enumeration fails. Its separate `tests/windows-egress-probe-selftest.ps1` runs nine mocked scenarios, including external TCP attempts from nested descendants, unrelated-process exclusion, missing-root fail-closed behavior, socket-enumeration errors, and loopback allowance. It does **not** exercise the actual OS network boundary. A clean snapshot is **not** proof of zero network activity.

**Observed security NO-GO on Windows, 2026-10-29:** With the local D1 debug preview running, `msedgewebview2.exe` descendants established **external IPv6 TCP port 443** connections (two to three in repeated snapshots). The same problem persisted with `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS='--disable-background-networking --disable-component-update'`. This is a runtime observation, not proof of what content was sent or whether the app initiated the traffic. Do **not** claim the desktop is zero-egress/offline-isolated, or allow PHI, release, or clinical use. Any future resolution requires a separately reviewed, application-scoped OS isolation policy and packet-level verification; do not disable system-wide WebView2 security updates or firewall other applications.

## Known blocks

This independent D1 experiment must remain a **Draft** until a separately accepted topology/language decision (ADR-0003 + proposed ADR-0013), reviewed dependency locks/licenses/advisories, Windows/macOS/Linux app-level tests, verified zero network calls, IPC negative tests, WebView2 behavior, accessibility, process resource budgets and signed installer/uninstall lifecycle receipts. No release, tag, protected-main merge, PHI authorization or clinical-performance claim may be inferred from successful builds.
